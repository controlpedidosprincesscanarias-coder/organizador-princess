import os
import sys
import logging
import threading
from datetime import datetime
import ttkbootstrap as ttk
import tkinter as tk
from ttkbootstrap.constants import Wrap, NO, YES  # noqa: F401
from tkinter import filedialog, StringVar, messagebox
from PIL import Image, ImageTk
from pedidos_agenda_bridge import iniciar_bridge_pedidos, detener_bridge

# ── Módulos extraídos en Fase 2 ───────────────────────────────────────────────
import sys as _sys; _sys.path.insert(0, "app")  # asegura que app/ es importable
from db.sqlite import (
    CONFIG_FILE, load_config, save_config, load_agenda, save_agenda,
    get_nombre_usuario, update_nombre_usuario_db, tiene_nombre_configurado, get_bridge_credentials,
    update_bridge_credentials,
)
from utils.sonido import _reproducir_sonido_aviso
import negocio.alertas as _alertas_mod
from negocio.alertas import (
    monitor_avisos, mostrar_alerta,
    poll_alertas,   # ANTI-REGRESION: poller thread-safe para console=False de PyInstaller
)
from services.update_service import (
    _lanzar_check_update, _check_version_reset,
    _aplicar_solo_actualizacion, _aplicar_instalacion_desde_cero,
    # _dialogo_nueva_version and _dialogo_nueva_version_safe remain as nested
    # functions in main_agenda (they use local closure vars)
)
import services.update_service as _update_mod
import services.admin_auth as admin_auth

# ── Módulos extraídos en Fase 3A ──────────────────────────────────────────────
from ui.assets import (
    get_embedded_logo, get_crown_tk, _apply_icon,
)
from ui.saludo import mostrar_saludo_diario
from ui.agenda import abrir_agenda as _abrir_agenda_ventana
from ui.calendario import abrir_calendario as _abrir_calendario_ventana
from ui.agenda_helpers import get_nombre
from ui.importexport import (exportar_config, importar_config,
                             exportar_agenda, importar_agenda)
from ui.ventana_config import (_ventana_config, _abrir_submenu)
from ui.ventana_chat import _ventana_chat
import ui.ventana_chat as _ventana_chat_mod
import ui.chat_popup as _chat_popup_mod
from services.chat_client import get_chat_client, EVT_NUEVO_MENSAJE
from context import AppContext
from utils.instancia_unica import asegurar_instancia_unica, liberar_instancia_actual
# ─────────────────────────────────────────────────────────────────────────────

# ── INSTANCIA ÚNICA ───────────────────────────────────────────────────────────
# Si ya hay otra instancia de esta app en ejecución, se cierra automáticamente
# antes de continuar con esta. Debe ejecutarse cuanto antes, antes de crear
# la ventana principal (app = ttk.Window(...) más abajo) y sin ralentizar
# el arranque perceptiblemente.
# ANTI-REGRESION: no eliminar — evita popups duplicados y escrituras
# concurrentes sobre agenda.json / usuarios.db cuando la app queda abierta
# sin querer en varias sesiones/lanzamientos.
asegurar_instancia_unica()

import atexit
atexit.register(liberar_instancia_actual)  # red de seguridad para salidas no contempladas
# ─────────────────────────────────────────────────────────────────────────────



# ─────────────────────────────────────────────────────────────────────────────


# ---------------------------------------------------
# FIX Python 3.14 + ttkbootstrap — msgcat
# "invalid command name ::msgcat::mcmset" al arrancar:
# ttkbootstrap intenta cargar localizaciones Tcl antes
# de que msgcat este disponible. Se neutraliza la funcion
# sin perder funcionalidad (solo afecta a textos internos
# de dialogos ttkbootstrap que no se usan en esta app).
# ---------------------------------------------------
import ttkbootstrap.localization as _ttkl
_ttkl.initialize_localities = lambda *a, **kw: None


# Nombre del usuario actual - se resuelve una sola vez al arrancar
NOMBRE_USUARIO_ACTUAL = get_nombre_usuario()

# ---------------------------------------------------
# LOGO CABECERA incrustado en base64
# ---------------------------------------------------

GOLD  = "#C9A84C"
LIGHT = "#D8E8F0"
NUM_OPCIONES = 30
NUM_ACCESOS_RAPIDOS = 6
MARGEN = 44   # px aprox. 2 dedos en cada borde
APP_VERSION  = "v4.18.06"   # ← actualizar en cada release (debe coincidir con el tag del release en GitHub)
GITHUB_REPO  = "controlpedidosprincesscanarias-coder/organizador-princess"  # repo de releases
_update_mod.APP_VERSION = APP_VERSION  # propagar a services/update_service.py
_update_mod.GITHUB_REPO = GITHUB_REPO




# Caché global de corona para evitar GC


# Icono global — persiste en memoria para todas las ventanas (evita GC)




# ---------------------------------------------------
# ── AUTO-ACTUALIZACIÓN DESDE GITHUB RELEASES ─────────────────────────────────
#
# Al arrancar, consulta la API pública de GitHub:
#   GET https://api.github.com/repos/{GITHUB_REPO}/releases/latest
#
# Si el tag del último release es mayor que APP_VERSION, muestra un diálogo
# que descarga el instalador .exe del asset, lo guarda en %TEMP% y lo lanza.
# El instalador cierra la agenda automáticamente (KillOrganizador en el .iss).
#
# La comprobación se hace en un hilo para no bloquear el arranque.
# ─────────────────────────────────────────────────────────────────────────────







# CONTROL DE VERSION — deteccion pasiva al arrancar.
# La decision de instalacion (desde cero o solo actualizar)
# se toma interactivamente en la UI, despues de cargar config.
# ---------------------------------------------------






# Ejecutar la comprobacion ANTES de cargar config.
# Si hay nueva version, config se carga tal cual (sin reset todavia);
# el usuario decidira que hacer desde la UI.
_nueva_version_detectada, _version_anterior = _check_version_reset()

config = load_config()



# ── Helpers de formato de fecha ─────────────────────────────────────────────


agenda_data = load_agenda()

btn_labels  = {}   # opcion_key -> StringVar
btn_widgets = {}   # opcion_key -> Button widget

ar_labels  = {}   # ar_key -> StringVar   (accesos rápidos del header)
ar_widgets = {}   # ar_key -> Button widget



from utils.rutas import _lanzar_ruta  # ANTI-REGRESION: movida a utils/rutas.py (compartida con ventana_config)

def ejecutar_opcion(opcion, idx):
    sub_cfg = config.get(opcion, {}).get("submenu", {})
    if sub_cfg.get("enabled"):
        _abrir_submenu(ctx, opcion, idx)
        return
    if opcion not in config or "ruta" not in config[opcion]:
        _ventana_config(ctx, opcion, idx, nuevo=True)
        return
    _lanzar_ruta(config[opcion]["ruta"], config[opcion].get("tipo", "aplicacion"))

def ejecutar_ar(ar_key, idx):
    sub_cfg = config.get(ar_key, {}).get("submenu", {})
    if sub_cfg.get("enabled"):
        _abrir_submenu(ctx, ar_key, idx)
        return
    if ar_key not in config or "ruta" not in config[ar_key]:
        _ventana_config(ctx, ar_key, idx, nuevo=True,
                        titulo_display=f"Acceso Rápido {idx}")
        return
    _lanzar_ruta(config[ar_key]["ruta"], config[ar_key].get("tipo", "aplicacion"))

# =========================================================
# VENTANA DE CONFIGURACION — 3 tipos simples
# =========================================================
# icono · etiqueta · valor · placeholder · usa explorar
_TIPOS = [
    ("📁", "Carpeta de red",    "carpeta",    r"\\servidor\carpeta",  True),
    ("🌐", "Página web",        "web",        "https://",             False),
    ("⚙️",  "Archivo ejecutable","ejecutable", r"C:\ruta\programa.exe",True),
]


# =========================================================
# VENTANA ADMIN DE SUBOPCIONES
# =========================================================


# =========================================================
# VENTANA DE CONFIGURACION DE SUBOPCION
# =========================================================


# =========================================================
# VENTANA DE SUBMENU (runtime — al pulsar botón principal)
# =========================================================
_submenu_activo = None   # referencia a la ventana de submenú abierta






# ANTI-REGRESION: antes había credenciales ADMIN_USER / ADMIN_PASSWORD
# hardcodeadas aquí. Sustituidas por el sistema sin hardcode de
# services/admin_auth.py — ver _ventana_login_admin() más abajo.
# =========================================================
# MÓDULO DE AGENDA
# =========================================================
def abrir_agenda():
    """Abre la ventana «Agenda de Avisos» (código en app/ui/agenda.py)."""
    _abrir_agenda_ventana(ctx)












# =========================================================
# MÓDULO CALENDARIO + VACACIONES
# =========================================================
# (v4.18.08) La ventana Calendario y sus constantes están en app/ui/calendario.py










# =========================================================
# MÓDULO CORREO — FESTIVOS Y VACACIONES  © VAMA 2026
# =========================================================







def abrir_calendario():
    """Abre la ventana «Calendario» (código en app/ui/calendario.py)."""
    _abrir_calendario_ventana(ctx)





_admin_autenticado = False   # sesión activa mientras la app esté abierta

def _ventana_login_admin(on_success):
    """Diálogo de autenticación antes de abrir el panel de administración.

    Sin credenciales hardcodeadas (ver services/admin_auth.py):
      · El usuario de login es SIEMPRE el usuario de Windows (no editable).
      · Si ese usuario ya existe en Control de Pedidos, se valida la
        contraseña contra la plataforma en cada intento.
      · Si no existe, se muestra un formulario de alta (nombre a mostrar +
        contraseña + repetir contraseña); se guarda cifrado localmente
        (hash+salt) y se notifica a Control de Pedidos para que un
        administrador cree la cuenta real.
      · Máximo 3 intentos fallidos → bloqueo temporal.
    """
    from tkinter import StringVar as _SV

    uwin = admin_auth.get_windows_user()

    dlg = ttk.Toplevel()
    dlg.withdraw()
    dlg.title("Acceso Administración")
    dlg.resizable(False, False)
    dlg.attributes("-topmost", True)
    _apply_icon(dlg)

    _dw = 500
    _sw = dlg.winfo_screenwidth()
    _sh = dlg.winfo_screenheight()

    # ── Cabecera ─────────────────────────────────────────────
    hdr = ttk.Frame(dlg, padding=(20, 16, 20, 8))
    hdr.pack(fill="x")
    ttk.Label(hdr, text="⚙  Administración",
              font=("Segoe UI", 13, "bold")).pack(anchor="w")
    var_subtitulo = _SV(value="Comprobando tu usuario en Control de Pedidos…")
    ttk.Label(hdr, textvariable=var_subtitulo,
              font=("Segoe UI", 9), foreground=LIGHT,
              wraplength=400).pack(anchor="w", pady=(4, 0))
    ttk.Separator(dlg).pack(fill="x")

    body = ttk.Frame(dlg, padding=(20, 14, 20, 0))
    body.pack(fill="both", expand=True)

    # Usuario de Windows — siempre visible, nunca editable
    row_u = ttk.Frame(body)
    row_u.pack(fill="x", pady=(0, 10))
    ttk.Label(row_u, text="Usuario Windows:", font=("Segoe UI", 9),
              width=16, anchor="w").pack(side="left")
    ttk.Label(row_u, text=uwin, font=("Consolas", 10, "bold"),
              foreground="#C9A84C").pack(side="left")

    # Contenedor dinámico: cambia entre modo "login" y modo "alta"
    dyn = ttk.Frame(body)
    dyn.pack(fill="x")

    var_toggle_txt = _SV(value="")
    lbl_toggle = ttk.Label(body, textvariable=var_toggle_txt,
                           font=("Segoe UI", 8, "underline"),
                           foreground="#5aa9e6", cursor="hand2")
    lbl_toggle.pack(anchor="w", pady=(8, 0))

    ttk.Separator(dlg).pack(fill="x", padx=0, pady=(10, 0))
    frame_btns = ttk.Frame(dlg, padding=(20, 8, 20, 12))
    frame_btns.pack(fill="x")

    _refs = {"btn_principal": None, "modo": None}

    def _reposicionar():
        dlg.update_idletasks()
        _dh = dlg.winfo_reqheight() + 10
        dlg.geometry(f"{_dw}x{_dh}+{(_sw - _dw)//2}+{(_sh - _dh)//2}")

    def _limpiar_dyn():
        for w in dyn.winfo_children():
            w.destroy()
        for w in frame_btns.winfo_children():
            w.destroy()

    # ── Modo LOGIN: el usuario ya existe (o no se pudo confirmar) ──────
    def _modo_login():
        _limpiar_dyn()
        _refs["modo"] = "login"
        var_subtitulo.set("Introduce tu contraseña de Control de Pedidos.")
        var_toggle_txt.set("¿Todavía no tienes cuenta en Control de Pedidos?  Crear acceso")

        ttk.Label(dyn, text="Contraseña:", font=("Segoe UI", 9)).pack(anchor="w")
        var_pass = _SV()
        entry_pass = ttk.Entry(dyn, textvariable=var_pass,
                               font=("Segoe UI", 10), show="●")
        entry_pass.pack(fill="x", pady=(3, 0))

        var_err = _SV(value="")
        ttk.Label(dyn, textvariable=var_err, font=("Segoe UI", 8, "bold"),
                  foreground="#e74c3c", wraplength=400).pack(anchor="w", pady=(6, 0))

        def _intentar_acceso(event=None):
            clave = var_pass.get()
            if not clave:
                return
            btn_entrar.configure(state="disabled")
            dlg.configure(cursor="watch")
            dlg.update_idletasks()
            resultado = admin_auth.verificar_acceso(uwin, clave)
            dlg.configure(cursor="")
            if resultado["ok"]:
                global _admin_autenticado
                _admin_autenticado = True
                print(f"[LOG] Acceso Admin — usuario Windows: {uwin} "
                      f"({resultado.get('nombre','')}, modo={resultado.get('modo')}) — "
                      f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                dlg.destroy()
                on_success()
                return
            btn_entrar.configure(state="normal")
            if resultado.get("bloqueado"):
                mins = max(1, resultado["segundos"] // 60)
                var_err.set(f"⛔  Demasiados intentos fallidos. Vuelve a intentarlo en ~{mins} min.")
                entry_pass.configure(state="disabled")
                btn_entrar.configure(state="disabled")
            else:
                restantes = resultado.get("intentos_restantes", 0)
                var_err.set(
                    f"✗  {resultado['error']}  "
                    f"({restantes} intento{'s' if restantes != 1 else ''} restante{'s' if restantes != 1 else ''})"
                )
                var_pass.set("")
                entry_pass.focus_set()
            # El mensaje de error puede ocupar más (o menos) líneas que el
            # contenido con el que se calculó el alto inicial de la ventana
            # (ventana no redimensionable por el usuario) — recalculamos.
            _reposicionar()

        entry_pass.bind("<Return>", _intentar_acceso)

        btn_entrar = ttk.Button(frame_btns, text="  Entrar  ",
                                bootstyle="warning", command=_intentar_acceso)
        btn_entrar.pack(side="left", padx=(0, 8))
        ttk.Button(frame_btns, text="  Cancelar  ",
                   bootstyle="secondary", command=dlg.destroy).pack(side="left")
        _refs["btn_principal"] = btn_entrar

        entry_pass.focus_set()
        _reposicionar()

    # ── Modo ALTA: usuario nuevo — nombre + contraseña + repetir ───────
    _HOTELES = [
        "Guayarmina Princess", "Princess Inspire Tenerife", "La Palma Princess",
        "Taurito Princess", "TUI Blue Suite Princess", "Mogan Princess",
        "Gran Canaria Princess", "Maspalomas & Tabaiba Princess",
        "Club Jandia Princess", "Fuerteventura Princess", "Central Compras (Oficina)",
    ]

    def _modo_alta():
        _limpiar_dyn()
        _refs["modo"] = "alta"
        var_subtitulo.set(
            "Tu usuario de Windows todavía no tiene cuenta en Control de "
            "Pedidos. Rellena tus datos — un administrador revisará la "
            "solicitud y te enviará tus credenciales por correo."
        )
        var_toggle_txt.set("¿Ya tienes cuenta en Control de Pedidos?  Iniciar sesión")

        ttk.Label(dyn, text="Nombre:", font=("Segoe UI", 9)).pack(anchor="w")
        var_nombre = _SV()
        entry_nombre = ttk.Entry(dyn, textvariable=var_nombre, font=("Segoe UI", 10))
        entry_nombre.pack(fill="x", pady=(3, 10))

        ttk.Label(dyn, text="Apellidos:", font=("Segoe UI", 9)).pack(anchor="w")
        var_apellidos = _SV()
        entry_apellidos = ttk.Entry(dyn, textvariable=var_apellidos, font=("Segoe UI", 10))
        entry_apellidos.pack(fill="x", pady=(3, 10))

        ttk.Label(dyn, text="Correo electrónico:", font=("Segoe UI", 9)).pack(anchor="w")
        var_email = _SV()
        entry_email = ttk.Entry(dyn, textvariable=var_email, font=("Segoe UI", 10))
        entry_email.pack(fill="x", pady=(3, 10))

        ttk.Label(dyn, text="Teléfono móvil de empresa:", font=("Segoe UI", 9)).pack(anchor="w")
        var_movil = _SV()
        entry_movil = ttk.Entry(dyn, textvariable=var_movil, font=("Segoe UI", 10))
        entry_movil.pack(fill="x", pady=(3, 10))

        ttk.Label(dyn, text="Hotel(es) — puedes marcar varios:",
                  font=("Segoe UI", 9)).pack(anchor="w")
        list_hoteles = tk.Listbox(dyn, selectmode="multiple", exportselection=False,
                                  height=6, font=("Segoe UI", 9))
        for h in _HOTELES:
            list_hoteles.insert("end", h)
        list_hoteles.pack(fill="x", pady=(3, 0))

        var_err = _SV(value="")
        ttk.Label(dyn, textvariable=var_err, font=("Segoe UI", 8, "bold"),
                  foreground="#e74c3c", wraplength=400).pack(anchor="w", pady=(6, 0))

        def _crear_acceso(event=None):
            nombre    = var_nombre.get().strip()
            apellidos = var_apellidos.get().strip()
            email     = var_email.get().strip()
            movil     = var_movil.get().strip()
            hoteles   = ", ".join(_HOTELES[i] for i in list_hoteles.curselection())
            if not nombre:
                var_err.set("⚠  Indica tu nombre.")
                return
            if not apellidos:
                var_err.set("⚠  Indica tus apellidos.")
                return
            if not email or "@" not in email or "." not in email.split("@")[-1]:
                var_err.set("⚠  Introduce un correo electrónico válido.")
                return
            if not movil:
                var_err.set("⚠  Indica un teléfono móvil de empresa.")
                return
            if not hoteles:
                var_err.set("⚠  Selecciona al menos un hotel.")
                return
            btn_crear.configure(state="disabled")
            dlg.configure(cursor="watch")
            dlg.update_idletasks()
            resultado = admin_auth.solicitar_alta_directa(
                uwin, nombre, apellidos, email, movil, hoteles)
            dlg.configure(cursor="")

            if not resultado.get("ok"):
                btn_crear.configure(state="normal")
                error = resultado.get("error", "")
                if error == "sin_conexion":
                    var_err.set("⚠  Sin conexión con Control de Pedidos. Inténtalo de nuevo "
                                "más tarde.")
                else:
                    var_err.set(f"⚠  {error}")
                return

            dlg.destroy()

            # Precarga en "Mi Usuario" (2026-07-28): nombre a mostrar =
            # nombre + primer apellido, y el usuario de login del bridge
            # ya relleno con el usuario de Windows detectado — así el
            # usuario solo tiene que escribir una contraseña propia ahí
            # para tener acceso local ya mismo, mientras se aprueba la
            # solicitud. La contraseña la escribe él/ella, no la ponemos
            # aquí — verificar_acceso() la acepta la primera vez que la
            # introduzca en el diálogo de Acceso Administración.
            primer_apellido = apellidos.split()[0] if apellidos else ""
            nombre_mostrar = f"{nombre} {primer_apellido}".strip()
            try:
                update_nombre_usuario_db(uwin, nombre_mostrar)
                update_bridge_credentials(uwin, uwin, "")
            except Exception:  # noqa: BLE001
                import sys as _sys, traceback as _tb
                print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)

            messagebox.showinfo(
                "Solicitud enviada",
                f"Tu solicitud de acceso ha sido registrada (usuario '{uwin}').\n\n"
                f"Un administrador la revisará y recibirás un correo con tus "
                f"credenciales de acceso en cuanto se apruebe.\n\n"
                f"Mientras tanto: vuelve a pulsar «⚙ Admin» y elige la "
                f"contraseña que quieras — esa contraseña te dará acceso ya "
                f"mismo al panel de este equipo (sección «👤 Mi Usuario» "
                f"incluida), pero todavía NO al chat ni a los avisos de "
                f"Control de Pedidos, que necesitan la cuenta real.\n\n"
                f"Cuando llegue el correo de aprobación, entra en "
                f"«👤 Mi Usuario» y sustituye esa contraseña provisional por "
                f"la contraseña que te hayan enviado — eso desbloquea el "
                f"chat y el resto de funciones compartidas con Control de "
                f"Pedidos.",
                parent=app,
            )

        btn_crear = ttk.Button(frame_btns, text="  Enviar solicitud  ",
                               bootstyle="success", command=_crear_acceso)
        btn_crear.pack(side="left", padx=(0, 8))
        ttk.Button(frame_btns, text="  Cancelar  ",
                   bootstyle="secondary", command=dlg.destroy).pack(side="left")
        _refs["btn_principal"] = btn_crear

        entry_nombre.focus_set()
        _reposicionar()

    def _toggle_modo(event=None):
        if _refs["modo"] == "login":
            _modo_alta()
        else:
            _modo_login()

    lbl_toggle.bind("<Button-1>", _toggle_modo)

    # Mostrar de entrada en modo login (caso más habitual) mientras se
    # confirma en segundo plano si el usuario existe o no en la plataforma.
    _modo_login()
    dlg.deiconify()
    dlg.grab_set()

    def _comprobar_existencia_bg():
        existe = admin_auth.existe_en_plataforma(uwin)

        def _aplicar():
            if not dlg.winfo_exists():
                return
            if existe is False:
                # Confirmado que no existe todavía en Control de Pedidos.
                # OJO: esto también es cierto mientras hay una solicitud YA
                # enviada pendiente de aprobación (2026-07-28: bridge_user
                # queda precargado = uwin, sin contraseña, ver _crear_acceso
                # más arriba). En ese caso NO hay que forzar otra vez el
                # formulario de alta — hay que dejar el modo login para que
                # el usuario pueda escribir su contraseña momentánea, que es
                # lo que gestiona verificar_acceso() (bloque "1-bis"). Antes
                # esto se sobrescribía siempre, así que reabrir «⚙ Admin»
                # volvía a mostrar "Enviar solicitud" en vez de dejar
                # continuar. (Fix v4.14.4.)
                #
                # (2026-08-01) BUG en el fix anterior: la condición exigía
                # ADEMÁS que bridge_password estuviera vacío ("and not
                # _bp_pend"). Eso cubría el primer reinicio (recién enviada
                # la solicitud, sin contraseña todavía), pero en cuanto el
                # usuario creaba su contraseña momentánea (verificar_acceso
                # "1-bis" la guarda vía update_bridge_credentials con la
                # contraseña YA puesta), bridge_password dejaba de estar
                # vacío — y en el SIGUIENTE reinicio esta condición volvía a
                # dar False, cayendo al "elif" de más abajo y forzando otra
                # vez el formulario de alta. Resultado: quien ya se había
                # creado su contraseña momentánea se quedaba sin poder
                # volver a entrar al panel Admin nunca más (ni con esa
                # contraseña, porque el formulario que salía era el de
                # "Enviar solicitud", no el de login). Basta con NO exigir
                # que la contraseña esté vacía — el aviso de "solicitud
                # pendiente" es válido tanto si aún no hay contraseña local
                # como si ya la hay.
                _bu_pend, _bp_pend = get_bridge_credentials(uwin)
                _solicitud_pendiente = bool(_bu_pend) and _bu_pend.lower() == uwin.lower()
                if _solicitud_pendiente:
                    if _refs["modo"] == "login":
                        if _bp_pend:
                            var_subtitulo.set(
                                "Solicitud de acceso pendiente de aprobación. "
                                "Introduce tu contraseña para acceder a este "
                                "equipo mientras tanto."
                            )
                        else:
                            var_subtitulo.set(
                                "Solicitud de acceso ya enviada, pendiente de aprobación. "
                                "Introduce (o crea) tu contraseña momentánea para acceder "
                                "a este equipo mientras tanto."
                            )
                elif _refs["modo"] == "login":
                    _modo_alta()
            elif existe is True:
                if _refs["modo"] == "login":
                    var_subtitulo.set("Introduce tu contraseña de Control de Pedidos.")
            else:
                # Sin red: dejamos el modo login (con fallback offline al
                # hash local si ya existía un registro guardado antes).
                if _refs["modo"] == "login":
                    var_subtitulo.set(
                        "Sin conexión con Control de Pedidos — se usará el "
                        "acceso guardado en este equipo si existe."
                    )
            if dlg.winfo_exists():
                _reposicionar()

        dlg.after(0, _aplicar)

    threading.Thread(target=_comprobar_existencia_bg, daemon=True,
                     name="AdminAuthCheckExiste").start()

    dlg.bind("<Escape>", lambda e: dlg.destroy())
    dlg.wait_window()










MANUAL_NOMBRE = "Manual_Usuario_OrganizadorPrincess.pdf"

def abrir_manual():
    """Abre el Manual de Usuario en PDF.

    Busca el archivo en este orden:
      1. Carpeta de instalación (junto al .exe — ruta habitual tras instalar).
      2. Carpeta del script / ejecutable empaquetado (desarrollo).
      3. Directorio de trabajo actual.
    Si no lo encuentra en ninguna, muestra un mensaje orientativo.
    """

    candidatos = [
        # 1) Junto al ejecutable (PyInstaller pone sys.executable en la carpeta de instalación)
        os.path.join(os.path.dirname(sys.executable), MANUAL_NOMBRE),
        # 2) Junto al script (ejecución directa en desarrollo)
        os.path.join(os.path.dirname(os.path.abspath(__file__)), MANUAL_NOMBRE),
        # 3) Directorio de trabajo
        os.path.join(os.getcwd(), MANUAL_NOMBRE),
    ]

    ruta_manual = next((p for p in candidatos if os.path.isfile(p)), None)

    if ruta_manual:
        try:
            os.startfile(os.path.normpath(ruta_manual))
        except Exception as e:
            messagebox.showerror(
                "Error al abrir el manual",
                f"⚠️  No se pudo abrir el manual:\n\n"
                f"    {ruta_manual}\n\n"
                f"Detalle: {e}\n\n"
                "Comprueba que tienes un lector de PDF instalado (por ejemplo Adobe Reader o Edge).",
                parent=app,
            )
    else:
        messagebox.showwarning(
            "Manual no encontrado",
            f"⚠️  No se ha encontrado el archivo:\n\n"
            f"    {MANUAL_NOMBRE}\n\n"
            "El manual se instala junto con la aplicación.\n"
            "Si acabas de actualizar, vuelve a ejecutar el instalador\n"
            "o contacta con el Dpto. Central de Compras para obtenerlo.",
            parent=app,
        )


# =========================================================
# VISTA DEL MENÚ PRINCIPAL — extendida (la de siempre) o reducida (v4.18.00)
# =========================================================
VISTA_ACCESOS_REDUCIDA = 4    # accesos dorados que se ven en la reducida (los 4 primeros)
VISTA_MAX_AZULES       = 10   # botones azules de la reducida: 2 filas x 5


def _vista_actual():
    """(modo, [números de botones azules de la reducida]). Valores por defecto
    seguros si falta o está mal la clave "vista_menu" del config."""
    cfg = config.get("vista_menu")
    if not isinstance(cfg, dict):
        cfg = {}
    modo = "reducida" if cfg.get("modo") == "reducida" else "extendida"
    sel = []
    for v in cfg.get("reducida_opciones") or []:
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if 1 <= n <= NUM_OPCIONES and n not in sel:
            sel.append(n)
    sel = sorted(sel)[:VISTA_MAX_AZULES] or list(range(1, VISTA_MAX_AZULES + 1))
    return modo, sel


def _ventana_vista_menu(parent):
    """Ventana de Admin para elegir vista extendida/reducida y qué botones azules
    se ven en la reducida. Al guardar se aplica al momento."""
    modo_ini, sel_ini = _vista_actual()
    dlg = ttk.Toplevel(parent)
    dlg.withdraw()
    dlg.title("Vista del menú principal")
    dlg.resizable(False, False)
    _apply_icon(dlg)
    dlg.transient(parent)

    body = ttk.Frame(dlg, padding=(20, 16, 20, 8))
    body.pack(fill="both", expand=True)
    ttk.Label(body, text="\U0001F5A5  Vista del menú principal",
              font=("Segoe UI", 12, "bold")).pack(anchor="w")

    var_modo = StringVar(value=modo_ini)
    ttk.Radiobutton(
        body, variable=var_modo, value="extendida",
        text="Extendida (la de siempre)",
    ).pack(anchor="w", pady=(12, 0))
    ttk.Label(body, font=("Segoe UI", 8), foreground=LIGHT, wraplength=560, justify="left",
              text=f"Cabecera completa, {NUM_ACCESOS_RAPIDOS} accesos dorados y los {NUM_OPCIONES} botones azules.",
              ).pack(anchor="w", padx=(24, 0), pady=(0, 6))
    ttk.Radiobutton(
        body, variable=var_modo, value="reducida",
        text="Reducida",
    ).pack(anchor="w")
    ttk.Label(body, font=("Segoe UI", 8), foreground=LIGHT, wraplength=560, justify="left",
              text=(f"Logo y cabecera, los {VISTA_ACCESOS_REDUCIDA} primeros accesos dorados, Agenda / "
                    f"Calendario / Chat y solo los botones azules que marques abajo (máximo "
                    f"{VISTA_MAX_AZULES}, en 2 filas de 5). La ventana se hace más pequeña."),
              ).pack(anchor="w", padx=(24, 0), pady=(0, 4))

    ttk.Separator(body).pack(fill="x", pady=(8, 8))
    fila_cuenta = ttk.Frame(body)
    fila_cuenta.pack(fill="x")
    ttk.Label(fila_cuenta, text="Botones azules de la vista reducida:",
              font=("Segoe UI", 9, "bold")).pack(side="left")
    lbl_cuenta = ttk.Label(fila_cuenta, text="", font=("Segoe UI", 9), foreground=GOLD)
    lbl_cuenta.pack(side="right")

    lista = ttk.Frame(body)
    lista.pack(fill="x", pady=(6, 0))
    for c in range(3):
        lista.columnconfigure(c, weight=1, uniform="vista")
    vars_sel = {}

    def _actualizar_cuenta():
        n = sum(1 for v in vars_sel.values() if v.get())
        lbl_cuenta.configure(text=f"{n} de {VISTA_MAX_AZULES}")

    def _al_marcar(i):
        if sum(1 for v in vars_sel.values() if v.get()) > VISTA_MAX_AZULES:
            vars_sel[i].set(False)
            messagebox.showwarning(
                "Vista reducida",
                f"Se pueden marcar como máximo {VISTA_MAX_AZULES} botones.\n"
                "Desmarca alguno para poder elegir otro.", parent=dlg)
        _actualizar_cuenta()

    por_columna = (NUM_OPCIONES + 2) // 3
    for i in range(1, NUM_OPCIONES + 1):
        nombre = get_nombre(ctx, f"opcion_{i:02d}", i)
        if len(nombre) > 30:
            nombre = nombre[:29] + "…"
        vars_sel[i] = tk.BooleanVar(value=(i in sel_ini))
        ttk.Checkbutton(
            lista, text=f"{i:02d} · {nombre}", variable=vars_sel[i],
            command=lambda ix=i: _al_marcar(ix),
        ).grid(row=(i - 1) % por_columna, column=(i - 1) // por_columna,
               sticky="w", padx=(0, 10), pady=1)
    _actualizar_cuenta()

    ttk.Label(body, text="Se muestran siempre en el orden numérico del menú.",
              font=("Segoe UI", 8), foreground=LIGHT).pack(anchor="w", pady=(8, 0))

    def _guardar():
        sel = sorted(i for i, v in vars_sel.items() if v.get())
        modo = var_modo.get()
        if modo == "reducida" and not sel:
            messagebox.showwarning("Vista reducida",
                                   "Marca al menos un botón azul para la vista reducida.", parent=dlg)
            return
        config["vista_menu"] = {"modo": modo, "reducida_opciones": sel}
        save_config(config)
        dlg.destroy()
        _aplicar_vista()

    ttk.Separator(dlg).pack(fill="x")
    btns = ttk.Frame(dlg, padding=(20, 10, 20, 12))
    btns.pack(fill="x")
    ttk.Button(btns, text="\u2714  Guardar y aplicar", bootstyle="success",
               command=_guardar).pack(side="left", padx=(0, 8))
    ttk.Button(btns, text="Cancelar", bootstyle="secondary",
               command=dlg.destroy).pack(side="left")
    dlg.bind("<Escape>", lambda e: dlg.destroy())

    dlg.update_idletasks()
    w, h = dlg.winfo_reqwidth(), dlg.winfo_reqheight()
    x = max(0, (dlg.winfo_screenwidth() - w) // 2)
    y = max(20, (dlg.winfo_screenheight() - h) // 2 - 20)
    dlg.geometry(f"{w}x{h}+{x}+{y}")
    dlg.deiconify()
    dlg.grab_set()


def abrir_admin():
    """Solicita credenciales y, si son correctas, abre el panel de administración.
    Si ya se autenticó en esta sesión, abre directamente el panel."""
    def _abrir_panel():
        sw = app.winfo_screenwidth()
        sh = app.winfo_screenheight()
        aw = min(1100, sw - MARGEN * 2)
        ah = min(920,  sh - MARGEN * 2)
        # Un dedo del borde superior (~40 px) y pegado a la derecha (~40 px)
        ax = sw - aw - 40
        ay = 40

        win = ttk.Toplevel()
        win.title("Administración - Accesos y Opciones del Menú")
        win.geometry(f"{aw}x{ah}+{ax}+{ay}")
        win.resizable(False, False)
        win.minsize(1100, 500)
        _apply_icon(win)

        # ── Cabecera ──────────────────────────────────────────────
        hdr = ttk.Frame(win, padding=(20, 12, 20, 6))
        hdr.pack(fill="x")
        ttk.Label(hdr, text="\u2699  Administrar Accesos y Opciones del Menú",
                  font=("Segoe UI", 13, "bold")).pack(side="left")
        ttk.Button(hdr, text="  Cerrar  ", bootstyle="secondary",
                   command=win.destroy).pack(side="right", ipadx=4)

        def _limpiar_todo():
            """Elimina toda la configuración y restaura los valores por defecto."""
            from tkinter import messagebox as _mb
            ok = _mb.askyesno(
                "Limpiar todo",
                "¿Deseas eliminar toda la configuración de botones y accesos rápidos?\n\n"
                "Todos los botones volverán a su estado 'POR DEFINIR'.",
                icon="warning",
                parent=win
            )
            if not ok:
                return
            # Borrar claves de opciones y accesos rápidos en config
            keys_to_delete = [k for k in config
                              if k.startswith("opcion_") or k.startswith("acceso_rapido_")]
            for k in keys_to_delete:
                del config[k]
            save_config(config)
            # Actualizar labels en la ventana principal
            for i in range(1, NUM_OPCIONES + 1):
                op = f"opcion_{i:02d}"
                if op in btn_labels:
                    btn_labels[op].set(f"{i}. POR DEFINIR")
            for i in range(1, NUM_ACCESOS_RAPIDOS + 1):
                ak = f"acceso_rapido_{i:02d}"
                if ak in ar_labels:
                    ar_labels[ak].set(f"\u2605  ACCESO {i}")
            win.destroy()

        def _ventana_modificar_usuario():
            """Toplevel para cambiar el nombre del usuario Windows ACTUAL en la DB.
            Incluye seccion de credenciales de Control de Pedidos para el bridge.
            """
            uwin_actual = os.getenv("USERNAME", "").lower()

            mu_win = ttk.Toplevel()
            mu_win.title("Mi Usuario")
            mu_win.resizable(False, False)
            _apply_icon(mu_win)

            _muw = 460
            mu_win.withdraw()

            from tkinter import StringVar as _SV2

            # ── Cabecera ──────────────────────────────────────────────────────
            mu_hdr = ttk.Frame(mu_win, padding=(20, 14, 20, 8))
            mu_hdr.pack(fill="x")
            ttk.Label(mu_hdr, text="\U0001f464  Mi Usuario",
                      font=("Segoe UI", 12, "bold")).pack(anchor="w")
            ttk.Label(mu_hdr,
                      text="Nombre de sesion y credenciales de Control de Pedidos.",
                      font=("Segoe UI", 9), foreground=LIGHT,
                      wraplength=420).pack(anchor="w", pady=(3, 0))
            ttk.Separator(mu_win).pack(fill="x")

            # ── Cuerpo ────────────────────────────────────────────────────────
            body = ttk.Frame(mu_win, padding=(20, 14, 20, 0))
            body.pack(fill="both", expand=True)

            # Fila: usuario Windows (solo lectura)
            row_u = ttk.Frame(body)
            row_u.pack(fill="x", pady=(0, 8))
            ttk.Label(row_u, text="Usuario Windows:",
                      font=("Segoe UI", 9), width=20, anchor="w").pack(side="left")
            ttk.Label(row_u, text=uwin_actual,
                      font=("Consolas", 10, "bold"), foreground="#C9A84C").pack(side="left")

            # Fila: nombre a mostrar
            row_n = ttk.Frame(body)
            row_n.pack(fill="x", pady=(0, 4))
            ttk.Label(row_n, text="Nombre a mostrar:",
                      font=("Segoe UI", 9), width=20, anchor="w").pack(side="left")
            var_nombre_edit = _SV2(value=NOMBRE_USUARIO_ACTUAL)
            entry_nombre = ttk.Entry(row_n, textvariable=var_nombre_edit,
                                     font=("Segoe UI", 10), width=26)
            entry_nombre.pack(side="left", fill="x", expand=True)
            entry_nombre.focus_set()
            entry_nombre.select_range(0, "end")

            # ── Separador seccion bridge ──────────────────────────────────────
            ttk.Separator(body).pack(fill="x", pady=(14, 10))
            ttk.Label(body, text="\U0001f4e1  Control de Pedidos — credenciales bridge",
                      font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))
            ttk.Label(body,
                      text=(
                          "Introduce tu usuario y contrasena de Control de Pedidos.\n"
                          "Los avisos emergentes mostraran SOLO tus pedidos asignados,\n"
                          "igual que los mensajes de Telegram."
                      ),
                      font=("Segoe UI", 8), foreground=LIGHT,
                      wraplength=420).pack(anchor="w", pady=(0, 8))

            # Cargar credenciales actuales desde DB
            _bu_actual, _bp_actual = get_bridge_credentials(uwin_actual)

            # Fila: usuario bridge
            row_bu = ttk.Frame(body)
            row_bu.pack(fill="x", pady=(0, 4))
            ttk.Label(row_bu, text="Usuario (login):",
                      font=("Segoe UI", 9), width=20, anchor="w").pack(side="left")
            var_bridge_user = _SV2(value=_bu_actual)
            ttk.Entry(row_bu, textvariable=var_bridge_user,
                      font=("Segoe UI", 10), width=26).pack(side="left", fill="x", expand=True)

            # Fila: contrasena bridge
            row_bp = ttk.Frame(body)
            row_bp.pack(fill="x", pady=(0, 4))
            ttk.Label(row_bp, text="Contrasena:",
                      font=("Segoe UI", 9), width=20, anchor="w").pack(side="left")
            var_bridge_pass = _SV2(value=_bp_actual)
            entry_pass = ttk.Entry(row_bp, textvariable=var_bridge_pass,
                                   font=("Segoe UI", 10), width=26, show="\u2022")
            entry_pass.pack(side="left", fill="x", expand=True)

            # Toggle mostrar/ocultar contrasena
            var_show_pass = _SV2(value="0")
            def _toggle_pass():
                entry_pass.configure(show="" if var_show_pass.get() == "1" else "\u2022")
            ttk.Checkbutton(
                row_bp, text="Mostrar", variable=var_show_pass,
                bootstyle="secondary", command=_toggle_pass
            ).pack(side="left", padx=(6, 0))

            # Indicador de estado del bridge (lectura)
            try:
                import pedidos_agenda_bridge as _pab
                _bu_activo = _pab.BRIDGE_USER or _bu_actual
                _rol_activo = _pab._session.rol
                _bridge_ok  = _pab._session._logged_in
                _estado_txt = (
                    f"\u2705  Conectado como '{_bu_activo}' (rol: {_rol_activo})"
                    if _bridge_ok
                    else "\u26a0\ufe0f  Sin sesion activa  \u2014  guardado activo al reiniciar"
                )
                _estado_col = "#2ecc71" if _bridge_ok else "#e67e22"
            except Exception:
                _estado_txt = "\u2014  Bridge no iniciado en esta sesion"
                _estado_col = LIGHT
            ttk.Label(body, text=_estado_txt,
                      font=("Segoe UI", 8), foreground=_estado_col,
                      wraplength=420).pack(anchor="w", pady=(4, 0))

            # Error label global
            var_mu_err = _SV2()
            ttk.Label(body, textvariable=var_mu_err,
                      font=("Segoe UI", 8, "bold"),
                      foreground="#e74c3c").pack(anchor="w", pady=(6, 0))

            # ── Guardar ───────────────────────────────────────────────────────
            def _guardar_cambio():
                nuevo_nombre = var_nombre_edit.get().strip()
                if not nuevo_nombre:
                    var_mu_err.set("\u26a0  El nombre no puede estar vacio.")
                    return

                nuevo_bu = var_bridge_user.get().strip()
                nuevo_bp = var_bridge_pass.get().strip()

                # 1) Guardar nombre
                update_nombre_usuario_db(uwin_actual, nuevo_nombre)
                nombre_leido = get_nombre_usuario()
                if nombre_leido != nuevo_nombre:
                    var_mu_err.set("\u26a0  No se pudo guardar el nombre. Comprueba permisos de la DB.")
                    return

                global NOMBRE_USUARIO_ACTUAL
                NOMBRE_USUARIO_ACTUAL = nuevo_nombre

                # 2) Guardar credenciales bridge
                update_bridge_credentials(uwin_actual, nuevo_bu, nuevo_bp)

                # 3) Aplicar credenciales al bridge en memoria (sin reiniciar)
                try:
                    import pedidos_agenda_bridge as _pab
                    if nuevo_bu != _pab.BRIDGE_USER or nuevo_bp != _pab.BRIDGE_PASSWORD:
                        _pab.BRIDGE_USER     = nuevo_bu
                        _pab.BRIDGE_PASSWORD = nuevo_bp
                        # Forzar re-login en el siguiente ciclo del hilo
                        _pab._session._logged_in = False
                        _pab._session.username   = ""
                        _pab._session.rol        = ""
                except Exception:  # noqa: BLE001
                    import sys as _sys, traceback as _tb
                    print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)

                messagebox.showinfo(
                    "Mi Usuario",
                    f"Guardado correctamente.\n\n"
                    f"  Nombre: {uwin_actual}  \u2192  {nuevo_nombre}\n"
                    f"  Bridge: {nuevo_bu or '(vacio)'}",
                    parent=mu_win,
                )
                mu_win.destroy()

            # ── Botones ───────────────────────────────────────────────────────
            ttk.Separator(mu_win).pack(fill="x", pady=(10, 0))
            mu_btns = ttk.Frame(mu_win, padding=(20, 8, 20, 12))
            mu_btns.pack(fill="x")
            ttk.Button(mu_btns, text="\u2714  Guardar",
                       bootstyle="success",
                       command=_guardar_cambio).pack(side="left", padx=(0, 8))
            ttk.Button(mu_btns, text="Cancelar",
                       bootstyle="secondary",
                       command=mu_win.destroy).pack(side="left")

            mu_win.bind("<Return>", lambda e: _guardar_cambio())
            mu_win.bind("<Escape>", lambda e: mu_win.destroy())

            # Medir altura real y centrar antes de mostrar
            mu_win.update_idletasks()
            mu_win.update()
            _muh_real = max(mu_win.winfo_reqheight(), 420)
            _msw2 = mu_win.winfo_screenwidth()
            _msh2 = mu_win.winfo_screenheight()
            _x = (_msw2 - _muw) // 2
            _y = max((_msh2 - _muh_real) // 2, 40)
            mu_win.geometry(f"{_muw}x{_muh_real}+{_x}+{_y}")
            mu_win.deiconify()

            mu_win.grab_set()

        # Botones cabecera panel Admin
        ttk.Button(
            hdr,
            text="🧹  Limpiar todo",
            bootstyle="danger-outline",
            command=_limpiar_todo,
        ).pack(side="right", padx=(0, 8), ipadx=4)

        ttk.Button(
            hdr,
            text="👤  Mi Usuario",
            bootstyle="info-outline",
            command=_ventana_modificar_usuario,
        ).pack(side="right", padx=(0, 8), ipadx=4)

        ttk.Button(
            hdr,
            text="\U0001F5A5  Vista",
            bootstyle="warning-outline",
            command=lambda: _ventana_vista_menu(win),
        ).pack(side="right", padx=(0, 8), ipadx=4)

        ttk.Separator(win).pack(fill="x", padx=20, pady=(0, 8))

        # ── Helper: fila uniforme  [Botón con nombre] [Editar] ───
        def _fila(parent, row, col, nombre, bootstyle_btn, on_edit, opcion_key=None):
            """Dibuja una celda con botón descriptivo + botón Editar."""
            cell = ttk.Frame(parent, padding=(4, 3))
            cell.grid(row=row, column=col, padx=5, pady=4, sticky="nsew")
            cell.columnconfigure(0, weight=1)

            # Indicador de submenú si está activo
            sub_activo = opcion_key and config.get(opcion_key, {}).get("submenu", {}).get("enabled", False)
            texto_btn  = ("▶ " + nombre) if sub_activo else nombre

            # Botón descriptivo — color según sección, texto pequeño para que quepa
            ttk.Button(
                cell,
                text=texto_btn,
                bootstyle=("info" if sub_activo else bootstyle_btn),
                state="disabled",
                style="sm." + ("info" if sub_activo else bootstyle_btn) + ".TButton",
            ).grid(row=0, column=0, sticky="ew", ipady=4)

            # Botón Editar — naranja/warning para destacar sobre el fondo oscuro
            ttk.Button(
                cell,
                text="✎  Editar",
                bootstyle="warning-outline",
                command=on_edit,
            ).grid(row=1, column=0, sticky="ew", pady=(5, 0), ipady=3)

        # ── SECCIÓN ACCESOS RÁPIDOS ──────────────────────────────
        ttk.Label(win,
                  text="\u2605  Accesos Rápidos del Header",
                  font=("Segoe UI", 10, "bold"),
                  foreground=GOLD).pack(anchor="w", padx=20, pady=(0, 4))

        ar_grid = ttk.Frame(win, padding=(14, 0, 14, 4))
        ar_grid.pack(fill="x")
        for c in range(3):
            ar_grid.columnconfigure(c, weight=1, uniform="ar")

        for i in range(1, NUM_ACCESOS_RAPIDOS + 1):
            ar_key  = f"acceso_rapido_{i:02d}"
            nombre  = config.get(ar_key, {}).get("nombre", f"\u2605  ACCESO {i}")
            _fila(
                ar_grid, (i - 1) // 3, (i - 1) % 3,
                nombre,
                bootstyle_btn="warning",
                on_edit=lambda ak=ar_key, ix=i, w=win: (
                    w.destroy(),
                    _ventana_config(ctx, ak, ix, titulo_display=f"Acceso Rápido {ix}")
                ),
                opcion_key=ar_key,
            )

        ttk.Separator(win).pack(fill="x", padx=20, pady=(4, 8))

        # ── SECCIÓN OPCIONES DEL MENÚ ────────────────────────────
        ttk.Label(win,
                  text="\u2630  Opciones del Menú Principal",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20, pady=(0, 4))

        # ── Exportar/Importar + Footer — empaquetado ANTES del grid
        # para que quede fijo en la parte inferior sin ser aplastado
        # por el expand=True del grid de opciones.
        # ─────────────────────────────────────────────────────────
        bottom_frame = ttk.Frame(win)
        bottom_frame.pack(side="bottom", fill="x")

        # ── Fila única de botones: Configuración y Agenda en la misma línea ──
        ttk.Separator(bottom_frame).pack(fill="x", padx=20, pady=(6, 0))
        port_frame = ttk.Frame(bottom_frame, padding=(20, 6, 20, 6))
        port_frame.pack(fill="x")

        # Grupo Configuración
        ttk.Label(port_frame,
                  text="🖥  Configuración:",
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
        ttk.Button(
            port_frame,
            text="📤  Exportar",
            bootstyle="info-outline",
            command=lambda: exportar_config(ctx, parent_win=win),
        ).pack(side="left", padx=(0, 4))
        ttk.Button(
            port_frame,
            text="📥  Importar",
            bootstyle="warning-outline",
            command=lambda: importar_config(ctx, parent_win=win),
        ).pack(side="left", padx=(0, 20))

        # Grupo Agenda
        ttk.Label(port_frame,
                  text="📅  Agenda:",
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
        ttk.Button(
            port_frame,
            text="📤  Exportar",
            bootstyle="info-outline",
            command=lambda: exportar_agenda(ctx, parent_win=win),
        ).pack(side="left", padx=(0, 4))
        ttk.Button(
            port_frame,
            text="📥  Importar",
            bootstyle="success-outline",
            command=lambda: importar_agenda(ctx, parent_win=win),
        ).pack(side="left")

        # ── Footer: firma y versión — al final del todo ──
        ttk.Separator(bottom_frame).pack(fill="x", padx=20, pady=(0, 0))
        footer_adm = ttk.Frame(bottom_frame, padding=(20, 4, 20, 6))
        footer_adm.pack(fill="x")
        ttk.Label(footer_adm,
                  text="\u00a9 VAMA 2026  \u2022  Princess Hotels & Resorts  \u2022  Central Compras Canarias",
                  font=("Segoe UI", 8), foreground=LIGHT, anchor="w").pack(side="left")
        ttk.Label(footer_adm,
                  text=APP_VERSION,
                  font=("Segoe UI", 8, "bold"), foreground=GOLD, anchor="e").pack(side="right")

        # ── Grid de opciones — ocupa el espacio restante entre cabecera y bottom ──
        grid = ttk.Frame(win, padding=(14, 0, 14, 0))
        grid.pack(fill="both", expand=True)

        COLS = 6
        for c in range(COLS):
            grid.columnconfigure(c, weight=1, uniform="adm")

        for i in range(1, NUM_OPCIONES + 1):
            opcion = f"opcion_{i:02d}"
            nombre = get_nombre(ctx, opcion, i)
            r = (i - 1) // COLS
            c = (i - 1) % COLS
            grid.rowconfigure(r, weight=1)
            _fila(
                grid, r, c,
                f"{i:02d} · {nombre}",
                bootstyle_btn="primary",
                on_edit=lambda op=opcion, ix=i, w=win: (
                    w.destroy(),
                    _ventana_config(ctx, op, ix)
                ),
                opcion_key=opcion,
            )

    # Primero solicitar credenciales; si son correctas se abre el panel
    if _admin_autenticado:
        _abrir_panel()
    else:
        _ventana_login_admin(on_success=_abrir_panel)

# =========================================================
# VENTANA PRINCIPAL — tamano dinamico segun resolucion
# =========================================================
# Se crea app directamente (sin ventana temporal) para evitar
# el error "NULL main window" de Tcl/Tk en Python 3.14
app = ttk.Window(
    title="Organizador de Escritorio  \u2022  Princess Hotels & Resort  \u2022",
    themename="superhero",
    resizable=(False, False)
)
# Forzar fondo oscuro en TODOS los frames ttk desde el inicio
# para evitar el flash blanco al arrancar
_bg_color = str(app.style.colors.bg)
app.configure(bg=_bg_color)
app.style.configure("TFrame", background=_bg_color)
app.style.configure("TLabel", background=_bg_color)
app.update_idletasks()  # FIX: aplicar estilos TFrame/TLabel ANTES de crear los widgets,
                        # para evitar el borde blanco inicial en los 30 botones del grid
app.withdraw()   # ocultar ventana temporalmente

# ── Inyección de dependencias en módulo alertas ──────────────────────────────
_alertas_mod.app         = app
_alertas_mod.agenda_data = agenda_data
_alertas_mod.save_agenda = save_agenda
_alertas_mod._apply_icon = _apply_icon  # ANTI-REGRESION: necesario para icono en popups de aviso
# ANTI-REGRESION (Fase 3.7g): callback para refrescar la lista de avisos tras desactivar un evento
# Se asigna desde _abrir_agenda() para que apunte a la cargar_avisos() activa en ese momento.
# No se puede asignar ahora porque cargar_avisos aún no existe (se define dentro de _abrir_agenda).
# ─────────────────────────────────────────────────────────────────────────────

# ── AppContext — contenedor central de dependencias ──────────────────────────
ctx = AppContext(
    app            = app,
    config         = config,
    agenda_data    = agenda_data,
    save_config    = save_config,
    save_agenda    = save_agenda,
    nombre_usuario = NOMBRE_USUARIO_ACTUAL,
    apply_icon     = _apply_icon,
    get_crown_tk   = get_crown_tk,
    btn_labels     = btn_labels,
    btn_widgets    = btn_widgets,
    ar_labels      = ar_labels,
    ar_widgets     = ar_widgets,
)
# ─────────────────────────────────────────────────────────────────────────────


# ── Fuentes personalizadas ────────────────────────────────
# Botones del grid principal — texto más grande y legible
app.style.configure("primary.TButton",
                    font=("Segoe UI", 12, "bold"),
                    bordercolor=_bg_color,
                    lightcolor=_bg_color,
                    darkcolor=_bg_color,
                    focuscolor=_bg_color,
                    borderwidth=0,
                    focusthickness=0)
# Botones AR cabecera — tipografía elegante, texto negro
app.style.configure("warning.TButton",
                    font=("Georgia", 12, "bold"),
                    foreground="#0d0d0d")
# Botones descriptivos panel Admin — fuente pequeña para que el texto quepa
# foreground forzado para contrarrestar el oscurecimiento del estado disabled
app.style.configure("sm.primary.TButton",
                    font=("Segoe UI", 8, "bold"),
                    foreground="#FFFFFF")
app.style.map("sm.primary.TButton",
              foreground=[("disabled", "#FFFFFF")])
app.style.configure("sm.info.TButton",
                    font=("Segoe UI", 8, "bold"),
                    foreground="#FFFFFF")
app.style.map("sm.info.TButton",
              foreground=[("disabled", "#FFFFFF")])
app.style.configure("sm.warning.TButton",
                    font=("Segoe UI", 8, "bold"),
                    foreground="#1a1a1a")
app.style.map("sm.warning.TButton",
              foreground=[("disabled", "#1a1a1a")])

# Se oculta mientras se calcula geometria
app.withdraw()
app.update_idletasks()

SCR_W = app.winfo_screenwidth()
SCR_H = app.winfo_screenheight()

# wm_maxsize() devuelve el área de trabajo REAL de Windows
# (pantalla completa menos barra de tareas), sin depender de
# constantes fijas que varían según resolución o escala DPI.
try:
    _work_w, _work_h = app.wm_maxsize()
    # Sanity-check: si el valor parece inválido, usar fallback
    if _work_w < 400 or _work_h < 300:
        raise ValueError
except Exception:
    _work_w = SCR_W
    _work_h = SCR_H - 80   # fallback conservador

WIN_W = min(_work_w, SCR_W) - MARGEN * 2
WIN_X = MARGEN

# Pegado al borde superior
WIN_Y = 0

# Altura real disponible: restamos MARGEN arriba + 60 px para la barra
# de tareas. En portátiles esto garantiza que la ventana no queda tapada.
WIN_H = min(_work_h, SCR_H) - MARGEN - 60

app.geometry(f"{WIN_W}x{WIN_H}+{WIN_X}+{WIN_Y}")

# Icono de la ventana
_apply_icon(app)

# =========================================================
# CABECERA  # ANTI-REGRESIÓN Fase 3.7 — padding reducido, título proporcional
# =========================================================
header_frame = ttk.Frame(app, padding=(20, 8, 20, 8))   # ANTI-REGRESIÓN: era (24,14,24,14)
header_frame.pack(fill="x")

logo_img = None
logo = get_embedded_logo()
if logo:
    logo_h = max(120, min(140, WIN_H // 8))               # ANTI-REGRESIÓN: era max(48, min(60, WIN_H // 16))
    logo_w = int(logo.width * logo_h / logo.height)
    logo_scaled = logo.resize((logo_w, logo_h), Image.LANCZOS)
    logo_img = ImageTk.PhotoImage(logo_scaled)
    ttk.Label(header_frame, image=logo_img).pack(side="left", padx=(0, 16), anchor="center")

sep_v = ttk.Frame(header_frame, width=2, style="secondary.TFrame")
sep_v.pack(side="left", fill="y", padx=(0, 16), pady=6)

title_block = ttk.Frame(header_frame)
title_block.pack(side="left", fill="y", anchor="center")  # ANTI-REGRESIÓN: era pady=4, sin anchor

titulo_size = max(16, min(22, WIN_W // 52))               # ANTI-REGRESIÓN: era max(20, min(28, WIN_W//42))

# Línea 1: título, tamaño reducido y más proporcionado
ttk.Label(title_block, text="Menú Principal",
          font=("Segoe UI", titulo_size, "bold"), anchor="w").pack(anchor="w", fill="x")

# Línea 2: empresa
ttk.Label(title_block,
          text="\u2605  Central Compras Princess Canarias  \u2605",
          font=("Segoe UI", 9, "bold"), foreground=LIGHT,  # ANTI-REGRESIÓN: era size 10
          anchor="center", justify="center").pack(fill="x", pady=(2, 0))

# Línea 3: saludo
hora_actual = datetime.now().hour
_saludo_prefix = "Buenos días" if hora_actual < 14 else "Buenas tardes"
ttk.Label(title_block,
          text=f"{_saludo_prefix}, {NOMBRE_USUARIO_ACTUAL}",
          font=("Segoe UI", 9), foreground=LIGHT,           # ANTI-REGRESIÓN: era size 10
          anchor="center", justify="center").pack(fill="x", pady=(1, 0))

# Línea 3b: aviso si el usuario aún no configuró su nombre real
if not tiene_nombre_configurado():
    ttk.Label(title_block,
              text="\u26a0  Configura tu nombre en Admin \u2192 Mi Usuario",
              font=("Segoe UI", 8, "italic"), foreground=GOLD,
              anchor="center", justify="center").pack(fill="x", pady=(1, 0))

# Línea 4: botones Admin + Manual — zona de "utilidades" bajo el saludo,
# separada de la zona de trabajo diario (Agenda/Calendario/Chat) que queda
# en right_col. Antes "Manual de uso" vivía apilado ahí con esas tres,
# ensanchando esa columna; al ser una consulta puntual (no de uso diario
# como el chat), se saca de ahí y se coloca aquí, junto a Admin.
# bootstyle "info-outline" (el mismo teal que Agenda/Calendario/Chat) —
# se probó "secondary-outline" primero pero se veía apagado/deshabilitado
# (gris muy claro), así que se cambió antes de esta versión final. (v4.9.0)
utilidades_frame = ttk.Frame(title_block)
utilidades_frame.pack(anchor="center", pady=(5, 0))

btn_admin = ttk.Button(
    utilidades_frame,
    text="\u2699  Admin",
    bootstyle="warning-outline",
    command=abrir_admin,
    width=13
)
btn_admin.pack(side="left", ipady=2)

btn_manual = ttk.Button(
    utilidades_frame,
    text="\U0001F4D6  Manual",
    bootstyle="info-outline",
    command=abrir_manual,
    width=13
)
btn_manual.pack(side="left", padx=(6, 0), ipady=2)

# ── Columna derecha: Agenda + Calendario + Chat  (Admin y Manual ya no están aquí)
right_col = ttk.Frame(header_frame)
right_col.pack(side="right", padx=(8, 0), fill="y")

ttk.Button(
    right_col,
    text="📅  Agenda",
    bootstyle="info",
    command=abrir_agenda,
    width=18
).pack(fill="x", pady=(0, 4), ipady=4)  # ANTI-REGRESIÓN: era ipady=6

ttk.Button(
    right_col,
    text="📆  Calendario",
    bootstyle="info",
    command=abrir_calendario,
    width=18
).pack(fill="x", pady=(0, 4), ipady=4)  # ANTI-REGRESIÓN: era ipady=6

# Botón CHAT — acceso directo (v4.8.17). Hasta ahora solo se podía abrir
# desde dentro de Calendario; con el chat ya conectado en segundo plano
# desde el arranque (v4.8.5), tiene sentido un acceso directo aquí en vez
# de obligar a pasar por Calendario primero.
ttk.Button(
    right_col,
    text="💬  Chat",
    bootstyle="info",
    command=lambda: _ventana_chat(ctx),
    width=18
).pack(fill="x", ipady=4)  # ANTI-REGRESIÓN (v4.9.0): último de la columna, sin Manual debajo ya

ttk.Frame(header_frame, width=1, style="secondary.TFrame").pack(
    side="right", fill="y", padx=(12, 12), pady=8)   # separador fino

# ── ACCESOS RÁPIDOS — 2 filas × 3 columnas, centradas verticalmente
ar_frame = ttk.Frame(header_frame)
ar_frame.pack(side="left", fill="both", expand=True, padx=(16, 0))

for c in range(3):
    ar_frame.columnconfigure(c, weight=1, uniform="ar", minsize=60)  # ANTI-REGRESIÓN: era minsize=80
ar_frame.rowconfigure(0, weight=1)
ar_frame.rowconfigure(1, weight=1)

for i in range(1, NUM_ACCESOS_RAPIDOS + 1):
    ar_key = f"acceso_rapido_{i:02d}"
    var = StringVar(value=config.get(ar_key, {}).get("nombre", f"\u2605  ACCESO {i}"))
    ar_labels[ar_key] = var

    btn_ar = ttk.Button(
        ar_frame,
        textvariable=var,
        bootstyle="warning",
        command=lambda ak=ar_key, ix=i: ejecutar_ar(ak, ix)
    )
    _row = (i - 1) // 3
    _col = (i - 1) % 3
    btn_ar.grid(row=_row, column=_col, padx=4, pady=2, sticky="nsew", ipady=5)  # ANTI-REGRESIÓN: era pady=3, ipady=10
    ar_widgets[ar_key] = btn_ar

ttk.Separator(app).pack(fill="x", padx=24, pady=(0, 12))

# =========================================================
# GRID DE BOTONES — 6 col x 4 filas, tamano adaptado
# =========================================================
_bg = str(app.style.colors.bg)
grid_frame = tk.Frame(app, bg=_bg)
grid_frame.pack(fill="both", expand=True, padx=12, pady=0)

for c in range(6):
    grid_frame.columnconfigure(c, weight=1, uniform="col")

# Filas con weight=1 para que se expandan y llenen todo el espacio disponible
for r in range(5):
    grid_frame.rowconfigure(r, weight=1)

btn_ipad = 4
_btn_wrap = max(100, WIN_W // 6 - 20)
btn_cells = {}   # opcion_key -> Frame contenedor (para mostrar/ocultar según la vista)
btn_lbls  = {}   # opcion_key -> Label con el texto (para ajustar el ajuste de línea)


def _colocar_celda(cell, row, col, ncols, nrows):
    """Coloca una celda del grid azul: sin margen en los bordes exteriores,
    mayor separación entre botones."""
    cell.grid(row=row, column=col,
              padx=(0 if col == 0 else 4, 0 if col == ncols - 1 else 4),
              pady=(0 if row == 0 else 4, 0 if row == nrows - 1 else 4),
              sticky="nsew")


for i in range(1, NUM_OPCIONES + 1):
    opcion = f"opcion_{i:02d}"
    var = StringVar(value=get_nombre(ctx, opcion, i))
    btn_labels[opcion] = var

    row = (i - 1) // 6
    col = (i - 1) % 6

    cell = ttk.Frame(grid_frame)
    _colocar_celda(cell, row, col, 6, 5)
    btn_cells[opcion] = cell
    cell.rowconfigure(0, weight=1)
    cell.columnconfigure(0, weight=1)

    # Botón ttk real (maneja el click y el estilo visual)
    btn = ttk.Button(
        cell,
        bootstyle="primary",
        command=lambda x=opcion, ix=i: ejecutar_opcion(x, ix)
    )
    btn.grid(row=0, column=0, sticky="nsew", ipady=btn_ipad)

    # Label transparente encima con wraplength y alineación centrada
    lbl = ttk.Label(
        cell,
        textvariable=var,
        wraplength=_btn_wrap,
        font=("Segoe UI", 10, "bold"),  # ANTI-REGRESIÓN: era 12 — demasiado grande en botones anchos
        anchor="center",
        justify="center",
        background=app.style.colors.primary,
        foreground="white",
        cursor="hand2",
    )
    lbl.grid(row=0, column=0, sticky="nsew", padx=4, pady=2)  # ANTI-REGRESIÓN: era padx=6, pady=4
    lbl.bind("<Button-1>", lambda e, x=opcion, ix=i: ejecutar_opcion(x, ix))
    # Hover visual: oscurecer ligeramente el label al pasar el ratón
    lbl.bind("<Enter>", lambda e, lw=lbl: lw.configure(background=app.style.colors.info))
    lbl.bind("<Leave>", lambda e, lw=lbl: lw.configure(background=app.style.colors.primary))

    btn_widgets[opcion] = btn
    btn_lbls[opcion] = lbl

# =========================================================
# PIE DE PAGINA
# =========================================================
ttk.Separator(app).pack(fill="x", padx=12, pady=(4, 0))

footer_frame = ttk.Frame(app, padding=(24, 4, 24, 6))  # ANTI-REGRESIÓN: era (24,6,24,10)
footer_frame.pack(fill="x")

ttk.Label(
    footer_frame,
    text="\u00a9 VAMA 2026  \u2022  Princess Hotels & Resorts  \u2022  Central Compras Canarias",
    font=("Segoe UI", 9),
    foreground=LIGHT,
    anchor="w"
).pack(side="left")

ttk.Label(
    footer_frame,
    text=APP_VERSION,
    font=("Segoe UI", 9, "bold"),
    foreground=GOLD,
    anchor="e"
).pack(side="right")

def _aplicar_vista():
    """Reorganiza el menú principal según config["vista_menu"] (v4.18.00):
    extendida = como siempre; reducida = 4 accesos dorados (2x2) y los botones
    azules elegidos (2 filas x 5), con la ventana ajustada a ese contenido."""
    modo, sel = _vista_actual()
    red = (modo == "reducida")

    # Accesos dorados
    cols_ar = 2 if red else 3
    for i in range(1, NUM_ACCESOS_RAPIDOS + 1):
        w = ar_widgets.get(f"acceso_rapido_{i:02d}")
        if w is None:
            continue
        if red and i > VISTA_ACCESOS_REDUCIDA:
            w.grid_remove()
        else:
            w.grid(row=(i - 1) // cols_ar, column=(i - 1) % cols_ar,
                   padx=4, pady=2, sticky="nsew", ipady=5)
    for c in range(3):
        if c < cols_ar:
            ar_frame.columnconfigure(c, weight=1, uniform="ar", minsize=60)
        else:
            ar_frame.columnconfigure(c, weight=0, uniform="", minsize=0)

    # Botones azules
    visibles = sel if red else list(range(1, NUM_OPCIONES + 1))
    ncols, nrows = (5, 2) if red else (6, 5)
    for i in range(1, NUM_OPCIONES + 1):
        cell = btn_cells.get(f"opcion_{i:02d}")
        if cell is None:
            continue
        if i in visibles:
            k = visibles.index(i)
            _colocar_celda(cell, k // ncols, k % ncols, ncols, nrows)
        else:
            cell.grid_remove()
    for c in range(6):
        if c < ncols:
            grid_frame.columnconfigure(c, weight=1, uniform="col")
        else:
            grid_frame.columnconfigure(c, weight=0, uniform="", minsize=0)
    for r in range(5):
        grid_frame.rowconfigure(r, weight=1 if r < nrows else 0, minsize=0)

    # Tamaño y posición de la ventana
    app.update_idletasks()
    if red:
        w_ven = min(WIN_W, max(header_frame.winfo_reqwidth() + 40, ncols * 150 + 40))
        h_ven = min(WIN_H, header_frame.winfo_reqheight() + nrows * 96
                    + footer_frame.winfo_reqheight() + 44)
        ajuste = max(100, w_ven // ncols - 20)
    else:
        w_ven, h_ven = WIN_W, WIN_H
        ajuste = _btn_wrap
    for lbl_b in btn_lbls.values():
        lbl_b.configure(wraplength=ajuste)
    app.geometry(f"{w_ven}x{h_ven}+{WIN_X}+{WIN_Y}")


_aplicar_vista()

# FIX: forzar que ttkbootstrap genere y aplique las imágenes de estilo
# de los botones (primary.TButton, etc.) ANTES de mostrar la ventana,
# para evitar que el borde se vea blanco unos segundos y luego cambie a negro.
app.update_idletasks()
app.update()

# Se muestra la ventana ya construida
app.deiconify()

# FIX popup-ciego: señalizar al bridge antes de destruir la ventana
# (el botón X también pasa por aquí)
def _on_close_app():
    try:
        detener_bridge()
    except Exception:
        pass  # UI — ignorar silenciosamente
    try:
        save_agenda(agenda_data)
    except Exception:  # noqa: BLE001
        import sys as _sys, traceback as _tb
        print(f"[ERROR] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
    try:
        liberar_instancia_actual()
    except Exception:
        pass  # UI — ignorar silenciosamente
    try:
        app.destroy()
    except Exception:
        pass  # UI — ignorar silenciosamente

app.protocol("WM_DELETE_WINDOW", _on_close_app)

# ── Dialogo de nueva version (si procede) ─────────────────────────────────────
# Se lanza despues de deiconify para que la ventana tenga padre visible.
# El usuario elige entre:
#   A) Solo actualizar version  → se mantienen config y agenda intactos
#   B) Instalacion desde cero   → se resetea config y se borra la agenda
#                                  (con opcion de hacer copia de seguridad primero)
# ─────────────────────────────────────────────────────────────────────────────
if _nueva_version_detectada:
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
                app.after(300, lambda: mostrar_saludo_diario(ctx))
            else:
                # Desde cero
                hacer_backup = var_backup.get() == "si"
                _appdata_dir_local = os.path.dirname(os.path.abspath(
                    __import__("db.sqlite", fromlist=["CONFIG_FILE"]).CONFIG_FILE))
                ruta_bk      = var_ruta_bk.get().strip() or _appdata_dir_local

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
            app.after(300, lambda: mostrar_saludo_diario(ctx))

        ttk.Button(
            pie, text="  Cancelar  ",
            bootstyle="secondary",
            command=_cancelar,
        ).pack(side="right", padx=(8, 0))

        def _confirmar_safe():
            try:
                _confirmar()
            except Exception as _exc:
                import traceback
                messagebox.showerror(
                    "Error al confirmar",
                    f"Error inesperado:\n\n{_exc}\n\n{traceback.format_exc()[-600:]}",
                    parent=dlg,
                )
        ttk.Button(
            pie, text="  Confirmar  ",
            bootstyle="warning",
            command=_confirmar_safe,
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

    app.after(200, _dialogo_nueva_version_safe)
# =========================================================
# SALUDO DIARIO — se muestra solo una vez al dia
# =========================================================




# Lanzar el saludo con un pequeño retardo para que la ventana principal
# haya terminado de renderizarse completamente antes de mostrarlo.
# Si hay nueva version, el saludo se lanza desde dentro del dialogo de version
# para evitar colision de grab_set() entre ambas ventanas modales.
if not _nueva_version_detectada:
    app.after(400, lambda: mostrar_saludo_diario(ctx))

# Hilo de vigilancia de avisos (daemon -> muere al cerrar la app)
# ANTI-REGRESION (bug Fase 3.7e): nombrar el hilo para detectar si ya existe
# (evita que doble-click o reload arranque un segundo monitor en paralelo)
_monitor_existente = any(t.name == "MonitorAvisos" for t in threading.enumerate())
if not _monitor_existente:
    threading.Thread(target=monitor_avisos, daemon=True, name="MonitorAvisos").start()
else:
    import logging as _lg
    _lg.getLogger("monitor_avisos").warning("Monitor ya activo — arranque adicional ignorado")

# Poller thread-safe de popups — necesario con PyInstaller console=False.
# El hilo monitor encola en _popup_queue; este poller (ejecutado en el hilo
# principal) vacía la cola cada 500 ms y se re-registra automáticamente.
# SIN este poller, app.after() llamado desde el hilo monitor lanza:
#     RuntimeError: main thread is not in main loop
app.after(500, poll_alertas)

iniciar_bridge_pedidos(agenda_data, save_agenda, app, app_root=app, mostrar_alerta_fn=mostrar_alerta)

# ── Chat: conexión en segundo plano + burbujas emergentes (v4.8.14) ────────
# Hasta ahora el chat solo se conectaba al abrir su ventana, así que un
# mensaje nuevo pasaba desapercibido si no la tenías abierta. Igual que
# iniciar_bridge_pedidos arriba, se conecta ya desde el arranque del
# Organizador; poll_chat() es el único que drena cliente.eventos y reparte
# cada evento a quien corresponda — la ventana principal si está abierta
# (ver _HANDLER en ui/ventana_chat.py) y cualquier burbuja flotante abierta
# (ver ui/chat_popup.py) — para no tener varios consumidores compitiendo
# por la misma cola. Si nadie está viendo ese canal en ningún sitio, se
# abre una burbuja nueva sola, abajo a la derecha, en vez del aviso
# genérico de antes — se puede leer y responder sin abrir la ventana
# completa.
_chat_cliente = get_chat_client()
_chat_cliente.iniciar_conexion_en_segundo_plano()

def poll_chat():
    try:
        while True:
            ev = _chat_cliente.eventos.get_nowait()

            if _ventana_chat_mod._HANDLER is not None:
                try:
                    _ventana_chat_mod._HANDLER(ev)
                except Exception:
                    logging.getLogger("chat").exception("Error actualizando la ventana de chat")

            if _chat_popup_mod is not None:
                try:
                    _chat_popup_mod.procesar_evento(ev)
                except Exception:
                    logging.getLogger("chat").exception("Error actualizando una burbuja de chat")

            if ev.get("tipo") == EVT_NUEVO_MENSAJE:
                m = ev["mensaje"]
                remitente = m.get("remitente", "")
                if remitente and remitente != _chat_cliente.username:
                    canal_id = m.get("canal_id", "")
                    _reproducir_sonido_aviso("aviso")
                    # Si ya se está viendo ese canal (ventana principal abierta
                    # en ese canal, o ya hay una burbuja abierta para él), el
                    # mensaje ya es visible ahí mismo — no hace falta nada más
                    # que el sonido, para no duplicar avisos sobre lo mismo.
                    ya_visible = (
                        _ventana_chat_mod._CANAL_VISIBLE == canal_id
                        or canal_id in _chat_popup_mod._POPUPS
                    )
                    if not ya_visible:
                        nombre_remitente = _chat_cliente.nombre_de(remitente)
                        if canal_id == "general":
                            titulo = "General"
                        elif canal_id.startswith("grp:"):
                            titulo = f"{nombre_remitente}  (grupo)"
                        else:
                            titulo = nombre_remitente
                        _chat_popup_mod.mostrar_popup_chat(ctx, canal_id, titulo, mensaje_inicial=m)
    except Exception:
        pass  # queue.Empty — nada pendiente
    app.after(700, poll_chat)

app.after(700, poll_chat)

# Comprobar actualizaciones en GitHub Releases (hilo daemon, no bloquea)
# Se lanza con retardo para que la ventana principal esté visible primero.
app.after(3000, lambda: _lanzar_check_update(app))

# ── CIERRE AUTOMÁTICO A LAS 17:00 (DESACTIVADO 2026-07-20) ──────────────────
# Se desactiva a petición: no había ningún conflicto real que lo justificara
# (agenda.json/config.json/usuarios.db son locales por usuario en %APPDATA%,
# no un recurso compartido en red), y el problema de instancias duplicadas
# que este cierre ayudaba a mitigar de forma indirecta ya está resuelto de
# raíz en utils/instancia_unica.py (mutex de sistema operativo).
# Si en el futuro aparecieran síntomas de degradación en sesiones muy largas
# (memoria, hilos, conexión del chat/bridge), reactivar descomentando la
# llamada a app.after(5_000, _vigilar_cierre_automatico) más abajo — la
# función se deja intacta, solo se ha quitado su arranque.
_HORA_CIERRE = (17, 0)   # (hora, minuto) — ajustar aquí si se necesita cambiar

def _vigilar_cierre_automatico():
    """Cierre automático diario a _HORA_CIERRE.

    Solo cierra si la hora actual está dentro de la ventana de cierre
    (entre _HORA_CIERRE y _HORA_CIERRE + 5 minutos). Así, si la app
    se abre después de esa hora no se cierra — solo se cierra si estaba
    abierta en el momento exacto de las _HORA_CIERRE.
    """
    from datetime import timedelta
    ahora    = datetime.now()
    hoy      = ahora.date()
    t_cierre = datetime.combine(hoy, ahora.time().replace(
                   hour=_HORA_CIERRE[0], minute=_HORA_CIERRE[1],
                   second=0, microsecond=0))
    t_ventana_fin = t_cierre + timedelta(minutes=5)

    if t_cierre <= ahora <= t_ventana_fin:
        # Estamos dentro de los 5 minutos de la hora de cierre → cerrar
        try:
            save_agenda(agenda_data)
        except Exception:  # noqa: BLE001
            import sys as _sys, traceback as _tb
            print(f"[ERROR] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
        try:
            app.title("Cerrando automáticamente… — Organizador Princess")
        except Exception:
            pass  # UI — ignorar silenciosamente
        detener_bridge()
        try:
            liberar_instancia_actual()
        except Exception:
            pass  # UI — ignorar silenciosamente
        app.after(1500, app.destroy)
        return   # no re-programar

    # Fuera de la ventana de cierre → seguir comprobando cada 60 s
    app.after(60_000, _vigilar_cierre_automatico)

# Arrancar el vigilante con retardo de 5 s para no solapar con el arranque
# app.after(5_000, _vigilar_cierre_automatico)   # DESACTIVADO 2026-07-20 — ver nota arriba
# ─────────────────────────────────────────────────────────────────────────────

# Mostrar la ventana ahora que todo está construido — evita el flash blanco
app.update_idletasks()
app.deiconify()

app.mainloop()
