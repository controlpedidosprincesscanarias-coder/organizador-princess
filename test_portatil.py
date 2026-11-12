"""Pruebas de la copia portátil del Organizador (v4.18.54), sin Windows ni interfaz.

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_portatil.py
"""
import hashlib
import io
import os
import re
import sys
import tempfile
import zipfile

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(RAIZ, "app"))
from services import portatil as P  # noqa: E402

fallos = []
n = 0


def ok(cond, texto):
    global n
    n += 1
    print(("OK    " if cond else "FALLO ") + texto)
    if not cond:
        fallos.append(texto)


class _Resp(io.BytesIO):
    def __init__(self, datos):
        super().__init__(datos)
        self.headers = {"Content-Length": str(len(datos))}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def _zip_con(nombre_dentro, contenido):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr(nombre_dentro, contenido)
    return b.getvalue()


VERSION = "4.18.54"
INSTALADOR = f"OrganizadorPrincess_Setup_{VERSION}.exe"
ZIP = f"OrganizadorPrincess_Portatil_v{VERSION}.zip"

# ── 1. ¿Portátil o instalado? ────────────────────────────────────────────────
with tempfile.TemporaryDirectory() as d:
    exe = os.path.join(d, P.NOMBRE_EXE)
    open(exe, "wb").close()
    ok(P.es_portatil(exe, frozen=True), "un .exe sin el desinstalador al lado es la copia portátil")
    open(os.path.join(d, P.DESINSTALADOR), "wb").close()
    ok(not P.es_portatil(exe, frozen=True), "con unins000.exe al lado es una instalación")
    ok(not P.es_portatil(exe, frozen=False), "desde el código (sin compilar) nunca es portátil")

# ── 2. Qué archivo de la Release coge cada uno ───────────────────────────────
assets = [{"name": ZIP, "browser_download_url": "u-zip"}, {"name": ZIP + ".sha256", "browser_download_url": "u-zip-sha"},
          {"name": INSTALADOR, "browser_download_url": "u-exe"}, {"name": INSTALADOR + ".sha256", "browser_download_url": "u-exe-sha"}]
a, s = P.elegir_assets(assets, portatil=False)
ok(a and a["name"] == INSTALADOR and s["name"] == INSTALADOR + ".sha256", "instalado: el instalador y su .sha256")
a, s = P.elegir_assets(assets, portatil=True)
ok(a and a["name"] == ZIP and s["name"] == ZIP + ".sha256", "portátil: el .zip portátil y su .sha256")
viejo = next((x for x in assets if x["name"].lower().endswith(".exe")), None)
ok(viejo["name"] == INSTALADOR,
   "los Organizadores ya instalados (primer .exe de la Release) siguen cogiendo el instalador aunque el .zip vaya antes")
ok(P.elegir_assets([{"name": INSTALADOR}], portatil=True) == (None, None),
   "una Release sin copia portátil no ofrece nada a la portátil (no se baja el instalador)")

# ── 3. Descarga, comprobación y extracción ───────────────────────────────────
contenido_exe = b"MZ nuevo organizador" * 100
datos_zip = _zip_con(P.NOMBRE_EXE, contenido_exe)
hash_ok = hashlib.sha256(datos_zip).hexdigest()


def abrir_con(datos, texto_sha):
    def abrir(url, timeout):
        return _Resp(texto_sha.encode() if url == "sha" else datos)
    return abrir


with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as tmp:
    exe = os.path.join(d, P.NOMBRE_EXE)
    open(exe, "wb").write(b"MZ viejo")
    nuevo = P.descargar_y_preparar("zip", "sha", ZIP, tmp, exe, abrir_con(datos_zip, f"{hash_ok}  {ZIP}"))
    ok(open(nuevo, "rb").read() == contenido_exe and nuevo.endswith(".nuevo.exe"),
       "con el SHA-256 correcto deja el .exe del .zip junto al actual como «.nuevo.exe»")
    ok(not os.listdir(tmp), "el .zip descargado se borra después")
    os.remove(nuevo)

    try:
        P.descargar_y_preparar("zip", "sha", ZIP, tmp, exe, abrir_con(datos_zip, "0" * 64))
        ok(False, "un SHA-256 distinto debe impedir la actualización")
    except RuntimeError as e:
        ok("SHA-256" in str(e) and not os.path.exists(P.rutas(exe)[0]),
           "con un SHA-256 distinto no se actualiza y no queda nada descargado")

    try:
        P.descargar_y_preparar("zip", "", ZIP, tmp, exe, abrir_con(datos_zip, ""))
        ok(False, "sin .sha256 no debe actualizarse")
    except RuntimeError:
        ok(True, "sin .sha256 publicado no se actualiza")

    raro = _zip_con("otra_cosa.txt", b"x")
    try:
        P.descargar_y_preparar("zip", "sha", ZIP, tmp, exe, abrir_con(raro, hashlib.sha256(raro).hexdigest()))
        ok(False, "un .zip sin el .exe debe rechazarse")
    except RuntimeError as e:
        ok(P.NOMBRE_EXE in str(e), "un .zip que no trae OrganizadorPrincess.exe se rechaza")

# ── 4. Sustituir el .exe y limpiar los restos ────────────────────────────────
with tempfile.TemporaryDirectory() as d:
    exe = os.path.join(d, P.NOMBRE_EXE)
    nuevo, anterior = P.rutas(exe)
    open(exe, "wb").write(b"viejo")
    open(nuevo, "wb").write(b"nuevo")
    P.sustituir_exe(nuevo, exe)
    ok(open(exe, "rb").read() == b"nuevo" and open(anterior, "rb").read() == b"viejo",
       "el nuevo ocupa el sitio del actual y el actual pasa a «.anterior.exe»")
    borrados, pendientes = P.limpiar_restos(exe)
    ok(borrados == [os.path.basename(anterior)] and not pendientes and os.path.isfile(exe),
       "al arrancar la versión nueva se borra «.anterior.exe» y el programa sigue en su sitio")
    try:
        P.sustituir_exe(os.path.join(d, "no_existe.exe"), exe)
        ok(False, "sin el .exe nuevo debe fallar")
    except RuntimeError:
        ok(open(exe, "rb").read() == b"nuevo", "si falla a mitad, el programa actual queda como estaba")

env = P.entorno_limpio({"_PYI_ARCHIVE_FILE": "x", "_MEIPASS2": "y", "PATH": "p"})
ok("_PYI_ARCHIVE_FILE" not in env and "_MEIPASS2" not in env and env["PATH"] == "p"
   and env["PYINSTALLER_RESET_ENVIRONMENT"] == "1", "la versión nueva se abre sin las variables internas de la vieja")


# ── 5. Enlace organizadorprincess:// para el usuario (sin administrador) ─────
class _WinregFalso:
    HKEY_CURRENT_USER = "HKCU"
    REG_SZ = 1

    def __init__(self):
        self.valores = {}

    def CreateKey(self, raiz, clave):

        class _K:
            def __enter__(self):
                return (raiz, clave)

            def __exit__(self, *a):
                return False
        self._ultima = (raiz, clave)
        return _K()

    def SetValueEx(self, k, nombre, _r, _t, dato):
        self.valores[(k[0], k[1], nombre)] = dato


w = _WinregFalso()
ruta = r"C:\Users\alguien\Programas\OrganizadorPrincess.exe"
ok(P.registrar_enlace_usuario(ruta, winreg_mod=w), "registra el enlace con el registro de Windows del usuario")
ok(w.valores.get(("HKCU", r"Software\Classes\organizadorprincess\shell\open\command", "")) == f'"{ruta}"'
   and ("HKCU", r"Software\Classes\organizadorprincess", "URL Protocol") in w.valores
   and all(k[0] == "HKCU" for k in w.valores),
   "solo en HKEY_CURRENT_USER (sin administrador) y apuntando a esta copia")
ok(P.registrar_enlace_usuario(ruta, winreg_mod=object()) is False, "si el registro falla, no se rompe el arranque")

# ── 6. Compilación y publicación ─────────────────────────────────────────────
spec = open(os.path.join(RAIZ, "main.spec"), encoding="utf-8").read()
ok("'services.portatil'" in spec, "main.spec incluye services.portatil en hiddenimports")
ok("'documentos'" in spec and "release_notes/release_notes.md" in spec,
   "el manual y las notas de las versiones van dentro del .exe")
flujo = open(os.path.join(RAIZ, ".github", "workflows", "compilar.yml"), encoding="utf-8").read()
ok("Compress-Archive" in flujo and flujo.index("outputs.instalador }}.sha256\" `") < flujo.index("outputs.portatil }}\" `"),
   "el workflow publica el .zip portátil, después del instalador")
prep = open(os.path.join(RAIZ, "compilacion", "preparar_release.py"), encoding="utf-8").read()
nombre = re.search(r"portatil=(OrganizadorPrincess_Portatil_v)\{v_app\}\.zip", prep)
ok(nombre and P._RE_ZIP.match(nombre.group(1) + VERSION + ".zip"),
   "el nombre del .zip que genera la compilación es el que busca la copia portátil")
ok(".exe" not in re.sub(r"Setup_\{v_app\}\.exe", "", prep.split("portatil=")[1].split("\n")[0]),
   "la copia portátil nunca se publica como .exe suelto")
upd = open(os.path.join(RAIZ, "app", "services", "update_service.py"), encoding="utf-8").read()
ok("elegir_assets(assets, portatil=True)" in upd and "_descargar_portatil()" in upd,
   "el actualizador usa el .zip y la actualización sin instalador en la copia portátil")

print()
if fallos:
    print(f"{len(fallos)} de {n} comprobaciones FALLAN")
    sys.exit(1)
print(f"Copia portátil: {n} comprobaciones OK.")
