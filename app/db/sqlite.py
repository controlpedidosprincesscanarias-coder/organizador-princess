"""
db/sqlite.py
Gestión de rutas, configuración, agenda y base de datos de usuarios.
Extraído de main_agenda.py en Fase 2 del sprint de estabilización.
"""
import os
import json
import sqlite3

from db import dpapi   # (v4.16.9) cifrado de la contraseña del puente con DPAPI

# ── Rutas y archivos ──────────────────────────────────────────────────────────

def get_config_path():
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    folder = os.path.join(appdata, "OrganizadorPrincess")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "config.json")


CONFIG_FILE = get_config_path()
AGENDA_FILE = os.path.join(os.path.dirname(CONFIG_FILE), "agenda.json")
DB_FILE      = os.path.join(os.path.dirname(CONFIG_FILE), "usuarios.db")
VERSION_FILE = os.path.join(os.path.dirname(CONFIG_FILE), "version.json")

USUARIOS_INICIALES = {
    "dcompras":    "Jesus Curbelo",
    "comprascan":  "Victor Martin",
    "comprascan2": "Said Driss",
    "comprascan3": "David Rodriguez",
    "comprascan4": "Fran Gonzalez",
    "comprascan6": "Maria Cruz",
}  # añadir/editar usuarios desde Admin → Mi Usuario

# ── Config JSON ───────────────────────────────────────────────────────────────

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        content = f.read().strip()
        if not content:
            return {}
        return json.loads(content)


def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ── Marcador local de "Limpiar chat" (2026-08-01) ──────────────────────────────
# Guarda, por canal, la fecha/hora en que el usuario pulsó "Limpiar chat" en
# ESTE equipo. A partir de ahí, cualquier mensaje con creado_en anterior o
# igual a esa marca se considera "limpiado" y no se vuelve a mostrar al cargar
# el historial — ni en la ventana principal ni en la burbuja flotante —
# aunque el mensaje siga existiendo en el servidor para el resto de
# participantes. Es un borrado LOCAL por dispositivo (no hay acceso desde
# aquí al backend de chat para un borrado real en servidor): si el mismo
# usuario abre el chat desde otro PC, ahí seguirá viendo el histórico
# completo hasta que también pulse "Limpiar chat" en ese equipo.

def get_chat_limpiado(canal_id: str):
    """Marca de tiempo (ISO 8601 UTC, con sufijo 'Z') del último "Limpiar
    chat" para este canal en este equipo, o None si nunca se ha limpiado.

    (2026-08-01) Guarda-cláusula `if not canal_id`: al abrir un chat
    privado NUEVO (sin mensajes todavía), `_abrir_nueva_conversacion()`
    pasa canal_id=None a propósito (lo resuelve el backend en el primer
    mensaje). Sin esta guarda, todas las conversaciones nuevas sin
    resolver compartían la misma clave "null" al guardar en JSON — y
    limpiar UNA conversación nueva marcaba también como limpiadas todas
    las DEMÁS conversaciones nuevas todavía sin resolver, en vez de
    afectar solo a la abierta. Con la guarda, un canal sin resolver
    simplemente no tiene marca que aplicar (tampoco falta le hace: si no
    tiene canal_id es porque no tiene mensajes todavía)."""
    if not canal_id:
        return None
    cfg = load_config()
    return (cfg.get("chat_limpiado") or {}).get(canal_id)


def set_chat_limpiado(canal_id: str, marca_iso: str):
    """Guarda la marca de tiempo de limpieza para este canal en este
    equipo. No hace nada si canal_id todavía no está resuelto (None) —
    ver nota en get_chat_limpiado()."""
    if not canal_id:
        return
    cfg = load_config()
    marcas = cfg.get("chat_limpiado") or {}
    marcas[canal_id] = marca_iso
    cfg["chat_limpiado"] = marcas
    save_config(cfg)


def filtrar_mensajes_limpiados(canal_id: str, mensajes: list) -> list:
    """Quita de `mensajes` los que sean anteriores o iguales a la marca de
    "Limpiar chat" de este canal (si no hay ninguna, devuelve la lista tal
    cual). `creado_en` ya viene en ISO 8601 UTC desde el backend, así que
    comparar como strings funciona directamente sin parsear fechas."""
    marca = get_chat_limpiado(canal_id)
    if not marca:
        return mensajes
    return [m for m in mensajes if (m.get("creado_en") or "") > marca]


# ── Agenda JSON ───────────────────────────────────────────────────────────────

def load_agenda():
    if not os.path.exists(AGENDA_FILE):
        return {}
    try:
        with open(AGENDA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return json.loads(content) if content else {}
    except Exception:
        return {}


def save_agenda(data):
    with open(AGENDA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ── DB de usuarios (SQLite) ───────────────────────────────────────────────────

def _init_db_usuarios():
    """Crea la tabla config_usuarios si no existe y rellena los valores iniciales."""
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS config_usuarios (
            username_win    TEXT PRIMARY KEY,
            nombre_real     TEXT NOT NULL,
            bridge_user     TEXT DEFAULT '',
            bridge_password TEXT DEFAULT ''
        )
    """)
    for col in ("bridge_user", "bridge_password"):
        try:
            cur.execute(f"ALTER TABLE config_usuarios ADD COLUMN {col} TEXT DEFAULT ''")
        except Exception:  # noqa: BLE001
            import sys as _sys, traceback as _tb
            print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
    for uwin, nombre in USUARIOS_INICIALES.items():
        cur.execute(
            "INSERT OR IGNORE INTO config_usuarios (username_win, nombre_real) VALUES (?, ?)",
            (uwin, nombre)
        )
    con.commit()
    con.close()


def get_nombre_usuario():
    """Devuelve el nombre real del usuario Windows actual leyendo la DB."""
    _init_db_usuarios()
    uwin = os.getenv("USERNAME", "").lower()
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute("SELECT nombre_real FROM config_usuarios WHERE username_win = ?", (uwin,))
        row = cur.fetchone()
        con.close()
        if row:
            return row[0]
    except Exception:  # noqa: BLE001
        import sys as _sys, traceback as _tb
        print(f"[ERROR] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
    return uwin or "Usuario"


def update_nombre_usuario_db(username_win, nuevo_nombre):
    """Actualiza el nombre real de un usuario en la DB.
    Usa INSERT OR REPLACE para garantizar que la fila se crea si no existia,
    evitando el fallo silencioso del UPDATE cuando el login Windows no coincide
    exactamente con las claves de USUARIOS_INICIALES.
    """
    _init_db_usuarios()
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO config_usuarios (username_win, nombre_real) VALUES (?, ?)",
        (username_win, nuevo_nombre)
    )
    con.commit()
    con.close()


def get_bridge_credentials(username_win=None):
    _init_db_usuarios()
    if username_win is None:
        username_win = os.getenv("USERNAME", "").lower()
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute(
            "SELECT bridge_user, bridge_password FROM config_usuarios WHERE username_win = ?",
            (username_win,)
        )
        row = cur.fetchone()
        con.close()
        if row:
            usuario, guardada = row[0] or "", row[1] or ""
            # (v4.16.9) Una contraseña antigua en claro se cifra sola la
            # primera vez que se lee (solo en Windows).
            if guardada and not dpapi.esta_protegido(guardada) and dpapi.disponible():
                _migrar_bridge_password(username_win, guardada)
            return (usuario, dpapi.desproteger(guardada))
    except Exception:  # noqa: BLE001
        import sys as _sys, traceback as _tb
        print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
    return ("", "")


def _migrar_bridge_password(username_win, en_claro):
    """Sustituye la contraseña en claro por la cifrada y compacta el fichero
    (VACUUM) para que no queden restos legibles en páginas libres."""
    cifrada = dpapi.proteger(en_claro)
    if not dpapi.esta_protegido(cifrada):
        return   # DPAPI no disponible o falló: se deja como estaba
    try:
        con = sqlite3.connect(DB_FILE)
        con.execute("UPDATE config_usuarios SET bridge_password=? WHERE username_win=?",
                    (cifrada, username_win))
        con.commit()
        con.execute("VACUUM")
        con.close()
    except Exception:  # noqa: BLE001
        import sys as _sys, traceback as _tb
        print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)


def tiene_nombre_configurado():
    """Devuelve True si el usuario Windows actual tiene un nombre real configurado en la DB
    (distinto del propio username de Windows)."""
    _init_db_usuarios()
    uwin = os.getenv("USERNAME", "").lower()
    try:
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute("SELECT nombre_real FROM config_usuarios WHERE username_win = ?", (uwin,))
        row = cur.fetchone()
        con.close()
        if row and row[0] and row[0].lower() != uwin:
            return True
    except Exception:  # noqa: BLE001
        import sys as _sys, traceback as _tb
        print(f"[ERROR] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
    return False


def update_bridge_credentials(username_win, bridge_user, bridge_password):
    _init_db_usuarios()
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute(
        """INSERT INTO config_usuarios (username_win, nombre_real, bridge_user, bridge_password)
           VALUES (?, COALESCE((SELECT nombre_real FROM config_usuarios WHERE username_win=?), ?), ?, ?)
           ON CONFLICT(username_win) DO UPDATE SET
               bridge_user=excluded.bridge_user,
               bridge_password=excluded.bridge_password""",
        (username_win, username_win, username_win, bridge_user, dpapi.proteger(bridge_password))
    )
    con.commit()
    con.close()
