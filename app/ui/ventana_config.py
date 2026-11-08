"""
app/ui/ventana_config.py
Ventana de configuración de opciones, accesos rápidos y submenús.
Extraído de main_agenda.py en Fase 3B.

Recibe AppContext (ctx) — sin globals.
"""
import ttkbootstrap as ttk
from tkinter import filedialog, messagebox, StringVar  # ANTI-REGRESION: StringVar era global de main_agenda
from ui.assets import _apply_icon                      # ANTI-REGRESION: usada en todas las ventanas Toplevel
from utils.rutas import _lanzar_ruta                   # ANTI-REGRESION: usada en _ejecutar_sub

# Constantes de color — ANTI-REGRESION: eran globals de main_agenda, no se llevaron al extraer el módulo
GOLD  = "#C9A84C"
LIGHT = "#D8E8F0"

# Geometría — ANTI-REGRESION: idem
MARGEN = 44   # px aprox. 2 dedos en cada borde

# Versión de la app mostrada en la ventana Admin — ANTI-REGRESION: idem
# Debe mantenerse sincronizada con APP_VERSION en main_agenda.py
APP_VERSION = "v4.4.3B"

# Tipos de acceso disponibles en el selector de la ventana de config — ANTI-REGRESION: idem
# icono · etiqueta · valor · placeholder · usa explorar
_TIPOS = [
    ("📁", "Carpeta de red",     "carpeta",     r"\\servidor\carpeta",   True),
    ("🌐", "Página web",         "web",         "https://",              False),
    ("⚙️",  "Archivo ejecutable", "ejecutable",  r"C:\ruta\programa.exe", True),
]

# Estado interno del módulo — referencia al submenú activo
_submenu_activo = None


def _ventana_config(ctx, opcion, idx, nuevo=False, titulo_display=None):
    win = ttk.Toplevel()
    win.title("Configurar acceso" if nuevo else "Editar acceso")
    _cw, _ch = 620, 610          # ancho para "Archivo ejecutable" y alto con sección submenú
    _sw = win.winfo_screenwidth()
    _sh = win.winfo_screenheight()
    _margen_izq = 60             # separación del borde izquierdo
    _cx = _margen_izq            # siempre a la izquierda, sin solapar admin
    _cy = (_sh - _ch) // 2      # centrada verticalmente
    win.geometry(f"{_cw}x{_ch}+{_cx}+{_cy}")
    win.resizable(False, False)
    _apply_icon(win)

    cfg_actual = ctx.config.get(opcion, {})
    tipo_actual = cfg_actual.get("tipo", "carpeta")
    # Migración: tipos antiguos → nuevo esquema
    if tipo_actual not in ("carpeta", "web", "ejecutable"):
        tipo_actual = "carpeta"

    label_title = titulo_display if titulo_display else f"Opción {idx}"

    # ── Cabecera de la ventana ────────────────────────────────
    hdr = ttk.Frame(win, padding=(22, 16, 22, 10))
    hdr.pack(fill="x")
    ttk.Label(hdr, text=label_title,
              font=("Segoe UI", 13, "bold")).pack(side="left")

    ttk.Separator(win).pack(fill="x", padx=0)

    body = ttk.Frame(win, padding=(22, 14, 22, 0))
    body.pack(fill="both", expand=True)

    # ── Nombre ───────────────────────────────────────────────
    ttk.Label(body, text="Nombre del botón:", font=("Segoe UI", 9)).pack(anchor="w")
    nombre_actual = cfg_actual.get("nombre",
                        titulo_display if titulo_display else f"{idx}. POR DEFINIR")
    var_nombre = StringVar(value=nombre_actual)
    ttk.Entry(body, textvariable=var_nombre,
              font=("Segoe UI", 10)).pack(fill="x", pady=(3, 14))

    # ── Tipo — 3 botones grandes horizontales ────────────────
    ttk.Label(body, text="Tipo de enlace:", font=("Segoe UI", 9)).pack(anchor="w")
    var_tipo = StringVar(value=tipo_actual)

    frame_tipos = ttk.Frame(body)
    frame_tipos.pack(fill="x", pady=(4, 14))
    for col, (icono, etiqueta, valor, _, _con_explorar) in enumerate(_TIPOS):
        frame_tipos.columnconfigure(col, weight=1)
        btn_t = ttk.Radiobutton(
            frame_tipos,
            text=f"{icono}  {etiqueta}",
            variable=var_tipo,
            value=valor,
            bootstyle="toolbutton-primary",
        )
        btn_t.grid(row=0, column=col, padx=(0 if col == 0 else 6, 0), sticky="ew", ipady=6)

    # ── Ruta ─────────────────────────────────────────────────
    lbl_ruta = ttk.Label(body, text="Ruta / Dirección:", font=("Segoe UI", 9))
    lbl_ruta.pack(anchor="w")

    ruta_actual = cfg_actual.get("ruta", "")
    var_ruta = StringVar(value=ruta_actual)

    frame_ruta = ttk.Frame(body)
    frame_ruta.pack(fill="x", pady=(3, 0))
    entry_ruta = ttk.Entry(frame_ruta, textvariable=var_ruta, font=("Segoe UI", 9))
    entry_ruta.pack(side="left", fill="x", expand=True, padx=(0, 8))

    btn_explorar = ttk.Button(
        frame_ruta, text="Explorar…", bootstyle="secondary-outline", width=10
    )
    btn_explorar.pack(side="left")

    # Placeholder dinámico según tipo seleccionado
    def _actualizar_ui(*_):
        t = var_tipo.get()
        for _, _, v, ph, con_exp in _TIPOS:
            if v == t:
                if not var_ruta.get():
                    entry_ruta.configure(foreground="#888888")
                    # No sobreescribir si ya hay valor; solo mostrar hint visual
                btn_explorar.configure(state="normal" if con_exp else "disabled")
                break

    var_tipo.trace_add("write", _actualizar_ui)
    _actualizar_ui()   # estado inicial

    def explorar():
        t = var_tipo.get()
        if t == "carpeta":
            r = filedialog.askdirectory(parent=win, title="Seleccionar carpeta de red")
        else:   # ejecutable
            r = filedialog.askopenfilename(
                parent=win,
                title="Seleccionar archivo ejecutable o documento",
                filetypes=[
                    ("Ejecutables y documentos", "*.exe *.bat *.cmd *.lnk *.pyw *.ps1 *.rdp *.xlsx *.xls *.xlsm *.docx *.doc *.pdf"),
                    ("Aplicación (.exe)",          "*.exe"),
                    ("Script (.bat/.cmd)",         "*.bat *.cmd"),
                    ("Acceso directo (.lnk)",      "*.lnk"),
                    ("Escritorio remoto (.rdp)",   "*.rdp"),
                    ("PowerShell (.ps1)",          "*.ps1"),
                    ("Excel (.xlsx/.xls/.xlsm)",   "*.xlsx *.xls *.xlsm"),
                    ("Word (.docx/.doc)",          "*.docx *.doc"),
                    ("PDF (.pdf)",                 "*.pdf"),
                    ("Todos los archivos",         "*.*"),
                ],
            )
        if r:
            var_ruta.set(r)

    btn_explorar.configure(command=explorar)

    # ── Submenú ─────────────────────────────────────────────
    ttk.Separator(win).pack(fill="x", padx=0, pady=(12, 0))
    sub_frame = ttk.Frame(win, padding=(22, 10, 22, 0))
    sub_frame.pack(fill="x")

    ttk.Label(sub_frame, text="▶  Submenú",
              font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 4))

    sub_cfg_actual = cfg_actual.get("submenu", {})
    from tkinter import IntVar
    var_sub_enabled = IntVar(value=1 if sub_cfg_actual.get("enabled", False) else 0)
    var_sub_count   = StringVar(value=str(sub_cfg_actual.get("count", 5)))

    chk_sub = ttk.Checkbutton(
        sub_frame,
        text="Activar submenú (este botón abrirá una ventana con subopciones)",
        variable=var_sub_enabled,
        bootstyle="round-toggle-primary",
    )
    chk_sub.pack(anchor="w")

    sub_opts_frame = ttk.Frame(sub_frame)
    sub_opts_frame.pack(fill="x", pady=(8, 0))

    ttk.Label(sub_opts_frame,
              text="Número de subopciones (1–10):",
              font=("Segoe UI", 9)).pack(side="left")
    spin_sub = ttk.Spinbox(
        sub_opts_frame, from_=1, to=10,
        textvariable=var_sub_count,
        width=5, state="readonly",
        bootstyle="primary",
    )
    spin_sub.pack(side="left", padx=(8, 16))

    btn_cfg_subs = ttk.Button(
        sub_opts_frame,
        text="⚙  Configurar subopciones…",
        bootstyle="info-outline",
    )
    btn_cfg_subs.pack(side="left")

    def _toggle_sub(*_):
        s = "readonly" if var_sub_enabled.get() else "disabled"
        spin_sub.configure(state=s)
        btn_cfg_subs.configure(state="normal" if var_sub_enabled.get() else "disabled")

    var_sub_enabled.trace_add("write", _toggle_sub)
    _toggle_sub()   # estado inicial

    def _abrir_cfg_subs():
        try:
            cnt = int(var_sub_count.get())
        except ValueError:
            cnt = 5
        nombre_p = var_nombre.get().strip() or (titulo_display or f"Opción {idx}")
        _ventana_admin_submenu(ctx, opcion, idx, cnt, nombre_p)   # ANTI-REGRESION: ctx requerido (bug Fase 3.7)

    btn_cfg_subs.configure(command=_abrir_cfg_subs)

    # ── Botones Guardar / Cancelar ───────────────────────────
    ttk.Separator(win).pack(fill="x", padx=0, pady=(14, 0))
    frame_btns = ttk.Frame(win, padding=(22, 10, 22, 14))
    frame_btns.pack(fill="x")

    def guardar():
        nombre = var_nombre.get().strip() or (titulo_display if titulo_display else f"{idx}. POR DEFINIR")
        ruta   = var_ruta.get().strip()
        tipo   = var_tipo.get()
        entry  = ctx.config.get(opcion, {})
        entry["nombre"] = nombre
        entry["tipo"]   = tipo
        if ruta:
            entry["ruta"] = ruta
        # Guardar configuración de submenú
        try:
            sub_count = int(var_sub_count.get())
        except ValueError:
            sub_count = 5
        entry["submenu"] = {
            "enabled": bool(var_sub_enabled.get()),
            "count":   sub_count,
        }
        ctx.config[opcion] = entry
        ctx.save_config(ctx.config)
        if opcion in ctx.btn_labels:
            ctx.btn_labels[opcion].set(nombre)
        if opcion in ctx.ar_labels:
            ctx.ar_labels[opcion].set(nombre)
        win.destroy()

    ttk.Button(frame_btns, text="  Guardar  ",
               bootstyle="success", command=guardar).pack(side="left", padx=(0, 8))
    ttk.Button(frame_btns, text="  Cancelar  ",
               bootstyle="secondary", command=win.destroy).pack(side="left")


def _ventana_admin_submenu(ctx, opcion, idx, count, nombre_padre):
    """Ventana para administrar las subopciones de un botón principal."""
    sw = ctx.app.winfo_screenwidth()
    sh = ctx.app.winfo_screenheight()
    aw = min(860, sw - MARGEN * 2)
    ah = min(640, sh - MARGEN * 2)
    ax = (sw - aw) // 2
    ay = (sh - ah) // 2

    win = ttk.Toplevel()
    win.title(f"Subopciones — {nombre_padre}")
    win.geometry(f"{aw}x{ah}+{ax}+{ay}")
    win.resizable(False, False)
    _apply_icon(win)

    # Cabecera
    hdr = ttk.Frame(win, padding=(20, 12, 20, 6))
    hdr.pack(fill="x")
    ttk.Label(hdr,
              text=f"▶  Subopciones de: {nombre_padre}",
              font=("Segoe UI", 12, "bold")).pack(side="left")
    ttk.Button(hdr, text="  Cerrar  ",
               bootstyle="secondary", command=win.destroy).pack(side="right")

    ttk.Separator(win).pack(fill="x", padx=20, pady=(0, 8))

    ttk.Label(win,
              text=f"Este botón tiene {count} subopción/es configurables.",
              font=("Segoe UI", 9), foreground=LIGHT).pack(anchor="w", padx=20, pady=(0, 8))

    COLS = min(5, count)
    grid = ttk.Frame(win, padding=(14, 0, 14, 0))
    grid.pack(fill="both", expand=True)
    for c in range(COLS):
        grid.columnconfigure(c, weight=1, uniform="sc")

    def _fila_sub(parent, row, col, sub_key, sub_idx):
        sub_nombre = ctx.config.get(sub_key, {}).get("nombre", f"SUB {sub_idx}")
        cell = ttk.Frame(parent, padding=(4, 3))
        cell.grid(row=row, column=col, padx=5, pady=4, sticky="nsew")
        cell.columnconfigure(0, weight=1)
        parent.rowconfigure(row, weight=1)

        ttk.Button(
            cell,
            text=f"{sub_idx:02d} · {sub_nombre}",
            bootstyle="info",
            state="disabled",
            style="sm.info.TButton",
        ).grid(row=0, column=0, sticky="ew", ipady=4)

        def _editar(sk=sub_key, si=sub_idx):
            win.destroy()
            _ventana_config_sub(ctx, sk, si, nombre_padre)   # ANTI-REGRESION: ctx requerido (bug Fase 3.7)

        ttk.Button(
            cell,
            text="✎  Editar",
            bootstyle="warning-outline",
            command=_editar,
        ).grid(row=1, column=0, sticky="ew", pady=(5, 0), ipady=3)

    for i in range(1, count + 1):
        sub_key = f"{opcion}_sub_{i:02d}"
        r = (i - 1) // COLS
        c = (i - 1) % COLS
        _fila_sub(grid, r, c, sub_key, i)

    ttk.Separator(win).pack(fill="x", padx=20, pady=(8, 0))
    footer = ttk.Frame(win, padding=(20, 5, 20, 8))
    footer.pack(fill="x")
    ttk.Label(footer,
              text="\u00a9 VAMA 2026  \u2022  Princess Hotels & Resorts  \u2022  Central Compras Canarias",
              font=("Segoe UI", 8), foreground=LIGHT, anchor="w").pack(side="left")
    ttk.Label(footer, text=APP_VERSION,
              font=("Segoe UI", 8, "bold"), foreground=GOLD, anchor="e").pack(side="right")


def _ventana_config_sub(ctx, sub_key, sub_idx, nombre_padre):
    """Ventana de configuración de una subopción individual."""
    win = ttk.Toplevel()
    win.title(f"Subopción {sub_idx} — {nombre_padre}")
    _cw, _ch = 620, 480
    _sw = win.winfo_screenwidth()
    _sh = win.winfo_screenheight()
    _cx = (_sw - _cw) // 2
    _cy = (_sh - _ch) // 2
    win.geometry(f"{_cw}x{_ch}+{_cx}+{_cy}")
    win.resizable(False, False)
    _apply_icon(win)

    cfg_actual = ctx.config.get(sub_key, {})
    tipo_actual = cfg_actual.get("tipo", "carpeta")
    if tipo_actual not in ("carpeta", "web", "ejecutable"):
        tipo_actual = "carpeta"

    # Cabecera
    hdr = ttk.Frame(win, padding=(22, 16, 22, 10))
    hdr.pack(fill="x")
    ttk.Label(hdr,
              text=f"▶  Subopción {sub_idx}  —  {nombre_padre}",
              font=("Segoe UI", 12, "bold")).pack(side="left")
    ttk.Separator(win).pack(fill="x")

    body = ttk.Frame(win, padding=(22, 14, 22, 0))
    body.pack(fill="both", expand=True)

    # Nombre
    ttk.Label(body, text="Nombre del botón:", font=("Segoe UI", 9)).pack(anchor="w")
    nombre_actual = cfg_actual.get("nombre", f"SUB {sub_idx}")
    var_nombre = StringVar(value=nombre_actual)
    ttk.Entry(body, textvariable=var_nombre,
              font=("Segoe UI", 10)).pack(fill="x", pady=(3, 14))

    # Tipo
    ttk.Label(body, text="Tipo de enlace:", font=("Segoe UI", 9)).pack(anchor="w")
    var_tipo = StringVar(value=tipo_actual)
    frame_tipos = ttk.Frame(body)
    frame_tipos.pack(fill="x", pady=(4, 14))
    for col, (icono, etiqueta, valor, _, _con_explorar) in enumerate(_TIPOS):
        frame_tipos.columnconfigure(col, weight=1)
        ttk.Radiobutton(
            frame_tipos,
            text=f"{icono}  {etiqueta}",
            variable=var_tipo,
            value=valor,
            bootstyle="toolbutton-primary",
        ).grid(row=0, column=col, padx=(0 if col == 0 else 6, 0), sticky="ew", ipady=6)

    # Ruta
    ttk.Label(body, text="Ruta / Dirección:", font=("Segoe UI", 9)).pack(anchor="w")
    ruta_actual = cfg_actual.get("ruta", "")
    var_ruta = StringVar(value=ruta_actual)
    frame_ruta = ttk.Frame(body)
    frame_ruta.pack(fill="x", pady=(3, 0))
    entry_ruta = ttk.Entry(frame_ruta, textvariable=var_ruta, font=("Segoe UI", 9))
    entry_ruta.pack(side="left", fill="x", expand=True, padx=(0, 8))
    btn_explorar = ttk.Button(
        frame_ruta, text="Explorar…", bootstyle="secondary-outline", width=10
    )
    btn_explorar.pack(side="left")

    def _actualizar_ui(*_):
        for _, _, v, ph, con_exp in _TIPOS:
            if v == var_tipo.get():
                btn_explorar.configure(state="normal" if con_exp else "disabled")
                break

    var_tipo.trace_add("write", _actualizar_ui)
    _actualizar_ui()

    def explorar():
        t = var_tipo.get()
        if t == "carpeta":
            r = filedialog.askdirectory(parent=win, title="Seleccionar carpeta de red")
        else:
            r = filedialog.askopenfilename(
                parent=win,
                title="Seleccionar archivo ejecutable o documento",
                filetypes=[
                    ("Ejecutables y documentos", "*.exe *.bat *.cmd *.lnk *.pyw *.ps1 *.rdp *.xlsx *.xls *.xlsm *.docx *.doc *.pdf"),
                    ("Aplicación (.exe)", "*.exe"),
                    ("Script (.bat/.cmd)", "*.bat *.cmd"),
                    ("Acceso directo (.lnk)", "*.lnk"),
                    ("Escritorio remoto (.rdp)", "*.rdp"),
                    ("PowerShell (.ps1)", "*.ps1"),
                    ("Excel (.xlsx/.xls/.xlsm)", "*.xlsx *.xls *.xlsm"),
                    ("Word (.docx/.doc)", "*.docx *.doc"),
                    ("PDF (.pdf)", "*.pdf"),
                    ("Todos los archivos", "*.*"),
                ],
            )
        if r:
            var_ruta.set(r)

    btn_explorar.configure(command=explorar)

    # Guardar / Cancelar
    ttk.Separator(win).pack(fill="x", padx=0, pady=(14, 0))
    frame_btns = ttk.Frame(win, padding=(22, 10, 22, 14))
    frame_btns.pack(fill="x")

    def guardar_sub():
        nombre = var_nombre.get().strip() or f"SUB {sub_idx}"
        ruta   = var_ruta.get().strip()
        tipo   = var_tipo.get()
        entry  = ctx.config.get(sub_key, {})
        entry["nombre"] = nombre
        entry["tipo"]   = tipo
        if ruta:
            entry["ruta"] = ruta
        ctx.config[sub_key] = entry
        ctx.save_config(ctx.config)
        win.destroy()

    ttk.Button(frame_btns, text="  Guardar  ",
               bootstyle="success", command=guardar_sub).pack(side="left", padx=(0, 8))
    ttk.Button(frame_btns, text="  Cancelar  ",
               bootstyle="secondary", command=win.destroy).pack(side="left")


def _clear_submenu_ref():
    # ANTI-REGRESION: ctx eliminado de la firma — esta función no usa ctx
    global _submenu_activo
    _submenu_activo = None


def _abrir_submenu(ctx, opcion, idx):
    """Abre la ventana de submenú cuando el usuario pulsa un botón con submenu activado."""
    global _submenu_activo
    # Cerrar submenú previo si sigue abierto
    if _submenu_activo is not None:
        try:
            _submenu_activo.destroy()
        except Exception:
            pass  # UI — ignorar silenciosamente
        _submenu_activo = None
    sub_cfg  = ctx.config.get(opcion, {}).get("submenu", {})
    count    = sub_cfg.get("count", 5)
    nombre_p = ctx.config.get(opcion, {}).get("nombre", f"Opción {idx}")

    COLS = min(5, count)
    rows = (count + COLS - 1) // COLS

    BTN_W = 170
    BTN_H = 72
    PAD   = 10
    HDR_H = 52
    FTR_H = 20

    # FIX: evita el borde blanco inicial de los botones (parpadeo blanco->negro al arrancar)
    ctx.app.style.configure(
        "SubBtn.TButton",
        background=ctx.app.style.colors.info,
        bordercolor=ctx.app.style.colors.info,
        lightcolor=ctx.app.style.colors.info,
        darkcolor=ctx.app.style.colors.info,
        relief="flat",
        borderwidth=0,
        focusthickness=0,
    )

    win_w = COLS * (BTN_W + PAD) + PAD * 2
    win_h = rows * (BTN_H + PAD) + PAD * 2 + HDR_H + FTR_H

    sw = ctx.app.winfo_screenwidth()
    sh = ctx.app.winfo_screenheight()
    wx = (sw - win_w) // 2
    wy = (sh - win_h) // 2

    win = ttk.Toplevel()
    _submenu_activo = win
    win.protocol("WM_DELETE_WINDOW", lambda: (_clear_submenu_ref(), win.destroy()))
    win.title(f"▶  {nombre_p}")
    win.geometry(f"{win_w}x{win_h}+{wx}+{wy}")
    win.resizable(False, False)
    win.attributes("-topmost", True)
    _apply_icon(win)

    # Cabecera compacta
    hdr = ttk.Frame(win, padding=(14, 8, 14, 4))
    hdr.pack(fill="x")
    ttk.Label(hdr, text=f"▶  {nombre_p}",
              font=("Segoe UI", 11, "bold")).pack(side="left")
    ttk.Button(hdr, text="✕", bootstyle="secondary", width=3,
               command=lambda: (_clear_submenu_ref(), win.destroy())).pack(side="right")
    ttk.Separator(win).pack(fill="x")

    # Grid de subbotones
    grid_f = ttk.Frame(win, padding=(PAD, PAD, PAD, PAD))
    grid_f.pack(fill="both", expand=True)
    for c in range(COLS):
        grid_f.columnconfigure(c, weight=1, uniform="sc")

    _sub_labels = {}

    for i in range(1, count + 1):
        sub_key = f"{opcion}_sub_{i:02d}"
        sub_nombre = ctx.config.get(sub_key, {}).get("nombre", f"SUB {i}")
        r = (i - 1) // COLS
        c = (i - 1) % COLS

        cell = ttk.Frame(grid_f)
        cell.grid(row=r, column=c, padx=5, pady=5, sticky="nsew")
        grid_f.rowconfigure(r, weight=1)
        cell.rowconfigure(0, weight=1)
        cell.columnconfigure(0, weight=1)

        var_sub = StringVar(value=sub_nombre)
        _sub_labels[sub_key] = var_sub

        btn = ttk.Button(cell, bootstyle="info",
                         style="SubBtn.TButton",
                         command=lambda sk=sub_key, si=i: _ejecutar_sub(ctx, sk, si, win, _sub_labels, nombre_p))
        btn.grid(row=0, column=0, sticky="nsew", ipady=6)

        lbl = ttk.Label(
            cell,
            textvariable=var_sub,
            wraplength=BTN_W - 20,
            font=("Segoe UI", 10, "bold"),
            anchor="center", justify="center",
            background=ctx.app.style.colors.info,
            foreground="white",
            cursor="hand2",
        )
        lbl.grid(row=0, column=0, sticky="nsew", padx=4, pady=3)
        lbl.bind("<Button-1>",
                 lambda e, sk=sub_key, si=i: _ejecutar_sub(ctx, sk, si, win, _sub_labels, nombre_p))
        lbl.bind("<Enter>", lambda e, lw=lbl: lw.configure(background=ctx.app.style.colors.primary))
        lbl.bind("<Leave>", lambda e, lw=lbl: lw.configure(background=ctx.app.style.colors.info))

    win.bind("<Escape>", lambda e: (_clear_submenu_ref(), win.destroy()))


def _ejecutar_sub(ctx, sub_key, sub_idx, parent_win, sub_labels, nombre_padre):
    """Ejecuta una subopción o abre su configuración si no está definida."""
    if sub_key not in ctx.config or "ruta" not in ctx.config[sub_key]:
        def _post_config():
            # Actualizar label en la ventana de submenú si sigue abierta
            if sub_key in sub_labels and sub_key in ctx.config:
                sub_labels[sub_key].set(ctx.config[sub_key].get("nombre", f"SUB {sub_idx}"))
        _ventana_config_sub(ctx, sub_key, sub_idx, nombre_padre)
        # Programar actualización tras cerrar ctx.config
        parent_win.after(500, _post_config)
        return
    parent_win.destroy()
    _clear_submenu_ref()
    _lanzar_ruta(ctx.config[sub_key]["ruta"], ctx.config[sub_key].get("tipo", "carpeta"))
