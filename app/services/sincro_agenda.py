"""
services/sincro_agenda.py — agenda sincronizada con el usuario de Control de Pedidos (v4.18.66).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Petición de Víctor (13 nov 2026): «si pongo el mismo usuario en diferentes pc, siempre tenga mi agenda y
calendario sincronizado». Control de Pedidos (v12.34.36) guarda la agenda de cada usuario
(GET/POST /api/bridge/agenda, misma sesión que el resto del bridge).

Lógica pura, sin Tk ni red (la red está en pedidos_agenda_bridge.py, _loop_agenda). Pruebas: test_sincro_agenda.py.

Cómo se guarda en agenda.json (el formato de siempre, con unas claves internas más):
- Cada aviso, vacación y festivo lleva `_sid` (id estable), `_cambiado` (cuándo se cambió, ISO UTC) y `_h`
  (huella de su contenido). `_pendiente` = falta subirlo; `_nuevo` = nunca ha llegado al servidor.
- `agenda["_sincro"]`: `version` (lo último recibido del servidor), `usuario` (de quién es esta agenda),
  `conocidos` ({sid: tipo} en el último guardado, para notar los borrados) y `borrados` pendientes de subir.
- Los avisos de Control de Pedidos (`_bridge_gestionado`) no se sincronizan: son de cada sesión.

marcar_cambios() se llama en cada save_agenda (db/sqlite.py): así cualquier ventana que guarde (Agenda,
Vacaciones, Festivos, «Desactivar evento» del popup…) queda anotada sin tocar su código.

Reglas: gana el cambio más reciente (también en el servidor); los borrados se propagan; sin red se sigue
trabajando con la copia local y lo pendiente se sube al volver. La primera vez se fusiona: un elemento que
aún no está en el servidor y es idéntico a uno que llega de otro PC se queda con el del servidor, en vez de
duplicarse.
"""
import hashlib
import json
import threading
import uuid
from datetime import datetime, timezone

LISTAS = {"avisos": "aviso", "vacaciones": "vacacion", "festivos": "festivo"}
TIPO_A_LISTA = {t: l for l, t in LISTAS.items()}
CLAVE_ESTADO = "_sincro"
MAX_POR_ENVIO = 500

# Un solo cerrojo para marcar (al guardar, desde cualquier hilo) y aplicar lo del servidor.
CERROJO = threading.RLock()
# Se activa al guardar un cambio local: el hilo de sincronización lo sube a los pocos segundos.
CAMBIO_LOCAL = threading.Event()


def ahora_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dt(valor) -> datetime:
    """ISO → datetime con zona; lo que no se entiende cuenta como lo más antiguo."""
    try:
        texto = str(valor or "").strip()
        if texto.endswith("Z"):
            texto = texto[:-1] + "+00:00"
        dt = datetime.fromisoformat(texto)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime.min.replace(tzinfo=timezone.utc)


def sincronizable(item) -> bool:
    return isinstance(item, dict) and not item.get("_bridge_gestionado")


def contenido(item: dict) -> dict:
    """Lo que se sube: el elemento sin claves internas (las que empiezan por «_»)."""
    return {k: v for k, v in item.items() if not str(k).startswith("_")}


def huella(item: dict) -> str:
    texto = json.dumps(contenido(item), sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()


def estado(data: dict) -> dict:
    est = data.get(CLAVE_ESTADO)
    if not isinstance(est, dict):
        est = {}
        data[CLAVE_ESTADO] = est
    est.setdefault("version", 0)
    est.setdefault("usuario", "")
    est.setdefault("conocidos", {})
    est.setdefault("borrados", {})
    return est


def _elementos(data: dict):
    """(lista, tipo, índice, item) de cada elemento sincronizable."""
    for lista, tipo in LISTAS.items():
        items = data.get(lista)
        if not isinstance(items, list):
            continue
        for i, item in enumerate(items):
            if sincronizable(item):
                yield lista, tipo, i, item


def _buscar(data: dict, sid: str):
    for lista, _tipo, i, item in _elementos(data):
        if item.get("_sid") == sid:
            return lista, i, item
    return None, None, None


def conservar_identidad(original: dict, editado: dict) -> dict:
    """Al editar un elemento, las ventanas crean un dict nuevo: que siga siendo el mismo (mismo `_sid`)."""
    if isinstance(original, dict):
        for k in ("_sid", "_nuevo"):
            if k in original:
                editado[k] = original[k]
    return editado


def marcar_cambios(data: dict, ahora: str = None) -> bool:
    """Antes de guardar: id a lo nuevo, `_pendiente` a lo cambiado y anota los borrados. True si hay algo."""
    if not isinstance(data, dict):
        return False
    if CLAVE_ESTADO not in data and not any(True for _ in _elementos(data)):
        return False          # agenda vacía y nunca sincronizada: se guarda tal cual
    ahora = ahora or ahora_iso()
    est = estado(data)
    hay = False
    presentes = {}
    for _lista, tipo, _i, item in _elementos(data):
        if not item.get("_sid") or item["_sid"] in presentes:
            item["_sid"] = uuid.uuid4().hex
            item["_nuevo"] = True
        h = huella(item)
        if item.get("_h") != h:
            item["_h"] = h
            item["_cambiado"] = ahora
            item["_pendiente"] = True
            hay = True
        presentes[item["_sid"]] = tipo
    for sid, tipo in est["conocidos"].items():
        if sid not in presentes and sid not in est["borrados"]:
            est["borrados"][sid] = {"tipo": tipo, "cambiado_en": ahora}
            hay = True
    for sid in list(est["borrados"]):
        if sid in presentes:
            del est["borrados"][sid]
    est["conocidos"] = presentes
    return hay


def hay_pendientes(data: dict) -> bool:
    est = estado(data)
    return bool(est["borrados"]) or any(item.get("_pendiente") for *_x, item in _elementos(data))


def pendientes(data: dict) -> list:
    """Lo que hay que subir (POST /api/bridge/agenda)."""
    est = estado(data)
    salida = []
    for _lista, tipo, _i, item in _elementos(data):
        if item.get("_pendiente"):
            salida.append({"sid": item["_sid"], "tipo": tipo, "datos": contenido(item),
                           "cambiado_en": item.get("_cambiado") or ahora_iso()})
    for sid, b in est["borrados"].items():
        salida.append({"sid": sid, "tipo": b.get("tipo", "aviso"), "borrado": True,
                       "cambiado_en": b.get("cambiado_en") or ahora_iso()})
    return salida


def cambiar_usuario(data: dict, usuario: str) -> bool:
    """La agenda es de un usuario de Control de Pedidos. Si en este PC entra otro, se quita lo que vino del
    servidor del anterior (allí sigue guardado) y se empieza de cero con el nuevo; lo que nunca llegó a subirse
    se queda y se sube al nuevo. Devuelve True si ha cambiado algo de la agenda."""
    usuario = (usuario or "").strip().lower()
    est = estado(data)
    if not usuario or est["usuario"] == usuario:
        return False
    anterior = est["usuario"]
    est["usuario"] = usuario
    est["version"] = 0
    if not anterior:
        return False          # primera sincronización de este PC: se fusiona lo local con lo del servidor
    for lista in LISTAS:
        items = data.get(lista)
        if isinstance(items, list):
            data[lista] = [it for it in items if not sincronizable(it) or it.get("_nuevo")]
    est["borrados"] = {}
    est["conocidos"] = {it["_sid"]: tipo for _l, tipo, _i, it in _elementos(data) if it.get("_sid")}
    return True


def aplicar_remotos(data: dict, elementos: list) -> bool:
    """Aplica lo que llega del servidor (GET, o los rechazados de un POST). Si el cambio local pendiente es
    más reciente, se conserva el local (se subirá). Devuelve True si ha cambiado la agenda."""
    est = estado(data)
    cambio = False
    for e in elementos or []:
        sid, tipo = e.get("sid"), e.get("tipo")
        lista = TIPO_A_LISTA.get(tipo)
        if not sid or not lista:
            continue
        remoto_dt = _dt(e.get("cambiado_en"))
        borrado_local = est["borrados"].get(sid)
        if borrado_local:
            if _dt(borrado_local.get("cambiado_en")) > remoto_dt:
                continue                              # lo borré yo después: gana mi borrado
            del est["borrados"][sid]
        l_actual, i_actual, local = _buscar(data, sid)
        if local is not None and local.get("_pendiente") and _dt(local.get("_cambiado")) > remoto_dt:
            continue                                  # mi cambio es más reciente: se subirá
        if e.get("borrado"):
            if local is not None:
                data[l_actual].pop(i_actual)
                cambio = True
            est["conocidos"].pop(sid, None)
            continue
        datos = e.get("datos") if isinstance(e.get("datos"), dict) else {}
        nuevo = dict(contenido(datos))
        nuevo["_sid"] = sid
        nuevo["_cambiado"] = e.get("cambiado_en") or ahora_iso()
        nuevo["_h"] = huella(nuevo)
        if local is not None:
            if l_actual == lista:
                data[lista][i_actual] = nuevo
            else:
                data[l_actual].pop(i_actual)
                data.setdefault(lista, []).append(nuevo)
            cambio = cambio or huella(local) != nuevo["_h"] or l_actual != lista
        else:
            items = data.setdefault(lista, [])
            # Primera vez en varios PC: si aquí hay uno idéntico que aún no está en el servidor, es el mismo.
            gemelo = next((i for i, it in enumerate(items) if sincronizable(it) and it.get("_nuevo")
                           and it.get("_sid") != sid and huella(it) == nuevo["_h"]), None)
            if gemelo is not None:
                est["conocidos"].pop(items[gemelo].get("_sid"), None)
                items[gemelo] = nuevo
            else:
                items.append(nuevo)
                cambio = True
        est["conocidos"][sid] = tipo
    return cambio


def aplicar_respuesta(data: dict, enviados: list, respuesta: dict) -> bool:
    """Tras el POST: lo aceptado deja de estar pendiente (si no se ha vuelto a cambiar mientras tanto) y lo
    rechazado (el servidor tenía algo igual o más nuevo) se aplica. Devuelve True si cambia la agenda."""
    est = estado(data)
    por_sid = {e["sid"]: e for e in enviados}
    for a in (respuesta or {}).get("aceptados", []):
        e = por_sid.get(a.get("sid"))
        if not e:
            continue
        if e.get("borrado"):
            b = est["borrados"].get(e["sid"])
            if b and b.get("cambiado_en") == e["cambiado_en"]:
                del est["borrados"][e["sid"]]
            continue
        _l, _i, local = _buscar(data, e["sid"])
        if local is not None:
            local.pop("_nuevo", None)
            if local.get("_cambiado") == e["cambiado_en"]:
                local.pop("_pendiente", None)
    rechazados = (respuesta or {}).get("rechazados", [])
    for r in rechazados:
        _l, _i, local = _buscar(data, r.get("sid"))
        if local is not None:
            local.pop("_nuevo", None)
            if local.get("_cambiado") == (por_sid.get(r.get("sid")) or {}).get("cambiado_en"):
                local.pop("_pendiente", None)    # no se ha tocado desde el envío: manda el servidor
    return aplicar_remotos(data, rechazados)


def preparar_importacion(datos: dict, actual: dict) -> dict:
    """«Importar agenda» reemplaza la agenda: lo importado se sube como cambio nuevo y lo que había y no está
    en el archivo se borra también en los otros PC. Se mantiene el estado de sincronización actual."""
    datos = dict(datos) if isinstance(datos, dict) else {}
    datos.pop(CLAVE_ESTADO, None)
    for _lista, _tipo, _i, item in _elementos(datos):
        for k in ("_h", "_pendiente"):
            item.pop(k, None)
    est_actual = (actual or {}).get(CLAVE_ESTADO)
    if isinstance(est_actual, dict):
        datos[CLAVE_ESTADO] = json.loads(json.dumps(est_actual))
    return datos


def resumen(data: dict) -> str:
    """Texto corto para el registro: cuántos elementos hay y cuántos faltan por subir."""
    n = sum(1 for _ in _elementos(data))
    p = len(pendientes(data))
    return f"{n} elemento(s), {p} pendiente(s) de subir, versión {estado(data)['version']}"


# ── Ayudas para las ventanas (Agenda, Vacaciones, Festivos, Calendario) ──────────────────────────────────
# Las listas se pintan con su posición (idx). Si mientras está abierta llega un cambio de otro PC, la posición
# puede no ser ya la misma: por eso se busca el elemento por su id al guardar o borrar, y las ventanas
# abiertas se vuelven a pintar en cuanto se aplica lo recibido (refrescar_ventanas, en el hilo de Tk).

def _posicion(items: list, original, idx=None):
    sid = original.get("_sid") if isinstance(original, dict) else None
    for i, it in enumerate(items):
        if it is original or (sid and isinstance(it, dict) and it.get("_sid") == sid):
            return i
    if sid is None and idx is not None and 0 <= idx < len(items):
        return idx
    return None


def reemplazar(items: list, original: dict, editado: dict, idx=None) -> dict:
    """Guarda `editado` en el sitio de `original` (buscado por id). Si otro PC lo borró mientras se editaba,
    se añade de nuevo: lo último que ha hecho el usuario es editarlo."""
    conservar_identidad(original, editado)
    pos = _posicion(items, original, idx)
    if pos is None:
        items.append(editado)
    else:
        items[pos] = editado
    return editado


def quitar(items: list, original) -> bool:
    """Borra `original` (buscado por id). False si ya no estaba."""
    pos = _posicion(items, original)
    if pos is None:
        return False
    items.pop(pos)
    return True


_refrescos = []   # [(ventana, función)]


def registrar_refresco(ventana, funcion):
    """La ventana se vuelve a pintar con `funcion()` cuando llegan cambios de otro PC (mientras exista)."""
    _refrescos.append((ventana, funcion))


def refrescar_ventanas():
    """Llamar en el hilo de Tk. Quita las ventanas ya cerradas."""
    vivas = []
    for ventana, funcion in list(_refrescos):
        try:
            if ventana is not None and not ventana.winfo_exists():
                continue
            funcion()
            vivas.append((ventana, funcion))
        except Exception:  # noqa: BLE001 — ventana a medio cerrar
            continue
    _refrescos[:] = vivas


def actual(items: list, original):
    """El elemento tal como está ahora en la lista (otro PC puede haberlo cambiado), o None si ya no está."""
    pos = _posicion(items, original)
    return items[pos] if pos is not None else None
