"""Chat, fase 3 (v4.18.48): integrantes y gestión de los grupos (servidor del chat v1.5.0).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_chat_fase3.py  (en Windows o en cualquier sistema: si no hay Tkinter, se simula).
No se conecta a ningún servidor: las peticiones al chat se simulan.
"""
import importlib.abc
import importlib.machinery
import os
import queue
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

from ui import grupo_info  # noqa: E402
import services.chat_client as cc  # noqa: E402

fallos = []


def ok(nombre, cond, det=""):
    print(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
    if not cond:
        fallos.append(nombre)


ok("etiqueta: (tú) y quién gestiona",
   grupo_info.etiqueta({"username": "ana", "nombre": "Ana", "es_creador": True}, "ana") == "Ana (tú)  ·  gestiona el grupo")
ok("etiqueta de otro integrante", grupo_info.etiqueta({"username": "beto", "nombre": "Beto"}, "ana") == "Beto")
cand = grupo_info.candidatos([{"username": "carla", "nombre": "Carla"}, {"username": "beto", "nombre": "Beto"},
                              {"username": "dani", "nombre": "Ángel"}], [{"username": "beto"}])
ok("candidatos para añadir: los que no están, por nombre", [u["username"] for u in cand] == ["carla", "dani"], cand)

c = cc.ChatClient.__new__(cc.ChatClient)
c._get_rest = mock.MagicMock(return_value={"miembros": []})
c._post_rest = mock.MagicMock(return_value={"ok": True})
c.detalle_grupo("grp:1")
ok("detalle → GET /api/chat/grupos/grp:1", c._get_rest.call_args.args == ("/api/chat/grupos/grp:1",))
c.cambiar_miembros_grupo("grp:1", anadir=["carla"])
ok("añadir → POST …/miembros", c._post_rest.call_args.args == ("/api/chat/grupos/grp:1/miembros", {"anadir": ["carla"], "quitar": []}))
c.renombrar_grupo("grp:1", "Pescado")
ok("renombrar → POST …/nombre", c._post_rest.call_args.args == ("/api/chat/grupos/grp:1/nombre", {"nombre": "Pescado"}))
c.salir_grupo("grp:1")
ok("salir → POST …/salir", c._post_rest.call_args.args == ("/api/chat/grupos/grp:1/salir", {}))
c.eliminar_grupo("grp:1")
ok("eliminar → POST …/eliminar", c._post_rest.call_args.args == ("/api/chat/grupos/grp:1/eliminar", {}))
c.eventos = queue.Queue()
c._on_grupo_cambiado({"canal_id": "grp:1", "eliminado": True})
ok("el evento grupo_cambiado llega a la cola",
   c.eventos.get_nowait() == {"tipo": cc.EVT_GRUPO, "grupo": {"canal_id": "grp:1", "eliminado": True}})
ok("ui.grupo_info está en hiddenimports de main.spec",
   "'ui.grupo_info'" in open(os.path.join(RAIZ, "main.spec"), encoding="utf-8").read())

# ── (v4.18.50) Avisos de Control Pedidos (chat v1.6.0) ─────────────────────
ok("la conversación de avisos se reconoce", cc.es_canal_avisos("dm:ana:control-pedidos")
   and cc.es_canal_avisos("dm:control-pedidos:zoe") and not cc.es_canal_avisos("dm:ana:beto")
   and not cc.es_canal_avisos("general") and not cc.es_canal_avisos(None))
c2 = cc.ChatClient.__new__(cc.ChatClient)
import threading as _th  # noqa: E402
c2._mapa_nombres_lock, c2._mapa_nombres = _th.Lock(), {}
ok("la cuenta de avisos se llama «Control Pedidos»", c2.nombre_de("control-pedidos") == "Control Pedidos")
from ui import acciones_chat  # noqa: E402
class _Yo:
    username = "ana"
    def nombre_de(self, u): return u
acc = acciones_chat.acciones({"id": 5, "remitente": "control-pedidos", "contenido": "⚠️ Pedido 1"}, _Yo(), None, lambda m: None)
ok("a un aviso solo se le puede Reenviar (no Responder)", [e for e, _f in acc] == ["↪  Reenviar…"], acc)

print(f"\n{'Todas las comprobaciones OK.' if not fallos else str(len(fallos)) + ' fallo(s)'}")
sys.exit(1 if fallos else 0)
