"""
ui/agenda.py
Ventana «Agenda de Avisos»: lista de recordatorios, alta y edición de avisos.
Extraída de main_agenda.py en v4.18.08 (antes, abrir_agenda() era una función de ~470 líneas allí).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Recibe el AppContext (ctx): usa ctx.agenda_data y ctx.save_agenda.
"""
from datetime import datetime
from tkinter import StringVar, messagebox

import ttkbootstrap as ttk

import negocio.alertas as _alertas_mod
from negocio.alertas import _descripcion_aviso
from ui.assets import _apply_icon
from ui.colores import LIGHT
from ui.selector_fecha_hora import campo_fecha, campo_hora
from utils.fechas import _iso_a_ui, _ui_a_iso
from services import sincro_agenda   # (v4.18.66) agenda sincronizada con Control de Pedidos


def abrir_agenda(ctx):
    """Ventana principal de avisos/recordatorios."""
    win = ttk.Toplevel()
    win.title("📅 Agenda de Avisos")
    win.resizable(True, False)   # redimensionable en horizontal
    _apply_icon(win)

    # ── Compartido entre "Nuevo Aviso" y "Editar Aviso" ─────────────────────
    # ANTI-REGRESION (limpieza 2026-07-21): antes cada ventana definía su
    # propia copia idéntica de _OPCIONES_REP y su propio _on_rep_change casi
    # idéntico — al añadir el tipo "anual" (v4.8.12) hubo que tocar los dos
    # sitios a mano. Ahora hay uno solo de cada, y las dos ventanas lo usan.
    _OPCIONES_REP = [
        ("ninguna",    "Sin repetición  (una sola vez)"),
        ("cada_30min", "Cada 30 minutos"),
        ("cada_hora",  "Cada hora"),
        ("diario",     "Diariamente"),
        ("semanal",    "Semanalmente  (mismo día de la semana)"),
        ("mensual",    "Mensualmente  (mismo día del mes)"),
        ("anual",      "Anualmente  (mismo día y mes)"),
    ]

    def _aplicar_rep_ui(rep, lbl_hora_var, lbl_fecha, campo_h=None):
        """Ajusta la etiqueta de hora y el color de la etiqueta de fecha
        según el tipo de repetición elegido. Común a ambas ventanas.
        (v4.18.14) En «cada 30 minutos» y «cada hora» solo cuenta el minuto:
        la rueda de las horas se desactiva."""
        if rep in ("cada_30min", "cada_hora"):
            lbl_hora_var.set("Minuto de disparo (la hora no se usa):")
            lbl_fecha.configure(foreground="gray")
            if campo_h is not None:
                campo_h.horas.configure(state="disabled")
        else:
            lbl_hora_var.set("Hora:")
            lbl_fecha.configure(foreground="")
            if campo_h is not None:
                campo_h.horas.configure(state="normal")

    _aw = 860                    # ancho inicial ampliado
    _aw_min = 720                # mínimo para que quepan siempre los botones
    _sw = win.winfo_screenwidth()
    _sh = win.winfo_screenheight()
    win.minsize(_aw_min, 200)

    main_frame = ttk.Frame(win, padding=(20, 16, 20, 12))
    main_frame.pack(fill="both", expand=True)

    ttk.Label(main_frame, text="📅  Mis Recordatorios",
              font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 10))
    ttk.Separator(win).pack(fill="x")

    # ── Lista con scroll ──────────────────────────────────
    list_frame = ttk.Frame(main_frame)
    list_frame.pack(fill="both", expand=True, pady=(10, 0))

    canvas = ttk.Canvas(list_frame, highlightthickness=0)
    scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = ttk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    _canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # ANTI-REGRESION (reportado 2026-07-21): sin esto, el ancho de
    # scrollable_frame lo decide su contenido más ancho (el título del
    # aviso más largo que haya en ese momento), no el ancho real del
    # canvas — por eso las filas "a veces sí" ocupaban todo el ancho (si
    # coincidían con ser las más anchas) y otras veces se quedaban cortas.
    # Al redimensionar el canvas (incluida la primera vez que se dibuja),
    # se fuerza el ancho de la ventana interna a igualar el del canvas, y
    # cada fila (empaquetada con fill="x") sí ocupa entonces todo el ancho
    # visible, sin importar lo larga o corta que sea su propia etiqueta.
    def _ajustar_ancho_interno(event):
        canvas.itemconfig(_canvas_window, width=event.width)
    canvas.bind("<Configure>", _ajustar_ancho_interno)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # ANTI-REGRESION (reportado 2026-07-21): la rueda del ratón no movía
    # la lista porque el canvas nunca recibía el evento <MouseWheel> — solo
    # respondía si se arrastraba la barra de scroll a mano. Se enlaza
    # mientras el puntero está DENTRO de esta ventana (bind_all, pero solo
    # entre <Enter>/<Leave> del propio canvas) para no robarle la rueda del
    # ratón a cualquier otra ventana que esté abierta al mismo tiempo.
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _activar_scroll_raton(event=None):
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _desactivar_scroll_raton(event=None):
        canvas.unbind_all("<MouseWheel>")

    canvas.bind("<Enter>", _activar_scroll_raton)
    canvas.bind("<Leave>", _desactivar_scroll_raton)
    win.bind("<Destroy>", lambda e: _desactivar_scroll_raton())

    # Etiquetas legibles para cada modo de repetición (solo para esta lista;
    # la descripción completa de cada aviso la genera _descripcion_aviso,
    # importada de negocio.alertas — ver cabecera del fichero. ANTI-REGRESION
    # (limpieza 2026-07-21): existía una copia local de _descripcion_aviso
    # aquí mismo que TAPABA la importada sin usarla, con la lógica de
    # repetición duplicada en los dos sitios — cualquier cambio futuro (como
    # el tipo "anual") había que aplicarlo dos veces o se quedaba a medias.
    _REP_LABEL = {
        "ninguna":     "Sin repetición",
        "cada_30min":  "↺ Cada 30 min",
        "cada_hora":   "↺ Cada hora",
        "diario":      "↺ Diario",
        "semanal":     "↺ Semanal",
        "mensual":     "↺ Mensual",
        "anual":       "↺ Anual",
    }

    def cargar_avisos():
        for w in scrollable_frame.winfo_children():
            w.destroy()
        avisos = ctx.agenda_data.get("avisos", [])
        avisos.sort(key=lambda x: (x.get("repeticion","ninguna") != "ninguna",
                                   x["hora"], x["fecha"]))
        if not avisos:
            ttk.Label(scrollable_frame,
                      text="No hay avisos programados.",
                      foreground=LIGHT).pack(pady=20)
            return
        for i, aviso in enumerate(avisos):
            rep      = aviso.get("repeticion", "ninguna")
            es_rep   = rep != "ninguna"
            # ANTI-REGRESION (Fase 3.7g): indicador visual de aviso desactivado
            activo   = aviso.get("activo", True)
            if not activo:
                # Aviso desactivado: frame gris oscuro, texto apagado
                estilo_frame = "dark"
                color_texto  = "#888888"
                fuente_texto = ("Segoe UI", 10, "overstrike")  # tachado
            elif es_rep:
                estilo_frame = "info"
                color_texto  = None   # color por defecto del theme
                fuente_texto = ("Segoe UI", 10, "bold")
            else:
                estilo_frame = "secondary"
                color_texto  = None
                fuente_texto = ("Segoe UI", 10, "bold")
            f = ttk.Frame(scrollable_frame,
                          bootstyle=estilo_frame,
                          padding=(10, 6))
            f.pack(fill="x", pady=2, padx=4)
            # Botones y badges PRIMERO (side=right) para que el label no los desplace
            if not activo:
                # Badge "DESACTIVADO" con botón de reactivar
                ttk.Label(f, text="⏸ DESACTIVADO",
                          font=("Segoe UI", 8, "bold"),
                          foreground="#FF9900",
                          bootstyle="inverse-dark").pack(side="right", padx=(4, 0))
                ttk.Button(
                    f, text="▶", bootstyle="success-outline", width=3,
                    command=lambda ix=i: _reactivar_aviso(ix)
                ).pack(side="right", padx=(0, 2))
            elif es_rep:
                ttk.Label(f, text=_REP_LABEL.get(rep, rep),
                          font=("Segoe UI", 8),
                          bootstyle="inverse-info").pack(side="right", padx=(4, 0))
            ttk.Button(
                f, text="🗑", bootstyle="danger-outline", width=3,
                command=lambda ix=i: _eliminar_aviso(ix)
            ).pack(side="right")
            ttk.Button(
                f, text="✏", bootstyle="warning-outline", width=3,
                command=lambda ix=i: _editar_aviso(ix)
            ).pack(side="right", padx=(0, 4))
            # Label DESPUÉS con wraplength para que no desborde
            lbl_kw = dict(font=fuente_texto,
                          wraplength=max(400, win.winfo_width() - 200),
                          anchor="w")
            if color_texto:
                lbl_kw["foreground"] = color_texto
            ttk.Label(f, text=_descripcion_aviso(aviso), **lbl_kw).pack(
                side="left", fill="x", expand=True)

    def _eliminar_aviso(idx):
        # (v4.18.66) Se borra por su id, no por la posición: mientras se pregunta puede llegar un cambio de otro PC.
        aviso = ctx.agenda_data.get("avisos", [])[idx]
        if messagebox.askyesno("Confirmar", "¿Eliminar este aviso?", parent=win):
            sincro_agenda.quitar(ctx.agenda_data.get("avisos", []), aviso)
            ctx.save_agenda(ctx.agenda_data)
            cargar_avisos()

    def _reactivar_aviso(idx):
        """Reactiva un aviso desactivado — ANTI-REGRESION (Fase 3.7g)."""
        aviso = ctx.agenda_data.get("avisos", [])[idx]
        nombre = aviso.get("titulo", "este aviso")
        if messagebox.askyesno("Reactivar aviso",
                               f"¿Reactivar '{nombre}'?\n\nVolverá a dispararse según su programación.",
                               parent=win):
            aviso = sincro_agenda.actual(ctx.agenda_data.get("avisos", []), aviso) or aviso
            aviso["activo"] = True
            ctx.save_agenda(ctx.agenda_data)
            cargar_avisos()

    def _editar_aviso(idx):
        """Abre ventana de edición para el aviso en la posición idx."""
        aviso_actual = ctx.agenda_data.get("avisos", [])[idx]
        ev = ttk.Toplevel()
        ev.title("Editar Aviso")
        ev.resizable(False, False)
        _apply_icon(ev)

        _ew = 460
        body = ttk.Frame(ev, padding=(20, 14, 20, 0))
        body.pack(fill="both", expand=True)

        # ── Título ────────────────────────────────────────────
        ttk.Label(body, text="Título:", font=("Segoe UI", 9)).pack(anchor="w")
        v_tit = StringVar(value=aviso_actual.get("titulo", ""))
        ttk.Entry(body, textvariable=v_tit, font=("Segoe UI", 10)).pack(fill="x", pady=(3, 12))

        # ── Repetición ────────────────────────────────────────
        ttk.Label(body, text="Repetición:", font=("Segoe UI", 9)).pack(anchor="w")
        v_rep = StringVar(value=aviso_actual.get("repeticion", "ninguna"))
        frm_rep = ttk.Frame(body)
        frm_rep.pack(fill="x", pady=(3, 12))
        for val, lbl in _OPCIONES_REP:
            ttk.Radiobutton(frm_rep, text=lbl, variable=v_rep, value=val,
                            bootstyle="toolbutton-primary"
                            ).pack(anchor="w", pady=1)

        # ── Fecha ─────────────────────────────────────────────
        lbl_fecha = ttk.Label(body, text="Fecha de inicio:",
                              font=("Segoe UI", 9))
        lbl_fecha.pack(anchor="w")
        v_fec = StringVar(value=_iso_a_ui(aviso_actual.get("fecha", datetime.now().strftime("%Y-%m-%d"))))
        campo_fecha(body, v_fec)   # (v4.18.14) con calendario 📅

        # ── Hora ──────────────────────────────────────────────
        lbl_hora_var = StringVar(value="Hora:")
        ttk.Label(body, textvariable=lbl_hora_var,
                  font=("Segoe UI", 9)).pack(anchor="w")
        v_hor = StringVar(value=aviso_actual.get("hora", datetime.now().strftime("%H:%M")))
        campo_h = campo_hora(body, v_hor)   # (v4.18.14) ruedas de horas y minutos, sin escribir «:»

        # ── Mensaje ───────────────────────────────────────────
        ttk.Label(body, text="Mensaje (opcional):", font=("Segoe UI", 9)).pack(anchor="w")
        v_msg = StringVar(value=aviso_actual.get("mensaje", ""))
        ttk.Entry(body, textvariable=v_msg, font=("Segoe UI", 10)).pack(fill="x", pady=(3, 12))

        # ── Antelación del aviso ───────────────────────────────
        ttk.Label(body, text="⏰  Avisar con antelación:",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ant_frame = ttk.Frame(body)
        ant_frame.pack(fill="x", pady=(4, 0))

        ant_val = aviso_actual.get("antelacion", {})
        v_ant_dias = StringVar(value=str(ant_val.get("dias", 0)))
        v_ant_horas = StringVar(value=str(ant_val.get("horas", 0)))
        v_ant_mins = StringVar(value=str(ant_val.get("minutos", 0)))

        ttk.Label(ant_frame, text="Días:", font=("Segoe UI", 9)).grid(row=0, column=0, padx=(0,2))
        ttk.Spinbox(ant_frame, from_=0, to=365, textvariable=v_ant_dias,
                    width=5, state="readonly", bootstyle="info").grid(row=0, column=1, padx=(0,10))
        ttk.Label(ant_frame, text="Horas:", font=("Segoe UI", 9)).grid(row=0, column=2, padx=(0,2))
        ttk.Spinbox(ant_frame, from_=0, to=23, textvariable=v_ant_horas,
                    width=5, state="readonly", bootstyle="info").grid(row=0, column=3, padx=(0,10))
        ttk.Label(ant_frame, text="Minutos:", font=("Segoe UI", 9)).grid(row=0, column=4, padx=(0,2))
        ttk.Spinbox(ant_frame, from_=0, to=59, textvariable=v_ant_mins,
                    width=5, state="readonly", bootstyle="info").grid(row=0, column=5)

        var_err = StringVar()
        ttk.Label(body, textvariable=var_err,
                  font=("Segoe UI", 8, "bold"),
                  foreground="#e74c3c").pack(anchor="w", pady=(6, 0))

        # Actualizar etiqueta de hora según repetición
        def _on_rep_change(*_):
            _aplicar_rep_ui(v_rep.get(), lbl_hora_var, lbl_fecha, campo_h)

        v_rep.trace_add("write", _on_rep_change)
        _on_rep_change()  # Aplicar estado inicial

        def guardar_edicion():
            rep = v_rep.get()
            fecha_iso = _ui_a_iso(v_fec.get())
            try:
                datetime.strptime(f"{fecha_iso} {v_hor.get()}", "%Y-%m-%d %H:%M")
            except ValueError:
                var_err.set("⚠ Revisa la fecha (DD-MM-AAAA o el calendario 📅) y la hora.")
                return
            try:
                ant_d = int(v_ant_dias.get())
                ant_h = int(v_ant_horas.get())
                ant_m = int(v_ant_mins.get())
            except ValueError:
                ant_d = ant_h = ant_m = 0
            editado = {
                "titulo":     v_tit.get().strip() or "Aviso",
                "fecha":      fecha_iso,
                "hora":       v_hor.get(),
                "mensaje":    v_msg.get().strip(),
                "repeticion": rep,
                "activo":     aviso_actual.get("activo", True),
                "antelacion": {"dias": ant_d, "horas": ant_h, "minutos": ant_m},
            }
            # (v4.18.66) Que siga siendo el mismo elemento (mismo id) y en su sitio aunque otro PC haya cambiado la lista.
            sincro_agenda.reemplazar(ctx.agenda_data.setdefault("avisos", []), aviso_actual, editado, idx)
            ctx.save_agenda(ctx.agenda_data)
            ev.destroy()
            cargar_avisos()

        ttk.Separator(ev).pack(fill="x", pady=(10, 0))
        frame_btns = ttk.Frame(ev, padding=(20, 8, 20, 12))
        frame_btns.pack(fill="x")
        ttk.Button(frame_btns, text="  Guardar cambios  ",
                   bootstyle="warning", command=guardar_edicion).pack(side="left", padx=(0, 8))
        ttk.Button(frame_btns, text="  Cancelar  ",
                   bootstyle="secondary", command=ev.destroy).pack(side="left")

        ev.update_idletasks()
        _eh = ev.winfo_reqheight() + 10
        _sw2 = ev.winfo_screenwidth()
        _sh2 = ev.winfo_screenheight()
        ev.geometry(f"{_ew}x{_eh}+{(_sw2 - _ew)//2}+{(_sh2 - _eh)//2}")
        ev.grab_set()

    def _nuevo_aviso():
        nv = ttk.Toplevel()
        nv.title("Nuevo Aviso")
        nv.resizable(False, False)
        _apply_icon(nv)

        _nw = 460
        body = ttk.Frame(nv, padding=(20, 14, 20, 0))
        body.pack(fill="both", expand=True)

        # ── Título ────────────────────────────────────────────
        ttk.Label(body, text="Título:", font=("Segoe UI", 9)).pack(anchor="w")
        v_tit = StringVar()
        ttk.Entry(body, textvariable=v_tit, font=("Segoe UI", 10)).pack(fill="x", pady=(3, 12))

        # ── Repetición ────────────────────────────────────────
        ttk.Label(body, text="Repetición:", font=("Segoe UI", 9)).pack(anchor="w")
        v_rep = StringVar(value="ninguna")
        frm_rep = ttk.Frame(body)
        frm_rep.pack(fill="x", pady=(3, 12))
        for val, lbl in _OPCIONES_REP:
            ttk.Radiobutton(frm_rep, text=lbl, variable=v_rep, value=val,
                            bootstyle="toolbutton-primary"
                            ).pack(anchor="w", pady=1)

        # ── Fecha ─────────────────────────────────────────────
        lbl_fecha = ttk.Label(body, text="Fecha de inicio:",
                              font=("Segoe UI", 9))
        lbl_fecha.pack(anchor="w")
        v_fec = StringVar(value=datetime.now().strftime("%d-%m-%Y"))
        campo_fecha(body, v_fec)   # (v4.18.14) con calendario 📅

        # ── Hora ──────────────────────────────────────────────
        lbl_hora_var = StringVar(value="Hora:")
        ttk.Label(body, textvariable=lbl_hora_var,
                  font=("Segoe UI", 9)).pack(anchor="w")
        v_hor = StringVar(value=datetime.now().strftime("%H:%M"))
        campo_h = campo_hora(body, v_hor)   # (v4.18.14) ruedas de horas y minutos, sin escribir «:»

        # ── Mensaje ───────────────────────────────────────────
        ttk.Label(body, text="Mensaje (opcional):", font=("Segoe UI", 9)).pack(anchor="w")
        v_msg = StringVar()
        ttk.Entry(body, textvariable=v_msg, font=("Segoe UI", 10)).pack(fill="x", pady=(3, 12))

        # ── Antelación del aviso ───────────────────────────────
        ttk.Label(body, text="⏰  Avisar con antelación:",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w")
        ant_frame = ttk.Frame(body)
        ant_frame.pack(fill="x", pady=(4, 0))
        v_ant_dias  = StringVar(value="0")
        v_ant_horas = StringVar(value="0")
        v_ant_mins  = StringVar(value="0")
        ttk.Label(ant_frame, text="Días:", font=("Segoe UI", 9)).grid(row=0, column=0, padx=(0,2))
        ttk.Spinbox(ant_frame, from_=0, to=365, textvariable=v_ant_dias,
                    width=5, state="readonly", bootstyle="info").grid(row=0, column=1, padx=(0,10))
        ttk.Label(ant_frame, text="Horas:", font=("Segoe UI", 9)).grid(row=0, column=2, padx=(0,2))
        ttk.Spinbox(ant_frame, from_=0, to=23, textvariable=v_ant_horas,
                    width=5, state="readonly", bootstyle="info").grid(row=0, column=3, padx=(0,10))
        ttk.Label(ant_frame, text="Minutos:", font=("Segoe UI", 9)).grid(row=0, column=4, padx=(0,2))
        ttk.Spinbox(ant_frame, from_=0, to=59, textvariable=v_ant_mins,
                    width=5, state="readonly", bootstyle="info").grid(row=0, column=5)

        var_err = StringVar()
        ttk.Label(body, textvariable=var_err,
                  font=("Segoe UI", 8, "bold"),
                  foreground="#e74c3c").pack(anchor="w", pady=(6, 0))

        # Actualizar etiqueta de hora y visibilidad de fecha según repetición
        def _on_rep_change(*_):
            _aplicar_rep_ui(v_rep.get(), lbl_hora_var, lbl_fecha, campo_h)

        v_rep.trace_add("write", _on_rep_change)

        def guardar():
            rep = v_rep.get()
            fecha_iso = _ui_a_iso(v_fec.get())
            try:
                datetime.strptime(f"{fecha_iso} {v_hor.get()}", "%Y-%m-%d %H:%M")
            except ValueError:
                var_err.set("⚠ Revisa la fecha (DD-MM-AAAA o el calendario 📅) y la hora.")
                return
            try:
                ant_d = int(v_ant_dias.get())
                ant_h = int(v_ant_horas.get())
                ant_m = int(v_ant_mins.get())
            except ValueError:
                ant_d = ant_h = ant_m = 0
            nuevo = {
                "titulo":      v_tit.get().strip() or "Aviso",
                "fecha":       fecha_iso,
                "hora":        v_hor.get(),
                "mensaje":     v_msg.get().strip(),
                "repeticion":  rep,
                "activo":      True,
                "antelacion":  {"dias": ant_d, "horas": ant_h, "minutos": ant_m},
            }
            if "avisos" not in ctx.agenda_data:
                ctx.agenda_data["avisos"] = []
            ctx.agenda_data["avisos"].append(nuevo)
            ctx.save_agenda(ctx.agenda_data)
            nv.destroy()
            cargar_avisos()

        ttk.Separator(nv).pack(fill="x", pady=(10, 0))
        frame_btns = ttk.Frame(nv, padding=(20, 8, 20, 12))
        frame_btns.pack(fill="x")
        ttk.Button(frame_btns, text="  Guardar  ",
                   bootstyle="warning", command=guardar).pack(side="left", padx=(0, 8))
        ttk.Button(frame_btns, text="  Cancelar  ",
                   bootstyle="secondary", command=nv.destroy).pack(side="left")

        nv.update_idletasks()
        _nh = nv.winfo_reqheight() + 10
        nv.geometry(f"{_nw}x{_nh}+{(_sw - _nw)//2}+{(_sh - _nh)//2}")
        nv.grab_set()

    # ── Barra inferior ────────────────────────────────────
    ttk.Separator(win).pack(fill="x", pady=(10, 0))
    btn_bar = ttk.Frame(win, padding=(20, 8, 20, 12))
    btn_bar.pack(fill="x")
    ttk.Button(btn_bar, text="＋  Añadir Aviso",
               bootstyle="warning", command=_nuevo_aviso).pack(side="left", padx=(0, 8))
    ttk.Button(btn_bar, text="  Cerrar  ",
               bootstyle="secondary", command=win.destroy).pack(side="right")

    # ANTI-REGRESION (Fase 3.7g): registrar cargar_avisos como callback en alertas
    # para que _desactivar_evento() refresque la lista sin necesidad de cerrar y reabrir la ventana.
    _alertas_mod.on_agenda_changed = cargar_avisos
    sincro_agenda.registrar_refresco(win, cargar_avisos)   # (v4.18.66) cambios llegados de otro PC

    cargar_avisos()

    # Centrar con altura real tras construir todos los widgets
    win.update_idletasks()
    _ah = min(win.winfo_reqheight() + 10, _sh - 80)
    win.geometry(f"{_aw}x{_ah}+{(_sw - _aw)//2}+{(_sh - _ah)//2}")

    # Reajustar wraplength de los labels si el usuario redimensiona la ventana
    def _on_resize(event):
        if event.widget is win:
            new_wrap = max(400, event.width - 200)
            for f in scrollable_frame.winfo_children():
                for child in f.winfo_children():
                    if isinstance(child, ttk.Label) and child.cget("anchor") == "w":
                        try:
                            child.configure(wraplength=new_wrap)
                        except Exception:
                            pass  # UI — ignorar silenciosamente
    win.bind("<Configure>", _on_resize)

    win.grab_set()
