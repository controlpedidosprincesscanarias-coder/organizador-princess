"""
services/vinculo_navegador.py — vincular el navegador de este PC con el Organizador (v4.18.60).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Petición de Víctor (12 nov 2026): Control Pedidos tiene que saber si el Organizador está abierto en ESTE PC,
no solo si el usuario lo tiene abierto en alguno. Sin nada escuchando en el PC ni preguntas del navegador:
- La web de Control Pedidos guarda en el navegador un código propio y, en el aviso «abre o instala el
  Organizador», el botón «Abrir el Organizador» abre organizadorprincess://abrir?navegador=<código>.
- El Organizador recibe ese enlace al arrancar (Windows lo pasa como argumento: "%1" en el registro, en el
  .iss y en services/portatil.py), guarda el código en %APPDATA%\\OrganizadorPrincess\\navegadores.json y lo
  envía en cada consulta a Control Pedidos (cabecera X-Organizador-Navegadores, pedidos_agenda_bridge.py).
- Control Pedidos (v12.34.32, servicios/organizador.py) sabe así qué navegador está en el mismo PC que un
  Organizador abierto.

Sin tkinter: se prueba en test_control_pedidos.py.
"""
import json
import os
import re
from urllib.parse import parse_qs, urlparse

PROTOCOLO = "organizadorprincess"
MAXIMO = 10
_VALIDO = re.compile(r"^[A-Za-z0-9-]{16,64}$")


def ruta_por_defecto():
    from db.sqlite import CONFIG_FILE
    return os.path.join(os.path.dirname(CONFIG_FILE), "navegadores.json")


def extraer_navegador(argv):
    """Código de navegador del enlace organizadorprincess://…?navegador=… entre los argumentos, o None."""
    for arg in argv or []:
        texto = str(arg or "").strip().strip('"')
        if not texto.lower().startswith(PROTOCOLO + ":"):
            continue
        try:
            valores = parse_qs(urlparse(texto).query).get("navegador") or []
        except ValueError:
            continue
        for v in valores:
            if _VALIDO.match(v.strip()):
                return v.strip()
    return None


def leer(ruta=None):
    """Códigos guardados (el más reciente primero), solo los válidos."""
    try:
        with open(ruta or ruta_por_defecto(), encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, ValueError):
        return []
    lista = datos.get("navegadores") if isinstance(datos, dict) else None
    return [n for n in (lista or []) if isinstance(n, str) and _VALIDO.match(n)][:MAXIMO]


def guardar(codigo, ruta=None):
    """Añade el código (el primero de la lista; como mucho MAXIMO). True si lo ha guardado. Nunca lanza."""
    if not codigo or not _VALIDO.match(codigo):
        return False
    ruta = ruta or ruta_por_defecto()
    lista = [codigo] + [n for n in leer(ruta) if n != codigo]
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        tmp = ruta + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"navegadores": lista[:MAXIMO]}, f)
        os.replace(tmp, ruta)
        return True
    except OSError:
        return False


def guardar_desde_argv(argv, ruta=None):
    """Al arrancar: si el Organizador se abrió con el enlace de Control Pedidos, guarda su código."""
    codigo = extraer_navegador(argv)
    return guardar(codigo, ruta) if codigo else False


def cabecera(ruta=None):
    """Valor de la cabecera X-Organizador-Navegadores («a,b,c»), o "" si no hay ninguno."""
    return ",".join(leer(ruta))
