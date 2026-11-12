"""
services/portatil.py — Organizador portátil: un solo .exe, sin instalar (v4.18.54).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Petición de Víctor (12 nov 2026): hay PC que no permiten instalar programas, pero sí abrir un .exe suelto
(la Consola Registro Info funciona y se actualiza sola en ellos). El Organizador ya se compila como un solo
.exe; el instalador solo lo copia en Archivos de programa (pide administrador), pone los manuales, los
accesos directos y el enlace organizadorprincess://. La copia portátil:

- Se reconoce porque no tiene al lado el desinstalador de Inno Setup (unins000.exe).
- Se actualiza sola sin administrador, como la Consola: descarga el .zip portátil de la Release, comprueba
  su SHA-256 (obligatorio), saca el .exe nuevo junto al actual («.nuevo.exe»), cambia el actual a
  «.anterior.exe», pone el nuevo en su sitio y lo abre. Al arrancar, la versión nueva borra los restos.
- Registra el enlace organizadorprincess:// solo para el usuario de Windows (HKCU, sin administrador).
- Lleva dentro el manual y las notas de las versiones (main.spec, carpeta «documentos»).

ANTI-REGRESION: la copia portátil se publica DENTRO de un .zip y nunca como .exe suelto. Los Organizadores
instalados hasta la v4.18.52 cogen el PRIMER .exe de la Release como instalador
(update_service._check_update_github): con un segundo .exe podrían descargar el portátil y no actualizarse.

Sin tkinter: se prueba en test_portatil.py.
"""
import hashlib
import os
import re
import subprocess
import sys
import zipfile

NOMBRE_EXE = "OrganizadorPrincess.exe"
DESINSTALADOR = "unins000.exe"                 # lo deja Inno Setup en la carpeta de instalación
_RE_ZIP = re.compile(r"^OrganizadorPrincess_Portatil_v?[\d.]+\.zip$", re.I)
TAMANO_MAXIMO = 300 * 1024 * 1024              # un .zip de más de 300 MB no es nuestro
PROTOCOLO = "organizadorprincess"


def ruta_exe():
    return os.path.abspath(sys.executable)


def es_portatil(ruta=None, frozen=None):
    """True si es el .exe compilado y no está instalado (sin el desinstalador de Inno Setup al lado)."""
    if not (getattr(sys, "frozen", False) if frozen is None else frozen):
        return False
    carpeta = os.path.dirname(ruta or ruta_exe())
    return not os.path.isfile(os.path.join(carpeta, DESINSTALADOR))


def puede_actualizarse(ruta=None):
    """La copia portátil solo se actualiza sola si puede escribir en su carpeta."""
    return os.access(os.path.dirname(ruta or ruta_exe()), os.W_OK)


def elegir_assets(assets, portatil):
    """(archivo, su .sha256) de la Release para este Organizador, o (None, None).
    Instalado: el instalador (el primer .exe, igual que las versiones anteriores). Portátil: el .zip."""
    assets = assets or []
    if portatil:
        principal = next((a for a in assets if _RE_ZIP.match(a.get("name") or "")), None)
    else:
        principal = next((a for a in assets if (a.get("name") or "").lower().endswith(".exe")), None)
    if not principal:
        return None, None
    buscado = principal["name"].lower() + ".sha256"
    sha = next((a for a in assets if (a.get("name") or "").lower() == buscado), None)
    return principal, sha


def extraer_hash(texto, nombre):
    """SHA-256 (64 hex) para `nombre` en un .sha256: «<hash>», «<hash>  <fichero>» o «<hash> *<fichero>»."""
    for linea in (l.strip() for l in (texto or "").splitlines() if l.strip()):
        m = re.match(r"^([0-9a-fA-F]{64})(?:\s+\*?(.+))?$", linea)
        if m and (not m.group(2) or os.path.basename(m.group(2).strip()).lower() == nombre.lower()):
            return m.group(1).lower()
    return None


def rutas(ruta):
    """(nuevo, anterior) junto al .exe actual: «X.nuevo.exe» y «X.anterior.exe»."""
    base, ext = os.path.splitext(ruta)
    return base + ".nuevo" + (ext or ".exe"), base + ".anterior" + (ext or ".exe")


def limpiar_restos(ruta=None):
    """Borra los restos de una actualización anterior. Devuelve (borrados, pendientes). Nunca lanza."""
    borrados, pendientes = [], []
    for r in rutas(ruta or ruta_exe()):
        if not os.path.isfile(r):
            continue
        try:
            os.remove(r)
            borrados.append(os.path.basename(r))
        except OSError:
            pendientes.append(os.path.basename(r))
    return borrados, pendientes


def descargar_y_preparar(url_zip, url_sha, nombre_zip, carpeta_tmp, ruta, abrir, progreso=None):
    """Descarga el .zip portátil a `carpeta_tmp`, comprueba su SHA-256 y deja el .exe que trae junto al
    actual como «.nuevo.exe». Devuelve esa ruta. Si algo falla, borra lo descargado y lanza RuntimeError
    con un mensaje para el usuario. `abrir(url, timeout)` devuelve un objeto tipo respuesta de urllib."""
    if not url_sha:
        raise RuntimeError("La versión publicada no trae el .sha256 de la copia portátil: no se instala.")
    with abrir(url_sha, 20) as r:
        esperado = extraer_hash(r.read(65536).decode("utf-8", "ignore"), nombre_zip)
    if not esperado:
        raise RuntimeError("No se ha podido leer el SHA-256 publicado.")
    ruta_zip = os.path.join(carpeta_tmp, nombre_zip)
    nuevo, _ = rutas(ruta)
    sha, hecho = hashlib.sha256(), 0
    try:
        with abrir(url_zip, 120) as r, open(ruta_zip, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0) if getattr(r, "headers", None) else 0
            while True:
                trozo = r.read(256 * 1024)
                if not trozo:
                    break
                hecho += len(trozo)
                if hecho > TAMANO_MAXIMO:
                    raise RuntimeError("El archivo descargado es demasiado grande.")
                f.write(trozo)
                sha.update(trozo)
                if progreso:
                    progreso(hecho, total)
        if sha.hexdigest() != esperado:
            raise RuntimeError("El archivo descargado no coincide con el SHA-256 publicado (se ha borrado). "
                               "Vuelve a intentarlo más tarde.")
        with zipfile.ZipFile(ruta_zip) as z:
            dentro = next((n for n in z.namelist() if os.path.basename(n).lower() == NOMBRE_EXE.lower()), None)
            if not dentro:
                raise RuntimeError(f"El .zip no trae {NOMBRE_EXE}.")
            with z.open(dentro) as origen, open(nuevo, "wb") as destino:
                while True:
                    trozo = origen.read(256 * 1024)
                    if not trozo:
                        break
                    destino.write(trozo)
    except BaseException:
        for f in (nuevo,):
            try:
                os.remove(f)
            except OSError:
                pass
        raise
    finally:
        try:
            os.remove(ruta_zip)
        except OSError:
            pass
    return nuevo


def sustituir_exe(ruta_nuevo, ruta):
    """Pone el .exe nuevo en el sitio del actual (el actual pasa a «.anterior.exe»; Windows deja renombrar
    un .exe en uso). Si falla a mitad, deja el actual como estaba y lanza RuntimeError."""
    _, anterior = rutas(ruta)
    try:
        if os.path.exists(anterior):
            os.remove(anterior)
    except OSError:
        pass
    try:
        os.replace(ruta, anterior)
    except OSError as e:
        raise RuntimeError(f"No se pudo renombrar el programa actual: {e}")
    try:
        os.replace(ruta_nuevo, ruta)
    except OSError as e:
        try:
            os.replace(anterior, ruta)          # vuelta atrás: el actual sigue funcionando
        except OSError:
            pass
        raise RuntimeError(f"No se pudo colocar la versión nueva: {e}")


def entorno_limpio(entorno=None):
    """Variables de entorno para abrir otro .exe de PyInstaller desde este (sin las internas del actual)."""
    env = {k: v for k, v in (os.environ if entorno is None else entorno).items()
           if not k.startswith("_PYI") and k != "_MEIPASS2"}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def lanzar(ruta):
    """Abre el .exe (ya sustituido) como proceso independiente."""
    flags = 0
    if sys.platform.startswith("win"):
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen([ruta], cwd=os.path.dirname(ruta), close_fds=True, creationflags=flags, env=entorno_limpio())


def registrar_enlace_usuario(ruta=None, winreg_mod=None):
    """Registra organizadorprincess:// para el usuario de Windows (HKCU\\Software\\Classes), apuntando a
    esta copia. Es lo que hace el instalador para todo el equipo, pero sin administrador. Devuelve True si
    lo ha escrito. Nunca lanza."""
    try:
        if winreg_mod is None:
            if not sys.platform.startswith("win"):
                return False
            import winreg as winreg_mod
        exe = ruta or ruta_exe()
        base = rf"Software\Classes\{PROTOCOLO}"
        valores = [
            (base, "", "URL:Organizador Princess"),
            (base, "URL Protocol", ""),
            (base + r"\DefaultIcon", "", f'"{exe}",0'),
            (base + r"\shell\open\command", "", f'"{exe}" "%1"'),   # (v4.18.60) "%1": el enlace con el código del navegador
        ]
        for clave, nombre, dato in valores:
            with winreg_mod.CreateKey(winreg_mod.HKEY_CURRENT_USER, clave) as k:
                winreg_mod.SetValueEx(k, nombre, 0, winreg_mod.REG_SZ, dato)
        return True
    except Exception:  # noqa: BLE001
        return False


def documento_incluido(*partes):
    """Ruta de un documento que va dentro del .exe (main.spec → carpeta «documentos»), o None."""
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        return None
    ruta = os.path.join(base, "documentos", *partes)
    return ruta if os.path.isfile(ruta) else None


# ── Primer arranque: carpeta propia, arranque con Windows y escritorio (v4.18.54) ──────────────────────
# Petición de Víctor: la primera vez, preguntar en qué carpeta guardarlo (así el acceso directo y las
# actualizaciones van siempre a esa carpeta) y poner un acceso directo en la carpeta de Inicio de Windows
# para que arranque al iniciar sesión. Todo sin administrador. La ventana está en ui/primer_arranque_portatil.py.
NOMBRE_ACCESO = "Organizador Princess"
_CLAVE_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"
_CREATE_NO_WINDOW = 0x08000000


def carpeta_por_defecto():
    """Documentos\\Organizador Princess del usuario (carpeta suya, donde Windows deja escribir sin permisos)."""
    return os.path.join(os.path.expanduser("~"), "Documents", NOMBRE_ACCESO)


def leer_estado(ruta_json):
    """{"ruta_exe": …, "arranque": "acceso"|"registro"|None, "escritorio": bool} o {} si no hay."""
    import json
    try:
        with open(ruta_json, encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, dict) else {}
    except (OSError, ValueError):
        return {}


def guardar_estado(ruta_json, estado):
    import json
    try:
        os.makedirs(os.path.dirname(ruta_json), exist_ok=True)
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def _misma_ruta(a, b):
    return os.path.normcase(os.path.abspath(a or "")) == os.path.normcase(os.path.abspath(b or ""))


def que_hacer_al_arrancar(estado, exe_actual, existe=os.path.isfile):
    """«primera_vez» (preguntar la carpeta), «otra_copia» (ya hay una guardada en otra carpeta y existe)
    o «ok» (esta es la copia guardada)."""
    guardada = (estado or {}).get("ruta_exe")
    if not guardada or not existe(guardada):
        return "primera_vez"
    return "ok" if _misma_ruta(guardada, exe_actual) else "otra_copia"


def copiar_a_carpeta(carpeta, exe_actual):
    """Copia este .exe a `carpeta` (la crea si hace falta) y devuelve la ruta de la copia. Si ya es esa
    carpeta, devuelve el .exe actual sin copiar. Lanza RuntimeError con un mensaje si no se puede."""
    import shutil
    destino = os.path.join(carpeta, NOMBRE_EXE)
    if _misma_ruta(destino, exe_actual):
        return exe_actual
    try:
        os.makedirs(carpeta, exist_ok=True)
        tmp = destino + ".copiando"
        shutil.copy2(exe_actual, tmp)
        os.replace(tmp, destino)
    except OSError as e:
        raise RuntimeError(f"No se pudo copiar el Organizador a «{carpeta}»: {e}")
    return destino


def _ps_texto(s):
    """Texto entre comillas simples de PowerShell (las comillas simples se duplican)."""
    return "'" + str(s).replace("'", "''") + "'"


def orden_acceso_directo(ruta_exe, carpeta_especial):
    """Orden de PowerShell que crea «Organizador Princess.lnk» en una carpeta especial de Windows
    ('Startup' = carpeta de Inicio, 'Desktop' = escritorio) y escribe OK si queda creado."""
    carpeta = os.path.dirname(ruta_exe)
    return ("$w = New-Object -ComObject WScript.Shell; "
            f"$p = Join-Path ([Environment]::GetFolderPath({_ps_texto(carpeta_especial)})) {_ps_texto(NOMBRE_ACCESO + '.lnk')}; "
            "$s = $w.CreateShortcut($p); "
            f"$s.TargetPath = {_ps_texto(ruta_exe)}; $s.WorkingDirectory = {_ps_texto(carpeta)}; "
            f"$s.IconLocation = {_ps_texto(ruta_exe + ',0')}; $s.Description = {_ps_texto(NOMBRE_ACCESO)}; "
            "$s.Save(); if (Test-Path $p) { 'OK' }")


def crear_acceso_directo(ruta_exe, carpeta_especial, ejecutar=None):
    """Crea el acceso directo con PowerShell (viene con Windows; no pide administrador). True si se creó."""
    if ejecutar is None:
        if not sys.platform.startswith("win"):
            return False

        def ejecutar(orden):
            return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                                   "-Command", orden], capture_output=True, text=True, timeout=30,
                                  creationflags=_CREATE_NO_WINDOW).stdout
    try:
        return "OK" in (ejecutar(orden_acceso_directo(ruta_exe, carpeta_especial)) or "")
    except Exception:  # noqa: BLE001
        return False


def arranque_por_registro(ruta_exe, winreg_mod=None):
    """Plan B si PowerShell está bloqueado: arranque al iniciar sesión con HKCU\\…\\Run (sin administrador;
    se ve y se desactiva en el Administrador de tareas → Aplicaciones de arranque). True si se escribió."""
    try:
        if winreg_mod is None:
            if not sys.platform.startswith("win"):
                return False
            import winreg as winreg_mod
        with winreg_mod.CreateKey(winreg_mod.HKEY_CURRENT_USER, _CLAVE_RUN) as k:
            winreg_mod.SetValueEx(k, NOMBRE_ACCESO, 0, winreg_mod.REG_SZ, f'"{ruta_exe}"')
        return True
    except Exception:  # noqa: BLE001
        return False


def preparar_arranque_con_windows(ruta_exe, ejecutar=None, winreg_mod=None):
    """Acceso directo en la carpeta de Inicio o, si no se puede, la clave Run. «acceso», «registro» o None."""
    if crear_acceso_directo(ruta_exe, "Startup", ejecutar):
        return "acceso"
    if arranque_por_registro(ruta_exe, winreg_mod):
        return "registro"
    return None
