"""Base de datos local y acceso a Administración (v4.18.06).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_bd_y_acceso.py   (usa una carpeta de datos temporal; no toca la del equipo)
1. _init_db_usuarios no repite el ALTER TABLE (antes dejaba «duplicate column name» en cada lectura).
2. existe_en_plataforma codifica el usuario de Windows (antes, con un espacio, la petición ni salía).
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
cols = {f[1] for f in sqlite3.connect(bd.DB_FILE).execute("PRAGMA table_info(config_usuarios)")}
ok("la tabla tiene las columnas del bridge", {"bridge_user", "bridge_password"} <= cols, cols)

# Base antigua sin las columnas: se añaden
os.remove(bd.DB_FILE)
con = sqlite3.connect(bd.DB_FILE)
con.execute("CREATE TABLE config_usuarios (username_win TEXT PRIMARY KEY, nombre_real TEXT NOT NULL)")
con.commit(); con.close()
with contextlib.redirect_stderr(io.StringIO()):
    bd._init_db_usuarios()
cols = {f[1] for f in sqlite3.connect(bd.DB_FILE).execute("PRAGMA table_info(config_usuarios)")}
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

print(f"\n{'Todas las comprobaciones OK.' if not fallos else str(len(fallos)) + ' fallo(s)'}")
sys.exit(1 if fallos else 0)
