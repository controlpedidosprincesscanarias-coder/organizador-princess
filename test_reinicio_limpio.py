"""Pruebas del «Borrado completo y reinicio limpio» (v4.18.62), sin Windows ni interfaz.

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_reinicio_limpio.py
"""
import os
import re
import sys
import tempfile

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(RAIZ, "app"))
from services import reinicio_limpio as R  # noqa: E402

fallos = []
n = 0


def ok(cond, texto):
    global n
    n += 1
    print(("OK    " if cond else "FALLO ") + texto)
    if not cond:
        fallos.append(texto)


with tempfile.TemporaryDirectory() as d:
    carpeta = os.path.join(d, "OrganizadorPrincess")
    os.makedirs(os.path.join(carpeta, "backups"))
    for nombre in ("config.json", "agenda.json", "usuarios.db", "navegadores.json", "portatil.json",
                   os.path.join("backups", "agenda_1.json")):
        with open(os.path.join(carpeta, nombre), "w") as f:
            f.write("x")
    ok(not R.hay_pendiente(carpeta), "sin marca no hay nada pendiente")
    R.programar(carpeta)
    ok(R.hay_pendiente(carpeta), "programar deja la marca")
    borrados, quedan = R.aplicar(carpeta, dormir=lambda s: None)
    ok(sorted(borrados) == ["agenda.json", "backups", "config.json", "navegadores.json", "usuarios.db"],
       f"borra todo lo del usuario ({sorted(borrados)})")
    ok(quedan == [], "no queda nada sin borrar")
    ok(sorted(os.listdir(carpeta)) == ["portatil.json"], "conserva solo portatil.json y quita la marca")
    ok(not R.hay_pendiente(carpeta), "después ya no hay nada pendiente")

    # Un archivo que no se deja borrar a la primera (la copia antigua aún lo tiene abierto): se reintenta
    with open(os.path.join(carpeta, "agenda.json"), "w") as f:
        f.write("x")
    R.programar(carpeta)
    original = R._borrar
    veces = {"n": 0}

    def borrar_terco(ruta):
        if ruta.endswith("agenda.json") and veces["n"] < 2:
            veces["n"] += 1
            raise PermissionError("en uso")
        original(ruta)
    R._borrar = borrar_terco
    esperas = []
    borrados, quedan = R.aplicar(carpeta, dormir=esperas.append)
    ok(borrados == ["agenda.json"] and quedan == [] and len(esperas) == 2, "reintenta lo que está en uso")

    # Y si nunca se suelta, se informa y se sigue
    with open(os.path.join(carpeta, "bridge_errors.log"), "w") as f:
        f.write("x")
    R.programar(carpeta)

    def nunca(ruta):
        raise PermissionError("en uso")
    R._borrar = nunca
    borrados, quedan = R.aplicar(carpeta, intentos=3, dormir=lambda s: None)
    R._borrar = original
    ok(quedan == ["bridge_errors.log"] and not R.hay_pendiente(carpeta), "lo que no se suelta se deja y se informa")

    ok(R.aplicar(os.path.join(d, "no_existe")) == ([], []), "sin carpeta no hace nada")

ok(R.orden_relanzar(True, "C:\\Org\\OrganizadorPrincess.exe") == ["C:\\Org\\OrganizadorPrincess.exe"], "relanza el .exe")
ok(R.orden_relanzar(False, "python", "main_agenda.py") == ["python", "main_agenda.py"], "desde el código, python main_agenda.py")

# El desinstalador ya no borra los datos del usuario
iss = open(os.path.join(RAIZ, "OrganizadorPrincess_Setup.iss"), encoding="utf-8").read()
ok("{userappdata}" not in re.sub(r"(?m)^\s*;.*$", "", iss.split("[UninstallDelete]")[1].split("\n[")[0]),
   "el desinstalador no borra %APPDATA%\\OrganizadorPrincess")
ok("services.reinicio_limpio" in open(os.path.join(RAIZ, "main.spec"), encoding="utf-8").read(),
   "main.spec incluye services.reinicio_limpio")

print(f"\n{n - len(fallos)}/{n} correctas")
sys.exit(1 if fallos else 0)
