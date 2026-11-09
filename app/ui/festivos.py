"""
app/ui/festivos.py
Ventana de gestión de días festivos.
Extraído de main_agenda.py en Fase 3B.

Recibe AppContext (ctx) — sin globals.
"""
from datetime import datetime, date
import ttkbootstrap as ttk
from tkinter import messagebox, StringVar    # ANTI-REGRESION: StringVar era global de main_agenda
from ui.selector_fecha_hora import campo_fecha
from utils.fechas import _iso_a_ui, _ui_a_iso

# Constantes de color — ANTI-REGRESION: eran globals de main_agenda
GOLD  = "#C9A84C"
LIGHT = "#D8E8F0"


def _ventana_festivos(ctx):   # ANTI-REGRESIÓN: firma corregida — antes era (parent=None) pero ctx se usaba como global inexistente → NameError → ventana ciega
    """Gestión de días festivos.
    Cabecera y redimensionado unificados con la ventana Agenda
    (abrir_agenda): título único, sin subtítulo, y horizontal resizable
    (v4.10.5 — el scroll/ancho de canvas ya se unificó en v4.10.4)."""
    fwin = ttk.Toplevel()
    fwin.title("🎉 Festivos")
    fwin.resizable(True, False)   # ANTI-REGRESIÓN: unificado con Agenda — redimensionable en horizontal
    ctx.apply_icon(fwin)

    _fw = 560
    _sw = fwin.winfo_screenwidth()
    _sh = fwin.winfo_screenheight()
    fwin.minsize(480, 200)

    main = ttk.Frame(fwin, padding=(20, 16, 20, 12))
    main.pack(fill="both", expand=True)
    ttk.Label(main, text="🎉  Días Festivos",
              font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 10))
    ttk.Separator(fwin).pack(fill="x")

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
    fwin.bind("<Destroy>", lambda e: _desactivar_scroll_raton())

    def cargar():
        for w in sf.winfo_children():
            w.destroy()
        fests = ctx.agenda_data.get("festivos", [])
        fests_sorted = sorted(fests, key=lambda x: x["fecha"])
        total_fest = len(fests_sorted)

        if not fests_sorted:
            ttk.Label(sf, text="No hay festivos definidos.",
                      foreground=LIGHT).pack(pady=20)
        else:
            año_actual = None
            for i, fest in enumerate(fests_sorted):
                año = fest["fecha"][:4]
                if año != año_actual:
                    año_actual = año
                    ttk.Label(sf, text=f"── {año} ──",
                              font=("Segoe UI", 9, "bold"),
                              foreground=GOLD).pack(anchor="w", pady=(8, 2), padx=4)
                ant = fest.get("antelacion", {})
                ant_d = int(ant.get("dias", 0))
                ant_h = int(ant.get("horas", 0))
                ant_m = int(ant.get("minutos", 0))
                partes_ant = []
                if ant_d: partes_ant.append(f"{ant_d}d")
                if ant_h: partes_ant.append(f"{ant_h}h")
                if ant_m: partes_ant.append(f"{ant_m}min")
                ant_txt = f"  ⏰ -{' '.join(partes_ant)}" if partes_ant else ""
                frow = ttk.Frame(sf, bootstyle="danger", padding=(10, 6))
                frow.pack(fill="x", pady=2, padx=4)
                ttk.Label(frow, text=f"🎉  {fest['titulo']}",
                          font=("Segoe UI", 10, "bold")).pack(side="left")
                fecha_ui = _iso_a_ui(fest["fecha"])
                ttk.Label(frow,
                          text=f"  {fecha_ui}{ant_txt}",
                          font=("Segoe UI", 9)).pack(side="left")
                ttk.Button(frow, text="🗑", bootstyle="danger-outline", width=3,
                           command=lambda ix=fests.index(fest): _eliminar(ix)
                           ).pack(side="right")
                ttk.Button(frow, text="✏", bootstyle="warning-outline", width=3,
                           command=lambda ix=fests.index(fest): _editar_festivo(ix)
                           ).pack(side="right", padx=(0, 4))

            ttk.Label(sf,
                      text=f"Total festivos: {total_fest} día{'s' if total_fest != 1 else ''}",
                      font=("Segoe UI", 9, "bold"),
                      foreground=GOLD).pack(anchor="e", pady=(8, 2), padx=4)

    def _eliminar(idx):
        if messagebox.askyesno("Confirmar", "¿Eliminar este festivo?", parent=fwin):
            ctx.agenda_data.get("festivos", []).pop(idx)
            ctx.save_agenda(ctx.agenda_data)  # ANTI-REGRESIÓN: save_agenda no es global en módulo, usar ctx.save_agenda
            cargar()

    def _editar_festivo(idx):
        fest_actual = ctx.agenda_data.get("festivos", [])[idx]
        ew = ttk.Toplevel()
        ew.title("Editar Festivo")
        ew.resizable(False, False)
        ctx.apply_icon(ew)
        _epw = 420

        body = ttk.Frame(ew, padding=(20, 14, 20, 0))
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="Descripción:", font=("Segoe UI", 9)).pack(anchor="w")
        v_tit = StringVar(value=fest_actual.get("titulo", "Festivo"))
        ttk.Entry(body, textvariable=v_tit,
                  font=("Segoe UI", 10)).pack(fill="x", pady=(3, 12))

        ttk.Label(body, text="Fecha:",
                  font=("Segoe UI", 9)).pack(anchor="w")
        v_fecha = StringVar(value=_iso_a_ui(fest_actual.get("fecha", date.today().strftime("%Y-%m-%d"))))
        campo_fecha(body, v_fecha, pady=(3, 12))   # (v4.18.14) con calendario 📅

        # ── Antelación ────────────────────────────────────────
        ttk.Label(body, text="⏰  Avisar con antelación (antes del día):",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(6, 0))
        ant_frame = ttk.Frame(body)
        ant_frame.pack(fill="x", pady=(4, 0))
        ant_val = fest_actual.get("antelacion", {})
        v_ant_dias  = StringVar(value=str(int(ant_val.get("dias",    0))))
        v_ant_horas = StringVar(value=str(int(ant_val.get("horas",   0))))
        v_ant_mins  = StringVar(value=str(int(ant_val.get("minutos", 0))))
        ttk.Label(ant_frame, text="Días:",    font=("Segoe UI", 9)).grid(row=0, column=0, padx=(0, 2))
        ttk.Spinbox(ant_frame, from_=0, to=365, textvariable=v_ant_dias,
                    width=5, state="readonly", bootstyle="danger").grid(row=0, column=1, padx=(0, 10))
        ttk.Label(ant_frame, text="Horas:",   font=("Segoe UI", 9)).grid(row=0, column=2, padx=(0, 2))
        ttk.Spinbox(ant_frame, from_=0, to=23, textvariable=v_ant_horas,
                    width=5, state="readonly", bootstyle="danger").grid(row=0, column=3, padx=(0, 10))
        ttk.Label(ant_frame, text="Minutos:", font=("Segoe UI", 9)).grid(row=0, column=4, padx=(0, 2))
        ttk.Spinbox(ant_frame, from_=0, to=59, textvariable=v_ant_mins,
                    width=5, state="readonly", bootstyle="danger").grid(row=0, column=5)

        var_err = StringVar()
        ttk.Label(body, textvariable=var_err,
                  font=("Segoe UI", 8, "bold"),
                  foreground="#e74c3c").pack(anchor="w", pady=(6, 0))

        def guardar():
            try:
                d0 = datetime.strptime(_ui_a_iso(v_fecha.get()), "%Y-%m-%d").date()
            except ValueError:
                var_err.set("⚠ Revisa la fecha (DD-MM-AAAA o el calendario 📅).")
                return
            try:
                ant_d = int(v_ant_dias.get())
                ant_h = int(v_ant_horas.get())
                ant_m = int(v_ant_mins.get())
            except ValueError:
                ant_d = ant_h = ant_m = 0
            editado = {
                "titulo":     v_tit.get().strip() or "Festivo",
                "fecha":      d0.strftime("%Y-%m-%d"),
                "antelacion": {"dias": ant_d, "horas": ant_h, "minutos": ant_m},
            }
            ctx.agenda_data.get("festivos", [])[idx] = editado
            ctx.save_agenda(ctx.agenda_data)  # ANTI-REGRESIÓN: save_agenda no es global en módulo, usar ctx.save_agenda
            ew.destroy()
            cargar()

        ttk.Separator(ew).pack(fill="x", pady=(10, 0))
        fb = ttk.Frame(ew, padding=(20, 8, 20, 12))
        fb.pack(fill="x")
        ttk.Button(fb, text="  Guardar  ",
                   bootstyle="danger", command=guardar).pack(side="left", padx=(0, 8))
        ttk.Button(fb, text="  Cancelar  ",
                   bootstyle="secondary", command=ew.destroy).pack(side="left")

        ew.update_idletasks()
        _eph = ew.winfo_reqheight() + 10
        _esw = ew.winfo_screenwidth()
        _esh = ew.winfo_screenheight()
        ew.geometry(f"{_epw}x{_eph}+{(_esw - _epw)//2}+{(_esh - _eph)//2}")
        ew.grab_set()

    def _nuevo_festivo():
        nw = ttk.Toplevel()
        nw.title("Nuevo Festivo")
        nw.resizable(False, False)
        ctx.apply_icon(nw)
        _npw = 420

        body = ttk.Frame(nw, padding=(20, 14, 20, 0))
        body.pack(fill="both", expand=True)

        ttk.Label(body, text="Descripción:", font=("Segoe UI", 9)).pack(anchor="w")
        v_tit = StringVar(value="Festivo")
        ttk.Entry(body, textvariable=v_tit,
                  font=("Segoe UI", 10)).pack(fill="x", pady=(3, 12))

        ttk.Label(body, text="Fecha:",
                  font=("Segoe UI", 9)).pack(anchor="w")
        v_fecha = StringVar(value=date.today().strftime("%d-%m-%Y"))
        campo_fecha(body, v_fecha, pady=(3, 12))   # (v4.18.14) con calendario 📅

        ttk.Label(body, text="⏰  Avisar con antelación (antes del día):",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(6, 0))
        ant_frame = ttk.Frame(body)
        ant_frame.pack(fill="x", pady=(4, 0))
        v_ant_dias  = StringVar(value="0")
        v_ant_horas = StringVar(value="0")
        v_ant_mins  = StringVar(value="0")
        ttk.Label(ant_frame, text="Días:",    font=("Segoe UI", 9)).grid(row=0, column=0, padx=(0, 2))
        ttk.Spinbox(ant_frame, from_=0, to=365, textvariable=v_ant_dias,
                    width=5, state="readonly", bootstyle="danger").grid(row=0, column=1, padx=(0, 10))
        ttk.Label(ant_frame, text="Horas:",   font=("Segoe UI", 9)).grid(row=0, column=2, padx=(0, 2))
        ttk.Spinbox(ant_frame, from_=0, to=23, textvariable=v_ant_horas,
                    width=5, state="readonly", bootstyle="danger").grid(row=0, column=3, padx=(0, 10))
        ttk.Label(ant_frame, text="Minutos:", font=("Segoe UI", 9)).grid(row=0, column=4, padx=(0, 2))
        ttk.Spinbox(ant_frame, from_=0, to=59, textvariable=v_ant_mins,
                    width=5, state="readonly", bootstyle="danger").grid(row=0, column=5)

        var_err = StringVar()
        ttk.Label(body, textvariable=var_err,
                  font=("Segoe UI", 8, "bold"),
                  foreground="#e74c3c").pack(anchor="w", pady=(6, 0))

        def guardar():
            try:
                d0 = datetime.strptime(_ui_a_iso(v_fecha.get()), "%Y-%m-%d").date()
            except ValueError:
                var_err.set("⚠ Revisa la fecha (DD-MM-AAAA o el calendario 📅).")
                return
            try:
                ant_d = int(v_ant_dias.get())
                ant_h = int(v_ant_horas.get())
                ant_m = int(v_ant_mins.get())
            except ValueError:
                ant_d = ant_h = ant_m = 0
            nuevo = {
                "titulo":     v_tit.get().strip() or "Festivo",
                "fecha":      d0.strftime("%Y-%m-%d"),
                "antelacion": {"dias": ant_d, "horas": ant_h, "minutos": ant_m},
            }
            if "festivos" not in ctx.agenda_data:
                ctx.agenda_data["festivos"] = []
            ctx.agenda_data["festivos"].append(nuevo)
            ctx.save_agenda(ctx.agenda_data)  # ANTI-REGRESIÓN: save_agenda no es global en módulo, usar ctx.save_agenda
            nw.destroy()
            cargar()

        ttk.Separator(nw).pack(fill="x", pady=(10, 0))
        fb = ttk.Frame(nw, padding=(20, 8, 20, 12))
        fb.pack(fill="x")
        ttk.Button(fb, text="  Guardar  ",
                   bootstyle="danger", command=guardar).pack(side="left", padx=(0, 8))
        ttk.Button(fb, text="  Cancelar  ",
                   bootstyle="secondary", command=nw.destroy).pack(side="left")

        nw.update_idletasks()
        _nph = nw.winfo_reqheight() + 10
        _sw2 = nw.winfo_screenwidth()
        _sh2 = nw.winfo_screenheight()
        nw.geometry(f"{_npw}x{_nph}+{(_sw2 - _npw)//2}+{(_sh2 - _nph)//2}")
        nw.grab_set()

    cargar()

    ttk.Separator(fwin).pack(fill="x", pady=(10, 0))
    bb = ttk.Frame(fwin, padding=(20, 8, 20, 12))
    bb.pack(fill="x")
    ttk.Button(bb, text="＋  Nuevo Festivo",
               bootstyle="danger", command=_nuevo_festivo).pack(side="left", padx=(0, 8))
    ttk.Button(bb, text="  Cerrar  ",
               bootstyle="secondary", command=fwin.destroy).pack(side="right")

    fwin.update_idletasks()
    _fh = min(fwin.winfo_reqheight() + 10, _sh - 80)
    fwin.geometry(f"{_fw}x{_fh}+{(_sw - _fw)//2}+{(_sh - _fh)//2}")

    # ANTI-REGRESIÓN: igual que en abrir_agenda — reajusta el wraplength de
    # las etiquetas de fila si el usuario ensancha la ventana (ahora
    # redimensionable en horizontal).
    def _on_resize(event):
        if event.widget is fwin:
            new_wrap = max(300, event.width - 160)
            for f in sf.winfo_children():
                for child in f.winfo_children():
                    if isinstance(child, ttk.Label) and child.cget("anchor") == "w":
                        try:
                            child.configure(wraplength=new_wrap)
                        except Exception:
                            pass  # UI — ignorar silenciosamente
    fwin.bind("<Configure>", _on_resize)

    fwin.grab_set()
