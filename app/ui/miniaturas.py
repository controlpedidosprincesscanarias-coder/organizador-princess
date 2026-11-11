"""ui/miniaturas.py — miniaturas de las imágenes del chat (v4.18.44).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Antes, una imagen enviada al chat se veía solo como su nombre («📷 foto.jpg») y había que pulsarla
para abrirla. Ahora la ventana del chat y la burbuja enseñan una miniatura encima del nombre.

- La descarga va en un hilo aparte (no se congela la ventana) y pasa por
  ChatClient.descargar_bytes(): solo del almacén de adjuntos, sin redirecciones y con tamaño máximo.
- Se reduce con Pillow a MAX_ANCHO × MAX_ALTO y se guarda en memoria (por URL), para no volver a
  descargarla al cambiar de conversación o al abrir la burbuja.
- Si algo falla (sin conexión, archivo que no es una imagen…), se llama a `listo(None)` y queda solo
  el nombre del archivo, como antes.
"""
import io
import logging
import os
import threading

MAX_ANCHO, MAX_ALTO = 240, 180
_EXTENSIONES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
_cache = {}                 # url -> imagen de Pillow ya reducida
_cerrojo = threading.Lock()


def es_imagen(mensaje) -> bool:
    """True si el mensaje es una imagen adjunta (tipo «imagen» o extensión de imagen)."""
    adjunto = (mensaje or {}).get("adjunto") or {}
    if not adjunto.get("url"):
        return False
    if mensaje.get("tipo") == "imagen":
        return True
    mime = str(adjunto.get("mime_type") or "")
    ext = os.path.splitext(str(adjunto.get("nombre_archivo") or ""))[1].lower()
    return mime.startswith("image/") or ext in _EXTENSIONES


def reducir(datos: bytes):
    """Imagen de Pillow reducida a MAX_ANCHO × MAX_ALTO (sin agrandar), en RGBA."""
    from PIL import Image
    img = Image.open(io.BytesIO(datos))
    img.thumbnail((MAX_ANCHO, MAX_ALTO))
    return img.convert("RGBA")


def cargar(widget, cliente, url, listo):
    """Llama a `listo(PhotoImage | None)` en el hilo de la interfaz cuando la miniatura está lista."""
    def _entregar(img):
        if not widget.winfo_exists():
            return
        foto = None
        if img is not None:
            try:
                from PIL import ImageTk
                foto = ImageTk.PhotoImage(img, master=widget)
            except Exception as exc:  # noqa: BLE001
                logging.getLogger("chat").warning("No se pudo mostrar la miniatura: %s", exc)
        listo(foto)

    with _cerrojo:
        img = _cache.get(url)
    if img is not None:
        widget.after(0, lambda: _entregar(img))
        return

    def _hilo():
        try:
            img_ = reducir(cliente.descargar_bytes(url))
            with _cerrojo:
                _cache[url] = img_
        except Exception as exc:  # noqa: BLE001
            logging.getLogger("chat").warning("Sin miniatura para %s: %s", url, exc)
            img_ = None
        try:
            widget.after(0, lambda: _entregar(img_))
        except RuntimeError:
            pass                    # la ventana se cerró mientras se descargaba
    threading.Thread(target=_hilo, daemon=True, name="Chat-Miniatura").start()
