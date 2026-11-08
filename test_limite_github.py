"""Límite de consultas de GitHub en la comprobación de actualizaciones (v4.18.06).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_limite_github.py  (en Windows o en cualquier sistema: si no hay Tkinter, se simula).
"""
import importlib.abc
import importlib.machinery
import os
import sys
from unittest import mock

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(RAIZ, "app"))
sys.path.insert(0, RAIZ)

try:
    import tkinter  # noqa: F401
    import ttkbootstrap  # noqa: F401
except ImportError:
    class _Simulado(importlib.abc.MetaPathFinder, importlib.abc.Loader):
        def find_spec(self, name, path, target=None):
            if name.split(".")[0] in ("tkinter", "_tkinter", "ttkbootstrap") or name in ("PIL.ImageTk", "winsound"):
                return importlib.machinery.ModuleSpec(name, self, is_package=True)
        def create_module(self, spec):
            m = mock.MagicMock()
            m.__path__, m.__name__, m.__spec__ = [], spec.name, spec
            return m
        def exec_module(self, m):
            pass
    sys.meta_path.insert(0, _Simulado())

from services.update_service import _espera_por_limite_github as espera, _ESPERA_LIMITE_MAX_S  # noqa: E402

fallos = []
def ok(nombre, cond):
    print(("OK    " if cond else "FALLO ") + nombre)
    if not cond:
        fallos.append(nombre)

AHORA = 1_000_000
ok("403 por límite (Remaining 0) espera hasta el Reset + margen",
   espera(403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(AHORA + 600)}, AHORA, 30) == 630)
ok("cabeceras en cualquier mayúscula/minúscula",
   espera(403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": str(AHORA + 600)}, AHORA, 0) == 600)
ok("429 con Retry-After",
   espera(429, {"Retry-After": "120"}, AHORA, 0) == 120)
ok("403 con Retry-After (límite secundario)",
   espera(403, {"Retry-After": "90"}, AHORA, 0) == 90)
ok("403 sin cabeceras de límite (proxy, filtrado...) → error normal",
   espera(403, {"X-RateLimit-Remaining": "12"}, AHORA, 0) is None and espera(403, {}, AHORA, 0) is None)
ok("404, 500... → error normal", espera(404, {}, AHORA, 0) is None and espera(500, {"Retry-After": "5"}, AHORA, 0) is None)
ok("espera mínima de 1 minuto aunque el Reset ya haya pasado",
   espera(403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(AHORA - 50)}, AHORA, 0) == 60)
ok("espera máxima de 2 horas",
   espera(403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(AHORA + 99999)}, AHORA, 0) == _ESPERA_LIMITE_MAX_S)
ok("429 sin cabeceras → 15 min", espera(429, {}, AHORA, 0) == 900)
ok("el margen al azar está entre 0 y 5 min",
   all(600 <= espera(403, {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(AHORA + 600)}, AHORA) <= 900
       for _ in range(200)))

print(f"\n{'Todas las comprobaciones OK.' if not fallos else str(len(fallos)) + ' fallo(s)'}")
sys.exit(1 if fallos else 0)
