"""
utils/marca_internet.py — «marca de Internet» (Mark of the Web) en los archivos que descarga el chat (v4.18.80).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Petición de Víctor (25 nov 2026): «Con el chat del organizador de escritorio, ¿hay que realizar algún arreglo de
seguridad?». Los navegadores marcan lo que descargan con un flujo NTFS oculto `Zone.Identifier` (ZoneId=3, zona
Internet). Con esa marca, Windows avisa antes de abrir un programa, Word/Excel/PowerPoint abren el documento en
«Vista protegida» y bloquean sus macros, y el lector de PDF lo abre en modo protegido. Los adjuntos que guardaba el
chat no la llevaban: un .doc o .xls con macros enviado por el chat se abría como un archivo de confianza del PC.

Sin tkinter. Fuera de Windows (o en un disco sin NTFS, como un USB en FAT) no hace nada. Pruebas en
test_chat_fase7.py.
"""
import logging
import sys
import urllib.parse

log = logging.getLogger("chat")

ZONA_INTERNET = 3


def contenido(url: str = "") -> str:
    """Texto del flujo Zone.Identifier, como el que escriben los navegadores (sin usuario ni datos de la URL)."""
    lineas = ["[ZoneTransfer]", f"ZoneId={ZONA_INTERNET}"]
    try:
        u = urllib.parse.urlparse(str(url or ""))
        if u.scheme in ("http", "https") and u.hostname:
            lineas.append(f"HostUrl={u.scheme}://{u.hostname}/")
    except Exception:  # noqa: BLE001
        pass
    return "\r\n".join(lineas) + "\r\n"


def marcar(ruta: str, url: str = "", es_windows: bool = None) -> bool:
    """Pone la marca de Internet a `ruta`. Devuelve True si la ha puesto. Nunca lanza: si no se puede (otro
    sistema, disco sin NTFS), el archivo queda igual que antes."""
    if es_windows is None:
        es_windows = sys.platform.startswith("win")
    if not es_windows or not ruta:
        return False
    try:
        with open(ruta + ":Zone.Identifier", "w", encoding="ascii", newline="") as f:
            f.write(contenido(url))
        return True
    except OSError as e:
        log.info("No se pudo poner la marca de Internet a %s: %s", ruta, e)
        return False
