"""Chat, fase 5 (v4.18.70): escuchar los mensajes de voz del chat (servidor del chat v1.8.0).

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

import tempfile  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402

from services import voz  # noqa: E402
from ui import acciones_chat  # noqa: E402

fallos = []


def ok(nombre, cond, det=""):
    print(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
    if not cond:
        fallos.append(nombre)


VOZ = {"id": 7, "tipo": "voz", "contenido": "🎤 Mensaje de voz (0:12)",
       "adjunto": {"url": "https://x.supabase.co/a/voz_1.m4a", "nombre_archivo": "voz_1.m4a", "duracion_ms": 12400}}
ARCHIVO = {"id": 8, "tipo": "archivo", "adjunto": {"url": "https://x.supabase.co/a/nota.m4a", "nombre_archivo": "nota.m4a"}}

ok("es_voz: tipo «voz» con adjunto", voz.es_voz(VOZ) and not voz.es_voz(ARCHIVO) and not voz.es_voz({"tipo": "voz"})
   and not voz.es_voz(None))
ok("duración «0:12», «3:00» y sin dato «0:00»", voz.texto_duracion(12400) == "0:12"
   and voz.texto_duracion(180000) == "3:00" and voz.texto_duracion(None) == "0:00" and voz.texto_duracion("x") == "0:00")
ok("texto de la burbuja", voz.texto_burbuja(VOZ).startswith("🎤  Mensaje de voz (0:12)"))
ok("la cita de un mensaje de voz", acciones_chat.texto_cita(VOZ) == "🎤 Mensaje de voz")
ok("registrar solo los de voz", voz.registrar(VOZ) and not voz.registrar(ARCHIVO)
   and voz.es_url_de_voz(VOZ["adjunto"]["url"]) and not voz.es_url_de_voz(ARCHIVO["adjunto"]["url"]))
r1, r2 = voz.ruta_cache("https://a/1.m4a", "1.m4a"), voz.ruta_cache("https://a/2.m4a", "2.m4a")
ok("caché: una ruta por URL, en la carpeta temporal y con extensión de audio",
   r1 != r2 and r1 == voz.ruta_cache("https://a/1.m4a", "1.m4a") and r1.startswith(tempfile.gettempdir())
   and r1.endswith(".m4a") and voz.ruta_cache("https://a/3", "x.exe").endswith(".m4a"))


class MciSimulado:
    def __init__(self, falla_open=False):
        self.ordenes, self.modo, self.falla_open = [], "playing", falla_open

    def __call__(self, orden):
        self.ordenes.append(orden)
        if orden.startswith("open") and self.falla_open:
            raise OSError("MCI 263")
        if orden.startswith("status"):
            return self.modo
        return ""


mci = MciSimulado()
abiertos = []
rep = voz.ReproductorVoz(mci=mci, abrir_con_programa=abiertos.append, es_windows=True)
ok("reproducir con MCI", rep.reproducir("u1", "C:/t/a.m4a") == "mci" and rep.sonando == "u1"
   and any(o.startswith('open "C:/t/a.m4a" type mpegvideo') for o in mci.ordenes)
   and any(o.startswith("play ") for o in mci.ordenes) and not abiertos, mci.ordenes)
ok("mientras suena, no ha terminado", not rep.ha_terminado())
mci.modo = "stopped"
ok("al acabar, se libera", rep.ha_terminado() and rep.sonando is None and mci.ordenes[-1].startswith("close"))
rep2 = voz.ReproductorVoz(mci=MciSimulado(falla_open=True), abrir_con_programa=abiertos.append, es_windows=True)
ok("si MCI no puede, se abre con el programa predeterminado",
   rep2.reproducir("u2", "C:/t/b.m4a") == "programa" and abiertos == ["C:/t/b.m4a"] and rep2.sonando is None)
ok("fuera de Windows no hace nada", voz.ReproductorVoz(mci=MciSimulado(), es_windows=False).reproducir("u", "r") == "nada")

# pulsar(): descarga una vez, reproduce, un segundo clic para y lo descargado se reutiliza
mci = MciSimulado()
rep = voz.ReproductorVoz(mci=mci, abrir_con_programa=abiertos.append, es_windows=True)
descargas, errores, listo = [], [], threading.Event()


def descargar(url):
    descargas.append(url)
    return b"audio"


def despues(ms, f):
    if ms == 0:
        f()
        listo.set()


url = "https://x.supabase.co/a/prueba_%d.m4a" % int(time.time() * 1000)
voz.pulsar(url, "voz.m4a", descargar, despues, errores.append, rep=rep)
listo.wait(5)
ok("primer clic: descarga y suena", descargas == [url] and rep.sonando == url and not errores, (descargas, errores))
ok("el audio queda en la caché", open(voz.ruta_cache(url, "voz.m4a"), "rb").read() == b"audio")
voz.pulsar(url, "voz.m4a", descargar, despues, errores.append, rep=rep)
ok("segundo clic: para", rep.sonando is None)
listo.clear()
voz.pulsar(url, "voz.m4a", descargar, despues, errores.append, rep=rep)
listo.wait(5)
ok("tercer clic: vuelve a sonar sin descargar otra vez", descargas == [url] and rep.sonando == url)
listo.clear()


def descarga_mala(u):
    raise ValueError("La dirección del adjunto no es de confianza.")


voz.pulsar("https://otro/sin_cache.m4a", "v.m4a", descarga_mala, despues, errores.append, rep=rep)
listo.wait(5)
ok("si no se puede descargar, se avisa", errores and "no es de confianza" in errores[-1], errores)
os.remove(voz.ruta_cache(url, "voz.m4a"))

# Las ventanas lo usan
fuente_v = open(os.path.join(RAIZ, "app", "ui", "ventana_chat.py"), encoding="utf-8").read()
fuente_p = open(os.path.join(RAIZ, "app", "ui", "chat_popup.py"), encoding="utf-8").read()
ok("ventana y burbuja pintan y escuchan los mensajes de voz",
   all("voz.registrar(m)" in f and "voz.es_url_de_voz(url)" in f and "voz.pulsar(" in f for f in (fuente_v, fuente_p)))
ok("services.voz está en hiddenimports de main.spec",
   "'services.voz'" in open(os.path.join(RAIZ, "main.spec"), encoding="utf-8").read())

print()
print("TODO OK" if not fallos else f"{len(fallos)} FALLO(S): {fallos}")
sys.exit(1 if fallos else 0)
