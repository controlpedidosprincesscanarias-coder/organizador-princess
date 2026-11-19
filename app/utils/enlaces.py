"""utils/enlaces.py — enlaces dentro de los mensajes del chat (v4.18.74, chat v1.9.0).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Petición de Víctor (19 nov 2026): «¿se podría poner reproductor de vídeos o vídeos web si se envían?», con un
enlace de TikTok de ejemplo, «y en el chat de escritorio igual». Los enlaces se pueden pulsar (se abren en el
navegador) y, bajo un enlace de TikTok, YouTube o Instagram, sale una tarjeta con la miniatura, el título y el
autor que prepara el servidor del chat (GET /api/chat/vista-previa). Mismas reglas que el servidor
(chat/vista_previa.py) y la app del móvil (datos/Enlaces.kt).

Sin tkinter. Pruebas en test_chat_fase6.py.
"""
import os
import re
from urllib.parse import urlsplit

_RE_ENLACE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_FINALES = ".,;:!?)]}»"

SITIOS = {
    "tiktok": ("TikTok", ("tiktok.com",)),
    "youtube": ("YouTube", ("youtube.com", "youtu.be", "youtube-nocookie.com")),
    "instagram": ("Instagram", ("instagram.com", "instagr.am")),
}

EXT_VIDEO = {".mp4", ".m4v", ".mov", ".3gp", ".webm", ".mkv", ".avi", ".wmv"}


def _host(url):
    try:
        p = urlsplit(url)
    except ValueError:
        return None
    if p.scheme.lower() not in ("http", "https") or p.username or p.password:
        return None
    return (p.hostname or "").lower().rstrip(".") or None


def abrible(url) -> bool:
    """Solo se abren en el navegador direcciones http/https sin usuario ni contraseña."""
    return _host(str(url or "")) is not None


def trozos(texto):
    """[(texto, url | None)]: el texto partido en trozos normales y enlaces (sin la puntuación final pegada)."""
    texto = str(texto or "")
    salida, desde = [], 0
    for m in _RE_ENLACE.finditer(texto):
        url = m.group(0).rstrip(_FINALES)
        if not url or not abrible(url):
            continue
        if m.start() > desde:
            salida.append((texto[desde:m.start()], None))
        salida.append((url, url))
        desde = m.start() + len(url)
    if desde < len(texto):
        salida.append((texto[desde:], None))
    return salida


def sitio_de_video(url):
    """«tiktok», «youtube» o «instagram» si es un enlace https de esos sitios; si no, None."""
    if not str(url or "").lower().startswith("https://"):
        return None
    host = _host(url)
    if not host:
        return None
    for clave, (_nombre, hosts) in SITIOS.items():
        if any(host == h or host.endswith("." + h) for h in hosts):
            return clave
    return None


def nombre_sitio(url) -> str:
    clave = sitio_de_video(url)
    return SITIOS[clave][0] if clave else "Vídeo"


def primer_video(texto):
    """El primer enlace de vídeo del mensaje (solo uno lleva tarjeta, como en el móvil)."""
    return next((u for _t, u in trozos(texto) if u and sitio_de_video(u)), None)


def es_video(mensaje) -> bool:
    """Vídeo adjunto (no un mensaje de voz): tipo de archivo video/* o extensión de vídeo."""
    m = mensaje or {}
    adj = m.get("adjunto") or {}
    if not adj.get("url") or m.get("tipo") == "voz":
        return False
    mime = str(adj.get("mime_type") or "").lower()
    ext = os.path.splitext(str(adj.get("nombre_archivo") or ""))[1].lower()
    return mime.startswith("video/") or ext in EXT_VIDEO
