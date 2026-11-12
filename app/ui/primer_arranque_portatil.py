"""
app/ui/primer_arranque_portatil.py  ·  v4.18.54
Primer arranque de la copia portátil: en qué carpeta guardarla, arranque al iniciar sesión y escritorio.

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Petición de Víctor (12 nov 2026): la primera vez, preguntar en qué carpeta guardarlo (así el acceso directo
y las actualizaciones van siempre a esa carpeta) y poner un acceso directo en la carpeta de Inicio de
Windows para que arranque solo al iniciar sesión. La lógica, sin tkinter, está en services/portatil.py.

- Primera vez: se elige la carpeta (por defecto Documentos\\Organizador Princess), el Organizador se copia
  allí, se crean los accesos directos y se vuelve a abrir desde esa carpeta.
- Si se abre otra copia (p. ej. la que quedó en Descargas) y la guardada existe: «Ya tienes el Organizador
  en …» → abrir esa (recomendado) o usar esta a partir de ahora.
- Solo en la copia portátil: la instalada no pasa por aquí.
"""
import os
import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk

from services import portatil as P
from ui.assets import _apply_icon


def _aplicar_accesos(exe, arranque, escritorio):
    """Crea los accesos pedidos y devuelve (estado de arranque, escritorio creado)."""
    modo = P.preparar_arranque_con_windows(exe) if arranque else None
    hecho_esc = P.crear_acceso_directo(exe, "Desktop") if escritorio else False
    P.registrar_enlace_usuario(exe)
    return modo, hecho_esc


def _cambiar_de_copia(app, exe_nuevo, salir):
    """Abre la copia de `exe_nuevo` y cierra esta."""
    try:
        P.lanzar(exe_nuevo)
    except Exception as e:  # noqa: BLE001
        messagebox.showerror("Organizador Princess", f"No se pudo abrir «{exe_nuevo}»:\n{e}", parent=app)
        return False
    app.after(500, salir)
    return True


def comprobar(app, ruta_estado, salir=lambda: os._exit(0)):
    """Llamar al arrancar (con la ventana principal ya creada). Solo hace algo en la copia portátil."""
    if not P.es_portatil():
        return
    exe = P.ruta_exe()
    estado = P.leer_estado(ruta_estado)
    accion = P.que_hacer_al_arrancar(estado, exe)
    if accion == "ok":
        return
    if accion == "otra_copia":
        guardada = estado["ruta_exe"]
        abrir_esa = messagebox.askyesno(
            "Organizador Princess",
            f"Ya tienes el Organizador guardado en:\n\n{os.path.dirname(guardada)}\n\n"
            "Es el que arranca con Windows y el que se actualiza solo.\n\n"
            "¿Abrir ese? (Recomendado. Si pulsas «No», se usará esta copia a partir de ahora.)",
            parent=app)
        if abrir_esa:
            _cambiar_de_copia(app, guardada, salir)
            return
        modo, esc = _aplicar_accesos(exe, bool(estado.get("arranque")), bool(estado.get("escritorio")))
        P.guardar_estado(ruta_estado, {"ruta_exe": exe, "arranque": modo, "escritorio": esc})
        return
    _ventana_primera_vez(app, exe, ruta_estado, salir)


def _ventana_primera_vez(app, exe, ruta_estado, salir):
    win = ttk.Toplevel(app)
    win.title("Organizador Princess — primera vez")
    win.resizable(False, False)
    _apply_icon(win)
    win.transient(app)
    win.attributes("-topmost", True)

    cuerpo = ttk.Frame(win, padding=(20, 16, 20, 12))
    cuerpo.pack(fill="both", expand=True)
    ttk.Label(cuerpo, text="💼  Organizador Princess sin instalar", font=("Segoe UI", 13, "bold")).pack(anchor="w")
    ttk.Label(cuerpo, text="Elige la carpeta donde guardarlo. Desde ahí arrancará con Windows y ahí se\n"
                           "actualizará solo. Tu agenda y tu configuración no cambian de sitio.",
              font=("Segoe UI", 9), foreground="#adb5bd", justify="left").pack(anchor="w", pady=(4, 12))

    actual = os.path.dirname(exe)
    var_carpeta = tk.StringVar(value=P.carpeta_por_defecto())
    fila = ttk.Frame(cuerpo)
    fila.pack(fill="x")
    ttk.Entry(fila, textvariable=var_carpeta, width=58).pack(side="left", fill="x", expand=True)

    def _elegir():
        r = filedialog.askdirectory(parent=win, title="Carpeta para el Organizador",
                                    initialdir=var_carpeta.get() if os.path.isdir(var_carpeta.get()) else actual)
        if r:
            var_carpeta.set(os.path.normpath(r))
    ttk.Button(fila, text="Cambiar…", bootstyle="secondary", command=_elegir).pack(side="left", padx=(8, 0))
    ttk.Button(cuerpo, text="Dejarlo donde está ahora", bootstyle="link",
               command=lambda: var_carpeta.set(actual)).pack(anchor="w", pady=(4, 8))

    var_arranque = tk.BooleanVar(value=True)
    var_escritorio = tk.BooleanVar(value=True)
    ttk.Checkbutton(cuerpo, text="Arrancar el Organizador al iniciar sesión en Windows",
                    variable=var_arranque).pack(anchor="w", pady=2)
    ttk.Checkbutton(cuerpo, text="Acceso directo en el escritorio", variable=var_escritorio).pack(anchor="w", pady=2)
    var_err = tk.StringVar()
    ttk.Label(cuerpo, textvariable=var_err, foreground="#e74c3c", font=("Segoe UI", 9, "bold"),
              wraplength=520, justify="left").pack(anchor="w", pady=(8, 0))

    botones = ttk.Frame(cuerpo)
    botones.pack(fill="x", pady=(12, 0))

    def _aceptar():
        carpeta = var_carpeta.get().strip()
        if not carpeta:
            var_err.set("Escribe o elige una carpeta.")
            return
        try:
            destino = P.copiar_a_carpeta(carpeta, exe)
        except RuntimeError as e:
            var_err.set(f"{e}\nElige otra carpeta (por ejemplo, dentro de Documentos).")
            return
        modo, esc = _aplicar_accesos(destino, var_arranque.get(), var_escritorio.get())
        P.guardar_estado(ruta_estado, {"ruta_exe": destino, "arranque": modo, "escritorio": esc})
        avisos = []
        if var_arranque.get() and not modo:
            avisos.append("No se pudo preparar el arranque con Windows en este equipo.")
        if var_escritorio.get() and not esc:
            avisos.append("No se pudo crear el acceso directo del escritorio.")
        win.destroy()
        if avisos:
            messagebox.showwarning("Organizador Princess", "\n".join(avisos), parent=app)
        if destino != exe:
            messagebox.showinfo("Organizador Princess",
                                f"El Organizador se ha guardado en:\n\n{os.path.dirname(destino)}\n\n"
                                "Ahora se abrirá desde ahí. La copia de la carpeta actual ya no hace falta: "
                                "puedes borrarla cuando quieras.", parent=app)
            _cambiar_de_copia(app, destino, salir)

    def _ahora_no():
        # Sin guardar nada: se volverá a preguntar la próxima vez que se abra.
        win.destroy()

    ttk.Button(botones, text="✅  Guardar aquí", bootstyle="success", command=_aceptar).pack(side="left")
    ttk.Button(botones, text="Ahora no", bootstyle="secondary", command=_ahora_no).pack(side="left", padx=(8, 0))

    win.update_idletasks()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    win.geometry(f"+{(win.winfo_screenwidth() - w) // 2}+{max(40, (win.winfo_screenheight() - h) // 2)}")
    win.lift()
    win.focus_force()
