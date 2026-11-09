"""
ui/admin.py
Administración: inicio de sesión (validado contra Control de Pedidos o con la credencial guardada),
panel «Accesos y Opciones del Menú», «Mi Usuario» y ventana «Vista del menú principal».
Extraído de main_agenda.py en v4.18.08 (antes, ~900 líneas allí).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Recibe el AppContext (ctx): config, save_config, app, etiquetas de botones, nombre del usuario,
versión (ctx.app_version) y la función que recoloca el menú tras cambiar la vista (ctx.aplicar_vista).
"""
import os
import threading
import tkinter as tk
from datetime import datetime
from tkinter import StringVar, messagebox

import ttkbootstrap as ttk

import services.admin_auth as admin_auth
from db.sqlite import (get_bridge_credentials, get_nombre_usuario, update_bridge_credentials,
                       update_nombre_usuario_db)
from ui.agenda_helpers import get_nombre
from ui.assets import _apply_icon
from ui.colores import GOLD, LIGHT
from ui.disposicion import (MARGEN, NUM_ACCESOS_RAPIDOS, NUM_OPCIONES, VISTA_ACCESOS_REDUCIDA,
                            VISTA_MAX_AZULES, vista_actual)
from ui.importexport import exportar_agenda, exportar_config, importar_agenda, importar_config
from ui.ventana_config import _ventana_config

# ANTI-REGRESION: antes había credenciales ADMIN_USER / ADMIN_PASSWORD hardcodeadas en
# main_agenda.py. Sustituidas por el sistema sin hardcode de services/admin_auth.py.
_admin_autenticado = False   # sesión activa mientras la app esté abierta


def _ventana_login_admin(ctx, on_success):
    """Diálogo de autenticación antes de abrir el panel de administración.

    Sin credenciales hardcodeadas (ver services/admin_auth.py):
      · El usuario de login es SIEMPRE el usuario de Windows (no editable).
      · Si ese usuario ya existe en Control de Pedidos, se valida la
        contraseña contra la plataforma en cada intento.
      · Si no existe, se muestra un formulario de alta (nombre a mostrar +
        contraseña + repetir contraseña); se guarda cifrado localmente
        (hash+salt) y se notifica a Control de Pedidos para que un
        administrador cree la cuenta real.
      · Máximo 3 intentos fallidos → bloqueo temporal.
    """
    from tkinter import StringVar as _SV

    uwin = admin_auth.get_windows_user()

    dlg = ttk.Toplevel()
    dlg.withdraw()
    dlg.title("Acceso Administración")
    dlg.resizable(False, False)
    dlg.attributes("-topmost", True)
    _apply_icon(dlg)

    _dw = 500
    _sw = dlg.winfo_screenwidth()
    _sh = dlg.winfo_screenheight()

    # ── Cabecera ─────────────────────────────────────────────
    hdr = ttk.Frame(dlg, padding=(20, 16, 20, 8))
    hdr.pack(fill="x")
    ttk.Label(hdr, text="⚙  Administración",
              font=("Segoe UI", 13, "bold")).pack(anchor="w")
    var_subtitulo = _SV(value="Comprobando tu usuario en Control de Pedidos…")
    ttk.Label(hdr, textvariable=var_subtitulo,
              font=("Segoe UI", 9), foreground=LIGHT,
              wraplength=400).pack(anchor="w", pady=(4, 0))
    ttk.Separator(dlg).pack(fill="x")

    body = ttk.Frame(dlg, padding=(20, 14, 20, 0))
    body.pack(fill="both", expand=True)

    # Usuario de Windows — siempre visible, nunca editable
    row_u = ttk.Frame(body)
    row_u.pack(fill="x", pady=(0, 10))
    ttk.Label(row_u, text="Usuario Windows:", font=("Segoe UI", 9),
              width=16, anchor="w").pack(side="left")
    ttk.Label(row_u, text=uwin, font=("Consolas", 10, "bold"),
              foreground="#C9A84C").pack(side="left")

    # Contenedor dinámico: cambia entre modo "login" y modo "alta"
    dyn = ttk.Frame(body)
    dyn.pack(fill="x")

    var_toggle_txt = _SV(value="")
    lbl_toggle = ttk.Label(body, textvariable=var_toggle_txt,
                           font=("Segoe UI", 8, "underline"),
                           foreground="#5aa9e6", cursor="hand2")
    lbl_toggle.pack(anchor="w", pady=(8, 0))

    ttk.Separator(dlg).pack(fill="x", padx=0, pady=(10, 0))
    frame_btns = ttk.Frame(dlg, padding=(20, 8, 20, 12))
    frame_btns.pack(fill="x")

    _refs = {"btn_principal": None, "modo": None}

    def _reposicionar():
        dlg.update_idletasks()
        _dh = dlg.winfo_reqheight() + 10
        dlg.geometry(f"{_dw}x{_dh}+{(_sw - _dw)//2}+{(_sh - _dh)//2}")

    def _limpiar_dyn():
        for w in dyn.winfo_children():
            w.destroy()
        for w in frame_btns.winfo_children():
            w.destroy()

    # ── Modo LOGIN: el usuario ya existe (o no se pudo confirmar) ──────
    def _modo_login():
        _limpiar_dyn()
        _refs["modo"] = "login"
        var_subtitulo.set("Introduce tu contraseña de Control de Pedidos.")
        var_toggle_txt.set("¿Todavía no tienes cuenta en Control de Pedidos?  Crear acceso")

        ttk.Label(dyn, text="Contraseña:", font=("Segoe UI", 9)).pack(anchor="w")
        var_pass = _SV()
        entry_pass = ttk.Entry(dyn, textvariable=var_pass,
                               font=("Segoe UI", 10), show="●")
        entry_pass.pack(fill="x", pady=(3, 0))

        var_err = _SV(value="")
        ttk.Label(dyn, textvariable=var_err, font=("Segoe UI", 8, "bold"),
                  foreground="#e74c3c", wraplength=400).pack(anchor="w", pady=(6, 0))

        def _intentar_acceso(event=None):
            clave = var_pass.get()
            if not clave:
                return
            btn_entrar.configure(state="disabled")
            dlg.configure(cursor="watch")
            dlg.update_idletasks()
            resultado = admin_auth.verificar_acceso(uwin, clave)
            dlg.configure(cursor="")
            if resultado["ok"]:
                global _admin_autenticado
                _admin_autenticado = True
                print(f"[LOG] Acceso Admin — usuario Windows: {uwin} "
                      f"({resultado.get('nombre','')}, modo={resultado.get('modo')}) — "
                      f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                dlg.destroy()
                on_success()
                return
            btn_entrar.configure(state="normal")
            if resultado.get("bloqueado"):
                mins = max(1, resultado["segundos"] // 60)
                var_err.set(f"⛔  Demasiados intentos fallidos. Vuelve a intentarlo en ~{mins} min.")
                entry_pass.configure(state="disabled")
                btn_entrar.configure(state="disabled")
            else:
                restantes = resultado.get("intentos_restantes", 0)
                var_err.set(
                    f"✗  {resultado['error']}  "
                    f"({restantes} intento{'s' if restantes != 1 else ''} restante{'s' if restantes != 1 else ''})"
                )
                var_pass.set("")
                entry_pass.focus_set()
            # El mensaje de error puede ocupar más (o menos) líneas que el
            # contenido con el que se calculó el alto inicial de la ventana
            # (ventana no redimensionable por el usuario) — recalculamos.
            _reposicionar()

        entry_pass.bind("<Return>", _intentar_acceso)

        btn_entrar = ttk.Button(frame_btns, text="  Entrar  ",
                                bootstyle="warning", command=_intentar_acceso)
        btn_entrar.pack(side="left", padx=(0, 8))
        ttk.Button(frame_btns, text="  Cancelar  ",
                   bootstyle="secondary", command=dlg.destroy).pack(side="left")
        _refs["btn_principal"] = btn_entrar

        entry_pass.focus_set()
        _reposicionar()

    # ── Modo ALTA: usuario nuevo — nombre + contraseña + repetir ───────
    _HOTELES = [
        "Guayarmina Princess", "Princess Inspire Tenerife", "La Palma Princess",
        "Taurito Princess", "TUI Blue Suite Princess", "Mogan Princess",
        "Gran Canaria Princess", "Maspalomas & Tabaiba Princess",
        "Club Jandia Princess", "Fuerteventura Princess", "Central Compras (Oficina)",
    ]

    def _modo_alta():
        _limpiar_dyn()
        _refs["modo"] = "alta"
        var_subtitulo.set(
            "Tu usuario de Windows todavía no tiene cuenta en Control de "
            "Pedidos. Rellena tus datos — un administrador revisará la "
            "solicitud y te enviará tus credenciales por correo."
        )
        var_toggle_txt.set("¿Ya tienes cuenta en Control de Pedidos?  Iniciar sesión")

        ttk.Label(dyn, text="Nombre:", font=("Segoe UI", 9)).pack(anchor="w")
        var_nombre = _SV()
        entry_nombre = ttk.Entry(dyn, textvariable=var_nombre, font=("Segoe UI", 10))
        entry_nombre.pack(fill="x", pady=(3, 10))

        ttk.Label(dyn, text="Apellidos:", font=("Segoe UI", 9)).pack(anchor="w")
        var_apellidos = _SV()
        entry_apellidos = ttk.Entry(dyn, textvariable=var_apellidos, font=("Segoe UI", 10))
        entry_apellidos.pack(fill="x", pady=(3, 10))

        ttk.Label(dyn, text="Correo electrónico:", font=("Segoe UI", 9)).pack(anchor="w")
        var_email = _SV()
        entry_email = ttk.Entry(dyn, textvariable=var_email, font=("Segoe UI", 10))
        entry_email.pack(fill="x", pady=(3, 10))

        ttk.Label(dyn, text="Teléfono móvil de empresa:", font=("Segoe UI", 9)).pack(anchor="w")
        var_movil = _SV()
        entry_movil = ttk.Entry(dyn, textvariable=var_movil, font=("Segoe UI", 10))
        entry_movil.pack(fill="x", pady=(3, 10))

        ttk.Label(dyn, text="Hotel(es) — puedes marcar varios:",
                  font=("Segoe UI", 9)).pack(anchor="w")
        list_hoteles = tk.Listbox(dyn, selectmode="multiple", exportselection=False,
                                  height=6, font=("Segoe UI", 9))
        for h in _HOTELES:
            list_hoteles.insert("end", h)
        list_hoteles.pack(fill="x", pady=(3, 0))

        var_err = _SV(value="")
        ttk.Label(dyn, textvariable=var_err, font=("Segoe UI", 8, "bold"),
                  foreground="#e74c3c", wraplength=400).pack(anchor="w", pady=(6, 0))

        def _crear_acceso(event=None):
            nombre    = var_nombre.get().strip()
            apellidos = var_apellidos.get().strip()
            email     = var_email.get().strip()
            movil     = var_movil.get().strip()
            hoteles   = ", ".join(_HOTELES[i] for i in list_hoteles.curselection())
            if not nombre:
                var_err.set("⚠  Indica tu nombre.")
                return
            if not apellidos:
                var_err.set("⚠  Indica tus apellidos.")
                return
            if not email or "@" not in email or "." not in email.split("@")[-1]:
                var_err.set("⚠  Introduce un correo electrónico válido.")
                return
            if not movil:
                var_err.set("⚠  Indica un teléfono móvil de empresa.")
                return
            if not hoteles:
                var_err.set("⚠  Selecciona al menos un hotel.")
                return
            btn_crear.configure(state="disabled")
            dlg.configure(cursor="watch")
            dlg.update_idletasks()
            resultado = admin_auth.solicitar_alta_directa(
                uwin, nombre, apellidos, email, movil, hoteles)
            dlg.configure(cursor="")

            if not resultado.get("ok"):
                btn_crear.configure(state="normal")
                error = resultado.get("error", "")
                if error == "sin_conexion":
                    var_err.set("⚠  Sin conexión con Control de Pedidos. Inténtalo de nuevo "
                                "más tarde.")
                else:
                    var_err.set(f"⚠  {error}")
                return

            dlg.destroy()

            # Precarga en "Mi Usuario" (2026-07-28): nombre a mostrar =
            # nombre + primer apellido, y el usuario de login del bridge
            # ya relleno con el usuario de Windows detectado — así el
            # usuario solo tiene que escribir una contraseña propia ahí
            # para tener acceso local ya mismo, mientras se aprueba la
            # solicitud. La contraseña la escribe él/ella, no la ponemos
            # aquí — verificar_acceso() la acepta la primera vez que la
            # introduzca en el diálogo de Acceso Administración.
            primer_apellido = apellidos.split()[0] if apellidos else ""
            nombre_mostrar = f"{nombre} {primer_apellido}".strip()
            try:
                update_nombre_usuario_db(uwin, nombre_mostrar)
                update_bridge_credentials(uwin, uwin, "")
            except Exception:  # noqa: BLE001
                import sys as _sys, traceback as _tb
                print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)

            messagebox.showinfo(
                "Solicitud enviada",
                f"Tu solicitud de acceso ha sido registrada (usuario '{uwin}').\n\n"
                f"Un administrador la revisará y recibirás un correo con tus "
                f"credenciales de acceso en cuanto se apruebe.\n\n"
                f"Mientras tanto: vuelve a pulsar «⚙ Admin» y elige la "
                f"contraseña que quieras — esa contraseña te dará acceso ya "
                f"mismo al panel de este equipo (sección «👤 Mi Usuario» "
                f"incluida), pero todavía NO al chat ni a los avisos de "
                f"Control de Pedidos, que necesitan la cuenta real.\n\n"
                f"Cuando llegue el correo de aprobación, entra en "
                f"«👤 Mi Usuario» y sustituye esa contraseña provisional por "
                f"la contraseña que te hayan enviado — eso desbloquea el "
                f"chat y el resto de funciones compartidas con Control de "
                f"Pedidos.",
                parent=ctx.app,
            )

        btn_crear = ttk.Button(frame_btns, text="  Enviar solicitud  ",
                               bootstyle="success", command=_crear_acceso)
        btn_crear.pack(side="left", padx=(0, 8))
        ttk.Button(frame_btns, text="  Cancelar  ",
                   bootstyle="secondary", command=dlg.destroy).pack(side="left")
        _refs["btn_principal"] = btn_crear

        entry_nombre.focus_set()
        _reposicionar()

    def _toggle_modo(event=None):
        if _refs["modo"] == "login":
            _modo_alta()
        else:
            _modo_login()

    lbl_toggle.bind("<Button-1>", _toggle_modo)

    # Mostrar de entrada en modo login (caso más habitual) mientras se
    # confirma en segundo plano si el usuario existe o no en la plataforma.
    _modo_login()
    dlg.deiconify()
    dlg.grab_set()

    def _comprobar_existencia_bg():
        existe = admin_auth.existe_en_plataforma(uwin)

        def _aplicar():
            if not dlg.winfo_exists():
                return
            if existe is False:
                # Confirmado que no existe todavía en Control de Pedidos.
                # OJO: esto también es cierto mientras hay una solicitud YA
                # enviada pendiente de aprobación (2026-07-28: bridge_user
                # queda precargado = uwin, sin contraseña, ver _crear_acceso
                # más arriba). En ese caso NO hay que forzar otra vez el
                # formulario de alta — hay que dejar el modo login para que
                # el usuario pueda escribir su contraseña momentánea, que es
                # lo que gestiona verificar_acceso() (bloque "1-bis"). Antes
                # esto se sobrescribía siempre, así que reabrir «⚙ Admin»
                # volvía a mostrar "Enviar solicitud" en vez de dejar
                # continuar. (Fix v4.14.4.)
                #
                # (2026-08-01) BUG en el fix anterior: la condición exigía
                # ADEMÁS que bridge_password estuviera vacío ("and not
                # _bp_pend"). Eso cubría el primer reinicio (recién enviada
                # la solicitud, sin contraseña todavía), pero en cuanto el
                # usuario creaba su contraseña momentánea (verificar_acceso
                # "1-bis" la guarda vía update_bridge_credentials con la
                # contraseña YA puesta), bridge_password dejaba de estar
                # vacío — y en el SIGUIENTE reinicio esta condición volvía a
                # dar False, cayendo al "elif" de más abajo y forzando otra
                # vez el formulario de alta. Resultado: quien ya se había
                # creado su contraseña momentánea se quedaba sin poder
                # volver a entrar al panel Admin nunca más (ni con esa
                # contraseña, porque el formulario que salía era el de
                # "Enviar solicitud", no el de login). Basta con NO exigir
                # que la contraseña esté vacía — el aviso de "solicitud
                # pendiente" es válido tanto si aún no hay contraseña local
                # como si ya la hay.
                _bu_pend, _bp_pend = get_bridge_credentials(uwin)
                _solicitud_pendiente = bool(_bu_pend) and _bu_pend.lower() == uwin.lower()
                if _solicitud_pendiente:
                    if _refs["modo"] == "login":
                        if _bp_pend:
                            var_subtitulo.set(
                                "Solicitud de acceso pendiente de aprobación. "
                                "Introduce tu contraseña para acceder a este "
                                "equipo mientras tanto."
                            )
                        else:
                            var_subtitulo.set(
                                "Solicitud de acceso ya enviada, pendiente de aprobación. "
                                "Introduce (o crea) tu contraseña momentánea para acceder "
                                "a este equipo mientras tanto."
                            )
                elif _refs["modo"] == "login":
                    _modo_alta()
            elif existe is True:
                if _refs["modo"] == "login":
                    var_subtitulo.set("Introduce tu contraseña de Control de Pedidos.")
            else:
                # Sin red: dejamos el modo login (con fallback offline al
                # hash local si ya existía un registro guardado antes).
                if _refs["modo"] == "login":
                    var_subtitulo.set(
                        "Sin conexión con Control de Pedidos — se usará el "
                        "acceso guardado en este equipo si existe."
                    )
            if dlg.winfo_exists():
                _reposicionar()

        dlg.after(0, _aplicar)

    threading.Thread(target=_comprobar_existencia_bg, daemon=True,
                     name="AdminAuthCheckExiste").start()

    dlg.bind("<Escape>", lambda e: dlg.destroy())
    dlg.wait_window()


def _ventana_vista_menu(ctx, parent):
    """Ventana de Admin para elegir vista extendida/reducida y qué botones azules
    se ven en la reducida. Al guardar se aplica al momento."""
    modo_ini, sel_ini = vista_actual(ctx.config)
    dlg = ttk.Toplevel(parent)
    dlg.withdraw()
    dlg.title("Vista del menú principal")
    dlg.resizable(False, False)
    _apply_icon(dlg)
    dlg.transient(parent)

    body = ttk.Frame(dlg, padding=(20, 16, 20, 8))
    body.pack(fill="both", expand=True)
    ttk.Label(body, text="\U0001F5A5  Vista del menú principal",
              font=("Segoe UI", 12, "bold")).pack(anchor="w")

    var_modo = StringVar(value=modo_ini)
    ttk.Radiobutton(
        body, variable=var_modo, value="extendida",
        text="Extendida (la de siempre)",
    ).pack(anchor="w", pady=(12, 0))
    ttk.Label(body, font=("Segoe UI", 8), foreground=LIGHT, wraplength=560, justify="left",
              text=f"Cabecera completa, {NUM_ACCESOS_RAPIDOS} accesos dorados y los {NUM_OPCIONES} botones azules.",
              ).pack(anchor="w", padx=(24, 0), pady=(0, 6))
    ttk.Radiobutton(
        body, variable=var_modo, value="reducida",
        text="Reducida",
    ).pack(anchor="w")
    ttk.Label(body, font=("Segoe UI", 8), foreground=LIGHT, wraplength=560, justify="left",
              text=(f"Logo y cabecera, los {VISTA_ACCESOS_REDUCIDA} primeros accesos dorados, Agenda / "
                    f"Calendario / Chat y solo los botones azules que marques abajo (máximo "
                    f"{VISTA_MAX_AZULES}, en 2 filas de 5). La ventana se hace más pequeña."),
              ).pack(anchor="w", padx=(24, 0), pady=(0, 4))

    ttk.Separator(body).pack(fill="x", pady=(8, 8))
    fila_cuenta = ttk.Frame(body)
    fila_cuenta.pack(fill="x")
    ttk.Label(fila_cuenta, text="Botones azules de la vista reducida:",
              font=("Segoe UI", 9, "bold")).pack(side="left")
    lbl_cuenta = ttk.Label(fila_cuenta, text="", font=("Segoe UI", 9), foreground=GOLD)
    lbl_cuenta.pack(side="right")

    lista = ttk.Frame(body)
    lista.pack(fill="x", pady=(6, 0))
    for c in range(3):
        lista.columnconfigure(c, weight=1, uniform="vista")
    vars_sel = {}

    def _actualizar_cuenta():
        n = sum(1 for v in vars_sel.values() if v.get())
        lbl_cuenta.configure(text=f"{n} de {VISTA_MAX_AZULES}")

    def _al_marcar(i):
        if sum(1 for v in vars_sel.values() if v.get()) > VISTA_MAX_AZULES:
            vars_sel[i].set(False)
            messagebox.showwarning(
                "Vista reducida",
                f"Se pueden marcar como máximo {VISTA_MAX_AZULES} botones.\n"
                "Desmarca alguno para poder elegir otro.", parent=dlg)
        _actualizar_cuenta()

    por_columna = (NUM_OPCIONES + 2) // 3
    for i in range(1, NUM_OPCIONES + 1):
        nombre = get_nombre(ctx, f"opcion_{i:02d}", i)
        if len(nombre) > 30:
            nombre = nombre[:29] + "…"
        vars_sel[i] = tk.BooleanVar(value=(i in sel_ini))
        ttk.Checkbutton(
            lista, text=f"{i:02d} · {nombre}", variable=vars_sel[i],
            command=lambda ix=i: _al_marcar(ix),
        ).grid(row=(i - 1) % por_columna, column=(i - 1) // por_columna,
               sticky="w", padx=(0, 10), pady=1)
    _actualizar_cuenta()

    ttk.Label(body, text="Se muestran siempre en el orden numérico del menú.",
              font=("Segoe UI", 8), foreground=LIGHT).pack(anchor="w", pady=(8, 0))

    def _guardar():
        sel = sorted(i for i, v in vars_sel.items() if v.get())
        modo = var_modo.get()
        if modo == "reducida" and not sel:
            messagebox.showwarning("Vista reducida",
                                   "Marca al menos un botón azul para la vista reducida.", parent=dlg)
            return
        ctx.config["vista_menu"] = {"modo": modo, "reducida_opciones": sel}
        ctx.save_config(ctx.config)
        dlg.destroy()
        ctx.aplicar_vista()

    ttk.Separator(dlg).pack(fill="x")
    btns = ttk.Frame(dlg, padding=(20, 10, 20, 12))
    btns.pack(fill="x")
    ttk.Button(btns, text="\u2714  Guardar y aplicar", bootstyle="success",
               command=_guardar).pack(side="left", padx=(0, 8))
    ttk.Button(btns, text="Cancelar", bootstyle="secondary",
               command=dlg.destroy).pack(side="left")
    dlg.bind("<Escape>", lambda e: dlg.destroy())

    dlg.update_idletasks()
    w, h = dlg.winfo_reqwidth(), dlg.winfo_reqheight()
    x = max(0, (dlg.winfo_screenwidth() - w) // 2)
    y = max(20, (dlg.winfo_screenheight() - h) // 2 - 20)
    dlg.geometry(f"{w}x{h}+{x}+{y}")
    dlg.deiconify()
    dlg.grab_set()


def abrir_admin(ctx):
    """Solicita credenciales y, si son correctas, abre el panel de administración.
    Si ya se autenticó en esta sesión, abre directamente el panel."""
    def _abrir_panel():
        sw = ctx.app.winfo_screenwidth()
        sh = ctx.app.winfo_screenheight()
        aw = min(1100, sw - MARGEN * 2)
        ah = min(920,  sh - MARGEN * 2)
        # Un dedo del borde superior (~40 px) y pegado a la derecha (~40 px)
        ax = sw - aw - 40
        ay = 40

        win = ttk.Toplevel()
        win.title("Administración - Accesos y Opciones del Menú")
        win.geometry(f"{aw}x{ah}+{ax}+{ay}")
        win.resizable(False, False)
        win.minsize(1100, 500)
        _apply_icon(win)

        # ── Cabecera ──────────────────────────────────────────────
        hdr = ttk.Frame(win, padding=(20, 12, 20, 6))
        hdr.pack(fill="x")
        ttk.Label(hdr, text="\u2699  Administrar Accesos y Opciones del Menú",
                  font=("Segoe UI", 13, "bold")).pack(side="left")
        ttk.Button(hdr, text="  Cerrar  ", bootstyle="secondary",
                   command=win.destroy).pack(side="right", ipadx=4)

        def _limpiar_todo():
            """Elimina toda la configuración y restaura los valores por defecto."""
            from tkinter import messagebox as _mb
            ok = _mb.askyesno(
                "Limpiar todo",
                "¿Deseas eliminar toda la configuración de botones y accesos rápidos?\n\n"
                "Todos los botones volverán a su estado 'POR DEFINIR'.",
                icon="warning",
                parent=win
            )
            if not ok:
                return
            # Borrar claves de opciones y accesos rápidos en config
            keys_to_delete = [k for k in ctx.config
                              if k.startswith("opcion_") or k.startswith("acceso_rapido_")]
            for k in keys_to_delete:
                del ctx.config[k]
            ctx.save_config(ctx.config)
            # Actualizar labels en la ventana principal
            for i in range(1, NUM_OPCIONES + 1):
                op = f"opcion_{i:02d}"
                if op in ctx.btn_labels:
                    ctx.btn_labels[op].set(f"{i}. POR DEFINIR")
            for i in range(1, NUM_ACCESOS_RAPIDOS + 1):
                ak = f"acceso_rapido_{i:02d}"
                if ak in ctx.ar_labels:
                    ctx.ar_labels[ak].set(f"\u2605  ACCESO {i}")
            win.destroy()

        def _ventana_modificar_usuario():
            """Toplevel para cambiar el nombre del usuario Windows ACTUAL en la DB.
            Incluye seccion de credenciales de Control de Pedidos para el bridge.
            """
            uwin_actual = os.getenv("USERNAME", "").lower()

            mu_win = ttk.Toplevel()
            mu_win.title("Mi Usuario")
            mu_win.resizable(False, False)
            _apply_icon(mu_win)

            _muw = 460
            mu_win.withdraw()

            from tkinter import StringVar as _SV2

            # ── Cabecera ──────────────────────────────────────────────────────
            mu_hdr = ttk.Frame(mu_win, padding=(20, 14, 20, 8))
            mu_hdr.pack(fill="x")
            ttk.Label(mu_hdr, text="\U0001f464  Mi Usuario",
                      font=("Segoe UI", 12, "bold")).pack(anchor="w")
            ttk.Label(mu_hdr,
                      text="Nombre de sesion y credenciales de Control de Pedidos.",
                      font=("Segoe UI", 9), foreground=LIGHT,
                      wraplength=420).pack(anchor="w", pady=(3, 0))
            ttk.Separator(mu_win).pack(fill="x")

            # ── Cuerpo ────────────────────────────────────────────────────────
            body = ttk.Frame(mu_win, padding=(20, 14, 20, 0))
            body.pack(fill="both", expand=True)

            # Fila: usuario Windows (solo lectura)
            row_u = ttk.Frame(body)
            row_u.pack(fill="x", pady=(0, 8))
            ttk.Label(row_u, text="Usuario Windows:",
                      font=("Segoe UI", 9), width=20, anchor="w").pack(side="left")
            ttk.Label(row_u, text=uwin_actual,
                      font=("Consolas", 10, "bold"), foreground="#C9A84C").pack(side="left")

            # Fila: nombre a mostrar
            row_n = ttk.Frame(body)
            row_n.pack(fill="x", pady=(0, 4))
            ttk.Label(row_n, text="Nombre a mostrar:",
                      font=("Segoe UI", 9), width=20, anchor="w").pack(side="left")
            var_nombre_edit = _SV2(value=ctx.nombre_usuario)
            entry_nombre = ttk.Entry(row_n, textvariable=var_nombre_edit,
                                     font=("Segoe UI", 10), width=26)
            entry_nombre.pack(side="left", fill="x", expand=True)
            entry_nombre.focus_set()
            entry_nombre.select_range(0, "end")

            # ── Separador seccion bridge ──────────────────────────────────────
            ttk.Separator(body).pack(fill="x", pady=(14, 10))
            ttk.Label(body, text="\U0001f4e1  Control de Pedidos — credenciales bridge",
                      font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 2))
            ttk.Label(body,
                      text=(
                          "Introduce tu usuario y contrasena de Control de Pedidos.\n"
                          "Los avisos emergentes mostraran SOLO tus pedidos asignados,\n"
                          "igual que los mensajes de Telegram."
                      ),
                      font=("Segoe UI", 8), foreground=LIGHT,
                      wraplength=420).pack(anchor="w", pady=(0, 8))

            # Cargar credenciales actuales desde DB
            _bu_actual, _bp_actual = get_bridge_credentials(uwin_actual)

            # Fila: usuario bridge
            row_bu = ttk.Frame(body)
            row_bu.pack(fill="x", pady=(0, 4))
            ttk.Label(row_bu, text="Usuario (login):",
                      font=("Segoe UI", 9), width=20, anchor="w").pack(side="left")
            var_bridge_user = _SV2(value=_bu_actual)
            ttk.Entry(row_bu, textvariable=var_bridge_user,
                      font=("Segoe UI", 10), width=26).pack(side="left", fill="x", expand=True)

            # Fila: contrasena bridge
            row_bp = ttk.Frame(body)
            row_bp.pack(fill="x", pady=(0, 4))
            ttk.Label(row_bp, text="Contrasena:",
                      font=("Segoe UI", 9), width=20, anchor="w").pack(side="left")
            var_bridge_pass = _SV2(value=_bp_actual)
            entry_pass = ttk.Entry(row_bp, textvariable=var_bridge_pass,
                                   font=("Segoe UI", 10), width=26, show="\u2022")
            entry_pass.pack(side="left", fill="x", expand=True)

            # Toggle mostrar/ocultar contrasena
            var_show_pass = _SV2(value="0")
            def _toggle_pass():
                entry_pass.configure(show="" if var_show_pass.get() == "1" else "\u2022")
            ttk.Checkbutton(
                row_bp, text="Mostrar", variable=var_show_pass,
                bootstyle="secondary", command=_toggle_pass
            ).pack(side="left", padx=(6, 0))

            # Indicador de estado del bridge (lectura)
            try:
                import pedidos_agenda_bridge as _pab
                _bu_activo = _pab.BRIDGE_USER or _bu_actual
                _rol_activo = _pab._session.rol
                _bridge_ok  = _pab._session._logged_in
                _estado_txt = (
                    f"\u2705  Conectado como '{_bu_activo}' (rol: {_rol_activo})"
                    if _bridge_ok
                    else "\u26a0\ufe0f  Sin sesion activa  \u2014  guardado activo al reiniciar"
                )
                _estado_col = "#2ecc71" if _bridge_ok else "#e67e22"
            except Exception:
                _estado_txt = "\u2014  Bridge no iniciado en esta sesion"
                _estado_col = LIGHT
            ttk.Label(body, text=_estado_txt,
                      font=("Segoe UI", 8), foreground=_estado_col,
                      wraplength=420).pack(anchor="w", pady=(4, 0))

            # Error label global
            var_mu_err = _SV2()
            ttk.Label(body, textvariable=var_mu_err,
                      font=("Segoe UI", 8, "bold"),
                      foreground="#e74c3c").pack(anchor="w", pady=(6, 0))

            # ── Guardar ───────────────────────────────────────────────────────
            def _guardar_cambio():
                nuevo_nombre = var_nombre_edit.get().strip()
                if not nuevo_nombre:
                    var_mu_err.set("\u26a0  El nombre no puede estar vacio.")
                    return

                nuevo_bu = var_bridge_user.get().strip()
                nuevo_bp = var_bridge_pass.get().strip()

                # 1) Guardar nombre
                update_nombre_usuario_db(uwin_actual, nuevo_nombre)
                nombre_leido = get_nombre_usuario()
                if nombre_leido != nuevo_nombre:
                    var_mu_err.set("\u26a0  No se pudo guardar el nombre. Comprueba permisos de la DB.")
                    return

                ctx.nombre_usuario = nuevo_nombre

                # 2) Guardar credenciales bridge
                update_bridge_credentials(uwin_actual, nuevo_bu, nuevo_bp)

                # 3) Aplicar credenciales al bridge en memoria (sin reiniciar)
                try:
                    import pedidos_agenda_bridge as _pab
                    if nuevo_bu != _pab.BRIDGE_USER or nuevo_bp != _pab.BRIDGE_PASSWORD:
                        _pab.BRIDGE_USER     = nuevo_bu
                        _pab.BRIDGE_PASSWORD = nuevo_bp
                        # Forzar re-login en el siguiente ciclo del hilo
                        _pab._session._logged_in = False
                        _pab._session.username   = ""
                        _pab._session.rol        = ""
                except Exception:  # noqa: BLE001
                    import sys as _sys, traceback as _tb
                    print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)

                messagebox.showinfo(
                    "Mi Usuario",
                    f"Guardado correctamente.\n\n"
                    f"  Nombre: {uwin_actual}  \u2192  {nuevo_nombre}\n"
                    f"  Bridge: {nuevo_bu or '(vacio)'}",
                    parent=mu_win,
                )
                mu_win.destroy()

            # ── Botones ───────────────────────────────────────────────────────
            ttk.Separator(mu_win).pack(fill="x", pady=(10, 0))
            mu_btns = ttk.Frame(mu_win, padding=(20, 8, 20, 12))
            mu_btns.pack(fill="x")
            ttk.Button(mu_btns, text="\u2714  Guardar",
                       bootstyle="success",
                       command=_guardar_cambio).pack(side="left", padx=(0, 8))
            ttk.Button(mu_btns, text="Cancelar",
                       bootstyle="secondary",
                       command=mu_win.destroy).pack(side="left")

            mu_win.bind("<Return>", lambda e: _guardar_cambio())
            mu_win.bind("<Escape>", lambda e: mu_win.destroy())

            # Medir altura real y centrar antes de mostrar
            mu_win.update_idletasks()
            mu_win.update()
            _muh_real = max(mu_win.winfo_reqheight(), 420)
            _msw2 = mu_win.winfo_screenwidth()
            _msh2 = mu_win.winfo_screenheight()
            _x = (_msw2 - _muw) // 2
            _y = max((_msh2 - _muh_real) // 2, 40)
            mu_win.geometry(f"{_muw}x{_muh_real}+{_x}+{_y}")
            mu_win.deiconify()

            mu_win.grab_set()

        # Botones cabecera panel Admin
        ttk.Button(
            hdr,
            text="🧹  Limpiar todo",
            bootstyle="danger-outline",
            command=_limpiar_todo,
        ).pack(side="right", padx=(0, 8), ipadx=4)

        ttk.Button(
            hdr,
            text="👤  Mi Usuario",
            bootstyle="info-outline",
            command=_ventana_modificar_usuario,
        ).pack(side="right", padx=(0, 8), ipadx=4)

        ttk.Button(
            hdr,
            text="\U0001F5A5  Vista",
            bootstyle="warning-outline",
            command=lambda: _ventana_vista_menu(ctx, win),
        ).pack(side="right", padx=(0, 8), ipadx=4)

        ttk.Separator(win).pack(fill="x", padx=20, pady=(0, 8))

        # ── Helper: fila uniforme  [Botón con nombre] [Editar] ───
        def _fila(parent, row, col, nombre, bootstyle_btn, on_edit, opcion_key=None):
            """Dibuja una celda con botón descriptivo + botón Editar."""
            cell = ttk.Frame(parent, padding=(4, 3))
            cell.grid(row=row, column=col, padx=5, pady=4, sticky="nsew")
            cell.columnconfigure(0, weight=1)

            # Indicador de submenú si está activo
            sub_activo = opcion_key and ctx.config.get(opcion_key, {}).get("submenu", {}).get("enabled", False)
            texto_btn  = ("▶ " + nombre) if sub_activo else nombre

            # Botón descriptivo — color según sección, texto pequeño para que quepa
            ttk.Button(
                cell,
                text=texto_btn,
                bootstyle=("info" if sub_activo else bootstyle_btn),
                state="disabled",
                style="sm." + ("info" if sub_activo else bootstyle_btn) + ".TButton",
            ).grid(row=0, column=0, sticky="ew", ipady=4)

            # Botón Editar — naranja/warning para destacar sobre el fondo oscuro
            ttk.Button(
                cell,
                text="✎  Editar",
                bootstyle="warning-outline",
                command=on_edit,
            ).grid(row=1, column=0, sticky="ew", pady=(5, 0), ipady=3)

        # ── SECCIÓN ACCESOS RÁPIDOS ──────────────────────────────
        ttk.Label(win,
                  text="\u2605  Accesos Rápidos del Header",
                  font=("Segoe UI", 10, "bold"),
                  foreground=GOLD).pack(anchor="w", padx=20, pady=(0, 4))

        ar_grid = ttk.Frame(win, padding=(14, 0, 14, 4))
        ar_grid.pack(fill="x")
        for c in range(3):
            ar_grid.columnconfigure(c, weight=1, uniform="ar")

        for i in range(1, NUM_ACCESOS_RAPIDOS + 1):
            ar_key  = f"acceso_rapido_{i:02d}"
            nombre  = ctx.config.get(ar_key, {}).get("nombre", f"\u2605  ACCESO {i}")
            _fila(
                ar_grid, (i - 1) // 3, (i - 1) % 3,
                nombre,
                bootstyle_btn="warning",
                on_edit=lambda ak=ar_key, ix=i, w=win: (
                    w.destroy(),
                    _ventana_config(ctx, ak, ix, titulo_display=f"Acceso Rápido {ix}")
                ),
                opcion_key=ar_key,
            )

        ttk.Separator(win).pack(fill="x", padx=20, pady=(4, 8))

        # ── SECCIÓN OPCIONES DEL MENÚ ────────────────────────────
        ttk.Label(win,
                  text="\u2630  Opciones del Menú Principal",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20, pady=(0, 4))

        # ── Exportar/Importar + Footer — empaquetado ANTES del grid
        # para que quede fijo en la parte inferior sin ser aplastado
        # por el expand=True del grid de opciones.
        # ─────────────────────────────────────────────────────────
        bottom_frame = ttk.Frame(win)
        bottom_frame.pack(side="bottom", fill="x")

        # ── Fila única de botones: Configuración y Agenda en la misma línea ──
        ttk.Separator(bottom_frame).pack(fill="x", padx=20, pady=(6, 0))
        port_frame = ttk.Frame(bottom_frame, padding=(20, 6, 20, 6))
        port_frame.pack(fill="x")

        # Grupo Configuración
        ttk.Label(port_frame,
                  text="🖥  Configuración:",
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
        ttk.Button(
            port_frame,
            text="📤  Exportar",
            bootstyle="info-outline",
            command=lambda: exportar_config(ctx, parent_win=win),
        ).pack(side="left", padx=(0, 4))
        ttk.Button(
            port_frame,
            text="📥  Importar",
            bootstyle="warning-outline",
            command=lambda: importar_config(ctx, parent_win=win),
        ).pack(side="left", padx=(0, 20))

        # Grupo Agenda
        ttk.Label(port_frame,
                  text="📅  Agenda:",
                  font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))
        ttk.Button(
            port_frame,
            text="📤  Exportar",
            bootstyle="info-outline",
            command=lambda: exportar_agenda(ctx, parent_win=win),
        ).pack(side="left", padx=(0, 4))
        ttk.Button(
            port_frame,
            text="📥  Importar",
            bootstyle="success-outline",
            command=lambda: importar_agenda(ctx, parent_win=win),
        ).pack(side="left")

        # ── Footer: firma y versión — al final del todo ──
        ttk.Separator(bottom_frame).pack(fill="x", padx=20, pady=(0, 0))
        footer_adm = ttk.Frame(bottom_frame, padding=(20, 4, 20, 6))
        footer_adm.pack(fill="x")
        ttk.Label(footer_adm,
                  text="\u00a9 VAMA 2026  \u2022  Princess Hotels & Resorts  \u2022  Central Compras Canarias",
                  font=("Segoe UI", 8), foreground=LIGHT, anchor="w").pack(side="left")
        ttk.Label(footer_adm,
                  text=ctx.app_version,
                  font=("Segoe UI", 8, "bold"), foreground=GOLD, anchor="e").pack(side="right")

        # ── Grid de opciones — ocupa el espacio restante entre cabecera y bottom ──
        grid = ttk.Frame(win, padding=(14, 0, 14, 0))
        grid.pack(fill="both", expand=True)

        COLS = 6
        for c in range(COLS):
            grid.columnconfigure(c, weight=1, uniform="adm")

        for i in range(1, NUM_OPCIONES + 1):
            opcion = f"opcion_{i:02d}"
            nombre = get_nombre(ctx, opcion, i)
            r = (i - 1) // COLS
            c = (i - 1) % COLS
            grid.rowconfigure(r, weight=1)
            _fila(
                grid, r, c,
                f"{i:02d} · {nombre}",
                bootstyle_btn="primary",
                on_edit=lambda op=opcion, ix=i, w=win: (
                    w.destroy(),
                    _ventana_config(ctx, op, ix)
                ),
                opcion_key=opcion,
            )

    # Primero solicitar credenciales; si son correctas se abre el panel
    if _admin_autenticado:
        _abrir_panel()
    else:
        _ventana_login_admin(ctx, on_success=_abrir_panel)
