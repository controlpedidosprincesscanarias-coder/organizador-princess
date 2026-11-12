"""ui/notas_version.py — notas de la versión al pulsar el número de versión (v4.18.44).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Petición de Víctor: «si se pulsa sobre la versión en cualquiera de las ventanas del Organizador, que se
vean las notas de actualización de esa versión». El número de versión del pie del menú principal, de
Administración y de Configuración se puede pulsar y abre una ventana con las notas de la versión
instalada, con formato, y un botón para ver las de todas las versiones.

Las notas salen de release_notes/release_notes.md, que el instalador copia junto al programa
(«{app}\\release_notes\\», ver el .iss), así que funcionan sin Internet. notas_de() y ruta_notas()
no dependen de Tkinter (se prueban en test_notas_version.py).
"""
import os
import re
import sys

URL_RELEASES = "https://github.com/controlpedidosprincesscanarias-coder/organizador-princess/releases"
_RE_CABECERA = re.compile(r"^# .*?v?(\d+(?:\.\d+)+)\s*$")


def _numeros(version):
    return tuple(int(n) for n in re.findall(r"\d+", str(version or "")))


def ruta_notas():
    """release_notes.md instalado junto al .exe o, desde el código, el del repositorio."""
    candidatos = []
    if getattr(sys, "frozen", False):
        candidatos.append(os.path.join(os.path.dirname(sys.executable), "release_notes", "release_notes.md"))
        # (v4.18.54) La copia portátil las lleva dentro del .exe (main.spec, carpeta «documentos»)
        if getattr(sys, "_MEIPASS", None):
            candidatos.append(os.path.join(sys._MEIPASS, "documentos", "release_notes", "release_notes.md"))
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    candidatos.append(os.path.join(raiz, "release_notes", "release_notes.md"))
    return next((c for c in candidatos if os.path.isfile(c)), None)


def leer_notas(ruta=None):
    ruta = ruta or ruta_notas()
    if not ruta:
        return ""
    try:
        with open(ruta, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def notas_de(version, texto):
    """El apartado de `version` dentro de release_notes.md (desde su «# … vX.Y.Z» hasta el siguiente
    «# »), sin el separador final. Compara los números («v4.18.4» = «4.18.04»). None si no está."""
    buscada = _numeros(version)
    if not buscada:
        return None
    lineas = (texto or "").splitlines()
    inicio = None
    for i, linea in enumerate(lineas):
        m = _RE_CABECERA.match(linea)
        if not m:
            continue
        if inicio is not None:
            fin = i
            break
        if _numeros(m.group(1)) == buscada:
            inicio = i
    else:
        fin = len(lineas)
    if inicio is None:
        return None
    apartado = "\n".join(lineas[inicio:fin]).rstrip()
    apartado = re.sub(r"\n\s*-{3,}\s*$", "", apartado).rstrip()
    return apartado


def abrir(parent, version, todas=False):
    """Ventana con las notas de `version` (o de todas las versiones)."""
    import tkinter as tk
    import webbrowser
    import ttkbootstrap as ttk

    texto = leer_notas()
    contenido = texto if todas else notas_de(version, texto)
    win = ttk.Toplevel(parent)
    win.title("Notas de todas las versiones" if todas else f"Novedades de la versión {version}")
    win.geometry("620x520")
    win.transient(parent)

    marco = ttk.Frame(win, padding=10)
    marco.pack(fill="both", expand=True)
    barra = ttk.Scrollbar(marco, orient="vertical")
    txt = tk.Text(marco, font=("Segoe UI", 9), wrap="word", relief="flat", background="#1e1e2e",
                  foreground="#D8E8F0", padx=10, pady=8, yscrollcommand=barra.set)
    barra.configure(command=txt.yview)
    barra.pack(side="right", fill="y")
    txt.pack(side="left", fill="both", expand=True)
    if contenido:
        try:
            from ui.markdown_texto import pintar
            pintar(txt, contenido)
        except Exception:  # noqa: BLE001
            txt.insert("1.0", contenido)
    else:
        txt.insert("1.0", f"No se han encontrado en este equipo las notas de la versión {version}.\n\n"
                          "Puedes verlas en la página de versiones del Organizador (botón de abajo).")
    txt.configure(state="disabled")

    pie = ttk.Frame(win, padding=(10, 0, 10, 10))
    pie.pack(fill="x")
    ttk.Button(pie, text="Cerrar", bootstyle="secondary", command=win.destroy).pack(side="right")
    ttk.Button(pie, text="🌐  Ver en GitHub", bootstyle="info-outline",
               command=lambda: webbrowser.open(URL_RELEASES)).pack(side="right", padx=(0, 6))
    if not todas:
        ttk.Button(pie, text="📜  Todas las versiones", bootstyle="info-outline",
                   command=lambda: abrir(parent, version, todas=True)).pack(side="left")
    win.after(10, win.lift)
    return win


def hacer_pulsable(etiqueta, parent, version):
    """Convierte la etiqueta con el número de versión en un enlace a sus notas."""
    try:
        etiqueta.configure(cursor="hand2")
    except Exception:  # noqa: BLE001
        pass
    etiqueta.bind("<Button-1>", lambda e: abrir(parent, version))
