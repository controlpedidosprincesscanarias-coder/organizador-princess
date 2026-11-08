"""
app/ui/saludo.py
Popup de bienvenida diario con resumen de eventos y alertas del bridge.
Extraído de main_agenda.py en Fase 3A del sprint de estabilización.

Patrón: todas las dependencias se reciben via AppContext (ctx).
No hay globals. No hay imports circulares.

Uso:
    from ui.saludo import mostrar_saludo_diario
    mostrar_saludo_diario(ctx)
"""
import threading
from datetime import datetime, date
import ttkbootstrap as ttk

from db.sqlite import load_agenda, save_config
from ui.assets import _apply_icon                    # ANTI-REGRESION: usada en el popup de saludo
from negocio.correo import (                         # ANTI-REGRESION: usadas en botones de correo del saludo
    _enriquecer_evento_correo,
    _abrir_ventana_correo,
)

# Constantes de color — ANTI-REGRESION: eran globals de main_agenda
GOLD  = "#C9A84C"
LIGHT = "#D8E8F0"


def mostrar_saludo_diario(ctx):
    """Muestra un popup de bienvenida una sola vez al día.
    Recibe AppContext en lugar de acceder a globals.
    """
    hoy_str = date.today().isoformat()
    ultimo  = ctx.config.get("_saludo_ultimo_dia", "")
    if ultimo == hoy_str:
        return

    ctx.config["_saludo_ultimo_dia"] = hoy_str
    save_config(ctx.config)

    def _construir_y_mostrar():
        try:
            from pedidos_agenda_bridge import get_resumen_alertas
            resumen_bridge = get_resumen_alertas()
        except Exception:
            resumen_bridge = {"total": 0, "urgentes": 0, "normales": 0}

        data_fresca = load_agenda()

        hora_actual = datetime.now().hour
        saludo = "Buenos días" if hora_actual < 14 else "Buenas tardes"

        hoy_dt = date.today()
        eventos_hoy = []
        for av in data_fresca.get("avisos", []):
            if not av.get("activo", True):
                continue
            rep = av.get("repeticion", "ninguna")
            fecha_str = hoy_dt.strftime("%Y-%m-%d")
            fecha_inicio = av.get("fecha", "")
            if rep == "ninguna" and av.get("fecha") == fecha_str:
                eventos_hoy.append(av)
            elif rep == "diario":
                if fecha_str >= fecha_inicio:
                    eventos_hoy.append(av)
            elif rep == "semanal":
                try:
                    if (fecha_str >= fecha_inicio and
                            datetime.strptime(av["fecha"], "%Y-%m-%d").weekday() == hoy_dt.weekday()):
                        eventos_hoy.append(av)
                except Exception:  # noqa: BLE001
                    import sys as _sys, traceback as _tb
                    print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
            elif rep == "mensual":
                try:
                    if (fecha_str >= fecha_inicio and
                            datetime.strptime(av["fecha"], "%Y-%m-%d").day == hoy_dt.day):
                        eventos_hoy.append(av)
                except Exception:  # noqa: BLE001
                    import sys as _sys, traceback as _tb
                    print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
            elif rep in ("cada_hora", "cada_30min"):
                if fecha_str >= fecha_inicio:
                    eventos_hoy.append(av)

        vacs_hoy     = [v for v in data_fresca.get("vacaciones", [])
                        if v["fecha_inicio"] <= hoy_dt.strftime("%Y-%m-%d") <= v["fecha_fin"]]
        festivos_hoy = [f for f in data_fresca.get("festivos", [])
                        if f.get("fecha") == hoy_dt.strftime("%Y-%m-%d")]

        _avisos_bridge = [av for av in eventos_hoy if av.get("_bridge_gestionado")]  # reservado
        eventos_agenda = [av for av in eventos_hoy if not av.get("_bridge_gestionado")]

        tiene_eventos = bool(eventos_agenda or vacs_hoy or festivos_hoy)
        tiene_alertas = resumen_bridge["total"] > 0

        if tiene_eventos:
            n_ev = len(eventos_agenda) + len(vacs_hoy) + len(festivos_hoy)
            msg_eventos = f"Tienes {n_ev} evento{'s' if n_ev > 1 else ''} en la agenda de hoy."
        else:
            msg_eventos = "No tienes eventos programados para hoy."

        if tiene_alertas:
            n_u = resumen_bridge["urgentes"]
            n_n = resumen_bridge["normales"]
            partes = []
            if n_u:
                partes.append(f"🚨 {n_u} urgente{'s' if n_u > 1 else ''}")
            if n_n:
                partes.append(f"⚠️ {n_n} en seguimiento")
            msg_alertas = "Pedidos con alerta: " + "  ·  ".join(partes)
        else:
            msg_alertas = None

        ctx.app.after(0, lambda: _popup_saludo(
            ctx, saludo, msg_eventos, msg_alertas,
            tiene_eventos, tiene_alertas, hoy_dt, data_fresca,
        ))

    threading.Thread(target=_construir_y_mostrar, daemon=True, name="SaludoBridge").start()

def _popup_saludo(ctx, saludo, msg_eventos, msg_alertas, tiene_eventos, tiene_alertas, hoy_dt, data_fresca):
    """Construye y muestra el popup del saludo diario en el hilo de Tkinter."""
    pop = ttk.Toplevel()
    pop.title("Bienvenido")
    pop.resizable(False, False)
    pop.attributes("-topmost", True)
    ctx.apply_icon(pop)

    _pw = 460
    # Altura base + espacio extra si hay alertas del bridge
    _ph = 210
    if tiene_eventos:
        _ph += 30
    if tiene_alertas:
        _ph += 36
    _sw = pop.winfo_screenwidth()
    _sh = pop.winfo_screenheight()
    pop.geometry(f"{_pw}x{_ph}+{(_sw - _pw)//2}+{(_sh - _ph)//2}")

    frm = ttk.Frame(pop, padding=(28, 20, 28, 16))
    frm.pack(fill="both", expand=True)

    ttk.Label(frm,
              text=f"\u00a1{saludo}, {ctx.nombre_usuario}!",
              font=("Segoe UI", 13, "bold"),
              foreground=GOLD,
              anchor="center",
              justify="center").pack(fill="x", pady=(0, 8))

    ttk.Label(frm,
              text=msg_eventos,
              font=("Segoe UI", 10),
              wraplength=400,
              anchor="center",
              justify="center").pack(fill="x", pady=(0, 6 if tiene_alertas else 14))

    # ── Línea de alertas del bridge (solo si hay alguna) ──────────────────
    if tiene_alertas:
        ttk.Label(frm,
                  text=msg_alertas,
                  font=("Segoe UI", 10, "bold"),
                  foreground="#E05252" if msg_alertas and "🚨" in msg_alertas else GOLD,
                  wraplength=400,
                  anchor="center",
                  justify="center").pack(fill="x", pady=(0, 14))

    btn_frame = ttk.Frame(frm)
    btn_frame.pack()

    def _cerrar():
        pop.destroy()

    # ----------------------------------------------------------
    # "Ver eventos" abre SOLO la ventana Detalle del día.
    # ----------------------------------------------------------
    def _abrir_detalle_hoy():
        pop.destroy()   # cerrar el saludo primero

        _pw_det = 320
        _sh_det = ctx.app.winfo_screenheight()   # ANTI-REGRESION: usar ctx.app, no 'app' (bug Fase 3.6)
        _sw_det = ctx.app.winfo_screenwidth()    # ANTI-REGRESION: usar ctx.app, no 'app' (bug Fase 3.6)

        _dia_nombres = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES",
                        "VIERNES", "SÁBADO", "DOMINGO"]

        pw = ttk.Toplevel()
        pw.withdraw()
        pw.title("📅 Detalle del día")
        pw.resizable(False, True)
        _apply_icon(pw)
        pw.transient(ctx.app)                    # ANTI-REGRESION: usar ctx.app, no 'app' (bug Fase 3.6)

        pan_header = ttk.Frame(pw, bootstyle="dark", padding=(12, 12, 12, 10))
        pan_header.pack(fill="x")

        pan_hdr_row = ttk.Frame(pan_header, bootstyle="dark")
        pan_hdr_row.pack(fill="x")

        _crown_tk = ctx.get_crown_tk(size=36)
        if _crown_tk:
            lbl_crown = ttk.Label(pan_hdr_row, image=_crown_tk,
                                  bootstyle="inverse-dark")
            lbl_crown.pack(side="left", padx=(0, 10))
            lbl_crown._crown_ref = _crown_tk

        bloque_texto = ttk.Frame(pan_hdr_row, bootstyle="dark")
        bloque_texto.pack(side="left", fill="x", expand=True)

        ttk.Label(bloque_texto,
                  text=_dia_nombres[hoy_dt.weekday()],
                  font=("Segoe UI", 13, "bold"),
                  bootstyle="inverse-dark",
                  anchor="w").pack(anchor="w")

        ttk.Label(bloque_texto,
                  text=hoy_dt.strftime("%d/%m/%Y"),
                  font=("Segoe UI", 9),
                  foreground=LIGHT,
                  bootstyle="inverse-dark",
                  anchor="w").pack(anchor="w", pady=(2, 0))

        ttk.Separator(pw).pack(fill="x")

        pan_body = ttk.Frame(pw, padding=(12, 10, 12, 10))
        pan_body.pack(fill="both", expand=True)

        # Usar data_fresca para que los avisos del bridge aparezcan aquí también
        eventos = []
        for av in data_fresca.get("avisos", []):
            if not av.get("activo", True):
                continue
            rep = av.get("repeticion", "ninguna")
            fecha_str = hoy_dt.strftime("%Y-%m-%d")
            fecha_inicio = av.get("fecha", "")
            if rep == "ninguna" and av.get("fecha") == fecha_str:
                eventos.append(av)
            elif rep == "diario":
                if fecha_str >= fecha_inicio:
                    eventos.append(av)
            elif rep == "semanal":
                try:
                    if (fecha_str >= fecha_inicio and
                            datetime.strptime(av["fecha"], "%Y-%m-%d").weekday() == hoy_dt.weekday()):
                        eventos.append(av)
                except Exception:  # noqa: BLE001
                    import sys as _sys, traceback as _tb
                    print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
            elif rep == "mensual":
                try:
                    if (fecha_str >= fecha_inicio and
                            datetime.strptime(av["fecha"], "%Y-%m-%d").day == hoy_dt.day):
                        eventos.append(av)
                except Exception:  # noqa: BLE001
                    import sys as _sys, traceback as _tb
                    print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
            elif rep in ("cada_hora", "cada_30min"):
                if fecha_str >= fecha_inicio:
                    eventos.append(av)
        vacs  = [v for v in data_fresca.get("vacaciones", [])
                 if v["fecha_inicio"] <= hoy_dt.strftime("%Y-%m-%d") <= v["fecha_fin"]]
        fests = [f for f in data_fresca.get("festivos", [])
                 if f.get("fecha") == hoy_dt.strftime("%Y-%m-%d")]

        if not eventos and not vacs and not fests:
            ttk.Label(pan_body,
                      text="Sin eventos para este día.",
                      font=("Segoe UI", 9),
                      foreground=LIGHT,
                      wraplength=_pw_det - 28,
                      anchor="center",
                      justify="center").pack(expand=True, pady=20)
        else:
            for v in vacs:
                ev_enr = _enriquecer_evento_correo(
                    v, "VACACIONES",
                    v.get("fecha_inicio", ""), v.get("fecha_fin", "")
                )
                frv = ttk.Frame(pan_body, bootstyle="success", padding=(8, 5))
                frv.pack(fill="x", pady=(0, 6))
                ttk.Label(frv, text="🏖  " + v["titulo"],
                          font=("Segoe UI", 9, "bold"),
                          bootstyle="inverse-success",
                          wraplength=_pw_det - 36).pack(anchor="w")
                if ev_enr["PermiteCorreo"]:
                    ttk.Button(
                        frv,
                        text="  ✉  Enviar correo sobre este aviso  ",
                        bootstyle="success-outline",
                        command=lambda e=ev_enr, p=pw: _abrir_ventana_correo(e, parent=p),
                    ).pack(anchor="w", pady=(4, 0))

            for ft in fests:
                ev_enr = _enriquecer_evento_correo(
                    ft, "FESTIVO",
                    ft.get("fecha", "")
                )
                frf = ttk.Frame(pan_body, bootstyle="danger", padding=(8, 5))
                frf.pack(fill="x", pady=(0, 6))
                ttk.Label(frf, text="🎉  " + ft["titulo"],
                          font=("Segoe UI", 9, "bold"),
                          bootstyle="inverse-danger",
                          wraplength=_pw_det - 36).pack(anchor="w")
                if ev_enr["PermiteCorreo"]:
                    ttk.Button(
                        frf,
                        text="  ✉  Enviar correo sobre este aviso  ",
                        bootstyle="danger-outline",
                        command=lambda e=ev_enr, p=pw: _abrir_ventana_correo(e, parent=p),
                    ).pack(anchor="w", pady=(4, 0))

            for ev in sorted(eventos, key=lambda x: x["hora"]):
                es_rep = ev.get("repeticion", "ninguna") != "ninguna"
                es_bridge = ev.get("_bridge_gestionado", False)
                nivel = ev.get("_nivel", "")
                if es_bridge:
                    icono = "🚨" if nivel == "urgente" else "⚠️"
                    estilo = "danger" if nivel == "urgente" else "warning"
                else:
                    icono  = "🔁" if es_rep else "🔔"
                    estilo = "secondary"
                fre = ttk.Frame(pan_body, bootstyle=estilo, padding=(8, 6))
                fre.pack(fill="x", pady=(0, 5))
                ttk.Label(fre,
                          text=f"{icono}  {ev['hora']}",
                          font=("Segoe UI", 10, "bold"),
                          bootstyle=f"inverse-{estilo}").pack(anchor="w")
                ttk.Label(fre,
                          text=ev["titulo"],
                          font=("Segoe UI", 9),
                          bootstyle=f"inverse-{estilo}",
                          wraplength=_pw_det - 36).pack(anchor="w", pady=(2, 0))

        ttk.Separator(pw).pack(fill="x")
        pie = ttk.Frame(pw, padding=(12, 8, 12, 10))
        pie.pack(fill="x")
        ttk.Button(pie, text="  Cerrar  ", bootstyle="secondary",
                   command=pw.destroy).pack(side="right")

        pw.update_idletasks()
        _ph_det = min(max(pw.winfo_reqheight() + 10, 280), _sh_det - 60)
        _x_det  = (_sw_det - _pw_det) // 2
        _y_det  = (_sh_det - _ph_det) // 2
        pw.geometry(f"{_pw_det}x{_ph_det}+{_x_det}+{_y_det}")
        pw.deiconify()
        pw.lift()
        pw.focus_force()
        pw.grab_set()

    if tiene_eventos or tiene_alertas:
        ttk.Button(btn_frame,
                   text="\U0001f4c5  Ver eventos",
                   bootstyle="info",
                   command=_abrir_detalle_hoy,
                   width=16).pack(side="left", padx=(0, 8))

    ttk.Button(btn_frame,
               text="  Entendido  ",
               bootstyle="warning",
               command=_cerrar,
               width=14).pack(side="left")

    pop.grab_set()
