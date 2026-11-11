"""Base de datos local y acceso a Administración (v4.18.06).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_bd_y_acceso.py   (usa una carpeta de datos temporal; no toca la del equipo)
1. _init_db_usuarios no repite el ALTER TABLE (antes dejaba «duplicate column name» en cada lectura).
2. existe_en_plataforma codifica el usuario de Windows (antes, con un espacio, la petición ni salía).
3. (v4.18.38) config.json y agenda.json a prueba de cortes: escritura segura con copia .bak y
   recuperación si al arrancar están vacíos o dañados (antes se perdía toda la configuración).
4. (v4.18.42) El chat solo se abre si hay cuenta de Control de Pedidos guardada (Mi Usuario).
"""
import contextlib
import io
import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.abspath(__file__))
TMP = tempfile.mkdtemp(prefix="organizador_prueba_")
os.environ["APPDATA"] = TMP
os.environ["LOCALAPPDATA"] = TMP
sys.path.insert(0, os.path.join(RAIZ, "app"))
sys.path.insert(0, RAIZ)

fallos = []
def ok(nombre, cond, det=""):
    print(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
    if not cond:
        fallos.append(nombre)

from db import sqlite as bd  # noqa: E402
ok("la base de datos de prueba está en la carpeta temporal", bd.DB_FILE.startswith(TMP), bd.DB_FILE)
err = io.StringIO()
with contextlib.redirect_stderr(err):
    bd._init_db_usuarios(); bd._init_db_usuarios()
    bd.update_bridge_credentials("usuario prueba", "usuario prueba", "x")
    bd.get_bridge_credentials("usuario prueba")
ok("sin avisos «duplicate column» al inicializar varias veces", "duplicate column" not in err.getvalue(), err.getvalue()[:200])
import sqlite3  # noqa: E402


def columnas():
    """Columnas de config_usuarios, cerrando la conexión (en Windows un archivo abierto no se puede borrar)."""
    con = sqlite3.connect(bd.DB_FILE)
    try:
        return {f[1] for f in con.execute("PRAGMA table_info(config_usuarios)")}
    finally:
        con.close()


cols = columnas()
ok("la tabla tiene las columnas del bridge", {"bridge_user", "bridge_password"} <= cols, cols)

# Base antigua sin las columnas: se añaden
os.remove(bd.DB_FILE)
con = sqlite3.connect(bd.DB_FILE)
con.execute("CREATE TABLE config_usuarios (username_win TEXT PRIMARY KEY, nombre_real TEXT NOT NULL)")
con.commit(); con.close()
with contextlib.redirect_stderr(io.StringIO()):
    bd._init_db_usuarios()
cols = columnas()
ok("en una base antigua se añaden las columnas que faltan", {"bridge_user", "bridge_password"} <= cols, cols)

try:
    from services import admin_auth  # noqa: E402
except ImportError as e:  # cryptography no instalada
    admin_auth = None
    print(f"(se omite la parte de admin_auth: {e})")
if admin_auth:
    rutas = []
    admin_auth._request_json = lambda path, data=None, method=None: rutas.append(path) or {"existe": True}
    r = admin_auth.existe_en_plataforma("usuario prueba")
    ok("existe_en_plataforma con espacio en el usuario: la consulta sale codificada",
       r is True and rutas and rutas[-1].endswith("usuario_windows=usuario%20prueba"), rutas)
    admin_auth.existe_en_plataforma("muñoz")
    ok("…y con «ñ»", rutas[-1].endswith("usuario_windows=mu%C3%B1oz"), rutas)

# ── 3. config.json y agenda.json a prueba de cortes (v4.18.38) ──────────────────
import json as _json  # noqa: E402
import logging as _logging  # noqa: E402
_logging.disable(_logging.CRITICAL)
bd.save_config({"usuario": "usuario prueba", "accesos": [1, 2]})
bd.save_config({"usuario": "usuario prueba", "accesos": [1, 2, 3]})
ok("guardar config deja copia .bak de la versión anterior",
   _json.load(open(bd.CONFIG_FILE + ".bak")) == {"usuario": "usuario prueba", "accesos": [1, 2]})
ok("…y no deja el .tmp", not os.path.exists(bd.CONFIG_FILE + ".tmp"))
open(bd.CONFIG_FILE, "w").close()                       # se cortó a mitad de escritura: vacío
ok("config.json vacío: se recupera de la copia .bak", bd.load_config() == {"usuario": "usuario prueba", "accesos": [1, 2]},
   bd.load_config())
ok("…se reescribe ya bien y se guarda el dañado aparte",
   _json.load(open(bd.CONFIG_FILE))["usuario"] == "usuario prueba"
   and any(n.startswith("config.json.danado_") for n in os.listdir(TMP + "/OrganizadorPrincess")))
with open(bd.CONFIG_FILE, "w") as f:
    f.write('{"usuario": "usu')                         # a medias
os.remove(bd.CONFIG_FILE + ".bak")
with open(os.path.join(os.path.dirname(bd.CONFIG_FILE), "config_backup_v4.18.34_20261111_150000.json"), "w") as f:
    _json.dump({"usuario": "de la copia de actualizar"}, f)
ok("config.json a medias y sin .bak: se recupera de la copia de la última actualización",
   bd.load_config() == {"usuario": "de la copia de actualizar"}, bd.load_config())
bd.save_config({})
ok("una configuración vacía guardada a propósito («desde cero») se respeta", bd.load_config() == {})
bd.save_agenda({"2026-11-11": [{"texto": "Reunión ñ"}]})
bd.save_agenda({"2026-11-12": [{"texto": "Otra"}]})
with open(bd.AGENDA_FILE, "w", encoding="utf-8") as f:
    f.write("{")
ok("agenda.json dañado: se recupera de la copia .bak", bd.load_agenda() == {"2026-11-11": [{"texto": "Reunión ñ"}]},
   bd.load_agenda())
bd.save_agenda({})
ok("una agenda vaciada a propósito se respeta", bd.load_agenda() == {})
_logging.disable(_logging.NOTSET)

# ── 4. El chat necesita la cuenta de Control de Pedidos (v4.18.42) ──────────────
try:
    from services import chat_client  # noqa: E402
except ImportError as e:  # socketio/requests no instalados
    chat_client = None
    print(f"(se omite la parte del chat: {e})")
if chat_client:
    ok("sin cuenta guardada, el chat no se abre", chat_client.cuenta_chat_configurada("sin cuenta") is False)
    bd.update_bridge_credentials("con cuenta", "usuario prueba", "x")
    ok("con usuario y contraseña guardados, sí", chat_client.cuenta_chat_configurada("con cuenta") is True)
    bd.update_bridge_credentials("solo usuario", "usuario prueba", "")
    ok("con usuario pero sin contraseña, no", chat_client.cuenta_chat_configurada("solo usuario") is False)

print(f"\n{'Todas las comprobaciones OK.' if not fallos else str(len(fallos)) + ' fallo(s)'}")
sys.exit(1 if fallos else 0)
