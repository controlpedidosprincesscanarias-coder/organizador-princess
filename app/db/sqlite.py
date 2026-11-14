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

# (v4.18.58) Aquí había una lista fija (USUARIOS_INICIALES) con el usuario de Windows y el nombre real de
# cada compañero del departamento, solo para el saludo del menú. Se quitó (acordado con Víctor el 11 nov
# 2026): se quedaba desfasada y dejaba datos personales en un repositorio público. Ahora el nombre es el que
# da Control de Pedidos al entrar con la cuenta de cada uno (guardar_nombre_si_falta) o el que se pone en
# Administración → Mi Usuario. Los equipos que ya lo tenían guardado en usuarios.db no notan nada.

# ── Config JSON ───────────────────────────────────────────────────────────────

# (v4.18.38) Escritura a prueba de cortes. Antes se escribía encima del archivo: se vaciaba y luego
# se escribía, así que si el Organizador se cerraba en medio (el instalador lo cierra a la fuerza con
# taskkill /F al actualizar, un apagón…) el archivo se quedaba vacío o a medias. Al leerlo se tomaba
# como una configuración vacía sin avisar, y el siguiente guardado (p. ej. el saludo del día)
# sobrescribía la buena para siempre. Ahora:
#   - se escribe en <archivo>.tmp y se sustituye de golpe (os.replace), guardando antes la versión
#     anterior, si era válida, en <archivo>.bak;
#   - si al leer el archivo está vacío o dañado, se recupera de <archivo>.bak (o, para config.json,
#     de la copia config_backup_*.json más reciente que tenga datos), se guarda aparte el dañado
#     (<archivo>.danado_<fecha>) y queda en el log «recuperacion».
# Lo prueban las comprobaciones de test_bd_y_acceso.py.

def _leer_json(ruta, encoding=None):
    """Contenido del JSON o None si no existe, está vacío o no se puede leer."""
    try:
        with open(ruta, "r", encoding=encoding) as f:
            contenido = f.read().strip()
        return json.loads(contenido) if contenido else None
    except (OSError, ValueError):
        return None


def _escribir_json_seguro(ruta, data, encoding=None, **opciones):
    """Escribe en <ruta>.tmp, guarda la versión válida anterior en <ruta>.bak y sustituye."""
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding=encoding) as f:
        json.dump(data, f, indent=4, **opciones)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    if _leer_json(ruta, encoding):          # solo se guarda como copia una versión con datos
        try:
            import shutil
            shutil.copy2(ruta, ruta + ".bak")
        except OSError:
            pass
    os.replace(tmp, ruta)


def _recuperar_json(ruta, encoding=None, copias_extra=()):
    """Si <ruta> existe pero está vacío o dañado, lo recupera de <ruta>.bak o de `copias_extra`
    (de la más reciente a la más antigua). Devuelve los datos recuperados o None."""
    import logging
    import shutil
    from datetime import datetime
    log = logging.getLogger("recuperacion")
    candidatos = [ruta + ".bak"] + sorted(copias_extra, key=lambda r: os.path.getmtime(r) if os.path.exists(r) else 0,
                                          reverse=True)
    for copia in candidatos:
        datos = _leer_json(copia, encoding)
        if datos:
            try:
                shutil.copy2(ruta, ruta + ".danado_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
            except OSError:
                pass
            try:
                _escribir_json_seguro(ruta, datos, encoding)
            except OSError:
                pass
            log.warning("%s estaba vacío o dañado: recuperado de %s", os.path.basename(ruta), os.path.basename(copia))
            return datos
    log.error("%s estaba vacío o dañado y no hay ninguna copia con datos", os.path.basename(ruta))
    return None


def _copias_config():
    carpeta = os.path.dirname(CONFIG_FILE)
    try:
        return [os.path.join(carpeta, n) for n in os.listdir(carpeta)
                if n.startswith("config_backup_") and n.endswith(".json")]
    except OSError:
        return []


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    datos = _leer_json(CONFIG_FILE)
    if datos is None:
        datos = _recuperar_json(CONFIG_FILE, copias_extra=_copias_config())
    return datos if isinstance(datos, dict) else {}


def save_config(data):
    _escribir_json_seguro(CONFIG_FILE, data)


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
    datos = _leer_json(AGENDA_FILE, "utf-8")
    if datos is None:
        datos = _recuperar_json(AGENDA_FILE, "utf-8")
    return datos if isinstance(datos, dict) else {}


def save_agenda(data):
    # (v4.18.66) Agenda sincronizada con el usuario de Control de Pedidos: antes de guardar se anota qué ha
    # cambiado (ids, pendientes, borrados) y se avisa al hilo de sincronización para que lo suba enseguida.
    # Va aquí para que valga para cualquier ventana que guarde la agenda. Ver services/sincro_agenda.py.
    hay_cambios = False
    sincro = None
    try:
        from services import sincro_agenda as sincro
        with sincro.CERROJO:
            hay_cambios = sincro.marcar_cambios(data)
    except Exception as exc:  # noqa: BLE001 — la agenda se guarda igual aunque falle la sincronización
        import logging
        logging.getLogger("sincro_agenda").warning("marcar_cambios: %s", exc)
    _escribir_json_seguro(AGENDA_FILE, data, "utf-8", ensure_ascii=False)
    if hay_cambios and sincro is not None:
        sincro.CAMBIO_LOCAL.set()


# ── DB de usuarios (SQLite) ───────────────────────────────────────────────────

def _init_db_usuarios():
    """Crea la tabla config_usuarios si no existe (y las columnas que falten)."""
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
    # (v4.18.06) Solo se añaden las columnas que falten: antes se intentaba
    # el ALTER cada vez (esta función se llama en cada lectura) y fallaba con
    # «duplicate column name», dejando dos avisos en el log en cada llamada.
    existentes = {fila[1] for fila in cur.execute("PRAGMA table_info(config_usuarios)")}
    for col in ("bridge_user", "bridge_password"):
        if col in existentes:
            continue
        try:
            cur.execute(f"ALTER TABLE config_usuarios ADD COLUMN {col} TEXT DEFAULT ''")
        except Exception:  # noqa: BLE001
            import sys as _sys, traceback as _tb
            print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
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
    exactamente con una fila ya guardada.
    """
    _init_db_usuarios()
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    # (v4.18.58) Antes era INSERT OR REPLACE con solo dos columnas: al cambiar el nombre se borraban el
    # usuario y la contraseña de Control de Pedidos guardados (no se notaba porque Mi Usuario los vuelve a
    # guardar justo después). Ahora solo cambia el nombre.
    cur.execute(
        """INSERT INTO config_usuarios (username_win, nombre_real) VALUES (?, ?)
           ON CONFLICT(username_win) DO UPDATE SET nombre_real = excluded.nombre_real""",
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


def guardar_nombre_si_falta(username_win, nombre):
    """(v4.18.58) Guarda como nombre del usuario de Windows el que da Control de Pedidos al entrar
    (/api/bridge/login), SOLO si todavía no tiene uno propio (sin fila, vacío o igual al usuario de
    Windows). Nunca pisa un nombre puesto a mano en Mi Usuario ni toca las credenciales.
    Devuelve True si lo ha guardado."""
    uwin = (username_win or os.getenv("USERNAME", "")).lower()
    nombre = (nombre or "").strip()
    if not uwin or not nombre or nombre.lower() == uwin:
        return False
    try:
        _init_db_usuarios()
        con = sqlite3.connect(DB_FILE)
        cur = con.cursor()
        cur.execute("SELECT nombre_real FROM config_usuarios WHERE username_win = ?", (uwin,))
        fila = cur.fetchone()
        if fila and fila[0] and fila[0].strip() and fila[0].strip().lower() != uwin:
            con.close()
            return False
        cur.execute(
            """INSERT INTO config_usuarios (username_win, nombre_real) VALUES (?, ?)
               ON CONFLICT(username_win) DO UPDATE SET nombre_real = excluded.nombre_real""",
            (uwin, nombre))
        con.commit()
        con.close()
        return True
    except Exception:  # noqa: BLE001
        import sys as _sys, traceback as _tb
        print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
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
