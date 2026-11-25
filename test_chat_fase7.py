"""Chat, fase 7 (v4.18.80): auditoría de seguridad del chat de escritorio.

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_chat_fase7.py   (no necesita Tkinter ni Windows; no se conecta a ningún servidor)
1. Los adjuntos que guarda el chat llevan la «marca de Internet» (Zone.Identifier, zona 3), como los navegadores:
   Office los abre en Vista protegida y Windows avisa antes de ejecutar nada.
2. Un host extra de adjuntos escrito sin el punto («supabase.co») no acepta «evilsupabase.co».
3. Los vídeos adjuntos se abren con el reproductor (antes solo se enseñaban en el Explorador); los programas, nunca.
"""
import os
import sys
import tempfile
from unittest import mock

RAIZ = os.path.dirname(os.path.abspath(__file__))
TMP = tempfile.mkdtemp(prefix="organizador_prueba_")
os.environ["APPDATA"] = TMP
sys.path.insert(0, os.path.join(RAIZ, "app"))

fallos = []
def ok(nombre, cond, det=""):
    print(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
    if not cond:
        fallos.append(nombre)

from utils import marca_internet as mi  # noqa: E402

# ── 1. Marca de Internet ─────────────────────────────────────────────────────
c = mi.contenido("https://usuario:clave@abc.supabase.co/storage/v1/object/public/chat/x.doc?token=1")
ok("1. zona Internet (3)", "[ZoneTransfer]\r\nZoneId=3\r\n" in c, repr(c))
ok("1. solo el sitio, sin usuario, ruta ni parámetros", "HostUrl=https://abc.supabase.co/\r\n" in c and "clave" not in c
   and "token" not in c, repr(c))
ok("1. sin URL válida, solo la zona", mi.contenido("javascript:x") == "[ZoneTransfer]\r\nZoneId=3\r\n")
archivo = os.path.join(TMP, "pedido.doc")
open(archivo, "wb").write(b"x")
ok("1. fuera de Windows no hace nada", mi.marcar(archivo, "https://abc.supabase.co/x", es_windows=False) is False
   and not os.path.exists(archivo + ":Zone.Identifier"))
# En Linux «archivo:Zone.Identifier» es un archivo normal: sirve para ver qué se escribiría en Windows
ok("1. en Windows escribe el flujo Zone.Identifier", mi.marcar(archivo, "https://abc.supabase.co/x", es_windows=True)
   and open(archivo + ":Zone.Identifier", encoding="ascii", newline="").read().startswith("[ZoneTransfer]\r\nZoneId=3"))
ok("1. si no se puede escribir, no rompe", mi.marcar(os.path.join(TMP, "no", "existe.doc"), "", es_windows=True) is False)

try:
    from services import chat_client as cc
except ImportError as e:      # socketio / requests no instalados
    cc = None
    print(f"(se omite la parte de chat_client: {e})")

if cc:
    # descargar_adjunto pone la marca al guardar en Descargas
    with mock.patch.object(cc.ChatClient, "descargar_bytes", staticmethod(lambda url: b"datos")), \
         mock.patch.object(cc.os.path, "expanduser", lambda p: TMP), \
         mock.patch.object(cc.marca_internet, "marcar") as marcar:
        ruta = cc.ChatClient.descargar_adjunto(object.__new__(cc.ChatClient), "https://abc.supabase.co/f.xls", "f.xls")
    ok("1. descargar_adjunto marca el archivo guardado", marcar.call_args and marcar.call_args[0][0] == ruta
       and os.path.exists(ruta), marcar.call_args)
    destino = os.path.join(TMP, "copia.pdf")
    with mock.patch.object(cc.ChatClient, "descargar_bytes", staticmethod(lambda url: b"%PDF")), \
         mock.patch.object(cc.marca_internet, "marcar") as marcar:
        cc.ChatClient.guardar_adjunto_como(object.__new__(cc.ChatClient), "https://abc.supabase.co/c.pdf", destino)
    ok("1. «Guardar como…» también", marcar.call_args and marcar.call_args[0][0] == destino)
    ok("1. los mensajes de voz también", "marca_internet.marcar(ruta, url)" in
       open(os.path.join(RAIZ, "app", "services", "voz.py"), encoding="utf-8").read())

    # ── 2. Hosts de adjuntos ─────────────────────────────────────────────────
    ok("2. el almacén del chat se acepta", cc.url_adjunto_permitida("https://abc.supabase.co/x.pdf"))
    ok("2. un dominio que solo termina igual, no", not cc.url_adjunto_permitida("https://evilsupabase.co/x.pdf"))
    ok("2. sin https, no", not cc.url_adjunto_permitida("http://abc.supabase.co/x.pdf"))
    with mock.patch.object(cc, "load_config", lambda: {"chat_hosts_adjuntos": ["archivos.ejemplo.dev"]}):
        ok("2. host extra sin punto: acepta el propio y sus subdominios",
           cc.url_adjunto_permitida("https://archivos.ejemplo.dev/x") and cc.url_adjunto_permitida("https://a.archivos.ejemplo.dev/x"))
        ok("2. …pero no uno que solo termina igual", not cc.url_adjunto_permitida("https://malarchivos.ejemplo.dev/x"))

    # ── 3. Qué se abre directamente ──────────────────────────────────────────
    from utils import enlaces
    ok("3. los vídeos se abren con el reproductor", enlaces.EXT_VIDEO <= cc.EXT_ABRIR_DIRECTO,
       enlaces.EXT_VIDEO - cc.EXT_ABRIR_DIRECTO)
    peligrosas = {".exe", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".hta", ".lnk", ".msi", ".scr", ".html", ".svg",
                  ".docm", ".xlsm", ".apk", ".jar", ".py", ".url"}
    ok("3. los programas y scripts nunca se abren directamente", not (peligrosas & cc.EXT_ABRIR_DIRECTO),
       peligrosas & cc.EXT_ABRIR_DIRECTO)

spec = open(os.path.join(RAIZ, "main.spec"), encoding="utf-8").read()
ok("módulo nuevo en hiddenimports", "'utils.marca_internet'" in spec)

if fallos:
    print(f"\n{len(fallos)} FALLO(S)")
    sys.exit(1)
print("\nChat fase 7 OK")
