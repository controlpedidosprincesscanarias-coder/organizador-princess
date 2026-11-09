"""
app/ui/emoticonos.py  ·  v4.18.18
Botón 😊 del chat: abre un panel con emoticonos y respuestas rápidas («👍 Ok», «👌 Perfecto»…)
que se añaden a lo que se está escribiendo. Lo usan la ventana grande del chat
(ui/ventana_chat.py) y la burbuja flotante (ui/chat_popup.py).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Los emoticonos son texto normal: viajan dentro del mensaje, el servidor del chat no cambia y
se ven también en las versiones anteriores del Organizador.
"""
import tkinter as tk

# Sin el selector de variante U+FE0F (❤️ → ❤): Tk lo pintaría como un recuadro.
EMOTICONOS = [
    "👍", "👌", "✅", "🙏", "👏", "🙌", "💪", "👀",
    "😊", "😀", "😂", "😉", "😅", "🤔", "😮", "😢",
    "😡", "😴", "❤", "🎉", "⭐", "🔥", "☕", "🍽",
    "📦", "🚚", "📄", "📅", "⏰", "⚠", "❌", "✔",
]
RESPUESTAS = ["👍 Ok", "👌 Perfecto", "👍 Me gusta", "🙏 Gracias", "✅ Hecho", "👀 Lo miro", "⏰ Ahora voy", "📞 Te llamo"]

_COLUMNAS = 8
_FONDO, _BOTON, _BOTON_ACTIVO, _TEXTO = "#1b2735", "#25313f", "#33415a", "#e8edf2"
_FUENTE_EMOJI = ("Segoe UI Emoji", 14)
_FUENTE_TEXTO = ("Segoe UI", 9)


def insertar(entry, texto):
    """Añade `texto` donde está el cursor, con un espacio delante si hace falta."""
    try:
        pos = entry.index("insert")
        antes = entry.get()[:pos]
    except tk.TclError:
        return
    if antes and not antes.endswith(" "):
        texto = " " + texto
    entry.insert("insert", texto + " ")
    entry.focus_set()


_ABIERTO = [None]


def abrir_panel(boton, entry, encima=False):
    """Panel de emoticonos pegado al botón 😊. Un clic añade el emoticono y cierra el panel;
    con Mayús + clic se queda abierto para poner varios. Esc o pulsar fuera lo cierran."""
    previo = _ABIERTO[0]
    if previo is not None and previo.winfo_exists():   # el botón 😊 también lo cierra
        previo.destroy()
        _ABIERTO[0] = None
        return None
    dueno = boton.winfo_toplevel()
    pan = tk.Toplevel(dueno)
    _ABIERTO[0] = pan
    pan.withdraw()
    pan.overrideredirect(True)
    pan.configure(bg=_FONDO, highlightthickness=1, highlightbackground="#2f4258")
    if encima:                      # la burbuja está siempre encima: el panel también
        pan.attributes("-topmost", True)

    def cerrar(event=None):
        if pan.winfo_exists():
            pan.destroy()
        try:
            entry.focus_set()
        except tk.TclError:
            pass

    def elegir(texto, event=None):
        insertar(entry, texto)
        if not (event is not None and event.state & 0x0001):   # Mayús: no se cierra
            cerrar()
        else:
            pan.focus_set()

    rejilla = tk.Frame(pan, bg=_FONDO)
    rejilla.pack(padx=6, pady=(6, 2))
    for i, e in enumerate(EMOTICONOS):
        b = tk.Label(rejilla, text=e, font=_FUENTE_EMOJI, bg=_BOTON, fg=_TEXTO, width=2, cursor="hand2")
        b.grid(row=i // _COLUMNAS, column=i % _COLUMNAS, padx=1, pady=1, ipadx=2)
        b.bind("<Button-1>", lambda ev, e=e: elegir(e, ev))
        b.bind("<Enter>", lambda ev, b=b: b.configure(bg=_BOTON_ACTIVO))
        b.bind("<Leave>", lambda ev, b=b: b.configure(bg=_BOTON))

    tk.Label(pan, text="Respuestas rápidas", font=("Segoe UI", 8), bg=_FONDO, fg="#8fa3b8").pack(anchor="w", padx=8, pady=(4, 0))
    rapidas = tk.Frame(pan, bg=_FONDO)
    rapidas.pack(padx=6, pady=(2, 6), fill="x")
    for i, r in enumerate(RESPUESTAS):
        b = tk.Label(rapidas, text=r, font=_FUENTE_TEXTO, bg=_BOTON, fg=_TEXTO, cursor="hand2", padx=6, pady=3)
        b.grid(row=i // 4, column=i % 4, padx=1, pady=1, sticky="ew")
        b.bind("<Button-1>", lambda ev, r=r: elegir(r, ev))
        b.bind("<Enter>", lambda ev, b=b: b.configure(bg=_BOTON_ACTIVO))
        b.bind("<Leave>", lambda ev, b=b: b.configure(bg=_BOTON))
    for c in range(4):
        rapidas.columnconfigure(c, weight=1)

    pan.bind("<Escape>", cerrar)
    def _al_perder_foco(event=None):
        def _comprobar():
            if not pan.winfo_exists():
                return
            try:
                f = pan.focus_get()
            except (KeyError, tk.TclError):
                f = None
            if f is None or f.winfo_toplevel() is not pan:
                cerrar()
        pan.after(150, _comprobar)
    pan.bind("<FocusOut>", _al_perder_foco)
    pan.update_idletasks()
    w, h = pan.winfo_reqwidth(), pan.winfo_reqheight()
    x = boton.winfo_rootx() + boton.winfo_width() - w      # alineado a la derecha del botón
    y = boton.winfo_rooty() - h - 4                         # por encima de la caja de escribir
    x = max(0, min(x, pan.winfo_screenwidth() - w))
    if y < 0:
        y = boton.winfo_rooty() + boton.winfo_height() + 4
    pan.geometry(f"+{x}+{y}")
    pan.deiconify()
    pan.lift()
    pan.focus_force()
    return pan
