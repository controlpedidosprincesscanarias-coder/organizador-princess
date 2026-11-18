"""
ui/calendario.py
Ventana «Calendario» (vista de mes y de semana) con avisos, vacaciones y festivos, y acceso a
Festivos, Vacaciones y a las agendas imprimibles del día, la semana y el mes.
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
from ui.colores import LIGHT
from ui.festivos import _ventana_festivos
from ui.vacaciones import _ventana_vacaciones
from services import sincro_agenda   # (v4.18.66) agenda sincronizada con Control de Pedidos
import tkinter as tk
from ui import estilo_calendario as E          # (v4.18.72) aspecto nuevo
from utils.textos_calendario import lineas_celda, MESES_CORTOS as _MESES_CORTOS, rango as rango_fechas

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
        pan_body = tk.Frame(pw, bg=E.FONDO, padx=12, pady=10)
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
        pw._lbl_dia_nombre.config(text=_dia_nombres[fecha_dt.weekday()].capitalize())
        # (v4.18.72) «28 de noviembre de 2026» en lugar de «28/11/2026»
        pw._lbl_dia_fecha.config(text=f"{fecha_dt.day} de {_NOMBRES_MES[fecha_dt.month-1].lower()} de {fecha_dt.year}")

        # Limpiar cuerpo anterior
        for w in pw._pan_body.winfo_children():
            w.destroy()

        eventos = _eventos_del_dia(ctx, fecha_dt)
        vacs    = _vacaciones_del_dia(ctx, fecha_dt)
        fests   = _festivos_del_dia(ctx, fecha_dt)

        # (v4.18.72) Cada cosa del día en una tarjeta con la franja de su color, como en el calendario.
        def _tarjeta(tipo, titulo, detalle="", ev_correo=None):
            fondo = E.TARJETA
            marco = tk.Frame(pw._pan_body, bg=fondo, highlightthickness=1, highlightbackground=E.BORDE)
            marco.pack(fill="x", pady=(0, 6))
            tk.Frame(marco, bg=E.COLOR_TIPO[tipo], width=4).pack(side="left", fill="y")
            cuerpo = tk.Frame(marco, bg=fondo)
            cuerpo.pack(side="left", fill="both", expand=True, padx=10, pady=7)
            E.etiqueta(cuerpo, f"{E.ICONO_TIPO[tipo]}  {titulo}", fuente=E.F_NEGRITA, anchor="w",
                       justify="left", wraplength=pw._pw_val - 60).pack(fill="x")
            if detalle:
                E.etiqueta(cuerpo, detalle, color=E.TEXTO_SUAVE, fuente=E.F_PEQUE, anchor="w",
                           justify="left", wraplength=pw._pw_val - 60).pack(fill="x", pady=(2, 0))
            if ev_correo is not None and ev_correo["PermiteCorreo"]:
                ttk.Button(cuerpo, text="  ✉  Enviar correo sobre este aviso  ",
                           bootstyle="light-outline",
                           command=lambda e=ev_correo, p=pw: _abrir_ventana_correo(e, parent=p),
                           ).pack(anchor="w", pady=(6, 0))

        if not eventos and not vacs and not fests:
            E.etiqueta(pw._pan_body, "Sin avisos para este día.", fondo=E.FONDO, color=E.TEXTO_SUAVE,
                       fuente=E.F_NORMAL).pack(expand=True, pady=30)
        else:
            for ft in fests:
                ev_enr = _enriquecer_evento_correo(ft, "FESTIVO", ft.get("fecha", ""))
                _tarjeta("festivo", ft["titulo"], "Festivo", ev_enr)
            for v in vacs:
                ev_enr = _enriquecer_evento_correo(v, "VACACIONES",
                                                   v.get("fecha_inicio", ""), v.get("fecha_fin", ""))
                _tarjeta("vacaciones", v["titulo"],
                         "Vacaciones: " + rango_fechas(v.get("fecha_inicio"), v.get("fecha_fin")), ev_enr)
            _rep = {"diario": "Todos los días", "semanal": "Cada semana", "mensual": "Cada mes",
                    "cada_hora": "Cada hora", "cada_30min": "Cada 30 minutos"}
            for ev in sorted(eventos, key=lambda x: x["hora"]):
                rep = ev.get("repeticion", "ninguna")
                _tarjeta("aviso" if rep == "ninguna" else "repetitivo", f"{ev['hora']}   {ev['titulo']}",
                         _rep.get(rep, "Aviso único") if rep != "ninguna" else "Aviso único")

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
    # (v4.18.72) Rediseño: celdas oscuras con el número del día y, dentro, una línea por festivo,
    # vacaciones y aviso (con su hora y su título), hoy con borde dorado, el día elegido en cian y los
    # días del mes anterior y siguiente en gris. Colores en ui/estilo_calendario.py.
    win.configure(background=E.FONDO)
    top = ttk.Frame(frm_cal, padding=(18, 14, 18, 2))      # fila 1: periodo y botones de las otras ventanas
    top.pack(fill="x")
    nav = ttk.Frame(frm_cal, padding=(18, 8, 18, 8))       # fila 2: navegación, Mes/Semana y leyenda
    nav.pack(fill="x")
    cal_frame   = tk.Frame(frm_cal, bg=E.FONDO)
    lbl_periodo = ttk.Label(top, text="", font=E.F_TITULO)

    def renderizar():
        for w in cal_frame.winfo_children():
            w.destroy()
        for i in range(8):
            cal_frame.rowconfigure(i, weight=0, minsize=0, uniform="")
            cal_frame.columnconfigure(i, weight=0, minsize=0, uniform="")
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

    def _ir_a_hoy():
        # (v4.18.72) Botón «Hoy»: vuelve al mes (o a la semana) de hoy.
        nav_fecha[0] = hoy if vista_var.get() == "semana" else hoy.replace(day=1)
        renderizar()

    # ── Cabecera de navegación (el marco «top» se crea más arriba) ──

    lbl_periodo.pack(side="left")

    ttk.Button(nav, text="◀", width=3, bootstyle="secondary",
               command=lambda: _navegar(-1)).pack(side="left")
    ttk.Button(nav, text="Hoy", bootstyle="light-outline",
               command=_ir_a_hoy).pack(side="left", padx=4)
    ttk.Button(nav, text="▶", width=3, bootstyle="secondary",
               command=lambda: _navegar(+1)).pack(side="left", padx=(0, 14))

    frm_toggle = ttk.Frame(nav)
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

    ttk.Button(top, text="  🏖  Vacaciones  ", bootstyle="success-outline",
               command=lambda: _ventana_vacaciones(ctx)).pack(side="right")
    ttk.Button(top, text="  🎉  Festivos  ", bootstyle="danger-outline",
               command=lambda: _ventana_festivos(ctx)).pack(side="right", padx=(0, 6))
    # (v4.18.72) Sin botón «Chat»: venía de versiones antiguas y el chat ya está en el menú principal (petición de Víctor).

    # ── Leyenda: un punto del color de cada tipo ──────────
    ley = tk.Frame(nav, bg=E.FONDO)
    ley.pack(side="right")
    for txt, color in [("Aviso único", E.AZUL), ("Repetitivo", E.CIAN), ("Vacaciones", E.VERDE),
                       ("Festivo", E.ROJO), ("Hoy", E.DORADO)]:
        E.etiqueta(ley, "●", fondo=E.FONDO, color=color, fuente=E.F_NORMAL).pack(side="left", padx=(12, 0))
        E.etiqueta(ley, txt, fondo=E.FONDO, color=E.TEXTO_SUAVE, fuente=E.F_PEQUE).pack(side="left", padx=(3, 0))

    # ── Área del calendario ───────────────────────────────
    cal_frame.pack(fill="both", expand=True, padx=16, pady=(0, 4))

    def _al_pulsar(widget, fd):
        """Clic en la celda o en cualquier cosa de dentro: abre o cierra el detalle del día."""
        def _on_click(e, fd=fd):
            if dia_sel[0] == fd:
                _ocultar_panel_dia()
                renderizar()
            else:
                _mostrar_panel_dia(fd)
                renderizar()
                # Reposicionar subventana tras renderizar (win puede haber cambiado)
                win.after(50, _posicionar_panel_win)
        pila = [widget]
        while pila:
            w = pila.pop()
            w.bind("<Button-1>", _on_click)
            w.configure(cursor="hand2")
            pila.extend(w.winfo_children())

    def _linea(padre, tipo, texto, fondo):
        """Una línea de la celda: franja del color del tipo y el texto sobre un fondo suave."""
        fila = tk.Frame(padre, bg=E.FONDO_TIPO.get(tipo, fondo))
        fila.pack(fill="x", pady=(2, 0))
        if tipo != "mas":
            tk.Frame(fila, bg=E.COLOR_TIPO[tipo], width=3).pack(side="left", fill="y")
        icono = E.ICONO_TIPO.get(tipo, "")
        E.etiqueta(fila, f"{icono} {texto}".strip() if tipo in ("festivo", "vacaciones") else texto,
                   fondo=E.FONDO_TIPO.get(tipo, fondo),
                   color=E.TEXTO_SUAVE if tipo == "mas" else E.TEXTO,
                   fuente=E.F_PEQUE, anchor="w").pack(side="left", fill="x", padx=(4, 2))

    def _numero_dia(padre, fecha_dt, fondo, es_hoy, fuera, grande=False):
        fuente = ("Segoe UI", 16 if grande else 10, "bold" if (es_hoy or grande) else "normal")
        if es_hoy:
            lbl = tk.Label(padre, text=f" {fecha_dt.day} ", bg=E.DORADO, fg=E.FONDO, font=fuente, bd=0)
        else:
            lbl = E.etiqueta(padre, str(fecha_dt.day), fondo=fondo,
                             color=E.TEXTO_APAGADO if fuera else E.TEXTO, fuente=fuente)
        lbl._fuera_mes = fuera   # (v4.18.72) las capturas del manual distinguen los días de otro mes
        return lbl

    def _celda(fecha_dt, fuera):
        es_hoy = fecha_dt == hoy
        es_sel = fecha_dt == dia_sel[0]
        if fuera:
            fondo = E.FUERA_MES
        elif fecha_dt.weekday() >= 5:
            fondo = E.TARJETA_FIN
        else:
            fondo = E.TARJETA
        borde = E.CIAN if es_sel else (E.DORADO if es_hoy else E.BORDE)
        cell = tk.Frame(cal_frame, bg=fondo, highlightthickness=2 if (es_sel or es_hoy) else 1,
                        highlightbackground=borde, highlightcolor=borde)
        dentro = tk.Frame(cell, bg=fondo)
        dentro.pack(fill="both", expand=True, padx=6, pady=5)
        _numero_dia(dentro, fecha_dt, fondo, es_hoy, fuera).pack(anchor="nw")
        if not fuera:
            lineas = lineas_celda(_eventos_del_dia(ctx, fecha_dt), _vacaciones_del_dia(ctx, fecha_dt),
                                  _festivos_del_dia(ctx, fecha_dt), maximo=3, ancho=10)
            for tipo, texto in lineas:
                _linea(dentro, tipo, texto, fondo)
            _al_pulsar(cell, fecha_dt)
        return cell

    def _render_mes():
        d   = nav_fecha[0]
        año = d.year
        mes = d.month
        lbl_periodo.config(text=f"{_NOMBRES_MES[mes-1]}  {año}")

        for c, ds in enumerate(_DIAS_SEM):
            cal_frame.columnconfigure(c, weight=1, minsize=110, uniform="col")
            E.etiqueta(cal_frame, ds.upper(), fondo=E.FONDO,
                       color=E.TEXTO_APAGADO if c >= 5 else E.TEXTO_SUAVE,
                       fuente=E.F_PEQUE_NEG, anchor="w").grid(row=0, column=c, padx=(8, 2), pady=(0, 4), sticky="ew")

        semanas = _cal_mod.Calendar(firstweekday=0).monthdatescalendar(año, mes)
        for s_idx, semana in enumerate(semanas):
            cal_frame.rowconfigure(s_idx + 1, weight=1, minsize=92, uniform="fila")
            for d_idx, fecha_dt in enumerate(semana):
                _celda(fecha_dt, fecha_dt.month != mes).grid(
                    row=s_idx + 1, column=d_idx, padx=2, pady=2, sticky="nsew")

    def _render_semana():
        d     = nav_fecha[0]
        lunes = d - timedelta(days=d.weekday())
        dom   = lunes + timedelta(days=6)
        lbl_periodo.config(
            text=f"{lunes.day} {_MESES_CORTOS[lunes.month-1]} – {dom.day} {_MESES_CORTOS[dom.month-1]} {dom.year}")
        cal_frame.rowconfigure(0, weight=1)

        for c in range(7):
            cal_frame.columnconfigure(c, weight=1, uniform="col")
            fecha_dt = lunes + timedelta(days=c)
            eventos  = _eventos_del_dia(ctx, fecha_dt)
            vacs     = _vacaciones_del_dia(ctx, fecha_dt)
            fests    = _festivos_del_dia(ctx, fecha_dt)
            es_hoy   = fecha_dt == hoy
            es_sel   = fecha_dt == dia_sel[0]
            fondo    = E.TARJETA_FIN if c >= 5 else E.TARJETA
            borde    = E.CIAN if es_sel else (E.DORADO if es_hoy else E.BORDE)

            col = tk.Frame(cal_frame, bg=fondo, highlightthickness=2 if (es_sel or es_hoy) else 1,
                           highlightbackground=borde, highlightcolor=borde)
            col.grid(row=0, column=c, padx=3, pady=2, sticky="nsew")
            cab = tk.Frame(col, bg=fondo)
            cab.pack(fill="x", padx=8, pady=(8, 6))
            E.etiqueta(cab, _DIAS_SEM[c].upper(), fondo=fondo,
                       color=E.DORADO if es_hoy else E.TEXTO_SUAVE, fuente=E.F_PEQUE_NEG).pack(anchor="w")
            _numero_dia(cab, fecha_dt, fondo, es_hoy, False, grande=True).pack(anchor="w")
            tk.Frame(col, bg=E.BORDE, height=1).pack(fill="x", padx=8)

            cuerpo = tk.Frame(col, bg=fondo)
            cuerpo.pack(fill="both", expand=True, padx=6, pady=6)
            for tipo, texto in lineas_celda(eventos, vacs, fests, maximo=99, ancho=60):
                fila = tk.Frame(cuerpo, bg=E.FONDO_TIPO[tipo])
                fila.pack(fill="x", pady=(0, 4))
                tk.Frame(fila, bg=E.COLOR_TIPO[tipo], width=3).pack(side="left", fill="y")
                E.etiqueta(fila, f"{E.ICONO_TIPO[tipo]} {texto}", fondo=E.FONDO_TIPO[tipo],
                           fuente=E.F_PEQUE, anchor="w", justify="left",
                           wraplength=104).pack(side="left", fill="x", padx=(4, 2), pady=3)
            if not (eventos or vacs or fests):
                E.etiqueta(cuerpo, "Sin avisos", fondo=fondo, color=E.TEXTO_APAGADO,
                           fuente=E.F_PEQUE).pack(pady=14)
            _al_pulsar(col, fecha_dt)   # (v4.18.72) toda la columna se puede pulsar, no solo la cabecera

    sincro_agenda.registrar_refresco(win, renderizar)   # (v4.18.66) cambios llegados de otro PC
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
    pie = ttk.Frame(frm_cal, padding=(18, 10, 18, 14))
    pie.pack(fill="x")
    def _cerrar_todo():
        _ocultar_panel_dia()
        win.destroy()

    # Botones de impresión (lado izquierdo del pie)
    frm_print = ttk.Frame(pie)
    frm_print.pack(side="left")
    ttk.Button(frm_print,
               text="🖨  Agenda del Día",
               bootstyle="light-outline",
               command=_imprimir_dia).pack(side="left", padx=(0, 6))
    ttk.Button(frm_print,
               text="🖨  Agenda Semanal",
               bootstyle="light-outline",
               command=_imprimir_semana).pack(side="left", padx=(0, 6))
    ttk.Button(frm_print,
               text="🖨  Agenda Mensual",
               bootstyle="light-outline",
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
