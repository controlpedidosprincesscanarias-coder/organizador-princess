"""ui/grupo_info.py — integrantes y gestión de un grupo del chat (v4.18.48, servidor del chat v1.5.0).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Al pulsar la foto o el nombre de un grupo en la cabecera de la conversación se abre esta ventana con sus
integrantes (foto, nombre y quién lo gestiona). Decisión de Víctor: quien creó el grupo añade y quita
compañeros, lo renombra y lo elimina; cualquier miembro ve la lista y puede salirse. Los grupos antiguos sin
creador guardado los puede gestionar cualquier miembro (el servidor lo decide: campo `puede_gestionar`).

candidatos() y etiqueta() no dependen de Tkinter (se prueban en test_chat_fase3.py).
"""
import threading

from ui import avatares

_TAM_FOTO = 28


def etiqueta(miembro, yo) -> str:
    """Texto de un integrante en la lista: «Ana López (tú) · gestiona el grupo»."""
    texto = miembro.get("nombre") or miembro.get("username") or ""
    if miembro.get("username") == yo:
        texto += " (tú)"
    if miembro.get("es_creador"):
        texto += "  ·  gestiona el grupo"
    return texto


def candidatos(usuarios, miembros) -> list:
    """Compañeros que se pueden añadir: los que no están ya en el grupo, por nombre."""
    dentro = {m.get("username") for m in miembros or []}
    return sorted((u for u in usuarios or [] if u.get("username") and u["username"] not in dentro),
                  key=lambda u: (u.get("nombre") or u["username"]).lower())


def abrir(parent, cliente, canal_id, al_cambiar=None, al_salir=None):
    """Ventana con los integrantes. `al_cambiar(nombre)` se llama tras renombrar o cambiar miembros;
    `al_salir()` tras salirse o eliminar el grupo (para volver al General)."""
    import tkinter as tk
    from tkinter import messagebox, simpledialog
    import ttkbootstrap as ttk

    win = ttk.Toplevel(parent)
    win.title("Integrantes del grupo")
    win.geometry("440x500")
    win.transient(parent)
    estado = {"detalle": {}, "fotos": []}

    lbl_titulo = ttk.Label(win, text="Cargando…", font=("Segoe UI", 12, "bold"))
    lbl_titulo.pack(anchor="w", padx=14, pady=(12, 0))
    lbl_sub = ttk.Label(win, text="", foreground="#8fa3b8")
    lbl_sub.pack(anchor="w", padx=14, pady=(0, 6))
    ttk.Style().configure("Integrantes.Treeview", rowheight=_TAM_FOTO + 8)
    lista = ttk.Treeview(win, show="tree", selectmode="extended", style="Integrantes.Treeview", height=6)
    lista.column("#0", width=320, stretch=True)
    lista.pack(fill="both", expand=True, padx=14, pady=(0, 8))

    gestion = ttk.Frame(win, padding=(14, 0, 14, 4))
    pie = ttk.Frame(win, padding=(14, 4, 14, 12))
    pie.pack(fill="x", side="bottom")

    def _en_hilo(funcion, despues):
        def _hilo():
            r = funcion()
            win.after(0, lambda: win.winfo_exists() and despues(r))
        threading.Thread(target=_hilo, daemon=True, name="Chat-Grupo").start()

    def _error(r, accion):
        messagebox.showwarning("Grupo", (r or {}).get("error") or f"No se pudo {accion} "
                               "(¿el servidor del chat está actualizado?).", parent=win)

    def _pintar(d):
        if not d.get("miembros"):
            lbl_titulo.configure(text="Grupo")
            lbl_sub.configure(text="No se han podido cargar los integrantes.")
            return
        estado["detalle"] = d
        lbl_titulo.configure(text=d.get("nombre") or "Grupo")
        lbl_sub.configure(text=f"{len(d['miembros'])} integrantes")
        lista.delete(*lista.get_children())
        estado["fotos"].clear()
        for m in d["miembros"]:
            foto = avatares.imagen(win, m.get("avatar"), m.get("nombre") or m["username"], _TAM_FOTO,
                                   clave=m["username"])
            estado["fotos"].append(foto)
            lista.insert("", "end", iid=m["username"], text="  " + etiqueta(m, cliente.username), image=foto)
        if d.get("puede_gestionar"):
            gestion.pack(fill="x", before=pie)
            btn_eliminar.pack(side="left", padx=(6, 0))
        else:
            gestion.pack_forget()
            btn_eliminar.pack_forget()

    def _cargar():
        _en_hilo(lambda: cliente.detalle_grupo(canal_id), _pintar)

    def _tras_cambio(r, accion):
        if r.get("miembros"):
            _pintar(r)
            if al_cambiar:
                al_cambiar(r.get("nombre"))
        else:
            _error(r, accion)

    def _anadir():
        d = estado["detalle"]

        def _elegir(usuarios):
            opciones = candidatos(usuarios, d.get("miembros"))
            if not opciones:
                messagebox.showinfo("Grupo", "Todos los compañeros están ya en el grupo.", parent=win)
                return
            sel = ttk.Toplevel(win)
            sel.title("Añadir al grupo")
            sel.transient(win)
            lb = tk.Listbox(sel, selectmode="multiple", height=min(14, len(opciones)), font=("Segoe UI", 10))
            for u in opciones:
                lb.insert("end", u.get("nombre") or u["username"])
            lb.pack(fill="both", expand=True, padx=12, pady=(12, 6))

            def _ok():
                elegidos = [opciones[i]["username"] for i in lb.curselection()]
                sel.destroy()
                if elegidos:
                    _en_hilo(lambda: cliente.cambiar_miembros_grupo(canal_id, anadir=elegidos),
                             lambda r: _tras_cambio(r, "añadir"))
            ttk.Button(sel, text="➕  Añadir", bootstyle="success", command=_ok).pack(side="right", padx=12, pady=(0, 12))
            ttk.Button(sel, text="Cancelar", bootstyle="secondary", command=sel.destroy).pack(side="right", pady=(0, 12))
        _en_hilo(cliente.obtener_usuarios, _elegir)

    def _quitar():
        elegidos = [u for u in lista.selection() if u != cliente.username]
        if not elegidos:
            messagebox.showinfo("Grupo", "Elige en la lista a quién quitar (para salir tú, «Salir del grupo»).",
                                parent=win)
            return
        nombres = ", ".join(lista.item(u, "text").strip().split("  ·")[0] for u in elegidos)
        if messagebox.askyesno("Quitar del grupo", f"¿Quitar del grupo a {nombres}?", parent=win):
            _en_hilo(lambda: cliente.cambiar_miembros_grupo(canal_id, quitar=elegidos),
                     lambda r: _tras_cambio(r, "quitar"))

    def _renombrar():
        nuevo = simpledialog.askstring("Renombrar el grupo", "Nombre nuevo:",
                                       initialvalue=estado["detalle"].get("nombre") or "", parent=win)
        if nuevo and nuevo.strip():
            _en_hilo(lambda: cliente.renombrar_grupo(canal_id, nuevo.strip()), lambda r: _tras_cambio(r, "renombrar"))

    def _fin(r, accion):
        if r.get("ok"):
            win.destroy()
            if al_salir:
                al_salir()
        else:
            _error(r, accion)

    def _salir():
        if messagebox.askyesno("Salir del grupo", "¿Salir de este grupo? Dejarás de ver sus mensajes.", parent=win):
            _en_hilo(lambda: cliente.salir_grupo(canal_id), lambda r: _fin(r, "salir del grupo"))

    def _eliminar():
        if messagebox.askyesno("Eliminar el grupo", "¿Eliminar el grupo para todos, con todos sus mensajes y "
                               "archivos?\n\nNo se puede deshacer.", icon="warning", parent=win):
            _en_hilo(lambda: cliente.eliminar_grupo(canal_id), lambda r: _fin(r, "eliminar el grupo"))

    ttk.Button(gestion, text="➕  Añadir", bootstyle="success-outline", command=_anadir).pack(side="left")
    ttk.Button(gestion, text="➖  Quitar", bootstyle="warning-outline", command=_quitar).pack(side="left", padx=6)
    ttk.Button(gestion, text="✏  Renombrar", bootstyle="info-outline", command=_renombrar).pack(side="left")
    ttk.Button(pie, text="🚪  Salir del grupo", bootstyle="light-outline", command=_salir).pack(side="left")
    btn_eliminar = ttk.Button(pie, text="🗑  Eliminar grupo", bootstyle="danger-outline", command=_eliminar)
    ttk.Button(pie, text="Cerrar", bootstyle="secondary", command=win.destroy).pack(side="right")
    _cargar()
    return win
