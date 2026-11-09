"""
ui/ventana_chat.py  ·  v1.0  ·  © VAMA 2026
============================================
Ventana de chat interno entre usuarios de Control de Pedidos, visto desde
main_agenda. Lista de conversaciones (General + privados) a la izquierda,
mensajes a la derecha.

HILOS — igual que el resto de la app: los eventos del socket llegan en un
hilo de fondo (ver services/chat_client.py) y se drenan aquí con
ventana.after(...), nunca tocando widgets desde el hilo del socket.
"""

import os
import threading
import logging
import tempfile as _tempfile
import tkinter as tk
import tkinter.font as tkfont
import ttkbootstrap as ttk
from datetime import datetime
from tkinter import messagebox, filedialog

from services.chat_client import get_chat_client, EVT_CONECTADO, EVT_DESCONECTADO, \
    EVT_NUEVO_MENSAJE, EVT_ERROR
from ui.chat_bubbles import BubbleList, fecha_hora_local
from ui.emoticonos import abrir_panel
from db.sqlite import set_chat_limpiado, filtrar_mensajes_limpiados

_VENTANA_ACTUAL = None  # evita abrir dos veces (instancia única de la ventana)
_CANAL_VISIBLE  = None  # canal_id que se está viendo AHORA en la ventana (o None si está cerrada)
_HANDLER        = None  # función que procesa un evento del chat mientras la ventana está abierta;
                         # la rellena poll_chat() en main_agenda.py, que es quien de verdad drena
                         # cliente.eventos desde que arranca el Organizador (v1.2) — así solo hay
                         # UN consumidor de la cola, nunca esta ventana y main_agenda.py a la vez.
_CERRAR         = None  # (v4.18.16) cierra la ventana y devuelve lo que se estaba escribiendo


def cerrar_para_seguir_en_burbuja():
    """(v4.18.16, petición de Víctor) Cuando el otro contesta en la conversación que se está
    viendo, la conversación sigue en la burbuja flotante: se cierra esta ventana y se devuelve
    el texto que hubiera a medio escribir, para no perderlo. Devuelve None si no estaba abierta."""
    if _CERRAR is None:
        return None
    try:
        return _CERRAR()
    except Exception:  # noqa: BLE001
        logging.getLogger("chat").exception("No se pudo cerrar la ventana del chat")
        return None


def _ventana_chat(ctx):
    global _VENTANA_ACTUAL, _HANDLER, _CERRAR
    if _VENTANA_ACTUAL is not None and _VENTANA_ACTUAL.winfo_exists():
        _VENTANA_ACTUAL.lift()
        _VENTANA_ACTUAL.focus_force()
        return

    cliente = get_chat_client()

    win = ttk.Toplevel(ctx.app)
    win.title("💬 Chat — Control de Pedidos")
    win.geometry("880x560")
    win.minsize(700, 460)
    ctx.apply_icon(win)
    _VENTANA_ACTUAL = win

    canal_actual = {"id": "general", "otro": None}

    # ── Layout: lista de conversaciones | mensajes ───────────────────────
    paned = ttk.Panedwindow(win, orient="horizontal")
    paned.pack(fill="both", expand=True, padx=8, pady=8)

    frm_lista = ttk.Frame(paned, padding=(0, 0, 6, 0))
    frm_chat  = ttk.Frame(paned, padding=(6, 0, 0, 0))
    paned.add(frm_lista, weight=1)
    paned.add(frm_chat, weight=3)

    lbl_estado = ttk.Label(frm_lista, text="Conectando…", bootstyle="light")
    lbl_estado.pack(fill="x", pady=(0, 6))

    ttk.Label(frm_lista, text="Conversaciones", font=("-size", 10, "-weight", "bold")).pack(
        anchor="w")
    lista = tk.Listbox(frm_lista, activestyle="none", exportselection=False, width=22)
    lista.pack(fill="both", expand=True, pady=(4, 6))
    _canales_por_indice = []  # paralelo a las filas de `lista`

    _BTN_NUEVA_TXT = "＋  Nueva conversación"
    ttk.Button(frm_lista, text=_BTN_NUEVA_TXT, bootstyle="info-outline",
               command=lambda: _abrir_nueva_conversacion(cliente, win, ctx,
                                                           lambda cid, otro, titulo=None:
                                                           _cambiar_canal(cid, otro, titulo))
               ).pack(fill="x")

    # ── Ancho del panel lateral medido de verdad, no adivinado a mano ──────
    # (2026-07-27) Un ancho fijo (en caracteres o en px) se queda corto en
    # cuanto aparece un nombre más largo del que se tuvo en cuenta al
    # elegirlo — y sobra espacio cuando los nombres son cortos. En vez de
    # eso, cada vez que se refresca la lista de conversaciones (conexión,
    # mensaje nuevo, alta de usuario) se mide en píxeles el texto más ancho
    # realmente presente (etiquetas de conversación + el botón "＋ Nueva
    # conversación", que casi siempre es el elemento más ancho del panel) y
    # se mueve el separador del Panedwindow a esa medida. Con un tope
    # máximo para que un nombre absurdamente largo no se coma media
    # ventana — a partir de ahí el usuario puede arrastrar el separador a
    # mano si de verdad lo necesita.
    _fuente_lista = tkfont.Font(font=lista.cget("font"))
    _fuente_boton = tkfont.nametofont("TkDefaultFont")

    def _ajustar_ancho_sidebar():
        etiquetas = [_BTN_NUEVA_TXT] + [lista.get(i) for i in range(lista.size())]
        if not etiquetas:
            return
        ancho_px = max(_fuente_lista.measure(t) for t in etiquetas)
        ancho_px = max(ancho_px, _fuente_boton.measure(_BTN_NUEVA_TXT))
        ancho_px += 40  # scrollbar/padding/margen interno del Listbox y el Frame
        ancho_min = 150
        ancho_max = max(ancho_min, win.winfo_width() - 260)  # deja sitio a los mensajes
        ancho_px = max(ancho_min, min(ancho_px, ancho_max))
        try:
            paned.sashpos(0, ancho_px)
        except tk.TclError:
            pass  # la ventana puede no estar todavía mapeada la primera vez

    win.after(50, _ajustar_ancho_sidebar)

    # ── Panel de mensajes ─────────────────────────────────────────────────
    frm_titulo_chat = ttk.Frame(frm_chat)
    frm_titulo_chat.pack(fill="x")
    lbl_titulo_chat = ttk.Label(frm_titulo_chat, text="General",
                                 font=("-size", 11, "-weight", "bold"))
    lbl_titulo_chat.pack(side="left", anchor="w")

    def _limpiar_chat():
        # (2026-08-01) A petición del usuario: ahora la limpieza SÍ persiste
        # — se guarda una marca de tiempo local (por canal, por equipo) y
        # _cargar_historial() la usa para no volver a mostrar nada anterior
        # a esa marca, ni siquiera al reabrir el chat o la app. Sigue sin
        # borrar nada del servidor (los demás participantes del canal no se
        # ven afectados), y si el mismo usuario entra desde otro PC seguirá
        # viendo el histórico completo ahí hasta que también limpie en ese
        # equipo — ver filtrar_mensajes_limpiados() en db/sqlite.py.
        if not messagebox.askyesno(
                "Limpiar chat",
                "¿Vaciar el historial de esta conversación en este equipo?\n\n"
                "Dejarás de ver los mensajes anteriores a ahora mismo, incluso "
                "si sales del chat y vuelves a entrar. No se borra nada del "
                "servidor — los demás participantes siguen viendo el "
                "historial completo, y si tú entras desde otro equipo también "
                "lo seguirás viendo ahí.",
                parent=win):
            return
        set_chat_limpiado(canal_actual["id"], datetime.utcnow().isoformat() + "Z")
        msgs.limpiar()
        _ids_pintados.clear()

    ttk.Button(frm_titulo_chat, text="🧹 Limpiar chat", bootstyle="info-outline",
               command=lambda: _limpiar_chat()).pack(side="right")

    # Paleta a juego con ui/chat_popup.py, para que las burbujas se vean
    # igual en la ventana principal y en la ventana emergente flotante.
    _COLOR_PROPIO = "#1f8f63"
    _COLOR_AJENO  = "#3a4a63"
    _COLOR_META   = "#8fa3b8"

    # Fila de escribir/adjuntar/enviar — se empaqueta ANTES que el área de
    # mensajes y anclada a side="bottom" (2026-07-27, fix de layout): así
    # reserva siempre su hueco fijo desde abajo, y es la zona de mensajes
    # ajusta al espacio que quede, en vez de al revés. Con el orden antiguo
    # (mensajes primero, expand=True, y esta fila después con side="top"),
    # en ventanas justas de alto — pantalla pequeña, escalado de Windows al
    # 125-150% — el área de mensajes se comía todo el hueco disponible y
    # esta fila quedaba sin sitio y desaparecía del todo.
    frm_envio = ttk.Frame(frm_chat)
    frm_envio.pack(side="bottom", fill="x", pady=(6, 0))
    entry_msg = ttk.Entry(frm_envio)
    entry_msg.pack(side="left", fill="x", expand=True, padx=(0, 6))

    def _enviar(event=None):
        contenido = entry_msg.get().strip()
        if not contenido:
            return
        canal_envio = canal_actual["id"] if canal_actual["id"] != "general" else "general"
        cliente.enviar_mensaje(
            contenido,
            canal_id=canal_envio,
            destinatario=canal_actual["otro"] if canal_actual["id"] != "general" else None,
        )
        entry_msg.delete(0, "end")
        # Pintado optimista — no esperamos al eco del servidor para que se
        # sienta instantáneo; cuando llegue el eco con su id real (ver
        # _pintar_mensaje), se reconoce por contenido+canal en
        # _pendientes_propios y no se repinta.
        _pendientes_propios.append({"canal_id": canal_envio, "contenido": contenido})
        _pintar_mensaje({"remitente": cliente.username, "contenido": contenido,
                          "creado_en": ""}, propio=True)

    entry_msg.bind("<Return>", _enviar)

    def _enviar_rutas(rutas):
        """Envía uno o varios archivos al canal abierto (cada uno en su propio hilo)."""
        canal_envio = canal_actual["id"] if canal_actual["id"] != "general" else "general"
        destinatario = canal_actual["otro"] if canal_actual["id"] != "general" else None
        for ruta in rutas:
            def _hilo(ruta=ruta):
                resultado = cliente.enviar_archivo(ruta, canal_id=canal_envio, destinatario=destinatario)
                if "captura_chat_" in ruta and ruta.startswith(_tempfile.gettempdir()):
                    try: os.remove(ruta)       # temporal de una captura pegada
                    except OSError: pass
                if resultado.get("ok"):
                    win.after(0, lambda r=resultado: _pintar_mensaje(r["mensaje"], propio=True))
                else:
                    error = resultado.get("error", "No se pudo enviar el archivo")
                    win.after(0, lambda e=error: lbl_estado.configure(text=f"🔴 {e}", bootstyle="danger"))
            threading.Thread(target=_hilo, daemon=True, name="Chat-EnviarArchivo").start()

    def _destino_texto():
        return "el chat General" if canal_actual["id"] == "general" else f"«{canal_actual['otro'] or 'esta conversación'}»"

    def _confirmar_y_enviar(rutas, etiquetas=None):
        """Arrastrar y pegar piden confirmación: un archivo soltado por error en una
        conversación no se puede deshacer."""
        _os = os
        rutas = [r for r in rutas if _os.path.isfile(r)]
        if not rutas:
            lbl_estado.configure(text="🔴 Solo se pueden enviar archivos, no carpetas", bootstyle="danger")
            return
        if len(rutas) > 5:
            messagebox.showwarning("Chat", "Se pueden enviar como máximo 5 archivos a la vez.", parent=win)
            return
        nombres = etiquetas or [_os.path.basename(r) for r in rutas]
        lista = "\n".join(f"  • {n}" for n in nombres)
        if messagebox.askyesno("Chat", f"¿Enviar a {_destino_texto()}?\n\n{lista}", parent=win):
            _enviar_rutas(rutas)
        else:
            for r in rutas:        # capturas pegadas: se borra el temporal si no se envía
                if r.startswith(_tempfile.gettempdir()) and "captura_chat_" in r:
                    try: _os.remove(r)
                    except OSError: pass

    def _adjuntar():
        ruta = filedialog.askopenfilename(
            parent=win,
            title="Elegir imagen o documento para enviar",
            filetypes=[
                ("Imágenes y documentos", "*.png *.jpg *.jpeg *.gif *.bmp *.webp "
                                           "*.pdf *.doc *.docx *.xls *.xlsx"),
                ("Todos los archivos", "*.*"),
            ],
        )
        if not ruta:
            return
        _enviar_rutas([ruta])

    def _pegar(event=None):
        """Ctrl+V: si el portapapeles trae una imagen (captura de pantalla) o archivos
        copiados en el Explorador, se ofrece enviarlos; si trae texto, pega como siempre."""
        try:
            from PIL import ImageGrab
            contenido = ImageGrab.grabclipboard()
        except Exception:
            return None                       # sin soporte → pegado normal de texto
        if contenido is None:
            return None
        if isinstance(contenido, (list, tuple)):
            _confirmar_y_enviar([str(r) for r in contenido])
            return "break"
        try:                                   # es una imagen
            _os = os
            nombre = "captura_chat_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
            ruta = _os.path.join(_tempfile.gettempdir(), nombre)
            contenido.save(ruta, format="PNG")
            _confirmar_y_enviar([ruta], etiquetas=["Imagen del portapapeles"])
            return "break"
        except Exception as exc:
            logging.getLogger("chat").warning("No se pudo pegar la imagen del portapapeles: %s", exc)
            return None

    entry_msg.bind("<Control-v>", _pegar)
    entry_msg.bind("<Control-V>", _pegar)

    # (v4.18.18) Emoticonos y respuestas rápidas
    btn_emo = ttk.Button(frm_envio, text="😊", bootstyle="info-outline", width=4)
    btn_emo.configure(command=lambda: abrir_panel(btn_emo, entry_msg))
    btn_emo.pack(side="left", padx=(0, 6))
    ttk.Button(frm_envio, text="📎", bootstyle="info-outline", width=4,
               command=_adjuntar).pack(side="left", padx=(0, 6), ipady=4, ipadx=2)
    ttk.Button(frm_envio, text="Enviar", bootstyle="success",
               command=_enviar).pack(side="left")

    def _click_adjunto(url, nombre_archivo):
        def _hilo():
            try:
                ruta = cliente.descargar_adjunto(url, nombre_archivo)
                cliente.abrir_archivo(ruta)
            except Exception as exc:
                logging.getLogger("chat").warning("No se pudo descargar/abrir el adjunto: %s", exc)
                # (v4.18.06) `exc` se pasa como argumento por defecto: Python
                # borra la variable del except al salir del bloque, y la
                # lambda, que se ejecuta después, daba NameError y el aviso
                # de error nunca llegaba a mostrarse.
                win.after(0, lambda e=exc: messagebox.showerror(
                    "Chat", f"No se pudo descargar «{nombre_archivo}»:\n{e}", parent=win))
        threading.Thread(target=_hilo, daemon=True, name="Chat-DescargarAdjunto").start()

    # Burbujas de verdad (rectángulos redondeados en Canvas), con hora
    # HH:MM y copia por clic derecho — ver ui/chat_bubbles.py. Comparte
    # implementación con la burbuja flotante (ui/chat_popup.py), así que
    # cualquier mejora futura de las burbujas se hace en un solo sitio.
    msgs = BubbleList(frm_chat, bg="#1e2530", color_propio=_COLOR_PROPIO,
                       color_ajeno=_COLOR_AJENO, color_texto="#f2f5f8",
                       color_meta=_COLOR_META, on_click_adjunto=_click_adjunto)
    msgs.pack(fill="both", expand=True, pady=(4, 6))

    _ids_pintados = set()
    # Los mensajes propios se pintan al vuelo (optimista, ver _enviar) SIN
    # id porque el socket es "fire and forget" — no hay id real hasta que
    # llega el eco por EVT_NUEVO_MENSAJE. Antes, ese eco se volvía a pintar
    # aparte (mismo texto, sin deduplicar porque _ids_pintados solo mira
    # "id"), y el mensaje salía duplicado: una burbuja sin hora (la
    # optimista) y otra con hora (el eco). Al reabrir la ventana, el
    # historial ya no tiene la copia optimista — por eso solo quedaba la
    # buena. _pendientes_propios hace de puente: guarda qué contenidos
    # propios ya están pintados a la espera de su eco, para no repetirlos.
    _pendientes_propios = []

    def _pintar_mensaje(m, propio=None):
        mid = m.get("id")
        if propio is None:
            propio = (m.get("remitente") == cliente.username)
        if mid is not None:
            if mid in _ids_pintados:
                return
            if propio:
                contenido_m = m.get("contenido", "")
                canal_m = m.get("canal_id", canal_actual["id"])
                for i, pend in enumerate(_pendientes_propios):
                    if pend["canal_id"] == canal_m and pend["contenido"] == contenido_m:
                        del _pendientes_propios[i]
                        _ids_pintados.add(mid)
                        return  # ya está en pantalla desde el pintado optimista
            _ids_pintados.add(mid)
        quien = "Tú" if propio else cliente.nombre_de(m.get("remitente", ""))
        hora = fecha_hora_local(m)
        adjunto = m.get("adjunto")
        if adjunto:
            icono = "📷" if m.get("tipo") == "imagen" else "📎"
            msgs.agregar_burbuja(f"{icono}  {adjunto['nombre_archivo']}", hora, propio,
                                  meta_nombre=quien, es_adjunto=True,
                                  adjunto_url=adjunto["url"],
                                  adjunto_nombre_archivo=adjunto["nombre_archivo"])
        else:
            msgs.agregar_burbuja(m.get("contenido", ""), hora, propio, meta_nombre=quien)

    def _cargar_historial(canal_id, destinatario):
        msgs.limpiar()
        _ids_pintados.clear()

        def _fetch():
            data = cliente.obtener_mensajes(
                canal_id=canal_id if canal_id != "general" else "general",
                destinatario=destinatario,
            )
            # Orden cronológico explícito antes de pintar (no depender de
            # en qué orden los devuelva la API) — la más reciente siempre
            # queda abajo, justo encima de la caja de escribir.
            mensajes = sorted(data.get("mensajes", []), key=lambda m: m.get("creado_en") or "")
            resolved_canal = data.get("canal_id", canal_id)
            # (2026-08-01) Descartar los que quedaron "limpiados" en este
            # equipo — ver _limpiar_chat() y db/sqlite.py.
            mensajes = filtrar_mensajes_limpiados(resolved_canal, mensajes)
            win.after(0, lambda: win.winfo_exists() and [_pintar_mensaje(m) for m in mensajes])
            canal_actual["id"] = resolved_canal
            cliente.unirse_canal(resolved_canal)

        threading.Thread(target=_fetch, daemon=True).start()

    def _cambiar_canal(canal_id, otro_usuario, titulo=None):
        global _CANAL_VISIBLE
        canal_actual["id"]  = canal_id
        canal_actual["otro"] = otro_usuario
        _CANAL_VISIBLE = canal_id
        lbl_titulo_chat.configure(text=titulo or otro_usuario or "General")
        _cargar_historial(canal_id, otro_usuario)
        _refrescar_lista_canales()

    def _refrescar_lista_canales():
        def _fetch():
            canales = cliente.obtener_canales()
            def _pintar():
                if not win.winfo_exists():   # (v4.18.16) la ventana se cerró mientras se cargaba
                    return
                lista.delete(0, "end")
                _canales_por_indice.clear()
                for c in canales:
                    tipo = c.get("tipo")
                    if tipo == "general":
                        nombre = "General"
                    elif tipo == "grupo":
                        nombre = c.get("nombre") or "Grupo"
                    else:
                        nombre = cliente.nombre_de(c.get("otro_usuario")) if c.get("otro_usuario") else "?"
                    no_leidos = c.get("no_leidos", 0)
                    icono = {"general": "💬 ", "grupo": "👥 "}.get(tipo, "👤 ")
                    etiqueta = f"{icono}{nombre}"
                    if no_leidos:
                        etiqueta += f"  ({no_leidos})"
                    lista.insert("end", etiqueta)
                    _canales_por_indice.append((c["canal_id"], c.get("otro_usuario"), nombre))
                _ajustar_ancho_sidebar()
            win.after(0, _pintar)
        threading.Thread(target=_fetch, daemon=True).start()

    def _on_seleccion_lista(event=None):
        sel = lista.curselection()
        if not sel:
            return
        canal_id, otro, nombre = _canales_por_indice[sel[0]]
        _cambiar_canal(canal_id, otro, nombre)

    lista.bind("<<ListboxSelect>>", _on_seleccion_lista)

    # ── Manejo de eventos del socket mientras la ventana está abierta ──────
    # v1.2: quien de verdad drena cliente.eventos es poll_chat() en
    # main_agenda.py, desde que arranca el Organizador (no solo mientras
    # esta ventana está abierta) — así el chat puede avisar con un popup
    # aunque la ventana esté cerrada. Esta función solo actualiza la UI
    # local cuando SÍ está abierta; el sonido y el popup los decide el
    # poller central para no duplicarlos.
    def _manejar_evento(ev):
        if not win.winfo_exists():
            return
        tipo = ev.get("tipo")
        if tipo == EVT_CONECTADO:
            lbl_estado.configure(text="🟢 Conectado", bootstyle="success")
            _refrescar_lista_canales()
        elif tipo == EVT_DESCONECTADO:
            lbl_estado.configure(text="🟡 Reconectando…", bootstyle="warning")
        elif tipo == EVT_NUEVO_MENSAJE:
            m = ev["mensaje"]
            if m.get("canal_id") == canal_actual["id"]:
                _pintar_mensaje(m)
            _refrescar_lista_canales()
        elif tipo == EVT_ERROR:
            lbl_estado.configure(text="🔴 Error de conexión", bootstyle="danger")

    _HANDLER = _manejar_evento
    # Si el chat ya estaba conectado en segundo plano (arranque del
    # Organizador, ver main_agenda.py), refleja el estado real de inmediato
    # en vez de mostrar "Conectando…" un rato de más.
    if cliente.conectado:
        lbl_estado.configure(text="🟢 Conectado", bootstyle="success")
        _refrescar_lista_canales()

    def _iniciar():
        if not cliente.username:
            if not cliente.login():
                win.after(0, lambda: lbl_estado.configure(
                    text="🔴 No se pudo iniciar sesión", bootstyle="danger"))
                return
        cliente.conectar()
        cliente.refrescar_mapa_nombres()   # recoge altas de usuarios nuevos
                                            # sin tener que reiniciar la app

    threading.Thread(target=_iniciar, daemon=True).start()
    _cargar_historial("general", None)

    def _on_cerrar():
        global _VENTANA_ACTUAL, _CANAL_VISIBLE, _HANDLER, _CERRAR
        _VENTANA_ACTUAL = None
        _CANAL_VISIBLE = None
        _HANDLER = None
        _CERRAR = None
        win.destroy()
    win.protocol("WM_DELETE_WINDOW", _on_cerrar)

    def _cerrar_devolviendo_borrador():
        borrador = entry_msg.get() if entry_msg.winfo_exists() else ""
        _on_cerrar()
        return borrador
    _CERRAR = _cerrar_devolviendo_borrador

    # Arrastrar archivos desde el Explorador sobre la ventana (v4.18.00).
    # Si no se puede activar (no es Windows, error de la API) queda el botón 📎 y Ctrl+V.
    # Interruptor: "chat_arrastrar_soltar": false en config.json lo desactiva sin tocar el programa.
    try:
        if ctx.config.get("chat_arrastrar_soltar", True):
            from ui.dnd_windows import hook_dropfiles
            hook_dropfiles(win, _confirmar_y_enviar)
    except Exception as exc:
        logging.getLogger("chat").warning("Arrastrar y soltar no disponible: %s", exc)


def _abrir_nueva_conversacion(cliente, parent, ctx, on_elegido):
    """Elegir UN compañero abre/crea un privado (como hasta ahora). Elegir
    DOS O MÁS pide un nombre de grupo y crea un canal de grupo nuevo."""
    sel = ttk.Toplevel(parent)
    sel.title("Nueva conversación")
    sel.geometry("460x460")
    sel.minsize(400, 380)
    ctx.apply_icon(sel)

    ttk.Label(sel, text="Elige uno o varios compañeros:", padding=10).pack(anchor="w")
    ttk.Label(sel, text="(1 compañero → chat privado · 2 o más → grupo)",
              bootstyle="light", font=("-size", 8)).pack(anchor="w", padx=10)

    lb = tk.Listbox(sel, selectmode="multiple", exportselection=False)

    frm_nombre = ttk.Frame(sel)
    lbl_nombre = ttk.Label(frm_nombre, text="Nombre del grupo:")
    entry_nombre = ttk.Entry(frm_nombre)

    # Controles fijos de abajo — se reservan ANTES de empaquetar la lista
    # (mismo fix de layout que en la ventana principal del chat, 2026-07-27):
    # se empaquetan con side="bottom", en orden inverso al visual (el
    # primero en empaquetarse queda el más abajo del todo), para que nunca
    # se queden sin sitio en ventanas justas de alto.
    ttk.Button(sel, text="Abrir chat", bootstyle="success",
               command=lambda: _elegir()).pack(side="bottom", pady=(0, 10))
    lbl_estado_sel = ttk.Label(sel, text="", bootstyle="danger")
    lbl_estado_sel.pack(side="bottom", anchor="w", padx=10)

    lb.pack(fill="both", expand=True, padx=10, pady=(6, 10))

    def _actualizar_visibilidad_nombre(event=None):
        n_sel = len(lb.curselection())
        if n_sel >= 2:
            frm_nombre.pack(side="bottom", fill="x", padx=10, pady=(0, 6))
            lbl_nombre.pack(anchor="w")
            entry_nombre.pack(fill="x")
        else:
            frm_nombre.pack_forget()

    lb.bind("<<ListboxSelect>>", _actualizar_visibilidad_nombre)

    # Ancho medido de verdad (2026-07-27), mismo criterio que el panel
    # lateral de la ventana principal: en vez de una anchura fija adivinada
    # a mano (se quedaba corta con "...LLARENA  (hotel)"), se mide en
    # píxeles la entrada más larga que de verdad se cargó y se agranda la
    # ventana si hace falta — nunca se encoge por debajo del tamaño
    # inicial/mínimo, así que un listado con nombres cortos no achica la
    # ventana de golpe.
    def _ajustar_ancho_ventana():
        if lb.size() == 0:
            return
        fuente = tkfont.Font(font=lb.cget("font"))
        ancho_px = max(fuente.measure(lb.get(i)) for i in range(lb.size()))
        ancho_px += 70  # scrollbar + padding interno + margen de la ventana
        ancho_actual = sel.winfo_width()
        if ancho_px > ancho_actual:
            alto_actual = sel.winfo_height()
            ancho_max = 700  # tope — a partir de ahí, que el usuario redimensione a mano
            sel.geometry(f"{min(ancho_px, ancho_max)}x{alto_actual}")

    def _cargar():
        usuarios = cliente.obtener_usuarios()
        def _pintar():
            for u in usuarios:
                lb.insert("end", f"{u['nombre']}  ({u['rol']})")
            lb._usuarios = usuarios  # noqa: SLF001 — referencia simple, ventana efímera
            _ajustar_ancho_ventana()
        sel.after(0, _pintar)
    threading.Thread(target=_cargar, daemon=True).start()

    def _elegir(event=None):
        sel_idx = lb.curselection()
        if not sel_idx or not hasattr(lb, "_usuarios"):
            return
        elegidos = [lb._usuarios[i] for i in sel_idx]

        if len(elegidos) == 1:
            u = elegidos[0]
            sel.destroy()
            # canal_id se deja en None a propósito: el backend lo resuelve y
            # lo crea si hace falta a partir de "destinatario" (ver
            # GET /api/chat/mensajes?destinatario=...).
            on_elegido(None, u["username"], u.get("nombre") or u["username"])
            return

        nombre_grupo = entry_nombre.get().strip()
        if not nombre_grupo:
            lbl_estado_sel.configure(text="Ponle un nombre al grupo antes de crearlo.")
            return

        def _crear():
            usernames = [u["username"] for u in elegidos]
            resultado = cliente.crear_grupo(nombre_grupo, usernames)
            if resultado.get("ok"):
                sel.after(0, lambda: [sel.destroy(),
                                       on_elegido(resultado["canal_id"], None, nombre_grupo)])
            else:
                error = resultado.get("error", "No se pudo crear el grupo")
                sel.after(0, lambda: lbl_estado_sel.configure(text=error))
        threading.Thread(target=_crear, daemon=True).start()
