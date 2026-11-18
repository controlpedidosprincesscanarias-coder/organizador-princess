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
from services import sincro_agenda   # (v4.18.66) agenda sincronizada con Control de Pedidos
import tkinter as tk
from ui import estilo_calendario as E          # (v4.18.72) aspecto nuevo
from utils import textos_calendario as T

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
    vwin.resizable(True, True)   # ANTI-REGRESIÓN: unificado con Agenda — redimensionable en horizontal
    ctx.apply_icon(vwin)

    _vw = 640
    _sw = vwin.winfo_screenwidth()
    _sh = vwin.winfo_screenheight()
    vwin.minsize(520, 200)

    # (v4.18.72) Rediseño: cabecera con resumen, tarjetas con bloque de fecha y estado (ui/estilo_calendario.py).
    vwin.configure(background=E.FONDO)
    v_resumen = StringVar()
    E.cabecera(vwin, "🏖", "Vacaciones", v_resumen)
    sf = E.lista_desplazable(vwin, vwin)

    def cargar():
        for w in sf.winfo_children():
            w.destroy()
        vacs  = ctx.agenda_data.get("vacaciones", [])
        hoy   = date.today()
        v_resumen.set(T.resumen_vacaciones(vacs, hoy))
        vacs_sorted = sorted(vacs, key=lambda x: x["fecha_inicio"])

        if not vacs_sorted:
            E.vacia(sf, "No hay periodos de vacaciones.\nPulsa «+  Nuevo Periodo» para añadir el primero.")
            return
        año_actual = None
        for vac in vacs_sorted:
            año = vac["fecha_inicio"][:4]
            if año != año_actual:
                año_actual = año
                total = sum(_dias_entre(v["fecha_inicio"], v["fecha_fin"])
                            for v in vacs_sorted if v["fecha_inicio"][:4] == año)
                E.separador_anio(sf, año, T.dias(total))
            estado = T.estado_periodo(vac["fecha_inicio"], vac["fecha_fin"], hoy)
            pasado = estado == "pasado"
            _, cuerpo = E.tarjeta(sf, E.VERDE, apagado=pasado)
            E.bloque_fecha(cuerpo, vac["fecha_inicio"], E.VERDE, apagado=pasado).pack(side="left", padx=(0, 14))

            ix = vacs.index(vac)
            E.botones_fila(cuerpo, lambda ix=ix: _editar_periodo(ix),
                           lambda ix=ix: _eliminar(ix)).pack(side="right")

            texto = tk.Frame(cuerpo, bg=E.TARJETA)
            texto.pack(side="left", fill="x", expand=True)
            fila1 = tk.Frame(texto, bg=E.TARJETA)
            fila1.pack(fill="x")
            E.etiqueta(fila1, vac.get("titulo") or "Vacaciones", fuente=E.F_NEGRITA,
                       color=E.TEXTO_SUAVE if pasado else E.TEXTO, anchor="w").pack(side="left")
            if estado == "en_curso":
                E.etiqueta_estado(fila1, "En curso", E.VERDE).pack(side="left", padx=(8, 0))
            elif pasado:
                E.etiqueta_estado(fila1, "Pasado", E.TEXTO_APAGADO).pack(side="left", padx=(8, 0))
            n = _dias_entre(vac["fecha_inicio"], vac["fecha_fin"])
            E.etiqueta(texto, f"{T.rango(vac['fecha_inicio'], vac['fecha_fin'])}   ·   {T.dias(n)}",
                       color=E.TEXTO_SUAVE, fuente=E.F_SUBTITULO, anchor="w").pack(fill="x", pady=(2, 0))
            ant = T.antelacion(vac.get("antelacion"))
            falta = "" if estado != "proximo" else T.cuanto_falta(vac["fecha_inicio"], hoy)
            detalle = "   ·   ".join(x for x in (f"Empieza {falta}" if falta else "", f"⏰ {ant}" if ant else "") if x)
            if detalle:
                E.etiqueta(texto, detalle, color=E.TEXTO_APAGADO if pasado else E.TEXTO_SUAVE,
                           fuente=E.F_PEQUE, anchor="w").pack(fill="x", pady=(2, 0))

    def _eliminar(idx):
        # (v4.18.66) Se borra por su id, no por la posición: mientras se pregunta puede llegar un cambio de otro PC.
        periodo = ctx.agenda_data.get("vacaciones", [])[idx]
        if messagebox.askyesno("Confirmar", "¿Eliminar este periodo?", parent=vwin):
            sincro_agenda.quitar(ctx.agenda_data.get("vacaciones", []), periodo)
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
            # (v4.18.66) Que siga siendo el mismo elemento (mismo id) y en su sitio aunque otro PC haya cambiado la lista.
            sincro_agenda.reemplazar(ctx.agenda_data.setdefault("vacaciones", []), vac_actual, editado, idx)
            ctx.save_agenda(ctx.agenda_data)
            ew.destroy()
            cargar()

        ttk.Separator(ew).pack(fill="x", pady=(10, 0))
        fb = ttk.Frame(ew, padding=(20, 8, 20, 12))
        fb.pack(fill="x")
        ttk.Button(fb, text="  Guardar  ",
                   bootstyle="success", command=guardar).pack(side="left", padx=(0, 8))
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
                   bootstyle="success", command=guardar).pack(side="left", padx=(0, 8))
        ttk.Button(fb, text="  Cancelar  ",
                   bootstyle="secondary", command=nw.destroy).pack(side="left")

        nw.update_idletasks()
        _nph = nw.winfo_reqheight() + 10
        nw.geometry(f"{_npw}x{_nph}+{(_sw - _npw)//2}+{(_sh - _nph)//2}")
        nw.grab_set()

    sincro_agenda.registrar_refresco(vwin, cargar)   # (v4.18.66) cambios llegados de otro PC
    cargar()

    pie = tk.Frame(vwin, bg=E.FONDO)
    pie.pack(fill="x", padx=22, pady=(12, 16))
    # (v4.18.72) «+» normal: el «＋» de ancho completo salía con otra letra (con serifa) en el botón.
    ttk.Button(pie, text="+  Nuevo Periodo",
               bootstyle="success", command=_nuevo_periodo).pack(side="left")
    ttk.Button(pie, text="  Cerrar  ",
               bootstyle="secondary", command=vwin.destroy).pack(side="right")

    vwin.update_idletasks()
    _vh = min(max(vwin.winfo_reqheight() + 10, 460), _sh - 80)
    vwin.geometry(f"{_vw}x{_vh}+{(_sw - _vw)//2}+{(_sh - _vh)//2}")
    vwin.grab_set()
