"""
negocio/correo.py
Generación y envío de borradores de correo para festivos y vacaciones.
Extraído de main_agenda.py en Fase 2 del sprint de estabilización.

Uso:
    from negocio.correo import _enriquecer_evento_correo, _generar_texto_correo, _abrir_ventana_correo
"""
from datetime import datetime
import ttkbootstrap as ttk
from tkinter import messagebox, StringVar
from ui.assets import _apply_icon          # ANTI-REGRESION: usada en _abrir_ventana_correo

# Constante de color — ANTI-REGRESION: era global de main_agenda
LIGHT = "#D8E8F0"

# NOMBRE_USUARIO_ACTUAL se inyecta desde main_agenda al arrancar
NOMBRE_USUARIO_ACTUAL: str = ""


def _enriquecer_evento_correo(evento: dict, tipo_correo: str,
                               fecha_inicio: str, fecha_fin: str = None) -> dict:
    """Añade PermiteCorreo, TipoCorreo y fechas al dict del evento.
    PermiteCorreo = True solo si tipo_correo es FESTIVO o VACACIONES.
    """
    tipo = tipo_correo.upper()
    ev = dict(evento)
    ev["PermiteCorreo"] = tipo in ("FESTIVO", "VACACIONES")
    ev["TipoCorreo"]    = tipo
    ev["_FechaInicio"]  = fecha_inicio
    ev["_FechaFin"]     = fecha_fin if fecha_fin else fecha_inicio
    return ev



def _generar_texto_correo(evento_enriquecido: dict) -> tuple:
    """Devuelve (asunto, cuerpo) redactados según el tipo de evento."""
    tipo      = evento_enriquecido.get("TipoCorreo", "")
    titulo    = evento_enriquecido.get("titulo", "")
    f_ini_iso = evento_enriquecido.get("_FechaInicio", "")
    f_fin_iso = evento_enriquecido.get("_FechaFin", f_ini_iso)

    def _fmt(iso):
        try:
            return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return iso

    f_ini_ui  = _fmt(f_ini_iso)
    f_fin_ui  = _fmt(f_fin_iso)
    mismo_dia = f_ini_iso == f_fin_iso

    if tipo == "FESTIVO":
        asunto = f"Aviso de cierre por festivo — {titulo} ({f_ini_ui})"
        cuerpo = (
            f"Estimados/as,\n\n"
            f"Les comunicamos que el departamento de Central de Compras permanecerá\n"
            f"CERRADO con motivo del día festivo:\n\n"
            f"    🎉  {titulo}\n"
            f"    📅  Fecha: {f_ini_ui}\n\n"
            f"Disculpen las molestias ocasionadas. Estaremos de vuelta el siguiente\n"
            f"día laborable.\n\n"
            f"Atentamente,\n"
            f"{NOMBRE_USUARIO_ACTUAL}\n"
            f"Central de Compras — Princess Hotels & Resorts"
        )
    elif tipo == "VACACIONES":
        if mismo_dia:
            periodo_txt = f"el día {f_ini_ui}"
        else:
            periodo_txt = f"del {f_ini_ui} al {f_fin_ui} (ambos inclusive)"
        asunto = f"Aviso de ausencia por vacaciones — {titulo}"
        cuerpo = (
            f"Estimados/as,\n\n"
            f"Les informo de que estaré ausente por vacaciones {periodo_txt}.\n\n"
            f"    🏖  Periodo: {titulo}\n"
            f"    📅  {periodo_txt.capitalize()}\n\n"
            f"Durante mi ausencia, pueden contactar con el departamento de\n"
            f"Central de Compras para cualquier gestión urgente.\n\n"
            f"Un cordial saludo,\n"
            f"{NOMBRE_USUARIO_ACTUAL}\n"
            f"Central de Compras — Princess Hotels & Resorts"
        )
    else:
        asunto = f"Aviso: {titulo}"
        cuerpo = f"Evento: {titulo}\nFecha: {f_ini_ui}"

    return asunto, cuerpo



def _abrir_ventana_correo(evento_enriquecido: dict, parent=None):
    """Ventana modal con el borrador del correo, editable.
    Botones: Abrir en cliente de correo | Copiar al portapapeles | Cerrar.
    """
    import tkinter as _tk
    import urllib.parse

    asunto, cuerpo = _generar_texto_correo(evento_enriquecido)
    tipo  = evento_enriquecido.get("TipoCorreo", "")
    icono = "🎉" if tipo == "FESTIVO" else "🏖"

    win = ttk.Toplevel()
    win.title("✉  Borrador de correo")
    win.resizable(False, False)
    _apply_icon(win)
    if parent:
        win.transient(parent)

    _ww = 540
    _sw = win.winfo_screenwidth()
    _sh = win.winfo_screenheight()

    # ── Cabecera ──────────────────────────────────────────────
    hdr = ttk.Frame(win, padding=(20, 14, 20, 8))
    hdr.pack(fill="x")
    ttk.Label(hdr,
              text=f"{icono}  Correo sobre este aviso",
              font=("Segoe UI", 13, "bold")).pack(anchor="w")
    ttk.Label(hdr,
              text=f"Tipo: {tipo.capitalize()}  —  {evento_enriquecido.get('titulo', '')}",
              font=("Segoe UI", 9),
              foreground=LIGHT).pack(anchor="w", pady=(3, 0))
    ttk.Separator(win).pack(fill="x")

    body = ttk.Frame(win, padding=(20, 12, 20, 0))
    body.pack(fill="both", expand=True)

    # ── Asunto ────────────────────────────────────────────────
    ttk.Label(body, text="Asunto:", font=("Segoe UI", 9, "bold")).pack(anchor="w")
    var_asunto = StringVar(value=asunto)
    ttk.Entry(body, textvariable=var_asunto,
              font=("Segoe UI", 9)).pack(fill="x", pady=(3, 10))

    # ── Cuerpo ────────────────────────────────────────────────
    ttk.Label(body, text="Cuerpo del correo:",
              font=("Segoe UI", 9, "bold")).pack(anchor="w")
    txt_frame = ttk.Frame(body)
    txt_frame.pack(fill="both", expand=True, pady=(3, 0))

    txt_cuerpo = _tk.Text(
        txt_frame, font=("Segoe UI", 9), wrap="word",
        height=14, relief="flat", padx=6, pady=6,
    )
    sb_txt = ttk.Scrollbar(txt_frame, orient="vertical", command=txt_cuerpo.yview)
    txt_cuerpo.configure(yscrollcommand=sb_txt.set)
    txt_cuerpo.pack(side="left", fill="both", expand=True)
    sb_txt.pack(side="right", fill="y")
    txt_cuerpo.insert("1.0", cuerpo)

    # ── Pie ───────────────────────────────────────────────────
    ttk.Separator(win).pack(fill="x", pady=(10, 0))
    pie = ttk.Frame(win, padding=(20, 8, 20, 12))
    pie.pack(fill="x")

    def _abrir_mailto():
        asunto_enc = urllib.parse.quote(var_asunto.get())
        cuerpo_enc = urllib.parse.quote(txt_cuerpo.get("1.0", "end").strip())
        import webbrowser
        try:
            webbrowser.open(f"mailto:?subject={asunto_enc}&body={cuerpo_enc}")
        except Exception as exc:
            messagebox.showerror("Error al abrir el correo",
                                 f"No se pudo abrir el cliente de correo:\n\n{exc}",
                                 parent=win)

    def _copiar_portapapeles():
        texto = (
            f"Asunto: {var_asunto.get()}\n"
            f"{'─' * 50}\n"
            f"{txt_cuerpo.get('1.0', 'end').strip()}"
        )
        win.clipboard_clear()
        win.clipboard_append(texto)
        win.update()
        messagebox.showinfo("Copiado",
                            "El borrador del correo se ha copiado al portapapeles.",
                            parent=win)

    ttk.Button(pie, text="  📧  Abrir en cliente de correo  ",
               bootstyle="warning",
               command=_abrir_mailto).pack(side="left", padx=(0, 8))
    ttk.Button(pie, text="  📋  Copiar  ",
               bootstyle="info-outline",
               command=_copiar_portapapeles).pack(side="left", padx=(0, 8))
    ttk.Button(pie, text="  Cerrar  ",
               bootstyle="secondary",
               command=win.destroy).pack(side="right")

    win.update_idletasks()
    _wh = win.winfo_reqheight() + 10
    win.geometry(f"{_ww}x{_wh}+{(_sw - _ww)//2}+{(_sh - _wh)//2}")
    win.grab_set()
