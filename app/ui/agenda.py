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
from ui.assets import _apply_icon
from ui.selector_fecha_hora import campo_fecha, campo_hora
from utils.fechas import _iso_a_ui, _ui_a_iso
from services import sincro_agenda   # (v4.18.66) agenda sincronizada con Control de Pedidos
import tkinter as tk
from ui import estilo_calendario as E          # (v4.18.72) aspecto nuevo
from utils import textos_calendario as T


def abrir_agenda(ctx):
    """Ventana principal de avisos/recordatorios."""
    win = ttk.Toplevel()
    win.title("📅 Agenda de Avisos")
    win.resizable(True, True)   # (v4.18.72) también en vertical, como Vacaciones y Festivos
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

    # (v4.18.72) Rediseño con el mismo aspecto que Calendario, Vacaciones y Festivos (ui/estilo_calendario.py):
    # cabecera con resumen y una tarjeta por aviso, con la hora en grande, la franja del color de su tipo
    # (azul único, cian repetitivo, gris desactivado) y, debajo del título, cuándo salta y su antelación.
    win.configure(background=E.FONDO)
    v_resumen = StringVar()
    E.cabecera(win, "📅", "Mis Recordatorios", v_resumen)
    scrollable_frame = E.lista_desplazable(win, win)

    def _tarjeta_aviso(i, aviso, ahora):
        rep    = aviso.get("repeticion", "ninguna")
        es_rep = rep != "ninguna"
        # ANTI-REGRESION (Fase 3.7g): indicador visual de aviso desactivado
        activo = aviso.get("activo", True)
        pasado = T.aviso_pasado(aviso, ahora)
        apagado = (not activo) or pasado
        color = E.CIAN if es_rep else E.AZUL
        _, cuerpo = E.tarjeta(scrollable_frame, color, apagado=apagado)

        # Hora en grande y tipo debajo, como el bloque de fecha de Vacaciones y Festivos
        bloque = tk.Frame(cuerpo, bg=E.TARJETA, width=64)
        bloque.pack(side="left", padx=(0, 14))
        E.etiqueta(bloque, T.hora_aviso(aviso), color=E.TEXTO_APAGADO if apagado else E.TEXTO,
                   fuente=("Segoe UI", 15, "bold")).pack()
        E.etiqueta(bloque, T.NOMBRE_REPETICION.get(rep, rep).upper(),
                   color=E.TEXTO_APAGADO if apagado else color, fuente=E.F_PEQUE_NEG).pack()

        # Botones PRIMERO (side=right) para que el texto no los desplace
        botones = E.botones_fila(cuerpo, lambda ix=i: _editar_aviso(ix), lambda ix=i: _eliminar_aviso(ix))
        botones.pack(side="right")
        if not activo:
            ttk.Button(botones, text="▶", bootstyle="success-outline", width=3,
                       command=lambda ix=i: _reactivar_aviso(ix)).pack(side="left", padx=(6, 0))

        texto = tk.Frame(cuerpo, bg=E.TARJETA)
        texto.pack(side="left", fill="x", expand=True)
        fila1 = tk.Frame(texto, bg=E.TARJETA)
        fila1.pack(fill="x")
        E.etiqueta(fila1, aviso.get("titulo", ""), fuente=("Segoe UI", 10, "bold overstrike") if not activo else E.F_NEGRITA,
                   color=E.TEXTO_SUAVE if apagado else E.TEXTO, anchor="w", justify="left",
                   wraplength=max(300, win.winfo_width() - 330)).pack(side="left")
        if not activo:
            E.etiqueta_estado(fila1, "⏸ Desactivado", E.DORADO).pack(side="left", padx=(8, 0))
        elif pasado:
            E.etiqueta_estado(fila1, "Pasado", E.TEXTO_APAGADO).pack(side="left", padx=(8, 0))
        detalle = T.cuando_aviso(aviso)
        if not es_rep and not pasado:
            falta = T.cuanto_falta(aviso.get("fecha"), ahora.date())
            if falta:
                detalle += f"   ·   {falta}"
        ant = T.antelacion(aviso.get("antelacion"))
        if ant:
            detalle += f"   ·   ⏰ {ant}"
        E.etiqueta(texto, detalle, color=E.TEXTO_APAGADO if apagado else E.TEXTO_SUAVE,
                   fuente=E.F_SUBTITULO, anchor="w").pack(fill="x", pady=(2, 0))

    def cargar_avisos():
        for w in scrollable_frame.winfo_children():
            w.destroy()
        avisos = ctx.agenda_data.get("avisos", [])
        avisos.sort(key=lambda x: (x.get("repeticion","ninguna") != "ninguna",
                                   x["hora"], x["fecha"]))
        ahora = datetime.now()
        v_resumen.set(T.resumen_agenda(avisos, ahora))
        if not avisos:
            E.vacia(scrollable_frame, "No hay avisos programados.\nPulsa «+  Añadir Aviso» para crear el primero.")
            return
        grupo = None
        for i, aviso in enumerate(avisos):
            es_rep = aviso.get("repeticion", "ninguna") != "ninguna"
            if es_rep != grupo:
                grupo = es_rep
                n = sum(1 for a in avisos if (a.get("repeticion", "ninguna") != "ninguna") == es_rep)
                E.separador_anio(scrollable_frame, "Repetitivos" if es_rep else "Avisos únicos",
                                 f"{n} aviso{'s' if n != 1 else ''}")
            _tarjeta_aviso(i, aviso, ahora)

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
    btn_bar = tk.Frame(win, bg=E.FONDO)
    btn_bar.pack(fill="x", padx=22, pady=(12, 16))
    # (v4.18.72) «+» normal: el «＋» de ancho completo salía con otra letra en el botón.
    ttk.Button(btn_bar, text="+  Añadir Aviso",
               bootstyle="primary", command=_nuevo_aviso).pack(side="left")
    ttk.Button(btn_bar, text="  Cerrar  ",
               bootstyle="secondary", command=win.destroy).pack(side="right")

    # ANTI-REGRESION (Fase 3.7g): registrar cargar_avisos como callback en alertas
    # para que _desactivar_evento() refresque la lista sin necesidad de cerrar y reabrir la ventana.
    _alertas_mod.on_agenda_changed = cargar_avisos
    sincro_agenda.registrar_refresco(win, cargar_avisos)   # (v4.18.66) cambios llegados de otro PC

    cargar_avisos()

    # Centrar con altura real tras construir todos los widgets
    win.update_idletasks()
    _ah = min(max(win.winfo_reqheight() + 10, 520), _sh - 80)
    win.geometry(f"{_aw}x{_ah}+{(_sw - _aw)//2}+{(_sh - _ah)//2}")

    win.grab_set()
