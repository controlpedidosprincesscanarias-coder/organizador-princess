"""Organizador y Control Pedidos (v4.18.52): el aviso «abre o instala el Organizador» de Control Pedidos.

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_control_pedidos.py  (en cualquier sistema; no se conecta a ningún servidor).
1. Cada consulta a Control Pedidos lleva la versión instalada (cabecera X-Organizador-Version): así sabe que
   este Organizador está abierto y cuál tiene cada uno (Control Pedidos v12.34.26).
2. El instalador registra el enlace organizadorprincess:// (botón «Abrir el Organizador») apuntando al
   programa instalado, y lo borra al desinstalar.
3. (v4.18.60) El enlace trae el código del navegador de Control Pedidos: se guarda y se envía en cada
   consulta (X-Organizador-Navegadores), para que Control Pedidos sepa si está abierto en ESTE PC.
"""
import json
import os
import re
import sys
from unittest import mock

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(RAIZ, "app"))
sys.path.insert(0, RAIZ)

try:
    import tkinter  # noqa: F401
except ImportError:   # sin Tkinter (Linux de pruebas): se simula, como en test_chat_fase1.py
    import importlib.abc
    import importlib.machinery

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

fallos = []


def ok(nombre, cond, det=""):
    print(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
    if not cond:
        fallos.append(nombre)


# ── 1. La versión en cada consulta ───────────────────────────────────────────
import pedidos_agenda_bridge as bridge  # noqa: E402
import services.update_service as update  # noqa: E402

enviadas = []


class _Resp:
    def read(self): return json.dumps({"ok": True}).encode()
    def __enter__(self): return self
    def __exit__(self, *a): return False


sesion = bridge._Session()
with mock.patch.object(update, "APP_VERSION", "v4.18.52"), \
        mock.patch.object(sesion._opener, "open", side_effect=lambda req, timeout=0: enviadas.append(req) or _Resp()):
    sesion._request("/api/bridge/notificaciones")
cab = {k.lower(): v for k, v in enviadas[-1].header_items()} if enviadas else {}
ok("la consulta lleva la versión instalada", cab.get("x-organizador-version") == "v4.18.52", cab)
ok("…sin perder el User-Agent de navegador (Cloudflare)", "Mozilla/5.0" in cab.get("user-agent", ""), cab)
with mock.patch.object(update, "APP_VERSION", ""):
    ok("sin versión conocida no falla (cabecera vacía)", bridge._version_organizador() == "")

main = open(os.path.join(RAIZ, "main_agenda.py"), encoding="utf-8").read()
ok("main_agenda deja la versión en update_service (de ahí la lee el bridge)",
   "_update_mod.APP_VERSION = APP_VERSION" in main)

# ── 2. El enlace organizadorprincess:// en el instalador ────────────────────
iss = open(os.path.join(RAIZ, "OrganizadorPrincess_Setup.iss"), encoding="utf-8").read()
reg = re.search(r"^\[Registry\]\n(.*?)(?:\n\s*\n|\n;)", iss, re.S | re.M)
lineas = reg.group(1).splitlines() if reg else []
ok("el instalador tiene la sección [Registry]", bool(lineas), iss[:0])
ok("registra el protocolo organizadorprincess con «URL Protocol»",
   any('Subkey: "organizadorprincess"' in l and 'ValueName: "URL Protocol"' in l for l in lineas), lineas)
ok("…que se borra al desinstalar", any("organizadorprincess" in l and "uninsdeletekey" in l for l in lineas), lineas)
comando = next((l for l in lineas if "shell\\open\\command" in l), "")
ok("…y abre el programa instalado", '{app}\\{#MyAppExe}' in comando, comando)
ok("…pasándole el enlace (\"%1\"), con el código del navegador desde la v4.18.60", '""%1""' in comando, comando)
ok("el instalador sigue pidiendo administrador (HKCR, para todos los usuarios del equipo)",
   "PrivilegesRequired=admin" in iss)

# ── 3. Navegador vinculado (v4.18.60) ───────────────────────────────────────
import tempfile  # noqa: E402
import services.vinculo_navegador as vn  # noqa: E402
COD = "0b6c2e1a-4d2f-4c3b-9e8a-7f6d5c4b3a21"
ok("lee el código del enlace que abre el navegador",
   vn.extraer_navegador([f"organizadorprincess://abrir?navegador={COD}"]) == COD)
ok("…también con «/» antes de «?» y entre comillas",
   vn.extraer_navegador([f'"organizadorprincess://abrir/?navegador={COD}"']) == COD)
ok("sin enlace o con un código raro, nada",
   vn.extraer_navegador([]) is None and vn.extraer_navegador(["--algo"]) is None
   and vn.extraer_navegador(["organizadorprincess://abrir?navegador=<script>"]) is None
   and vn.extraer_navegador(["organizadorprincess://abrir"]) is None
   and vn.extraer_navegador([f"https://otra.web/?navegador={COD}"]) is None)
with tempfile.TemporaryDirectory() as d:
    ruta = os.path.join(d, "navegadores.json")
    ok("sin vincular, la cabecera va vacía", vn.cabecera(ruta) == "")
    ok("al abrirse con el enlace, guarda el código",
       vn.guardar_desde_argv([f"organizadorprincess://abrir?navegador={COD}"], ruta) and vn.leer(ruta) == [COD])
    otros = [f"{i:032d}" for i in range(12)]
    for o in otros:
        vn.guardar(o, ruta)
    vn.guardar(COD, ruta)
    lista = vn.leer(ruta)
    ok("como mucho 10, sin repetir y el último vinculado primero",
       len(lista) == 10 and lista[0] == COD and len(set(lista)) == 10, lista)
    ok("la cabecera los lleva separados por comas", vn.cabecera(ruta) == ",".join(lista))
    open(ruta, "w").write("{roto")
    ok("un archivo dañado no rompe nada", vn.leer(ruta) == [] and vn.guardar(COD, ruta) and vn.leer(ruta) == [COD])
enviadas.clear()
with mock.patch.object(vn, "cabecera", return_value=COD), \
        mock.patch.object(sesion._opener, "open", side_effect=lambda req, timeout=0: enviadas.append(req) or _Resp()):
    sesion._request("/api/bridge/notificaciones")
cab = {k.lower(): v for k, v in enviadas[-1].header_items()} if enviadas else {}
ok("cada consulta lleva los navegadores vinculados", cab.get("x-organizador-navegadores") == COD, cab)
ok("main_agenda guarda el código al arrancar con el enlace", "guardar_desde_argv(sys.argv[1:])" in main)
spec = open(os.path.join(RAIZ, "main.spec"), encoding="utf-8").read()
ok("main.spec incluye services.vinculo_navegador", "'services.vinculo_navegador'" in spec)

print(f"\n{'Todas las comprobaciones OK.' if not fallos else str(len(fallos)) + ' fallo(s)'}")
sys.exit(1 if fallos else 0)
