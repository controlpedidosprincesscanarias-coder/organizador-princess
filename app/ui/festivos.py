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
from services import sincro_agenda   # (v4.18.66) agenda sincronizada con Control de Pedidos
import tkinter as tk
from ui import estilo_calendario as E          # (v4.18.72) aspecto nuevo
from utils import textos_calendario as T

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
    fwin.resizable(True, True)   # ANTI-REGRESIÓN: unificado con Agenda — redimensionable en horizontal
    ctx.apply_icon(fwin)

    _fw = 600
    _sw = fwin.winfo_screenwidth()
    _sh = fwin.winfo_screenheight()
    fwin.minsize(480, 200)

    # (v4.18.72) Rediseño: cabecera con resumen, tarjetas con bloque de fecha y estado (ui/estilo_calendario.py).
    fwin.configure(background=E.FONDO)
    v_resumen = StringVar()
    E.cabecera(fwin, "🎉", "Festivos", v_resumen)
    sf = E.lista_desplazable(fwin, fwin)

    def cargar():
        for w in sf.winfo_children():
            w.destroy()
        fests = ctx.agenda_data.get("festivos", [])
        hoy   = date.today()
        v_resumen.set(T.resumen_festivos(fests, hoy))
        fests_sorted = sorted(fests, key=lambda x: x["fecha"])

        if not fests_sorted:
            E.vacia(sf, "No hay festivos definidos.\nPulsa «+  Nuevo Festivo» para añadir el primero.")
            return
        año_actual = None
        for fest in fests_sorted:
            año = fest["fecha"][:4]
            if año != año_actual:
                año_actual = año
                n_año = sum(1 for f in fests_sorted if f["fecha"][:4] == año)
                E.separador_anio(sf, año, f"{n_año} festivo{'s' if n_año != 1 else ''}")
            estado = T.estado_periodo(fest["fecha"], fest["fecha"], hoy)
            pasado = estado == "pasado"
            _, cuerpo = E.tarjeta(sf, E.ROJO, apagado=pasado)
            E.bloque_fecha(cuerpo, fest["fecha"], E.ROJO, apagado=pasado).pack(side="left", padx=(0, 14))

            ix = fests.index(fest)
            E.botones_fila(cuerpo, lambda ix=ix: _editar_festivo(ix),
                           lambda ix=ix: _eliminar(ix)).pack(side="right")

            texto = tk.Frame(cuerpo, bg=E.TARJETA)
            texto.pack(side="left", fill="x", expand=True)
            fila1 = tk.Frame(texto, bg=E.TARJETA)
            fila1.pack(fill="x")
            E.etiqueta(fila1, fest.get("titulo") or "Festivo", fuente=E.F_NEGRITA,
                       color=E.TEXTO_SUAVE if pasado else E.TEXTO, anchor="w").pack(side="left")
            if estado == "en_curso":
                E.etiqueta_estado(fila1, "Hoy", E.ROJO).pack(side="left", padx=(8, 0))
            elif pasado:
                E.etiqueta_estado(fila1, "Pasado", E.TEXTO_APAGADO).pack(side="left", padx=(8, 0))
            d = T.a_fecha(fest["fecha"])
            linea2 = T.DIAS_LARGOS[d.weekday()].capitalize() if d else ""
            falta = T.cuanto_falta(fest["fecha"], hoy) if estado == "proximo" else ""
            if falta:
                linea2 += f"   ·   {falta}"
            E.etiqueta(texto, linea2, color=E.TEXTO_SUAVE, fuente=E.F_SUBTITULO,
                       anchor="w").pack(fill="x", pady=(2, 0))
            ant = T.antelacion(fest.get("antelacion"))
            if ant:
                E.etiqueta(texto, f"⏰ {ant}", color=E.TEXTO_APAGADO if pasado else E.TEXTO_SUAVE,
                           fuente=E.F_PEQUE, anchor="w").pack(fill="x", pady=(2, 0))

    def _eliminar(idx):
        # (v4.18.66) Se borra por su id, no por la posición: mientras se pregunta puede llegar un cambio de otro PC.
        festivo = ctx.agenda_data.get("festivos", [])[idx]
        if messagebox.askyesno("Confirmar", "¿Eliminar este festivo?", parent=fwin):
            sincro_agenda.quitar(ctx.agenda_data.get("festivos", []), festivo)
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
            # (v4.18.66) Que siga siendo el mismo elemento (mismo id) y en su sitio aunque otro PC haya cambiado la lista.
            sincro_agenda.reemplazar(ctx.agenda_data.setdefault("festivos", []), fest_actual, editado, idx)
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

    sincro_agenda.registrar_refresco(fwin, cargar)   # (v4.18.66) cambios llegados de otro PC
    cargar()

    pie = tk.Frame(fwin, bg=E.FONDO)
    pie.pack(fill="x", padx=22, pady=(12, 16))
    # (v4.18.72) «+» normal: el «＋» de ancho completo salía con otra letra en el botón.
    ttk.Button(pie, text="+  Nuevo Festivo",
               bootstyle="danger", command=_nuevo_festivo).pack(side="left")
    ttk.Button(pie, text="  Cerrar  ",
               bootstyle="secondary", command=fwin.destroy).pack(side="right")

    fwin.update_idletasks()
    _fh = min(max(fwin.winfo_reqheight() + 10, 460), _sh - 80)
    fwin.geometry(f"{_fw}x{_fh}+{(_sw - _fw)//2}+{(_sh - _fh)//2}")
    fwin.grab_set()
