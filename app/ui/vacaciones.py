"""
app/ui/vacaciones.py
Ventana de gestión de periodos de vacaciones.
Extraído de main_agenda.py en Fase 3B.

Recibe AppContext (ctx) — sin globals.
"""
from datetime import datetime, date
import ttkbootstrap as ttk
from tkinter import messagebox, StringVar    # ANTI-REGRESION: StringVar era global de main_agenda
from ui.selector_fecha_hora import campo_fecha
from utils.fechas import _iso_a_ui, _ui_a_iso, _dias_entre

# Constantes de color — ANTI-REGRESION: eran globals de main_agenda
GOLD  = "#C9A84C"
LIGHT = "#D8E8F0"


def _ventana_vacaciones(ctx):   # ANTI-REGRESIÓN: firma corregida — antes era (parent=None) pero ctx se usaba como global inexistente → NameError → ventana ciega
    """Gestión de periodos de vacaciones anuales.
    Cabecera y redimensionado unificados con la ventana Agenda
    (abrir_agenda): título único, sin subtítulo, y horizontal resizable
    (v4.10.5 — el scroll/ancho de canvas ya se unificó en v4.10.4)."""
    vwin = ttk.Toplevel()
    vwin.title("🏖 Vacaciones")
    vwin.resizable(True, False)   # ANTI-REGRESIÓN: unificado con Agenda — redimensionable en horizontal
    ctx.apply_icon(vwin)

    _vw = 600
    _sw = vwin.winfo_screenwidth()
    _sh = vwin.winfo_screenheight()
    vwin.minsize(520, 200)

    main = ttk.Frame(vwin, padding=(20, 16, 20, 12))
    main.pack(fill="both", expand=True)
    ttk.Label(main, text="🏖  Periodos de Vacaciones",
              font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 10))
    ttk.Separator(vwin).pack(fill="x")

    # Scrollable list
    lf = ttk.Frame(main)
    lf.pack(fill="both", expand=True, pady=(10, 0))
    canvas = ttk.Canvas(lf, highlightthickness=0)
    sb     = ttk.Scrollbar(lf, orient="vertical", command=canvas.yview)
    sf     = ttk.Frame(canvas)
    sf.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    _canvas_window = canvas.create_window((0, 0), window=sf, anchor="nw")
    canvas.configure(yscrollcommand=sb.set)

    # ANTI-REGRESION (mismo patrón que Agenda, v4.8.9): sin esto, el ancho
    # de sf lo decide su contenido más ancho ya insertado, no el ancho real
    # del canvas — las filas se quedaban cortas salvo que coincidieran con
    # ser la más ancha del momento.
    def _ajustar_ancho_interno(event):
        canvas.itemconfig(_canvas_window, width=event.width)
    canvas.bind("<Configure>", _ajustar_ancho_interno)

    canvas.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    # ANTI-REGRESION (mismo patrón que Agenda, v4.8.9): la rueda del ratón
    # no movía la lista — solo se enlaza mientras el puntero está dentro
    # del canvas, para no robarle la rueda a otra ventana abierta a la vez.
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        return "break"

    def _activar_scroll_raton(event=None):
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _desactivar_scroll_raton(event=None):
        canvas.unbind_all("<MouseWheel>")

    canvas.bind("<Enter>", _activar_scroll_raton)
    canvas.bind("<Leave>", _desactivar_scroll_raton)
    vwin.bind("<Destroy>", lambda e: _desactivar_scroll_raton())

    def cargar():
        for w in sf.winfo_children():
            w.destroy()
        vacs  = ctx.agenda_data.get("vacaciones", [])
        vacs_sorted = sorted(vacs, key=lambda x: x["fecha_inicio"])
        total = sum(_dias_entre(v["fecha_inicio"], v["fecha_fin"]) for v in vacs_sorted)

        if not vacs_sorted:
            ttk.Label(sf, text="No hay periodos definidos.",
                      foreground=LIGHT).pack(pady=20)
        else:
            año_actual = None
            for i, vac in enumerate(vacs_sorted):
                año = vac["fecha_inicio"][:4]
                if año != año_actual:
                    año_actual = año
                    ttk.Label(sf, text=f"── {año} ──",
                              font=("Segoe UI", 9, "bold"),
                              foreground=GOLD).pack(anchor="w", pady=(8, 2), padx=4)
                dias = _dias_entre(vac["fecha_inicio"], vac["fecha_fin"])
                f = ttk.Frame(sf, bootstyle="success", padding=(10, 6))
                f.pack(fill="x", pady=2, padx=4)
                ttk.Label(f, text=f"🏖  {vac['titulo']}",
                          font=("Segoe UI", 10, "bold")).pack(side="left")
                fecha_ini_ui = _iso_a_ui(vac["fecha_inicio"])
                fecha_fin_ui = _iso_a_ui(vac["fecha_fin"])
                ant = vac.get("antelacion", {})
                ant_d = int(ant.get("dias", 0))
                ant_h = int(ant.get("horas", 0))
                ant_m = int(ant.get("minutos", 0))
                partes_ant = []
                if ant_d: partes_ant.append(f"{ant_d}d")
                if ant_h: partes_ant.append(f"{ant_h}h")
                if ant_m: partes_ant.append(f"{ant_m}min")
                ant_txt = f"  ⏰ -{' '.join(partes_ant)}" if partes_ant else ""
                ttk.Label(f,
                          text=f"  {fecha_ini_ui} → {fecha_fin_ui}  ({dias} d){ant_txt}",
                          font=("Segoe UI", 9)).pack(side="left")
                ttk.Button(f, text="🗑", bootstyle="danger-outline", width=3,
                           command=lambda ix=vacs.index(vac): _eliminar(ix)
                           ).pack(side="right")
                ttk.Button(f, text="✏", bootstyle="success-outline", width=3,
                           command=lambda ix=vacs.index(vac): _editar_periodo(ix)
                           ).pack(side="right", padx=(0, 4))

            ttk.Label(sf,
                      text=f"Total programado: {total} días",
                      font=("Segoe UI", 9, "bold"),
                      foreground=GOLD).pack(anchor="e", pady=(8, 2), padx=4)

    def _eliminar(idx):
        if messagebox.askyesno("Confirmar", "¿Eliminar este periodo?", parent=vwin):
            ctx.agenda_data.get("vacaciones", []).pop(idx)
            ctx.save_agenda(ctx.agenda_data)
            cargar()

    def _editar_periodo(idx):
        vac_actual = ctx.agenda_data.get("vacaciones", [])[idx]
        ew = ttk.Toplevel()
        ew.title("Editar Periodo")
        ew.resizable(False, False)
        ctx.apply_icon(ew)
        _epw = 420

        body = ttk.Frame(ew, padding=(20, 14, 20, 0))
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="Descripción:", font=("Segoe UI", 9)).pack(anchor="w")
        v_tit = StringVar(value=vac_actual.get("titulo", "Vacaciones"))
        ttk.Entry(body, textvariable=v_tit,
                  font=("Segoe UI", 10)).pack(fill="x", pady=(3, 12))

        ttk.Label(body, text="Fecha inicio:",
                  font=("Segoe UI", 9)).pack(anchor="w")
        v_ini = StringVar(value=_iso_a_ui(vac_actual.get("fecha_inicio", date.today().strftime("%Y-%m-%d"))))
        campo_fecha(body, v_ini, pady=(3, 12))   # (v4.18.14) con calendario 📅

        ttk.Label(body, text="Fecha fin:",
                  font=("Segoe UI", 9)).pack(anchor="w")
        v_fin = StringVar(value=_iso_a_ui(vac_actual.get("fecha_fin", date.today().strftime("%Y-%m-%d"))))
        campo_fecha(body, v_fin, pady=(3, 0))   # (v4.18.14) con calendario 📅

        # Contador de días en tiempo real
        v_dias = StringVar()
        ttk.Label(body, textvariable=v_dias,
                  font=("Segoe UI", 9, "bold"),
                  foreground=GOLD).pack(anchor="e", pady=(4, 0))

        def _upd_dias(*_):
            d = _dias_entre(_ui_a_iso(v_ini.get()), _ui_a_iso(v_fin.get()))
            v_dias.set(f"📅  {d} días naturales" if d > 0 else "")
        v_ini.trace_add("write", _upd_dias)
        v_fin.trace_add("write", _upd_dias)
        _upd_dias()

        # ── Antelación ────────────────────────────────────────
        ttk.Label(body, text="⏰  Avisar con antelación (antes del inicio):",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 0))
        ant_frame = ttk.Frame(body)
        ant_frame.pack(fill="x", pady=(4, 0))
        ant_val = vac_actual.get("antelacion", {})
        v_ant_dias  = StringVar(value=str(int(ant_val.get("dias",    0))))
        v_ant_horas = StringVar(value=str(int(ant_val.get("horas",   0))))
        v_ant_mins  = StringVar(value=str(int(ant_val.get("minutos", 0))))
        ttk.Label(ant_frame, text="Días:",    font=("Segoe UI", 9)).grid(row=0, column=0, padx=(0, 2))
        ttk.Spinbox(ant_frame, from_=0, to=365, textvariable=v_ant_dias,
                    width=5, state="readonly", bootstyle="success").grid(row=0, column=1, padx=(0, 10))
        ttk.Label(ant_frame, text="Horas:",   font=("Segoe UI", 9)).grid(row=0, column=2, padx=(0, 2))
        ttk.Spinbox(ant_frame, from_=0, to=23, textvariable=v_ant_horas,
                    width=5, state="readonly", bootstyle="success").grid(row=0, column=3, padx=(0, 10))
        ttk.Label(ant_frame, text="Minutos:", font=("Segoe UI", 9)).grid(row=0, column=4, padx=(0, 2))
        ttk.Spinbox(ant_frame, from_=0, to=59, textvariable=v_ant_mins,
                    width=5, state="readonly", bootstyle="success").grid(row=0, column=5)

        var_err = StringVar()
        ttk.Label(body, textvariable=var_err,
                  font=("Segoe UI", 8, "bold"),
                  foreground="#e74c3c").pack(anchor="w", pady=(6, 0))

        def guardar():
            try:
                d0 = datetime.strptime(_ui_a_iso(v_ini.get()), "%Y-%m-%d").date()
                d1 = datetime.strptime(_ui_a_iso(v_fin.get()), "%Y-%m-%d").date()
            except ValueError:
                var_err.set("⚠ Revisa la fecha (DD-MM-AAAA o el calendario 📅).")
                return
            if d1 < d0:
                var_err.set("⚠ La fecha fin debe ser igual o posterior al inicio.")
                return
            try:
                ant_d = int(v_ant_dias.get())
                ant_h = int(v_ant_horas.get())
                ant_m = int(v_ant_mins.get())
            except ValueError:
                ant_d = ant_h = ant_m = 0
            editado = {
                "titulo":       v_tit.get().strip() or "Vacaciones",
                "fecha_inicio": d0.strftime("%Y-%m-%d"),
                "fecha_fin":    d1.strftime("%Y-%m-%d"),
                "antelacion":   {"dias": ant_d, "horas": ant_h, "minutos": ant_m},
            }
            ctx.agenda_data.get("vacaciones", [])[idx] = editado
            ctx.save_agenda(ctx.agenda_data)
            ew.destroy()
            cargar()

        ttk.Separator(ew).pack(fill="x", pady=(10, 0))
        fb = ttk.Frame(ew, padding=(20, 8, 20, 12))
        fb.pack(fill="x")
        ttk.Button(fb, text="  Guardar  ",
                   bootstyle="warning", command=guardar).pack(side="left", padx=(0, 8))
        ttk.Button(fb, text="  Cancelar  ",
                   bootstyle="secondary", command=ew.destroy).pack(side="left")

        ew.update_idletasks()
        _eph = ew.winfo_reqheight() + 10
        _esw = ew.winfo_screenwidth()
        _esh = ew.winfo_screenheight()
        ew.geometry(f"{_epw}x{_eph}+{(_esw - _epw)//2}+{(_esh - _eph)//2}")
        ew.grab_set()

    def _nuevo_periodo():
        nw = ttk.Toplevel()
        nw.title("Nuevo Periodo")
        nw.resizable(False, False)
        ctx.apply_icon(nw)
        _npw = 420

        body = ttk.Frame(nw, padding=(20, 14, 20, 0))
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="Descripción:", font=("Segoe UI", 9)).pack(anchor="w")
        v_tit = StringVar(value="Vacaciones")
        ttk.Entry(body, textvariable=v_tit,
                  font=("Segoe UI", 10)).pack(fill="x", pady=(3, 12))

        ttk.Label(body, text="Fecha inicio:",
                  font=("Segoe UI", 9)).pack(anchor="w")
        v_ini = StringVar(value=date.today().strftime("%d-%m-%Y"))
        campo_fecha(body, v_ini, pady=(3, 12))   # (v4.18.14) con calendario 📅

        ttk.Label(body, text="Fecha fin:",
                  font=("Segoe UI", 9)).pack(anchor="w")
        v_fin = StringVar(value=date.today().strftime("%d-%m-%Y"))
        campo_fecha(body, v_fin, pady=(3, 0))   # (v4.18.14) con calendario 📅

        # Contador de días en tiempo real
        v_dias = StringVar()
        ttk.Label(body, textvariable=v_dias,
                  font=("Segoe UI", 9, "bold"),
                  foreground=GOLD).pack(anchor="e", pady=(4, 0))

        def _upd_dias(*_):
            d = _dias_entre(_ui_a_iso(v_ini.get()), _ui_a_iso(v_fin.get()))
            v_dias.set(f"📅  {d} días naturales" if d > 0 else "")
        v_ini.trace_add("write", _upd_dias)
        v_fin.trace_add("write", _upd_dias)
        _upd_dias()

        # ── Antelación del aviso de vacaciones ────────────────
        ttk.Label(body, text="⏰  Avisar con antelación (antes del inicio):",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(10, 0))
        ant_vac_frame = ttk.Frame(body)
        ant_vac_frame.pack(fill="x", pady=(4, 0))
        v_vant_dias  = StringVar(value="0")
        v_vant_horas = StringVar(value="0")
        v_vant_mins  = StringVar(value="0")
        ttk.Label(ant_vac_frame, text="Días:", font=("Segoe UI", 9)).grid(row=0, column=0, padx=(0,2))
        ttk.Spinbox(ant_vac_frame, from_=0, to=365, textvariable=v_vant_dias,
                    width=5, state="readonly", bootstyle="success").grid(row=0, column=1, padx=(0,10))
        ttk.Label(ant_vac_frame, text="Horas:", font=("Segoe UI", 9)).grid(row=0, column=2, padx=(0,2))
        ttk.Spinbox(ant_vac_frame, from_=0, to=23, textvariable=v_vant_horas,
                    width=5, state="readonly", bootstyle="success").grid(row=0, column=3, padx=(0,10))
        ttk.Label(ant_vac_frame, text="Minutos:", font=("Segoe UI", 9)).grid(row=0, column=4, padx=(0,2))
        ttk.Spinbox(ant_vac_frame, from_=0, to=59, textvariable=v_vant_mins,
                    width=5, state="readonly", bootstyle="success").grid(row=0, column=5)

        var_err = StringVar()
        ttk.Label(body, textvariable=var_err,
                  font=("Segoe UI", 8, "bold"),
                  foreground="#e74c3c").pack(anchor="w", pady=(6, 0))

        def guardar():
            try:
                d0 = datetime.strptime(_ui_a_iso(v_ini.get()), "%Y-%m-%d").date()
                d1 = datetime.strptime(_ui_a_iso(v_fin.get()), "%Y-%m-%d").date()
            except ValueError:
                var_err.set("⚠ Revisa la fecha (DD-MM-AAAA o el calendario 📅).")
                return
            if d1 < d0:
                var_err.set("⚠ La fecha fin debe ser igual o posterior al inicio.")
                return
            try:
                ant_d = int(v_vant_dias.get())
                ant_h = int(v_vant_horas.get())
                ant_m = int(v_vant_mins.get())
            except ValueError:
                ant_d = ant_h = ant_m = 0
            nuevo = {
                "titulo":       v_tit.get().strip() or "Vacaciones",
                "fecha_inicio": d0.strftime("%Y-%m-%d"),
                "fecha_fin":    d1.strftime("%Y-%m-%d"),
                "antelacion":   {"dias": ant_d, "horas": ant_h, "minutos": ant_m},
            }
            if "vacaciones" not in ctx.agenda_data:
                ctx.agenda_data["vacaciones"] = []
            ctx.agenda_data["vacaciones"].append(nuevo)
            ctx.save_agenda(ctx.agenda_data)
            nw.destroy()
            cargar()

        ttk.Separator(nw).pack(fill="x", pady=(10, 0))
        fb = ttk.Frame(nw, padding=(20, 8, 20, 12))
        fb.pack(fill="x")
        ttk.Button(fb, text="  Guardar  ",
                   bootstyle="warning", command=guardar).pack(side="left", padx=(0, 8))
        ttk.Button(fb, text="  Cancelar  ",
                   bootstyle="secondary", command=nw.destroy).pack(side="left")

        nw.update_idletasks()
        _nph = nw.winfo_reqheight() + 10
        nw.geometry(f"{_npw}x{_nph}+{(_sw - _npw)//2}+{(_sh - _nph)//2}")
        nw.grab_set()

    cargar()

    ttk.Separator(vwin).pack(fill="x", pady=(10, 0))
    bb = ttk.Frame(vwin, padding=(20, 8, 20, 12))
    bb.pack(fill="x")
    ttk.Button(bb, text="＋  Nuevo Periodo",
               bootstyle="warning", command=_nuevo_periodo).pack(side="left", padx=(0, 8))
    ttk.Button(bb, text="  Cerrar  ",
               bootstyle="secondary", command=vwin.destroy).pack(side="right")

    vwin.update_idletasks()
    _vh = min(vwin.winfo_reqheight() + 10, _sh - 80)
    vwin.geometry(f"{_vw}x{_vh}+{(_sw - _vw)//2}+{(_sh - _vh)//2}")

    # ANTI-REGRESIÓN: igual que en abrir_agenda — reajusta el wraplength de
    # las etiquetas de fila si el usuario ensancha la ventana (ahora
    # redimensionable en horizontal).
    def _on_resize(event):
        if event.widget is vwin:
            new_wrap = max(300, event.width - 160)
            for f in sf.winfo_children():
                for child in f.winfo_children():
                    if isinstance(child, ttk.Label) and child.cget("anchor") == "w":
                        try:
                            child.configure(wraplength=new_wrap)
                        except Exception:
                            pass  # UI — ignorar silenciosamente
    vwin.bind("<Configure>", _on_resize)

    vwin.grab_set()
