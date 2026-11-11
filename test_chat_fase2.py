"""Chat, fase 2 (v4.18.46): responder citando, reenviar y eliminar mensajes (servidor del chat v1.4.0).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_chat_fase2.py  (en Windows o en cualquier sistema: si no hay Tkinter, se simula).
No se conecta a ningún servidor: las peticiones al chat se simulan.
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

from ui import acciones_chat as ac  # noqa: E402
import services.chat_client as cc  # noqa: E402

fallos = []


def ok(nombre, cond, det=""):
    print(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
    if not cond:
        fallos.append(nombre)


class _Cliente:
    username = "ana"
    def nombre_de(self, u):
        return {"beto": "Beto Pérez", "carla": "Carla"}.get(u, u)


cli = _Cliente()

# ── 1. Qué lleva cada burbuja ────────────────────────────────────────────────
m = {"id": 7, "remitente": "beto", "contenido": "Yo lo pido", "tipo": "texto", "reenviado": False,
     "responde_a": {"id": 3, "remitente": "ana", "contenido": "¿Quién pide?", "tipo": "texto"}}
d = ac.datos_burbuja(m, cli)
ok("la cita lleva quién (Tú si es propia) y qué", d["cita"] == ("Tú", "¿Quién pide?"), d)
ok("sin reenviado ni eliminado", d["reenviado"] is False and d["eliminado"] is False, d)
ok("mensaje de un servidor antiguo (sin campos nuevos): sin cita",
   ac.datos_burbuja({"id": 1, "contenido": "hola"}, cli) == {"cita": None, "reenviado": False, "eliminado": False})
ok("reenviado y eliminado", ac.datos_burbuja({"id": 2, "reenviado": True, "tipo": "eliminado"}, cli)
   == {"cita": None, "reenviado": True, "eliminado": True})

# ── 2. Acciones del menú ─────────────────────────────────────────────────────
etiquetas = lambda lst: [e for e, _f in lst]  # noqa: E731
ok("mensaje de otro: Responder y Reenviar (no Eliminar)",
   etiquetas(ac.acciones(m, cli, None, lambda x: None)) == ["↩  Responder", "↪  Reenviar…"])
propio = dict(m, remitente="ana")
ok("mensaje propio: también Eliminar", "🗑  Eliminar" in etiquetas(ac.acciones(propio, cli, None, lambda x: None)))
ok("sin id (pintado optimista): sin acciones", ac.acciones({"remitente": "ana", "contenido": "x"}, cli, None, None) == [])
ok("eliminado: sin acciones", ac.acciones(dict(propio, tipo="eliminado"), cli, None, None) == [])
llamado = []
ac.acciones(m, cli, None, lambda x: llamado.append(x))[0][1]()
ok("«Responder» llama con el mensaje", llamado == [m])

# ── 3. Textos ────────────────────────────────────────────────────────────────
ok("cita de un adjunto: «📷 nombre»", ac.texto_cita({"tipo": "imagen", "adjunto": {"nombre_archivo": "obra.jpg"}}) == "📷 obra.jpg")
ok("barra de respuesta con nombre real", ac.resumen_barra(m, cli).startswith("↩  Respondiendo a Beto Pérez: Yo lo pido"))
ok("barra recortada", ac.resumen_barra(dict(m, contenido="x" * 300), cli).endswith("…"))

# ── 4. Destinos de «Reenviar a…» ─────────────────────────────────────────────
canales = [{"tipo": "general", "canal_id": "general"}, {"tipo": "grupo", "canal_id": "grp:1", "nombre": "Compras"},
           {"tipo": "privado", "canal_id": "dm:ana:beto", "otro_usuario": "beto"}]
usuarios = [{"username": "ana", "nombre": "Ana"}, {"username": "beto", "nombre": "Beto Pérez"},
            {"username": "carla", "nombre": "Carla"}]
dest = ac.destinos(canales, usuarios, cli)
ok("conversaciones y después compañeros sin privado (ni yo ni los repetidos)",
   [(c, dd) for _e, c, dd in dest] == [("general", None), ("grp:1", None), ("dm:ana:beto", None), (None, "carla")], dest)

# ── 5. Cliente: lo que se manda al servidor ──────────────────────────────────
c = cc.ChatClient.__new__(cc.ChatClient)
c._sio = mock.MagicMock(connected=True)
c.enviar_mensaje("Yo lo pido", canal_id="grp:1", responde_a=3)
ok("enviar con responde_a por el socket", c._sio.emit.call_args.args == ("enviar_mensaje",
   {"contenido": "Yo lo pido", "canal_id": "grp:1", "responde_a": 3}), c._sio.emit.call_args)
c.enviar_mensaje("hola", canal_id="general")
ok("sin responder no se manda responde_a", "responde_a" not in c._sio.emit.call_args.args[1])
c._post_rest = mock.MagicMock(return_value={"ok": True})
c.eliminar_mensaje(7)
ok("eliminar → POST /api/chat/mensajes/7/eliminar", c._post_rest.call_args.args == ("/api/chat/mensajes/7/eliminar", {}))
c.reenviar_mensaje(7, destinatario="carla")
ok("reenviar a un compañero", c._post_rest.call_args.args == ("/api/chat/mensajes/7/reenviar", {"destinatario": "carla"}))
c.reenviar_mensaje(7, canal_id="grp:1")
ok("reenviar a una conversación", c._post_rest.call_args.args[1] == {"canal_id": "grp:1"})
c.eventos = __import__("queue").Queue()
c._on_mensaje_eliminado({"id": 7, "canal_id": "grp:1"})
ev = c.eventos.get_nowait()
ok("el evento mensaje_eliminado llega a la cola", ev == {"tipo": cc.EVT_ELIMINADO, "mensaje": {"id": 7, "canal_id": "grp:1"}}, ev)
spec = open(os.path.join(RAIZ, "main.spec"), encoding="utf-8").read()
ok("ui.acciones_chat está en hiddenimports de main.spec", "'ui.acciones_chat'" in spec)

print(f"\n{'Todas las comprobaciones OK.' if not fallos else str(len(fallos)) + ' fallo(s)'}")
sys.exit(1 if fallos else 0)
