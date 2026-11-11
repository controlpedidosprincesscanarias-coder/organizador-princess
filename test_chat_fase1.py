"""Chat y notas de versión (v4.18.44): notas de cada versión, miniaturas, «Guardar como…», historial de
la burbuja y QR de descarga directa.

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_chat_fase1.py  (en Windows o en cualquier sistema: si no hay Tkinter, se simula).
No se conecta a ningún servidor: las descargas se simulan.
"""
import importlib.abc
import importlib.machinery
import os
import sys
import tempfile
from io import BytesIO
from unittest import mock

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(RAIZ, "app"))

try:
    import tkinter  # noqa: F401
except ImportError:
    class _Simulado(importlib.abc.MetaPathFinder, importlib.abc.Loader):
        def find_spec(self, name, path, target=None):
            if name.split(".")[0] in ("tkinter", "_tkinter", "ttkbootstrap"):
                return importlib.machinery.ModuleSpec(name, self, is_package=True)
        def create_module(self, spec):
            m = mock.MagicMock()
            m.__path__, m.__name__, m.__spec__ = [], spec.name, spec
            return m
        def exec_module(self, m):
            pass
    sys.meta_path.insert(0, _Simulado())

from PIL import Image  # noqa: E402

from ui import notas_version, miniaturas  # noqa: E402
import services.chat_client as cc  # noqa: E402

fallos = []


def ok(nombre, cond, det=""):
    print(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
    if not cond:
        fallos.append(nombre)


# ── 1. Notas de una versión ──────────────────────────────────────────────────
NOTAS = """# ✨ Organizador Princess v4.18.44

## Chat
- Miniaturas.

---

# ✨ Organizador Princess v4.18.4

- Algo antiguo.

---
"""
n = notas_version.notas_de("v4.18.44", NOTAS)
ok("notas de la versión pedida, sin la siguiente ni el separador final",
   n is not None and n.startswith("# ✨ Organizador Princess v4.18.44") and "Algo antiguo" not in n
   and not n.rstrip().endswith("---"), n)
ok("los números se comparan como números («v4.18.04» = «4.18.4»)",
   "Algo antiguo" in (notas_version.notas_de("4.18.04", NOTAS) or ""))
ok("una versión que no está → None", notas_version.notas_de("v9.9.9", NOTAS) is None)
ok("sin número → None", notas_version.notas_de("", NOTAS) is None)
real = notas_version.leer_notas(os.path.join(RAIZ, "release_notes", "release_notes.md"))
sys.path.insert(0, RAIZ)
version_actual = next(l.split('"')[1] for l in open(os.path.join(RAIZ, "main_agenda.py"), encoding="utf-8")
                      if l.startswith("APP_VERSION"))
ok(f"release_notes.md tiene las notas de la versión actual ({version_actual})",
   notas_version.notas_de(version_actual, real) is not None)
ok("desde el código, ruta_notas() encuentra release_notes.md", bool(notas_version.ruta_notas()))

# ── 2. Imágenes del chat ─────────────────────────────────────────────────────
ok("tipo «imagen» → miniatura", miniaturas.es_imagen({"tipo": "imagen", "adjunto": {"url": "u", "nombre_archivo": "x"}}))
ok("extensión .JPG → miniatura", miniaturas.es_imagen({"tipo": "archivo", "adjunto": {"url": "u", "nombre_archivo": "F.JPG"}}))
ok("mime image/png → miniatura", miniaturas.es_imagen({"adjunto": {"url": "u", "nombre_archivo": "a", "mime_type": "image/png"}}))
ok("un PDF no", not miniaturas.es_imagen({"tipo": "archivo", "adjunto": {"url": "u", "nombre_archivo": "f.pdf"}}))
ok("un mensaje de texto no", not miniaturas.es_imagen({"contenido": "hola"}))
buf = BytesIO()
Image.new("RGB", (1200, 900), "red").save(buf, format="JPEG")
img = miniaturas.reducir(buf.getvalue())
ok("la miniatura cabe en 240×180 y guarda la proporción", img.size == (240, 180), img.size)
buf = BytesIO()
Image.new("RGB", (60, 40), "blue").save(buf, format="PNG")
ok("una imagen pequeña no se agranda", miniaturas.reducir(buf.getvalue()).size == (60, 40))

# ── 3. Descargas: solo del almacén de adjuntos ───────────────────────────────
try:
    cc.ChatClient.descargar_bytes("https://malicioso.example.com/x.png")
    ok("descargar_bytes rechaza una dirección de fuera", False)
except ValueError:
    ok("descargar_bytes rechaza una dirección de fuera", True)


class _Resp:
    headers = {"Content-Length": "5"}
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def raise_for_status(self): pass
    def iter_content(self, n): yield b"hola!"


with mock.patch.object(cc.requests, "get", return_value=_Resp()) as g:
    destino = os.path.join(tempfile.mkdtemp(), "copia.txt")
    yo = mock.MagicMock(descargar_bytes=cc.ChatClient.descargar_bytes)
    cc.ChatClient.guardar_adjunto_como(yo, "https://abc.supabase.co/f.txt", destino)
    ok("«Guardar como…» guarda el adjunto donde se ha elegido", open(destino, "rb").read() == b"hola!")
    ok("…sin seguir redirecciones", g.call_args.kwargs.get("allow_redirects") is False, g.call_args)

# ── 4. La burbuja carga el historial completo (antes, los 3 últimos de hoy) ──
popup = open(os.path.join(RAIZ, "app", "ui", "chat_popup.py"), encoding="utf-8").read()
ok("la burbuja ya no recorta el historial a 3 mensajes", ")[-3:]" not in popup and "_es_de_hoy" not in popup)

# ── 5. QR de descarga directa ────────────────────────────────────────────────
from ui import chat_movil  # noqa: E402
ok("el QR descarga la .apk directamente (nombre fijo)",
   chat_movil.URL_DESCARGA.endswith("/releases/latest/download/ChatPrincess.apk"), chat_movil.URL_DESCARGA)
try:
    from pyzbar.pyzbar import decode  # noqa: E402
    leido = decode(Image.open(os.path.join(RAIZ, "app", "ui", "qr_chat_movil.png")))[0].data.decode()
    ok("la imagen del QR lleva ese mismo enlace", leido == chat_movil.URL_DESCARGA, leido)
except Exception as e:  # noqa: BLE001  (pyzbar no viene en la compilación: se omite)
    print(f"(se omite la lectura del QR: {e})")

print(f"\n{'Todas las comprobaciones OK.' if not fallos else str(len(fallos)) + ' fallo(s)'}")
sys.exit(1 if fallos else 0)
