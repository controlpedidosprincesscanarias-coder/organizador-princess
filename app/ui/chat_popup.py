"""
ui/chat_popup.py  ·  v1.0  ·  © VAMA 2026
==========================================
Ventana emergente flotante de chat, anclada abajo a la derecha de la
pantalla (estilo "cabezas de chat" de Facebook Messenger). Se abre sola
cuando llega un mensaje nuevo y no hay forma más directa de verlo (la
ventana principal de ui/ventana_chat.py no está abierta), para poder
leer y responder sin tener que abrir la ventana completa.

Varias conversaciones pueden tener su propia burbuja abierta a la vez;
se apilan de derecha a izquierda. Cerrar una no afecta a las demás ni a
la ventana principal — son independientes, comparten el mismo
ChatClient (y por tanto la misma conexión de socket) pero cada una
pinta solo los mensajes de su propio canal_id.

INTEGRACIÓN CON poll_chat (main_agenda.py)
-------------------------------------------
Igual que ui/ventana_chat.py expone un único _HANDLER para la ventana
principal, este módulo expone procesar_evento(ev), que poll_chat llama
SIEMPRE (haya o no burbujas abiertas) para repartir cada evento a la
burbuja que corresponda por canal_id. Abrir una burbuja nueva para un
mensaje que llega sin ninguna burbuja ni ventana principal abierta lo
decide main_agenda.py, no este módulo — aquí solo se expone
mostrar_popup_chat() para que lo invoque cuando corresponda.
"""

import os
import tempfile
import threading
import logging
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

from services.chat_client import get_chat_client, nombre_adjunto_seguro, es_canal_avisos, EVT_NUEVO_MENSAJE, EVT_AVATAR, EVT_ELIMINADO, EVT_GRUPO
from ui import avatares, miniaturas, acciones_chat
from ui.chat_bubbles import BubbleList, fecha_hora_local
from ui.emoticonos import abrir_panel, imagen as imagen_emoticono
from db.sqlite import filtrar_mensajes_limpiados

_POPUPS = {}   # canal_id -> {"win", "pintar", "handler"}

_ANCHO, _ALTO = 330, 380   # (v4.18.18) 330: cabe también el botón 😊
_MARGEN = 16
_SEPARACION = 10
_ALTO_BARRA_TAREAS = 48   # hueco aproximado para no tapar la barra de Windows

# ── Paleta (a juego con el resto del Organizador, pero con más contraste
#    que el chat de texto plano anterior — burbujas de verdad, no solo
#    texto de color sobre fondo plano) ────────────────────────────────────
_COLOR_FONDO  = "#1b2735"
_COLOR_HEADER = "#134e6f"
_COLOR_PROPIO = "#1f8f63"
_COLOR_AJENO  = "#3a4a63"
_COLOR_TEXTO  = "#e8edf2"
_COLOR_META   = "#8fa3b8"
_COLOR_ENTRY  = "#25313f"


def _posicion_libre(app):
    """Esquina inferior derecha, apilando hacia la izquierda si ya hay
    otras burbujas abiertas (como los chats de Messenger)."""
    sw = app.winfo_screenwidth()
    sh = app.winfo_screenheight()
    x = sw - _ANCHO - _MARGEN
    y = sh - _ALTO - _MARGEN - _ALTO_BARRA_TAREAS
    ocupadas = [info["win"].winfo_x() for info in _POPUPS.values()
                if info["win"].winfo_exists()]
    for ox in sorted(ocupadas, reverse=True):
        if abs(ox - x) < _ANCHO:
            x = ox - _ANCHO - _SEPARACION
    return x, y


def cerrar_todas():
    """Por si se necesita desde algún flujo de cierre general de la app."""
    for canal_id in list(_POPUPS.keys()):
        info = _POPUPS.pop(canal_id, None)
        if info and info["win"].winfo_exists():
            info["win"].destroy()


def procesar_evento(ev):
    """Llamado por poll_chat() en main_agenda.py para CADA evento del
    chat, haya o no burbujas abiertas ahora mismo."""
    if ev.get("tipo") == EVT_AVATAR:
        for info in list(_POPUPS.values()):
            if info["win"].winfo_exists() and info.get("foto"):
                info["foto"]()
        return
    if ev.get("tipo") == EVT_GRUPO:
        # (v4.18.48) Si se elimina el grupo, se cierra su burbuja; si cambia, se recarga
        g = ev.get("grupo") or {}
        info = _POPUPS.get(g.get("canal_id"))
        if info and info["win"].winfo_exists():
            if g.get("eliminado"):
                info["win"].destroy()
            elif info.get("recargar"):
                info["recargar"]()
        return
    if ev.get("tipo") == EVT_ELIMINADO:
        # (v4.18.46) Un mensaje eliminado: la burbuja de ese canal vuelve a cargar la conversación
        info = _POPUPS.get((ev.get("mensaje") or {}).get("canal_id"))
        if info and info["win"].winfo_exists() and info.get("recargar"):
            info["recargar"]()
        return
    if ev.get("tipo") != EVT_NUEVO_MENSAJE:
        return
    m = ev["mensaje"]
    info = _POPUPS.get(m.get("canal_id"))
    if info and info["win"].winfo_exists():
        info["pintar"](m)


def mostrar_popup_chat(ctx, canal_id, titulo, mensaje_inicial=None, borrador=""):
    """Abre una burbuja nueva para `canal_id`, o si ya existe la trae al
    frente — y en ambos casos pinta `mensaje_inicial` si se da uno.
    `borrador` (v4.18.16): texto a medio escribir en la ventana grande, que
    se cerró para seguir la conversación aquí."""
    cliente = get_chat_client()

    if canal_id in _POPUPS and _POPUPS[canal_id]["win"].winfo_exists():
        info = _POPUPS[canal_id]
        info["win"].deiconify()
        info["win"].lift()
        if mensaje_inicial:
            info["pintar"](mensaje_inicial)
        return

    win = tk.Toplevel(ctx.app)
    win.overrideredirect(True)          # sin marco nativo — burbuja "flotante"
    win.attributes("-topmost", True)
    win.configure(bg=_COLOR_FONDO, highlightthickness=1,
                  highlightbackground="#2f4258")
    x, y = _posicion_libre(ctx.app)
    win.geometry(f"{_ANCHO}x{_ALTO}+{x}+{y}")

    # ── Cabecera (arrastrable, con cerrar / abrir ventana completa) ────────
    header = tk.Frame(win, bg=_COLOR_HEADER, height=36)
    header.pack(fill="x")
    header.pack_propagate(False)
    # (v4.18.28) Foto de la persona o del grupo (o sus iniciales) en vez del 💬
    lbl_foto = tk.Label(header, bg=_COLOR_HEADER, bd=0)
    lbl_foto.pack(side="left", padx=(8, 0))

    def _pintar_foto():
        if not win.winfo_exists():
            return
        if canal_id == "general":
            img = avatares.imagen_general(win, 26)
        elif str(canal_id).startswith("grp:"):
            img = avatares.imagen_grupo(win, cliente.avatar_canal(canal_id), titulo.replace("  (grupo)", ""),
                                        26, canal_id=canal_id, al_cargar=_pintar_foto)
        else:
            otro = None
            if str(canal_id).startswith("dm:") and cliente.username:
                otros = [p for p in canal_id[3:].split(":") if p.lower() != cliente.username.lower()]
                otro = otros[0] if otros else None
            img = avatares.imagen(win, cliente.avatar_canal(canal_id), titulo, 26, clave=otro,
                                  al_cargar=_pintar_foto)
        lbl_foto.configure(image=img)
        lbl_foto.image = img
    _pintar_foto()
    tk.Label(header, text=titulo, bg=_COLOR_HEADER, fg="white",
              font=("Segoe UI", 10, "bold")).pack(side="left", padx=(8, 10))

    def _cerrar():
        _POPUPS.pop(canal_id, None)
        if win.winfo_exists():
            win.destroy()

    def _abrir_completa():
        _cerrar()
        from ui.ventana_chat import _ventana_chat
        _ventana_chat(ctx)

    tk.Button(header, text="⤢", bg=_COLOR_HEADER, fg="white", bd=0,
              activebackground=_COLOR_HEADER, activeforeground="white",
              relief="flat", cursor="hand2", command=_abrir_completa,
              font=("Segoe UI", 10)).pack(side="right", padx=(0, 2))
    tk.Button(header, text="✕", bg=_COLOR_HEADER, fg="white", bd=0,
              activebackground=_COLOR_HEADER, activeforeground="white",
              relief="flat", cursor="hand2", command=_cerrar,
              font=("Segoe UI", 10)).pack(side="right", padx=(0, 6))

    _drag = {"x": 0, "y": 0}
    def _drag_start(e):
        _drag["x"], _drag["y"] = e.x, e.y
    def _drag_move(e):
        win.geometry(f"+{win.winfo_x() + e.x - _drag['x']}+{win.winfo_y() + e.y - _drag['y']}")
    header.bind("<ButtonPress-1>", _drag_start)
    header.bind("<B1-Motion>", _drag_move)

    # ── Entrada de texto — se crea y empaqueta ANTES que la zona de
    #    mensajes (2026-07-28, mismo criterio que ya se aplicó hoy en
    #    ventana_chat.py): así reserva siempre su hueco de abajo, en vez
    #    de depender de un height= fijo adivinado a mano como hacía la
    #    versión anterior (ver el ANTI-REGRESION de más arriba, que ya
    #    no hace falta con este orden).
    frm_envio = tk.Frame(win, bg=_COLOR_FONDO)
    frm_envio.pack(side="bottom", fill="x", padx=6, pady=(0, 6))
    entry = tk.Entry(frm_envio, bg=_COLOR_ENTRY, fg="white",
                      insertbackground="white", bd=0,
                      font=("Segoe UI", 9))
    entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 4))
    if borrador:
        entry.insert(0, borrador)
    if es_canal_avisos(canal_id):           # (v4.18.50) avisos de Control Pedidos: solo lectura
        entry.insert(0, "Solo avisos de Control Pedidos")
        entry.configure(state="disabled", disabledbackground=_COLOR_ENTRY, disabledforeground=_COLOR_META)

    # (v4.18.46) Barra «↩ Respondiendo a …» encima de la caja de escribir
    respondiendo = {"m": None}
    frm_resp = tk.Frame(win, bg=_COLOR_FONDO)
    lbl_resp = tk.Label(frm_resp, text="", bg=_COLOR_FONDO, fg=_COLOR_META, font=("Segoe UI", 8),
                        anchor="w", justify="left", wraplength=260)
    lbl_resp.pack(side="left", fill="x", expand=True)

    def _cancelar_respuesta():
        respondiendo["m"] = None
        frm_resp.pack_forget()

    tk.Button(frm_resp, text="✕", bg=_COLOR_FONDO, fg=_COLOR_META, bd=0, relief="flat",
              activebackground=_COLOR_FONDO, command=_cancelar_respuesta).pack(side="right")

    def _responder(m):
        respondiendo["m"] = m
        lbl_resp.configure(text=acciones_chat.resumen_barra(m, cliente))
        frm_resp.pack(side="bottom", fill="x", padx=6, after=frm_envio)
        entry.focus_set()

    def _click_adjunto(url, nombre_archivo):
        def _hilo():
            try:
                ruta = cliente.descargar_adjunto(url, nombre_archivo)
                cliente.abrir_archivo(ruta)
            except Exception as exc:
                logging.getLogger("chat").warning("No se pudo descargar/abrir el adjunto: %s", exc)
        threading.Thread(target=_hilo, daemon=True, name="ChatPopup-DescargarAdjunto").start()

    def _guardar_adjunto(url, nombre_archivo):
        """(v4.18.44) «Guardar como…», como en la ventana del chat."""
        destino = _dialogo(filedialog.asksaveasfilename, title="Guardar adjunto",
                           initialfile=nombre_adjunto_seguro(nombre_archivo))
        if not destino:
            return

        def _hilo():
            try:
                cliente.guardar_adjunto_como(url, destino)
            except Exception as exc:
                logging.getLogger("chat").warning("No se pudo guardar el adjunto: %s", exc)
                if win.winfo_exists():
                    win.after(0, lambda e=exc: _dialogo(messagebox.showerror, "Chat",
                                                        f"No se pudo guardar «{nombre_archivo}»:\n{e}"))
        threading.Thread(target=_hilo, daemon=True, name="ChatPopup-GuardarAdjunto").start()

    # ── Mensajes: burbujas de verdad (rectángulos redondeados en Canvas),
    #    con hora HH:MM y copia por clic derecho — ver ui/chat_bubbles.py.
    msgs = BubbleList(win, bg=_COLOR_FONDO, color_propio=_COLOR_PROPIO,
                       color_ajeno=_COLOR_AJENO, color_texto=_COLOR_TEXTO,
                       color_meta=_COLOR_META, font_texto=("Segoe UI", 9),
                       font_meta=("Segoe UI", 7), on_click_adjunto=_click_adjunto,
                       on_guardar_adjunto=_guardar_adjunto,
                       cargar_imagen=lambda url, listo: miniaturas.cargar(win, cliente, url, listo))
    msgs.pack(fill="both", expand=True, padx=6, pady=6)

    ids_pintados = set()
    # Ver comentario equivalente en ui/ventana_chat.py — el eco del propio
    # mensaje llega sin poder deduplicarse por id (el pintado optimista no
    # tiene id todavía), así que se reconcilia por contenido+canal.
    pendientes_propios = []

    def _pintar(m, propio=None):
        mid = m.get("id")
        if propio is None:
            propio = (m.get("remitente") == cliente.username)
        if mid is not None:
            if mid in ids_pintados:
                return
            if propio:
                contenido_m = m.get("contenido", "")
                canal_m = m.get("canal_id", canal_id)
                for i, pend in enumerate(pendientes_propios):
                    if pend["canal_id"] == canal_m and pend["contenido"] == contenido_m:
                        del pendientes_propios[i]
                        ids_pintados.add(mid)
                        # (v4.18.46) ya tiene id: Responder, Reenviar y Eliminar en su menú
                        if pend.get("cv") is not None:
                            msgs.poner_acciones(pend["cv"], acciones_chat.acciones(
                                m, cliente, win, _responder, _recargar))
                        return  # ya está en pantalla desde el pintado optimista
            ids_pintados.add(mid)
        quien = "Tú" if propio else cliente.nombre_de(m.get("remitente", ""))
        hora = fecha_hora_local(m)
        if m.get("tipo") == "sistema":          # (v4.18.48) «👥 Ana ha añadido a Carla»
            return msgs.agregar_aviso(m.get("contenido", ""), hora)
        # (v4.18.46) Cita, «Reenviado», eliminado y el menú Responder / Reenviar / Eliminar
        extra = dict(acciones_chat.datos_burbuja(m, cliente),
                     acciones=acciones_chat.acciones(m, cliente, win, _responder, _recargar))
        adjunto = m.get("adjunto")
        if adjunto:
            icono = "📷" if m.get("tipo") == "imagen" else "📎"
            return msgs.agregar_burbuja(f"{icono} {adjunto['nombre_archivo']}", hora, propio,
                                         meta_nombre=quien, es_adjunto=True,
                                         adjunto_url=adjunto["url"],
                                         adjunto_nombre_archivo=adjunto["nombre_archivo"],
                                         es_imagen=miniaturas.es_imagen(m), **extra)
        return msgs.agregar_burbuja(m.get("contenido", ""), hora, propio, meta_nombre=quien, **extra)

    def _enviar(event=None):
        contenido = entry.get().strip()
        if not contenido:
            return
        citado = respondiendo["m"]          # (v4.18.46) responder citando
        cliente.enviar_mensaje(contenido, canal_id=canal_id, responde_a=citado.get("id") if citado else None)
        entry.delete(0, "end")
        pendiente = {"canal_id": canal_id, "contenido": contenido, "cv": None}
        pendientes_propios.append(pendiente)
        pendiente["cv"] = _pintar({
            "remitente": cliente.username, "contenido": contenido,
            "responde_a": ({"id": citado["id"], "remitente": citado.get("remitente"),
                            "contenido": acciones_chat.texto_cita(citado)} if citado else None)}, propio=True)
        _cancelar_respuesta()

    entry.bind("<Return>", _enviar)

    def _dialogo(fn, *args, **kw):
        """Los avisos y preguntas, por encima de la burbuja (que está siempre encima)."""
        win.attributes("-topmost", False)
        try:
            return fn(*args, parent=win, **kw)
        finally:
            if win.winfo_exists():
                win.attributes("-topmost", True)
                _forzar_foco()

    def _enviar_rutas(rutas):
        for ruta in rutas:
            def _hilo(ruta=ruta):
                resultado = cliente.enviar_archivo(ruta, canal_id=canal_id)
                if "captura_chat_" in ruta and ruta.startswith(tempfile.gettempdir()):
                    try:
                        os.remove(ruta)       # temporal de una captura pegada
                    except OSError:
                        pass
                if not win.winfo_exists():
                    return
                if resultado.get("ok"):
                    win.after(0, lambda r=resultado: _pintar(r["mensaje"], propio=True))
                else:
                    error = resultado.get("error", "No se pudo enviar el archivo")
                    win.after(0, lambda e=error: _dialogo(messagebox.showwarning, "Chat", f"{os.path.basename(ruta)}: {e}"))
            threading.Thread(target=_hilo, daemon=True, name="ChatPopup-EnviarArchivo").start()

    def _confirmar_y_enviar(rutas, etiquetas=None):
        """(v4.18.16) Arrastrar y soltar y Ctrl+V, como en la ventana grande: se pregunta
        antes de enviar, porque un archivo soltado por error no se puede deshacer."""
        rutas = [r for r in rutas if os.path.isfile(r)]
        if not rutas:
            _dialogo(messagebox.showwarning, "Chat", "Solo se pueden enviar archivos, no carpetas.")
            return
        if len(rutas) > 5:
            _dialogo(messagebox.showwarning, "Chat", "Se pueden enviar como máximo 5 archivos a la vez.")
            return
        nombres = etiquetas or [os.path.basename(r) for r in rutas]
        lista = "\n".join(f"  • {n}" for n in nombres)
        if _dialogo(messagebox.askyesno, "Chat", f"¿Enviar a «{titulo}»?\n\n{lista}"):
            _enviar_rutas(rutas)
        else:
            for r in rutas:
                if r.startswith(tempfile.gettempdir()) and "captura_chat_" in r:
                    try:
                        os.remove(r)
                    except OSError:
                        pass

    def _pegar(event=None):
        """Ctrl+V: una captura de pantalla o archivos copiados se ofrecen para enviar;
        el texto se pega como siempre (igual que en la ventana grande)."""
        try:
            from PIL import ImageGrab
            contenido = ImageGrab.grabclipboard()
        except Exception:
            return None
        if contenido is None:
            return None
        if isinstance(contenido, (list, tuple)):
            _confirmar_y_enviar([str(r) for r in contenido])
            return "break"
        try:
            nombre = "captura_chat_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
            ruta = os.path.join(tempfile.gettempdir(), nombre)
            contenido.save(ruta, format="PNG")
            _confirmar_y_enviar([ruta], etiquetas=["Imagen del portapapeles"])
            return "break"
        except Exception as exc:
            logging.getLogger("chat").warning("No se pudo pegar la imagen del portapapeles: %s", exc)
            return None

    entry.bind("<Control-v>", _pegar)
    entry.bind("<Control-V>", _pegar)

    def _adjuntar():
        win.attributes("-topmost", False)
        try:
            ruta = filedialog.askopenfilename(
                parent=win,
                title="Elegir imagen o documento",
                filetypes=[
                    ("Imágenes y documentos", "*.png *.jpg *.jpeg *.gif *.bmp *.webp "
                                               "*.pdf *.doc *.docx *.xls *.xlsx"),
                    ("Todos los archivos", "*.*"),
                ],
            )
        finally:
            if win.winfo_exists():
                win.attributes("-topmost", True)
        if ruta:
            _enviar_rutas([ruta])

    # (v4.18.18) Emoticonos y respuestas rápidas
    _img_emo = imagen_emoticono("😊", pequena=True)   # (v4.18.22) en color
    btn_emo = tk.Button(frm_envio, text="" if _img_emo is not None else "😊", image=_img_emo or "", bg=_COLOR_ENTRY, fg="white", bd=0,
                        activebackground="#33415a", activeforeground="white",
                        relief="flat", cursor="hand2", font=("Segoe UI", 12), pady=4,
                        width=30 if _img_emo is not None else 2)   # con imagen, el ancho va en píxeles
    btn_emo.configure(command=lambda: abrir_panel(btn_emo, entry, encima=True))
    btn_emo.pack(side="left", padx=(0, 4))
    tk.Button(frm_envio, text="📎", bg=_COLOR_ENTRY, fg="white", bd=0,
              activebackground="#33415a", activeforeground="white",
              relief="flat", cursor="hand2", command=_adjuntar,
              font=("Segoe UI", 13), width=2, pady=4).pack(side="left", padx=(0, 4))
    tk.Button(frm_envio, text="➤", bg=_COLOR_PROPIO, fg="white", bd=0,
              activebackground="#25a374", activeforeground="white",
              relief="flat", cursor="hand2", command=_enviar,
              font=("Segoe UI", 10, "bold"), width=3).pack(side="left")
    # ANTI-REGRESION (reportado 2026-07-21): entry.focus_set() nada más
    # crearla no basta en una ventana overrideredirect+topmost — Windows no
    # siempre le da el foco de teclado real a una ventana así en el mismo
    # instante en que se crea. Se fuerza con un pequeño respiro (win.after)
    # para dar tiempo a que la ventana esté totalmente mapeada, y también
    # al hacer clic en cualquier parte de la burbuja, por si el usuario
    # clica antes de que ese respiro termine.
    def _forzar_foco(event=None):
        win.lift()
        win.focus_force()
        entry.focus_set()
    win.after(150, _forzar_foco)
    win.bind("<Button-1>", _forzar_foco)
    entry.focus_set()

    _POPUPS[canal_id] = {"win": win, "pintar": _pintar, "foto": _pintar_foto}
    win.protocol("WM_DELETE_WINDOW", _cerrar)

    # Arrastrar archivos desde el Explorador sobre la burbuja (v4.18.16), como en la ventana
    # grande y con el mismo interruptor: "chat_arrastrar_soltar": false en config.json.
    try:
        if ctx.config.get("chat_arrastrar_soltar", True):
            from ui.dnd_windows import hook_dropfiles
            hook_dropfiles(win, _confirmar_y_enviar)
    except Exception as exc:
        logging.getLogger("chat").warning("Arrastrar y soltar no disponible en la burbuja: %s", exc)

    # ── Historial reciente (últimos mensajes), en segundo plano ─────────
    def _cargar():
        data = cliente.obtener_mensajes(canal_id=canal_id)
        # (2026-08-01) Descartar los que quedaron "limpiados" en este equipo
        # desde la ventana principal — ver _limpiar_chat() en ventana_chat.py
        # y db/sqlite.py. Mismo canal_id, misma marca — si se limpió en la
        # ventana principal, tampoco debe reaparecer aquí.
        mensajes_canal = filtrar_mensajes_limpiados(canal_id, data.get("mensajes", []))
        # (v4.18.44) El historial completo, como en la ventana del chat, para poder subir y ver
        # los mensajes anteriores (Víctor: «la burbuja debe ser igual en este sentido»). Antes
        # solo se pintaban los 3 últimos de HOY. Ordenados por fecha: el más reciente abajo,
        # justo encima de la caja de escribir.
        mensajes = sorted(mensajes_canal, key=lambda m: m.get("creado_en") or "")
        def _pintar_todos():
            if not win.winfo_exists():
                return
            for m in mensajes:
                _pintar(m)
            if mensaje_inicial:
                _pintar(mensaje_inicial)
        win.after(0, _pintar_todos)
    def _recargar():
        """(v4.18.46) Vuelve a cargar la conversación (p. ej. tras eliminar un mensaje)."""
        if not win.winfo_exists():
            return
        msgs.limpiar()
        ids_pintados.clear()
        threading.Thread(target=_cargar, daemon=True, name="ChatPopup-Historial").start()

    _POPUPS[canal_id]["recargar"] = _recargar
    threading.Thread(target=_cargar, daemon=True, name="ChatPopup-Historial").start()
