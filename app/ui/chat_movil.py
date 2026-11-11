"""
app/ui/chat_movil.py  ·  v4.18.44
Ventana «Chat en el móvil»: cómo instalar Chat Dpto. Compras Princess para Android, con un código QR.

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

La app Android (repo público chat-movil-princess) es el mismo chat, con la misma cuenta de Control de
Pedidos: se puede estar conectado a la vez en el Organizador y en el móvil.
"""
import os
import tkinter as tk
import webbrowser

import ttkbootstrap as ttk

from ui.assets import _apply_icon

# (v4.18.44) El QR descarga la .apk directamente (Víctor: «sin tener que pasar y seleccionar en la cuenta
# de GitHub»). Cada Release del móvil publica, además de ChatPrincess_<versión>.apk, una copia idéntica con
# nombre fijo, ChatPrincess.apk, que es la que da este enlace (workflow compilar.yml del repo del móvil).
URL_DESCARGA = "https://github.com/controlpedidosprincesscanarias-coder/chat-movil-princess/releases/latest/download/ChatPrincess.apk"
URL_PAGINA = "https://github.com/controlpedidosprincesscanarias-coder/chat-movil-princess/releases/latest"
_QR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qr_chat_movil.png")
_ABIERTA = [None]

PASOS = [
    "Escanea el código con la cámara del móvil (o abre el enlace en el móvil).",
    "Se descarga «ChatPrincess.apk» directamente. Si el navegador avisa de que «puede ser dañino», "
    "pulsa «Descargar de todas formas».",
    "Abre el archivo descargado. La primera vez, Android pide permitir «Instalar apps desconocidas»: "
    "actívalo, vuelve atrás y pulsa «Instalar».",
    "Si aparece Google Play Protect («App no segura» o «App desconocida»), toca «Más detalles» → "
    "«Instalar de todas formas». Es normal: la app no viene de Google Play.",
    "Entra con tu usuario y tu contraseña de Control de Pedidos y acepta las notificaciones.",
    "En Ajustes de la app, pulsa «Quitar el ahorro de batería» para recibir los avisos con la app cerrada.",
]


def abrir_chat_movil(parent):
    """Abre (o trae al frente) la ventana con el QR y los pasos."""
    if _ABIERTA[0] is not None and _ABIERTA[0].winfo_exists():
        _ABIERTA[0].lift()
        return _ABIERTA[0]
    win = ttk.Toplevel(parent)
    win.title("📱 Chat en el móvil")
    win.resizable(False, False)
    _apply_icon(win)
    _ABIERTA[0] = win

    cuerpo = ttk.Frame(win, padding=(20, 16, 20, 12))
    cuerpo.pack(fill="both", expand=True)
    ttk.Label(cuerpo, text="📱  Chat Dpto. Compras Princess para Android", font=("Segoe UI", 13, "bold")).pack(anchor="w")
    ttk.Label(cuerpo, text="El mismo chat, con tu cuenta de Control de Pedidos. Puedes tenerlo a la vez\n"
                           "en el Organizador y en el móvil: los mensajes llegan a los dos.",
              font=("Segoe UI", 9), foreground="#adb5bd", justify="left").pack(anchor="w", pady=(4, 12))

    fila = ttk.Frame(cuerpo)
    fila.pack(fill="x")
    try:
        img = tk.PhotoImage(file=_QR)
        win._qr = img   # Tk necesita que la imagen siga viva
        tk.Label(fila, image=img, bg="white", bd=0).pack(side="left", padx=(0, 16))
    except tk.TclError:
        pass
    pasos = ttk.Frame(fila)
    pasos.pack(side="left", fill="both", expand=True)
    for i, t in enumerate(PASOS, 1):
        ttk.Label(pasos, text=f"{i}.  {t}", wraplength=340, justify="left", font=("Segoe UI", 9)).pack(anchor="w", pady=3)

    enlace = ttk.Label(cuerpo, text=URL_DESCARGA, foreground="#5bc0de", cursor="hand2", font=("Segoe UI", 8, "underline"))
    enlace.pack(anchor="w", pady=(12, 2))
    enlace.bind("<Button-1>", lambda e: webbrowser.open(URL_DESCARGA))
    ttk.Label(cuerpo, text="Actualizaciones: la app avisa sola al abrirse cuando hay una versión nueva; se descarga\n"
                           "desde la propia app y Android pide confirmar «Actualizar» (si sale Play Protect: «Más detalles» →\n"
                           "«Instalar de todas formas»).",
              font=("Segoe UI", 8), foreground="#adb5bd", justify="left").pack(anchor="w", pady=(6, 0))

    ttk.Separator(win).pack(fill="x")
    pie = ttk.Frame(win, padding=(20, 8, 20, 12))
    pie.pack(fill="x")
    ttk.Button(pie, text="🌐  Abrir el enlace", bootstyle="info-outline",
               command=lambda: webbrowser.open(URL_DESCARGA)).pack(side="left")
    ttk.Button(pie, text="📜  Página de versiones", bootstyle="info-outline",
               command=lambda: webbrowser.open(URL_PAGINA)).pack(side="left", padx=(6, 0))
    ttk.Button(pie, text="Cerrar", bootstyle="secondary", command=win.destroy).pack(side="right")
    win.update_idletasks()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    win.geometry(f"+{(win.winfo_screenwidth() - w) // 2}+{(win.winfo_screenheight() - h) // 2}")
    return win
