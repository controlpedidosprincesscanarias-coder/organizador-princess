"""Genera las imágenes en color de los emoticonos del chat (app/ui/emoticonos_color/).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Tkinter en Windows dibuja los emoticonos de un solo color; por eso el panel 😊 usa estas imágenes.
Se dibujan con la fuente libre Noto Color Emoji (licencia SIL OFL 1.1).
Uso: python compilacion/generar_emoticonos.py [ruta de NotoColorEmoji.ttf]
Solo hace falta volver a ejecutarlo si cambia la lista de app/ui/emoticonos.py.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "app"))
from ui.emoticonos import EMOTICONOS, RESPUESTAS, nombre_imagen  # noqa: E402

FUENTE = sys.argv[1] if len(sys.argv) > 1 else "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
TAMANOS = {"": 28, "_p": 18}     # panel y respuestas rápidas
DESTINO = os.path.join(RAIZ, "app", "ui", "emoticonos_color")


def dibujar(emoji, lado):
    f = ImageFont.truetype(FUENTE, 109)          # la fuente de color solo tiene este tamaño
    lienzo = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(lienzo).text((80, 80), emoji, font=f, embedded_color=True, anchor="mm")
    caja = lienzo.getbbox()
    if caja is None:
        raise SystemExit(f"La fuente no tiene el emoticono {emoji!r}")
    recorte = lienzo.crop(caja)
    escala = lado / max(recorte.size)
    recorte = recorte.resize((max(1, round(recorte.width * escala)), max(1, round(recorte.height * escala))), Image.LANCZOS)
    final = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
    final.paste(recorte, ((lado - recorte.width) // 2, (lado - recorte.height) // 2), recorte)
    return final


os.makedirs(DESTINO, exist_ok=True)
todos = list(dict.fromkeys(EMOTICONOS + [r.split(" ", 1)[0] for r in RESPUESTAS]))
for e in todos:
    for sufijo, lado in TAMANOS.items():
        dibujar(e, lado).save(os.path.join(DESTINO, nombre_imagen(e, sufijo)), optimize=True)
print(f"{len(todos)} emoticonos en {DESTINO}")
