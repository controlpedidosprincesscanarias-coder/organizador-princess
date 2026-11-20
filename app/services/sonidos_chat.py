"""
services/sonidos_chat.py — sonido de los mensajes nuevos del chat, elegido por cada persona (v4.18.76).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Petición de Víctor (20 nov 2026): «que desde Herramientas o Administrador se pueda cambiar el sonido de los
mensajes, pudiendo elegir diferentes según el chat o grupo». Decisiones de Víctor (20 nov 2026):
  · cada persona elige sus sonidos (no un administrador para todos);
  · se guardan solo en este equipo (en config.json), sin sincronizar con el móvil ni tocar el servidor del chat;
  · se ofrece una lista de tonos incluidos, un archivo .wav propio del PC y «🔕 Silencio»;
  · se cambian desde el menú ⋮ de cada conversación (y 🔔 en la burbuja) y desde Administración.

En config.json:
    "chat_sonidos": {
        "predeterminado": "clasico",              # el de todos los chats que no tengan uno propio
        "canales": {"grp:7": "campanita", "dm:ana:luis": "silencio", "general": "archivo:C:\\...\\tono.wav"}
    }
Valores: el id de un tono de TONOS, "silencio" o "archivo:<ruta de un .wav>". Un chat sin entrada (o con
"predeterminado") usa el predeterminado. Sin nada guardado suena «Clásico», el doble pitido de siempre.

Los tonos incluidos se generan aquí mismo como .wav (sin archivos de sonido en el repositorio) y se guardan una
vez en la carpeta temporal. Se reproducen con winsound.PlaySound sin esperar (no bloquea la ventana). Fuera de
Windows no suena nada (las pruebas y las capturas de los manuales se hacen en Linux).

Sin tkinter. Pruebas en test_sonidos_chat.py.
"""
import io
import logging
import math
import os
import struct
import sys
import tempfile
import threading
import wave

log = logging.getLogger("chat")

CLAVE_CONFIG = "chat_sonidos"
PREDETERMINADO = "predeterminado"     # valor de un chat que sigue al sonido general
SILENCIO = "silencio"
PREFIJO_ARCHIVO = "archivo:"
TONO_INICIAL = "clasico"

_FRECUENCIA_MUESTREO = 22050

# id → (nombre en pantalla, notas). Cada nota: (frecuencia en Hz, duración en ms); frecuencia 0 = pausa.
TONOS = {
    "clasico":    ("Clásico",                [(1000, 200), (0, 40), (1000, 200)]),
    "campanita":  ("Campanita",              [(1568, 120), (2093, 380)]),
    "burbuja":    ("Burbuja",                [(660, 70), (990, 110)]),
    "ascendente": ("Ascendente",             [(880, 150), (1100, 150), (1320, 300)]),
    "suave":      ("Suave",                  [(523, 160), (659, 260)]),
    "triple":     ("Triple toque",           [(1200, 80), (0, 60), (1200, 80), (0, 60), (1200, 80)]),
    "gota":       ("Gota",                   [(1400, 60), (700, 140)]),
    "timbre":     ("Timbre",                 [(988, 220), (784, 360)]),
}

_cerrojo = threading.Lock()


# ── Lectura y escritura de la elección (config.json) ─────────────────────────

def _datos(config) -> dict:
    datos = config.get(CLAVE_CONFIG) if isinstance(config, dict) else None
    return datos if isinstance(datos, dict) else {}


def valor_valido(valor) -> bool:
    if not isinstance(valor, str):
        return False
    if valor in TONOS or valor == SILENCIO:
        return True
    return valor.startswith(PREFIJO_ARCHIVO) and len(valor) > len(PREFIJO_ARCHIVO)


def predeterminado(config) -> str:
    """Sonido general (el de los chats sin uno propio). Nunca devuelve PREDETERMINADO."""
    v = _datos(config).get("predeterminado")
    return v if valor_valido(v) else TONO_INICIAL


def propio(config, canal_id) -> str:
    """Lo elegido para ese chat o grupo, o PREDETERMINADO si sigue al general."""
    canales = _datos(config).get("canales")
    v = canales.get(str(canal_id)) if isinstance(canales, dict) else None
    return v if valor_valido(v) else PREDETERMINADO


def sonido_de(config, canal_id) -> str:
    """El sonido que tiene que sonar en ese chat: el suyo o, si no tiene, el general."""
    v = propio(config, canal_id)
    return predeterminado(config) if v == PREDETERMINADO else v


def fijar_predeterminado(config, valor) -> None:
    if not valor_valido(valor):
        raise ValueError(f"sonido no válido: {valor!r}")
    datos = dict(_datos(config))
    datos["predeterminado"] = valor
    config[CLAVE_CONFIG] = datos


def fijar_canal(config, canal_id, valor) -> None:
    """Sonido propio de un chat o grupo; PREDETERMINADO (o None) lo devuelve al general."""
    datos = dict(_datos(config))
    canales = dict(datos.get("canales") or {}) if isinstance(datos.get("canales"), dict) else {}
    if valor in (None, PREDETERMINADO):
        canales.pop(str(canal_id), None)
    elif valor_valido(valor):
        canales[str(canal_id)] = valor
    else:
        raise ValueError(f"sonido no válido: {valor!r}")
    datos["canales"] = canales
    config[CLAVE_CONFIG] = datos


def valor_archivo(ruta: str) -> str:
    return PREFIJO_ARCHIVO + str(ruta)


def ruta_archivo(valor):
    """Ruta del .wav propio de un valor "archivo:…", o None."""
    if isinstance(valor, str) and valor.startswith(PREFIJO_ARCHIVO):
        return valor[len(PREFIJO_ARCHIVO):] or None
    return None


def es_wav(ruta) -> bool:
    return str(ruta or "").lower().endswith(".wav")


def nombre_de(valor, general=None) -> str:
    """Texto para la pantalla: «Campanita», «🔕 Silencio», «Archivo: tono.wav», «Como el general (…)»."""
    if valor == PREDETERMINADO:
        return f"Como el general ({nombre_de(general)})" if general else "Como el general"
    if valor == SILENCIO:
        return "🔕 Silencio"
    if valor in TONOS:
        return TONOS[valor][0]
    ruta = ruta_archivo(valor)
    if ruta:
        return "Archivo: " + os.path.basename(ruta.replace("\\", "/"))
    return TONOS[TONO_INICIAL][0]


def opciones(con_predeterminado: bool, general=None):
    """Lista (valor, texto) para un desplegable, sin el «archivo propio» (lo añade la ventana)."""
    lista = [(PREDETERMINADO, nombre_de(PREDETERMINADO, general))] if con_predeterminado else []
    lista += [(k, v[0]) for k, v in TONOS.items()]
    lista.append((SILENCIO, nombre_de(SILENCIO)))
    return lista


# ── Generación de los tonos incluidos ─────────────────────────────────────────

def wav_de_tono(tono_id: str) -> bytes:
    """Bytes de un .wav (mono, 16 bits, 22050 Hz) con las notas del tono, con entrada y salida suaves para
    que no chasquee."""
    _, notas = TONOS[tono_id]
    muestras = bytearray()
    for frecuencia, ms in notas:
        n = int(_FRECUENCIA_MUESTREO * ms / 1000)
        rampa = max(1, min(n // 4, int(_FRECUENCIA_MUESTREO * 0.012)))
        for i in range(n):
            if frecuencia <= 0:
                v = 0.0
            else:
                env = min(1.0, i / rampa, (n - 1 - i) / rampa)
                v = 0.45 * env * math.sin(2 * math.pi * frecuencia * i / _FRECUENCIA_MUESTREO)
            muestras += struct.pack("<h", int(v * 32767))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(_FRECUENCIA_MUESTREO)
        w.writeframes(bytes(muestras))
    return buf.getvalue()


def carpeta_tonos() -> str:
    return os.path.join(tempfile.gettempdir(), "OrganizadorPrincess_sonidos")


def archivo_de_tono(tono_id: str) -> str:
    """Ruta del .wav del tono en la carpeta temporal (lo crea la primera vez)."""
    carpeta = carpeta_tonos()
    ruta = os.path.join(carpeta, f"{tono_id}.wav")
    with _cerrojo:
        if not os.path.isfile(ruta):
            os.makedirs(carpeta, exist_ok=True)
            tmp = ruta + ".tmp"
            with open(tmp, "wb") as f:
                f.write(wav_de_tono(tono_id))
            os.replace(tmp, ruta)
    return ruta


def archivo_a_reproducir(valor):
    """Qué .wav suena para un valor, o None si es silencio. Un archivo propio que ya no existe (o que no es
    .wav) vuelve al tono inicial, para que un mensaje nunca pase sin sonido por error."""
    if valor == SILENCIO:
        return None
    ruta = ruta_archivo(valor)
    if ruta:
        if es_wav(ruta) and os.path.isfile(ruta):
            return ruta
        log.warning("Sonidos del chat: no se encuentra %s; suena el tono «Clásico»", ruta)
        return archivo_de_tono(TONO_INICIAL)
    return archivo_de_tono(valor if valor in TONOS else TONO_INICIAL)


# ── Reproducción ───────────────────────────────────────────────────────────────

def reproducir(valor) -> None:
    """Hace sonar un valor (un tono, un archivo o nada si es silencio), sin bloquear."""
    def _sonar():
        try:
            ruta = archivo_a_reproducir(valor)
            if not ruta or not sys.platform.startswith("win"):
                return
            import winsound
            winsound.PlaySound(ruta, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        except Exception:  # noqa: BLE001
            log.exception("Sonidos del chat: no se pudo reproducir %r", valor)
            try:
                import winsound as _ws
                _ws.MessageBeep(_ws.MB_ICONEXCLAMATION)
            except Exception:  # noqa: BLE001
                pass
    threading.Thread(target=_sonar, daemon=True, name="Chat-Sonido").start()


def sonar_mensaje(config, canal_id) -> None:
    """Sonido de un mensaje nuevo en ese chat (lo llama poll_chat de main_agenda.py)."""
    reproducir(sonido_de(config, canal_id))
