"""
services/reinicio_limpio.py — «Borrado completo y reinicio limpio» del Organizador (v4.18.62).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Petición de Víctor (13 nov 2026): desde esta versión, desinstalar ya no borra los datos (configuración, agenda,
«Mi Usuario»…: carpeta %APPDATA%\\OrganizadorPrincess), para que una reinstalación los conserve. Para empezar de
cero sin buscar carpetas a mano, Administración tiene un botón que lo borra todo y reinicia el Organizador.

Con el programa abierto, Windows no deja borrar los archivos que están en uso. Por eso:
1. `programar()` deja una marca en la carpeta de datos; la app se vuelve a abrir (`orden_relanzar`) y se cierra.
2. La copia nueva cierra la antigua (utils/instancia_unica.py) y, ANTES de cargar la configuración o la agenda,
   `aplicar()` borra todo el contenido de la carpeta, salvo lo de CONSERVAR (reintentando unos segundos los
   archivos que la copia antigua aún no haya soltado).

Se conserva `portatil.json`: no es un dato del usuario, sino dónde está instalada la copia portátil; sin él, la
copia portátil volvería a preguntar la carpeta y a copiarse. Sin tkinter: se prueba en test_reinicio_limpio.py.
"""
import os
import shutil
import sys
import time
from datetime import datetime

MARCA = ".reinicio_limpio_pendiente"
CONSERVAR = frozenset({"portatil.json", MARCA})


def carpeta_datos():
    """%APPDATA%\\OrganizadorPrincess (la misma que db/sqlite.get_config_path, sin crearla)."""
    return os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "OrganizadorPrincess")


def programar(carpeta=None):
    """Deja la marca para que el próximo arranque lo borre todo."""
    carpeta = carpeta or carpeta_datos()
    os.makedirs(carpeta, exist_ok=True)
    with open(os.path.join(carpeta, MARCA), "w", encoding="utf-8") as f:
        f.write(datetime.now().isoformat(timespec="seconds"))


def hay_pendiente(carpeta=None):
    return os.path.isfile(os.path.join(carpeta or carpeta_datos(), MARCA))


def _borrar(ruta):
    if os.path.isdir(ruta) and not os.path.islink(ruta):
        shutil.rmtree(ruta)
    else:
        os.remove(ruta)


def aplicar(carpeta=None, intentos=15, espera=0.3, dormir=time.sleep):
    """Borra el contenido de la carpeta de datos (salvo CONSERVAR) y quita la marca.

    Devuelve (borrados, no_borrados): nombres. Lo que no se pueda borrar tras los reintentos (por ejemplo, un
    registro que esta misma copia ya tiene abierto) se deja y se informa."""
    carpeta = carpeta or carpeta_datos()
    if not os.path.isdir(carpeta):
        return [], []
    pendientes = [n for n in sorted(os.listdir(carpeta)) if n not in CONSERVAR]
    borrados = []
    for _ in range(max(1, intentos)):
        siguen = []
        for nombre in pendientes:
            try:
                _borrar(os.path.join(carpeta, nombre))
                borrados.append(nombre)
            except FileNotFoundError:
                borrados.append(nombre)
            except OSError:
                siguen.append(nombre)
        pendientes = siguen
        if not pendientes:
            break
        dormir(espera)
    try:
        os.remove(os.path.join(carpeta, MARCA))
    except OSError:
        pass
    return borrados, pendientes


def orden_relanzar(frozen=None, ejecutable=None, script=None):
    """Orden para volver a abrir el Organizador: el .exe (instalado o portátil) o, desde el código,
    python main_agenda.py."""
    frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    ejecutable = ejecutable or sys.executable
    if frozen:
        return [ejecutable]
    script = script or os.path.abspath(sys.argv[0])
    return [ejecutable, script]
