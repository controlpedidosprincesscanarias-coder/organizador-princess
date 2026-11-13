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
    get_nombre_usuario, tiene_nombre_configurado,
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

# ── Módulos extraídos en Fase 3A ──────────────────────────────────────────────
from ui.assets import (
    get_embedded_logo, get_crown_tk, _apply_icon,
)
from ui.saludo import mostrar_saludo_diario
from ui.agenda import abrir_agenda as _abrir_agenda_ventana
from ui.calendario import abrir_calendario as _abrir_calendario_ventana
from ui.admin import abrir_admin as _abrir_admin_ventana
from ui.disposicion import (MARGEN, NUM_ACCESOS_RAPIDOS, NUM_OPCIONES, VISTA_ACCESOS_REDUCIDA,
                            vista_actual)
from ui.agenda_helpers import get_nombre
from ui.ventana_config import (_ventana_config, _abrir_submenu)
from ui.ventana_chat import _ventana_chat
from ui import notas_version as _notas_version
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

# ── (v4.18.62) BORRADO COMPLETO Y REINICIO LIMPIO ─────────────────────────────
# Si en Administración se pidió «Borrado completo y reinicio limpio», la copia anterior dejó una marca y se
# cerró (la ha cerrado también asegurar_instancia_unica). Se borra aquí, ANTES de cargar la configuración y la
# agenda (más abajo), para que nada vuelva a guardar los datos antiguos. Ver services/reinicio_limpio.py.
from services import reinicio_limpio as _reinicio_limpio
_REINICIO_LIMPIO = None
if _reinicio_limpio.hay_pendiente():
    try:
        _REINICIO_LIMPIO = _reinicio_limpio.aplicar()
    except Exception as _e_rl:  # nunca impedir el arranque por esto
        _REINICIO_LIMPIO = ([], [str(_e_rl)])
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
APP_VERSION  = "v4.18.64"   # ← actualizar en cada release (debe coincidir con el tag del release en GitHub)
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
# (v4.18.60) Si se abrió con «Abrir el Organizador» de Control Pedidos (organizadorprincess://abrir?navegador=…),
# se guarda el código de ese navegador: así Control Pedidos sabe que este PC tiene el Organizador abierto.
import services.vinculo_navegador as _vinculo_navegador  # noqa: E402
if _vinculo_navegador.guardar_desde_argv(sys.argv[1:]):
    logging.getLogger("actualizacion").info("Navegador vinculado con Control Pedidos")
# (v4.18.20) Si esta versión se instaló con «Actualizar ahora», no se pregunta cómo instalarla:
# ya se ha hecho «Solo actualizar versión» y al abrir se avisa con un mensaje breve.
_actualizada_sola = _nueva_version_detectada and _update_mod.actualizacion_automatica_aplicada(_version_anterior)
if _actualizada_sola:
    _nueva_version_detectada = False
# (v4.18.56) Primera vez en este equipo (no hay versión anterior guardada): no hay nada que «instalar»,
# así que no se pregunta cómo hacerlo; se hace «Solo actualizar versión», que no borra nada. Pasó con la
# copia portátil en un PC nuevo: salía «Nueva versión detectada — Versión anterior: desconocida».
_primera_vez_en_equipo = _update_mod.es_primera_vez_en_equipo(_nueva_version_detectada, _version_anterior)
if _primera_vez_en_equipo:
    _update_mod._aplicar_solo_actualizacion(_version_anterior)
    _nueva_version_detectada = False
# (v4.18.36) Borrar el instalador ya aplicado de la carpeta temporal y dejarlo anotado.
_instaladores_borrados, _instaladores_pendientes = _update_mod.borrar_instaladores_aplicados(APP_VERSION)
for _n in _instaladores_borrados:
    logging.getLogger("actualizacion").info("Instalador ya aplicado borrado: %s", _n)
for _n in _instaladores_pendientes:
    logging.getLogger("actualizacion").warning("No se pudo borrar el instalador %s (se reintentará al arrancar)", _n)
# (v4.18.54) Copia portátil (sin instalar): borrar el .exe anterior que dejó la actualización y registrar
# el enlace organizadorprincess:// para este usuario de Windows (el instalador lo hace para todo el equipo).
from services import portatil as _portatil  # noqa: E402
_es_portatil = _portatil.es_portatil()
_restos_portatil_pendientes = []
if _es_portatil:
    _restos_borrados, _restos_portatil_pendientes = _portatil.limpiar_restos()
    for _n in _restos_borrados:
        logging.getLogger("actualizacion").info("Copia anterior borrada: %s", _n)
    if not _portatil.registrar_enlace_usuario():
        logging.getLogger("actualizacion").warning("No se pudo registrar el enlace organizadorprincess:// del usuario")

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


# =========================================================
# VENTANAS PRINCIPALES (v4.18.08: su código está en app/ui/)
#   Agenda          → ui/agenda.py      (abrir_agenda)
#   Calendario      → ui/calendario.py  (abrir_calendario)
#   Administración  → ui/admin.py       (abrir_admin, login y «Vista»)
# ANTI-REGRESION: no hay credenciales fijas de Administración (ver
# services/admin_auth.py). Las ventanas reciben el AppContext (ctx), que se
# crea más abajo: estos envoltorios solo se llaman desde botones, ya con ctx.
# =========================================================
def abrir_agenda():
    """Abre la ventana «Agenda de Avisos»."""
    _abrir_agenda_ventana(ctx)


def abrir_calendario():
    """Abre la ventana «Calendario»."""
    _abrir_calendario_ventana(ctx)


def abrir_admin():
    """Abre Administración (pide la contraseña la primera vez en cada sesión)."""
    _abrir_admin_ventana(ctx)


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
    # 4) (v4.18.54) Dentro del propio .exe: la copia portátil no tiene el PDF al lado (main.spec, «documentos»)
    _incluido = _portatil.documento_incluido(MANUAL_NOMBRE)
    if _incluido:
        candidatos.append(_incluido)

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


# Vista del menú principal — extendida o reducida (v4.18.00). Constantes y
# lectura en ui/disposicion.py; la ventana «Vista» está en ui/admin.py.
def _vista_actual():
    """(modo, botones azules de la reducida) — ver ui/disposicion.vista_actual."""
    return vista_actual(config)

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
    app_version    = APP_VERSION,
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

_lbl_version = ttk.Label(
    footer_frame,
    text=APP_VERSION,
    font=("Segoe UI", 9, "bold"),
    foreground=GOLD,
    anchor="e"
)
_lbl_version.pack(side="right")
# (v4.18.44) Al pulsar la versión se ven sus notas (ui/notas_version.py)
_notas_version.hacer_pulsable(_lbl_version, app, APP_VERSION)

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


ctx.aplicar_vista = _aplicar_vista   # la usa ui/admin.py al guardar la vista
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
if _actualizada_sola:
    app.after(1500, lambda: messagebox.showinfo(
        "Organizador actualizado",
        f"El Organizador se ha actualizado a la versión {APP_VERSION}.\n\n"
        "Tu configuración y tu agenda se mantienen."
        + ("" if _es_portatil
           else "\nEl instalador descargado ya se ha borrado." if _instaladores_borrados and not _instaladores_pendientes
           else "\nEl instalador descargado se borrará en el próximo arranque." if _instaladores_pendientes else ""),
        parent=app))


def _reintentar_restos_portatil(intento=1):
    """(v4.18.54) La versión anterior puede tardar unos segundos en cerrarse: se reintenta cada 10 s, 6 veces."""
    _, pendientes = _portatil.limpiar_restos()
    if pendientes and intento < 6:
        app.after(10000, lambda: _reintentar_restos_portatil(intento + 1))
    elif pendientes:
        logging.getLogger("actualizacion").warning("No se pudo borrar %s; se reintentará al arrancar", pendientes)


if _restos_portatil_pendientes:
    app.after(10000, _reintentar_restos_portatil)

# (v4.18.54) Primer arranque de la copia portátil: carpeta donde guardarla, arranque con Windows y
# escritorio (ui/primer_arranque_portatil.py). En la versión instalada no hace nada.
if _es_portatil:
    import ui.primer_arranque_portatil as _primer_arranque  # noqa: E402
    app.after(1200, lambda: _primer_arranque.comprobar(
        app, os.path.join(os.path.dirname(CONFIG_FILE), "portatil.json")))

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
                    # (v4.18.16, petición de Víctor) Si es la conversación que se ve en la
                    # ventana grande, esa ventana se cierra y la conversación sigue en la
                    # burbuja, con lo que se estuviera escribiendo.
                    borrador = None
                    if (_ventana_chat_mod._CANAL_VISIBLE == canal_id
                            and canal_id not in _chat_popup_mod._POPUPS):
                        borrador = _ventana_chat_mod.cerrar_para_seguir_en_burbuja()
                    ya_visible = canal_id in _chat_popup_mod._POPUPS
                    if not ya_visible:
                        nombre_remitente = _chat_cliente.nombre_de(remitente)
                        if canal_id == "general":
                            titulo = "General"
                        elif canal_id.startswith("grp:"):
                            titulo = f"{nombre_remitente}  (grupo)"
                        else:
                            titulo = nombre_remitente
                        _chat_popup_mod.mostrar_popup_chat(ctx, canal_id, titulo, mensaje_inicial=m,
                                                           borrador=borrador or "")
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

# (v4.18.62) Aviso tras un «Borrado completo y reinicio limpio» (ver arriba, junto a la instancia única)
if _REINICIO_LIMPIO is not None:
    def _avisar_reinicio_limpio(_r=_REINICIO_LIMPIO):
        _texto = ("El Organizador se ha reiniciado en limpio: se han borrado la configuración, la agenda, "
                  "«Mi Usuario» y las copias de seguridad de este equipo.\n\n"
                  "Configúralo de nuevo como la primera vez (Administración) y vuelve a iniciar sesión en "
                  "Control de Pedidos.")
        if _r[1]:
            _texto += ("\n\nNo se pudo borrar (estaba en uso): " + ", ".join(_r[1][:5]) +
                       ". No afecta al funcionamiento.")
        messagebox.showinfo("Reinicio limpio", _texto)
    app.after(1500, _avisar_reinicio_limpio)

app.mainloop()
