"""
db/dpapi.py  ·  v1.0 (v4.16.9)
Cifrado de secretos locales con DPAPI de Windows (CryptProtectData).

Solo el MISMO usuario de Windows, en el MISMO equipo, puede descifrar lo que
se cifra aquí: no hay clave que guardar junto a los datos (a diferencia de
Fernet + admin_auth.key) y no hace falta ninguna dependencia extra, solo
ctypes. Se usa para la contraseña de Control de Pedidos guardada en
usuarios.db (config_usuarios.bridge_password).

Formato guardado: "dpapi1:" + base64(blob DPAPI). Un valor SIN ese prefijo es
una contraseña antigua en claro; db.sqlite la migra sola al leerla.

Comportamiento ante fallos (a propósito tolerante, para no dejar la app sin
avisos si DPAPI falla en algún equipo):
  - proteger() falla o no hay Windows -> devuelve el texto tal cual.
  - desproteger() falla (p. ej. la carpeta de datos se copió a otro PC o a
    otro usuario de Windows) -> devuelve "" y el usuario tiene que volver a
    escribir su contraseña en Admin -> Mi Usuario.
"""
import base64
import logging
import sys

log = logging.getLogger(__name__)

PREFIJO = "dpapi1:"


def disponible() -> bool:
    return sys.platform.startswith("win")


def _crypt(datos: bytes, cifrar: bool) -> bytes:
    import ctypes
    from ctypes import wintypes

    class _BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    fn = crypt32.CryptProtectData if cifrar else crypt32.CryptUnprotectData
    fn.argtypes = [ctypes.POINTER(_BLOB), ctypes.c_void_p, ctypes.POINTER(_BLOB),
                   ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                   ctypes.POINTER(_BLOB)]
    fn.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p

    buf = ctypes.create_string_buffer(datos, len(datos))
    entrada = _BLOB(len(datos), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    salida = _BLOB()
    if not fn(ctypes.byref(entrada), None, None, None, None, 0, ctypes.byref(salida)):
        raise OSError(ctypes.get_last_error(), "DPAPI falló")
    try:
        return ctypes.string_at(salida.pbData, salida.cbData)
    finally:
        kernel32.LocalFree(ctypes.cast(salida.pbData, ctypes.c_void_p))


def esta_protegido(valor: str) -> bool:
    return bool(valor) and valor.startswith(PREFIJO)


def proteger(texto: str) -> str:
    if not texto or esta_protegido(texto) or not disponible():
        return texto
    try:
        return PREFIJO + base64.b64encode(_crypt(texto.encode("utf-8"), True)).decode("ascii")
    except Exception as exc:  # noqa: BLE001
        log.warning("DPAPI: no se pudo cifrar, se guarda sin cifrar -- %s", exc)
        return texto


def desproteger(valor: str) -> str:
    if not esta_protegido(valor):
        return valor or ""
    try:
        return _crypt(base64.b64decode(valor[len(PREFIJO):]), False).decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        log.warning("DPAPI: no se pudo descifrar (otro equipo/usuario de Windows) -- %s", exc)
        return ""
