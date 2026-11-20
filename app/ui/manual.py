"""
ui/manual.py — ventana «📖 Manual de uso» del botón Manual del menú principal (v4.18.76).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Petición de Víctor (20 nov 2026): que funcione como el manual del chat del móvil. Buscador arriba, apartados que se
abren y se cierran con un clic (con una búsqueda escrita, los encontrados salen abiertos) y, abajo, el manual
completo en PDF: «Abrir» (con el lector de PDF del equipo) y «Guardar una copia…» (donde se elija).
El contenido y la búsqueda están en utils/manual_consulta.py; dónde está el PDF lo dice `buscar_pdf()`, que le
pasa main_agenda.py (junto al programa, junto al script o dentro del .exe en la portátil).
"""
import os
import shutil
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk

from utils import manual_consulta as mc

NOMBRE_PDF = "Manual_Usuario_OrganizadorPrincess.pdf"

_FONDO = "#1b2635"
_CAJA = "#24344a"
_TEXTO = "#e8edf3"
_META = "#8a97a8"
_DORADO = "#C9A84C"

_VENTANA = {"win": None}


def _abrir_archivo(ruta):
    if sys.platform.startswith("win"):
        os.startfile(os.path.normpath(ruta))          # noqa: S606 — el PDF del propio Organizador
    else:
        subprocess.Popen(["xdg-open", ruta])


def abrir(ctx, buscar_pdf):
    """Abre (o trae al frente) la ventana del manual. `buscar_pdf()` → ruta del PDF completo o None."""
    if _VENTANA["win"] is not None and _VENTANA["win"].winfo_exists():
        _VENTANA["win"].deiconify()
        _VENTANA["win"].lift()
        return _VENTANA["win"]
    win = ttk.Toplevel(ctx.app)
    _VENTANA["win"] = win
    win.title("Manual de uso")
    ctx.apply_icon(win)
    win.configure(bg=_FONDO)
    win.minsize(560, 480)

    cab = tk.Frame(win, bg=_FONDO)
    cab.pack(fill="x", padx=18, pady=(14, 6))
    tk.Label(cab, text="📖  Manual de uso", bg=_FONDO, fg=_TEXTO, font=("Segoe UI", 14, "bold")).pack(anchor="w")
    tk.Label(cab, text="Escribe lo que buscas (por ejemplo «sonido», «vacaciones» o «portátil») o pulsa un apartado "
                       "para abrirlo.", bg=_FONDO, fg=_META, font=("Segoe UI", 9), wraplength=600,
             justify="left").pack(anchor="w", pady=(2, 8))

    fila_busca = tk.Frame(cab, bg=_FONDO)
    fila_busca.pack(fill="x")
    tk.Label(fila_busca, text="🔍", bg=_FONDO, fg=_META, font=("Segoe UI", 11)).pack(side="left", padx=(0, 6))
    var = tk.StringVar()
    entrada = ttk.Entry(fila_busca, textvariable=var, font=("Segoe UI", 10))
    entrada.pack(side="left", fill="x", expand=True)
    ttk.Button(fila_busca, text="✕", width=3, bootstyle="secondary-outline",
               command=lambda: (var.set(""), entrada.focus_set())).pack(side="left", padx=(6, 0))

    # Pie: manual completo
    pie = tk.Frame(win, bg=_FONDO)
    pie.pack(side="bottom", fill="x", padx=18, pady=(6, 14))
    tk.Label(pie, text="Manual completo en PDF, con todas las pantallas y capturas:", bg=_FONDO, fg=_META,
             font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 6))
    botones = tk.Frame(pie, bg=_FONDO)
    botones.pack(fill="x")

    def _no_hay():
        messagebox.showwarning(
            "Manual no encontrado",
            f"No se ha encontrado el archivo {NOMBRE_PDF}.\n\nEl manual se instala junto con la aplicación: si "
            "acabas de actualizar, vuelve a ejecutar el instalador o contacta con el Dpto. Central de Compras.",
            parent=win)

    def _abrir_pdf():
        ruta = buscar_pdf()
        if not ruta:
            return _no_hay()
        try:
            _abrir_archivo(ruta)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Error al abrir el manual",
                                 f"No se pudo abrir el manual:\n\n{ruta}\n\nDetalle: {e}\n\n"
                                 "Comprueba que tienes un lector de PDF (por ejemplo Edge o Adobe Reader).",
                                 parent=win)

    def _guardar_pdf():
        ruta = buscar_pdf()
        if not ruta:
            return _no_hay()
        destino = filedialog.asksaveasfilename(
            parent=win, title="Guardar el manual completo", initialfile=NOMBRE_PDF,
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not destino:
            return
        try:
            shutil.copyfile(ruta, destino)
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Guardar el manual", f"No se pudo guardar:\n\n{e}", parent=win)
            return
        if messagebox.askyesno("Guardar el manual", f"Manual guardado en:\n\n{destino}\n\n¿Abrirlo ahora?", parent=win):
            try:
                _abrir_archivo(destino)
            except Exception:  # noqa: BLE001
                pass

    ttk.Button(botones, text="📄  Abrir el manual completo", bootstyle="info", command=_abrir_pdf).pack(side="left")
    ttk.Button(botones, text="💾  Guardar una copia…", bootstyle="info-outline",
               command=_guardar_pdf).pack(side="left", padx=(8, 0))
    ttk.Button(botones, text="  Cerrar  ", bootstyle="secondary", command=win.destroy).pack(side="right")
    tk.Frame(win, bg="#2f4258", height=1).pack(side="bottom", fill="x", padx=18)

    # Lista de apartados con desplazamiento
    zona = tk.Frame(win, bg=_FONDO)
    zona.pack(fill="both", expand=True, padx=(18, 6), pady=(4, 6))
    lienzo = tk.Canvas(zona, bg=_FONDO, highlightthickness=0, bd=0)
    barra = ttk.Scrollbar(zona, orient="vertical", command=lienzo.yview)
    lienzo.configure(yscrollcommand=barra.set)
    barra.pack(side="right", fill="y")
    lienzo.pack(side="left", fill="both", expand=True)
    interior = tk.Frame(lienzo, bg=_FONDO)
    id_int = lienzo.create_window((0, 0), window=interior, anchor="nw")
    interior.bind("<Configure>", lambda _e: lienzo.configure(scrollregion=lienzo.bbox("all")))

    ancho = {"px": 600}

    def _al_redimensionar(e):
        lienzo.itemconfigure(id_int, width=e.width)
        if abs(e.width - ancho["px"]) > 20:
            ancho["px"] = e.width
            _pintar()
    lienzo.bind("<Configure>", _al_redimensionar)

    def _rueda(e):
        if lienzo.winfo_exists():
            lienzo.yview_scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1), "units")
    win.bind("<MouseWheel>", _rueda)
    win.bind("<Button-4>", lambda _e: lienzo.yview_scroll(-1, "units"))
    win.bind("<Button-5>", lambda _e: lienzo.yview_scroll(1, "units"))

    abiertos = {}     # título → True/False elegido a mano (si no, abierto solo con búsqueda)

    def _pintar(*_):
        if not win.winfo_exists():
            return
        for w in interior.winfo_children():
            w.destroy()
        consulta = var.get()
        encontrados = mc.buscar(consulta)
        envolver = max(300, ancho["px"] - 80)
        if not encontrados:
            tk.Label(interior, text=f"No hay nada sobre «{consulta}». Prueba con otra palabra o abre el manual "
                                    "completo.", bg=_FONDO, fg=_META, font=("Segoe UI", 10),
                     wraplength=envolver, justify="left").pack(anchor="w", pady=8)
        for icono, titulo, lineas in encontrados:
            abierto = abiertos.get(titulo, bool(consulta.strip()))
            caja = tk.Frame(interior, bg=_CAJA, cursor="hand2")
            caja.pack(fill="x", pady=4, padx=(0, 6))
            fila = tk.Frame(caja, bg=_CAJA)
            fila.pack(fill="x", padx=12, pady=10)
            partes = [caja, fila,
                      tk.Label(fila, text=icono, bg=_CAJA, fg=_TEXTO, font=("Segoe UI Emoji", 13)),
                      tk.Label(fila, text=titulo, bg=_CAJA, fg=_TEXTO, font=("Segoe UI", 11, "bold"), anchor="w"),
                      tk.Label(fila, text="▴" if abierto else "▾", bg=_CAJA, fg=_META, font=("Segoe UI", 12))]
            partes[2].pack(side="left")
            partes[3].pack(side="left", padx=(10, 0), fill="x", expand=True)
            partes[4].pack(side="right")
            if abierto:
                cuerpo = tk.Frame(caja, bg=_CAJA)
                cuerpo.pack(fill="x", padx=(40, 14), pady=(0, 12))
                partes.append(cuerpo)
                for linea in lineas:
                    f = tk.Frame(cuerpo, bg=_CAJA)
                    f.pack(fill="x", pady=2)
                    b = tk.Label(f, text="•", bg=_CAJA, fg=_DORADO, font=("Segoe UI", 10, "bold"))
                    b.pack(side="left", anchor="n", padx=(0, 8))
                    t = tk.Label(f, text=linea, bg=_CAJA, fg=_TEXTO, font=("Segoe UI", 10),
                                 wraplength=envolver - 40, justify="left", anchor="w")
                    t.pack(side="left", fill="x", expand=True)
                    partes += [f, b, t]

            def _alternar(_e=None, tit=titulo, ab=abierto):
                abiertos[tit] = not ab
                _pintar()
            for w in partes:
                w.bind("<Button-1>", _alternar)
        lienzo.yview_moveto(0)

    var.trace_add("write", lambda *_: (abiertos.clear(), _pintar()))
    _pintar()

    win.update_idletasks()
    w, h = 680, 640
    x = max(0, (win.winfo_screenwidth() - w) // 2)
    y = max(0, (win.winfo_screenheight() - h) // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")
    entrada.focus_set()
    return win
