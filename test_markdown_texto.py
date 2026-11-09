"""Novedades de versión en Markdown mostradas con formato (ui/markdown_texto.py, v4.18.10).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_markdown_texto.py   (no necesita Tkinter)
"""
import os
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(RAIZ, "app"))
from ui.markdown_texto import analizar  # noqa: E402

fallos = []
def ok(nombre, cond, det=""):
    print(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
    if not cond:
        fallos.append(nombre)

def texto(r):
    return "".join(t for t, _ in r)

def con(r, etiqueta):
    return "".join(t for t, e in r if etiqueta in e)

r = analizar("# ✨ Organizador Princess v4.18.10\n\n## 🛠 Corrección\n\n- **Chat:** arreglado `config.json`.\n- Otra cosa\n")
ok("sin «#» ni «**» ni «`» en el texto mostrado", not any(s in texto(r) for s in ("#", "**", "`")), texto(r))
ok("título principal", con(r, "titulo1") == "✨ Organizador Princess v4.18.10", con(r, "titulo1"))
ok("subtítulo", con(r, "titulo2") == "🛠 Corrección", con(r, "titulo2"))
ok("viñetas con «•»", texto(r).count("•") == 2, texto(r))
ok("negrita dentro de una viñeta", any(t == "Chat:" and "negrita" in e and "vineta" in e for t, e in r), r)
ok("código en línea", con(r, "codigo") == "config.json", con(r, "codigo"))

r = analizar("Texto\n\n---\n\n================================================================\n\nFin")
ok("separadores --- y ==== se dibujan como línea", sum(1 for _, e in r if "separador" in e) == 2, r)

r = analizar("los símbolos `#` y `**` se ven tal cual")
ok("símbolos escritos como código se muestran literalmente", texto(r) == "los símbolos # y ** se ven tal cual" and con(r, "codigo") == "#**", texto(r))

r = analizar("> Incluye también la 4.18.06.\n1. Uno\n2. Dos\n  - sub")
ok("cita en cursiva", con(r, "cita") == "Incluye también la 4.18.06.", con(r, "cita"))
ok("lista numerada", "1.  Uno" in texto(r) and "2.  Dos" in texto(r), texto(r))
ok("viñeta anidada con sangría", "    •  sub" in texto(r), texto(r))

r = analizar("Línea con \\r\\n\r\nsegunda\r\n\r\n\r\n\r\ntercera")
ok("saltos de línea de Windows y huecos múltiples", texto(r) == "Línea con \\r\\n\nsegunda\n\ntercera", repr(texto(r)))
ok("texto vacío o None", analizar("") == [] and analizar(None) == [])
ok("asteriscos sueltos no rompen nada", texto(analizar("2 * 3 = 6")) == "2 * 3 = 6", texto(analizar("2 * 3 = 6")))

# Las notas reales de release_notes.md se muestran sin símbolos de Markdown
notas = open(os.path.join(RAIZ, "release_notes", "release_notes.md"), encoding="utf-8").read().split("\n---")[0]
t = "".join(x for x, e in analizar(notas) if "codigo" not in e)   # lo marcado como código se muestra tal cual
ok("las notas de la versión actual se ven sin «#» ni «**»", "**" not in t and not any(l.startswith("#") for l in t.splitlines()), t[:200])

print(f"\n{'Todas las comprobaciones OK.' if not fallos else str(len(fallos)) + ' fallo(s)'}")
sys.exit(1 if fallos else 0)
