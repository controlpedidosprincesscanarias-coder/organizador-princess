"""
ui/calendario.py
Ventana «Calendario» (vista de mes y de semana) con avisos, vacaciones y festivos, y acceso a
Chat, Festivos, Vacaciones y a las agendas imprimibles del día, la semana y el mes.
Extraída de main_agenda.py en v4.18.08 (antes, abrir_calendario() era una función de ~620 líneas allí).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Recibe el AppContext (ctx).
"""
import calendar as _cal_mod
from datetime import date, datetime, timedelta
from tkinter import StringVar

import ttkbootstrap as ttk

from negocio.correo import _abrir_ventana_correo, _enriquecer_evento_correo
from ui.agenda_helpers import _eventos_del_dia, _festivos_del_dia, _vacaciones_del_dia
from ui.assets import _apply_icon, get_crown_tk
from ui.colores import GOLD, LIGHT
from ui.festivos import _ventana_festivos
from ui.vacaciones import _ventana_vacaciones
from ui.ventana_chat import _ventana_chat

_NOMBRES_MES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
_DIAS_SEM    = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]


def abrir_calendario(ctx):
    """Ventana de calendario mensual / semanal con eventos y vacaciones.
    Se posiciona cerca del borde derecho de la pantalla.
    Al pulsar un día, se muestra un panel lateral izquierdo con los eventos de ese día.
    """
    win = ttk.Toplevel()
    win.withdraw()
    win.title("📆 Calendario")
    win.resizable(True, True)
    _apply_icon(win)

    _cw_cal = 960          # ancho del calendario
    _pw     = 320          # ancho de la subventana de detalle del día
    _margin = 40           # margen respecto al borde derecho (~1 dedo)
    _sw     = win.winfo_screenwidth()
    _sh     = win.winfo_screenheight()
    hoy     = date.today()

    vista_var     = StringVar(value="mes")
    nav_fecha     = [hoy.replace(day=1)]
    dia_sel       = [None]    # fecha seleccionada actualmente
    _panel_win    = [None]    # referencia a la subventana de detalle (Toplevel)

    # ── Layout principal: solo el calendario, limpio ──────────────────────────
    frm_cal = ttk.Frame(win)
    frm_cal.pack(fill="both", expand=True)

    # ── Subventana independiente de detalle del día ───────────────────────────
    def _construir_panel_win():
        """Crea la subventana Toplevel de detalle del día (si no existe)."""
        if _panel_win[0] is not None and _panel_win[0].winfo_exists():
            return  # ya existe, solo actualizar contenido

        pw = ttk.Toplevel()
        pw.withdraw()
        pw.title("📅 Detalle del día")
        pw.resizable(False, True)
        _apply_icon(pw)
        pw.transient(win)   # hijo lógico del calendario, no bloquea

        # Cerrar el panel: destruir pw primero, luego repintar el calendario
        def _on_close_panel():
            dia_sel[0] = None
            _panel_win[0] = None
            try:
                pw.destroy()
            except Exception:
                pass  # UI — ignorar silenciosamente
            # Diferir el renderizado al siguiente ciclo para que destroy() complete
            if win.winfo_exists():
                win.after(0, renderizar)
        pw.protocol("WM_DELETE_WINDOW", _on_close_panel)

        # ── Cabecera: corona (izda) + nombre del día + fecha (dcha) ──────────
        pan_header = ttk.Frame(pw, bootstyle="dark", padding=(12, 12, 12, 10))
        pan_header.pack(fill="x")

        pan_hdr_row = ttk.Frame(pan_header, bootstyle="dark")
        pan_hdr_row.pack(fill="x")

        _crown_tk = get_crown_tk(size=36)
        if _crown_tk:
            lbl_crown = ttk.Label(pan_hdr_row, image=_crown_tk,
                                  bootstyle="inverse-dark")
            lbl_crown.pack(side="left", padx=(0, 10))
            lbl_crown._crown_ref = _crown_tk   # evitar GC

        # Bloque dcha: nombre del día (grande) + fecha (pequeña) apilados
        bloque_texto = ttk.Frame(pan_hdr_row, bootstyle="dark")
        bloque_texto.pack(side="left", fill="x", expand=True)

        lbl_dia_nombre = ttk.Label(bloque_texto,
                                   text="",
                                   font=("Segoe UI", 13, "bold"),
                                   bootstyle="inverse-dark",
                                   anchor="w")
        lbl_dia_nombre.pack(anchor="w")

        lbl_dia_fecha = ttk.Label(bloque_texto,
                                  text="",
                                  font=("Segoe UI", 9),
                                  foreground=LIGHT,
                                  bootstyle="inverse-dark",
                                  anchor="w")
        lbl_dia_fecha.pack(anchor="w", pady=(2, 0))

        ttk.Separator(pw).pack(fill="x")

        # ── Cuerpo scrollable de eventos ──────────────────────────────────────
        pan_body = ttk.Frame(pw, padding=(12, 10, 12, 10))
        pan_body.pack(fill="both", expand=True)

        # Pie con botón cerrar
        ttk.Separator(pw).pack(fill="x")
        pie = ttk.Frame(pw, padding=(12, 8, 12, 10))
        pie.pack(fill="x")
        ttk.Button(pie, text="  Cerrar  ", bootstyle="secondary",
                   command=_on_close_panel).pack(side="right")

        # Guardar referencias internas en el objeto pw para actualizarlas
        pw._lbl_dia_nombre = lbl_dia_nombre
        pw._lbl_dia_fecha  = lbl_dia_fecha
        pw._pan_body       = pan_body
        pw._pw_val         = _pw

        _panel_win[0] = pw

    def _rellenar_panel_win(fecha_dt):
        """Actualiza el contenido de la subventana con los eventos de fecha_dt."""
        pw = _panel_win[0]
        if pw is None or not pw.winfo_exists():
            return

        _dia_nombres = ["LUNES","MARTES","MIÉRCOLES","JUEVES",
                        "VIERNES","SÁBADO","DOMINGO"]
        pw._lbl_dia_nombre.config(text=_dia_nombres[fecha_dt.weekday()])
        pw._lbl_dia_fecha.config(text=fecha_dt.strftime("%d/%m/%Y"))

        # Limpiar cuerpo anterior
        for w in pw._pan_body.winfo_children():
            w.destroy()

        eventos = _eventos_del_dia(ctx, fecha_dt)
        vacs    = _vacaciones_del_dia(ctx, fecha_dt)
        fests   = _festivos_del_dia(ctx, fecha_dt)

        if not eventos and not vacs and not fests:
            ttk.Label(pw._pan_body,
                      text="Sin eventos para este día.",
                      font=("Segoe UI", 9),
                      foreground=LIGHT,
                      wraplength=pw._pw_val - 28,
                      anchor="center",
                      justify="center").pack(expand=True, pady=20)
        else:
            # ── VACACIONES ──────────────────────────────────────
            for v in vacs:
                ev_enr = _enriquecer_evento_correo(
                    v, "VACACIONES",
                    v.get("fecha_inicio", ""), v.get("fecha_fin", "")
                )
                frv = ttk.Frame(pw._pan_body, bootstyle="success", padding=(8, 5))
                frv.pack(fill="x", pady=(0, 6))
                ttk.Label(frv, text="🏖  " + v["titulo"],
                          font=("Segoe UI", 9, "bold"),
                          bootstyle="inverse-success",
                          wraplength=pw._pw_val - 36).pack(anchor="w")
                if ev_enr["PermiteCorreo"]:
                    ttk.Button(
                        frv,
                        text="  ✉  Enviar correo sobre este aviso  ",
                        bootstyle="success-outline",
                        command=lambda e=ev_enr, p=pw: _abrir_ventana_correo(e, parent=p),
                    ).pack(anchor="w", pady=(4, 0))

            # ── FESTIVOS ────────────────────────────────────────
            for ft in fests:
                ev_enr = _enriquecer_evento_correo(
                    ft, "FESTIVO",
                    ft.get("fecha", "")
                )
                frf = ttk.Frame(pw._pan_body, bootstyle="danger", padding=(8, 5))
                frf.pack(fill="x", pady=(0, 6))
                ttk.Label(frf, text="🎉  " + ft["titulo"],
                          font=("Segoe UI", 9, "bold"),
                          bootstyle="inverse-danger",
                          wraplength=pw._pw_val - 36).pack(anchor="w")
                if ev_enr["PermiteCorreo"]:
                    ttk.Button(
                        frf,
                        text="  ✉  Enviar correo sobre este aviso  ",
                        bootstyle="danger-outline",
                        command=lambda e=ev_enr, p=pw: _abrir_ventana_correo(e, parent=p),
                    ).pack(anchor="w", pady=(4, 0))

            for ev in sorted(eventos, key=lambda x: x["hora"]):
                es_rep = ev.get("repeticion", "ninguna") != "ninguna"
                icono  = "🔁" if es_rep else "🔔"
                fre = ttk.Frame(pw._pan_body, bootstyle="secondary", padding=(8, 6))
                fre.pack(fill="x", pady=(0, 5))
                ttk.Label(fre,
                          text=f"{icono}  {ev['hora']}",
                          font=("Segoe UI", 10, "bold"),
                          bootstyle="inverse-secondary").pack(anchor="w")
                ttk.Label(fre,
                          text=ev["titulo"],
                          font=("Segoe UI", 9),
                          bootstyle="inverse-secondary",
                          wraplength=pw._pw_val - 36).pack(anchor="w", pady=(2, 0))

    def _posicionar_panel_win():
        """Coloca la subventana a la izquierda del calendario principal."""
        pw = _panel_win[0]
        if pw is None or not pw.winfo_exists():
            return
        pw.update_idletasks()
        _ph = min(max(pw.winfo_reqheight() + 10, 420), _sh - 60)
        # Obtener posición actual del calendario
        wx = win.winfo_x()
        wy = win.winfo_y()
        wh = win.winfo_height()
        # Colocar subventana justo a la izquierda con separación de 8px
        _px = max(0, wx - _pw - 8)
        _py = wy + (wh - _ph) // 2
        pw.geometry(f"{_pw}x{_ph}+{_px}+{_py}")
        pw.deiconify()

    def _mostrar_panel_dia(fecha_dt):
        """Crea o actualiza la subventana de detalle y la posiciona."""
        dia_sel[0] = fecha_dt
        _construir_panel_win()
        _rellenar_panel_win(fecha_dt)
        _posicionar_panel_win()

    def _ocultar_panel_dia():
        dia_sel[0] = None
        if _panel_win[0] is not None and _panel_win[0].winfo_exists():
            _panel_win[0].destroy()
            _panel_win[0] = None


    # ── Área y label creados antes de las funciones que los usan ─────────────
    # (v4.18.12) La cabecera se crea antes que el título del periodo para que este sea hijo
    # suyo y quede entre ◀ y ▶. Antes era hijo de frm_cal y se colocaba a la izquierda del
    # calendario, quitándole ancho (en la vista Semana no se veía el domingo).
    top = ttk.Frame(frm_cal, padding=(16, 12, 16, 6))
    top.pack(fill="x")
    cal_frame   = ttk.Frame(frm_cal, padding=(10, 8, 10, 8))
    lbl_periodo = ttk.Label(top, text="", font=("Segoe UI", 13, "bold"))

    def renderizar():
        for w in cal_frame.winfo_children():
            w.destroy()
        if vista_var.get() == "mes":
            _render_mes()
        else:
            _render_semana()

    def _navegar(delta):
        d = nav_fecha[0]
        if vista_var.get() == "mes":
            mes = d.month + delta
            año = d.year
            if mes > 12: mes, año = 1, año + 1
            elif mes < 1: mes, año = 12, año - 1
            nav_fecha[0] = d.replace(year=año, month=mes, day=1)
        else:
            nav_fecha[0] = d + timedelta(weeks=delta)
        renderizar()

    # ── Cabecera de navegación (el marco «top» se crea más arriba) ──

    ttk.Button(top, text="◀", width=3, bootstyle="secondary-outline",
               command=lambda: _navegar(-1)).pack(side="left")

    lbl_periodo.pack(side="left", padx=10)

    ttk.Button(top, text="▶", width=3, bootstyle="secondary-outline",
               command=lambda: _navegar(+1)).pack(side="left", padx=(0, 16))

    frm_toggle = ttk.Frame(top)
    frm_toggle.pack(side="left")
    ttk.Radiobutton(frm_toggle, text="  Mes  ", variable=vista_var, value="mes",
                    bootstyle="toolbutton-info",
                    command=renderizar).pack(side="left")
    def _a_semana():
        # (v4.18.12) Al pasar de Mes a Semana se abre la semana del día elegido o la de hoy
        # si está en el mes que se veía; antes salía siempre la semana del día 1.
        d = nav_fecha[0]
        for candidato in (dia_sel[0], hoy):
            if candidato and (candidato.year, candidato.month) == (d.year, d.month):
                nav_fecha[0] = candidato
                break
        renderizar()

    ttk.Radiobutton(frm_toggle, text=" Semana ", variable=vista_var, value="semana",
                    bootstyle="toolbutton-info",
                    command=_a_semana).pack(side="left")

    ttk.Button(top, text="  🏖  Vacaciones  ", bootstyle="warning-outline",
               command=lambda: _ventana_vacaciones(ctx)).pack(side="right")
    ttk.Button(top, text="  🎉  Festivos  ", bootstyle="danger-outline",
               command=lambda: _ventana_festivos(ctx)).pack(side="right", padx=(0, 6))
    ttk.Button(top, text="  💬  Chat  ", bootstyle="info-outline",
               command=lambda: _ventana_chat(ctx)).pack(side="right", padx=(0, 6))

    # ── Leyenda ───────────────────────────────────────────
    ley = ttk.Frame(frm_cal, padding=(16, 0, 16, 6))
    ley.pack(fill="x")
    for txt, fg in [("🔔 Aviso único", LIGHT),
                    ("🔁 Repetitivo",  LIGHT),
                    ("🏖 Vacaciones",  LIGHT),
                    ("🎉 Festivo",     LIGHT),
                    ("■ Hoy",         GOLD)]:
        ttk.Label(ley, text=txt, font=("Segoe UI", 8),
                  foreground=fg).pack(side="left", padx=8)

    ttk.Separator(frm_cal).pack(fill="x")

    # ── Área del calendario ───────────────────────────────
    cal_frame.pack(fill="both", expand=True)

    def _render_mes():
        d   = nav_fecha[0]
        año = d.year
        mes = d.month
        lbl_periodo.config(text=f"{_NOMBRES_MES[mes-1]}  {año}")

        for c, ds in enumerate(_DIAS_SEM):
            cal_frame.columnconfigure(c, weight=1, minsize=110)
            ttk.Label(cal_frame, text=ds, font=("Segoe UI", 9, "bold"),
                      anchor="center", bootstyle="inverse-secondary"
                      ).grid(row=0, column=c, padx=2, pady=(0, 4),
                             sticky="ew", ipady=4)

        semanas = _cal_mod.monthcalendar(año, mes)
        for s_idx, semana in enumerate(semanas):
            cal_frame.rowconfigure(s_idx + 1, weight=1, minsize=90)
            for d_idx, dia in enumerate(semana):
                if dia == 0:
                    ttk.Frame(cal_frame).grid(
                        row=s_idx+1, column=d_idx, padx=2, pady=2, sticky="nsew")
                    continue
                fecha_dt = date(año, mes, dia)
                eventos  = _eventos_del_dia(ctx, fecha_dt)
                vacs     = _vacaciones_del_dia(ctx, fecha_dt)
                fests    = _festivos_del_dia(ctx, fecha_dt)
                es_hoy   = fecha_dt == hoy
                es_sel   = fecha_dt == dia_sel[0]

                if es_sel:
                    estilo = "info"
                elif es_hoy:
                    estilo = "warning"
                elif fests:
                    estilo = "danger"
                elif vacs:
                    estilo = "success"
                elif eventos:
                    estilo = "primary"
                else:
                    estilo = "secondary"

                cell = ttk.Frame(cal_frame, bootstyle=estilo, padding=(4, 3),
                                 cursor="hand2")
                cell.grid(row=s_idx+1, column=d_idx, padx=2, pady=2, sticky="nsew")

                ttk.Label(cell, text=str(dia),
                          font=("Segoe UI", 10, "bold" if es_hoy else "normal"),
                          anchor="nw",
                          cursor="hand2").pack(anchor="nw")

                iconos = ""
                if any(a.get("repeticion","ninguna") == "ninguna" for a in eventos):
                    iconos += "🔔"
                if any(a.get("repeticion","ninguna") != "ninguna" for a in eventos):
                    iconos += "🔁"
                if vacs:
                    iconos += "🏖"
                if fests:
                    iconos += "🎉"
                if iconos:
                    ttk.Label(cell, text=iconos,
                              font=("Segoe UI", 8),
                              cursor="hand2").pack(anchor="sw")
                if fests:
                    nombre = fests[0]["titulo"]
                    if len(nombre) > 18: nombre = nombre[:17] + "…"
                    ttk.Label(cell, text=nombre,
                              font=("Segoe UI", 8),
                              wraplength=95,
                              cursor="hand2").pack(anchor="sw", fill="x")
                elif vacs:
                    nombre = vacs[0]["titulo"]
                    if len(nombre) > 18: nombre = nombre[:17] + "…"
                    ttk.Label(cell, text=nombre,
                              font=("Segoe UI", 8),
                              wraplength=95,
                              cursor="hand2").pack(anchor="sw", fill="x")

                # Clic en cualquier widget del cell → mostrar subventana de detalle
                def _on_click_dia(e, fd=fecha_dt):
                    if dia_sel[0] == fd:
                        _ocultar_panel_dia()
                        renderizar()
                    else:
                        _mostrar_panel_dia(fd)
                        renderizar()
                        # Reposicionar subventana tras renderizar (win puede haber cambiado)
                        win.after(50, _posicionar_panel_win)
                cell.bind("<Button-1>", _on_click_dia)
                for child in cell.winfo_children():
                    child.bind("<Button-1>", _on_click_dia)

    def _render_semana():
        d     = nav_fecha[0]
        lunes = d - timedelta(days=d.weekday())
        dom   = lunes + timedelta(days=6)
        lbl_periodo.config(
            text=f"Semana  {lunes.strftime('%d/%m')} — {dom.strftime('%d/%m/%Y')}")

        for c in range(7):
            cal_frame.columnconfigure(c, weight=1)
            fecha_dt = lunes + timedelta(days=c)
            eventos  = _eventos_del_dia(ctx, fecha_dt)
            vacs     = _vacaciones_del_dia(ctx, fecha_dt)
            fests    = _festivos_del_dia(ctx, fecha_dt)
            es_hoy   = fecha_dt == hoy
            es_sel   = fecha_dt == dia_sel[0]

            h_estilo = "info" if es_sel else ("warning" if es_hoy else "secondary")
            hdr = ttk.Frame(cal_frame, bootstyle=h_estilo, padding=(4, 3),
                            cursor="hand2")
            hdr.grid(row=0, column=c, padx=3, sticky="ew", ipady=2)
            ttk.Label(hdr, text=_DIAS_SEM[c],
                      font=("Segoe UI", 9, "bold"), anchor="center",
                      cursor="hand2").pack()
            ttk.Label(hdr, text=fecha_dt.strftime("%d/%m"),
                      font=("Segoe UI", 8), anchor="center",
                      cursor="hand2").pack()

            c_estilo = "danger" if fests else ("success" if vacs else ("primary" if eventos else "dark"))
            cuerpo = ttk.Frame(cal_frame, bootstyle=c_estilo, padding=(6, 6))
            cuerpo.grid(row=1, column=c, padx=3, pady=(2, 0), sticky="nsew")
            cal_frame.rowconfigure(1, weight=1)

            if fests:
                for ft in fests:
                    ttk.Label(cuerpo, text=f"🎉 {ft['titulo']}",
                              font=("Segoe UI", 8, "bold"),
                              wraplength=108).pack(anchor="w", pady=(0, 4))

            if vacs:
                for v in vacs:
                    ttk.Label(cuerpo, text=f"🏖 {v['titulo']}",
                              font=("Segoe UI", 8, "bold"),
                              wraplength=108).pack(anchor="w", pady=(0, 4))

            for ev in sorted(eventos, key=lambda x: x["hora"]):
                icono = "🔁" if ev.get("repeticion","ninguna") != "ninguna" else "🔔"
                ttk.Label(cuerpo,
                          text=f"{icono} {ev['hora']}  {ev['titulo']}",
                          font=("Segoe UI", 8),
                          wraplength=108).pack(anchor="w", pady=1)

            if not eventos and not vacs and not fests:
                ttk.Label(cuerpo, text="—", foreground="gray",
                          font=("Segoe UI", 9)).pack(pady=10)

            def _on_click_sem(e, fd=fecha_dt):
                if dia_sel[0] == fd:
                    _ocultar_panel_dia()
                    renderizar()
                else:
                    _mostrar_panel_dia(fd)
                    renderizar()
                    win.after(50, _posicionar_panel_win)
            hdr.bind("<Button-1>", _on_click_sem)
            for child in hdr.winfo_children():
                child.bind("<Button-1>", _on_click_sem)

    renderizar()

    # ── Funciones de impresión ────────────────────────────
    def _esc(valor):
        # (v4.16.9) Todo lo que viene de la agenda (títulos, horas, nombre de
        # usuario) se escapa antes de meterlo en el HTML de impresión: un evento
        # importado con <script> ya no se ejecuta en el navegador.
        import html as _html
        return _html.escape(str(valor), quote=True)

    def _nombre_dia_largo(fecha_dt):
        nombres = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
        return nombres[fecha_dt.weekday()]

    def _html_estilos():
        return """
        <style>
          body { font-family: 'Segoe UI', Arial, sans-serif; margin: 30px; color: #1a1a2e; }
          .cabecera {
            border-bottom: 3px solid #1a6fa6;
            padding-bottom: 14px;
            margin-bottom: 20px;
          }
          .cabecera h1 { font-size: 22px; margin: 0 0 4px 0; color: #1a6fa6; }
          .cabecera .usuario { font-size: 13px; color: #555; margin: 0; }
          table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 8px; }
          thead tr { background: #1a6fa6; color: #fff; }
          thead th { padding: 9px 14px; text-align: left; font-weight: 600; }
          tbody tr:nth-child(even) { background: #f0f6fb; }
          tbody td { padding: 8px 14px; border-bottom: 1px solid #d0e4f0; vertical-align: top; }
          tbody tr:last-child td { border-bottom: 2px solid #1a6fa6; }
          .sin-eventos { color: #999; font-style: italic; }
          .pie { margin-top: 18px; font-size: 11px; color: #aaa; text-align: right; }
          @media print { body { margin: 15px; } }
        </style>
        """

    def _filas_dia(fecha_dt):
        eventos = _eventos_del_dia(ctx, fecha_dt)
        vacs    = _vacaciones_del_dia(ctx, fecha_dt)
        fests   = _festivos_del_dia(ctx, fecha_dt)
        filas   = ""
        fecha_str  = fecha_dt.strftime("%d/%m/%Y")
        dia_nombre = _nombre_dia_largo(fecha_dt)
        if eventos or vacs or fests:
            for ev in sorted(eventos, key=lambda x: x.get("hora", "")):
                filas += (f"<tr><td>{fecha_str}</td><td>{dia_nombre}</td>"
                          f"<td>{_esc(ev.get('hora','—'))}</td>"
                          f"<td>{_esc(ev.get('titulo',''))}</td></tr>")
            for v in vacs:
                filas += (f"<tr><td>{fecha_str}</td><td>{dia_nombre}</td>"
                          f"<td>🏖</td><td>{_esc(v.get('titulo','Vacaciones'))}</td></tr>")
            for ft in fests:
                filas += (f"<tr><td>{fecha_str}</td><td>{dia_nombre}</td>"
                          f"<td>🎉</td><td>{_esc(ft.get('titulo','Festivo'))}</td></tr>")
        return filas

    def _abrir_html_impresion(titulo, subtitulo, cuerpo_filas):
        import tempfile
        import webbrowser
        usuario = ctx.nombre_usuario
        ahora   = datetime.now().strftime("%d/%m/%Y %H:%M")
        if not cuerpo_filas:
            cuerpo_filas = ("<tr><td colspan='4' class='sin-eventos'>"
                            "Sin eventos registrados para este período.</td></tr>")
        html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><title>{_esc(titulo)}</title>{_html_estilos()}</head>
<body>
  <div class="cabecera">
    <h1>{_esc(titulo)}</h1>
    <p class="usuario">
      {_esc(subtitulo)}&nbsp;&nbsp;|&nbsp;&nbsp;
      <strong>Usuario:</strong> {_esc(usuario)}&nbsp;&nbsp;|&nbsp;&nbsp;
      Impreso: {ahora}
    </p>
  </div>
  <table>
    <thead>
      <tr>
        <th>Fecha</th>
        <th>Día</th>
        <th>Hora</th>
        <th>Descripción</th>
      </tr>
    </thead>
    <tbody>{cuerpo_filas}</tbody>
  </table>
  <div class="pie">Central Compras Princess Canarias &mdash; © VAMA 2026</div>
  <script>window.onload = function(){{ window.print(); }}</script>
</body>
</html>"""
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=".html",
            mode="w", encoding="utf-8"
        )
        tmp.write(html)
        tmp.close()
        webbrowser.open(f"file:///{tmp.name.replace(chr(92), '/')}")

    def _imprimir_dia():
        fecha_dt = dia_sel[0] if dia_sel[0] else date.today()
        titulo   = "Agenda del Día"
        subtitulo = fecha_dt.strftime("%d/%m/%Y") + " — " + _nombre_dia_largo(fecha_dt)
        _abrir_html_impresion(titulo, subtitulo, _filas_dia(fecha_dt))

    def _imprimir_semana():
        d     = nav_fecha[0]
        lunes = d - timedelta(days=d.weekday())
        dom   = lunes + timedelta(days=6)
        titulo    = "Agenda Semanal"
        subtitulo = (f"Semana del {lunes.strftime('%d/%m/%Y')} "
                     f"al {dom.strftime('%d/%m/%Y')}")
        filas = ""
        for i in range(7):
            filas += _filas_dia(lunes + timedelta(days=i))
        _abrir_html_impresion(titulo, subtitulo, filas)

    def _imprimir_mes():
        d     = nav_fecha[0]
        año   = d.year
        mes   = d.month
        titulo    = "Agenda Mensual"
        subtitulo = f"{_NOMBRES_MES[mes-1]} {año}"
        dias_en_mes = _cal_mod.monthrange(año, mes)[1]
        filas = ""
        for dia in range(1, dias_en_mes + 1):
            filas += _filas_dia(date(año, mes, dia))
        _abrir_html_impresion(titulo, subtitulo, filas)

    # ── Pie de página ─────────────────────────────────────
    ttk.Separator(frm_cal).pack(fill="x", pady=(6, 0))
    pie = ttk.Frame(frm_cal, padding=(16, 8, 16, 12))
    pie.pack(fill="x")
    def _cerrar_todo():
        _ocultar_panel_dia()
        win.destroy()

    # Botones de impresión (lado izquierdo del pie)
    frm_print = ttk.Frame(pie)
    frm_print.pack(side="left")
    ttk.Button(frm_print,
               text="🖨  Agenda del Día",
               bootstyle="info-outline",
               command=_imprimir_dia).pack(side="left", padx=(0, 6))
    ttk.Button(frm_print,
               text="🖨  Agenda Semanal",
               bootstyle="success-outline",
               command=_imprimir_semana).pack(side="left", padx=(0, 6))
    ttk.Button(frm_print,
               text="🖨  Agenda Mensual",
               bootstyle="warning-outline",
               command=_imprimir_mes).pack(side="left")

    ttk.Button(pie, text="  Cerrar  ",
               bootstyle="secondary",
               command=_cerrar_todo).pack(side="right")

    win.protocol("WM_DELETE_WINDOW", _cerrar_todo)

    try:                                  # ANTI-REGRESION: si renderizar() u otra fase crashea,
        win.update_idletasks()            # la ventana no queda ciega (withdrawn sin deiconify)
        _ch = min(max(win.winfo_reqheight() + 10, 720), _sh - 60)
        # Posicionar cerca del borde derecho de pantalla
        _x  = max(0, _sw - _cw_cal - _margin)
        _y  = (_sh - _ch) // 2
        win.geometry(f"{_cw_cal}x{_ch}+{_x}+{_y}")
        win.deiconify()
        win.focus_force()
    except Exception:
        import traceback as _tb
        print(f"[ERROR abrir_calendario] {_tb.format_exc()}")
        try: win.destroy()
        except Exception: pass
