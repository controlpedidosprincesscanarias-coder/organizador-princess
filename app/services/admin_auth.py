"""
services/admin_auth.py
Sistema de usuario/contraseña de Administración — sin credenciales hardcodeadas.

Reglas (ver especificación "Sistema de usuario y contraseña Admin"):
  · El usuario de login es siempre el usuario de Windows (os.getlogin()).
  · Si ese usuario YA existe en Control de Pedidos, la contraseña
    introducida debe coincidir con la de Control de Pedidos — se valida
    contra la plataforma en cada intento (no hay copia local de verdad).
  · Si NO existe, se pide nombre a mostrar + contraseña (y repetición),
    se guarda localmente (cifrado) y se notifica a Control de Pedidos
    para que un administrador cree la cuenta real.
  · Persistencia local: SOLO nombre y contraseña (con hash+salt) en un
    archivo cifrado con Fernet. Nunca en claro, nunca en config.json.
  · Máximo 3 intentos fallidos → bloqueo temporal.

Este módulo no depende de tkinter: solo lógica de negocio, red y
almacenamiento. La ventana de login vive en app/ui (o main_agenda.py) y
llama a las funciones de aquí.
"""
import os
import sys
import json
import base64
import hashlib
import secrets as _secrets
import time
import urllib.request
import urllib.error

from db.sqlite import (CONFIG_FILE, get_bridge_credentials, get_nombre_usuario,
                        update_bridge_credentials)

# ── Ficheros locales ──────────────────────────────────────────────────────
_APPDATA_DIR   = os.path.dirname(CONFIG_FILE)
_KEY_FILE      = os.path.join(_APPDATA_DIR, "admin_auth.key")
_STORE_FILE    = os.path.join(_APPDATA_DIR, "admin_auth.dat")

# ── Config de bloqueo ─────────────────────────────────────────────────────
MAX_INTENTOS          = 3
BLOQUEO_SEGUNDOS      = 5 * 60   # 5 minutos de bloqueo temporal
PBKDF2_ITERACIONES    = 200_000

# ── URL de Control de Pedidos (misma que usa el bridge) ──────────────────
try:
    from pedidos_agenda_bridge import CONTROL_PEDIDOS_URL as _CP_URL
except Exception:  # noqa: BLE001 — import circular o bridge no cargado aún
    _CP_URL = "https://proxy.controlpedidosprincess-canarias.workers.dev"

_TIMEOUT = 12


def _log_warning(exc_info=True):
    import traceback as _tb
    print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=sys.stderr)


# ══════════════════════════════════════════════════════════════════════════
#  Usuario de Windows
# ══════════════════════════════════════════════════════════════════════════

def get_windows_user() -> str:
    """Usuario de login: SIEMPRE el usuario de Windows, nunca editable."""
    try:
        u = os.getlogin()
        if u:
            return u.strip().lower()
    except Exception:  # noqa: BLE001 — os.getlogin() falla sin consola/RDP a veces
        pass
    return (os.environ.get("USERNAME") or os.environ.get("USER") or "").strip().lower()


# ══════════════════════════════════════════════════════════════════════════
#  Cifrado local (Fernet) — clave y almacén separados
# ══════════════════════════════════════════════════════════════════════════

def _obtener_clave() -> bytes:
    """Clave Fernet persistida junto al resto de datos de la app.
    Se genera una sola vez por instalación/usuario de Windows."""
    from cryptography.fernet import Fernet
    os.makedirs(_APPDATA_DIR, exist_ok=True)
    if os.path.exists(_KEY_FILE):
        with open(_KEY_FILE, "rb") as f:
            return f.read().strip()
    clave = Fernet.generate_key()
    with open(_KEY_FILE, "wb") as f:
        f.write(clave)
    try:
        # Restringir el acceso al fichero de clave en la medida de lo
        # posible (best-effort: NTFS/Windows no respeta bits POSIX igual
        # que Linux, pero al menos quita lectura/escritura a "otros").
        os.chmod(_KEY_FILE, 0o600)
    except Exception:  # noqa: BLE001
        _log_warning()
    return clave


def _cargar_almacen() -> dict:
    """Descifra y devuelve el almacén completo {username_win: {...}}.
    Si no existe o está corrupto, devuelve un almacén vacío (nunca lanza)."""
    from cryptography.fernet import Fernet, InvalidToken
    if not os.path.exists(_STORE_FILE):
        return {}
    try:
        f = Fernet(_obtener_clave())
        with open(_STORE_FILE, "rb") as fh:
            token = fh.read()
        if not token:
            return {}
        datos = f.decrypt(token)
        return json.loads(datos.decode("utf-8"))
    except (InvalidToken, ValueError, json.JSONDecodeError):
        # Clave/archivo incompatibles (p.ej. reinstalación) — empezar de cero
        # en vez de dejar el login roto para siempre.
        return {}
    except Exception:  # noqa: BLE001
        _log_warning()
        return {}


def _guardar_almacen(datos: dict) -> None:
    from cryptography.fernet import Fernet
    f = Fernet(_obtener_clave())
    payload = json.dumps(datos, ensure_ascii=False).encode("utf-8")
    token = f.encrypt(payload)
    os.makedirs(_APPDATA_DIR, exist_ok=True)
    with open(_STORE_FILE, "wb") as fh:
        fh.write(token)
    try:
        os.chmod(_STORE_FILE, 0o600)
    except Exception:  # noqa: BLE001
        _log_warning()


# ══════════════════════════════════════════════════════════════════════════
#  Hash + salt de contraseña (dentro del almacén ya cifrado — defensa en
#  profundidad: aunque alguien recupere la clave Fernet, la contraseña no
#  queda en texto plano).
# ══════════════════════════════════════════════════════════════════════════

def _hash_password(password: str, salt_b64: str = None) -> tuple[str, str]:
    if salt_b64 is None:
        salt = _secrets.token_bytes(16)
        salt_b64 = base64.b64encode(salt).decode("ascii")
    else:
        salt = base64.b64decode(salt_b64)
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERACIONES
    )
    hash_b64 = base64.b64encode(hash_bytes).decode("ascii")
    return salt_b64, hash_b64


def _verificar_password(password: str, salt_b64: str, hash_b64: str) -> bool:
    _, comprobado = _hash_password(password, salt_b64)
    return _secrets.compare_digest(comprobado, hash_b64)


# ══════════════════════════════════════════════════════════════════════════
#  Registro local (nombre + contraseña con hash+salt)
# ══════════════════════════════════════════════════════════════════════════

def obtener_registro_local(username_win: str) -> dict | None:
    return _cargar_almacen().get(username_win)


def guardar_registro_local(username_win: str, nombre: str, password: str) -> None:
    """Guarda SOLO nombre y contraseña (hash+salt) — nunca en claro."""
    almacen = _cargar_almacen()
    salt_b64, hash_b64 = _hash_password(password)
    entrada = almacen.get(username_win, {})
    entrada.update({
        "nombre":           nombre,
        "salt":             salt_b64,
        "hash":             hash_b64,
        "intentos_fallidos": 0,
        "bloqueado_hasta":   0,
    })
    almacen[username_win] = entrada
    _guardar_almacen(almacen)


# ══════════════════════════════════════════════════════════════════════════
#  Bloqueo temporal tras intentos fallidos
# ══════════════════════════════════════════════════════════════════════════

def esta_bloqueado(username_win: str) -> tuple[bool, int]:
    """Devuelve (bloqueado, segundos_restantes)."""
    reg = obtener_registro_local(username_win)
    if not reg:
        return False, 0
    hasta = reg.get("bloqueado_hasta", 0) or 0
    restante = int(hasta - time.time())
    if restante > 0:
        return True, restante
    return False, 0


def registrar_intento_fallido(username_win: str) -> tuple[int, bool]:
    """Incrementa el contador de intentos fallidos.
    Devuelve (intentos_restantes, bloqueado_ahora)."""
    almacen = _cargar_almacen()
    entrada = almacen.get(username_win, {
        "nombre": "", "salt": "", "hash": "",
        "intentos_fallidos": 0, "bloqueado_hasta": 0,
    })
    entrada["intentos_fallidos"] = int(entrada.get("intentos_fallidos", 0)) + 1
    bloqueado_ahora = False
    if entrada["intentos_fallidos"] >= MAX_INTENTOS:
        entrada["bloqueado_hasta"] = time.time() + BLOQUEO_SEGUNDOS
        entrada["intentos_fallidos"] = 0   # el contador se reinicia tras bloquear
        bloqueado_ahora = True
    almacen[username_win] = entrada
    _guardar_almacen(almacen)
    restantes = max(0, MAX_INTENTOS - entrada["intentos_fallidos"])
    return restantes, bloqueado_ahora


def resetear_intentos(username_win: str) -> None:
    almacen = _cargar_almacen()
    if username_win in almacen:
        almacen[username_win]["intentos_fallidos"] = 0
        almacen[username_win]["bloqueado_hasta"] = 0
        _guardar_almacen(almacen)


# ══════════════════════════════════════════════════════════════════════════
#  Comunicación con Control de Pedidos
# ══════════════════════════════════════════════════════════════════════════

def _request_json(path: str, data: dict = None, method: str = None) -> dict:
    url = _CP_URL.rstrip("/") + path
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(
        url, data=body, method=method,
        headers={
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        },
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def existe_en_plataforma(username_win: str):
    """True/False si se pudo consultar; None si hubo un error de red
    (en ese caso el llamante debe decidir un fallback, p.ej. usar el
    registro local si existe)."""
    try:
        data = _request_json(f"/api/bridge/existe?usuario_windows={username_win}")
        return bool(data.get("existe", False))
    except Exception:  # noqa: BLE001
        _log_warning()
        return None


def validar_en_plataforma(username_win: str, password: str):
    """Valida usuario+contraseña contra Control de Pedidos.
    Devuelve dict {"ok": bool, "nombre": str, "rol": str, "error": str}
    o None si hubo un error de red (no se pudo ni siquiera comprobar)."""
    try:
        body = json.dumps({"username": username_win, "password": password}).encode()
        url = _CP_URL.rstrip("/") + "/api/bridge/login"
        req = urllib.request.Request(
            url, data=body, method="POST",
            headers={
                "Content-Type": "application/json",
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            },
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
            return {"ok": True, "nombre": data.get("nombre", username_win),
                     "rol": data.get("rol", ""), "error": ""}
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"ok": False, "nombre": "", "rol": "", "error": "Usuario o contraseña incorrectos"}
        _log_warning()
        return None
    except Exception:  # noqa: BLE001
        _log_warning()
        return None


def solicitar_alta_directa(username_win: str, nombre: str, apellidos: str,
                            email: str, movil: str, hoteles: str) -> dict:
    """Solicitud de acceso en un solo paso (2026-07-27), contra
    /api/solicitar-usuario/directo — fusiona lo que en la web son fase 1
    (datos personales) y fase 2 (verificación del usuario de Windows),
    ya que el Organizador conoce el usuario de Windows de antemano y no
    necesita el rodeo del .bat/email que sí hace falta desde un
    navegador. La solicitud cae en la misma cola de aprobación del
    panel admin que las solicitudes hechas por la web; el admin sigue
    sin intervenir hasta que la aprueba, momento en el que se genera y
    envía la contraseña — este envío NO crea ningún acceso local ni
    contraseña propia (a diferencia del antiguo registrar_usuario_nuevo).

    Devuelve {"ok": True, "sol_id": int} o
             {"ok": False, "error": "<mensaje>", "ya_existe": bool opcional}
    Si no hay red en absoluto, {"ok": False, "error": "sin_conexion"}.
    """
    body = json.dumps({
        "nombre": nombre, "apellidos": apellidos, "email": email,
        "movil": movil, "hoteles": hoteles, "usuario_windows": username_win,
    }).encode("utf-8")
    url = _CP_URL.rstrip("/") + "/api/solicitar-usuario/directo"
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
            return {"ok": True, "sol_id": data.get("sol_id")}
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode())
            return {"ok": False, "error": data.get("error", f"Error {e.code}"),
                     "ya_existe": data.get("ya_existe", False)}
        except Exception:  # noqa: BLE001
            return {"ok": False, "error": f"Error {e.code} al enviar la solicitud."}
    except Exception as exc:  # noqa: BLE001 — sin red
        _log_warning()
        return {"ok": False, "error": "sin_conexion", "detalle": str(exc)}


def solicitar_alta_plataforma(username_win: str, nombre: str) -> bool:
    """Notifica a Control de Pedidos que hay un usuario nuevo pendiente
    de que un administrador le cree la cuenta. Devuelve True si se pudo
    avisar (no significa que la cuenta ya exista)."""
    try:
        data = _request_json(
            "/api/bridge/solicitar-alta",
            data={"usuario_windows": username_win, "nombre": nombre},
            method="POST",
        )
        return bool(data.get("ok", False))
    except Exception:  # noqa: BLE001
        _log_warning()
        return False


# ══════════════════════════════════════════════════════════════════════════
#  Flujo de alto nivel — lo que llama la ventana de login
# ══════════════════════════════════════════════════════════════════════════

def verificar_acceso(username_win: str, password: str) -> dict:
    """
    Intenta autenticar a `username_win` con `password`.

    Devuelve dict con una de estas formas:
      {"ok": True,  "nombre": str, "modo": "online"|"offline"}
      {"ok": False, "error": str, "bloqueado": bool, "segundos": int,
       "intentos_restantes": int}

    Reglas de bloqueo aplicadas SIEMPRE localmente (independiente de si
    la validación final es online u offline), para que un atacante sin
    red no pueda hacer fuerza bruta ilimitada contra el hash local.
    """
    bloqueado, restante = esta_bloqueado(username_win)
    if bloqueado:
        return {"ok": False, "error": "Demasiados intentos fallidos.",
                 "bloqueado": True, "segundos": restante, "intentos_restantes": 0}

    # ── 1) Comprobación LOCAL primero — evita conexiones innecesarias ──────
    #    (2026-07-27) Antes se intentaba siempre online primero y solo se
    #    caía al hash local si la red fallaba. Ahora, si ya tenemos una
    #    credencial local válida que coincide con lo introducido, la damos
    #    por buena directamente y ni siquiera intentamos conectar — así no
    #    hay que esperar el timeout de red cuando ya sabemos que es correcta
    #    (típico con Control de Pedidos caído varios días).
    #
    #    Dos fuentes locales, en este orden:
    #      a) el propio registro de admin_auth (se creó tras una validación
    #         online exitosa anterior)
    #      b) las credenciales guardadas en "Mi Usuario" (bridge, para los
    #         avisos de Telegram/popup) — el usuario puede haberlas
    #         configurado ahí sin que la validación online del panel Admin
    #         haya llegado nunca a completarse (p. ej. si Control de
    #         Pedidos ya estaba caído la primera vez que se intentó).
    #    Si NINGUNA coincide, seguimos con el intento online normal — no
    #    contamos esto como intento fallido todavía, porque podría ser un
    #    usuario que nunca ha guardado nada local y aún no sabemos si la
    #    contraseña es correcta de verdad.
    reg = obtener_registro_local(username_win)
    if reg and reg.get("hash") and _verificar_password(password, reg["salt"], reg["hash"]):
        resetear_intentos(username_win)
        return {"ok": True, "nombre": reg.get("nombre", username_win), "modo": "offline"}

    bridge_user, bridge_password = get_bridge_credentials(username_win)
    # (v4.16.9) compare_digest sobre bytes: con str lanza TypeError si la contraseña
    # lleva ñ, tildes u otros caracteres no ASCII.
    if bridge_password and _secrets.compare_digest(password.encode('utf-8'), bridge_password.encode('utf-8')):
        resetear_intentos(username_win)
        nombre = get_nombre_usuario() or username_win
        # Aprovechamos para poblar también el registro propio de admin_auth,
        # así las próximas veces se resuelve ya en el primer bloque de arriba.
        guardar_registro_local(username_win, nombre, password)
        return {"ok": True, "nombre": nombre, "modo": "offline"}

    # ── 1-bis) Primera contraseña propia, mientras se aprueba el alta ──────
    # (2026-07-28) Cuando se envía una solicitud de acceso desde
    # "Crear acceso", se deja el usuario de Windows ya guardado como
    # bridge_user en "Mi Usuario", pero SIN contraseña — todavía no hay
    # ninguna real (la pondrá el admin al aprobar). Si alguien en esa
    # situación (bridge_user ya coincide, bridge_password vacío) escribe
    # una contraseña aquí, la tomamos como la que elige para SU equipo
    # mientras espera: se guarda como si fuera la bridge_password de
    # verdad y da acceso local inmediato al panel — pero NO al chat ni a
    # los avisos de Control de Pedidos, que siguen necesitando la
    # contraseña real que llegará por correo al aprobarse la solicitud
    # (esa validación es online, contra el servidor, no contra esto).
    if bridge_user and bridge_user.lower() == username_win.lower() and not bridge_password:
        if len(password) < 4:
            registrar_intento_fallido(username_win)
            return {"ok": False, "error": "Elige una contraseña de al menos 4 caracteres.",
                     "bloqueado": False, "segundos": 0, "intentos_restantes": MAX_INTENTOS}
        resetear_intentos(username_win)
        nombre = get_nombre_usuario() or username_win
        update_bridge_credentials(username_win, bridge_user, password)
        guardar_registro_local(username_win, nombre, password)
        return {"ok": True, "nombre": nombre, "modo": "offline_pendiente_aprobacion"}

    tenia_algo_local = bool(reg and reg.get("hash")) or bool(bridge_password)

    # ── 2) Nada local coincide → intentamos online (fuente de verdad real)
    resultado_online = validar_en_plataforma(username_win, password)

    if resultado_online is not None:
        # Hubo respuesta de la plataforma (positiva o negativa) — es la
        # fuente de verdad.
        if resultado_online["ok"]:
            resetear_intentos(username_win)
            guardar_registro_local(username_win, resultado_online["nombre"], password)
            return {"ok": True, "nombre": resultado_online["nombre"], "modo": "online"}
        else:
            restantes, bloqueado_ahora = registrar_intento_fallido(username_win)
            if bloqueado_ahora:
                return {"ok": False, "error": "Demasiados intentos fallidos. Acceso bloqueado temporalmente.",
                         "bloqueado": True, "segundos": BLOQUEO_SEGUNDOS, "intentos_restantes": 0}
            return {"ok": False, "error": "Usuario o contraseña incorrectos.",
                     "bloqueado": False, "segundos": 0, "intentos_restantes": restantes}

    # ── 3) Sin red y sin coincidencia local ─────────────────────────────────
    if tenia_algo_local:
        # Había algo guardado (registro propio y/o bridge) pero la
        # contraseña introducida no coincidía con ninguno — cuenta como
        # intento fallido real, igual que si hubiéramos podido validar
        # online y el servidor hubiera dicho que no.
        restantes, bloqueado_ahora = registrar_intento_fallido(username_win)
        if bloqueado_ahora:
            return {"ok": False, "error": "Demasiados intentos fallidos. Acceso bloqueado temporalmente.",
                     "bloqueado": True, "segundos": BLOQUEO_SEGUNDOS, "intentos_restantes": 0}
        return {"ok": False, "error": "Usuario o contraseña incorrectos.",
                 "bloqueado": False, "segundos": 0, "intentos_restantes": restantes}

    return {"ok": False,
             "error": "Sin conexión con Control de Pedidos y no hay datos guardados en este equipo.",
             "bloqueado": False, "segundos": 0, "intentos_restantes": MAX_INTENTOS}


def registrar_usuario_nuevo(username_win: str, nombre: str, password: str) -> dict:
    """
    Flujo de alta para un usuario de Windows que todavía no existe en
    Control de Pedidos: guarda localmente (cifrado, hash+salt) y avisa a
    la plataforma para que un administrador cree la cuenta real.

    Devuelve {"ok": True, "notificado": bool} — "ok" es True en cuanto
    el guardado local tiene éxito, independientemente de si el aviso a
    Control de Pedidos llegó (si no llega, el usuario podrá seguir
    accediendo en modo offline con la contraseña que acaba de elegir).
    """
    guardar_registro_local(username_win, nombre, password)
    notificado = solicitar_alta_plataforma(username_win, nombre)
    return {"ok": True, "notificado": notificado}
