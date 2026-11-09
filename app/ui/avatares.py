"""
ui/avatares.py  ·  v4.18.28  ·  © VAMA 2026
============================================
Fotos de perfil del chat (personas y grupos) dibujadas en círculo. Si alguien no tiene
foto, o mientras se descarga, se pintan sus iniciales sobre un círculo de color: el mismo
color que en la app del móvil, porque se calcula igual (hashCode de Java del nombre).

Las fotos se descargan en un hilo de fondo (solo del almacén de adjuntos, ver
chat_client.descargar_avatar) y se guardan en memoria; quien pide una imagen recibe ya
las iniciales y, cuando llega la foto, se le llama `al_cargar` en el hilo de Tkinter.

Idea y desarrollo: Víctor Alejandro Martín Andrade (Central de Compras, Princess Hotels Canarias).
"""

import logging
import threading
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, ImageTk

log = logging.getLogger("chat")

# Misma paleta y mismo orden que Fotos.kt de la app Android
PALETA = ["#1F8F63", "#2F6FB5", "#B8913A", "#8E44AD", "#D35400", "#16A085", "#C0392B", "#34495E"]

_FUENTES = ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf")
_ESCALA = 4                    # se dibuja 4 veces más grande y se reduce: bordes suaves

_fotos = {}                    # url -> PIL.Image cuadrada (RGB), ya descargada
_fallidas = set()              # url que no se pudo descargar (no se reintenta en esta sesión)
_pendientes = {}               # url -> [(widget, al_cargar)] esperando la descarga
_cache_tk = {}                 # (url|iniciales, color, tamaño) -> PhotoImage (Tk necesita guardar la referencia)
_lock = threading.Lock()


def _hash_java(texto: str) -> int:
    """String.hashCode() de Java (sobre unidades UTF-16), con signo de 32 bits."""
    h = 0
    datos = texto.encode("utf-16-be")
    for i in range(0, len(datos), 2):
        h = (31 * h + ((datos[i] << 8) | datos[i + 1])) & 0xFFFFFFFF
    return h - (1 << 32) if h >= (1 << 31) else h


def color_de(clave: str) -> str:
    """Color fijo para cada nombre (el mismo en el Organizador y en el móvil)."""
    return PALETA[_hash_java((clave or "").lower()) % len(PALETA)]


def iniciales(nombre: str) -> str:
    """«Ana Demo» → «AD», «compras» → «C», «» → «?»."""
    partes = [p for p in str(nombre or "").split() if p and p[0].isalnum()]
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][:1].upper()
    return (partes[0][:1] + partes[1][:1]).upper()


def _fuente(tamano_px: int):
    for nombre in _FUENTES:
        try:
            return ImageFont.truetype(nombre, tamano_px)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=tamano_px)
    except TypeError:          # Pillow antiguo: fuente fija pequeña
        return ImageFont.load_default()


def _mascara(lado: int) -> Image.Image:
    grande = Image.new("L", (lado * _ESCALA, lado * _ESCALA), 0)
    ImageDraw.Draw(grande).ellipse((0, 0, lado * _ESCALA - 1, lado * _ESCALA - 1), fill=255)
    return grande.resize((lado, lado), Image.LANCZOS)


def imagen_iniciales(nombre: str, tamano: int, clave: str = None) -> Image.Image:
    """Círculo de color con las iniciales (RGBA, fondo transparente)."""
    lado = tamano * _ESCALA
    img = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((0, 0, lado - 1, lado - 1), fill=color_de(clave or nombre))
    texto = iniciales(nombre)
    fuente = _fuente(int(lado * (0.40 if len(texto) > 1 else 0.46)))
    try:
        d.text((lado / 2, lado / 2), texto, fill="white", font=fuente, anchor="mm")
    except (TypeError, ValueError):   # fuente sin soporte de anclaje
        d.text((lado * 0.3, lado * 0.25), texto, fill="white", font=fuente)
    return img.resize((tamano, tamano), Image.LANCZOS)


def imagen_foto(foto: Image.Image, tamano: int) -> Image.Image:
    """La foto (cuadrada) recortada en círculo (RGBA)."""
    img = foto.convert("RGB").resize((tamano, tamano), Image.LANCZOS).convert("RGBA")
    img.putalpha(_mascara(tamano))
    return img


def _descargar(url):
    from services.chat_client import get_chat_client
    foto = None
    try:
        datos = get_chat_client().descargar_avatar(url)
        foto = Image.open(BytesIO(datos))
        foto.load()
        foto = foto.convert("RGB")
    except Exception as exc:  # noqa: BLE001 — sin foto se quedan las iniciales
        log.warning("No se pudo descargar una foto de perfil: %s", exc)
    with _lock:
        if foto is not None:
            _fotos[url] = foto
        else:
            _fallidas.add(url)
        esperando = _pendientes.pop(url, [])
    if foto is None:
        return
    for widget, al_cargar in esperando:
        try:
            if widget.winfo_exists():
                widget.after(0, al_cargar)
        except Exception:  # noqa: BLE001 — la ventana se cerró mientras tanto
            pass


def imagen(widget, url, nombre, tamano=32, clave=None, al_cargar=None):
    """PhotoImage para mostrar ya: la foto si está descargada; si no, las iniciales.
    Si hay que descargarla, se hace en segundo plano y luego se llama `al_cargar()`
    en el hilo de Tkinter (a través de `widget`) para que se vuelva a pintar."""
    from services.chat_client import url_adjunto_permitida
    url = url if url and url_adjunto_permitida(url) else None
    with _lock:
        foto = _fotos.get(url) if url else None
        descargar = bool(url) and foto is None and url not in _fallidas
        if descargar:
            ya_en_marcha = url in _pendientes
            if al_cargar is not None:
                _pendientes.setdefault(url, []).append((widget, al_cargar))
            else:
                _pendientes.setdefault(url, [])
            descargar = not ya_en_marcha
    if descargar:
        threading.Thread(target=_descargar, args=(url,), daemon=True, name="Chat-Foto").start()
    if foto is not None:
        k = (url, tamano)
        if k not in _cache_tk:
            _cache_tk[k] = ImageTk.PhotoImage(imagen_foto(foto, tamano), master=widget)
        return _cache_tk[k]
    k = (iniciales(nombre), color_de(clave or nombre), tamano)
    if k not in _cache_tk:
        _cache_tk[k] = ImageTk.PhotoImage(imagen_iniciales(nombre, tamano, clave), master=widget)
    return _cache_tk[k]


def imagen_grupo(widget, url, nombre, tamano=32, canal_id=None, al_cargar=None):
    """Igual que imagen(), para un grupo (el color sale del canal, no del nombre)."""
    return imagen(widget, url, nombre or "Grupo", tamano, clave=canal_id or nombre, al_cargar=al_cargar)


def imagen_general(widget, tamano=32):
    """Icono del chat General (sin foto): círculo azul con «G»."""
    k = ("general", tamano)
    if k not in _cache_tk:
        lado = tamano * _ESCALA
        img = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse((0, 0, lado - 1, lado - 1), fill="#134e6f")
        try:
            d.text((lado / 2, lado / 2), "G", fill="white", font=_fuente(int(lado * 0.46)), anchor="mm")
        except (TypeError, ValueError):
            d.text((lado * 0.3, lado * 0.25), "G", fill="white", font=_fuente(int(lado * 0.46)))
        _cache_tk[k] = ImageTk.PhotoImage(img.resize((tamano, tamano), Image.LANCZOS), master=widget)
    return _cache_tk[k]


def olvidar(url):
    """Tras un cambio de foto: la URL nueva se descargará de nuevo (por si se reutiliza)."""
    with _lock:
        _fotos.pop(url, None)
        _fallidas.discard(url)
    for k in [k for k in _cache_tk if k[0] == url]:
        _cache_tk.pop(k, None)
