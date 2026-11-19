"""ui/vista_previa.py — tarjeta de los enlaces de vídeo en el chat (v4.18.74, servidor del chat v1.9.0).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Bajo un mensaje con un enlace de TikTok, YouTube o Instagram sale una tarjeta con la miniatura, el sitio, el
título y el autor; al pulsarla se abre el vídeo en el navegador. Los datos los da el servidor del chat
(ChatClient.vista_previa), una vez por enlace y en un hilo aparte; aquí se guardan en memoria. Si no llegan
(sin conexión o servidor anterior), la tarjeta se queda con el nombre del sitio.
"""
import base64
import io
import logging
import threading
import tkinter as tk
import webbrowser

from utils import enlaces

MAX_ANCHO, MAX_ALTO = 240, 135
_cache = {}                 # url -> (tarjeta | None, imagen de Pillow | None)
_cerrojo = threading.Lock()


def imagen_de(tarjeta):
    """La miniatura de la tarjeta («data:image/…;base64,…») como imagen de Pillow reducida, o None."""
    dato = str((tarjeta or {}).get("miniatura") or "")
    if not dato.startswith("data:image/") or "," not in dato:
        return None
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(base64.b64decode(dato.split(",", 1)[1], validate=True)))
        img.thumbnail((MAX_ANCHO, MAX_ALTO))
        return img.convert("RGBA")
    except Exception as exc:  # noqa: BLE001
        logging.getLogger("chat").info("Miniatura de la vista previa no válida: %s", exc)
        return None


def cargar(widget, cliente, url, listo):
    """Llama a `listo(tarjeta | None, PhotoImage | None)` en el hilo de la interfaz."""
    def _entregar(tarjeta, img):
        if not widget.winfo_exists():
            return
        foto = None
        if img is not None:
            try:
                from PIL import ImageTk
                foto = ImageTk.PhotoImage(img, master=widget)
            except Exception:  # noqa: BLE001
                foto = None
        listo(tarjeta, foto)

    with _cerrojo:
        guardado = _cache.get(url)
    if guardado is not None:
        widget.after(0, lambda: _entregar(*guardado))
        return

    def _hilo():
        try:
            tarjeta = cliente.vista_previa(url)
        except Exception as exc:  # noqa: BLE001
            logging.getLogger("chat").info("Sin vista previa para %s: %s", url, exc)
            tarjeta = None
        img = imagen_de(tarjeta)
        if tarjeta is not None:              # si no llegó, se vuelve a pedir la próxima vez
            with _cerrojo:
                _cache[url] = (tarjeta, img)
        try:
            widget.after(0, lambda: _entregar(tarjeta, img))
        except RuntimeError:
            pass                             # la ventana se cerró mientras tanto
    threading.Thread(target=_hilo, daemon=True, name="Chat-VistaPrevia").start()


def abrir(url):
    if enlaces.abrible(url):
        webbrowser.open(url)


def pintar_tarjeta(padre, url, bg, color_texto, color_meta, color_sitio, fuente, fuente_meta, cargar_tarjeta,
                   seguir_abajo=None):
    """Crea la tarjeta (Frame) bajo la burbuja y la rellena cuando llegan los datos. `seguir_abajo()` devuelve una
    función que, llamada tras crecer la tarjeta, vuelve al final de la conversación si se estaba al final."""
    tarjeta = tk.Frame(padre, bg=bg, bd=0, cursor="hand2")
    lbl_img = tk.Label(tarjeta, text="▶", bg="#000000", fg="#ffffff", font=(fuente.actual("family"), 18, "bold"),
                       width=0, padx=14, pady=6, cursor="hand2")
    lbl_img.pack(anchor="w", fill="x")
    lbl_sitio = tk.Label(tarjeta, text=f"▶  {enlaces.nombre_sitio(url)}", bg=bg, fg=color_sitio,
                         font=(fuente_meta.actual("family"), fuente_meta.actual("size"), "bold"), anchor="w",
                         cursor="hand2")
    lbl_sitio.pack(anchor="w", fill="x", padx=8, pady=(4, 0))
    lbl_titulo = tk.Label(tarjeta, text="", bg=bg, fg=color_texto, font=fuente, anchor="w", justify="left",
                          wraplength=MAX_ANCHO, cursor="hand2")
    lbl_autor = tk.Label(tarjeta, text="", bg=bg, fg=color_meta, font=fuente_meta, anchor="w", cursor="hand2")
    widgets = [tarjeta, lbl_img, lbl_sitio, lbl_titulo, lbl_autor]
    for w in widgets:
        w.bind("<Button-1>", lambda e: abrir(url))

    def _listo(datos, foto):
        if not tarjeta.winfo_exists():
            return
        # (v4.18.74) La tarjeta crece al llegar la miniatura: si se estaba al final, se sigue al final
        volver = seguir_abajo() if seguir_abajo else None
        if foto is not None:
            lbl_img.configure(image=foto, text="", padx=0, pady=0, bg=bg)
            lbl_img.image = foto
        if datos:
            lbl_sitio.configure(text=f"▶  {datos.get('sitio') or enlaces.nombre_sitio(url)}")
            titulo = " ".join(str(datos.get("titulo") or "").split())
            if titulo:
                lbl_titulo.configure(text=titulo[:120])
                lbl_titulo.pack(anchor="w", fill="x", padx=8)
            autor = str(datos.get("autor") or "").strip()
            if autor:
                lbl_autor.configure(text=autor[:60])
                lbl_autor.pack(anchor="w", fill="x", padx=8)
        tk.Frame(tarjeta, bg=bg, height=4).pack()
        if volver:
            volver()

    if cargar_tarjeta is not None:
        cargar_tarjeta(url, _listo)
    else:
        _listo(None, None)
    return tarjeta, widgets
