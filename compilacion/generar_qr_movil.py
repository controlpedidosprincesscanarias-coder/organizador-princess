"""Genera el código QR de descarga de Chat Princess para Android (app/ui/qr_chat_movil.png).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python compilacion/generar_qr_movil.py   (necesita «pip install qrcode»; no hace falta en el .exe)
Lleva a la página de la última versión publicada, que no cambia de dirección entre versiones.
"""
import os
import sys

import qrcode

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "app"))
from ui.chat_movil import URL_DESCARGA  # noqa: E402

qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=2)
qr.add_data(URL_DESCARGA)
qr.make(fit=True)
destino = os.path.join(RAIZ, "app", "ui", "qr_chat_movil.png")
qr.make_image(fill_color="#0F1F3D", back_color="white").save(destino)
print("QR guardado en", destino, "→", URL_DESCARGA)
