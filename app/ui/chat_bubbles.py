"""
ui/chat_bubbles.py  ·  v1.0  ·  © VAMA 2026
=============================================
Widget de burbujas de chat compartido entre la ventana principal
(ui/ventana_chat.py) y la burbuja flotante (ui/chat_popup.py).

Sustituye al tk.Text con tags de color que usaba cada ventana por su
cuenta (dos implementaciones casi idénticas, mantenidas por separado)
por un único widget: burbujas de verdad (rectángulos redondeados
dibujados en Canvas), con hora, copia por clic derecho y scroll suave
con la rueda del ratón.

Es una capa de PRESENTACIÓN únicamente — no sabe nada de sockets, de
ChatClient ni de canales. Cada ventana sigue manejando su propia
lógica de red exactamente igual que antes; solo cambia cómo se pinta
cada mensaje ya recibido.
"""

import tkinter as tk
import ui.emoticonos as _emo
import tkinter.font as tkfont
from datetime import datetime


def hora_local(mensaje: dict) -> str:
    """HH:MM en hora local a partir de creado_en (se asume UTC si trae
    sufijo 'Z', como devuelve el backend). Cadena vacía si no se puede
    interpretar — nunca lanza excepción hacia quien pinta el mensaje."""
    ts = mensaje.get("creado_en", "")
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone()
        return dt.strftime("%H:%M")
    except Exception:  # noqa: BLE001
        return ""


def fecha_hora_local(mensaje: dict) -> str:
    """DD/MM HH:MM en hora local — igual que hora_local() pero con la
    fecha delante, para las burbujas de chat (2026-07-29)."""
    ts = mensaje.get("creado_en", "")
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone()
        return dt.strftime("%d/%m %H:%M")
    except Exception:  # noqa: BLE001
        return ""


# (v4.18.22) Emoticonos en color dentro de los mensajes: Tk en Windows los dibuja de un solo
# color, así que los del panel 😊 (ui/emoticonos.py) se pintan como imagen. Los demás, como texto.
_VS16 = "\ufe0f"   # selector de variante: Tk lo pinta como un recuadro


def _trocear(linea, conocidos):
    """Parte una línea en [("t", texto) | ("e", emoticono)], con los emoticonos de `conocidos`."""
    linea = linea.replace(_VS16, "")
    trozos, actual, i = [], "", 0
    while i < len(linea):
        hallado = next((e for e in conocidos if linea.startswith(e, i)), None)
        if hallado:
            if actual:
                trozos.append(("t", actual))
                actual = ""
            trozos.append(("e", hallado))
            i += len(hallado)
        else:
            actual += linea[i]
            i += 1
    if actual:
        trozos.append(("t", actual))
    return trozos


def _puntos_rect_redondeado(x1, y1, x2, y2, r):
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    return [
        x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
    ]


class BubbleList(tk.Frame):
    """Contenedor con scroll para una lista de burbujas de chat, apiladas
    de arriba a abajo — la más antigua arriba, la más reciente abajo,
    justo encima de donde vaya la caja de escribir en cada ventana
    (eso lo decide quien use el widget, empaquetándolo antes o después
    de su propia fila de envío)."""

    def __init__(self, master, bg="#1b2735", color_propio="#1f8f63",
                 color_ajeno="#3a4a63", color_texto="#f2f5f8",
                 color_meta="#9fb2c4", ancho_max_burbuja=None,
                 font_texto=("Segoe UI", 9), font_meta=("Segoe UI", 7),
                 on_click_adjunto=None, **kw):
        super().__init__(master, bg=bg, **kw)
        self._bg = bg
        self._color_propio = color_propio
        self._color_ajeno = color_ajeno
        self._color_texto = color_texto
        self._color_meta = color_meta
        self._ancho_max = ancho_max_burbuja
        self._font_texto = tkfont.Font(font=font_texto)
        self._font_meta = tkfont.Font(font=font_meta)
        self._on_click_adjunto = on_click_adjunto

        self.canvas = tk.Canvas(self, bg=bg, bd=0, highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self._bind_rueda(self.canvas)
        self._bind_rueda(self.inner)

    # ── scroll suave con la rueda del ratón ─────────────────────────────
    def _on_inner_configure(self, _event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        if self._ancho_max is None:
            self.canvas.itemconfigure(self._win_id, width=event.width)

    def _bind_rueda(self, widget):
        widget.bind("<MouseWheel>", self._rueda, add="+")            # Windows
        widget.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-2, "units"), add="+")
        widget.bind("<Button-5>", lambda e: self.canvas.yview_scroll(2, "units"), add="+")

    def _rueda(self, event):
        self.canvas.yview_scroll(int(-event.delta / 40), "units")

    def _ir_al_final(self):
        self.canvas.update_idletasks()
        self.canvas.yview_moveto(1.0)

    def limpiar(self):
        """Borra todas las burbujas — para cuando se cambia de canal."""
        for w in self.inner.winfo_children():
            w.destroy()

    # ── burbujas ─────────────────────────────────────────────────────────
    def agregar_burbuja(self, texto, hora, propio, meta_nombre=None,
                         es_adjunto=False, adjunto_url=None,
                         adjunto_nombre_archivo=None):
        fila = tk.Frame(self.inner, bg=self._bg)
        fila.pack(fill="x", pady=(2, 2), padx=6)
        self._bind_rueda(fila)

        contenedor = tk.Frame(fila, bg=self._bg)
        contenedor.pack(side="right" if propio else "left",
                         anchor="e" if propio else "w")

        if meta_nombre:
            tk.Label(contenedor, text=meta_nombre, bg=self._bg,
                     fg=self._color_meta, font=self._font_meta,
                     ).pack(anchor="e" if propio else "w")

        ancho_disponible = self._ancho_max or max(220, int(self.canvas.winfo_width() * 0.68) or 220)
        lineas = self._envolver_texto(texto or "", ancho_disponible - 24)
        trozos_lineas = [self._trozos(l) for l in lineas]
        ancho_texto = max((self._ancho_trozos(t) for t in trozos_lineas), default=0)
        ancho_hora = self._font_meta.measure(hora) if hora else 0
        ancho_bloque = max(ancho_texto, ancho_hora) + 24
        alto_linea = self._font_texto.metrics("linespace") + 2
        alto_bloque = len(lineas) * alto_linea + 16 + (14 if hora else 0)

        color = self._color_propio if propio else self._color_ajeno
        cv = tk.Canvas(contenedor, width=ancho_bloque, height=alto_bloque,
                        bg=self._bg, bd=0, highlightthickness=0,
                        cursor="hand2" if es_adjunto else "")
        cv.pack()
        pts = _puntos_rect_redondeado(1, 1, ancho_bloque - 1, alto_bloque - 1, 12)
        cv.create_polygon(pts, smooth=True, fill=color, outline=color)

        y = 8
        for trozos in trozos_lineas:
            x = 12
            for tipo, valor in trozos:
                if tipo == "e":
                    img = _emo.imagen(valor, pequena=True)
                    cv.create_image(x, y + alto_linea // 2 - 1, image=img, anchor="w")
                    x += img.width() + 1
                    continue
                item = cv.create_text(x, y, text=valor, anchor="nw",
                                       fill=self._color_texto, font=self._font_texto)
                if es_adjunto:
                    bbox = cv.bbox(item)
                    cv.create_line(bbox[0], bbox[3] + 1, bbox[2], bbox[3] + 1,
                                    fill=self._color_texto)
                x += self._font_texto.measure(valor)
            y += alto_linea

        if hora:
            cv.create_text(ancho_bloque - 8, alto_bloque - 6, text=hora,
                            anchor="se", fill=self._color_texto, font=self._font_meta)

        if es_adjunto and self._on_click_adjunto and adjunto_url:
            cv.bind("<Button-1>",
                    lambda e: self._on_click_adjunto(adjunto_url, adjunto_nombre_archivo))

        # ── Copiar texto (clic derecho → menú contextual) ──────────────
        # No dependemos de la selección nativa de un Canvas (no existe
        # arrastre-para-seleccionar como en un Text) — cada burbuja
        # sabe su propio texto y lo copia entero al portapapeles.
        texto_copia = texto or ""
        menu = tk.Menu(cv, tearoff=0)
        menu.add_command(label="📋  Copiar mensaje",
                          command=lambda t=texto_copia: self._copiar(t))

        def _click_derecho(e, m=menu):
            try:
                m.tk_popup(e.x_root, e.y_root)
            finally:
                m.grab_release()

        cv.bind("<Button-3>", _click_derecho)
        self._bind_rueda(cv)
        self._bind_rueda(contenedor)

        self._ir_al_final()
        return cv

    def _trozos(self, linea):
        """Trozos de texto y emoticonos en color (solo los que tienen imagen)."""
        conocidos = [e for e in _emo.conocidos() if _emo.imagen(e, pequena=True) is not None]
        return _trocear(linea, conocidos) if conocidos else [("t", linea.replace(_VS16, ""))]

    def _ancho_trozos(self, trozos):
        return sum(_emo.imagen(v, pequena=True).width() + 1 if t == "e" else self._font_texto.measure(v)
                   for t, v in trozos)

    def _copiar(self, texto):
        self.clipboard_clear()
        self.clipboard_append(texto)

    def _envolver_texto(self, texto, ancho_px):
        """Envuelve `texto` en líneas que no superen ancho_px, respetando
        los saltos de línea que ya traiga el mensaje."""
        lineas_final = []
        for parrafo in texto.split("\n"):
            palabras = parrafo.split(" ")
            actual = ""
            for palabra in palabras:
                prueba = f"{actual} {palabra}".strip()
                if self._font_texto.measure(prueba) <= ancho_px or not actual:
                    actual = prueba
                else:
                    lineas_final.append(actual)
                    actual = palabra
            lineas_final.append(actual)
        return lineas_final or [""]
