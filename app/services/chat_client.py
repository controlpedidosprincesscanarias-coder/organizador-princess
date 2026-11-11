"""
services/chat_client.py  ·  v1.2  ·  © VAMA 2026
=================================================
Cliente de chat interno en tiempo real entre usuarios de "Control de
Pedidos", visto desde main_agenda (Organizador Princess).

DISEÑO
------
Reutiliza EXACTAMENTE el mismo mecanismo de autenticación que ya usa
pedidos_agenda_bridge.py: credenciales reales del usuario (BRIDGE_USER /
BRIDGE_PASSWORD, resueltas por %USERNAME% de Windows vía
db.sqlite.get_bridge_credentials()) contra POST /api/bridge/login, y el
mismo User-Agent de navegador para pasar el Worker de Cloudflare que hace
de proxy delante de Render (bloquea con 403 el User-Agent por defecto de
las librerías HTTP de Python al considerarlo tráfico de bot).

No hay login nuevo ni credenciales nuevas: es la misma cuenta con la que
ya se conecta el bridge de alertas.

DOS SERVICIOS DISTINTOS (v1.1, 16 julio 2026)
----------------------------------------------
Desde control_pedidos v12.7.0 el chat vive en un Web Service de Render
SEPARADO del principal (aislamiento de memoria, ver CHANGELOG). Por eso
ahora hay dos URLs:

- `CONTROL_PEDIDOS_URL`: SOLO para el login (`/api/bridge/login`), que
  sigue haciéndose contra el servicio principal — ahí vive la tabla
  `usuarios`.
- `CHAT_URL`: para todo lo demás del chat (REST `/api/chat/*` y el socket
  de Socket.IO). Este cliente NO es un navegador, así que no aplican las
  restricciones de cookies entre dominios distintos: la cookie de sesión
  que devuelve el login contra `CONTROL_PEDIDOS_URL` se reenvía tal cual
  a `CHAT_URL`, y ese servicio la valida porque comparte la misma
  `SECRET_KEY` (ver control_pedidos_chat/GUIA_DESPLIEGUE.md).

TRANSPORTE
----------
Se usa python-socketio (transports=["websocket", "polling"]). Si el
Worker de Cloudflare no reenvía la cabecera Upgrade de WebSocket (no se
puede confirmar sin revisar su código), la librería cae sola a
long-polling: el chat sigue funcionando, solo que con más latencia. No
hace falta ningún cambio en este módulo si eso ocurre.

HILOS
-----
python-socketio gestiona su propio hilo de fondo para la conexión. Los
callbacks (on_nuevo_mensaje, on_conectado, on_error) se ejecutan en ESE
hilo, nunca en el hilo principal de Tkinter — igual que ocurre con
pedidos_agenda_bridge.py. Por eso este módulo nunca toca widgets
directamente: encola cada evento en una queue.Queue thread-safe y quien
la lee (ui/ventana_chat.py) lo hace desde un app.after() en el hilo
principal, siguiendo el mismo patrón "ANTI-REGRESION" que
negocio.alertas.poll_alertas ya usa para los popups.
"""

import json
import logging
import mimetypes
import os
import queue
import re
import subprocess
import sys
import threading
import base64
import urllib.parse
from io import BytesIO

import requests
import socketio
from PIL import Image

from db.sqlite import get_bridge_credentials, load_config

log = logging.getLogger(__name__)

# Servicio PRINCIPAL (pedidos/alertas) — solo se usa aquí para el login.
# Mismo Worker de Cloudflare que usa pedidos_agenda_bridge.py.
CONTROL_PEDIDOS_URL = "https://proxy.controlpedidosprincess-canarias.workers.dev"

# Servicio de CHAT independiente (v1.1) — REST /api/chat/* y Socket.IO.
# Pasa por el Worker de Cloudflare (proxy-chat), igual que CONTROL_PEDIDOS_URL
# pasa por su propio Worker — así se evita el bloqueo del antivirus ESET a
# las IPs de Render directas. Desplegado el 20/07/2026.
CHAT_URL = "https://proxy-chat.controlpedidosprincess-canarias.workers.dev"

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# ── Seguridad de los adjuntos (v4.16.9) ─────────────────────────────────────
# El nombre del archivo y la URL los pone el servidor a partir de lo que mandó
# otro usuario, así que aquí NO se confía en ellos: se limpia el nombre, se
# comprueba que la URL es del almacén de adjuntos y solo se abren
# directamente tipos inofensivos.
_HOSTS_ADJUNTOS = (".supabase.co",)          # ampliable con config.json: "chat_hosts_adjuntos"
_ADJUNTO_MAX_DESCARGA = 12 * 1024 * 1024     # el servidor limita a 10 MB
_RESERVADOS_WIN = {"con", "prn", "aux", "nul", *{f"com{i}" for i in range(1, 10)},
                   *{f"lpt{i}" for i in range(1, 10)}}
_RE_NOMBRE_MALO = re.compile(r'[\x00-\x1f\x7f<>:"/\\|?*\u202a-\u202e\u2066-\u2069]')
# Se abren con el programa por defecto SOLO estas extensiones; el resto se
# guarda y se muestra en el Explorador (el usuario decide).
EXT_ABRIR_DIRECTO = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".pdf", ".txt", ".csv",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".odt", ".ods", ".odp", ".rtf",
}


def nombre_adjunto_seguro(nombre) -> str:
    """Nombre base sin rutas ni caracteres peligrosos ni nombres reservados."""
    nombre = str(nombre or "").replace("\\", "/").split("/")[-1]
    nombre = _RE_NOMBRE_MALO.sub("_", nombre).strip(" .")
    if not nombre:
        nombre = "archivo"
    base, ext = os.path.splitext(nombre)
    if base.lower() in _RESERVADOS_WIN:
        nombre = "_" + nombre
    if len(nombre) > 120:
        ext = ext if len(ext) <= 10 else ""
        nombre = nombre[:120 - len(ext)] + ext
    return nombre


def url_adjunto_permitida(url) -> bool:
    try:
        u = urllib.parse.urlparse(str(url))
    except Exception:
        return False
    if u.scheme != "https" or not u.hostname:
        return False
    extra = ()
    try:
        extra = tuple(h.lower() for h in (load_config().get("chat_hosts_adjuntos") or []))
    except Exception:
        pass
    host = u.hostname.lower()
    return any(host.endswith(h) for h in _HOSTS_ADJUNTOS + extra)


# Tipos de evento que se encolan para la UI (ver ChatClient.eventos)
EVT_CONECTADO      = "conectado"
EVT_DESCONECTADO   = "desconectado"
EVT_NUEVO_MENSAJE  = "nuevo_mensaje"
EVT_ERROR          = "error"
EVT_AVATAR         = "avatar_cambiado"   # (v4.18.28) foto de perfil de una persona o grupo
EVT_ELIMINADO      = "mensaje_eliminado"  # (v4.18.46) un mensaje se eliminó (chat v1.4.0)

_LADO_AVATAR = 256            # las fotos de perfil se suben en cuadrado de 256 px (como el móvil)
_AVATAR_MAX_DESCARGA = 1024 * 1024


def preparar_avatar(ruta_archivo: str) -> bytes:
    """Recorta la imagen al centro en cuadrado, la reduce a 256 px y la pasa a JPEG
    (lo mismo que hace la app del móvil). Respeta la orientación de las fotos de cámara."""
    from PIL import ImageOps
    img = Image.open(ruta_archivo)
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:  # noqa: BLE001 — EXIF roto: se usa tal cual
        pass
    img = ImageOps.fit(img.convert("RGB"), (_LADO_AVATAR, _LADO_AVATAR), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()


class ChatClient:
    """Envoltorio de alto nivel: login + REST de historial + socket.io."""

    def __init__(self):
        self._http = requests.Session()
        self._http.headers.update({"User-Agent": _USER_AGENT})
        self._sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=0,   # 0 = reintenta indefinidamente
            reconnection_delay=2,
            reconnection_delay_max=30,
        )
        self.username = ""
        self.nombre   = ""
        self.rol      = ""
        self._logged_in = False

        # Caché username(lower) → nombre real, para mostrar "Jesús Curbelo"
        # en vez de "dcompras" en mensajes/títulos/lista de conversaciones.
        # Se rellena con refrescar_mapa_nombres() (llamar en un hilo de
        # fondo — hace una petición REST) y se lee con nombre_de().
        self._mapa_nombres = {}
        self._mapa_nombres_lock = threading.Lock()
        # (v4.18.28) Fotos de perfil: clave ("user:<usuario>" o canal_id de un grupo) → URL.
        self._mapa_avatares = {}
        self.mi_foto = None

        # Eventos hacia la UI (thread-safe) — ver EVT_* arriba.
        # Cada item: {"tipo": EVT_..., ...datos}
        self.eventos: "queue.Queue[dict]" = queue.Queue()

        self._sio.on("connect", self._on_connect)
        self._sio.on("disconnect", self._on_disconnect)
        self._sio.on("nuevo_mensaje", self._on_nuevo_mensaje)
        self._sio.on("error_chat", self._on_error_chat)
        self._sio.on("avatar_cambiado", self._on_avatar_cambiado)
        self._sio.on("mensaje_eliminado", self._on_mensaje_eliminado)

    # ── Login (idéntico en espíritu a _Session.login() del bridge) ──────────

    def login(self, username_win=None) -> bool:
        bridge_user, bridge_password = get_bridge_credentials(username_win)
        if not bridge_user or not bridge_password:
            log.warning("ChatClient: sin credenciales guardadas (Admin -> Mi Usuario).")
            self.eventos.put({"tipo": EVT_ERROR,
                               "mensaje": "No hay credenciales guardadas. "
                                          "Configúralas en Admin -> Mi Usuario."})
            return False
        try:
            resp = self._http.post(
                CONTROL_PEDIDOS_URL.rstrip("/") + "/api/bridge/login",
                data=json.dumps({"username": bridge_user, "password": bridge_password}),
                headers={"Content-Type": "application/json"},
                timeout=20,
            )
            data = resp.json()
        except Exception as exc:
            log.warning("ChatClient: error de red en login — %s", exc)
            self.eventos.put({"tipo": EVT_ERROR, "mensaje": f"Sin conexión: {exc}"})
            return False

        self._logged_in = bool(data.get("ok"))
        if not self._logged_in:
            err = data.get("error", "credenciales incorrectas")
            log.warning("ChatClient: login fallido — %s", err)
            self.eventos.put({"tipo": EVT_ERROR, "mensaje": err})
            return False

        self.username = data.get("username", bridge_user)
        self.nombre   = data.get("nombre", bridge_user)
        self.rol      = data.get("rol", "")
        log.info("ChatClient: sesión iniciada como '%s'", self.username)
        return True

    def _cookie_header(self) -> str:
        """La cookie de sesión (puesta por /api/bridge/login contra
        CONTROL_PEDIDOS_URL) no se reenvía sola a CHAT_URL: son dominios
        distintos y `requests` respeta el dominio de la cookie igual que un
        navegador. Hay que forzarla a mano en cada petición al chat — tanto
        en el socket (ya se hacía) como en el REST (antes no, causaba 401
        en /api/chat/* aunque el login hubiera ido bien)."""
        return "; ".join(f"{c.name}={c.value}" for c in self._http.cookies)

    # ── Conexión socket.io (usa las cookies ya obtenidas en login()) ────────

    def conectar(self):
        """No bloquea: lanza la conexión en un hilo de fondo y vuelve al
        instante. El resultado (éxito o error) llega por self.eventos."""
        if not self._logged_in:
            log.warning("ChatClient: conectar() llamado sin login previo.")
            return
        if self._sio.connected:
            return

        def _intentar_conectar():
            self._sio.connect(
                CHAT_URL,
                headers={"User-Agent": _USER_AGENT, "Cookie": self._cookie_header()},
                transports=["websocket", "polling"],
                wait_timeout=20,
            )

        def _run():
            try:
                _intentar_conectar()
            except Exception as exc:
                # Mismo caso que en _get_rest/_post_rest: si la cookie ya
                # no es válida (p. ej. SECRET_KEY rotado en un redeploy),
                # reintentamos una vez con una sesión nueva antes de
                # rendirnos y avisar al usuario.
                log.warning("ChatClient: fallo al conectar el socket, reintentando login — %s", exc)
                if self.login():
                    try:
                        _intentar_conectar()
                        return
                    except Exception as exc2:
                        exc = exc2
                log.warning("ChatClient: no se pudo conectar el socket — %s", exc)
                self.eventos.put({"tipo": EVT_ERROR, "mensaje": f"Chat sin conexión: {exc}"})

        threading.Thread(target=_run, daemon=True).start()

    def desconectar(self):
        try:
            if self._sio.connected:
                self._sio.disconnect()
        except Exception:
            pass

    def iniciar_conexion_en_segundo_plano(self, username_win=None):
        """No bloquea: arranca login()+conectar() en un hilo de fondo desde
        que arranca el Organizador, sin esperar a que el usuario abra la
        ventana de chat — mismo patrón que pedidos_agenda_bridge con las
        alertas de pedidos (v1.2). Necesario para poder avisar con un popup
        de un mensaje nuevo aunque la ventana de chat esté cerrada."""
        def _run():
            if not self._logged_in:
                if not self.login(username_win):
                    return
            self.conectar()
            self.refrescar_mapa_nombres()   # para que "quién escribe" ya
                                             # salga con nombre real desde
                                             # el primer mensaje que llegue
        threading.Thread(target=_run, daemon=True, name="ChatClient-Inicio").start()

    @property
    def conectado(self) -> bool:
        return self._sio.connected

    # ── Envío ─────────────────────────────────────────────────────────────

    def enviar_mensaje(self, contenido: str, canal_id: str = None, destinatario: str = None,
                       responde_a: int = None):
        payload = {"contenido": contenido}
        if canal_id:
            payload["canal_id"] = canal_id
        if destinatario:
            payload["destinatario"] = destinatario
        if responde_a:
            payload["responde_a"] = responde_a      # (v4.18.46) responder citando (chat v1.4.0)
        if self._sio.connected:
            self._sio.emit("enviar_mensaje", payload)
        else:
            # Sin socket vivo (p.ej. justo tras un cold-start de Render):
            # se manda igual por REST, que es la misma ruta que usa el
            # frontend web y nunca depende de que el WebSocket esté arriba.
            self._post_rest("/api/chat/mensajes", payload)

    def eliminar_mensaje(self, mensaje_id: int) -> dict:
        """(v4.18.46) Elimina un mensaje propio (chat v1.4.0). {"ok": True, ...} o {"error": "..."}."""
        return self._post_rest(f"/api/chat/mensajes/{int(mensaje_id)}/eliminar", {})

    def reenviar_mensaje(self, mensaje_id: int, canal_id: str = None, destinatario: str = None) -> dict:
        """(v4.18.46) Reenvía un mensaje a otra conversación (chat v1.4.0)."""
        body = {"canal_id": canal_id} if canal_id else {"destinatario": destinatario}
        return self._post_rest(f"/api/chat/mensajes/{int(mensaje_id)}/reenviar", body)

    def unirse_canal(self, canal_id: str):
        if self._sio.connected:
            self._sio.emit("unirse_canal", {"canal_id": canal_id})

    # ── Archivos e imágenes (v1.3 · 2026-07-23) ─────────────────────────────
    # Las imágenes se redimensionan y comprimen ANTES de enviarlas (no hay
    # límite fijo de tamaño de cara al usuario) — un documento (PDF/Word/
    # etc.) no se puede redimensionar, así que ese va tal cual, sujeto al
    # tope duro del servidor (ADJUNTO_MAX_BYTES, ver control_pedidos_chat).
    _EXT_IMAGEN = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
    _LADO_MAX_IMAGEN = 1600     # px, el lado más largo tras redimensionar
    _CALIDAD_JPEG = 85
    _ADJUNTO_MAX_BYTES_LOCAL = 10 * 1024 * 1024  # debe coincidir con el servidor

    def enviar_archivo(self, ruta_archivo: str, canal_id: str = None,
                        destinatario: str = None) -> dict:
        """Envía una imagen (redimensionada) o un documento (PDF/Word/etc.,
        tal cual). Devuelve el dict de respuesta del servidor
        ({"ok": True, "mensaje": {...}} o {"error": "..."}). No lanza
        excepciones de red — las convierte en {"error": "..."} para que la
        ventana pueda mostrar el motivo sin romperse."""
        nombre_archivo = os.path.basename(ruta_archivo)
        ext = os.path.splitext(nombre_archivo)[1].lower()
        mime_type = mimetypes.guess_type(nombre_archivo)[0] or "application/octet-stream"

        try:
            if ext in self._EXT_IMAGEN:
                datos, mime_type = self._preparar_imagen(ruta_archivo)
            else:
                with open(ruta_archivo, "rb") as f:
                    datos = f.read()
        except Exception as exc:
            return {"error": f"No se pudo leer el archivo: {exc}"}

        if len(datos) > self._ADJUNTO_MAX_BYTES_LOCAL:
            return {"error": f"El archivo pesa demasiado (máximo "
                              f"{self._ADJUNTO_MAX_BYTES_LOCAL // (1024*1024)} MB)."}

        payload = {
            "nombre_archivo": nombre_archivo,
            "mime_type": mime_type,
            "contenido_base64": base64.b64encode(datos).decode("ascii"),
        }
        if canal_id:
            payload["canal_id"] = canal_id
        if destinatario:
            payload["destinatario"] = destinatario
        return self._post_rest("/api/chat/mensajes/archivo", payload)

    def _preparar_imagen(self, ruta_archivo: str):
        """Redimensiona (lado más largo a _LADO_MAX_IMAGEN) y comprime.
        PNG con transparencia se mantiene como PNG; el resto se convierte a
        JPEG, que comprime mucho mejor para fotos. Devuelve (bytes, mime)."""
        img = Image.open(ruta_archivo)
        img.thumbnail((self._LADO_MAX_IMAGEN, self._LADO_MAX_IMAGEN), Image.LANCZOS)
        tiene_alfa = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)
        buf = BytesIO()
        if tiene_alfa:
            img.save(buf, format="PNG", optimize=True)
            mime = "image/png"
        else:
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(buf, format="JPEG", quality=self._CALIDAD_JPEG, optimize=True)
            mime = "image/jpeg"
        return buf.getvalue(), mime

    @staticmethod
    def descargar_bytes(url: str) -> bytes:
        """(v4.18.44) Descarga un adjunto a memoria con las mismas comprobaciones de siempre: solo del
        almacén de adjuntos (url_adjunto_permitida), sin redirecciones y con tamaño máximo. Lo usan
        descargar_adjunto, guardar_adjunto_como y las miniaturas de las imágenes."""
        if not url_adjunto_permitida(url):
            raise ValueError("La dirección del adjunto no es de confianza.")
        with requests.get(url, timeout=30, stream=True, allow_redirects=False) as resp:
            resp.raise_for_status()
            declarado = int(resp.headers.get("Content-Length") or 0)
            if declarado > _ADJUNTO_MAX_DESCARGA:
                raise ValueError("El adjunto es demasiado grande.")
            datos = bytearray()
            for trozo in resp.iter_content(65536):
                datos.extend(trozo)
                if len(datos) > _ADJUNTO_MAX_DESCARGA:
                    raise ValueError("El adjunto es demasiado grande.")
        return bytes(datos)

    def guardar_adjunto_como(self, url: str, destino: str) -> str:
        """(v4.18.44) «Guardar como…»: descarga el adjunto y lo guarda donde ha elegido el usuario en
        el diálogo de Windows (que ya pregunta si quiere reemplazar un archivo existente)."""
        datos = self.descargar_bytes(url)
        with open(destino, "wb") as f:
            f.write(datos)
        return destino

    def descargar_adjunto(self, url: str, nombre_archivo: str) -> str:
        """Descarga un adjunto a la carpeta Descargas del usuario (nombre
        limpio y libre de colisiones) y devuelve la ruta local. Lanza
        excepción si falla — quien llame decide cómo avisar al usuario.

        (v4.16.9) El nombre se limpia aquí aunque el servidor ya lo haga
        (los mensajes antiguos pueden traer nombres con rutas), la URL debe
        ser del almacén de adjuntos y el archivo se crea de forma exclusiva
        dentro de Descargas."""
        datos = self.descargar_bytes(url)
        nombre = nombre_adjunto_seguro(nombre_archivo)
        carpeta = os.path.realpath(os.path.join(os.path.expanduser("~"), "Downloads"))
        os.makedirs(carpeta, exist_ok=True)
        base, ext = os.path.splitext(nombre)
        n = 0
        while True:
            ruta = os.path.join(carpeta, nombre if n == 0 else f"{base} ({n}){ext}")
            if os.path.dirname(os.path.realpath(ruta)) != carpeta:
                raise ValueError("Nombre de archivo no válido.")
            try:
                with open(ruta, "xb") as f:      # "x": nunca pisa un archivo existente
                    f.write(datos)
                return ruta
            except FileExistsError:
                n += 1

    @staticmethod
    def abrir_archivo(ruta: str):
        """Abre un adjunto ya descargado. Solo se abre directamente con el
        programa por defecto si es un tipo inofensivo (imágenes, PDF,
        Office, texto); cualquier otro se muestra en el Explorador sin
        ejecutarlo. (v4.16.9)"""
        ext = os.path.splitext(ruta)[1].lower()
        if sys.platform.startswith("win"):
            if ext in EXT_ABRIR_DIRECTO:
                os.startfile(ruta)  # noqa: S606
            else:
                subprocess.Popen(["explorer", "/select,", os.path.normpath(ruta)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", ruta] if ext in EXT_ABRIR_DIRECTO else ["open", "-R", ruta])
        else:
            subprocess.Popen(["xdg-open", ruta if ext in EXT_ABRIR_DIRECTO else os.path.dirname(ruta)])

    # ── Historial / listados (REST — funciona con o sin socket conectado) ──

    def obtener_canales(self) -> list:
        canales = self._get_rest("/api/chat/canales").get("canales", [])
        with self._mapa_nombres_lock:
            for c in canales:
                if c.get("tipo") == "grupo" and c.get("canal_id"):
                    self._mapa_avatares[c["canal_id"]] = c.get("avatar")
        return canales

    def crear_grupo(self, nombre: str, usuarios: list) -> dict:
        """usuarios: usernames de los compañeros a añadir (sin incluirte a
        ti — el servidor te añade automáticamente como creador)."""
        return self._post_rest("/api/chat/grupos", {"nombre": nombre, "usuarios": usuarios})

    def obtener_usuarios(self) -> list:
        return self._get_rest("/api/chat/usuarios").get("usuarios", [])

    def refrescar_mapa_nombres(self):
        """Descarga la lista de usuarios y actualiza el caché username→nombre
        real que usa nombre_de(). Hace una petición REST — llamar SIEMPRE en
        un hilo de fondo, nunca en el hilo de Tkinter. Si falla (sin red,
        servicio caído), se queda con lo que ya tuviera en caché — nunca
        lanza, para que un fallo aquí no rompa el pintado de mensajes."""
        try:
            usuarios = self.obtener_usuarios()
            with self._mapa_nombres_lock:
                for u in usuarios:
                    self._mapa_nombres[u["username"].lower()] = u.get("nombre") or u["username"]
                    self._mapa_avatares["user:" + u["username"].lower()] = u.get("avatar")
            if self.username:
                self.mi_foto = self.mi_avatar()
                self.obtener_canales()          # recoge las fotos de los grupos
        except Exception as exc:
            log.warning("ChatClient: no se pudo refrescar el mapa de nombres — %s", exc)

    # ── Fotos de perfil (v4.18.28; servidor del chat v1.3.0) ─────────────────

    def avatar_de(self, username: str):
        """URL de la foto de una persona, o None (se pintan sus iniciales)."""
        if not username:
            return None
        if self.username and username.lower() == self.username.lower():
            return self.mi_foto
        with self._mapa_nombres_lock:
            return self._mapa_avatares.get("user:" + username.lower())

    def avatar_canal(self, canal_id: str, otro_usuario: str = None):
        """Foto de una conversación: la de la otra persona en un privado, la del grupo en
        un grupo, ninguna en General."""
        if not canal_id or canal_id == "general":
            return None if not otro_usuario else self.avatar_de(otro_usuario)
        if canal_id.startswith("grp:"):
            with self._mapa_nombres_lock:
                return self._mapa_avatares.get(canal_id)
        if not otro_usuario and canal_id.startswith("dm:") and self.username:
            partes = [p for p in canal_id[3:].split(":") if p.lower() != self.username.lower()]
            otro_usuario = partes[0] if partes else None
        return self.avatar_de(otro_usuario)

    def mi_avatar(self):
        return self._get_rest("/api/chat/avatar").get("avatar")

    def cambiar_avatar(self, ruta_archivo: str = None, canal_id: str = None) -> dict:
        """Sube la foto (la tuya, o la del grupo si se da `canal_id`) o la quita si
        `ruta_archivo` es None. Devuelve el JSON del servidor ({"ok", "avatar"} o {"error"})."""
        if ruta_archivo:
            try:
                datos = preparar_avatar(ruta_archivo)
            except Exception as exc:  # noqa: BLE001
                return {"error": f"No se pudo leer la imagen: {exc}"}
            cuerpo = {"contenido_base64": base64.b64encode(datos).decode("ascii")}
        else:
            cuerpo = {"borrar": True}
        if canal_id:
            cuerpo["canal_id"] = canal_id
        resultado = self._post_rest("/api/chat/avatar", cuerpo)
        if resultado.get("ok"):
            self._aplicar_avatar(canal_id or ("user:" + (self.username or "").lower()),
                                 resultado.get("avatar"))
        elif not resultado.get("error"):
            resultado["error"] = "El servidor del chat no admite todavía fotos de perfil."
        return resultado

    def _aplicar_avatar(self, clave, url):
        if not clave:
            return
        with self._mapa_nombres_lock:
            self._mapa_avatares[clave] = url
        if self.username and clave == "user:" + self.username.lower():
            self.mi_foto = url

    def descargar_avatar(self, url: str) -> bytes:
        """Bytes de una foto de perfil (solo del almacén de adjuntos, https y máx. 1 MB)."""
        if not url_adjunto_permitida(url):
            raise ValueError("La dirección de la foto no es de confianza.")
        with requests.get(url, timeout=20, stream=True, allow_redirects=False) as resp:
            resp.raise_for_status()
            datos = bytearray()
            for trozo in resp.iter_content(65536):
                datos.extend(trozo)
                if len(datos) > _AVATAR_MAX_DESCARGA:
                    raise ValueError("La foto es demasiado grande.")
        return bytes(datos)

    def nombre_de(self, username: str) -> str:
        """Nombre real de un username (p.ej. 'dcompras' → 'Jesús Curbelo'),
        o el propio username tal cual si aún no está en caché (primer
        arranque, antes de que refrescar_mapa_nombres() haya terminado)."""
        if not username:
            return username
        with self._mapa_nombres_lock:
            return self._mapa_nombres.get(username.lower(), username)

    def obtener_mensajes(self, canal_id: str = None, destinatario: str = None) -> dict:
        params = {}
        if canal_id:
            params["canal_id"] = canal_id
        if destinatario:
            params["destinatario"] = destinatario
        return self._get_rest("/api/chat/mensajes", params=params)

    def _get_rest(self, path, params=None, _reintentado=False) -> dict:
        try:
            resp = self._http.get(
                CHAT_URL.rstrip("/") + path,
                params=params,
                headers={"Cookie": self._cookie_header()},
                timeout=20,
            )
            if resp.status_code == 401 and not _reintentado:
                # La cookie dejó de ser válida (SECRET_KEY rotado en un
                # redeploy, sesión caducada, etc.) — mismo patrón que ya
                # usa pedidos_agenda_bridge.py: reintentar el login una
                # vez, solo, y repetir la petición con la cookie nueva.
                # Sin esto, el chat se queda "colgado" con una cookie
                # muerta hasta que alguien cierra y reabre el Organizador
                # a mano (visto en producción el 27/07/2026).
                log.info("ChatClient: 401 en GET %s — reintentando login", path)
                if self.login():
                    return self._get_rest(path, params=params, _reintentado=True)
                return {}
            return resp.json()
        except Exception as exc:
            log.warning("ChatClient: error REST GET %s — %s", path, exc)
            return {}

    def _post_rest(self, path, body, _reintentado=False) -> dict:
        try:
            resp = self._http.post(
                CHAT_URL.rstrip("/") + path,
                data=json.dumps(body),
                headers={"Content-Type": "application/json",
                         "Cookie": self._cookie_header()},
                timeout=20,
            )
            if resp.status_code == 401 and not _reintentado:
                log.info("ChatClient: 401 en POST %s — reintentando login", path)
                if self.login():
                    return self._post_rest(path, body, _reintentado=True)
                return {}
            return resp.json()
        except Exception as exc:
            log.warning("ChatClient: error REST POST %s — %s", path, exc)
            return {}

    # ── Callbacks de socket.io (hilo de fondo — NO tocar Tkinter aquí) ──────

    def _on_connect(self):
        log.info("ChatClient: socket conectado")
        self.eventos.put({"tipo": EVT_CONECTADO})

    def _on_disconnect(self):
        log.info("ChatClient: socket desconectado")
        self.eventos.put({"tipo": EVT_DESCONECTADO})

    def _on_nuevo_mensaje(self, data):
        self.eventos.put({"tipo": EVT_NUEVO_MENSAJE, "mensaje": data})

    def _on_error_chat(self, data):
        self.eventos.put({"tipo": EVT_ERROR, "mensaje": data.get("error", "Error de chat")})

    def _on_mensaje_eliminado(self, data):
        self.eventos.put({"tipo": EVT_ELIMINADO, "mensaje": data or {}})

    def _on_avatar_cambiado(self, data):
        clave = str((data or {}).get("clave") or "")
        if clave.startswith("user:"):
            clave = "user:" + clave[5:].lower()
        self._aplicar_avatar(clave, (data or {}).get("avatar"))
        self.eventos.put({"tipo": EVT_AVATAR, "clave": clave, "avatar": (data or {}).get("avatar")})


# Instancia única compartida por toda la app, igual que hace el bridge
# con su propia _Session.
_cliente_global = None

def cuenta_chat_configurada(username_win=None) -> bool:
    """(v4.18.42) True si hay usuario y contraseña de Control de Pedidos guardados para este usuario
    de Windows (Administración → Mi Usuario). Sin ellos el chat no puede iniciar sesión, y la
    ventana se abría vacía, sin conversaciones y sin decir por qué."""
    usuario, clave = get_bridge_credentials(username_win)
    return bool(usuario and clave)


def get_chat_client() -> ChatClient:
    global _cliente_global
    if _cliente_global is None:
        _cliente_global = ChatClient()
    return _cliente_global
