"""Actualización de un clic (v4.18.20): instalar sola y no volver a preguntar al arrancar.

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_actualizacion.py  (en Windows o en cualquier sistema: si no hay Tkinter, se simula).
No instala nada: os.startfile se sustituye por uno de prueba.
"""
import importlib.abc
import importlib.machinery
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from unittest import mock

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(RAIZ, "app"))
sys.path.insert(0, RAIZ)
PERFIL = tempfile.mkdtemp(prefix="org_actualizacion_")
os.environ["APPDATA"] = PERFIL          # nunca la carpeta de datos real
os.environ["LOCALAPPDATA"] = PERFIL

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

import services.update_service as us  # noqa: E402

fallos = []
def ok(nombre, cond, det=""):
    print(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
    if not cond:
        fallos.append(nombre)

us.APP_VERSION = "v4.18.20"
lanzados = []
def startfile_ok(ruta, operacion="open", argumentos=""):
    lanzados.append((ruta, operacion, argumentos))
def startfile_cancelado(*a, **k):
    e = OSError("La operación fue cancelada por el usuario")
    e.winerror = 1223
    raise e

# 1. Lanzar el instalador: silencioso, por ShellExecute, y deja la marca de esta versión
with mock.patch.object(us.os, "startfile", startfile_ok, create=True):
    r = us._instalar_ya(r"C:\\tmp\\OrganizadorPrincess_Setup_4.18.20.exe", "v4.18.20")
ok("el instalador se lanza sin error", r is None, r)
ok("se lanza en modo silencioso", lanzados and "/SILENT" in lanzados[0][2] and "/SUPPRESSMSGBOXES" in lanzados[0][2], lanzados)
ok("queda la marca de la actualización automática", os.path.exists(us._MARCA_AUTO))

# 2. Al arrancar la versión nueva: «Solo actualizar» sin preguntar, y la marca se borra
ok("al arrancar se aplica «Solo actualizar versión» sin preguntar", us.actualizacion_automatica_aplicada("v4.18.18") is True)
with open(us.VERSION_FILE, encoding="utf-8") as f:
    ok("version.json queda con la versión nueva", json.load(f).get("version") == "v4.18.20")
ok("la marca se borra", not os.path.exists(us._MARCA_AUTO))
ok("sin marca, se pregunta como siempre", us.actualizacion_automatica_aplicada("v4.18.18") is False)

# 3. Marca de otra versión o antigua: se pregunta como siempre
for version, fecha, nombre in [("4.18.22", datetime.now(), "de otra versión"),
                               ("4.18.20", datetime.now() - timedelta(days=2), "de hace más de un día")]:
    with open(us._MARCA_AUTO, "w", encoding="utf-8") as f:
        json.dump({"version": version, "fecha": fecha.isoformat()}, f)
    ok(f"una marca {nombre} no se aplica", us.actualizacion_automatica_aplicada("v4.18.18") is False)

# 4. Si se cancela el permiso de Windows: mensaje claro y sin marca
with mock.patch.object(us.os, "startfile", startfile_cancelado, create=True):
    r = us._instalar_ya("x.exe", "v4.18.20")
ok("permiso de Windows cancelado: mensaje claro", r and "permiso" in r, r)
ok("permiso cancelado: no queda la marca", not os.path.exists(us._MARCA_AUTO))

# 5. Carpeta de descarga propia, que se vacía en cada descarga
c = us._carpeta_descarga_actualizacion()
open(os.path.join(c, "viejo.exe"), "w").close()
c2 = us._carpeta_descarga_actualizacion()
ok("carpeta temporal propia y vacía en cada descarga", c == c2 and not os.listdir(c2), os.listdir(c2))

# 5b. (v4.18.36) Al arrancar se borran los instaladores ya aplicados (esta versión o anteriores)
import tempfile as _tf
with _tf.TemporaryDirectory() as _c:
    for _n in ("OrganizadorPrincess_Setup_4.18.34.exe", "OrganizadorPrincess_Setup_4.18.34.exe.sha256",
               "OrganizadorPrincess_Setup_4.18.36.exe", "OrganizadorPrincess_Setup_4.18.38.exe", "otro.txt"):
        open(os.path.join(_c, _n), "w").close()
    b, p = us.borrar_instaladores_aplicados("v4.18.36", carpeta=_c)
    ok("se borran los instaladores de esta versión y anteriores",
       sorted(b) == ["OrganizadorPrincess_Setup_4.18.34.exe", "OrganizadorPrincess_Setup_4.18.34.exe.sha256",
                     "OrganizadorPrincess_Setup_4.18.36.exe"] and p == [], (b, p))
    ok("se dejan el de una versión más nueva y lo que no es un instalador",
       sorted(os.listdir(_c)) == ["OrganizadorPrincess_Setup_4.18.38.exe", "otro.txt"], os.listdir(_c))
    with mock.patch.object(us.os, "remove", side_effect=PermissionError("en uso")):
        open(os.path.join(_c, "OrganizadorPrincess_Setup_4.18.30.exe"), "w").close()
        b, p = us.borrar_instaladores_aplicados("v4.18.36", carpeta=_c)
    ok("si no se puede borrar, queda pendiente sin fallar", b == [] and p == ["OrganizadorPrincess_Setup_4.18.30.exe"], (b, p))
ok("sin carpeta de descarga, no falla", us.borrar_instaladores_aplicados("v4.18.36", carpeta=os.path.join(RAIZ, "no_existe")) == ([], []))

# 6. El instalador vuelve a abrir el Organizador tras la instalación silenciosa
iss = open(os.path.join(RAIZ, "OrganizadorPrincess_Setup.iss"), encoding="utf-8").read()
ok("el .iss reabre el Organizador al instalar en silencio (WizardSilent, usuario normal)",
   "Check: WizardSilent" in iss and "runasoriginaluser" in iss)
_taskkill = [l for l in iss.splitlines() if "taskkill" in l.lower() and not l.strip().startswith(("{", ";"))]
ok("el instalador cierra el Organizador SIN «/T» (con /T se cerraba a sí mismo al lanzarlo «Actualizar ahora»)",
   bool(_taskkill) and all("/T" not in l.upper().replace("/TERM", "") for l in _taskkill), _taskkill)

print(f"\n{'Todas las comprobaciones OK.' if not fallos else str(len(fallos)) + ' fallo(s)'}")
sys.exit(1 if fallos else 0)
