"""Manual consultable del botón «📖 Manual» (v4.18.76): apartados, buscador sin tildes ni mayúsculas y acceso al
PDF completo, como el manual del chat del móvil (utils/manual_consulta.py, ui/manual.py).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_manual_consulta.py   (no necesita Tkinter)
"""
import os
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(RAIZ, "app"))
from utils import manual_consulta as mc  # noqa: E402

fallos = []
def ok(nombre, cond, det=""):
    print(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
    if not cond:
        fallos.append(nombre)

titulos = [a[1] for a in mc.APARTADOS]
ok("hay apartados y ninguno vacío", len(mc.APARTADOS) >= 15 and all(a[0] and a[1] and a[2] for a in mc.APARTADOS))
ok("títulos sin repetir", len(set(titulos)) == len(titulos))
ok("sin consulta salen todos", mc.buscar("") == mc.APARTADOS and mc.buscar("   ") == mc.APARTADOS)
ok("sin tildes ni mayúsculas: «VERSION» encuentra «versión»", any("Actualizaciones" in a[1] for a in mc.buscar("VERSION")))
ok("«sonido» encuentra el apartado de los sonidos del chat", any(a[1] == "Sonido de los mensajes" for a in mc.buscar("sonido")))
ok("varias palabras: todas deben estar", all("portátil" in mc.normal(a[1] + " ".join(a[2])) or "portatil" in mc.normal(a[1] + " ".join(a[2]))
                                              for a in mc.buscar("portatil zip")) and mc.buscar("portatil zip"))
ok("una palabra que no existe no encuentra nada", mc.buscar("xyzzy") == [])
ok("normal quita tildes", mc.normal("Árbol Ñandú Versión") == "arbol nandu version")
for clave in ("vacaciones", "festivos", "agenda", "chat", "burbuja", "admin", "mi usuario", "actualizar", "voz", "grupo"):
    ok(f"«{clave}» da resultados", bool(mc.buscar(clave)))
texto = " ".join(" ".join(a[2]) for a in mc.APARTADOS)
ok("sin nombres de personas reales ni correos", "@" not in texto)

ma = open(os.path.join(RAIZ, "main_agenda.py"), encoding="utf-8").read()
ok("el botón Manual abre la ventana consultable", "_manual.abrir(ctx, _ruta_manual)" in ma)
ok("el PDF se sigue buscando también dentro del .exe (portátil)", "documento_incluido(MANUAL_NOMBRE)" in ma)
ui = open(os.path.join(RAIZ, "app", "ui", "manual.py"), encoding="utf-8").read()
ok("la ventana permite abrir y guardar el PDF completo", "Abrir el manual completo" in ui and "Guardar una copia" in ui)
spec = open(os.path.join(RAIZ, "main.spec"), encoding="utf-8").read()
ok("módulos nuevos en hiddenimports", "'ui.manual'" in spec and "'utils.manual_consulta'" in spec)

if fallos:
    print(f"\n{len(fallos)} FALLO(S)")
    sys.exit(1)
print("\nManual consultable OK")
