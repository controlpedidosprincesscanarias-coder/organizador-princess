"""ui/acciones_chat.py — responder citando, reenviar y eliminar mensajes del chat (v4.18.46).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Lo comparten la ventana del chat (ui/ventana_chat.py) y la burbuja (ui/chat_popup.py). Necesita el
servidor del chat v1.4.0 (campos `responde_a` y `reenviado`, rutas /eliminar y /reenviar y el evento
`mensaje_eliminado`). Con un servidor anterior, las rutas nuevas responden 404 y se avisa sin romper nada.

- datos_burbuja(): qué cita, marca de reenviado y estado de eliminado lleva una burbuja.
- acciones(): las entradas del menú del clic derecho (↩ Responder, ↪ Reenviar…, 🗑 Eliminar).
- La lógica sin Tkinter (datos_burbuja, texto_cita, destinos, puede_eliminar) se prueba en
  test_chat_fase2.py; las ventanas solo llaman a ChatClient.
"""
import logging
import threading

_LARGO_BARRA = 90


def texto_cita(m) -> str:
    """Texto corto de un mensaje para citarlo: el contenido, o «📎 archivo» si es un adjunto."""
    adjunto = (m or {}).get("adjunto") or {}
    if adjunto.get("nombre_archivo"):
        return f"{'📷' if (m.get('tipo') == 'imagen') else '📎'} {adjunto['nombre_archivo']}"
    return " ".join(str((m or {}).get("contenido") or "").split())


def datos_burbuja(m, cliente) -> dict:
    """kwargs de BubbleList.agregar_burbuja para la cita, el reenvío y el eliminado de `m`."""
    r = (m or {}).get("responde_a") or None
    cita = None
    if isinstance(r, dict) and r.get("id"):
        quien = "Tú" if r.get("remitente") == cliente.username else cliente.nombre_de(r.get("remitente", ""))
        cita = (quien, r.get("contenido") or "")
    return {"cita": cita, "reenviado": bool((m or {}).get("reenviado")),
            "eliminado": (m or {}).get("tipo") == "eliminado"}


def puede_eliminar(m, cliente) -> bool:
    return bool(m and m.get("id") and m.get("tipo") != "eliminado" and m.get("remitente") == cliente.username)


def acciones(m, cliente, parent, al_responder, al_cambiar=None) -> list:
    """[(etiqueta, función)] para el menú del clic derecho de la burbuja de `m`. Solo para mensajes
    que ya tienen id (el pintado optimista de uno propio aún no lo tiene)."""
    if not m or not m.get("id") or m.get("tipo") == "eliminado":
        return []
    lista = [("↩  Responder", lambda: al_responder(m)),
             ("↪  Reenviar…", lambda: reenviar(parent, cliente, m))]
    if puede_eliminar(m, cliente):
        lista.append(("🗑  Eliminar", lambda: eliminar(parent, cliente, m, al_cambiar)))
    return lista


def resumen_barra(m, cliente) -> str:
    """Texto de la barra «Respondiendo a …» encima de la caja de escribir."""
    quien = "ti mismo" if m.get("remitente") == cliente.username else cliente.nombre_de(m.get("remitente", ""))
    texto = texto_cita(m)
    if len(texto) > _LARGO_BARRA:
        texto = texto[:_LARGO_BARRA].rstrip() + "…"
    return f"↩  Respondiendo a {quien}: {texto}"


def eliminar(parent, cliente, m, al_cambiar=None):
    from tkinter import messagebox
    if not messagebox.askyesno("Eliminar mensaje",
                               "¿Eliminar este mensaje para todos?\n\nQuedará como «🚫 Mensaje eliminado». "
                               "No se puede deshacer.", parent=parent):
        return

    def _hilo():
        r = cliente.eliminar_mensaje(m["id"])
        if not r.get("ok"):
            error = r.get("error") or "No se pudo eliminar (¿el servidor del chat está actualizado?)."
            parent.after(0, lambda: parent.winfo_exists() and messagebox.showwarning("Chat", error, parent=parent))
        elif al_cambiar:
            parent.after(0, al_cambiar)
    threading.Thread(target=_hilo, daemon=True, name="Chat-Eliminar").start()


def destinos(canales, usuarios, cliente) -> list:
    """Conversaciones a las que se puede reenviar: [(etiqueta, canal_id, destinatario)]. Primero las que
    ya existen (General, grupos y privados) y después los compañeros sin privado abierto."""
    salida, con_privado = [], set()
    for c in canales or []:
        tipo = c.get("tipo")
        if tipo == "general":
            salida.append(("💬  General", "general", None))
        elif tipo == "grupo":
            salida.append((f"👥  {c.get('nombre') or 'Grupo'}", c.get("canal_id"), None))
        elif c.get("otro_usuario"):
            con_privado.add(c["otro_usuario"])
            salida.append((f"👤  {cliente.nombre_de(c['otro_usuario'])}", c.get("canal_id"), None))
    for u in usuarios or []:
        nombre = u.get("username")
        if nombre and nombre != cliente.username and nombre not in con_privado:
            salida.append((f"👤  {u.get('nombre') or nombre}", None, nombre))
    return salida


def reenviar(parent, cliente, m):
    """Ventana «Reenviar a…» con las conversaciones y los compañeros."""
    import tkinter as tk
    from tkinter import messagebox
    import ttkbootstrap as ttk

    win = ttk.Toplevel(parent)
    win.title("Reenviar a…")
    win.geometry("360x420")
    win.transient(parent)
    ttk.Label(win, text="Reenviar a…", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=(10, 2))
    ttk.Label(win, text=texto_cita(m)[:70], foreground="#8fa3b8").pack(anchor="w", padx=12, pady=(0, 6))
    lista = tk.Listbox(win, activestyle="none", font=("Segoe UI", 10))
    lista.pack(fill="both", expand=True, padx=12)
    lista.insert("end", "Cargando…")
    opciones = []
    pie = ttk.Frame(win, padding=10)
    pie.pack(fill="x")
    btn = ttk.Button(pie, text="↪  Reenviar", bootstyle="success", state="disabled")
    btn.pack(side="right")
    ttk.Button(pie, text="Cancelar", bootstyle="secondary", command=win.destroy).pack(side="right", padx=(0, 6))

    def _enviar(_e=None):
        sel = lista.curselection()
        if not sel or not opciones:
            return
        _etiqueta, canal_id, destinatario = opciones[sel[0]]
        btn.configure(state="disabled")

        def _hilo():
            r = cliente.reenviar_mensaje(m["id"], canal_id=canal_id, destinatario=destinatario)
            def _fin():
                if not win.winfo_exists():
                    return
                if r.get("ok"):
                    win.destroy()
                else:
                    btn.configure(state="normal")
                    messagebox.showwarning("Chat", r.get("error") or "No se pudo reenviar (¿el servidor del chat "
                                                                   "está actualizado?).", parent=win)
            win.after(0, _fin)
        threading.Thread(target=_hilo, daemon=True, name="Chat-Reenviar").start()

    btn.configure(command=_enviar)
    lista.bind("<Double-Button-1>", _enviar)
    lista.bind("<<ListboxSelect>>", lambda e: btn.configure(state="normal" if lista.curselection() else "disabled"))

    def _cargar():
        try:
            opciones.extend(destinos(cliente.obtener_canales(), cliente.obtener_usuarios(), cliente))
        except Exception as exc:  # noqa: BLE001
            logging.getLogger("chat").warning("No se pudieron cargar las conversaciones: %s", exc)

        def _pintar():
            if not win.winfo_exists():
                return
            lista.delete(0, "end")
            for etiqueta, _c, _d in opciones:
                lista.insert("end", etiqueta)
            if not opciones:
                lista.insert("end", "No se han podido cargar las conversaciones.")
        win.after(0, _pintar)
    threading.Thread(target=_cargar, daemon=True, name="Chat-Destinos").start()
    return win
