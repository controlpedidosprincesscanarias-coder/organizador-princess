"""
services/update_service.py
Comprobación de actualizaciones en GitHub y diálogos de instalación.
Extraído de main_agenda.py en Fase 2 del sprint de estabilización.

Uso desde main_agenda:
    from services.update_service import _lanzar_check_update, _check_version_reset
    _lanzar_check_update(app)
(La ventana «Nueva versión» tras instalar vive en main_agenda.py, _dialogo_nueva_version.)
"""
# Nota: este módulo usa tkinter/ttkbootstrap directamente porque toda la UI
# de actualización está acoplada a los diálogos. Se desacoplará en Fase 3.

import os
import ttkbootstrap as ttk                              # ANTI-REGRESION: era global de main_agenda
from db.sqlite import CONFIG_FILE, VERSION_FILE, AGENDA_FILE  # ANTI-REGRESION: AGENDA_FILE faltaba
from ui.assets import _apply_icon                       # ANTI-REGRESION: usada en todos los Toplevel
# Inyectados desde main_agenda al arrancar
APP_VERSION  = ""   # se sobreescribe desde main_agenda
GITHUB_REPO  = ""   # se sobreescribe desde main_agenda

# Constante de color — ANTI-REGRESION: era global de main_agenda
LIGHT = "#D8E8F0"
import json
import threading
from datetime import datetime
from tkinter import messagebox


# ──────────────────────────────────────────────────────────────────────────────
# GRACIA DE RECONEXIÓN — no avisar al primer fallo del check de GitHub,
# reintentar a los 5 min (2026-08-04)
# ──────────────────────────────────────────────────────────────────────────────
# PROBLEMA DETECTADO: a diferencia del aviso de conexión con Control de
# Pedidos (pedidos_agenda_bridge.py), este check NO tenía ningún límite de
# "1 diálogo por día" — cada fallo (HTTPError, URLError o excepción
# inesperada) mostraba el diálogo rojo "Error al comprobar actualizaciones"
# de inmediato y se reprogramaba a los 30 minutos sin más. Si GitHub no era
# alcanzable durante un rato (firewall, corte puntual, incidencia de
# GitHub), el diálogo podía reaparecer cada 30 minutos indefinidamente.
#
# CAMBIO: mismo criterio que en pedidos_agenda_bridge.py — el primer fallo
# no muestra el diálogo, concede _GRACIA_UPDATE_SEGUNDOS y reintenta UNA
# vez el mismo check. Si el reintento tiene éxito, se descarta en
# silencio (con log) y sigue el ciclo normal (2 h desde v4.18.06). Si el reintento
# también falla, entonces sí se muestra el diálogo — con el error de ese
# segundo intento — y a partir de ahí se retoma el ciclo normal (2 h)
# (el propio reintento, al ejecutar _check_update_github de nuevo, ya se
# encarga de reprogramarse).
_GRACIA_UPDATE_SEGUNDOS = 5 * 60

_gracia_update_en_curso = False
_gracia_update_lock     = threading.Lock()


# ── (v4.18.06) Límite de consultas de GitHub ────────────────────────────────
# Sin iniciar sesión, GitHub admite 60 consultas por hora por IP pública. Todos
# los equipos que salen a Internet por la misma IP de la empresa comparten ese
# cupo. Al agotarlo responde 403 (o 429) con X-RateLimit-Remaining: 0. No es un
# fallo de red: no se avisa al usuario (el diálogo rojo pedía abrir el
# firewall), no se gasta el reintento de gracia y se vuelve a mirar cuando
# GitHub lo permita (X-RateLimit-Reset / Retry-After), con un margen al azar
# para que los equipos no vuelvan todos a la vez.
# (v4.18.06, decisión de Víctor) Ciclo normal: al arrancar y después cada 2 h
# (antes, 30 min), con 0–10 min al azar para que los equipos no consulten a la
# vez. Una versión publicada llega a todos en unas 2 h como mucho.
_INTERVALO_CHECK_S = 2 * 60 * 60
_MARGEN_CHECK_S = 10 * 60


def _programar_siguiente_check(app_root):
    """Programa la siguiente comprobación de actualizaciones del ciclo normal."""
    import random as _rnd
    espera = _INTERVALO_CHECK_S + int(_rnd.uniform(0, _MARGEN_CHECK_S))
    app_root.after(espera * 1000, lambda: _lanzar_check_update(app_root))


_ESPERA_LIMITE_MIN_S = 60
_ESPERA_LIMITE_MAX_S = 2 * 60 * 60


def _espera_por_limite_github(codigo, cabeceras, ahora=None, azar=None):
    """Segundos a esperar si la respuesta es por límite de consultas de GitHub;
    None si es otro error (que sigue el tratamiento normal)."""
    import random as _rnd
    import time as _time
    if codigo not in (403, 429):
        return None
    cab = {str(k).lower(): str(v) for k, v in (cabeceras or {}).items()}
    retry_after = cab.get("retry-after", "").strip()
    restantes = cab.get("x-ratelimit-remaining", "").strip()
    if not retry_after and restantes != "0" and codigo != 429:
        return None   # 403 por otro motivo (proxy, filtrado...): error normal
    ahora = _time.time() if ahora is None else ahora
    margen = (_rnd.uniform(0, 300) if azar is None else azar)
    if retry_after.isdigit():
        espera = int(retry_after)
    elif cab.get("x-ratelimit-reset", "").strip().isdigit():
        espera = int(cab["x-ratelimit-reset"]) - ahora
    else:
        espera = 15 * 60
    return int(min(max(espera + margen, _ESPERA_LIMITE_MIN_S), _ESPERA_LIMITE_MAX_S))


# ── (v4.16.9) Comprobación de integridad del instalador descargado ──────────
# Si el release publica un fichero «<instalador>.sha256» (o «SHA256SUMS» /
# «SHA256SUMS.txt»), se compara el SHA-256 de lo descargado con el publicado.
# Detecta descargas corruptas o alteradas por el camino; NO sustituye a la
# firma de código del .exe (quien controle el release controla también el hash).
import hashlib
import re as _re_hash
from services import portatil as _portatil   # (v4.18.54) copia portátil, sin instalar

def _asset_hash(assets, nombre_exe):
    """Asset con el hash del instalador, o None."""
    candidatos = {nombre_exe.lower() + ".sha256", "sha256sums", "sha256sums.txt"}
    for a in assets:
        if (a.get("name") or "").lower() in candidatos:
            return a
    return None

def _extraer_hash(texto, nombre_exe):
    """Hash (64 hex) para `nombre_exe` dentro del contenido de un .sha256 o
    SHA256SUMS. Acepta «<hash>», «<hash>  <fichero>» y «<hash> *<fichero>»."""
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    for l in lineas:
        m = _re_hash.match(r"^([0-9a-fA-F]{64})\s+\*?(.+)$", l)
        if m and m.group(2).strip().lower() == nombre_exe.lower():
            return m.group(1).lower()
    if len(lineas) == 1:
        m = _re_hash.match(r"^([0-9a-fA-F]{64})(\s.*)?$", lineas[0])
        if m:
            return m.group(1).lower()
    return None

def _conceder_gracia_update(app_root):
    """
    Primer fallo del check de actualizaciones: no avisa, programa un único
    reintento silencioso a los 5 minutos (_check_update_github con
    _es_reintento_gracia=True). Si ya hay un reintento pendiente, no
    programa otro — todos los fallos mientras tanto son síntoma del mismo
    corte.
    """
    global _gracia_update_en_curso

    with _gracia_update_lock:
        if _gracia_update_en_curso:
            return
        _gracia_update_en_curso = True

    def _reintentar():
        global _gracia_update_en_curso
        try:
            _check_update_github(app_root, _es_reintento_gracia=True)
        finally:
            with _gracia_update_lock:
                _gracia_update_en_curso = False

    _timer = threading.Timer(_GRACIA_UPDATE_SEGUNDOS, _reintentar)
    _timer.daemon = True
    _timer.start()


def _check_update_github(app_root, _es_reintento_gracia: bool = False):
    """
    Hilo de comprobación de actualizaciones contra GitHub Releases.
    Se llama con app.after() desde el hilo principal tras el arranque.

    _es_reintento_gracia: True cuando esta llamada es el reintento
    programado a los 5 minutos tras un primer fallo silencioso (ver
    _conceder_gracia_update). En ese caso, si vuelve a fallar, SÍ se
    muestra el diálogo (ya no hay más gracia que conceder).
    """
    import urllib.request
    import urllib.error
    import json as _json
    import os as _os
    import socket as _socket
    import ssl as _ssl

    def _ssl_ctx():
        """
        Contexto SSL con verificación, usando el almacén de certificados de
        Windows (así funciona también detrás de un proxy corporativo con
        inspección SSL cuyo certificado raíz esté instalado en el equipo).

        (v4.16.9) Se quita el respaldo SIN verificación que había antes: si el
        contexto no se puede crear, la comprobación de actualización falla con
        un error normal en vez de continuar sin comprobar el certificado de
        GitHub (de ahí se baja un instalador que se ejecuta como administrador).
        """
        ctx = _ssl.create_default_context()
        ctx.load_default_certs()   # usa el almacén de Windows
        return ctx

    # ── LOG DE DIAGNÓSTICO ────────────────────────────────────────────────────
    # Escribe en %APPDATA%\OrganizadorPrincess\update_check.log
    # Útil para depurar PCs donde no aparece el aviso de actualización.
    # ELIMINAR este bloque una vez resuelto el problema.
    _log_path = _os.path.join(_os.path.dirname(CONFIG_FILE), "update_check.log")
    def _ulog(msg):
        ts = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(_log_path, "a", encoding="utf-8") as _lf:
                _lf.write(f"[{ts}] {msg}\n")
        except Exception:  # noqa: BLE001
            import sys as _sys, traceback as _tb
            print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
    # ─────────────────────────────────────────────────────────────────────────

    API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

    _ulog(f"=== CHECK INICIO  versión local={APP_VERSION} ===")
    _ulog(f"URL: {API_URL}")

    def _mostrar_error_red(titulo, cuerpo):
        """Muestra un diálogo de error de red en el hilo principal de Tkinter.
        Solo se invoca cuando el check falla — no aparece en condiciones normales."""
        import tkinter as _tk

        def _dlg():
            dlg = ttk.Toplevel(app_root)
            dlg.withdraw()
            dlg.title(titulo)
            dlg.resizable(False, False)
            dlg.attributes("-topmost", True)
            _apply_icon(dlg)
            dlg.transient(app_root)

            # Cabecera roja
            hdr = ttk.Frame(dlg, bootstyle="danger")
            hdr.pack(fill="x")
            _hi = ttk.Frame(hdr, bootstyle="danger")
            _hi.pack(fill="x", padx=16, pady=10)
            ttk.Label(_hi, text="⚠️  Error al comprobar actualizaciones",
                      font=("Segoe UI", 11, "bold"),
                      bootstyle="inverse-danger").pack(anchor="w")
            ttk.Label(_hi, text="El sistema de actualización automática no ha podido contactar con GitHub.",
                      font=("Segoe UI", 8),
                      bootstyle="inverse-danger").pack(anchor="w", pady=(2, 0))
            ttk.Separator(dlg).pack(fill="x")

            body = ttk.Frame(dlg, padding=(18, 12, 18, 4))
            body.pack(fill="both", expand=True)

            # Cuerpo — texto técnico seleccionable
            ttk.Label(body, text="📋  Detalle técnico para el servicio informático:",
                      font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 6))

            frm_txt = ttk.Frame(body)
            frm_txt.pack(fill="both", expand=True)
            txt = _tk.Text(frm_txt, height=10, width=70,
                           font=("Consolas", 8), wrap="word",
                           relief="flat", state="normal",
                           background="#1e1e2e", foreground="#f8d7da",
                           padx=10, pady=8)
            txt.insert("1.0", cuerpo)
            txt.configure(state="disabled")
            txt.pack(fill="both", expand=True)

            # Nota para el usuario
            ttk.Separator(dlg).pack(fill="x", pady=(10, 0))
            nota = ttk.Frame(dlg, padding=(18, 8, 18, 4))
            nota.pack(fill="x")
            ttk.Label(nota,
                      text=("ℹ️  Esta ventana solo aparece en modo diagnóstico.\n"
                             "Comparte el texto de arriba con el servicio informático para\n"
                             "que puedan autorizar el acceso a api.github.com (puerto 443 HTTPS)."),
                      font=("Segoe UI", 8), foreground="#adb5bd",
                      justify="left").pack(anchor="w")

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
                                    bootstyle="danger-outline", command=dlg.destroy)
            btn_copiar.pack(side="left", padx=(0, 8))
            btn_cerrar.pack(side="left")

            # Centrar y mostrar
            dlg.update_idletasks()
            _w, _h = 560, dlg.winfo_reqheight()
            _sw = dlg.winfo_screenwidth()
            _sh = dlg.winfo_screenheight()
            dlg.geometry(f"{_w}x{max(_h, 380)}+{(_sw-_w)//2}+{max(40,(_sh-_h)//2)}")
            dlg.deiconify()
            dlg.lift()
            dlg.focus_force()

            # Auto-cierre a los 2 minutos si nadie interactúa (mismo
            # criterio que el resto de avisos de error de conexión).
            def _autocierre_error_update():
                if dlg.winfo_exists():
                    dlg.destroy()

            dlg.after(2 * 60 * 1000, _autocierre_error_update)

        app_root.after(0, _dlg)

    # ── Diagnóstico de red previo (DNS) ───────────────────────────────────────
    dns_ip   = ""
    dns_ok   = False
    dns_info = ""
    try:
        dns_ip = _socket.gethostbyname("api.github.com")
        dns_ok = True
        dns_info = f"DNS ok — api.github.com → {dns_ip}"
        _ulog(dns_info)
    except Exception as _dns_exc:
        dns_info = f"DNS FALLO — {_dns_exc}"
        _ulog(dns_info)

    try:
        req = urllib.request.Request(
            API_URL,
            headers={"Accept": "application/vnd.github+json",
                     "User-Agent": "OrganizadorPrincess"}
        )
        with urllib.request.urlopen(req, timeout=10, context=_ssl_ctx()) as resp:
            _ulog(f"HTTP {resp.status} — Content-Length: {resp.headers.get('Content-Length', 'N/A')}")
            raw = resp.read()
            data = _json.loads(raw.decode())
            if _es_reintento_gracia:
                _ulog("Reintento de gracia OK — conexión recuperada, aviso suprimido")

    except urllib.error.HTTPError as exc:
        _espera_limite = _espera_por_limite_github(exc.code, dict(exc.headers or {}))
        if _espera_limite is not None:
            _ulog(f"HTTP {exc.code}: límite de consultas de GitHub agotado para esta IP — "
                  f"sin aviso; nuevo intento en {_espera_limite // 60} min")
            app_root.after(_espera_limite * 1000, lambda: _lanzar_check_update(app_root))
            return
        msg = (
            f"TIPO DE ERROR : HTTP {exc.code} {exc.reason}\n"
            f"\n"
            f"Aplicación    : MENU {APP_VERSION} (OrganizadorPrincess)\n"
            f"Equipo        : {_socket.gethostname()}\n"
            f"URL           : {API_URL}\n"
            f"DNS           : {dns_info}\n"
            f"\n"
            f"POSIBLE CAUSA : El servidor de GitHub respondió con un error HTTP.\n"
            f"               Código {exc.code} — puede indicar bloqueo por proxy\n"
            f"               corporativo, política de filtrado de contenido, o\n"
            f"               rate-limit de la IP de salida de la empresa.\n"
            f"\n"
            f"ACCIÓN REQUERIDA:\n"
            f"  · Permitir acceso HTTPS (puerto 443) a:\n"
            f"      api.github.com\n"
            f"      objects.githubusercontent.com  (descargas)\n"
            f"  · Si hay proxy corporativo, añadir excepción para los dominios anteriores.\n"
            f"\n"
            f"Log guardado en:\n  {_log_path}"
        )
        _ulog(f"HTTPError {exc.code}: {exc.reason}")
        if _es_reintento_gracia:
            _mostrar_error_red("Error de actualización — HTTP " + str(exc.code), msg)
            _programar_siguiente_check(app_root)
        else:
            _ulog("Primer fallo — gracia de 5 min antes de avisar")
            _conceder_gracia_update(app_root)
        return

    except urllib.error.URLError as exc:
        razon = str(exc.reason)
        if not dns_ok:
            causa = (
                "El equipo no puede resolver el nombre 'api.github.com'.\n"
                "Esto indica que el DNS corporativo puede estar bloqueando\n"
                "dominios externos, o que no hay conexión a Internet."
            )
            accion = (
                "  · Verificar que el DNS permite resolver dominios externos.\n"
                "  · Comprobar que el equipo tiene salida a Internet."
            )
        elif "SSL" in razon or "certificate" in razon.lower():
            causa = (
                "El proxy o firewall corporativo está interceptando la conexión\n"
                "HTTPS (SSL inspection) y el certificado presentado no es de confianza."
            )
            accion = (
                "  · Añadir excepción de inspección SSL para: api.github.com\n"
                "  · O instalar el certificado raíz del proxy en el equipo."
            )
        elif "timed out" in razon.lower() or "timeout" in razon.lower():
            causa = (
                "La conexión a api.github.com se ha agotado (timeout 10 s).\n"
                "El firewall puede estar descartando silenciosamente los paquetes\n"
                "en lugar de rechazarlos explícitamente."
            )
            accion = (
                f"  · Permitir tráfico HTTPS saliente (puerto 443 TCP) a:\n"
                f"      api.github.com  ({dns_ip or 'sin resolución DNS'})\n"
                f"  · Revisar reglas de firewall perimetral."
            )
        else:
            causa = f"No se ha podido establecer conexión con api.github.com.\nDetalle: {razon}"
            accion = (
                "  · Permitir acceso HTTPS (puerto 443) a api.github.com\n"
                "  · Comprobar proxy / firewall corporativo."
            )

        msg = (
            f"TIPO DE ERROR : URLError — {razon}\n"
            f"\n"
            f"Aplicación    : MENU {APP_VERSION} (OrganizadorPrincess)\n"
            f"Equipo        : {_socket.gethostname()}\n"
            f"URL           : {API_URL}\n"
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
        _ulog(f"URLError: {razon}")
        if _es_reintento_gracia:
            _mostrar_error_red("Error de actualización — Sin conexión", msg)
            _programar_siguiente_check(app_root)
        else:
            _ulog("Primer fallo — gracia de 5 min antes de avisar")
            _conceder_gracia_update(app_root)
        return

    except Exception as exc:
        msg = (
            f"TIPO DE ERROR : {type(exc).__name__} — {exc}\n"
            f"\n"
            f"Aplicación    : MENU {APP_VERSION} (OrganizadorPrincess)\n"
            f"Equipo        : {_socket.gethostname()}\n"
            f"URL           : {API_URL}\n"
            f"DNS           : {dns_info}\n"
            f"\n"
            f"POSIBLE CAUSA : Error inesperado durante la comprobación de actualizaciones.\n"
            f"\n"
            f"Log guardado en:\n  {_log_path}"
        )
        _ulog(f"ERROR inesperado: {type(exc).__name__}: {exc}")
        if _es_reintento_gracia:
            _mostrar_error_red("Error de actualización — Error inesperado", msg)
            _programar_siguiente_check(app_root)
        else:
            _ulog("Primer fallo — gracia de 5 min antes de avisar")
            _conceder_gracia_update(app_root)
        return

    tag_remoto  = data.get("tag_name", "")
    nombre_rel  = data.get("name", tag_remoto)

    _ulog(f"tag_remoto={tag_remoto!r}  nombre_rel={nombre_rel!r}")

    if not tag_remoto:
        _ulog("tag_remoto vacío — abortando sin mostrar diálogo")
        return

    try:
        local_v  = _parse_version(APP_VERSION)
        remote_v = _parse_version(tag_remoto)
        _ulog(f"versión local parseada={local_v}  remota={remote_v}")
        if remote_v <= local_v:
            _ulog("Ya al día — siguiente comprobación en unas 2 h")
            _programar_siguiente_check(app_root)
            return
        _ulog(f"Actualización disponible: {APP_VERSION} → {tag_remoto}")
    except Exception as exc:
        _ulog(f"ERROR comparando versiones: {exc}")
        return

    # Buscar el asset instalador (.exe) o, en la copia portátil (v4.18.54), el .zip portátil
    assets = data.get("assets", [])
    _es_portatil = _portatil.es_portatil()
    if _es_portatil:
        asset_exe, asset_sha = _portatil.elegir_assets(assets, portatil=True)
    else:
        asset_exe = next(
            (a for a in assets if a.get("name", "").lower().endswith(".exe")),
            None
        )
        asset_sha = _asset_hash(assets, asset_exe["name"]) if asset_exe else None
    url_sha        = asset_sha["browser_download_url"] if asset_sha else ""
    url_descarga   = asset_exe["browser_download_url"] if asset_exe else ""
    nombre_asset   = asset_exe["name"] if asset_exe else ""
    size_mb        = round(asset_exe["size"] / 1_048_576, 1) if asset_exe else 0
    notas          = data.get("body", "").strip()

    def _mostrar_dialogo_update():
        """Se ejecuta en el hilo principal de Tkinter."""
        import tkinter as _tk

        upd = ttk.Toplevel(app_root)
        upd.withdraw()
        upd.title(f"Actualización disponible — {tag_remoto}")
        upd.resizable(False, True)
        upd.attributes("-topmost", True)
        _apply_icon(upd)
        upd.transient(app_root)

        _UW = 600

        # Cabecera
        hdr = ttk.Frame(upd, bootstyle="success")
        hdr.pack(fill="x")
        _hi = ttk.Frame(hdr, bootstyle="success")
        _hi.pack(fill="x", padx=16, pady=12)
        ttk.Label(_hi, text=f"🆙  Nueva versión disponible: {tag_remoto}",
                  font=("Segoe UI", 13, "bold"),
                  bootstyle="inverse-success").pack(anchor="w")
        ttk.Label(_hi, text=f"Versión instalada: {APP_VERSION}  ·  {nombre_rel}",
                  font=("Segoe UI", 9),
                  bootstyle="inverse-success").pack(anchor="w", pady=(2, 0))
        ttk.Separator(upd).pack(fill="x")

        body = ttk.Frame(upd, padding=(18, 12, 18, 4))
        body.pack(fill="both", expand=True)

        # Notas de la versión
        if notas:
            ttk.Label(body, text="📋  Novedades:",
                      font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))
            frm_txt = ttk.Frame(body)
            frm_txt.pack(fill="both", expand=True, pady=(0, 10))
            sb_txt = ttk.Scrollbar(frm_txt, orient="vertical")
            sb_txt.pack(side="right", fill="y")
            txt = _tk.Text(frm_txt, height=12, width=68,
                           font=("Segoe UI", 9), wrap="word",
                           relief="flat", state="normal",
                           background="#1e1e2e", foreground="#D8E8F0",
                           padx=10, pady=8,
                           yscrollcommand=sb_txt.set)
            # (v4.18.10) Las novedades vienen en Markdown (body de la Release): se
            # muestran con formato. Si algo falla, se ponen tal cual, como antes.
            try:
                from ui.markdown_texto import pintar as _pintar_md
                _pintar_md(txt, notas)
            except Exception:  # noqa: BLE001
                txt.delete("1.0", "end")
                txt.insert("1.0", notas)
            txt.configure(state="disabled")
            txt.pack(side="left", fill="both", expand=True)
            sb_txt.config(command=txt.yview)

        # Info descarga
        if url_descarga:
            ttk.Label(body,
                      text=f"📦  {nombre_asset}  ({size_mb} MB)" if size_mb else f"📦  {nombre_asset}",
                      font=("Segoe UI", 9),
                      foreground=LIGHT).pack(anchor="w", pady=(0, 4))

        var_err = _tk.StringVar()
        lbl_err = ttk.Label(body, textvariable=var_err,
                             font=("Segoe UI", 8, "bold"),
                             foreground="#e74c3c")
        lbl_err.pack(anchor="w")

        # Barra de progreso (oculta hasta que empieza la descarga)
        var_prog = _tk.DoubleVar(value=0)
        pb = ttk.Progressbar(body, variable=var_prog,
                             maximum=100, bootstyle="success-striped",
                             length=_UW - 36)
        lbl_prog = ttk.Label(body, text="", font=("Segoe UI", 8), foreground=LIGHT)

        ttk.Separator(upd).pack(fill="x", pady=(8, 0))
        btns = ttk.Frame(upd, padding=(18, 8, 18, 12))
        btns.pack(fill="x")

        btn_instalar = ttk.Button(btns, text="⬇️  Actualizar ahora",
                                  bootstyle="success")
        btn_despues  = ttk.Button(btns, text="Recordar después",
                                  bootstyle="secondary",
                                  command=upd.destroy)
        btn_instalar.pack(side="left", padx=(0, 8))
        btn_despues.pack(side="left")

        # Auto-cierre (2026-07-24): si nadie decide, no tiene sentido dejar
        # esta ventana abierta para siempre — se comporta como si se
        # hubiera pulsado "Recordar después" (la recomprobación a los 30
        # min ya programada más abajo se sigue encargando de volver a
        # avisar). No se cierra si ya se ha empezado a descargar el
        # instalador, para no interrumpir esa descarga a medias.
        _estado_update = {"descarga_iniciada": False}

        def _autocierre_update():
            if upd.winfo_exists() and not _estado_update["descarga_iniciada"]:
                upd.destroy()

        upd.after(5 * 60 * 1000, _autocierre_update)

        def _descargar():
            if not url_descarga:
                var_err.set("⚠  No se encontró la copia portátil en este release." if _es_portatil
                            else "⚠  No se encontró el instalador en este release.")
                return
            if _es_portatil:
                _descargar_portatil()
                return

            # (v4.18.20, petición de Víctor) Un solo clic: sin preguntar carpeta, se descarga a una
            # carpeta temporal propia, se comprueba y se instala sola (ver _instalar_ya más abajo).
            dest_dir = _carpeta_descarga_actualizacion()

            _estado_update["descarga_iniciada"] = True
            dest_path = _os.path.join(dest_dir, nombre_asset)

            btn_instalar.configure(state="disabled")
            btn_despues.configure(state="disabled")
            pb.pack(fill="x", pady=(8, 2))
            lbl_prog.pack(anchor="w")

            def _hilo_descarga():
                try:
                    sha = hashlib.sha256()
                    with urllib.request.urlopen(url_descarga, timeout=120, context=_ssl_ctx()) as r:
                        total = int(r.headers.get("Content-Length", 0))
                        descargado = 0
                        chunk = 65536
                        with open(dest_path, "wb") as f_out:
                            while True:
                                bloque = r.read(chunk)
                                if not bloque:
                                    break
                                f_out.write(bloque)
                                sha.update(bloque)
                                descargado += len(bloque)
                                if total:
                                    pct = descargado / total * 100
                                    mb_d = round(descargado / 1_048_576, 1)
                                    mb_t = round(total / 1_048_576, 1)
                                    app_root.after(0, lambda p=pct, d=mb_d, t=mb_t: (
                                        var_prog.set(p),
                                        lbl_prog.configure(
                                            text=f"Descargando... {d} / {t} MB  ({p:.0f}%)")
                                    ))

                    # ── Integridad (v4.16.9) ──
                    estado_hash = "sin_hash"
                    if url_sha:
                        with urllib.request.urlopen(url_sha, timeout=20, context=_ssl_ctx()) as rh:
                            esperado = _extraer_hash(rh.read(65536).decode("utf-8", "ignore"), nombre_asset)
                        if not esperado:
                            estado_hash = "hash_ilegible"
                        elif esperado != sha.hexdigest():
                            try:
                                _os.remove(dest_path)
                            except OSError:
                                pass
                            raise RuntimeError(
                                "El instalador descargado no coincide con el hash publicado "
                                "(SHA-256). Se ha borrado; vuelve a intentarlo.")
                        else:
                            estado_hash = "ok"

                    # ── Descarga completada: se instala sola ──
                    def _ui_descarga_ok():
                        var_prog.set(100)
                        pb.configure(bootstyle="success")
                        _txt_hash = {
                            "ok": "🔒  Integridad verificada (SHA-256).",
                            "sin_hash": "⚠  Esta versión no publica hash: integridad sin verificar.",
                            "hash_ilegible": "⚠  No se pudo leer el hash publicado: integridad sin verificar.",
                        }.get(estado_hash, "")
                        if estado_hash != "ok" and not messagebox.askyesno(
                                "Actualización",
                                f"{_txt_hash}\n\n¿Instalar igualmente la versión {tag_remoto}?",
                                parent=upd):
                            _ofrecer_manual(_txt_hash)
                            return
                        lbl_prog.configure(
                            text=f"{_txt_hash}\n⏳  Instalando… Windows puede pedir permiso. El Organizador "
                                 "se cerrará y volverá a abrirse solo, ya actualizado.")
                        upd.update_idletasks()
                        error = _instalar_ya(dest_path, tag_remoto)
                        if error:
                            _ofrecer_manual(f"⚠  {error}")

                    def _ofrecer_manual(texto):
                        """Si no se puede instalar sola (permiso de Windows denegado…), queda como
                        antes: el instalador guardado y un botón para abrir su carpeta."""
                        lbl_prog.configure(text=f"{texto}\nInstalador guardado en:\n{dest_path}")

                        def _abrir_carpeta():
                            try:
                                upd.attributes("-topmost", False)
                                _os.startfile(_os.path.dirname(dest_path))
                            except Exception:  # noqa: BLE001
                                import sys as _sys, traceback as _tb
                                print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)

                        def _reintentar():
                            error = _instalar_ya(dest_path, tag_remoto)
                            if error:
                                lbl_prog.configure(text=f"⚠  {error}\nInstalador guardado en:\n{dest_path}")

                        btn_instalar.configure(text="🔁  Instalar", state="normal", command=_reintentar)
                        btn_despues.configure(text="📂  Abrir carpeta", state="normal", command=_abrir_carpeta)

                        upd.update_idletasks()
                        _nueva_h = max(upd.winfo_reqheight() + 10, 480)
                        _sw = upd.winfo_screenwidth()
                        _sh = upd.winfo_screenheight()
                        upd.geometry(f"{_UW}x{_nueva_h}+{(_sw-_UW)//2}+{max(40,(_sh-_nueva_h)//2)}")

                    app_root.after(0, _ui_descarga_ok)

                except Exception as exc_d:
                    app_root.after(0, lambda e=str(exc_d): (
                        var_err.set(f"⚠  Error en descarga: {e}"),
                        btn_instalar.configure(state="normal"),
                        btn_despues.configure(state="normal"),
                    ))

            import threading as _thr
            _thr.Thread(target=_hilo_descarga, daemon=True,
                        name="GithubDownload").start()

        def _descargar_portatil():
            """(v4.18.54) Copia portátil: como la Consola Registro Info, sin instalador ni administrador."""
            if not _portatil.puede_actualizarse():
                var_err.set("⚠  No se puede escribir en la carpeta del Organizador: copia a mano el .exe nuevo.")
                return
            _estado_update["descarga_iniciada"] = True
            btn_instalar.configure(state="disabled")
            btn_despues.configure(state="disabled")
            pb.pack(fill="x", pady=(8, 2))
            lbl_prog.pack(anchor="w")

            def _progreso(hecho, total):
                if total:
                    pct = hecho / total * 100
                    app_root.after(0, lambda p=pct, d=round(hecho / 1_048_576, 1), t=round(total / 1_048_576, 1): (
                        var_prog.set(p), lbl_prog.configure(text=f"Descargando... {d} / {t} MB  ({p:.0f}%)")))

            def _abrir_url(url, timeout):
                req = urllib.request.Request(url, headers={"User-Agent": "OrganizadorPrincess"})
                return urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx())

            def _hilo():
                try:
                    nuevo = _portatil.descargar_y_preparar(url_descarga, url_sha, nombre_asset,
                                                          _carpeta_descarga_actualizacion(),
                                                          _portatil.ruta_exe(), _abrir_url, _progreso)
                except Exception as exc_p:  # noqa: BLE001
                    app_root.after(0, lambda e=str(exc_p): (
                        var_err.set(f"⚠  {e}"),
                        btn_instalar.configure(state="normal"),
                        btn_despues.configure(state="normal")))
                    return
                app_root.after(0, lambda n=nuevo: _aplicar_portatil(n))

            def _aplicar_portatil(nuevo):
                var_prog.set(100)
                pb.configure(bootstyle="success")
                lbl_prog.configure(text="🔒  Integridad verificada (SHA-256).\n⏳  El Organizador se cerrará y "
                                        "volverá a abrirse solo, ya actualizado.")
                upd.update_idletasks()
                try:
                    with open(_MARCA_AUTO, "w", encoding="utf-8") as f:
                        json.dump({"version": str(tag_remoto).lstrip("vV"), "fecha": datetime.now().isoformat()}, f)
                except OSError:
                    pass
                try:
                    _portatil.sustituir_exe(nuevo, _portatil.ruta_exe())
                    _portatil.lanzar(_portatil.ruta_exe())
                except Exception as exc_s:  # noqa: BLE001
                    try:
                        os.remove(_MARCA_AUTO)
                    except OSError:
                        pass
                    var_err.set(f"⚠  {exc_s}")
                    btn_instalar.configure(state="normal")
                    btn_despues.configure(state="normal")
                    return
                # La versión nueva cierra también esta al arrancar (utils/instancia_unica.py).
                app_root.after(800, lambda: os._exit(0))

            import threading as _thr
            _thr.Thread(target=_hilo, daemon=True, name="GithubDownloadPortatil").start()

        btn_instalar.configure(command=_descargar)

        # Mostrar ventana centrada
        upd.update_idletasks()
        upd.update()
        _uh = max(upd.winfo_reqheight(), 460)
        _sw = upd.winfo_screenwidth()
        _sh = upd.winfo_screenheight()
        upd.geometry(f"{_UW}x{_uh}+{(_sw-_UW)//2}+{max(40,(_sh-_uh)//2)}")
        upd.deiconify()
        upd.lift()
        upd.focus_force()
        # NO grab_set: no bloquear la agenda mientras decide

    app_root.after(0, _mostrar_dialogo_update)
    # Aunque haya actualización pendiente, recomprobar en el ciclo normal por si el usuario
    # pospuso varias veces y hay una versión aún más nueva disponible
    _programar_siguiente_check(app_root)


_MARCA_AUTO = os.path.join(os.path.dirname(CONFIG_FILE), "actualizacion_automatica.json")
# Opciones de Inno Setup para la instalación de un clic: solo la barra de progreso, sin preguntas.
# El instalador cierra el Organizador (KillOrganizador) y lo vuelve a abrir al terminar
# ([Run] con Check: WizardSilent en el .iss, desde la v4.18.20).
_ARGS_INSTALADOR = "/SILENT /SUPPRESSMSGBOXES /NORESTART /SP-"


def _carpeta_descarga_actualizacion():
    """Carpeta temporal del usuario para el instalador; se vacía en cada descarga."""
    import tempfile
    carpeta = os.path.join(tempfile.gettempdir(), "OrganizadorPrincess_actualizacion")
    os.makedirs(carpeta, exist_ok=True)
    for f in os.listdir(carpeta):
        try:
            os.remove(os.path.join(carpeta, f))
        except OSError:
            pass
    return carpeta


def borrar_instaladores_aplicados(version_actual, carpeta=None):
    """(v4.18.36) Al arrancar: borra de la carpeta de descarga (%TEMP%\\OrganizadorPrincess_actualizacion)
    los instaladores de esta versión o anteriores, que ya están instalados (~40 MB cada uno). Antes se
    quedaban ahí hasta la actualización siguiente. Un instalador de una versión MÁS NUEVA (descargado
    pero sin instalar, p. ej. se canceló el permiso de Windows) se deja. Nunca lanza.
    Devuelve (borrados, pendientes): nombres borrados y los que no se pudieron borrar."""
    import re as _re
    import tempfile
    carpeta = carpeta or os.path.join(tempfile.gettempdir(), "OrganizadorPrincess_actualizacion")
    borrados, pendientes = [], []
    try:
        nombres = os.listdir(carpeta)
    except OSError:
        return borrados, pendientes
    actual = _parse_version(version_actual)
    for nombre in sorted(nombres):
        m = _re.match(r"^OrganizadorPrincess_Setup_v?([\d.]+?)\.exe(\.sha256)?$", nombre, _re.I)
        if not m or _parse_version(m.group(1)) > actual:
            continue
        try:
            os.remove(os.path.join(carpeta, nombre))
            borrados.append(nombre)
        except OSError:
            pendientes.append(nombre)
    return borrados, pendientes


def _limpiar_entorno_pyinstaller(entorno=None):
    """(v4.18.40) Quita del entorno las variables internas de PyInstaller de ESTE proceso (_PYI_*,
    _MEIPASS2) y pone PYINSTALLER_RESET_ENVIRONMENT=1 (PyInstaller 6.9+: «arranque limpio»).
    El instalador hereda el entorno y se lo pasa al Organizador nuevo que abre al terminar; con esas
    variables, el nuevo buscaba Python en la carpeta temporal _MEI… del viejo, que ya se había
    borrado al cerrarse: «Failed to load Python DLL …\\_MEI…\\python312.dll» (v4.18.38). Se cambia el
    entorno del propio proceso porque os.startfile no admite otro."""
    entorno = os.environ if entorno is None else entorno
    for clave in [k for k in entorno if k.startswith("_PYI") or k == "_MEIPASS2"]:
        entorno.pop(clave, None)
    entorno["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return entorno


def _instalar_ya(ruta_instalador, version):
    """Lanza el instalador ya comprobado. Devuelve None si se lanzó, o el motivo si no.
    Se usa ShellExecute (os.startfile) y no subprocess: el instalador pide permisos de
    administrador y solo así Windows muestra la pregunta de permiso (UAC)."""
    try:
        with open(_MARCA_AUTO, "w", encoding="utf-8") as f:
            json.dump({"version": str(version).lstrip("vV"), "fecha": datetime.now().isoformat()}, f)
    except OSError:
        pass
    try:
        _limpiar_entorno_pyinstaller()
        os.startfile(ruta_instalador, "open", _ARGS_INSTALADOR)
        return None
    except OSError as e:
        try:
            os.remove(_MARCA_AUTO)
        except OSError:
            pass
        if getattr(e, "winerror", None) == 1223:
            return "Se canceló el permiso de Windows. Pulsa «Instalar» para volver a intentarlo."
        return f"No se pudo abrir el instalador: {e}"
    except Exception as e:  # noqa: BLE001
        return f"No se pudo abrir el instalador: {e}"


def actualizacion_automatica_aplicada(version_anterior):
    """Al arrancar una versión nueva instalada con «Actualizar ahora» no se pregunta cómo
    instalarla: se hace «Solo actualizar versión» (lo normal) y se devuelve True.
    Solo si la marca es de esta misma versión y de hace menos de un día."""
    try:
        with open(_MARCA_AUTO, encoding="utf-8") as f:
            marca = json.load(f)
    except (OSError, ValueError):
        return False
    try:
        os.remove(_MARCA_AUTO)
    except OSError:
        pass
    try:
        reciente = (datetime.now() - datetime.fromisoformat(marca.get("fecha", ""))).total_seconds() < 86400
    except (TypeError, ValueError):
        reciente = False
    if not reciente or _parse_version(marca.get("version", "")) != _parse_version(APP_VERSION):
        return False
    _aplicar_solo_actualizacion(version_anterior)
    return True


def _lanzar_check_update(app_root):
    """Lanza la comprobación en hilo daemon para no bloquear el arranque."""
    import threading as _thr
    _thr.Thread(
        target=_check_update_github,
        args=(app_root,),
        daemon=True,
        name="GitHubUpdateCheck"
    ).start()


def _check_version_reset():
    """Compara APP_VERSION con la version guardada en version.json.
    Solo detecta si hay version nueva; NO modifica ningun archivo.
    Devuelve (True, version_anterior) si hay nueva version,
             (False, APP_VERSION)      si todo esta al dia.
    """
    version_guardada = ""
    if os.path.exists(VERSION_FILE):
        try:
            with open(VERSION_FILE, "r", encoding="utf-8") as f:
                data = json.loads(f.read().strip())
                version_guardada = data.get("version", "")
        except Exception:
            version_guardada = ""

    if version_guardada == APP_VERSION:
        return False, APP_VERSION

    return True, version_guardada  # version anterior (puede ser "")


def _parse_version(tag: str):
    """Convierte 'v4.2.1' → (4, 2, 1) para comparación numérica."""
    import re
    nums = re.findall(r"\d+", tag)
    return tuple(int(n) for n in nums)


def _aplicar_solo_actualizacion(version_anterior):
    """Actualiza version.json sin tocar config ni agenda.
    Hace backup de config.json por seguridad.
    """
    import shutil
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ver_tag = version_anterior or "anterior"

    # Backup de config (por si acaso)
    if os.path.exists(CONFIG_FILE):
        backup_cfg = CONFIG_FILE.replace(
            "config.json", f"config_backup_{ver_tag}_{ts}.json"
        )
        try:
            shutil.copy2(CONFIG_FILE, backup_cfg)
        except Exception:  # noqa: BLE001
            import sys as _sys, traceback as _tb
            print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)

    # Solo actualizamos version.json
    try:
        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            json.dump({"version": APP_VERSION}, f, indent=4)
    except Exception:  # noqa: BLE001
        import sys as _sys, traceback as _tb
        print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)


def _aplicar_instalacion_desde_cero(version_anterior, backup_agenda=False, ruta_backup=None):
    """Instalacion completa: resetea config, borra agenda (con backup opcional),
    y actualiza version.json.
    """
    import shutil
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ver_tag = version_anterior or "anterior"
    appdata_dir = os.path.dirname(CONFIG_FILE)

    # 1) Backup y borrado de agenda si el usuario lo pidio
    if backup_agenda and os.path.exists(AGENDA_FILE):
        carpeta_dest = ruta_backup if ruta_backup else appdata_dir
        nombre_bk    = f"agenda_backup_{ver_tag}_{ts}.json"
        dest         = os.path.join(carpeta_dest, nombre_bk)
        try:
            shutil.copy2(AGENDA_FILE, dest)
        except Exception:  # noqa: BLE001
            import sys as _sys, traceback as _tb
            print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
        # Borrar agenda
        try:
            os.remove(AGENDA_FILE)
        except Exception:  # noqa: BLE001
            import sys as _sys, traceback as _tb
            print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
    elif os.path.exists(AGENDA_FILE):
        # Sin backup: solo borramos
        try:
            os.remove(AGENDA_FILE)
        except Exception:  # noqa: BLE001
            import sys as _sys, traceback as _tb
            print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)

    # 2) Backup de config.json si existe
    if os.path.exists(CONFIG_FILE):
        backup_cfg = CONFIG_FILE.replace(
            "config.json", f"config_backup_{ver_tag}_{ts}.json"
        )
        try:
            shutil.copy2(CONFIG_FILE, backup_cfg)
        except Exception:  # noqa: BLE001
            import sys as _sys, traceback as _tb
            print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)

    # 3) Resetear config.json a vacio
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4)
    except Exception:  # noqa: BLE001
        import sys as _sys, traceback as _tb
        print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)

    # 4) Guardar nueva version en version.json
    try:
        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            json.dump({"version": APP_VERSION}, f, indent=4)
    except Exception:  # noqa: BLE001
        import sys as _sys, traceback as _tb
        print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
