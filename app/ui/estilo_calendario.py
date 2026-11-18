"""
ui/estilo_calendario.py
Aspecto común de Calendario, Vacaciones y Festivos (rediseño v4.18.72, petición de Víctor del 13 nov 2026:
«aspecto más moderno y profesional»): colores sobre el tema «superhero», tarjetas con una franja de color,
bloque de fecha («28 / NOV») y lista con desplazamiento.

Se usan widgets tk normales (Frame/Label) con el color puesto a mano: los ttk.Label dentro de un marco de
color se pintaban con el fondo del tema y salía un recuadro oscuro detrás de cada texto.

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.
"""
import tkinter as tk

import ttkbootstrap as ttk

from ui.colores import GOLD
from utils.textos_calendario import MESES_CORTOS, a_fecha

# ── Colores (tema «superhero») ────────────────────────────────────────────────
FONDO       = "#2b3e50"   # fondo de la ventana (el del tema)
TARJETA     = "#33485d"   # celdas y tarjetas
TARJETA_FIN = "#2f4356"   # sábados y domingos
TARJETA_SOBRE = "#3b526a" # al pasar el ratón
FUERA_MES   = "#2d4053"   # días del mes anterior o siguiente
BORDE       = "#3f566d"
TEXTO       = "#ffffff"
TEXTO_SUAVE = "#9fb2c4"
TEXTO_APAGADO = "#6f8396"
AZUL        = "#4c9be8"   # avisos
CIAN        = "#5bc0de"   # día elegido / repetitivos
VERDE       = "#5cb85c"   # vacaciones
ROJO        = "#d9534f"   # festivos
DORADO      = GOLD        # hoy

# Fondo suave de las etiquetas de cada tipo dentro de una celda
FONDO_TIPO = {"festivo": "#5a3a44", "vacaciones": "#355a45", "aviso": "#34506e",
              "repetitivo": "#2f5866", "mas": TARJETA}
COLOR_TIPO = {"festivo": ROJO, "vacaciones": VERDE, "aviso": AZUL, "repetitivo": CIAN, "mas": TEXTO_SUAVE}
ICONO_TIPO = {"festivo": "🎉", "vacaciones": "🏖", "aviso": "🔔", "repetitivo": "🔁", "mas": ""}

F_TITULO    = ("Segoe UI", 16, "bold")
F_SUBTITULO = ("Segoe UI", 9)
F_NORMAL    = ("Segoe UI", 10)
F_NEGRITA   = ("Segoe UI", 10, "bold")
F_PEQUE     = ("Segoe UI", 8)
F_PEQUE_NEG = ("Segoe UI", 8, "bold")


def etiqueta(padre, texto="", fondo=TARJETA, color=TEXTO, fuente=F_NORMAL, **kw):
    """tk.Label con el fondo de su marco (sin recuadro oscuro detrás)."""
    return tk.Label(padre, text=texto, bg=fondo, fg=color, font=fuente, bd=0, **kw)


def cabecera(padre, icono, titulo, subtitulo_var=None):
    """Título grande de la ventana y, debajo, una línea de resumen (StringVar)."""
    frm = tk.Frame(padre, bg=FONDO)
    frm.pack(fill="x", padx=22, pady=(18, 10))
    etiqueta(frm, f"{icono}  {titulo}", fondo=FONDO, fuente=F_TITULO).pack(anchor="w")
    if subtitulo_var is not None:
        tk.Label(frm, textvariable=subtitulo_var, bg=FONDO, fg=TEXTO_SUAVE, font=F_SUBTITULO,
                 bd=0, anchor="w", justify="left").pack(anchor="w", pady=(4, 0))
    return frm


def lista_desplazable(padre, ventana):
    """Marco con barra de desplazamiento y rueda del ratón (antes, copiado igual en Vacaciones y Festivos).
    Devuelve el marco interior, donde se ponen las filas."""
    lf = tk.Frame(padre, bg=FONDO)
    lf.pack(fill="both", expand=True, padx=(18, 10))
    canvas = tk.Canvas(lf, highlightthickness=0, bg=FONDO, bd=0)
    sb = ttk.Scrollbar(lf, orient="vertical", command=canvas.yview, bootstyle="round")
    sf = tk.Frame(canvas, bg=FONDO)
    sf.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    ventana_interior = canvas.create_window((0, 0), window=sf, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)
    # ANTI-REGRESION (v4.8.9): el ancho interior sigue al del canvas; si no, las filas se quedaban cortas.
    canvas.bind("<Configure>", lambda e: canvas.itemconfig(ventana_interior, width=e.width))
    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y", padx=(6, 0))

    # ANTI-REGRESION (v4.8.9): la rueda solo se enlaza con el puntero dentro, para no robársela a otra ventana.
    def _rueda(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"
    canvas.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _rueda))
    canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))
    ventana.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"), add="+")
    sf.canvas = canvas
    return sf


def separador_anio(padre, anio, derecha=""):
    """«2026 ──────────── 10 días»."""
    frm = tk.Frame(padre, bg=FONDO)
    frm.pack(fill="x", pady=(12, 6))
    etiqueta(frm, str(anio), fondo=FONDO, color=DORADO, fuente=("Segoe UI", 11, "bold")).pack(side="left")
    if derecha:
        etiqueta(frm, derecha, fondo=FONDO, color=TEXTO_SUAVE, fuente=F_PEQUE).pack(side="right")
    tk.Frame(frm, bg=BORDE, height=1).pack(side="left", fill="x", expand=True, padx=10, pady=(2, 0))
    return frm


def bloque_fecha(padre, fecha_iso, color, fondo=TARJETA, apagado=False):
    """Cuadro con el día grande y el mes abreviado debajo, como la hoja de un calendario."""
    d = a_fecha(fecha_iso)
    frm = tk.Frame(padre, bg=fondo, width=54)
    etiqueta(frm, f"{d.day:02d}" if d else "--", fondo=fondo,
             color=TEXTO_APAGADO if apagado else TEXTO, fuente=("Segoe UI", 17, "bold")).pack()
    etiqueta(frm, MESES_CORTOS[d.month - 1].upper() if d else "", fondo=fondo,
             color=TEXTO_APAGADO if apagado else color, fuente=F_PEQUE_NEG).pack()
    return frm


def tarjeta(padre, color, apagado=False):
    """Fila de una lista: franja de color a la izquierda y fondo de tarjeta. Devuelve (marco, cuerpo)."""
    marco = tk.Frame(padre, bg=TARJETA, highlightthickness=1, highlightbackground=BORDE)
    marco.pack(fill="x", pady=3)
    tk.Frame(marco, bg=TEXTO_APAGADO if apagado else color, width=4).pack(side="left", fill="y")
    cuerpo = tk.Frame(marco, bg=TARJETA)
    cuerpo.pack(side="left", fill="both", expand=True, padx=(12, 10), pady=8)
    return marco, cuerpo


def etiqueta_estado(padre, texto, color, fondo=TARJETA):
    """Pastilla pequeña («En curso», «Pasado», «Hoy»)."""
    return tk.Label(padre, text=f" {texto} ", bg=color, fg=FONDO if color != TEXTO_APAGADO else TEXTO,
                    font=F_PEQUE_NEG, bd=0, padx=4, pady=1)


def botones_fila(padre, al_editar, al_borrar):
    """Botones ✏ y 🗑 de una fila, discretos (el borde solo se colorea al pasar el ratón)."""
    frm = tk.Frame(padre, bg=TARJETA)
    ttk.Button(frm, text="✏", width=3, bootstyle="light-outline", command=al_editar).pack(side="left")
    ttk.Button(frm, text="🗑", width=3, bootstyle="danger-outline", command=al_borrar).pack(side="left", padx=(6, 0))
    return frm


def vacia(padre, texto):
    etiqueta(padre, texto, fondo=FONDO, color=TEXTO_SUAVE, fuente=F_NORMAL).pack(pady=40)
