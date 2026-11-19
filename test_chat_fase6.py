"""Chat, fase 6 (v4.18.74): enlaces pulsables, tarjeta de los enlaces de vídeo y vídeos adjuntos (chat v1.9.0).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_chat_fase6.py  (en Windows o en cualquier sistema: si no hay Tkinter, se simula y se salta
la parte que pinta burbujas de verdad). No se conecta a ningún servidor: las peticiones al chat se simulan.
"""
import base64
import importlib.abc
import importlib.machinery
import io
import os
import sys
from unittest import mock

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(RAIZ, "app"))

TK_REAL = True
try:
    import tkinter  # noqa: F401
except ImportError:
    TK_REAL = False

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

from utils import enlaces  # noqa: E402
from ui import vista_previa  # noqa: E402

fallos = []


def ok(nombre, cond, det=""):
    print(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
    if not cond:
        fallos.append(nombre)


# ── 1. Enlaces en el texto ───────────────────────────────────────────────────
t = enlaces.trozos("Mira https://vm.tiktok.com/ZNdemo/. Y esto: http://ejemplo.es/a?b=1) fin")
ok("1. trozos de texto y enlaces, sin la puntuación final",
   t == [("Mira ", None), ("https://vm.tiktok.com/ZNdemo/", "https://vm.tiktok.com/ZNdemo/"), (". Y esto: ", None),
         ("http://ejemplo.es/a?b=1", "http://ejemplo.es/a?b=1"), (") fin", None)], t)
ok("1. sin enlaces, un solo trozo", enlaces.trozos("hola") == [("hola", None)])
ok("1. ni javascript: ni ftp: ni con usuario", all(u is None for _t, u in enlaces.trozos(
    "javascript:alert(1) ftp://x.es/a")) and not enlaces.abrible("https://u:p@ejemplo.es/"))

# ── 2. Enlaces de vídeo ──────────────────────────────────────────────────────
ok("2. TikTok, YouTube e Instagram", [enlaces.sitio_de_video(u) for u in (
    "https://vm.tiktok.com/ZNdemo/", "https://youtu.be/abc", "https://m.youtube.com/watch?v=a",
    "https://www.instagram.com/reel/abc/")] == ["tiktok", "youtube", "youtube", "instagram"])
ok("2. otros sitios o sin https, no", [enlaces.sitio_de_video(u) for u in (
    "http://www.tiktok.com/@a/video/1", "https://tiktok.com.malo.example/x", "https://eviltiktok.com/x", "")] == [None] * 4)
ok("2. el primero de vídeo del mensaje",
   enlaces.primer_video("Hola https://ejemplo.es y https://youtu.be/abc, https://vm.tiktok.com/x") == "https://youtu.be/abc")
ok("2. nombre del sitio", enlaces.nombre_sitio("https://youtu.be/a") == "YouTube" and enlaces.nombre_sitio("x") == "Vídeo")

# ── 3. Vídeos adjuntos ───────────────────────────────────────────────────────
VIDEO = {"tipo": "archivo", "adjunto": {"url": "https://demo.supabase.co/a.mp4", "nombre_archivo": "viaje.MP4"}}
ok("3. un .mp4 es vídeo", enlaces.es_video(VIDEO))
ok("3. por el tipo video/*", enlaces.es_video({"adjunto": {"url": "u", "nombre_archivo": "clip", "mime_type": "video/quicktime"}}))
ok("3. ni una foto ni un mensaje de voz", not enlaces.es_video({"adjunto": {"url": "u", "nombre_archivo": "a.jpg"}})
   and not enlaces.es_video({"tipo": "voz", "adjunto": {"url": "u", "nombre_archivo": "voz.mp4"}}))

# ── 4. Miniatura de la tarjeta ───────────────────────────────────────────────
try:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (480, 360), (200, 30, 30)).save(buf, "JPEG")
    MINI = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    img = vista_previa.imagen_de({"miniatura": MINI})
    ok("4. la miniatura se reduce a 240×135 como mucho", img is not None and img.size[0] <= 240 and img.size[1] <= 135,
       getattr(img, "size", None))
    ok("4. sin miniatura, o que no es data:image, nada", vista_previa.imagen_de({"miniatura": None}) is None
       and vista_previa.imagen_de({"miniatura": "https://otro.sitio/a.jpg"}) is None
       and vista_previa.imagen_de({"miniatura": "data:image/jpeg;base64,@@@"}) is None)
except ImportError:
    MINI = None
    print("(sin Pillow: se salta la miniatura)")

# ── 5. ChatClient.vista_previa ───────────────────────────────────────────────
from services.chat_client import ChatClient  # noqa: E402
cli = ChatClient.__new__(ChatClient)
with mock.patch.object(ChatClient, "_get_rest", return_value={"tarjeta": {"sitio": "YouTube", "titulo": "Demo"}}) as g:
    r = cli.vista_previa("https://youtu.be/abc")
ok("5. pide la tarjeta al servidor del chat", r == {"sitio": "YouTube", "titulo": "Demo"}
   and g.call_args[0][0] == "/api/chat/vista-previa" and g.call_args[1]["params"] == {"url": "https://youtu.be/abc"})
for respuesta in ({}, {"error": "Solo hay vista previa…"}, {"tarjeta": "x"}):
    with mock.patch.object(ChatClient, "_get_rest", return_value=respuesta):
        ok(f"5. sin tarjeta con {respuesta!r} → None", cli.vista_previa("https://youtu.be/abc") is None)

# ── 6. Burbujas de verdad (solo con Tkinter real y pantalla) ─────────────────
if TK_REAL:
    import tkinter as tk
    try:
        raiz = tk.Tk()
    except tk.TclError:
        raiz = None
        print("(sin pantalla: se salta el pintado de burbujas)")
    if raiz is not None:
        from ui.chat_bubbles import BubbleList
        pedidas = []

        def cargar_tarjeta(url, listo):
            pedidas.append(url)
            foto = None
            if MINI is not None:
                from PIL import ImageTk
                foto = ImageTk.PhotoImage(vista_previa.imagen_de({"miniatura": MINI}), master=raiz)
            listo({"sitio": "TikTok", "titulo": "Receta de prueba", "autor": "demo", "miniatura": MINI}, foto)

        lista = BubbleList(raiz, cargar_tarjeta=cargar_tarjeta, color_enlace="#8fd3ff")
        lista.pack()
        raiz.update()
        cv = lista.agregar_burbuja("Mira https://vm.tiktok.com/ZNdemo/ ya", "10:00", False)
        raiz.update()
        colores = {cv.itemcget(i, "fill") for i in cv.find_all() if cv.type(i) == "text"}
        ok("6. el enlace se pinta en el color de los enlaces", "#8fd3ff" in colores, colores)
        enlace = [i for i in cv.find_all() if cv.type(i) == "text" and cv.itemcget(i, "fill") == "#8fd3ff"]
        ok("6. el enlace tiene su clic", bool(enlace) and bool(cv.tag_bind(enlace[0], "<Button-1>")))
        with mock.patch("webbrowser.open") as abrir:
            vista_previa.abrir("https://vm.tiktok.com/ZNdemo/")
            vista_previa.abrir("javascript:alert(1)")
        ok("6. al pulsar se abre en el navegador (y nunca javascript:)",
           abrir.call_args_list == [mock.call("https://vm.tiktok.com/ZNdemo/")], abrir.call_args_list)
        ok("6. tarjeta pedida una vez para el enlace de vídeo", pedidas == ["https://vm.tiktok.com/ZNdemo/"], pedidas)
        textos = []

        def _todos(w):
            for h in w.winfo_children():
                if isinstance(h, tk.Label):
                    textos.append(h.cget("text"))
                _todos(h)
        _todos(cv.master)
        ok("6. la tarjeta enseña el sitio, el título y el autor",
           "▶  TikTok" in textos and "Receta de prueba" in textos and "demo" in textos, textos)
        pedidas.clear()
        lista.agregar_burbuja("Sin vídeo: https://ejemplo.es", "10:01", True)
        raiz.update()
        ok("6. un enlace que no es de vídeo no lleva tarjeta", pedidas == [], pedidas)
        raiz.destroy()

print(f"\n{'Todas las comprobaciones OK.' if not fallos else str(len(fallos)) + ' fallo(s): ' + '; '.join(fallos)}")
sys.exit(1 if fallos else 0)
