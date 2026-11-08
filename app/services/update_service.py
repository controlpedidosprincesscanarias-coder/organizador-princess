"""
services/update_service.py
Comprobación de actualizaciones en GitHub y diálogos de instalación.
Extraído de main_agenda.py en Fase 2 del sprint de estabilización.

Uso desde main_agenda:
    from services.update_service import _lanzar_check_update, _dialogo_nueva_version_safe
    _lanzar_check_update(app)
"""
# Nota: este módulo usa tkinter/ttkbootstrap directamente porque toda la UI
# de actualización está acoplada a los diálogos. Se desacoplará en Fase 3.

import os
import ttkbootstrap as ttk                              # ANTI-REGRESION: era global de main_agenda
from tkinter import messagebox, filedialog, StringVar   # ANTI-REGRESION: idem
from db.sqlite import CONFIG_FILE, VERSION_FILE, AGENDA_FILE  # ANTI-REGRESION: AGENDA_FILE faltaba
from ui.assets import _apply_icon                       # ANTI-REGRESION: usada en todos los Toplevel
# Inyectados desde main_agenda al arrancar
APP_VERSION  = ""   # se sobreescribe desde main_agenda
GITHUB_REPO  = ""   # se sobreescribe desde main_agenda

# Constante de color — ANTI-REGRESION: era global de main_agenda
LIGHT = "#D8E8F0"
import sys
import json
import threading
from datetime import datetime
import ssl
import socket
import shutil
import tempfile
import zipfile
import urllib.request
import urllib.error
import subprocess
import traceback


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
# silencio (con log) y sigue el ciclo normal de 30 min. Si el reintento
# también falla, entonces sí se muestra el diálogo — con el error de ese
# segundo intento — y a partir de ahí se retoma el ciclo normal de 30 min
# (el propio reintento, al ejecutar _check_update_github de nuevo, ya se
# encarga de reprogramarse).
_GRACIA_UPDATE_SEGUNDOS = 5 * 60

_gracia_update_en_curso = False
_gracia_update_lock     = threading.Lock()


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
        Contexto SSL tolerante al proxy corporativo con SSL inspection.
        Intento 1: almacén de certificados de Windows (lo correcto).
        Intento 2: sin verificación (fallback para PCs con proxy muy restrictivo).
        En PCs sin proxy el contexto por defecto funciona igual que siempre.
        """
        try:
            ctx = _ssl.create_default_context()
            ctx.load_default_certs()   # usa el almacén de Windows
            return ctx
        except Exception:
            return _ssl._create_unverified_context()

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
            app_root.after(30 * 60 * 1000, lambda: _lanzar_check_update(app_root))
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
            app_root.after(30 * 60 * 1000, lambda: _lanzar_check_update(app_root))
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
            app_root.after(30 * 60 * 1000, lambda: _lanzar_check_update(app_root))
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
            _ulog("Ya al día — reintento en 30 min")
            app_root.after(30 * 60 * 1000, lambda: _lanzar_check_update(app_root))
            return
        _ulog(f"Actualización disponible: {APP_VERSION} → {tag_remoto}")
    except Exception as exc:
        _ulog(f"ERROR comparando versiones: {exc}")
        return

    # Buscar el asset instalador (.exe)
    assets = data.get("assets", [])
    asset_exe = next(
        (a for a in assets if a.get("name", "").lower().endswith(".exe")),
        None
    )
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

        btn_instalar = ttk.Button(btns, text="⬇️  Descargar actualización",
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
                var_err.set("⚠  No se encontró el instalador en este release.")
                return

            # Pedir carpeta de destino (por defecto Descargas del usuario)
            import tkinter.filedialog as _fd
            import pathlib as _pl
            carpeta_descargas = str(_pl.Path.home() / "Downloads")
            dest_dir = _fd.askdirectory(
                title="Selecciona dónde guardar el instalador",
                initialdir=carpeta_descargas,
                parent=upd)
            if not dest_dir:
                return  # usuario canceló

            _estado_update["descarga_iniciada"] = True
            dest_path = _os.path.join(dest_dir, nombre_asset)

            btn_instalar.configure(state="disabled")
            btn_despues.configure(state="disabled")
            pb.pack(fill="x", pady=(8, 2))
            lbl_prog.pack(anchor="w")

            def _hilo_descarga():
                try:
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

                    # ── Descarga completada ──
                    def _ui_descarga_ok():
                        var_prog.set(100)
                        pb.configure(bootstyle="success")
                        lbl_prog.configure(
                            text=f"✅  Instalador guardado en:\n{dest_path}")

                        # Mensaje informativo
                        lbl_info = ttk.Label(
                            body,
                            text=("Para completar la actualización, abre el archivo descargado\n"
                                  "y sigue los pasos del instalador. Puedes cerrar esta ventana."),
                            font=("Segoe UI", 8),
                            foreground="#adb5bd",
                            justify="left")
                        lbl_info.pack(anchor="w", pady=(6, 0))

                        # Botón abrir carpeta
                        def _abrir_carpeta():
                            try:
                                import os as _os3
                                upd.attributes("-topmost", False)
                                # Abrir directamente la carpeta donde está el instalador
                                _os3.startfile(_os3.path.dirname(dest_path))
                            except Exception:  # noqa: BLE001
                                import sys as _sys, traceback as _tb
                                print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)

                        btn_instalar.configure(
                            text="📂  Abrir carpeta de descarga",
                            state="normal",
                            command=_abrir_carpeta)
                        btn_despues.configure(
                            text="Cerrar",
                            state="normal",
                            command=upd.destroy)

                        # Redimensionar ventana
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
    # Aunque haya actualización pendiente, recomprobar en 30 minutos por si el usuario
    # pospuso varias veces y hay una versión aún más nueva disponible
    app_root.after(30 * 60 * 1000, lambda: _lanzar_check_update(app_root))


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


    def _dialogo_nueva_version():
        """Ventana modal de decision de instalacion de nueva version."""

        dlg = ttk.Toplevel(app)   # FIX: padre explícito para evitar fallo silencioso en after()
        dlg.withdraw()   # ocultar hasta posicionar correctamente
        dlg.title("Nueva version detectada  " + APP_VERSION)
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        _apply_icon(dlg)
        dlg.transient(app)

        # ── Cabecera ─────────────────────────────────────────────
        hdr = ttk.Frame(dlg, bootstyle="warning")
        hdr.pack(fill="x")
        _hdr_inner = ttk.Frame(hdr, bootstyle="warning")
        _hdr_inner.pack(fill="x", padx=16, pady=12)
        ttk.Label(
            _hdr_inner,
            text="🆕  Nueva version  " + APP_VERSION,
            font=("Segoe UI", 13, "bold"),
            bootstyle="inverse-warning",
        ).pack(anchor="w")
        ver_tag = _version_anterior or "desconocida"
        ttk.Label(
            _hdr_inner,
            text=f"Version anterior: {ver_tag}",
            font=("Segoe UI", 9),
            bootstyle="inverse-warning",
        ).pack(anchor="w", pady=(2, 0))

        ttk.Separator(dlg).pack(fill="x")

        # ── Cuerpo ───────────────────────────────────────────────
        body = ttk.Frame(dlg)
        body.pack(fill="x", padx=18, pady=(14, 6))

        ttk.Label(
            body,
            text="¿Como deseas instalar la nueva version?",
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        # Radio: tipo de instalacion
        var_modo = StringVar(value="actualizar")

        frm_r1 = ttk.Frame(body)
        frm_r1.pack(fill="x", pady=(0, 4))
        ttk.Radiobutton(
            frm_r1,
            text="  Solo actualizar version  (mantiene configuracion y agenda)",
            variable=var_modo,
            value="actualizar",
            bootstyle="warning",
        ).pack(anchor="w")

        frm_r2 = ttk.Frame(body)
        frm_r2.pack(fill="x", pady=(0, 6))
        ttk.Radiobutton(
            frm_r2,
            text="  Instalacion desde cero  (borra configuracion Y agenda)",
            variable=var_modo,
            value="desde_cero",
            bootstyle="danger",
        ).pack(anchor="w")

        ttk.Separator(body).pack(fill="x", pady=(6, 10))

        # Sub-bloque: opciones de copia de seguridad (solo visible en "desde_cero")
        # FIX Python 3.14 + ttkbootstrap: LabelFrame no acepta padding= como kwarg.
        # Se usa un Frame interior con padx/pady para replicar el mismo espaciado.
        frm_backup = ttk.LabelFrame(body, text=" Copia de seguridad de agenda (vacaciones y festivos incluidos) ")
        frm_backup.pack(fill="x", pady=(0, 8))
        _frm_backup_inner = ttk.Frame(frm_backup)
        _frm_backup_inner.pack(fill="x", padx=10, pady=8)

        var_backup = StringVar(value="si")
        ttk.Radiobutton(
            _frm_backup_inner,
            text="  Si, hacer copia de seguridad antes de borrar",
            variable=var_backup,
            value="si",
            bootstyle="success",
        ).pack(anchor="w", pady=(0, 4))
        ttk.Radiobutton(
            _frm_backup_inner,
            text="  No, borrar sin copia",
            variable=var_backup,
            value="no",
            bootstyle="danger",
        ).pack(anchor="w")

        ttk.Label(
            _frm_backup_inner,
            text="Carpeta destino de la copia:",
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(10, 2))

        frm_ruta = ttk.Frame(_frm_backup_inner)
        frm_ruta.pack(fill="x")

        _appdata_dir = os.path.dirname(CONFIG_FILE)
        var_ruta_bk = StringVar(value=_appdata_dir)

        ent_ruta = ttk.Entry(frm_ruta, textvariable=var_ruta_bk, width=42)
        ent_ruta.pack(side="left", fill="x", expand=True)

        def _elegir_carpeta():
            carpeta = filedialog.askdirectory(
                title="Elegir carpeta para la copia de seguridad",
                initialdir=var_ruta_bk.get(),
                parent=dlg,
            )
            if carpeta:
                var_ruta_bk.set(carpeta)

        ttk.Button(
            frm_ruta,
            text="  📁  ",
            bootstyle="secondary-outline",
            command=_elegir_carpeta,
        ).pack(side="left", padx=(6, 0))

        # Habilitar/deshabilitar sub-bloque segun modo
        def _toggle_backup(*_):
            estado = "normal" if var_modo.get() == "desde_cero" else "disabled"
            # Los widgets estan en _frm_backup_inner (nivel 1) y sus hijos (nivel 2)
            for w in _frm_backup_inner.winfo_children():
                try:
                    w.configure(state=estado)
                except Exception:
                    pass  # UI — ignorar silenciosamente
                for ww in w.winfo_children():
                    try:
                        ww.configure(state=estado)
                    except Exception:
                        pass  # UI — ignorar silenciosamente

        var_modo.trace_add("write", _toggle_backup)
        _toggle_backup()  # estado inicial

        ttk.Separator(dlg).pack(fill="x")

        # ── Pie con botones ───────────────────────────────────────
        pie = ttk.Frame(dlg)
        pie.pack(fill="x", padx=18, pady=(10, 12))

        def _confirmar():
            modo = var_modo.get()
            if modo == "actualizar":
                _aplicar_solo_actualizacion(_version_anterior)
                dlg.destroy()
                messagebox.showinfo(
                    "Version actualizada",
                    f"Version actualizada a {APP_VERSION}.\n\n"
                    "Tu configuracion y agenda permanecen intactas.\n"
                    "Usa 'Importar config' en el panel Admin si necesitas ajustar rutas.",
                    parent=app,
                )
                app.after(300, _mostrar_saludo_diario)
            else:
                # Desde cero
                hacer_backup = var_backup.get() == "si"
                ruta_bk      = var_ruta_bk.get().strip() or _appdata_dir

                if hacer_backup:
                    # Verificar que la carpeta existe o es creable
                    if not os.path.isdir(ruta_bk):
                        messagebox.showerror(
                            "Carpeta no valida",
                            f"La carpeta indicada no existe:\n{ruta_bk}\n\n"
                            "Selecciona una carpeta valida antes de continuar.",
                            parent=dlg,
                        )
                        return

                    confirmar = messagebox.askyesno(
                        "Confirmar instalación desde cero",
                        f"Se realizará una copia de seguridad de la agenda en:\n\n"
                        f"  {ruta_bk}\n\n"
                        "A continuación se borrarán la configuración y la agenda.\n\n"
                        "⚠️  La aplicación se cerrará automáticamente al terminar.\n"
                        "Deberás volver a abrirla para que los cambios surtan efecto.\n\n"
                        "¿Deseas continuar?",
                        parent=dlg,
                    )
                else:
                    confirmar = messagebox.askyesno(
                        "Confirmar instalación desde cero",
                        "Se borrarán la configuración Y la agenda SIN copia de seguridad.\n\n"
                        "⚠️  Esta acción no se puede deshacer.\n\n"
                        "La aplicación se cerrará automáticamente al terminar.\n"
                        "Deberás volver a abrirla para que los cambios surtan efecto.\n\n"
                        "¿Deseas continuar?",
                        icon="warning",
                        parent=dlg,
                    )

                if not confirmar:
                    return

                _aplicar_instalacion_desde_cero(
                    _version_anterior,
                    backup_agenda=hacer_backup,
                    ruta_backup=ruta_bk if hacer_backup else None,
                )
                dlg.destroy()

                msg_ok = f"✅  Instalación desde cero completada ({APP_VERSION}).\n\n"
                if hacer_backup:
                    msg_ok += f"📁  Copia de seguridad guardada en:\n     {ruta_bk}\n\n"
                msg_ok += (
                    "La configuración y la agenda han sido reiniciadas.\n\n"
                    "⚠️  La aplicación se cerrará ahora.\n"
                    "Vuelve a abrirla para que todos los cambios surtan efecto."
                )
                messagebox.showinfo("Instalación completada — reinicio necesario", msg_ok, parent=app)

                # Cerrar la aplicación para que los cambios surtan efecto al reabrir
                detener_bridge()
                app.destroy()

        def _cancelar():
            # El usuario no elige; marcamos la version igual para no volver a preguntar
            _aplicar_solo_actualizacion(_version_anterior)
            dlg.destroy()
            app.after(300, _mostrar_saludo_diario)

        ttk.Button(
            pie, text="  Cancelar  ",
            bootstyle="secondary",
            command=_cancelar,
        ).pack(side="right", padx=(8, 0))

        ttk.Button(
            pie, text="  Confirmar  ",
            bootstyle="warning",
            command=_confirmar,
        ).pack(side="right")

             # ── Posicionar y mostrar ───────────────────────────
        # Ancho minimo garantizado; la ventana esta oculta (withdraw)
        # hasta que Tk calcula el tamano real con update() completo.
        # Luego se posiciona en el lado izquierdo (~60 px del borde)
        # centrada verticalmente, sin solaparse con el saludo diario.
        _MIN_W = 480
        dlg.minsize(_MIN_W, 1)

        dlg.update_idletasks()
        dlg.update()   # renderizado completo antes de medir

        _sw = app.winfo_screenwidth()
        _sh = app.winfo_screenheight()

        _w = max(dlg.winfo_width(), dlg.winfo_reqwidth(), _MIN_W)
        _h = max(dlg.winfo_height(), dlg.winfo_reqheight())

        # X: ~60 px del borde izquierdo (~2-3 dedos)
        _x = 60
        # Y: centrado vertical, minimo 40 px del borde superior
        _y = max(40, (_sh - _h) // 2)

        dlg.geometry(f"{_w}x{_h}+{_x}+{_y}")
        dlg.deiconify()   # mostrar ya en posicion correcta
        dlg.lift()
        dlg.focus_force()
        dlg.grab_set()


    def _dialogo_nueva_version_safe():
        """Wrapper con captura de errores para que el after() no muera en silencio."""
        try:
            _dialogo_nueva_version()
        except Exception as _exc:
            import traceback
            _log_path = os.path.join(os.path.dirname(CONFIG_FILE), "version_error.log")
            with open(_log_path, "w", encoding="utf-8") as _f:
                traceback.print_exc(file=_f)
            messagebox.showerror(
                "Error al mostrar dialogo de version",
                f"Ha ocurrido un error inesperado:\n\n{_exc}\n\n"
                f"Detalle guardado en:\n{_log_path}",
                parent=app,
            )


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
