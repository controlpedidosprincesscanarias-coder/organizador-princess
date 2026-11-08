"""
utils/instancia_unica.py
Comprobación de instancia única al arrancar Organizador Princess.

Si ya existe una instancia previa de la app en ejecución en el mismo
equipo (mismo usuario de Windows), se cierra automáticamente esa
instancia antigua y se continúa el arranque solo con la nueva. Evita
tener varias ventanas abiertas a la vez, que provocaban avisos/popups
duplicados y escrituras concurrentes sobre agenda.json / usuarios.db.

ANTI-REGRESION: la comprobación debe ser MUY rápida (objetivo < 300 ms
en el caso normal) y ejecutarse ANTES de crear la ventana principal
(app = ttk.Window(...)). No se añade psutil como dependencia nueva —
se apoya en tasklist/taskkill de Windows vía subprocess, ocultando la
consola con CREATE_NO_WINDOW para no producir parpadeos de cmd.exe
(coherente con ser una app console=False de PyInstaller).

FIX 2026-07-20 (bug "ventanitas ciegas" / avisos duplicados):
El esquema anterior (leer PID de instance.lock -> matar -> escribir
PID nuevo) tenía una condición de carrera clásica TOCTOU: si dos
arranques ocurrían casi a la vez (doble clic accidental, un acceso
directo de inicio + un lanzamiento manual, etc.), ambos procesos
podían leer el lock file ANTES de que el otro escribiera su PID
nuevo. Ninguno mataba al otro y los dos quedaban vivos en paralelo,
cada uno con su propio hilo monitor_avisos y su propio bridge de
pedidos -> avisos duplicados y ventanas Toplevel apiladas que Windows
no repintaba (parecían "ciegas"/vacías).

Solución: usar un mutex con nombre a nivel de sistema operativo
(kernel32.CreateMutexW vía ctypes, sin dependencias nuevas). La
creación de un mutex con nombre es ATÓMICA a nivel de kernel: si dos
procesos lo piden en el mismo instante, Windows garantiza que solo
uno se entera de que "ya existía" (ERROR_ALREADY_EXISTS) y el otro no
-> ya no hay ventana de carrera posible, sea cual sea el timing.
Además, a diferencia del PID en un fichero, el mutex lo libera el
propio Windows automáticamente si el proceso muere de cualquier
forma (incluido un crash), así que nunca queda "colgado" apuntando a
un proceso que ya no existe.

Se mantiene el fichero instance.lock con el PID solo para poder
localizar y matar la instancia antigua real (petición de negocio:
la nueva instancia debe sustituir a la antigua, no simplemente
negarse a arrancar).
"""
import os
import sys
import time
import ctypes
import subprocess

from db.sqlite import CONFIG_FILE

_LOCK_FILE = os.path.join(os.path.dirname(CONFIG_FILE), "instance.lock")

_CREATE_NO_WINDOW = 0x08000000  # evita flash de consola al lanzar tasklist/taskkill

# Nombre único del mutex. "Local\" limita el alcance a la sesión de escritorio
# actual (no requiere privilegios especiales, a diferencia de "Global\").
_MUTEX_NAME = "Local\\OrganizadorPrincess_VAMA_SingleInstance_Mutex"
_ERROR_ALREADY_EXISTS = 183

# Handle del mutex mientras dure el proceso. Debe mantenerse vivo (no recolectado
# por el GC) para que el mutex siga "sujeto" — se libera solo al cerrar el proceso
# o al llamar explícitamente a liberar_instancia_actual().
_mutex_handle = None


def _nombre_proceso_actual() -> str:
    """Nombre del ejecutable actual (p. ej. 'OrganizadorPrincess.exe' o 'python.exe')."""
    return os.path.basename(sys.executable).lower()


def _proceso_existe(pid: int, nombre_esperado: str) -> bool:
    """True si el PID sigue vivo Y corresponde al mismo ejecutable.

    Comprobar también el nombre evita falsos positivos si Windows ha
    reciclado ese PID para un proceso completamente distinto entre medias.
    """
    if pid is None or pid <= 0:
        return False
    try:
        salida = subprocess.check_output(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            stderr=subprocess.DEVNULL,
            creationflags=_CREATE_NO_WINDOW,
            timeout=2,
        ).decode("mbcs", errors="ignore")
    except Exception:
        # Si tasklist falla (p.ej. entorno no-Windows en pruebas), no arriesgamos
        return False

    if not salida.strip() or "No tasks" in salida:
        return False

    primera_col = salida.split(",")[0].strip().strip('"').lower()
    return primera_col == nombre_esperado


def _terminar_proceso(pid: int) -> None:
    """Fuerza el cierre del proceso (y su árbol, /T) de forma segura.

    /T mata también procesos hijos huérfanos que pudiera haber dejado
    la instancia anterior (p.ej. hilos de actualización lanzados con
    subprocess), evitando bloqueos posteriores sobre los ficheros de
    datos compartidos (agenda.json, usuarios.db).
    """
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F", "/T"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_CREATE_NO_WINDOW,
            timeout=3,
        )
    except Exception:
        pass  # best-effort — si no se puede matar, seguimos igualmente


def _crear_mutex():
    """Intenta crear/adquirir el mutex con nombre.

    Devuelve (handle, ya_existia):
        handle     -> el handle del mutex (None si no se pudo crear, p.ej.
                       en un entorno no-Windows durante pruebas).
        ya_existia -> True si el mutex YA estaba en manos de otro proceso
                       vivo en el momento exacto de la llamada (dato fiable
                       al 100%, decidido por el kernel, no por nosotros).
    """
    try:
        kernel32 = ctypes.windll.kernel32
        kernel32.SetLastError(0)
        handle = kernel32.CreateMutexW(None, False, _MUTEX_NAME)
        ya_existia = (ctypes.GetLastError() == _ERROR_ALREADY_EXISTS)
        if not handle:
            return None, False
        return handle, ya_existia
    except Exception:
        # No estamos en Windows (p.ej. pruebas en otro SO) -> no bloqueamos arranque
        return None, False


def asegurar_instancia_unica(timeout_espera: float = 1.5) -> None:
    """Punto de entrada: llamar UNA VEZ al arrancar, antes de crear la UI.

    - Adquiere un mutex de sistema operativo con nombre fijo. Esto es
      ATÓMICO: como mucho un proceso puede "ganarlo" en cada instante,
      sea cual sea el timing de arranques simultáneos.
    - Si el mutex YA estaba cogido por otra instancia viva -> se localiza
      su PID en el lock file y se cierra, y se reintenta adquirir el
      mutex (que Windows libera automáticamente en cuanto ese proceso
      muere, incluso si muere de forma abrupta).
    - Escribe el PID de la instancia actual en el lock file (solo con
      fines informativos/de localización para el siguiente arranque).
    """
    global _mutex_handle
    nombre_actual = _nombre_proceso_actual()

    try:
        os.makedirs(os.path.dirname(_LOCK_FILE), exist_ok=True)
    except Exception:
        pass  # si no se puede crear la carpeta, no bloqueamos el arranque

    _mutex_handle, ya_existia = _crear_mutex()

    if ya_existia:
        # Hay, con total seguridad, otra instancia viva en este preciso instante
        # (lo dice el kernel, no un fichero que puede estar obsoleto). La
        # sustituimos: localizamos su PID en el lock file y la cerramos.
        pid_previo = None
        try:
            with open(_LOCK_FILE, "r", encoding="utf-8") as fh:
                contenido = fh.read().strip()
            if contenido:
                pid_previo = int(contenido.splitlines()[0])
        except Exception:
            pid_previo = None

        if pid_previo and pid_previo != os.getpid() and _proceso_existe(pid_previo, nombre_actual):
            _terminar_proceso(pid_previo)

        # Reintentar adquirir el mutex hasta timeout_espera, dando tiempo a que
        # Windows lo libere en cuanto el proceso antiguo termine de morir.
        _inicio_espera = time.time()
        while time.time() - _inicio_espera < timeout_espera:
            if _mutex_handle:
                try:
                    ctypes.windll.kernel32.CloseHandle(_mutex_handle)
                except Exception:
                    pass
            _mutex_handle, ya_existia = _crear_mutex()
            if not ya_existia:
                break
            time.sleep(0.1)
        # Si tras el timeout sigue "ocupado", arrancamos igualmente (mismo
        # criterio de tolerancia que tenía el código anterior): más vale una
        # app que arranca a una que se queda bloqueada para siempre.

    # Registrar esta instancia como la activa para futuros arranques
    try:
        with open(_LOCK_FILE, "w", encoding="utf-8") as fh:
            fh.write(str(os.getpid()))
    except Exception:
        pass  # no crítico — en el peor caso, el próximo arranque no detectará esta instancia


def liberar_instancia_actual() -> None:
    """Elimina el lock file y libera el mutex si pertenecen a esta instancia.

    Se llama en los cierres limpios (botón X, cierre automático de las
    17:00) para dejar el sitio libre de inmediato. No es estrictamente
    necesario —el mutex se libera solo al morir el proceso, sea limpio o
    no— pero evita la pequeña espera de reintento en el próximo arranque.
    """
    global _mutex_handle
    try:
        with open(_LOCK_FILE, "r", encoding="utf-8") as fh:
            contenido = fh.read().strip()
        if contenido and int(contenido.splitlines()[0]) == os.getpid():
            os.remove(_LOCK_FILE)
    except Exception:
        pass  # best-effort — no crítico

    if _mutex_handle:
        try:
            ctypes.windll.kernel32.CloseHandle(_mutex_handle)
        except Exception:
            pass
        _mutex_handle = None
