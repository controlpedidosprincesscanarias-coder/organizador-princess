"""
app/ui/selector_fecha_hora.py  ·  v4.18.14
Campos de fecha y de hora para los formularios de avisos, vacaciones y festivos.

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

- campo_fecha(): la caja de siempre (DD-MM-AAAA) con un botón 📅 que abre un calendario para
  elegir el día con un clic. También se puede escribir: «15112026», «15/11/2026» o «15-11-26»
  se convierten solos en 15-11-2026 al salir de la caja.
- campo_hora(): dos ruedas, horas y minutos, sin tener que escribir los dos puntos. Se mueven
  con las flechas, la rueda del ratón o escribiendo el número.
Las dos escriben en la misma StringVar de texto («DD-MM-AAAA» y «HH:MM») que usaban los
formularios, así que el guardado y las comprobaciones no cambian.
"""
import calendar
import re
from datetime import date, datetime

import tkinter as tk
import ttkbootstrap as ttk

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre"]
DIAS = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]
FORMATO = "%d-%m-%Y"


from utils.fechas import normalizar_fecha, normalizar_hora  # noqa: E402,F401  (lógica sin interfaz)


def semanas_del_mes(anio: int, mes: int):
    """Semanas del mes empezando en lunes; 0 = hueco de otro mes."""
    return calendar.Calendar(firstweekday=0).monthdayscalendar(anio, mes)


# ── Fecha ─────────────────────────────────────────────────────────────────
def campo_fecha(parent, var, pady=(3, 12)):
    """Caja de fecha con botón de calendario. Se empaqueta sola (fill="x")."""
    frm = ttk.Frame(parent)
    frm.pack(fill="x", pady=pady)
    ent = ttk.Entry(frm, textvariable=var, font=("Segoe UI", 10))
    ent.pack(side="left", fill="x", expand=True)
    btn = ttk.Button(frm, text="📅", width=3, bootstyle="info-outline",
                     command=lambda: abrir_calendario(ent, var))
    btn.pack(side="left", padx=(6, 0))
    ent.bind("<FocusOut>", lambda e: var.set(normalizar_fecha(var.get())), add="+")
    ent.bind("<Alt-Down>", lambda e: abrir_calendario(ent, var), add="+")
    frm.entry, frm.boton = ent, btn
    return frm


def abrir_calendario(ent, var):
    """Calendario desplegable bajo la caja de fecha. Un clic en un día lo elige y se cierra."""
    try:
        actual = datetime.strptime(normalizar_fecha(var.get()), FORMATO).date()
    except ValueError:
        actual = date.today()
    hoy = date.today()
    vista = [actual.year, actual.month]

    dueno = ent.winfo_toplevel()
    grab_anterior = dueno.grab_current()
    pop = ttk.Toplevel(dueno)
    pop.withdraw()
    pop.title("Elegir fecha")
    pop.resizable(False, False)
    pop.transient(dueno)
    marco = ttk.Frame(pop, padding=10)
    marco.pack(fill="both", expand=True)

    cab = ttk.Frame(marco)
    cab.pack(fill="x", pady=(0, 6))
    lbl = ttk.Label(cab, text="", font=("Segoe UI", 11, "bold"), anchor="center")
    rejilla = ttk.Frame(marco)
    rejilla.pack()

    def cerrar(event=None):
        try:
            pop.grab_release()
        except tk.TclError:
            pass
        pop.destroy()
        if grab_anterior is not None:
            try:
                grab_anterior.grab_set()
            except tk.TclError:
                pass
        ent.focus_set()

    def elegir(d):
        var.set(d.strftime(FORMATO))
        cerrar()

    def mover(delta):
        a, m = vista
        m += delta
        if m > 12:
            a, m = a + 1, 1
        elif m < 1:
            a, m = a - 1, 12
        vista[:] = [a, m]
        pintar()

    def pintar():
        for w in rejilla.winfo_children():
            w.destroy()
        a, m = vista
        lbl.configure(text=f"{MESES[m - 1]} {a}")
        for c, nombre in enumerate(DIAS):
            ttk.Label(rejilla, text=nombre, width=4, anchor="center", font=("Segoe UI", 9, "bold"),
                      foreground="#e74c3c" if c >= 5 else None).grid(row=0, column=c, pady=(0, 2))
        for f, semana in enumerate(semanas_del_mes(a, m), start=1):
            for c, dia in enumerate(semana):
                if not dia:
                    continue
                d = date(a, m, dia)
                estilo = "info" if d == actual else "warning" if d == hoy else "light-outline"
                ttk.Button(rejilla, text=str(dia), width=3, bootstyle=estilo,
                           command=lambda d=d: elegir(d)).grid(row=f, column=c, padx=1, pady=1)

    ttk.Button(cab, text="◀", width=3, bootstyle="secondary-outline", command=lambda: mover(-1)).pack(side="left")
    ttk.Button(cab, text="▶", width=3, bootstyle="secondary-outline", command=lambda: mover(+1)).pack(side="right")
    lbl.pack(side="left", fill="x", expand=True)

    pie = ttk.Frame(marco)
    pie.pack(fill="x", pady=(8, 0))
    ttk.Button(pie, text="Hoy", bootstyle="warning-outline", command=lambda: elegir(hoy)).pack(side="left")
    ttk.Button(pie, text="Cancelar", bootstyle="secondary", command=cerrar).pack(side="right")

    pintar()
    pop.bind("<Escape>", cerrar)
    pop.bind("<Prior>", lambda e: mover(-1))   # Re Pág: mes anterior
    pop.bind("<Next>", lambda e: mover(+1))    # Av Pág: mes siguiente
    pop.protocol("WM_DELETE_WINDOW", cerrar)
    pop.update_idletasks()
    x, y = ent.winfo_rootx(), ent.winfo_rooty() + ent.winfo_height() + 2
    x = max(0, min(x, pop.winfo_screenwidth() - pop.winfo_reqwidth()))
    if y + pop.winfo_reqheight() > pop.winfo_screenheight():
        y = max(0, ent.winfo_rooty() - pop.winfo_reqheight() - 2)
    pop.geometry(f"+{x}+{y}")
    pop.deiconify()
    pop.lift()
    pop.focus_force()
    try:
        pop.grab_set()
    except tk.TclError:
        pass
    return pop


# ── Hora ──────────────────────────────────────────────────────────────────
def campo_hora(parent, var, pady=(3, 12), paso_minutos=5):
    """Dos ruedas (horas : minutos) que escriben «HH:MM» en `var`. Se empaqueta sola.
    Las flechas de los minutos van de `paso_minutos` en `paso_minutos`, pero se puede escribir
    cualquier minuto. Devuelve el marco, con .horas y .minutos (los dos Spinbox)."""
    actual = normalizar_hora(var.get())
    h0, m0 = (actual.split(":") if re.fullmatch(r"\d\d:\d\d", actual) else ("09", "00"))
    v_h, v_m = tk.StringVar(value=h0), tk.StringVar(value=m0)

    frm = ttk.Frame(parent)
    frm.pack(fill="x", pady=pady)
    solo_num = (frm.register(lambda t: t == "" or (t.isdigit() and len(t) <= 2)), "%P")
    sp_h = ttk.Spinbox(frm, from_=0, to=23, increment=1, wrap=True, width=4, format="%02.0f",
                       textvariable=v_h, font=("Segoe UI", 11), justify="center",
                       validate="key", validatecommand=solo_num, bootstyle="info")
    sp_h.pack(side="left")
    ttk.Label(frm, text=" : ", font=("Segoe UI", 12, "bold")).pack(side="left")
    sp_m = ttk.Spinbox(frm, from_=0, to=59, increment=paso_minutos, wrap=True, width=4, format="%02.0f",
                       textvariable=v_m, font=("Segoe UI", 11), justify="center",
                       validate="key", validatecommand=solo_num, bootstyle="info")
    sp_m.pack(side="left")
    ttk.Label(frm, text="  (horas : minutos)", font=("Segoe UI", 8), foreground="gray").pack(side="left")

    def _a_var(*_):
        try:
            h, m = int(v_h.get() or 0), int(v_m.get() or 0)
        except ValueError:
            return
        if 0 <= h <= 23 and 0 <= m <= 59:
            var.set(f"{h:02d}:{m:02d}")
        else:
            var.set(f"{v_h.get()}:{v_m.get()}")   # el formulario avisará al guardar

    def _formatear(event=None):
        for v, tope in ((v_h, 23), (v_m, 59)):
            try:
                n = int(v.get() or 0)
            except ValueError:
                n = 0
            v.set(f"{max(0, min(tope, n)):02d}")

    def _rueda(sp, event):
        sp.event_generate("<<Increment>>" if (getattr(event, "delta", 0) > 0 or event.num == 4) else "<<Decrement>>")
        return "break"

    for sp in (sp_h, sp_m):
        sp.bind("<FocusOut>", _formatear, add="+")
        sp.bind("<MouseWheel>", lambda e, sp=sp: _rueda(sp, e))
        sp.bind("<Button-4>", lambda e, sp=sp: _rueda(sp, e))
        sp.bind("<Button-5>", lambda e, sp=sp: _rueda(sp, e))
    v_h.trace_add("write", _a_var)
    v_m.trace_add("write", _a_var)
    _a_var()
    frm.horas, frm.minutos = sp_h, sp_m
    return frm
