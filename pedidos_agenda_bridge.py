"""
pedidos_agenda_bridge.py  ·  v4.9  ·  © VAMA 2026
===================================================
Módulo puente entre "Control de Pedidos" (Flask/Supabase/Render) y
"Organizador Princess" (main_agenda.py / Tkinter).

CAMBIOS v4.9 (2026-08-04) — gracia de 5 min antes de avisar de un corte
----------------------------------------------------------------------------
PETICIÓN: el diálogo "Error de conexión con Control de Pedidos" saltaba
con el primer fallo de red (login, /api/bridge/alertas o
/api/bridge/notificaciones), aunque fuera un corte puntual que se
resuelve solo (wifi, cold start de Render, una petición perdida).

CAMBIO: ningún fallo de conexión muestra el diálogo al momento. La
primera vez que falla cualquiera de las tres operaciones se llama a
_reportar_fallo_conexion(), que NO avisa — programa un único reintento
a los 5 minutos (_GRACIA_RECONEXION_SEGUNDOS) de la MISMA operación que
falló. Si ese reintento tiene éxito, el fallo se descarta en silencio
(solo queda constancia en el log). Si el reintento también falla,
entonces sí se abre el diálogo, con el error de ese segundo intento
(que puede no coincidir con el del primero). Si llegan varios fallos
distintos mientras ya hay un reintento pendiente (p. ej. login y
alertas casi a la vez), no se programa uno por cada uno — todos son
síntoma del mismo corte, así que basta uno.

login() se divide en _intentar_login() (silenciosa, devuelve
(ok, titulo, cuerpo)) + login() (llama a _intentar_login() y, si
falla, delega en _reportar_fallo_conexion()) para poder reutilizar el
mismo intento tanto en la llamada normal como en el reintento
programado a los 5 min. _sincronizar_alertas() y _procesar_push()
siguen el mismo patrón con closures locales (_reintentar_alertas /
_reintentar_push).

El límite de "1 diálogo por tipo y día" de _mostrar_error_bridge()
(v4.3) se mantiene sin cambios — la gracia de 5 min ocurre ANTES de
llegar a ese punto, no lo sustituye.

CAMBIOS v4.8 (PRUEBA 2026-08-04) — dedup de popups movido al servidor
----------------------------------------------------------------------------
PROBLEMA: comprador de INSIRE reportó recibir el mismo popup "continuamente"
en el mismo día. El dedup de v4.4-v4.7 (_estado_popups, con reintento cada
popup_horas_critico/normal) vivía SOLO en memoria de este proceso: si
Organizador Princess se reiniciaba, ese historial se perdía y los avisos
volvían a saltar de golpe; y si el comprador tenía varios pedidos urgentes
acumulados, cada uno repetía cada hora por separado, dando sensación de
repetición constante.

CAMBIO: /api/bridge/alertas (Control de Pedidos v12.29.46+) ya no devuelve
todas las alertas activas — filtra en servidor (tabla bridge_popup_visto,
persistente) y solo manda lo que este usuario AÚN NO ha recibido como
popup. _sincronizar_alertas() se simplifica: cada alerta que llega se
muestra una vez, sin repetición ni reintento en este módulo. Las funciones
_config_repeticion/_debe_mostrar_popup/_registrar_popup_mostrado/
_resetear_al_cambio_de_dia y _estado_popups quedan sin usar (se dejan
definidas por si hay que revertir la prueba). Ver detalle completo en el
docstring de _sincronizar_alertas.

CAMBIOS v4.7 — periodicidad de popups configurable desde Admin
----------------------------------------------------------------------------
PROBLEMA: la cadencia de repetición de popups (1h para "urgente", 1x/día
para "aviso") estaba fija en código (INTERVALO_POPUP_URGENTE/NORMAL) e
igual para todos los tipos de pedido/estado. Cambiarla exigía recompilar y
redistribuir Organizador Princess en los 10 hoteles.

CAMBIOS: Control de Pedidos v12.5+ manda ahora, por cada pedido en alerta,
los campos "popup_repetir" / "popup_horas_critico" / "popup_horas_normal"
(config editable desde Admin → Config Alertas → grupo "Repetición de
Popups en Agenda", con un juego de valores por estado: enviado, firma
compras, firma hotel, entrega parcial, cotización). _debe_mostrar_popup()
y _aviso_para_popup() los leen vía _config_repeticion(), con fallback a
las constantes locales de siempre si el servidor no los manda (compat.
con versiones antiguas de Control de Pedidos). "popup_repetir"=False hace
que el popup se muestre una única vez por pedido.

De paso se corrige un bug preexistente: el reseteo de timer al escalar de
"aviso" a "urgente" comparaba contra nivel=="normal" (valor que nunca se
asigna) en vez de "aviso", así que nunca se disparaba.

CAMBIOS v4.4 — solo popup, sin persistir en agenda.json + arranque no bloqueante
----------------------------------------------------------------------------
PROBLEMA: al arrancar, saltaban varias ventanas que se abrían y cerraban
rápido; los avisos quedaban grabados en agenda.json pero no se veían como
popup. Causa: login()+_sincronizar_alertas()+_procesar_push() se llamaban
de forma síncrona en el hilo principal ANTES de app.mainloop(); si Render
tardaba (cold start), Tkinter se congelaba y al arrancar el mainloop todos
los app.after() pendientes se disparaban casi a la vez, compitiendo por
foco/grab con los popups ya encolados.

CAMBIOS:
  · _sincronizar_alertas y _procesar_push YA NO escriben en agenda.json.
    Solo disparan el popup (mostrar_alerta_fn); el dedup (1/día para
    "aviso", cada hora para "urgente") vive en memoria (_estado_popups,
    _push_procesados). Decisión explícita: se acepta perder un aviso si
    MENU está cerrado en el momento exacto en que llega (ya no hay
    replay al reiniciar — se elimina _replay_avisos_bridge_agenda de v4.2).
  · El login + primera sincronización ya no bloquean el hilo principal:
    se ejecutan dentro del propio hilo t1 (_loop_alertas), que arranca
    inmediatamente como daemon thread sin esperar a que termine.

NOTA: al no grabarse ya en agenda.json, los avisos de pedidos/techo/familia
dejan de aparecer en "Detalle del día" / resumen del saludo diario; siguen
llegando exclusivamente como popup puntual.

CAMBIOS v4.3 — límite de 1 diálogo de error por día
----------------------------------------------------
El sistema anterior suprimía errores "consecutivos" del mismo tipo, pero
_resetear_contador_errores() se llamaba en cada éxito de conexión. Si Render
caía y volvía varias veces en el mismo día, el diálogo reaparecía en cada
nuevo ciclo de fallo. Ahora el dict _errores_mostrados_hoy registra la fecha
(YYYY-MM-DD) en que se mostró cada tipo de error. Si ese tipo ya se notificó
hoy, los siguientes fallos van solo al log, independientemente de si hubo
éxitos intermedios. Al día siguiente vuelve a estar disponible para mostrarse.
_resetear_contador_errores() se mantiene por compatibilidad (no-op).

CAMBIOS v4.2 — replay de avisos bridge al arrancar  [OBSOLETO desde v4.4]
--------------------------------------------------------------------------
NOTA v4.4: este mecanismo se eliminó al dejar de grabar avisos en
agenda.json (ver CAMBIOS v4.4 más arriba). Se conserva el texto por
contexto histórico.

Corrige el caso en que avisos de TECHO URGENTE y FAMILIA REPETIDA
aparecían correctamente en la Agenda pero nunca disparaban popup ni
sonido en sesiones posteriores a la primera.

CAUSA RAÍZ: las notificaciones push (bridge_notificaciones) se marcan
leido=TRUE en BD en cuanto el bridge las recoge. Si MENU estaba cerrado
en ese momento, o se reinicia entre ciclos, los avisos quedan en
agenda.json pero ya no vuelven por el canal push. El monitor_avisos los
ignora (son _bridge_gestionado). Resultado: visible en Agenda, mudo.

SOLUCIÓN — _replay_avisos_bridge_agenda():
  Al arrancar, recorre agenda.json buscando avisos _bridge_gestionado
  con _push=True y fecha de hoy que esta sesión aún no haya mostrado.
  Los relanza como popups (con sonido) en el hilo principal de Tkinter
  vía app_root.after(1200, …), justo después del saludo diario.
  Tipos cubiertos: techo, supervision, familia_repetida_*, y cualquier
  futuro tipo push que lleve "_push": True. Los avisos de pedidos
  activos (sin _push) se excluyen para no duplicar con _sincronizar_alertas.

CAMBIOS v4.1 — diagnóstico de errores de red
----------------------------------------------
Cuando falla la conexión con control-pedidos (login, alertas o push)
se muestra un diálogo de error descriptivo en pantalla (igual que el
sistema de diagnóstico de actualizaciones de GitHub) con:
  · Tipo de error exacto (DNS, timeout, HTTPError, SSL inspection...)
  · Nombre del equipo, URL y endpoint que falló
  · Causa probable en lenguaje comprensible
  · Acción requerida lista para reenviar a informática
  · Botón "Copiar texto" para pegar en correo/ticket
El diálogo se muestra via app_root.after() desde el hilo principal de
Tkinter para no interferir con los hilos daemon del bridge.

CAMBIOS v4.0 — paridad total con Telegram
------------------------------------------
Además del polling periódico de /api/bridge/alertas (avisos que ya
existían en v3), ahora el bridge también consulta la COLA PUSH:

  GET /api/bridge/notificaciones

Cada vez que Control de Pedidos envía un mensaje de Telegram a un
usuario, encola simultáneamente una fila en bridge_notificaciones.
El bridge la recoge en el próximo ciclo y la convierte en un popup
INMEDIATO en main_agenda, garantizando paridad total:

  Telegram recibe → main_agenda recibe  (mismo aviso, mismo usuario)

Tipos de notificaciones push:
  · cambio_estado  → cambio manual de estado de un pedido
  · alerta_auto    → alerta automática diaria del job del scheduler
  · techo          → alerta de techo de gastos mensual
  · supervision    → copia de supervisión a admins (alertas urgentes)

POLLING vs PUSH
---------------
  · /api/bridge/alertas       → polling cada 15 min
    Mantiene los avisos en agenda.json sincronizados con el estado
    actual de los pedidos (alta, resolución, escalada urgente).

  · /api/bridge/notificaciones → polling cada 1 min
    Recoge eventos push (cambios de estado, techo, supervision).
    Se procesan como popup inmediato. No se graban en agenda.json
    (para no duplicar con los avisos periódicos), salvo que el
    pedido no esté ya registrado.

CONFIGURACIÓN
-------------
El usuario y contraseña se configuran en main_agenda →
  Panel Admin → "Mi Usuario" → sección "Control de Pedidos".
Deben coincidir exactamente con los de Control de Pedidos.
Los avisos llegan SOLO al usuario que corresponde, igual que Telegram.
"""

import threading
import time
import json
import logging
import http.cookiejar
import urllib.request
import urllib.error
import socket
import os
from datetime import date, datetime

log = logging.getLogger("pedidos_bridge")

# ──────────────────────────────────────────────────────────────────────────────
# HANDLER DE FICHERO PROPIO PARA EL LOGGER DEL BRIDGE
# ──────────────────────────────────────────────────────────────────────────────
# ANTI-REGRESION (bug detectado 2026-07-13): antes de este cambio, el logger
# "pedidos_bridge" NUNCA tenía un handler adjunto salvo cuando este archivo se
# ejecutaba directamente (`if __name__ == "__main__": logging.basicConfig(...)`
# más abajo). Al ser importado desde main_agenda.py (el caso real en producción)
# ese basicConfig no se ejecutaba nunca, así que TODAS las líneas log.info/
# warning/error de este módulo — incluida la que confirma que un popup de
# Telegram se está a punto de mostrar ("Bridge push: popup inmediato → ...")
# y cualquier excepción atrapada en los bucles _loop_alertas/_loop_push —
# se enviaban a un logger sin destino. Con PyInstaller en modo console=False
# no hay stderr visible, así que esos mensajes se perdían sin dejar rastro:
# imposible diagnosticar si el bridge llegaba a llamar a mostrar_alerta_fn().
# Se adjunta aquí un RotatingFileHandler propio (mismo patrón que
# negocio/alertas.py usa para monitor_avisos.log) para que quede constancia
# en disco de cada ciclo de sincronización, cada push procesado y cualquier
# fallo, sin tener que tocar ninguna línea log.xxx(...) ya existente.
def _init_bridge_file_logger() -> None:
    try:
        from logging.handlers import RotatingFileHandler
        _appdata  = os.environ.get("APPDATA", os.path.expanduser("~"))
        _log_dir  = os.path.join(_appdata, "OrganizadorPrincess")
        os.makedirs(_log_dir, exist_ok=True)
        _log_path = os.path.join(_log_dir, "pedidos_bridge.log")
        if not log.handlers:   # evitar duplicar handlers en reimports
            _h = RotatingFileHandler(
                _log_path, maxBytes=200_000, backupCount=1, encoding="utf-8"
            )
            _h.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            ))
            log.addHandler(_h)
            log.setLevel(logging.DEBUG)
            log.propagate = False  # no duplicar en el root logger / stderr
    except Exception:  # noqa: BLE001 — nunca romper el arranque del bridge por un fallo de logging
        pass

_init_bridge_file_logger()

# ──────────────────────────────────────────────────────────────────────────────
# SHUTDOWN  — se activa cuando la app principal cierra la ventana.
# Todos los hilos del bridge comprueban este flag antes de mostrar popups
# para evitar ventanas ciegas/vacías tras app.destroy().
# Llamar a  detener_bridge()  desde el on_closing / WM_DELETE_WINDOW.
# ──────────────────────────────────────────────────────────────────────────────
_shutdown = threading.Event()


def detener_bridge():
    """Señaliza el cierre de la app. Llamar ANTES de app.destroy()."""
    _shutdown.set()
    log.info("Bridge: shutdown señalizado — popups desactivados.")




# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN  ← NO tocar aquí: se gestiona desde Admin → Mi Usuario
# ──────────────────────────────────────────────────────────────────────────────

CONTROL_PEDIDOS_URL = "https://proxy.controlpedidosprincess-canarias.workers.dev"

BRIDGE_USER     = ""
BRIDGE_PASSWORD = ""

# ──────────────────────────────────────────────────────────────────────────────
# LOG DE DIAGNÓSTICO
# ──────────────────────────────────────────────────────────────────────────────
_appdata   = os.environ.get("APPDATA", os.path.expanduser("~"))
_log_path  = os.path.join(_appdata, "OrganizadorPrincess", "bridge_errors.log")

def _blog(msg: str):
    """Escribe una línea en bridge_errors.log con timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        os.makedirs(os.path.dirname(_log_path), exist_ok=True)
        with open(_log_path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:  # noqa: BLE001
        import sys as _sys, traceback as _tb
        print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)

# ──────────────────────────────────────────────────────────────────────────────
# DIÁLOGO DE ERROR DE RED  (se invoca desde el hilo principal vía app_root.after)
# ──────────────────────────────────────────────────────────────────────────────

# Referencia al app_root de Tkinter — se inyecta en iniciar_bridge_pedidos
_app_root = None

# Límite de diálogos de error: como máximo 1 por tipo de error por día.
# Clave: titulo[:60]  →  fecha ISO "YYYY-MM-DD" en que se mostró por última vez.
# Un éxito de conexión NO resetea este dict: si el servidor cae y vuelve varias
# veces en el mismo día, el diálogo solo se muestra la primera vez.
_errores_mostrados_hoy: dict = {}   # {tipo_clave: "YYYY-MM-DD"}


def _mostrar_error_bridge(titulo: str, cuerpo: str):
    """
    Programa la apertura del diálogo de error en el hilo principal de Tkinter.
    Muestra como máximo UN diálogo por tipo de error por día, independientemente
    de cuántas veces falle la conexión o de si hay éxitos intermedios.
    Los fallos adicionales del mismo día solo van al log.
    """

    _blog(f"ERROR: {titulo}\n{cuerpo}\n{'─'*60}")

    # No abrir diálogos si la app ya está cerrándose
    if _shutdown.is_set():
        return

    tipo_clave = titulo[:60]
    hoy = date.today().isoformat()

    if _errores_mostrados_hoy.get(tipo_clave) == hoy:
        log.warning("Bridge: error ya notificado hoy, suprimido. Ver %s", _log_path)
        return

    _errores_mostrados_hoy[tipo_clave] = hoy

    if _app_root is None:
        return

    try:
        import ttkbootstrap as ttk
        import tkinter as _tk

        def _dlg():
            try:
                dlg = ttk.Toplevel(_app_root)
                dlg.withdraw()
                dlg.title(titulo)
                dlg.resizable(False, False)
                dlg.attributes("-topmost", True)

                # Intentar aplicar el mismo icono que la app principal.
                # (v4.18.06) Se toma de ui.assets, que es donde vive: con
                # «from main_agenda import ...» Python volvía a ejecutar
                # main_agenda.py entero (es el script de arranque, registrado
                # como __main__), con una segunda ventana, un segundo bridge
                # y un mainloop anidado.
                try:
                    from ui.assets import _apply_icon
                    _apply_icon(dlg)
                except Exception:
                    pass  # UI — ignorar silenciosamente

                dlg.transient(_app_root)

                # Cabecera naranja (advertencia de conectividad, no fallo crítico)
                hdr = ttk.Frame(dlg, bootstyle="warning")
                hdr.pack(fill="x")
                _hi = ttk.Frame(hdr, bootstyle="warning")
                _hi.pack(fill="x", padx=16, pady=10)
                ttk.Label(
                    _hi,
                    text="⚠️  Error de conexión con Control de Pedidos",
                    font=("Segoe UI", 11, "bold"),
                    bootstyle="inverse-warning",
                ).pack(anchor="w")
                ttk.Label(
                    _hi,
                    text="No se han podido recuperar las alertas. Las notificaciones quedan suspendidas hasta restablecer la conexión.",
                    font=("Segoe UI", 8),
                    bootstyle="inverse-warning",
                    wraplength=520,
                ).pack(anchor="w", pady=(2, 0))

                ttk.Separator(dlg).pack(fill="x")

                body = ttk.Frame(dlg, padding=(18, 12, 18, 4))
                body.pack(fill="both", expand=True)

                ttk.Label(
                    body,
                    text="📋  Detalle técnico para el servicio informático:",
                    font=("Segoe UI", 9, "bold"),
                ).pack(anchor="w", pady=(0, 6))

                frm_txt = ttk.Frame(body)
                frm_txt.pack(fill="both", expand=True)
                txt = _tk.Text(
                    frm_txt,
                    height=12, width=72,
                    font=("Consolas", 8),
                    wrap="word",
                    relief="flat",
                    state="normal",
                    background="#1e1e2e",
                    foreground="#ffe8a1",
                    padx=10, pady=8,
                )
                txt.insert("1.0", cuerpo)
                txt.configure(state="disabled")
                txt.pack(fill="both", expand=True)

                ttk.Separator(dlg).pack(fill="x", pady=(10, 0))
                nota = ttk.Frame(dlg, padding=(18, 8, 18, 4))
                nota.pack(fill="x")
                ttk.Label(
                    nota,
                    text=(
                        "ℹ️  Los avisos de pedidos se reanudarán automáticamente en el siguiente ciclo\n"
                        "de comprobación cuando se restaure la conectividad.\n"
                        f"Log completo en:  {_log_path}"
                    ),
                    font=("Segoe UI", 8),
                    foreground="#adb5bd",
                    justify="left",
                ).pack(anchor="w")

                ttk.Separator(dlg).pack(fill="x", pady=(8, 0))
                btns = ttk.Frame(dlg, padding=(18, 8, 18, 12))
                btns.pack(fill="x")

                def _copiar():
                    dlg.clipboard_clear()
                    dlg.clipboard_append(cuerpo)
                    btn_copiar.configure(text="✅  Copiado")

                btn_copiar = ttk.Button(btns, text="📋  Copiar texto",
                                        bootstyle="secondary", command=_copiar)
                btn_cerrar = ttk.Button(btns, text="Cerrar",
                                        bootstyle="warning-outline", command=dlg.destroy)
                btn_copiar.pack(side="left", padx=(0, 8))
                btn_cerrar.pack(side="left")

                dlg.update_idletasks()
                _w = 580
                _h = max(dlg.winfo_reqheight(), 420)
                _sw = dlg.winfo_screenwidth()
                _sh = dlg.winfo_screenheight()
                dlg.geometry(f"{_w}x{_h}+{(_sw - _w) // 2}+{max(40, (_sh - _h) // 2)}")
                dlg.deiconify()
                dlg.lift()
                dlg.focus_force()

                # Auto-cierre (2026-07-27): si nadie la cierra, no tiene
                # sentido dejar este aviso abierto para siempre — mismo
                # criterio que la ventana de "Nueva versión disponible"
                # (ver update_service.py), pero a los 2 minutos en vez de 5,
                # porque aquí no hay ninguna acción en curso que se pueda
                # interrumpir (solo "Cerrar" / "Copiar texto").
                def _autocierre_error_bridge():
                    if dlg.winfo_exists():
                        dlg.destroy()

                dlg.after(2 * 60 * 1000, _autocierre_error_bridge)

            except Exception as exc_dlg:
                log.error("Bridge: no se pudo mostrar diálogo de error — %s", exc_dlg)

        _app_root.after(0, _dlg)

    except Exception as exc_outer:
        log.error("Bridge: fallo al programar diálogo — %s", exc_outer)


def _resetear_contador_errores():
    """Compatibilidad: ya no resetea nada. El límite es 1 diálogo/día por tipo,
    independientemente de los éxitos de conexión intermedios."""


# ──────────────────────────────────────────────────────────────────────────────
# GRACIA DE RECONEXIÓN — no avisar al primer fallo, reintentar a los 5 min
# ──────────────────────────────────────────────────────────────────────────────
# PETICIÓN (2026-08-04): el diálogo de error saltaba con el primer fallo de
# conexión, aunque fuera algo puntual (un corte de wifi de un segundo, un
# cold start de Render, una petición perdida) que se resuelve solo. Ahora
# el primer fallo NO muestra el diálogo: se concede una gracia de 5 minutos
# y se reintenta UNA vez la misma operación que falló. Si ese reintento
# también falla, entonces sí se abre el diálogo (con el error del
# reintento, que puede ser distinto al del primer fallo). Si el reintento
# tiene éxito, el fallo se descarta en silencio — no se avisa a nadie.
#
# _gracia_en_curso evita programar varios reintentos en paralelo si llegan
# varios fallos (de login, alertas o push) mientras ya hay uno pendiente de
# confirmar: todos son síntoma del mismo corte de conexión, así que basta
# con un único reintento a los 5 minutos.
_GRACIA_RECONEXION_SEGUNDOS = 5 * 60

_gracia_en_curso = False
_gracia_lock     = threading.Lock()


def _reportar_fallo_conexion(titulo: str, cuerpo: str, reintento_fn):
    """
    Punto único de entrada para cualquier fallo de conexión con Control de
    Pedidos (login, alertas, push). En vez de avisar al momento, concede
    _GRACIA_RECONEXION_SEGUNDOS antes de comprobar si el fallo persiste.

    reintento_fn: función sin argumentos que repite la operación que
    falló y devuelve (ok: bool, titulo: str, cuerpo: str). Se ejecuta en
    un hilo daemon aparte a los 5 minutos, nunca en el hilo que detectó
    el primer fallo.
    """
    global _gracia_en_curso

    _blog(f"Fallo de conexión detectado — {titulo}. Gracia de "
          f"{_GRACIA_RECONEXION_SEGUNDOS // 60} min antes de avisar (sin mostrar diálogo).")
    log.warning("Bridge: fallo de conexión (%s) — comprobando de nuevo en %ds antes de avisar",
                titulo, _GRACIA_RECONEXION_SEGUNDOS)

    with _gracia_lock:
        if _gracia_en_curso:
            log.info("Bridge: ya hay una comprobación de reconexión en curso — no se programa otra")
            return
        _gracia_en_curso = True

    def _confirmar_fallo():
        global _gracia_en_curso
        try:
            if _shutdown.is_set():
                return
            ok, titulo2, cuerpo2 = reintento_fn()
            if ok:
                log.info("Bridge: conexión recuperada durante la gracia — aviso suprimido (%s)", titulo)
                _blog(f"Conexión recuperada tras {_GRACIA_RECONEXION_SEGUNDOS // 60} min de gracia "
                      f"— no se muestra el aviso ({titulo}).")
            else:
                log.warning("Bridge: la conexión sigue caída tras la gracia — mostrando diálogo de error")
                _mostrar_error_bridge(titulo2 or titulo, cuerpo2 or cuerpo)
        except Exception as exc_confirmar:
            # Si el propio reintento revienta por algo inesperado, no nos
            # quedamos callados: mostramos el error original en vez de
            # perder el aviso por completo.
            log.error("Bridge: error inesperado confirmando el fallo de conexión — %s", exc_confirmar)
            _mostrar_error_bridge(titulo, cuerpo)
        finally:
            with _gracia_lock:
                _gracia_en_curso = False

    _timer = threading.Timer(_GRACIA_RECONEXION_SEGUNDOS, _confirmar_fallo)
    _timer.daemon = True
    _timer.start()


# ──────────────────────────────────────────────────────────────────────────────
# ANÁLISIS DE ERRORES DE RED → texto descriptivo
# ──────────────────────────────────────────────────────────────────────────────

def _analizar_error_red(exc, endpoint: str, dns_ip: str = "", dns_ok: bool = True) -> tuple:
    """
    Devuelve (titulo, cuerpo) con diagnóstico legible según el tipo de excepción.
    """
    host = CONTROL_PEDIDOS_URL.replace("https://", "").replace("http://", "").split("/")[0]
    equipo = socket.gethostname()
    url_completa = CONTROL_PEDIDOS_URL.rstrip("/") + endpoint
    dns_info = f"DNS ok — {host} → {dns_ip}" if dns_ok and dns_ip else (
        f"DNS FALLO — {host} no resuelto" if not dns_ok else "DNS no comprobado"
    )

    if isinstance(exc, urllib.error.HTTPError):
        titulo = f"Error de conexión con Control de Pedidos — HTTP {exc.code}"
        if exc.code == 401:
            causa = (
                "Credenciales incorrectas o sesión expirada.\n"
                "El servidor ha rechazado el usuario/contraseña configurados en\n"
                "Organizador Princess → Admin → Mi Usuario → Control de Pedidos."
            )
            accion = (
                "  · Verificar que el usuario y contraseña en 'Mi Usuario' son correctos.\n"
                "  · Confirmar que la cuenta existe y está activa en Control de Pedidos."
            )
        elif exc.code == 403:
            causa = (
                "Acceso prohibido. El proxy o firewall corporativo puede estar\n"
                "bloqueando las peticiones a este dominio."
            )
            accion = (
                f"  · Permitir acceso HTTPS (puerto 443) a:\n"
                f"      {host}\n"
                "  · Si hay proxy, añadir excepción para el dominio anterior."
            )
        elif exc.code == 429:
            causa = "Demasiadas peticiones en poco tiempo (rate-limit del servidor)."
            accion = "  · El bridge reintentará automáticamente en el siguiente ciclo."
        elif exc.code >= 500:
            causa = (
                f"El servidor de Control de Pedidos devolvió un error interno (HTTP {exc.code}).\n"
                "Puede estar reiniciando (Render Free Tier) o haber caído temporalmente."
            )
            accion = (
                "  · Esperar unos minutos; el bridge reintentará automáticamente.\n"
                "  · Si persiste, revisar el estado del servicio en Render."
            )
        else:
            causa = f"El servidor respondió con HTTP {exc.code} {exc.reason}."
            accion = "  · Revisar logs del servidor de Control de Pedidos."

        cuerpo = (
            f"TIPO DE ERROR : HTTP {exc.code} {exc.reason}\n"
            f"\n"
            f"Aplicación    : MENU — Organizador Princess\n"
            f"Equipo        : {equipo}\n"
            f"Endpoint      : {url_completa}\n"
            f"DNS           : {dns_info}\n"
            f"\n"
            f"POSIBLE CAUSA:\n"
            f"  {causa}\n"
            f"\n"
            f"ACCIÓN REQUERIDA:\n"
            f"{accion}\n"
            f"\n"
            f"Log guardado en:\n  {_log_path}"
        )

    elif isinstance(exc, urllib.error.URLError):
        razon = str(exc.reason)
        titulo = "Error de conexión con Control de Pedidos — Sin conexión"

        if not dns_ok:
            causa = (
                f"El equipo no puede resolver el nombre '{host}'.\n"
                "El DNS corporativo puede estar bloqueando dominios externos\n"
                "o no hay salida a Internet desde este equipo."
            )
            accion = (
                "  · Verificar que el DNS permite resolver dominios externos.\n"
                "  · Comprobar que el equipo tiene salida a Internet."
            )
        elif "SSL" in razon or "certificate" in razon.lower():
            causa = (
                "El proxy o firewall corporativo está interceptando la conexión\n"
                "HTTPS (SSL inspection) y el certificado no es de confianza."
            )
            accion = (
                f"  · Añadir excepción de inspección SSL para: {host}\n"
                "  · O instalar el certificado raíz del proxy en el equipo."
            )
        elif "timed out" in razon.lower() or "timeout" in razon.lower():
            causa = (
                f"La conexión a {host} se ha agotado (timeout).\n"
                "El firewall puede estar descartando silenciosamente los paquetes."
            )
            accion = (
                f"  · Permitir tráfico HTTPS saliente (puerto 443 TCP) a:\n"
                f"      {host}  ({dns_ip or 'sin IP resuelta'})\n"
                "  · Revisar reglas de firewall perimetral."
            )
        else:
            causa = f"No se pudo establecer conexión.\nDetalle: {razon}"
            accion = (
                f"  · Permitir acceso HTTPS (puerto 443) a {host}\n"
                "  · Comprobar proxy / firewall corporativo."
            )

        cuerpo = (
            f"TIPO DE ERROR : URLError — {razon}\n"
            f"\n"
            f"Aplicación    : MENU — Organizador Princess\n"
            f"Equipo        : {equipo}\n"
            f"Endpoint      : {url_completa}\n"
            f"DNS           : {dns_info}\n"
            f"\n"
            f"POSIBLE CAUSA:\n"
            f"  {causa}\n"
            f"\n"
            f"ACCIÓN REQUERIDA:\n"
            f"{accion}\n"
            f"\n"
            f"Log guardado en:\n  {_log_path}"
        )

    else:
        titulo = f"Error de conexión con Control de Pedidos — {type(exc).__name__}"
        cuerpo = (
            f"TIPO DE ERROR : {type(exc).__name__} — {exc}\n"
            f"\n"
            f"Aplicación    : MENU — Organizador Princess\n"
            f"Equipo        : {equipo}\n"
            f"Endpoint      : {url_completa}\n"
            f"DNS           : {dns_info}\n"
            f"\n"
            f"POSIBLE CAUSA : Error inesperado durante la conexión con Control de Pedidos.\n"
            f"\n"
            f"Log guardado en:\n  {_log_path}"
        )

    return titulo, cuerpo


def _dns_check() -> tuple:
    """Comprueba resolución DNS del host de control_pedidos. Devuelve (ip, ok)."""
    host = CONTROL_PEDIDOS_URL.replace("https://", "").replace("http://", "").split("/")[0]
    try:
        ip = socket.gethostbyname(host)
        return ip, True
    except Exception:
        return "", False


# ──────────────────────────────────────────────────────────────────────────────

def _cargar_credenciales_desde_db():
    global BRIDGE_USER, BRIDGE_PASSWORD
    if BRIDGE_USER and BRIDGE_PASSWORD:
        return
    try:
        # (v4.16.9) Pasa por get_bridge_credentials(): la contraseña está
        # cifrada con DPAPI y ese es el único sitio que la descifra.
        from db.sqlite import get_bridge_credentials
        uwin = os.getenv("USERNAME", "").lower()
        row = get_bridge_credentials(uwin)
        if row and row[0]:
            BRIDGE_USER     = row[0]
            BRIDGE_PASSWORD = row[1] or ""
            log.info("Bridge: credenciales cargadas desde DB para '%s'", uwin)
        else:
            log.warning(
                "Bridge: sin credenciales en DB para '%s'. "
                "Configurar en Admin -> Mi Usuario.", uwin
            )
    except Exception as exc:
        log.warning("Bridge: no se pudo leer credenciales desde DB -- %s", exc)


# Polling periódico de alertas activas (agenda.json)
INTERVALO_ALERTAS_MINUTOS = 15

# Polling de notificaciones push (cola inmediata)
INTERVALO_PUSH_SEGUNDOS = 15   # cada 15 segundos

# Intervalo de repetición del popup según nivel (en horas).
# CAMBIOS v4.7: estos valores ahora son solo el FALLBACK usado cuando
# Control de Pedidos no informa "popup_horas_critico"/"popup_horas_normal"
# en la alerta (servidor antiguo, o pedido de un estado sin prefijo
# reconocido). Con servidor v12.5+, la periodicidad real se regula por
# tipo de estado desde Admin → Config Alertas → grupo "Repetición de
# Popups en Agenda". Ver _config_repeticion().
INTERVALO_POPUP_URGENTE = 1    # 🚨 cada 1 hora (fallback)
INTERVALO_POPUP_NORMAL  = 24   # ⚠️ una vez al día (fallback)


def _version_organizador() -> str:
    """(v4.18.52) La versión instalada, que main_agenda deja en services.update_service.APP_VERSION. Se lee
    aquí, al hacer cada petición, porque este módulo nunca puede importar main_agenda."""
    try:
        import services.update_service as _update
        return str(getattr(_update, "APP_VERSION", "") or "")
    except Exception:  # noqa: BLE001
        return ""


def _navegadores_vinculados() -> str:
    """(v4.18.60) Códigos de los navegadores de este PC vinculados (services/vinculo_navegador.py)."""
    try:
        import services.vinculo_navegador as _vinculo
        return _vinculo.cabecera()
    except Exception:  # noqa: BLE001
        return ""


class _Session:
    """Gestiona login/cookie contra la API de Control de Pedidos."""

    def __init__(self):
        self._jar       = http.cookiejar.CookieJar()
        self._opener    = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._jar)
        )
        self._logged_in = False
        self.username   = ""
        self.nombre     = ""
        self.rol        = ""

    def _request(self, path, data=None, method=None, timeout=20):
        url = CONTROL_PEDIDOS_URL.rstrip("/") + path
        req = urllib.request.Request(
            url, data=data,
            headers={
                "Content-Type": "application/json",
                # Cloudflare bloquea con 403 el User-Agent por defecto de
                # urllib ("Python-urllib/3.x") al considerarlo tráfico de
                # bot. Con un User-Agent de navegador real la petición pasa
                # sin problema (mismo Worker que usa el navegador).
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                # (v4.18.52) Con cada consulta, Control Pedidos anota que el Organizador de esta persona
                # está abierto y con qué versión: así no le sale el aviso «abre o instala el
                # Organizador» y en Usuarios se ve quién está actualizado (Control Pedidos v12.34.26).
                "X-Organizador-Version": _version_organizador(),
                # (v4.18.60) Navegadores de este PC vinculados con «Abrir el Organizador» de Control
                # Pedidos: así sabe si el Organizador está abierto en el mismo equipo (v12.34.32).
                "X-Organizador-Navegadores": _navegadores_vinculados(),
            },
            method=method,
        )
        with self._opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())

    def login(self):
        """
        Login con gracia de reconexión: si falla, NO avisa al momento —
        programa un reintento a los 5 min vía _reportar_fallo_conexion()
        y solo avisa si ese reintento también falla. La lógica real del
        intento (sin avisar de nada) vive en _intentar_login(), que
        también usa el reintento programado, para que el diálogo final
        refleje el error real de ese segundo intento.
        """
        endpoint = "/api/bridge/login"
        ok, titulo, cuerpo = self._intentar_login(endpoint)
        if not ok:
            self._logged_in = False
            _reportar_fallo_conexion(titulo, cuerpo, lambda: self._intentar_login(endpoint))
        return ok

    def _intentar_login(self, endpoint: str):
        """
        Intento de login "silencioso": nunca abre el diálogo de error, solo
        devuelve (ok, titulo, cuerpo) para que el llamante decida cuándo
        avisar (inmediatamente la primera vez que se usa como reintento
        programado, o a través de la gracia de 5 min en login()).
        """
        # Usa /api/bridge/login (no /api/login): es una cuenta de servicio
        # que se reconecta sola en segundo plano, así que se salta a
        # propósito el paso de verificación por email tras varios días de
        # inactividad que sí aplica al login normal desde el navegador
        # (nadie va a estar delante para introducir ese código). Las
        # credenciales que valida son exactamente las mismas.
        dns_ip, dns_ok = _dns_check()
        try:
            body = json.dumps({
                "username": BRIDGE_USER,
                "password": BRIDGE_PASSWORD,
            }).encode()
            data = self._request(endpoint, data=body, method="POST")
            self._logged_in = data.get("ok", False)
            if self._logged_in:
                self.username = data.get("username", BRIDGE_USER)
                self.nombre   = data.get("nombre", BRIDGE_USER)
                self.rol      = data.get("rol", "")
                # (v4.18.58) El saludo usa el nombre de Control de Pedidos si este equipo no tiene uno propio.
                try:
                    from db.sqlite import guardar_nombre_si_falta
                    guardar_nombre_si_falta(None, data.get("nombre"))
                except Exception:  # noqa: BLE001
                    pass
                log.info("Bridge: sesión iniciada como '%s' (rol=%s)", self.username, self.rol)
                _resetear_contador_errores()
                return True, "", ""
            else:
                # Login fallido con respuesta 200 → credenciales incorrectas
                err_msg = data.get("error", "credenciales incorrectas")
                log.warning("Bridge: login fallido — %s", err_msg)
                # Simulamos un HTTPError 401 para reutilizar el analizador
                fake = urllib.error.HTTPError(endpoint, 401, err_msg, {}, None)
                titulo, cuerpo = _analizar_error_red(fake, endpoint, dns_ip, dns_ok)
                return False, titulo, cuerpo
        except (urllib.error.HTTPError, urllib.error.URLError, Exception) as exc:
            log.warning("Bridge: error en login — %s", exc)
            self._logged_in = False
            titulo, cuerpo = _analizar_error_red(exc, endpoint, dns_ip, dns_ok)
            return False, titulo, cuerpo

    def _get(self, path):
        """GET autenticado con reintento de login automático en 401."""
        try:
            result = self._request(path)
            _resetear_contador_errores()
            return result
        except urllib.error.HTTPError as e:
            if e.code == 401:
                log.info("Bridge: sesión expirada, reintentando login...")
                if self.login():
                    return self._request(path)
            raise

    def get_alertas_usuario(self):
        """GET /api/bridge/alertas — estado actual de pedidos del usuario."""
        return self._get("/api/bridge/alertas")

    def get_notificaciones_push(self):
        """GET /api/bridge/notificaciones — cola push de eventos inmediatos."""
        return self._get("/api/bridge/notificaciones")

    def _post(self, path, payload):
        """POST autenticado (JSON) con reintento de login automático en 401."""
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        try:
            result = self._request(path, data=body, method="POST")
            _resetear_contador_errores()
            return result
        except urllib.error.HTTPError as e:
            if e.code == 401:
                log.info("Bridge: sesión expirada, reintentando login...")
                if self.login():
                    return self._request(path, data=body, method="POST")
            raise

    def get_agenda(self, desde=0):
        """(v4.18.66) GET /api/bridge/agenda — la agenda de este usuario cambiada desde la versión `desde`."""
        return self._get(f"/api/bridge/agenda?desde={int(desde)}")

    def post_agenda(self, elementos):
        """(v4.18.66) POST /api/bridge/agenda — sube los cambios de la agenda de este usuario."""
        return self._post("/api/bridge/agenda", {"elementos": elementos})


_session = _Session()

_bridge_listo = threading.Event()

_resumen_alertas: dict = {"total": 0, "urgentes": 0, "normales": 0}
MAX_ESPERA_SALUDO = 8


def get_resumen_alertas() -> dict:
    _bridge_listo.wait(timeout=MAX_ESPERA_SALUDO)
    return dict(_resumen_alertas)


_estado_popups: dict  = {}
_push_procesados: set = set()

# (v4.18.04) Lo que Control de Pedidos manda MIENTRAS el Organizador está
# cerrado se pierde. Petición de Víctor: «todo aquello que llega desde
# Control de Pedidos si main_agenda está cerrada se pierde»; al abrir solo
# deben verse los avisos que el usuario programó en el calendario, sus
# eventos y las vacaciones y festivos. Control de Pedidos entrega y marca
# como entregado lo pendiente en la primera consulta con sesión (alertas y
# notificaciones inmediatas): esa primera respuesta es la acumulada con la
# app cerrada, así que se consulta (para que no vuelva a llegar) pero NO se
# muestra. Lo que ocurra desde entonces se muestra con normalidad.
_descartar_alertas_acumuladas: bool = True
_descartar_push_acumulado: bool = True


def _hoy_str() -> str:
    return date.today().strftime("%Y-%m-%d")


# ── v4.8 (PRUEBA 2026-08-04): dedup movido al servidor ───────────────────────
# Las 4 funciones siguientes (_config_repeticion, _debe_mostrar_popup,
# _registrar_popup_mostrado, _resetear_al_cambio_de_dia) y el dict
# _estado_popups ya NO se usan desde _sincronizar_alertas — el filtrado
# de qué popup mostrar vive ahora en Control de Pedidos (tabla
# bridge_popup_visto, ver _filtrar_popups_no_vistos en app.py). Se
# dejan definidas sin borrar por si hay que revertir la prueba.

def _config_repeticion(alerta: dict, nivel: str) -> tuple:
    """
    Extrae la config de repetición de popup para una alerta concreta, tal
    como la envía Control de Pedidos (editable desde Admin → Config Alertas,
    grupo "popup_repeticion") en cada pedido de /api/bridge/alertas:

        popup_repetir        (bool) — si False, se muestra 1 sola vez
        popup_horas_critico   (int) — horas de repetición si nivel="urgente"
        popup_horas_normal    (int) — horas de repetición si nivel="aviso"

    Si el servidor todavía no manda estos campos (versión antigua de
    Control de Pedidos), se cae a las constantes locales de siempre
    (INTERVALO_POPUP_URGENTE / INTERVALO_POPUP_NORMAL) para no romper nada.

    Devuelve (repetir: bool, horas: float).
    """
    repetir = alerta.get("popup_repetir")
    repetir = True if repetir is None else bool(repetir)

    if nivel == "urgente":
        horas = alerta.get("popup_horas_critico")
    else:
        horas = alerta.get("popup_horas_normal")

    if horas is None:
        horas = INTERVALO_POPUP_URGENTE if nivel == "urgente" else INTERVALO_POPUP_NORMAL
    try:
        horas = float(horas)
        if horas <= 0:
            horas = INTERVALO_POPUP_URGENTE if nivel == "urgente" else INTERVALO_POPUP_NORMAL
    except (TypeError, ValueError):
        horas = INTERVALO_POPUP_URGENTE if nivel == "urgente" else INTERVALO_POPUP_NORMAL

    return repetir, horas


def _debe_mostrar_popup(pid, nivel: str, alerta: dict = None) -> bool:
    """
    Decide si toca (re)mostrar el popup de un pedido.

    CAMBIOS v4.7 — periodicidad configurable desde Admin (Control de Pedidos)
    --------------------------------------------------------------------------
    Antes el intervalo de repetición era fijo por nivel (1h urgente / 1x
    día aviso, vía INTERVALO_POPUP_URGENTE/NORMAL). Ahora, si la alerta trae
    "popup_repetir"/"popup_horas_critico"/"popup_horas_normal" (Control de
    Pedidos v12.5+), se usa ese valor por tipo de estado, permitiendo que
    cada comprador/admin regule la cadencia desde el panel Admin sin tocar
    código ni recompilar Organizador Princess. Si "popup_repetir" es False,
    el popup se muestra una única vez y no vuelve a saltar para ese pedido
    (hasta que cambie de estado y desaparezca/reaparezca en la lista).
    """
    alerta = alerta or {}
    estado = _estado_popups.get(pid)
    repetir, horas = _config_repeticion(alerta, nivel)

    if estado is None or estado.get("dt_ultimo") is None:
        return True
    if not repetir:
        return False

    elapsed_h = (datetime.now() - estado["dt_ultimo"]).total_seconds() / 3600
    return elapsed_h >= horas


def _registrar_popup_mostrado(pid, nivel: str):
    ahora = datetime.now()
    if pid not in _estado_popups:
        _estado_popups[pid] = {}
    _estado_popups[pid]["nivel"]         = nivel
    _estado_popups[pid]["dt_ultimo"]     = ahora
    _estado_popups[pid]["disparado_hoy"] = True


def _resetear_al_cambio_de_dia():
    # CAMBIOS v4.7: ya no hace falta resetear "disparado_hoy" al cambiar de
    # día — _debe_mostrar_popup ahora usa siempre un intervalo en horas
    # (popup_horas_normal, por defecto 24h) en vez de un flag por-día, así
    # que el propio cálculo de horas transcurridas ya cubre el cambio de
    # día. Se deja la función (no-op) por compatibilidad con quien la llame.
    pass


def _aviso_para_popup(alerta):
    pid        = alerta.get("id", "?")
    pedido_num = alerta.get("pedido_num") or ""
    norden     = alerta.get("norden") or ""
    hotel      = alerta.get("hotel_nombre") or alerta.get("hotel_codigo") or "—"
    estado     = alerta.get("estado", "")
    proveedor  = alerta.get("proveedor_nombre") or "—"
    articulo   = alerta.get("articulo") or alerta.get("descripcion") or "—"
    dias       = alerta.get("dias_tramitacion", 0)
    nivel      = alerta.get("nivel_alerta", "aviso")
    icono      = "🚨" if nivel == "urgente" else "⚠️"
    nivel_txt  = "URGENTE" if nivel == "urgente" else "AVISO"
    repetir, horas = _config_repeticion(alerta, nivel)
    if not repetir:
        intervalo_txt = "sin recordatorio (aviso único)"
    elif horas == 24:
        intervalo_txt = "recordatorio diario"
    elif horas < 1:
        intervalo_txt = f"recordatorio cada {int(horas * 60)}min"
    else:
        horas_txt = int(horas) if float(horas).is_integer() else horas
        intervalo_txt = f"recordatorio cada {horas_txt}h"
    # (2026-07-29) Identificador reconocible en el título — antes era
    # "Pedido #{id}" con el id interno de la base de datos, que no coincide
    # con ninguno de los números que se ven en el panel web (ni el "Nº" de
    # línea ni el "Pedido DALI/SAP"), obligando a "descifrar" cuál era.
    # Mismo criterio que ya usa Telegram: SAP si existe, si no el nº de
    # línea, el id interno solo si no hay ninguno de los dos.
    if pedido_num:
        identificador = f"SAP {pedido_num}"
    elif norden:
        identificador = f"Nº{norden}"
    else:
        identificador = f"#{pid}"
    return {
        "titulo":  f"{icono} [{nivel_txt}] Pedido {identificador} · {hotel}",
        "mensaje": (
            f"Estado: {estado}\n"
            f"Proveedor: {proveedor}  ·  Artículo: {articulo}\n"
            f"{dias} día{'s' if dias != 1 else ''} sin avance  ({intervalo_txt})"
        ),
        "_pedido_id":         pid,
        "_nivel":             nivel,
        "_bridge_gestionado": True,
        "repeticion":         "ninguna",
        "antelacion":         {"dias": 0, "horas": 0, "minutos": 0},
    }


def _popup_desde_push(notif: dict) -> dict:
    nivel = notif.get("nivel", "aviso")
    return {
        "titulo":             notif.get("titulo", "Aviso de Control de Pedidos"),
        "mensaje":            notif.get("mensaje", ""),
        "_pedido_id":         notif.get("pedido_id"),
        "_nivel":             nivel,
        "_bridge_gestionado": True,
        "_push":              True,
        "repeticion":         "ninguna",
        "antelacion":         {"dias": 0, "horas": 0, "minutos": 0},
    }


_dia_actual: str = _hoy_str()


def _sincronizar_alertas(agenda_data, save_agenda_fn, mostrar_alerta_fn):
    """
    CAMBIOS v4.8 (PRUEBA 2026-08-04) — dedup movido al servidor
    ----------------------------------------------------------------------
    MOTIVO: comprador de INSIRE reportó el mismo popup repitiéndose
    "continuamente" en el mismo día. Sospecha (ver HISTORIAL/chat): el
    dedup de v4.4-v4.7 vivía SOLO en memoria de este proceso
    (_estado_popups, con reintento cada popup_horas_critico/normal). Si
    Organizador Princess se reiniciaba (o el intervalo configurado era
    corto y el comprador tenía varios pedidos urgentes acumulados), el
    aviso volvía a saltar aunque ya se hubiera mostrado.

    Desde Control de Pedidos v12.29.46, /api/bridge/alertas YA NO
    devuelve todas las alertas activas sin más: filtra en el propio
    servidor (tabla bridge_popup_visto) y solo incluye en "alertas" los
    pedidos que este usuario AÚN NO ha recibido como popup — de forma
    persistente, no en memoria del cliente. Cada alerta que llega aquí
    se muestra exactamente una vez, para siempre (ni con reintentos
    horarios ni al reiniciar la app). Si Organizador Princess estaba
    cerrada en el momento en que el pedido entró en alerta, se le
    entregará en cuanto vuelva a conectar — pero solo esa vez.

    En consecuencia, este módulo deja de necesitar _estado_popups /
    _debe_mostrar_popup / _config_repeticion (se dejan definidos más
    abajo, sin usar, por si hay que revertir la prueba rápidamente).

    El resumen para el saludo diario (get_resumen_alertas) ya no puede
    salir de "alertas" (que ahora es solo lo nuevo de este ciclo) — el
    servidor manda aparte total_activas/urgentes_activas/normales_activas
    con el recuento SIN filtrar.
    """
    global _dia_actual

    endpoint = "/api/bridge/alertas"

    try:
        resp = _session.get_alertas_usuario()
    except (urllib.error.HTTPError, urllib.error.URLError, Exception) as exc:
        log.warning("Bridge: no se pudo obtener alertas — %s", exc)
        dns_ip, dns_ok = _dns_check()
        titulo, cuerpo = _analizar_error_red(exc, endpoint, dns_ip, dns_ok)

        def _reintentar_alertas():
            try:
                _session.get_alertas_usuario()
                return True, "", ""
            except (urllib.error.HTTPError, urllib.error.URLError, Exception) as exc2:
                _dns_ip2, _dns_ok2 = _dns_check()
                titulo2, cuerpo2 = _analizar_error_red(exc2, endpoint, _dns_ip2, _dns_ok2)
                return False, titulo2, cuerpo2

        _reportar_fallo_conexion(titulo, cuerpo, _reintentar_alertas)
        _bridge_listo.set()
        return

    alertas = resp.get("alertas", [])   # ya filtradas: solo lo pendiente de entregar
    hoy     = _hoy_str()
    if hoy != _dia_actual:
        _dia_actual = hoy

    global _descartar_alertas_acumuladas
    descartar = _descartar_alertas_acumuladas
    _descartar_alertas_acumuladas = False
    for alerta in alertas:
        pid   = alerta.get("id")
        nivel = alerta.get("nivel_alerta", "aviso")
        if descartar:
            log.info("Bridge: alerta acumulada con la app cerrada, se descarta → pedido #%s (%s)", pid, nivel)
            continue
        if not _shutdown.is_set():
            mostrar_alerta_fn(_aviso_para_popup(alerta))
        log.info("Bridge: popup entregado (dedup servidor) → pedido #%s (%s)", pid, nivel)

    if alertas and descartar:
        log.info("Bridge alertas → %d alerta(s) acumuladas con la app cerrada, descartadas", len(alertas))
    elif alertas:
        log.info("Bridge alertas → %d popup(s) nuevos entregados", len(alertas))

    # v12.29.46: totales SIN filtrar, para el resumen del saludo diario.
    # Fallback a los campos antiguos por si se habla con un servidor
    # anterior a v12.29.46 que aún no manda total_activas/etc.
    if "total_activas" in resp:
        _resumen_alertas["total"]    = resp.get("total_activas", 0)
        _resumen_alertas["urgentes"] = resp.get("urgentes_activas", 0)
        _resumen_alertas["normales"] = resp.get("normales_activas", 0)
    else:
        _resumen_alertas["total"]    = len(alertas)
        _resumen_alertas["urgentes"] = sum(1 for a in alertas if a.get("nivel_alerta") == "urgente")
        _resumen_alertas["normales"] = sum(1 for a in alertas if a.get("nivel_alerta") != "urgente")
    _bridge_listo.set()


def _procesar_push(agenda_data, save_agenda_fn, mostrar_alerta_fn):
    """
    CAMBIOS v4.4 — deja de grabar en agenda.json
    ----------------------------------------------
    Las notificaciones push (techo, familia repetida, cambio de estado,
    supervisión...) ya NO se persisten en agenda.json. Solo disparan un
    popup inmediato. El dedup por sesión sigue en _push_procesados
    (en memoria): si la app se cierra antes de procesar un push, ese
    aviso concreto se pierde (no hay replay al reiniciar) — compromiso
    aceptado a cambio de simplicidad.
    """

    endpoint   = "/api/bridge/notificaciones"

    try:
        resp = _session.get_notificaciones_push()
    except (urllib.error.HTTPError, urllib.error.URLError, Exception) as exc:
        log.warning("Bridge push: no se pudo obtener notificaciones — %s", exc)
        dns_ip, dns_ok = _dns_check()
        titulo, cuerpo = _analizar_error_red(exc, endpoint, dns_ip, dns_ok)

        def _reintentar_push():
            try:
                _session.get_notificaciones_push()
                return True, "", ""
            except (urllib.error.HTTPError, urllib.error.URLError, Exception) as exc2:
                _dns_ip2, _dns_ok2 = _dns_check()
                titulo2, cuerpo2 = _analizar_error_red(exc2, endpoint, _dns_ip2, _dns_ok2)
                return False, titulo2, cuerpo2

        _reportar_fallo_conexion(titulo, cuerpo, _reintentar_push)
        return

    notifs = resp.get("notificaciones", [])
    global _descartar_push_acumulado
    descartar = _descartar_push_acumulado
    _descartar_push_acumulado = False
    if not notifs:
        return

    for notif in notifs:
        nid = notif.get("id")
        if nid in _push_procesados:
            continue
        _push_procesados.add(nid)

        if descartar:
            log.info("Bridge push: acumulada con la app cerrada, se descarta → tipo=%s id=%s", notif.get("tipo"), nid)
            continue

        popup = _popup_desde_push(notif)
        if not _shutdown.is_set():
            mostrar_alerta_fn(popup)
        log.info(
            "Bridge push: popup inmediato → tipo=%s nivel=%s id=%s",
            notif.get("tipo"), notif.get("nivel"), nid
        )


def _loop_alertas(agenda_data, save_agenda_fn, mostrar_alerta_fn):
    """Hilo: sincronización periódica de alertas activas (cada 15 min)."""
    for intento in range(1, 4):
        if _shutdown.is_set():
            return
        if _session.login():
            break
        log.info("Bridge: Render puede estar arrancando, reintento %d/3...", intento)
        time.sleep(30)

    while not _shutdown.is_set():
        try:
            if not _session._logged_in:
                log.info("Bridge: sesión no activa, reintentando login...")
                _session.login()
            if not _shutdown.is_set():
                _sincronizar_alertas(agenda_data, save_agenda_fn, mostrar_alerta_fn)
        except Exception as exc:
            log.error("Bridge alertas: error inesperado — %s", exc)
            _session._logged_in = False
        # Esperar en trozos de 1 s para reaccionar rápido al shutdown
        for _ in range(INTERVALO_ALERTAS_MINUTOS * 60):
            if _shutdown.is_set():
                return
            time.sleep(1)


def _loop_push(agenda_data, save_agenda_fn, mostrar_alerta_fn):
    """Hilo: cola push de notificaciones inmediatas (cada 60 s)."""
    _bridge_listo.wait(timeout=60)
    if _shutdown.is_set():
        return
    time.sleep(5)

    while not _shutdown.is_set():
        try:
            if _session._logged_in and not _shutdown.is_set():
                _procesar_push(agenda_data, save_agenda_fn, mostrar_alerta_fn)
        except Exception as exc:
            log.error("Bridge push: error inesperado — %s", exc)
        # Esperar en trozos de 1 s para reaccionar rápido al shutdown
        for _ in range(INTERVALO_PUSH_SEGUNDOS):
            if _shutdown.is_set():
                return
            time.sleep(1)


# ── (v4.18.66) Agenda sincronizada con el usuario de Control de Pedidos ──────────────────────────────────
# Petición de Víctor (13 nov 2026): con el mismo usuario en cualquier PC, la misma agenda (avisos,
# vacaciones y festivos). La lógica de qué subir y cómo fusionar está en services/sincro_agenda.py (sin red,
# con pruebas en test_sincro_agenda.py); aquí solo la red y el hilo. Lo que toca agenda_data se hace en el
# hilo principal de Tk (_en_principal), igual que las ventanas que la editan, y bajo sincro.CERROJO.
INTERVALO_AGENDA_SEGUNDOS = 120     # comprobar cambios de otros PC cada 2 min
ESPERA_TRAS_GUARDAR_SEGUNDOS = 3    # tras guardar algo aquí, subirlo a los pocos segundos
ESPERA_SIN_RUTA_SEGUNDOS = 3600     # Control de Pedidos anterior a v12.34.36 (404): volver a mirar en 1 h
_estado_agenda = {"ultima": None, "error": "", "sin_ruta": False}


def estado_sincro_agenda() -> dict:
    """Para mostrar en la interfaz: {"ultima": datetime|None, "error": str, "sin_ruta": bool}."""
    return dict(_estado_agenda)


def _en_principal(fn, timeout=30):
    """Ejecuta fn() en el hilo principal de Tk y devuelve su resultado (o lo ejecuta aquí si no hay Tk)."""
    if _app_root is None:
        return fn()
    hecho = threading.Event()
    caja = {}

    def _ejecutar():
        try:
            caja["r"] = fn()
        except Exception as exc:  # noqa: BLE001
            caja["e"] = exc
        finally:
            hecho.set()

    try:
        _app_root.after(0, _ejecutar)
    except Exception:  # noqa: BLE001 — Tk cerrándose
        return None
    if not hecho.wait(timeout):
        raise TimeoutError("el hilo principal no respondió")
    if "e" in caja:
        raise caja["e"]
    return caja.get("r")


def _sincronizar_agenda(agenda_data, save_agenda_fn):
    """Una vuelta: bajar lo cambiado en otros PC, aplicarlo y subir lo pendiente de este."""
    from services import sincro_agenda as sincro

    def _preparar():
        with sincro.CERROJO:
            cambio = sincro.cambiar_usuario(agenda_data, _session.username or BRIDGE_USER)
            # marcar_cambios antes de fusionar: la agenda de antes de esta versión aún no tiene ids.
            if sincro.marcar_cambios(agenda_data) or cambio:
                save_agenda_fn(agenda_data)
            if cambio:
                sincro.refrescar_ventanas()
            return sincro.estado(agenda_data)["version"]

    desde = _en_principal(_preparar)
    remotos = []
    while not _shutdown.is_set():
        resp = _session.get_agenda(desde)
        remotos.extend(resp.get("elementos") or [])
        desde = max(int(desde), int(resp.get("version") or 0))
        if not resp.get("mas"):
            break

    def _aplicar():
        with sincro.CERROJO:
            cambio = sincro.aplicar_remotos(agenda_data, remotos)
            sincro.estado(agenda_data)["version"] = max(sincro.estado(agenda_data)["version"], desde)
            save_agenda_fn(agenda_data)
            if cambio:
                sincro.refrescar_ventanas()   # en el mismo paso: las posiciones pintadas siguen valiendo
            return cambio, sincro.pendientes(agenda_data)

    _cambio, enviar = _en_principal(_aplicar)
    for i in range(0, len(enviar), sincro.MAX_POR_ENVIO):
        if _shutdown.is_set():
            break
        tanda = enviar[i:i + sincro.MAX_POR_ENVIO]
        resp = _session.post_agenda(tanda)

        def _respuesta(tanda=tanda, resp=resp):
            with sincro.CERROJO:
                c = sincro.aplicar_respuesta(agenda_data, tanda, resp)
                save_agenda_fn(agenda_data)
                if c:
                    sincro.refrescar_ventanas()
                return c

        _en_principal(_respuesta)
    # Lo guardado aquí durante la vuelta ya se ha subido (o se subirá en la siguiente): no hace falta otra.
    with sincro.CERROJO:
        if not sincro.hay_pendientes(agenda_data):
            sincro.CAMBIO_LOCAL.clear()
    if remotos or enviar:
        log.info("Agenda sincronizada: %d recibido(s), %d enviado(s) — %s",
                 len(remotos), len(enviar), sincro.resumen(agenda_data))


def _loop_agenda(agenda_data, save_agenda_fn):
    """Hilo: sincroniza la agenda al arrancar, a los pocos segundos de cada cambio y cada 2 min."""
    from services import sincro_agenda as sincro
    _bridge_listo.wait(timeout=90)
    while not _shutdown.is_set():
        espera = INTERVALO_AGENDA_SEGUNDOS
        if _session._logged_in:
            try:
                _sincronizar_agenda(agenda_data, save_agenda_fn)
                _estado_agenda.update(ultima=datetime.now(), error="", sin_ruta=False)
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    if not _estado_agenda["sin_ruta"]:
                        log.warning("Agenda: Control de Pedidos aún no sincroniza la agenda (404); "
                                    "se sigue con la copia local")
                    _estado_agenda.update(sin_ruta=True, error="")
                    espera = ESPERA_SIN_RUTA_SEGUNDOS
                else:
                    log.warning("Agenda: no se pudo sincronizar (HTTP %s); se reintentará", exc.code)
                    _estado_agenda["error"] = f"HTTP {exc.code}"
            except Exception as exc:  # noqa: BLE001 — sin red se sigue con la copia local
                log.warning("Agenda: no se pudo sincronizar (%s); se reintentará", exc)
                _estado_agenda["error"] = str(exc)[:200]
        for _ in range(espera):
            if _shutdown.is_set():
                return
            if sincro.CAMBIO_LOCAL.is_set() and _session._logged_in and not _estado_agenda["sin_ruta"]:
                sincro.CAMBIO_LOCAL.clear()
                time.sleep(ESPERA_TRAS_GUARDAR_SEGUNDOS)
                break
            time.sleep(1)


def iniciar_bridge_pedidos(agenda_data, save_agenda_fn, app_root_legacy=None, app_root=None,
                            mostrar_alerta_fn=None):
    """
    Arranca dos hilos en segundo plano:
      1. Hilo de alertas (polling 15 min)  — sincroniza agenda.json
      2. Hilo push (polling 60 s)          — notificaciones inmediatas

    app_root: referencia al widget Tk raíz (para mostrar diálogos de error
              en el hilo principal via app_root.after()).

    mostrar_alerta_fn: referencia directa a negocio.alertas.mostrar_alerta,
              inyectada por main_agenda.py. Ver ANTI-REGRESION más abajo.
    """
    global _dia_actual, _app_root

    # Compatibilidad con llamada antigua de 3 argumentos
    _app_root = app_root or app_root_legacy

    _shutdown.clear()   # FIX: resetear por si se llama de nuevo tras un reinicio
    _estado_popups.clear()
    _push_procesados.clear()
    global _descartar_alertas_acumuladas, _descartar_push_acumulado
    _descartar_alertas_acumuladas = True
    _descartar_push_acumulado = True
    _dia_actual = _hoy_str()
    _bridge_listo.clear()

    _cargar_credenciales_desde_db()

    if not BRIDGE_USER or not BRIDGE_PASSWORD:
        log.warning(
            "Bridge desactivado: configura tu usuario y contraseña de Control de Pedidos "
            "en Organizador Princess -> Admin -> Mi Usuario (sección Control de Pedidos)."
        )
        return

    # ANTI-REGRESION (bug detectado 2026-07-13): antes se intentaba obtener
    # mostrar_alerta con `import main_agenda as _ma; _ma.mostrar_alerta`.
    # main_agenda.py es el script de arranque (ejecutado directamente o como
    # .exe de PyInstaller) y Python lo registra en sys.modules como
    # "__main__", no como "main_agenda": ese import no reutiliza el módulo en
    # marcha, sino que vuelve a cargar y EJECUTAR main_agenda.py entero (o
    # falla), y en ningún caso da el mostrar_alerta() real. SOLUCIÓN:
    # main_agenda.py pasa mostrar_alerta como parámetro. (v4.18.06) Se quita
    # también el intento de «import main_agenda» que quedaba como
    # compatibilidad: no hay ninguna otra llamada y podía re-ejecutar la app.
    # Nunca importar main_agenda desde otro módulo.
    if mostrar_alerta_fn is not None:
        _mostrar_alerta = mostrar_alerta_fn
        log.info("Bridge: mostrar_alerta inyectada directamente por main_agenda.py")
    else:
        log.warning(
            "Bridge: no se recibió mostrar_alerta_fn — los popups quedarán solo en el log."
        )
        def _mostrar_alerta(aviso, **_):
            log.warning(
                "Bridge [popup fallback]: %s — %s",
                aviso.get("titulo", ""), aviso.get("mensaje", ""),
            )

    # CAMBIOS v4.4 — arranque no bloqueante
    # ------------------------------------------------------------
    # Antes, login()+_sincronizar_alertas()+_procesar_push() se llamaban aquí
    # de forma síncrona, en el hilo principal, ANTES de app.mainloop(). Si
    # Render tardaba en responder (cold start), Tkinter quedaba congelado
    # varios segundos; al arrancar el mainloop, todos los app.after()
    # programados (saludo, poller de popups, etc.) se disparaban casi a la
    # vez y competían por el foco/grab con los popups ya encolados — esto
    # es lo que se percibía como "ventanas que se abren y cierran rápido".
    # Ahora el login + primera sincronización se hacen en el propio hilo
    # t1 (_loop_alertas), que ya hace sus reintentos de login y arranca su
    # bucle sin bloquear Tkinter en ningún momento.

    t1 = threading.Thread(
        target=_loop_alertas,
        args=(agenda_data, save_agenda_fn, _mostrar_alerta),
        daemon=True,
        name="PedidosBridge-Alertas",
    )
    t1.start()

    t2 = threading.Thread(
        target=_loop_push,
        args=(agenda_data, save_agenda_fn, _mostrar_alerta),
        daemon=True,
        name="PedidosBridge-Push",
    )
    t2.start()

    t3 = threading.Thread(
        target=_loop_agenda,
        args=(agenda_data, save_agenda_fn),
        daemon=True,
        name="PedidosBridge-Agenda",
    )
    t3.start()

    log.info(
        "Bridge iniciado  |  usuario: %s (%s)  |  "
        "alertas: %d min  |  push: %d s  |  popup urgente: cada %dh  |  popup normal: 1/día",
        BRIDGE_USER, _session.rol,
        INTERVALO_ALERTAS_MINUTOS, INTERVALO_PUSH_SEGUNDOS, INTERVALO_POPUP_URGENTE,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Test rápido:  python pedidos_agenda_bridge.py
# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s  %(message)s")

    _data = {}

    def _save(d):
        print("\n=== Avisos que se escribirían en agenda.json ===")
        for av in d.get("avisos", []):
            print(f"  [{av.get('fecha')}] {av['titulo']}")
            print(f"       {av.get('mensaje', '')}\n")
        if not d.get("avisos"):
            print("  (sin alertas activas para este usuario)")

    def _fake_mostrar_alerta(aviso, **_):
        origen = "PUSH" if aviso.get("_push") else "POLLING"
        print(f"\n  🔔 [{origen}] POPUP → {aviso['titulo']}")
        print(f"                    {aviso.get('mensaje', '')}")

    print(f"Conectando a {CONTROL_PEDIDOS_URL} como '{BRIDGE_USER}' ...\n")
    if _session.login():
        print(f"  → Login OK  |  rol: {_session.rol}  |  nombre: {_session.nombre}\n")
        print("--- Alertas periódicas ---")
        _sincronizar_alertas(_data, _save, _fake_mostrar_alerta)
        print("\n--- Notificaciones push ---")
        _procesar_push(_data, _save, _fake_mostrar_alerta)
    else:
        print("No se pudo hacer login. Revisa BRIDGE_USER y BRIDGE_PASSWORD.")
