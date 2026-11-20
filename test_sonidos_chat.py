"""Sonidos de los mensajes del chat (v4.18.76): uno general y otro distinto para cada chat o grupo, con tonos
incluidos, un .wav propio o silencio; guardados en config.json de este equipo (services/sonidos_chat.py).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_sonidos_chat.py   (no necesita Tkinter ni Windows)
"""
import io
import json
import os
import sys
import tempfile
import wave

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(RAIZ, "app"))
from services import sonidos_chat as sc  # noqa: E402

fallos = []
def ok(nombre, cond, det=""):
    print(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
    if not cond:
        fallos.append(nombre)

# ── Sin nada guardado suena como siempre ─────────────────────────────────────
cfg = {}
ok("sin configurar, el general es «Clásico»", sc.predeterminado(cfg) == "clasico")
ok("sin configurar, cada chat sigue al general", sc.propio(cfg, "grp:7") == sc.PREDETERMINADO)
ok("sin configurar, un chat suena «Clásico»", sc.sonido_de(cfg, "dm:ana:luis") == "clasico")
ok("config que no es un diccionario no rompe", sc.sonido_de({"chat_sonidos": "x"}, "general") == "clasico")

# ── General y por chat o grupo ───────────────────────────────────────────────
sc.fijar_predeterminado(cfg, "campanita")
ok("cambiar el general cambia los chats sin sonido propio", sc.sonido_de(cfg, "grp:7") == "campanita")
sc.fijar_canal(cfg, "grp:7", "burbuja")
sc.fijar_canal(cfg, "dm:ana:luis", sc.SILENCIO)
ok("un grupo con su sonido", sc.sonido_de(cfg, "grp:7") == "burbuja")
ok("un privado en silencio", sc.sonido_de(cfg, "dm:ana:luis") == sc.SILENCIO)
ok("los demás siguen con el general", sc.sonido_de(cfg, "general") == "campanita")
sc.fijar_predeterminado(cfg, "timbre")
ok("el sonido propio no cambia al cambiar el general", sc.sonido_de(cfg, "grp:7") == "burbuja")
sc.fijar_canal(cfg, "grp:7", sc.PREDETERMINADO)
ok("«Como el general» quita el sonido propio", "grp:7" not in cfg["chat_sonidos"]["canales"]
   and sc.sonido_de(cfg, "grp:7") == "timbre")
ok("se guarda en config.json como JSON", json.loads(json.dumps(cfg)) == cfg)

try:
    sc.fijar_canal(cfg, "grp:1", "inventado")
    ok("un sonido que no existe se rechaza", False)
except ValueError:
    ok("un sonido que no existe se rechaza", True)
try:
    sc.fijar_predeterminado(cfg, sc.PREDETERMINADO)
    ok("el general no puede ser «igual que el general»", False)
except ValueError:
    ok("el general no puede ser «igual que el general»", True)
ok("un valor estropeado en config.json se ignora",
   sc.sonido_de({"chat_sonidos": {"predeterminado": 5, "canales": {"general": "zzz"}}}, "general") == "clasico")

# ── Textos ─────────────────────────────────────────────────────────────────────
ok("nombre del silencio", sc.nombre_de(sc.SILENCIO) == "🔕 Silencio")
ok("nombre de un archivo propio (ruta de Windows)",
   sc.nombre_de(sc.valor_archivo(r"C:\Users\x\Música\pío.wav")) == "Archivo: pío.wav",
   sc.nombre_de(sc.valor_archivo(r"C:\Users\x\Música\pío.wav")))
ok("«Como el general» dice cuál es", sc.nombre_de(sc.PREDETERMINADO, "gota") == "Como el general (Gota)")
op = sc.opciones(True, "clasico")
ok("opciones: primero «igual que el general», al final silencio",
   op[0][0] == sc.PREDETERMINADO and op[-1][0] == sc.SILENCIO and len(op) == len(sc.TONOS) + 2)
ok("opciones del general sin «igual que el general»", all(v != sc.PREDETERMINADO for v, _ in sc.opciones(False)))
ok("al menos 6 tonos para elegir", len(sc.TONOS) >= 6)

# ── Tonos generados ──────────────────────────────────────────────────────────
for tono in sc.TONOS:
    datos = sc.wav_de_tono(tono)
    with wave.open(io.BytesIO(datos)) as w:
        dur = w.getnframes() / w.getframerate()
        ok(f"tono «{tono}» es un .wav válido y corto", w.getnchannels() == 1 and w.getsampwidth() == 2
           and 0.1 < dur < 1.5, f"{dur:.2f} s")

with tempfile.TemporaryDirectory() as tmp:
    original = sc.carpeta_tonos
    sc.carpeta_tonos = lambda: os.path.join(tmp, "tonos")
    try:
        r = sc.archivo_a_reproducir("campanita")
        ok("un tono se guarda una vez en la carpeta temporal", os.path.isfile(r) and r.endswith("campanita.wav"))
        ok("el silencio no reproduce nada", sc.archivo_a_reproducir(sc.SILENCIO) is None)
        propio = os.path.join(tmp, "mio.wav")
        open(propio, "wb").write(sc.wav_de_tono("gota"))
        ok("un .wav propio se reproduce tal cual", sc.archivo_a_reproducir(sc.valor_archivo(propio)) == propio)
        r = sc.archivo_a_reproducir(sc.valor_archivo(os.path.join(tmp, "borrado.wav")))
        ok("un .wav propio que ya no existe vuelve a «Clásico»", r.endswith("clasico.wav"))
        mp3 = os.path.join(tmp, "cancion.mp3")
        open(mp3, "wb").write(b"x")
        ok("un archivo que no es .wav vuelve a «Clásico»",
           sc.archivo_a_reproducir(sc.valor_archivo(mp3)).endswith("clasico.wav"))
        sc.reproducir("campanita")          # fuera de Windows no suena, pero no tiene que fallar
        ok("reproducir fuera de Windows no falla", True)
    finally:
        sc.carpeta_tonos = original

# ── Conexiones con la interfaz ───────────────────────────────────────────────
def leer(rel):
    return open(os.path.join(RAIZ, rel), encoding="utf-8").read()

ma = leer("main_agenda.py")
ok("el aviso del chat usa el sonido elegido para el canal", "_sonidos_chat.sonar_mensaje(config, canal_id)" in ma)
ok("el aviso del chat ya no usa el pitido fijo de los avisos",
   '_reproducir_sonido_aviso("aviso")\n                    # Si ya' not in ma)
ok("menú ⋮ de la ventana del chat", "Sonido de este chat" in leer("app/ui/ventana_chat.py"))
ok("botón 🔔 en la burbuja", "sonidos_chat.elegir_sonido_canal" in leer("app/ui/chat_popup.py"))
ok("botón en Administración", "Sonidos del chat" in leer("app/ui/admin.py"))
spec = leer("main.spec")
ok("módulos nuevos en hiddenimports", "'services.sonidos_chat'" in spec and "'ui.sonidos_chat'" in spec)

if fallos:
    print(f"\n{len(fallos)} FALLO(S)")
    sys.exit(1)
print("\nSonidos del chat OK")
