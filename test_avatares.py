"""Fotos de perfil del chat (v4.18.28): colores e iniciales, recorte de la foto y cliente.

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_avatares.py  (en Windows o en cualquier sistema: si no hay Tkinter, se simula).
No se conecta a ningún servidor: las peticiones al chat se simulan.
"""
import base64
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

from ui import avatares  # noqa: E402
import services.chat_client as cc  # noqa: E402

fallos = []
def ok(nombre, cond, det=""):
    print(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
    if not cond:
        fallos.append(nombre)


# ── 1. Mismos colores que la app del móvil (String.hashCode de Java) ─────────
ok("1. hashCode('abc') = 96354 (igual que Java)", avatares._hash_java("abc") == 96354)
ok("1. hashCode('') = 0", avatares._hash_java("") == 0)
ok("1. hashCode con desbordamiento (negativo, como Java)",
   avatares._hash_java("polygenelubricants") == -2147483648, avatares._hash_java("polygenelubricants"))
ok("1. hashCode con acentos (UTF-16)", avatares._hash_java("é") == 233)
ok("1. color fijo y sin distinguir mayúsculas",
   avatares.color_de("Ana Demo") == avatares.color_de("ana demo") and avatares.color_de("x") in avatares.PALETA)
ok("1. floorMod: un hash negativo da un índice válido",
   avatares.color_de("polygenelubricants") == avatares.PALETA[0])

# ── 2. Iniciales ─────────────────────────────────────────────────────────────
for nombre, esperado in (("Ana Demo", "AD"), ("compras", "C"), ("", "?"), ("  ", "?"),
                         ("María José López", "MJ"), ("(hotel) Recepción", "R"), ("ñandú azul", "ÑA")):
    ok(f"2. iniciales({nombre!r}) = {esperado}", avatares.iniciales(nombre) == esperado, avatares.iniciales(nombre))

# ── 3. Imágenes en círculo ───────────────────────────────────────────────────
ini = avatares.imagen_iniciales("Ana Demo", 32)
ok("3. iniciales: 32×32 con transparencia", ini.size == (32, 32) and ini.mode == "RGBA")
ok("3. iniciales: esquina transparente y centro de color",
   ini.getpixel((0, 0))[3] == 0 and ini.getpixel((16, 4))[3] > 200)
foto = avatares.imagen_foto(Image.new("RGB", (256, 256), "#123456"), 28)
ok("3. foto: recortada en círculo", foto.size == (28, 28) and foto.getpixel((0, 0))[3] == 0
   and foto.getpixel((14, 14))[3] == 255)

# ── 4. Preparar la foto antes de subirla (como el móvil: 256 px, cuadrada, JPEG) ──
with tempfile.TemporaryDirectory() as tmp:
    ruta = os.path.join(tmp, "foto.png")
    Image.new("RGBA", (400, 300), (200, 30, 30, 255)).save(ruta)
    datos = cc.preparar_avatar(ruta)
    img = Image.open(BytesIO(datos))
    ok("4. preparar_avatar: JPEG de 256×256", img.format == "JPEG" and img.size == (256, 256), (img.format, img.size))
    ok("4. preparar_avatar: tamaño razonable (< 100 KB)", len(datos) < 100 * 1024, len(datos))

    # ── 5. Cliente: subir, quitar, mapas y evento ─────────────────────────────
    cli = cc.ChatClient()
    cli.username = "Ana.Demo"
    enviado = {}

    def _post(path, body, _reintentado=False):
        enviado.clear(); enviado.update(path=path, body=body)
        return {"ok": True, "avatar": None if body.get("borrar") else "https://x.supabase.co/a.jpg"}
    cli._post_rest = _post

    r = cli.cambiar_avatar(ruta)
    ok("5. cambiar mi foto: POST /api/chat/avatar con la imagen en base64",
       enviado.get("path") == "/api/chat/avatar"
       and Image.open(BytesIO(base64.b64decode(enviado["body"]["contenido_base64"]))).size == (256, 256)
       and "canal_id" not in enviado["body"], enviado)
    ok("5. mi foto queda guardada (mi_foto y avatar_de mío)",
       r.get("ok") and cli.mi_foto == "https://x.supabase.co/a.jpg" and cli.avatar_de("ana.demo") == cli.mi_foto)
    cli.cambiar_avatar(None)
    ok("5. quitar mi foto: borrar=True", enviado["body"] == {"borrar": True} and cli.mi_foto is None)
    cli.cambiar_avatar(ruta, canal_id="grp:abc")
    ok("5. foto de grupo: lleva canal_id y se guarda para el grupo",
       enviado["body"].get("canal_id") == "grp:abc" and cli.avatar_canal("grp:abc") == "https://x.supabase.co/a.jpg")
    cli._post_rest = lambda path, body, _reintentado=False: {}
    r = cli.cambiar_avatar(ruta)
    ok("5. servidor antiguo (sin la ruta): mensaje de error claro", not r.get("ok") and "fotos" in r.get("error", ""), r)
    r = cli.cambiar_avatar(os.path.join(tmp, "no_existe.png"))
    ok("5. imagen que no se puede leer: error sin llamar al servidor", "error" in r and not r.get("ok"))

cli._get_rest = lambda path, params=None, _reintentado=False: (
    {"usuarios": [{"username": "Compras2.Demo", "nombre": "Compradora", "avatar": "https://x.supabase.co/c2.jpg"},
                  {"username": "hotel.demo", "nombre": "Hotel"}]} if path == "/api/chat/usuarios" else
    {"canales": [{"canal_id": "grp:g1", "tipo": "grupo", "avatar": "https://x.supabase.co/g1.jpg"},
                 {"canal_id": "general", "tipo": "general"}]} if path == "/api/chat/canales" else
    {"avatar": "https://x.supabase.co/yo.jpg"} if path == "/api/chat/avatar" else {})
cli.refrescar_mapa_nombres()
ok("5. refrescar: fotos de compañeros, mía y de grupos",
   cli.avatar_de("compras2.demo") == "https://x.supabase.co/c2.jpg" and cli.avatar_de("hotel.demo") is None
   and cli.mi_foto == "https://x.supabase.co/yo.jpg" and cli.avatar_canal("grp:g1") == "https://x.supabase.co/g1.jpg")
ok("5. avatar_canal: privado → la foto del otro (deducido del canal_id)",
   cli.avatar_canal("dm:ana.demo:compras2.demo") == "https://x.supabase.co/c2.jpg")
ok("5. avatar_canal: General → sin foto", cli.avatar_canal("general") is None)

while not cli.eventos.empty():
    cli.eventos.get_nowait()
cli._on_avatar_cambiado({"clave": "user:HOTEL.demo", "avatar": "https://x.supabase.co/h.jpg"})
ev = cli.eventos.get_nowait()
ok("5. evento avatar_cambiado: actualiza la foto y avisa a la interfaz",
   ev["tipo"] == cc.EVT_AVATAR and cli.avatar_de("hotel.demo") == "https://x.supabase.co/h.jpg", ev)
cli._on_avatar_cambiado({"clave": "grp:g1", "avatar": None})
ok("5. evento de grupo con foto quitada", cli.avatar_canal("grp:g1") is None)
cli._on_avatar_cambiado({"clave": "user:ana.demo", "avatar": "https://x.supabase.co/nueva.jpg"})
ok("5. evento de mi foto (desde el móvil) actualiza mi_foto", cli.mi_foto == "https://x.supabase.co/nueva.jpg")

# ── 6. Seguridad: solo fotos del almacén de adjuntos ─────────────────────────
for url in ("http://x.supabase.co/a.jpg", "https://evil.example.com/a.jpg", "file:///etc/passwd", ""):
    try:
        cli.descargar_avatar(url)
        ok(f"6. rechaza {url!r}", False)
    except ValueError:
        ok(f"6. rechaza {url!r}", True)

if fallos:
    print(f"\n{len(fallos)} fallo(s)")
    sys.exit(1)
print("\nTodo OK")
