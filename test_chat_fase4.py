"""Chat, fase 4 (v4.18.64): vaciar y eliminar chats, y avisos al escribir a usuarios desactivados o que ya no
existen (servidor del chat v1.7.0).

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

import services.chat_client as cc  # noqa: E402

fallos = []


def ok(nombre, cond, det=""):
    print(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
    if not cond:
        fallos.append(nombre)


def cliente(post=None, conectado=False):
    c = cc.ChatClient.__new__(cc.ChatClient)
    c.eventos = queue.Queue()
    c._post_rest = mock.MagicMock(return_value=post if post is not None else {"ok": True})
    c._sio = mock.MagicMock()
    c._sio.connected = conectado
    return c


c = cliente()
c.vaciar_chat("dm:ana:beto")
ok("vaciar → POST /api/chat/canales/<id>/vaciar", c._post_rest.call_args.args == ("/api/chat/canales/dm:ana:beto/vaciar", {}))
c.eliminar_chat("dm:ana:beto")
ok("eliminar → POST /api/chat/canales/<id>/eliminar",
   c._post_rest.call_args.args == ("/api/chat/canales/dm:ana:beto/eliminar", {}))
ok("sin respuesta del chat → error", "error" in cliente(post={}).vaciar_chat("general"))

c._on_conversacion_oculta({"canal_id": "dm:ana:beto", "eliminada": True, "hasta": "x"})
ok("el evento conversacion_oculta llega a la cola", c.eventos.get_nowait() == {
    "tipo": cc.EVT_OCULTA, "conversacion": {"canal_id": "dm:ana:beto", "eliminada": True, "hasta": "x"}})

c._on_error_chat({"error": "Beto está temporalmente desactivado", "codigo": cc.DESTINO_DESACTIVADO,
                  "usuario": "beto", "canal_id": "dm:ana:beto"})
ev = c.eventos.get_nowait()
ok("error_chat con «codigo» pasa codigo, usuario y canal", ev["tipo"] == cc.EVT_ERROR
   and ev["codigo"] == "usuario_desactivado" and ev["usuario"] == "beto" and ev["canal_id"] == "dm:ana:beto", ev)
c._on_error_chat({"error": "Demasiados mensajes"})
ev = c.eventos.get_nowait()
ok("error_chat antiguo (sin codigo) sigue igual", ev["mensaje"] == "Demasiados mensajes" and ev["codigo"] is None)

# Por REST (sin socket) el error llega en la respuesta y se pasa a la cola igual
c = cliente(post={"error": "Beto ya no existe", "codigo": cc.DESTINO_NO_EXISTE, "usuario": "beto"})
c.enviar_mensaje("hola", canal_id="dm:ana:beto")
ev = c.eventos.get_nowait()
ok("envío por REST a quien ya no existe → evento con codigo y canal",
   ev["codigo"] == "usuario_no_existe" and ev["canal_id"] == "dm:ana:beto", ev)
c = cliente(post={"ok": True, "mensaje": {}})
c.enviar_mensaje("hola", canal_id="general")
ok("envío por REST correcto → sin eventos de error", c.eventos.empty())
c = cliente(conectado=True)
c.enviar_mensaje("hola", canal_id="dm:ana:beto")
ok("con socket se sigue enviando por socket", c._sio.emit.call_args.args[0] == "enviar_mensaje"
   and not c._post_rest.called)

# Las ventanas atienden los eventos nuevos
fuente_v = open(os.path.join(RAIZ, "app", "ui", "ventana_chat.py"), encoding="utf-8").read()
fuente_p = open(os.path.join(RAIZ, "app", "ui", "chat_popup.py"), encoding="utf-8").read()
ok("ventana: botones «Vaciar chat» y «Eliminar chat»", "🧹 Vaciar chat" in fuente_v and "🗑 Eliminar chat" in fuente_v)
ok("ventana: ya no se limpia solo en este equipo", "set_chat_limpiado(" not in fuente_v)
ok("ventana: vacía y elimina en el servidor", "cliente.vaciar_chat(" in fuente_v and "cliente.eliminar_chat(" in fuente_v)
ok("ventana y burbuja atienden EVT_OCULTA", "EVT_OCULTA" in fuente_v and "EVT_OCULTA" in fuente_p)
ok("ventana y burbuja avisan de usuario desactivado o que no existe",
   all(x in f for f in (fuente_v, fuente_p) for x in ("DESTINO_DESACTIVADO", "DESTINO_NO_EXISTE", "askyesno")))
ok("ventana: muestra otro_estado", "otro_estado" in fuente_v)

print()
print("TODO OK" if not fallos else f"{len(fallos)} FALLO(S): {fallos}")
sys.exit(1 if fallos else 0)
