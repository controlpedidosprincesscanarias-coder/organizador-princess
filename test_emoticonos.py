"""Emoticonos en color del chat (v4.18.22): imágenes del panel y trozos de los mensajes.

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_emoticonos.py  (en Windows o en cualquier sistema: si no hay Tkinter, se simula).
"""
import importlib.abc
import importlib.machinery
import os
import sys
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

from ui.emoticonos import EMOTICONOS, RESPUESTAS, conocidos, nombre_imagen, _CARPETA_COLOR  # noqa: E402
from ui.chat_bubbles import _trocear  # noqa: E402

fallos = []
def ok(nombre, cond, det=""):
    print(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
    if not cond:
        fallos.append(nombre)

faltan = [nombre_imagen(e, s) for e in conocidos() for s in ("", "_p")
          if not os.path.exists(os.path.join(_CARPETA_COLOR, nombre_imagen(e, s)))]
ok("cada emoticono del panel y de las respuestas rápidas tiene su imagen en color (2 tamaños)", not faltan, faltan)
ok("32 emoticonos y 8 respuestas rápidas", len(EMOTICONOS) == 32 and len(RESPUESTAS) == 8)
ok("nombre de imagen: códigos Unicode sin el selector de variante", nombre_imagen("❤️") == "2764.png" and nombre_imagen("👍", "_p") == "1f44d_p.png")

c = conocidos()
ok("mensaje con emoticonos: texto e imágenes en orden",
   _trocear("Vale 👍 gracias 🙏", c) == [("t", "Vale "), ("e", "👍"), ("t", " gracias "), ("e", "🙏")], _trocear("Vale 👍 gracias 🙏", c))
ok("el ❤️ del móvil (con selector de variante) también va en color", _trocear("❤️", c) == [("e", "❤")], _trocear("❤️", c))
ok("emoticonos que no están en el panel se quedan como texto", _trocear("🦄 hola", c) == [("t", "🦄 hola")], _trocear("🦄 hola", c))
ok("texto sin emoticonos, igual", _trocear("Sin nada", c) == [("t", "Sin nada")])
ok("emoticonos seguidos", _trocear("👍👍", c) == [("e", "👍"), ("e", "👍")])

print(f"\n{'Todas las comprobaciones OK.' if not fallos else str(len(fallos)) + ' fallo(s)'}")
sys.exit(1 if fallos else 0)
