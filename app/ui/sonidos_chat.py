"""
ui/sonidos_chat.py — ventanas para elegir el sonido de los mensajes del chat (v4.18.76).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Petición de Víctor (20 nov 2026): cambiar el sonido de los mensajes y poder elegir uno distinto para cada chat
o grupo. Dos entradas:
  · ventana_sonidos(ctx): «🔔 Sonidos del chat» de Administración. Sonido general y la lista de todas las
    conversaciones (General, privados y grupos), cada una con el suyo.
  · elegir_sonido_canal(ctx, …): «🔔 Sonido de este chat» del menú ⋮ de la ventana del chat y del botón 🔔 de la
    burbuja.
Cada cambio se guarda al momento en config.json (solo en este equipo). La lógica está en services/sonidos_chat.py.
"""
import logging
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk

from services import sonidos_chat as sc
from services.chat_client import get_chat_client, es_canal_avisos, BOT_NOMBRE

log = logging.getLogger("chat")

_ARCHIVO_PROPIO = "📁 Archivo propio (.wav)…"
_GOLD = "#C9A84C"
_META = "#8a97a8"

_VENTANA = {"win": None}


def _guardar(ctx):
    try:
        ctx.save_config(ctx.config)
    except Exception:  # noqa: BLE001
        log.exception("Sonidos del chat: no se pudo guardar config.json")


def _selector(ctx, parent, valor_inicial, con_predeterminado, al_cambiar, ancho=30):
    """Desplegable de sonidos + ▶ para probarlo. `al_cambiar(valor)` se llama con el valor ya validado.
    Devuelve el marco."""
    frm = ttk.Frame(parent)
    general = sc.predeterminado(ctx.config) if con_predeterminado else None
    actual = {"valor": valor_inicial}

    def _lista():
        opts = sc.opciones(con_predeterminado, general)
        ruta = sc.ruta_archivo(actual["valor"])
        if ruta:
            opts.append((actual["valor"], sc.nombre_de(actual["valor"])))
        opts.append((None, _ARCHIVO_PROPIO))
        return opts

    opts = _lista()
    var = tk.StringVar(value=sc.nombre_de(actual["valor"], general))
    combo = ttk.Combobox(frm, textvariable=var, state="readonly", width=ancho,
                         values=[t for _, t in opts])
    combo.pack(side="left")

    def _elegido(_e=None):
        texto = var.get()
        valor = next((v for v, t in opts if t == texto), sc.PREDETERMINADO)
        if texto == _ARCHIVO_PROPIO:
            ruta = filedialog.askopenfilename(
                parent=frm.winfo_toplevel(), title="Elegir un sonido (.wav)",
                filetypes=[("Sonidos WAV", "*.wav")])
            if not ruta:
                var.set(sc.nombre_de(actual["valor"], general))
                return
            if not sc.es_wav(ruta):
                messagebox.showwarning("Sonidos del chat", "Elige un archivo de sonido .wav.",
                                       parent=frm.winfo_toplevel())
                var.set(sc.nombre_de(actual["valor"], general))
                return
            valor = sc.valor_archivo(ruta)
        actual["valor"] = valor
        opts[:] = _lista()
        combo.configure(values=[t for _, t in opts])
        var.set(sc.nombre_de(valor, general))
        al_cambiar(valor)
        sc.reproducir(sc.predeterminado(ctx.config) if valor == sc.PREDETERMINADO else valor)

    combo.bind("<<ComboboxSelected>>", _elegido)

    def _probar():
        v = actual["valor"]
        sc.reproducir(sc.predeterminado(ctx.config) if v == sc.PREDETERMINADO else v)

    ttk.Button(frm, text="▶", width=3, bootstyle="info-outline", command=_probar).pack(side="left", padx=(4, 0))
    return frm


def _centrar(win, parent, ancho, alto):
    win.update_idletasks()
    try:
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x, y = px + (pw - ancho) // 2, py + (ph - alto) // 2
    except Exception:  # noqa: BLE001
        x = (win.winfo_screenwidth() - ancho) // 2
        y = (win.winfo_screenheight() - alto) // 2
    win.geometry(f"{ancho}x{alto}+{max(0, x)}+{max(0, y)}")


def elegir_sonido_canal(ctx, parent, canal_id, titulo):
    """Diálogo pequeño «🔔 Sonido de este chat» (menú ⋮ del chat y botón 🔔 de la burbuja)."""
    win = ttk.Toplevel(parent)
    win.title("Sonido de este chat")
    win.resizable(False, False)
    win.attributes("-topmost", True)       # la burbuja también está siempre encima
    ctx.apply_icon(win)
    cuerpo = ttk.Frame(win, padding=(18, 14, 18, 12))
    cuerpo.pack(fill="both", expand=True)
    ttk.Label(cuerpo, text=f"🔔  {titulo}", font=("Segoe UI", 11, "bold")).pack(anchor="w")
    ttk.Label(cuerpo, text="Sonido de los mensajes nuevos de esta conversación (solo en este equipo).",
              font=("Segoe UI", 9), foreground=_META, wraplength=360).pack(anchor="w", pady=(2, 10))

    def _cambio(valor):
        sc.fijar_canal(ctx.config, canal_id, valor)
        _guardar(ctx)

    _selector(ctx, cuerpo, sc.propio(ctx.config, canal_id), True, _cambio, ancho=34).pack(anchor="w")
    pie = ttk.Frame(cuerpo)
    pie.pack(fill="x", pady=(14, 0))
    ttk.Button(pie, text="🔔 Todos los sonidos…", bootstyle="link",
               command=lambda: (win.destroy(), ventana_sonidos(ctx))).pack(side="left")
    ttk.Button(pie, text="  Cerrar  ", bootstyle="secondary", command=win.destroy).pack(side="right")
    _centrar(win, parent, 460, 180)
    win.grab_set()
    return win


def _nombre_canal(c, cliente):
    tipo = c.get("tipo")
    if tipo == "general" or c.get("canal_id") == "general":
        return "💬 General"
    if tipo == "grupo":
        return "👥 " + (c.get("nombre") or "Grupo")
    if es_canal_avisos(c.get("canal_id")):
        return "📢 " + BOT_NOMBRE
    otro = c.get("otro_usuario")
    return "👤 " + (cliente.nombre_de(otro) if otro else "?")


def ventana_sonidos(ctx, parent=None):
    """«🔔 Sonidos del chat» (Administración): el general y uno por cada chat o grupo."""
    if _VENTANA["win"] is not None and _VENTANA["win"].winfo_exists():
        _VENTANA["win"].deiconify()
        _VENTANA["win"].lift()
        return _VENTANA["win"]
    win = ttk.Toplevel(parent or ctx.app)
    _VENTANA["win"] = win
    win.title("Sonidos del chat")
    ctx.apply_icon(win)
    win.minsize(560, 420)

    cab = ttk.Frame(win, padding=(20, 16, 20, 8))
    cab.pack(fill="x")
    ttk.Label(cab, text="🔔  Sonidos del chat", font=("Segoe UI", 13, "bold")).pack(anchor="w")
    ttk.Label(cab, text="Elige cómo suenan los mensajes nuevos: uno general y, si quieres, otro distinto para cada "
                        "chat o grupo. Se guarda al momento y solo en este equipo (el móvil tiene sus propios "
                        "sonidos en Ajustes).",
              font=("Segoe UI", 9), foreground=_META, wraplength=520, justify="left").pack(anchor="w", pady=(4, 0))
    ttk.Separator(win).pack(fill="x")

    gen = ttk.Frame(win, padding=(20, 10, 20, 10))
    gen.pack(fill="x")
    ttk.Label(gen, text="Sonido general", font=("Segoe UI", 10, "bold"), foreground=_GOLD,
              width=22).pack(side="left")

    def _cambio_general(valor):
        sc.fijar_predeterminado(ctx.config, valor)
        _guardar(ctx)
        _pintar_lista(_canales["lista"])       # «Como el general (…)» cambia de texto

    _selector(ctx, gen, sc.predeterminado(ctx.config), False, _cambio_general).pack(side="left")
    ttk.Separator(win).pack(fill="x")

    pie = ttk.Frame(win, padding=(20, 8, 20, 12))
    pie.pack(side="bottom", fill="x")

    def _todo_general():
        if not messagebox.askyesno("Sonidos del chat",
                                   "¿Quitar los sonidos propios de todos los chats y grupos?\n\n"
                                   "Todos sonarán con el sonido general.", parent=win):
            return
        datos = dict(ctx.config.get(sc.CLAVE_CONFIG) or {})
        datos["canales"] = {}
        ctx.config[sc.CLAVE_CONFIG] = datos
        _guardar(ctx)
        _pintar_lista(_canales["lista"])

    ttk.Button(pie, text="↺ Todos con el general", bootstyle="warning-outline",
               command=_todo_general).pack(side="left")
    ttk.Button(pie, text="  Cerrar  ", bootstyle="secondary", command=win.destroy).pack(side="right")
    ttk.Separator(win).pack(side="bottom", fill="x")

    ttk.Label(win, text="Cada conversación", font=("Segoe UI", 10, "bold"),
              padding=(20, 8, 20, 4)).pack(anchor="w")

    # Lista con desplazamiento
    zona = ttk.Frame(win)
    zona.pack(fill="both", expand=True, padx=(20, 8))
    lienzo = tk.Canvas(zona, highlightthickness=0, bd=0, bg=ttk.Style().colors.bg)
    barra = ttk.Scrollbar(zona, orient="vertical", command=lienzo.yview)
    lienzo.configure(yscrollcommand=barra.set)
    barra.pack(side="right", fill="y")
    lienzo.pack(side="left", fill="both", expand=True)
    interior = ttk.Frame(lienzo)
    id_int = lienzo.create_window((0, 0), window=interior, anchor="nw")
    interior.bind("<Configure>", lambda _e: lienzo.configure(scrollregion=lienzo.bbox("all")))
    lienzo.bind("<Configure>", lambda e: lienzo.itemconfigure(id_int, width=e.width))

    def _rueda(e):
        if lienzo.winfo_exists():
            lienzo.yview_scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1), "units")
    win.bind("<MouseWheel>", _rueda)

    _canales = {"lista": None}
    cliente = get_chat_client()

    def _pintar_lista(canales):
        if not win.winfo_exists():
            return
        for w in interior.winfo_children():
            w.destroy()
        if canales is None:
            ttk.Label(interior, text="Cargando las conversaciones…", foreground=_META).pack(anchor="w", pady=6)
            return
        if not canales:
            ttk.Label(interior, text="No se han podido cargar las conversaciones. Comprueba que el chat está "
                                     "conectado y vuelve a abrir esta ventana.",
                      foreground=_META, wraplength=480).pack(anchor="w", pady=6)
            return
        for c in canales:
            cid = c.get("canal_id")
            if not cid:
                continue
            fila = ttk.Frame(interior)
            fila.pack(fill="x", pady=3)
            ttk.Label(fila, text=_nombre_canal(c, cliente), width=26, anchor="w").pack(side="left")

            def _cambio(valor, cid=cid):
                sc.fijar_canal(ctx.config, cid, valor)
                _guardar(ctx)
            _selector(ctx, fila, sc.propio(ctx.config, cid), True, _cambio, ancho=32).pack(side="left")

    _pintar_lista(None)

    def _cargar():
        try:
            canales = cliente.obtener_canales() or []
        except Exception:  # noqa: BLE001
            log.exception("Sonidos del chat: no se pudo cargar la lista de conversaciones")
            canales = []
        _canales["lista"] = canales
        if win.winfo_exists():
            win.after(0, lambda: _pintar_lista(canales))
    threading.Thread(target=_cargar, daemon=True, name="Chat-Sonidos").start()

    _centrar(win, parent or ctx.app, 640, 560)
    return win
