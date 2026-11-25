"""
services/voz.py — escuchar en el Organizador los mensajes de voz del chat (v4.18.70, chat v1.8.0).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Petición de Víctor (18 nov 2026): los mensajes de voz se graban en la app del móvil; el Organizador solo los
reproduce. Un clic en la burbuja «🎤 Mensaje de voz (0:12)» lo descarga (una vez, a una carpeta temporal) y lo
reproduce con el reproductor de Windows integrado (MCI, winmm.dll: sin dependencias nuevas); otro clic lo para.
Solo suena uno a la vez, en la ventana del chat y en las burbujas. Si Windows no puede reproducirlo así, se abre
con el programa de audio predeterminado.

Sin tkinter: la ventana le pasa `despues(ms, funcion)` (win.after) para avisar de que terminó.
Pruebas en test_chat_fase5.py.
"""
import ctypes
import hashlib
import logging
import os
import sys
import tempfile
import threading

log = logging.getLogger("chat")

_ALIAS = "organizador_voz"
_EXT_PERMITIDAS = {".m4a", ".aac", ".ogg", ".opus", ".mp3"}


def es_voz(m) -> bool:
    """Mensaje de voz del chat v1.8.0: tipo «voz» con adjunto."""
    adj = (m or {}).get("adjunto") or {}
    return (m or {}).get("tipo") == "voz" and bool(adj.get("url"))


# URL → nombre de los mensajes de voz pintados (ventana y burbujas): el clic en ellos reproduce en vez de abrir
_URLS_VOZ = {}


def registrar(m) -> bool:
    """Anota un mensaje de voz pintado. True si lo es."""
    if not es_voz(m):
        return False
    adj = m["adjunto"]
    _URLS_VOZ[adj["url"]] = adj.get("nombre_archivo") or ""
    return True


def es_url_de_voz(url) -> bool:
    return url in _URLS_VOZ


def texto_duracion(ms) -> str:
    """12400 → «0:12»."""
    try:
        s = max(0, int(ms or 0)) // 1000
    except (TypeError, ValueError):
        s = 0
    return f"{s // 60}:{s % 60:02d}"


def texto_burbuja(m) -> str:
    dur = texto_duracion(((m or {}).get("adjunto") or {}).get("duracion_ms"))
    return f"🎤  Mensaje de voz ({dur})   ▶ clic para escuchar"


def ruta_cache(url: str, nombre: str = "") -> str:
    """Archivo temporal de un audio (el mismo para la misma URL: se descarga una sola vez)."""
    ext = os.path.splitext(nombre or "")[1].lower()
    if ext not in _EXT_PERMITIDAS:
        ext = ".m4a"
    carpeta = os.path.join(tempfile.gettempdir(), "OrganizadorPrincess_voz")
    os.makedirs(carpeta, exist_ok=True)
    return os.path.join(carpeta, hashlib.sha1(url.encode("utf-8")).hexdigest()[:20] + ext)


def _mci(orden: str) -> str:
    """Una orden MCI de Windows. Lanza OSError si falla."""
    buf = ctypes.create_unicode_buffer(256)
    err = ctypes.windll.winmm.mciSendStringW(orden, buf, 255, 0)
    if err:
        raise OSError(f"MCI {err}: {orden.split(' ')[0]}")
    return buf.value


class ReproductorVoz:
    """Un solo audio a la vez. `mci` se puede sustituir en las pruebas."""

    def __init__(self, mci=None, abrir_con_programa=None, es_windows=None):
        self._mci = mci or _mci
        self._abrir = abrir_con_programa or (lambda ruta: os.startfile(ruta))  # noqa: S606 (audio ya comprobado)
        self._es_windows = sys.platform.startswith("win") if es_windows is None else es_windows
        self.sonando = None            # URL del que suena
        self._lock = threading.Lock()

    def reproducir(self, url: str, ruta: str) -> str:
        """Reproduce `ruta`. Devuelve "mci" si suena dentro del Organizador, "programa" si se abrió con el
        programa predeterminado o "nada" si no se pudo."""
        self.parar()
        if not self._es_windows:
            return "nada"
        try:
            self._mci(f'open "{ruta}" type mpegvideo alias {_ALIAS}')
            self._mci(f"play {_ALIAS}")
            self.sonando = url
            return "mci"
        except OSError as e:
            log.info("Mensaje de voz: el reproductor de Windows no pudo (%s); se abre con el programa predeterminado", e)
            self.parar()
            try:
                self._abrir(ruta)
                return "programa"
            except OSError as e2:
                log.warning("Mensaje de voz: no se pudo abrir el audio: %s", e2)
                return "nada"

    def parar(self):
        if self.sonando is not None or self._es_windows:
            try:
                self._mci(f"close {_ALIAS}")
            except OSError:
                pass
        self.sonando = None

    def ha_terminado(self) -> bool:
        """True (y libera el audio) si el que sonaba ya acabó."""
        if self.sonando is None:
            return True
        try:
            modo = self._mci(f"status {_ALIAS} mode").strip().lower()
        except OSError:
            modo = "stopped"
        if modo in ("playing", "seeking", "paused"):
            return False
        self.parar()
        return True


_reproductor = None


def reproductor() -> ReproductorVoz:
    global _reproductor
    if _reproductor is None:
        _reproductor = ReproductorVoz()
    return _reproductor


def pulsar(url: str, nombre: str, descargar_bytes, despues, al_error=None, rep=None):
    """Clic en un mensaje de voz: si es el que suena, lo para; si no, lo descarga (en un hilo) y lo reproduce.
    `despues(ms, funcion)` vuelve al hilo de la interfaz (win.after); `al_error(texto)` avisa al usuario."""
    rep = rep or reproductor()
    if rep.sonando == url:
        rep.parar()
        return

    def _vigilar():
        if not rep.ha_terminado():
            despues(500, _vigilar)

    def _sonar(ruta):
        modo = rep.reproducir(url, ruta)
        if modo == "mci":
            despues(500, _vigilar)
        elif modo == "nada" and al_error:
            al_error("No se pudo reproducir el mensaje de voz en este equipo.")

    def _hilo():
        ruta = ruta_cache(url, nombre)
        try:
            if not (os.path.exists(ruta) and os.path.getsize(ruta) > 0):
                datos = descargar_bytes(url)
                with open(ruta + ".part", "wb") as f:
                    f.write(datos)
                os.replace(ruta + ".part", ruta)
                from utils import marca_internet          # (v4.18.80) por si se abre con el programa de audio
                marca_internet.marcar(ruta, url)
        except Exception as e:  # noqa: BLE001
            log.warning("Mensaje de voz: no se pudo descargar: %s", e)
            if al_error:
                despues(0, lambda e=e: al_error(f"No se pudo descargar el mensaje de voz:\n{e}"))
            return
        despues(0, lambda: _sonar(ruta))

    threading.Thread(target=_hilo, daemon=True, name="Chat-Voz").start()
