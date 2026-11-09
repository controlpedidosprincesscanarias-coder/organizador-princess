"""
ui/markdown_texto.py
Muestra en un tk.Text las novedades de una versión escritas en Markdown (el «body» de la Release de
GitHub), con formato en vez de los símbolos «#», «**»… (v4.18.10).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Solo lo que usan las notas de versión: títulos (#, ##, ###), viñetas (- / * / 1.), **negrita**,
`código`, citas (>) y separadores (--- / ===). Lo demás se muestra como texto normal.
analizar() no depende de Tkinter (se prueba en test_markdown_texto.py); pintar() lo vuelca en un Text.
"""
import re

_RE_EN_LINEA = re.compile(r"(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`)")
_RE_TITULO = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_RE_VINETA = re.compile(r"^(\s*)[-*+]\s+(.*)$")
_RE_NUMERADA = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
_RE_SEPARADOR = re.compile(r"^\s*([-=_*])\1{2,}\s*$")


def _en_linea(texto, base=()):
    """Trocea **negrita**, __negrita__ y `código` dentro de una línea."""
    trozos = []
    for parte in _RE_EN_LINEA.split(texto):
        if not parte:
            continue
        if (parte.startswith("**") and parte.endswith("**")) or (parte.startswith("__") and parte.endswith("__")):
            trozos.append((parte[2:-2], tuple(base) + ("negrita",)))
        elif parte.startswith("`") and parte.endswith("`"):
            trozos.append((parte[1:-1], tuple(base) + ("codigo",)))
        else:
            trozos.append((parte, tuple(base)))
    return trozos


def analizar(markdown):
    """Lista de (texto, etiquetas) lista para insertar en un Text. Las etiquetas posibles son:
    titulo1, titulo2, titulo3, vineta, cita, negrita, codigo y separador."""
    salida = []
    lineas = (markdown or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    anterior_vacia = True
    for linea in lineas:
        if not linea.strip():
            if not anterior_vacia:
                salida.append(("\n", ()))
            anterior_vacia = True
            continue
        anterior_vacia = False
        m = _RE_TITULO.match(linea)
        if m:
            nivel = min(len(m.group(1)), 3)
            salida.extend(_en_linea(m.group(2), (f"titulo{nivel}",)))
            salida.append(("\n", ()))
            continue
        if _RE_SEPARADOR.match(linea):
            salida.append(("─" * 40 + "\n", ("separador",)))
            continue
        m = _RE_VINETA.match(linea)
        if m:
            sangria = "    " * (len(m.group(1).expandtabs(4)) // 2)
            salida.append((f"{sangria}•  ", ("vineta",)))
            salida.extend(_en_linea(m.group(2), ("vineta",)))
            salida.append(("\n", ()))
            continue
        m = _RE_NUMERADA.match(linea)
        if m:
            sangria = "    " * (len(m.group(1).expandtabs(4)) // 2)
            salida.append((f"{sangria}{m.group(2)}.  ", ("vineta",)))
            salida.extend(_en_linea(m.group(3), ("vineta",)))
            salida.append(("\n", ()))
            continue
        if linea.lstrip().startswith(">"):
            salida.extend(_en_linea(linea.lstrip()[1:].strip(), ("cita",)))
            salida.append(("\n", ()))
            continue
        salida.extend(_en_linea(linea.strip()))
        salida.append(("\n", ()))
    while salida and salida[-1] == ("\n", ()):
        salida.pop()
    return salida


def pintar(txt, markdown, fuente=("Segoe UI", 9), color_titulo="#C9A84C", color_codigo="#F0C674"):
    """Vuelca `markdown` con formato en el tk.Text `txt` (que debe estar en state="normal")."""
    familia, tam = fuente[0], fuente[1]
    txt.tag_configure("titulo1", font=(familia, tam + 4, "bold"), foreground=color_titulo, spacing1=4, spacing3=4)
    txt.tag_configure("titulo2", font=(familia, tam + 2, "bold"), foreground=color_titulo, spacing1=6, spacing3=2)
    txt.tag_configure("titulo3", font=(familia, tam + 1, "bold"), spacing1=4)
    txt.tag_configure("vineta", lmargin1=8, lmargin2=26)
    txt.tag_configure("cita", font=(familia, tam, "italic"), lmargin1=12, lmargin2=12)
    txt.tag_configure("negrita", font=(familia, tam, "bold"))
    txt.tag_configure("codigo", font=("Consolas", tam), foreground=color_codigo)
    txt.tag_configure("separador", foreground="#5A6A7A")
    for texto, etiquetas in analizar(markdown):
        txt.insert("end", texto, etiquetas)
