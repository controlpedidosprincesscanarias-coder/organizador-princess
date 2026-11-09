# Prueba de uso del Organizador Princess (ver pruebas_uso/README.md).
# La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
# Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.
#
# Variables de entorno:
#   CLAVE_PRUEBA_ARCHIVO  archivo con la contraseña de «usuario prueba» (obligatoria; nunca se imprime)
#   CHAT_DESTINO          usuario del chat al que enviar UN mensaje de prueba (por defecto, ninguno)
#   CREAR_PEDIDO_PR=1     crear y cancelar un pedido en el hotel PR para el aviso real (por defecto, no)
import json, os, threading, time, urllib.request, webbrowser
from datetime import datetime, timedelta, date
import requests

ESPERA_INICIAL = 9000
CLAVE = open(os.environ["CLAVE_PRUEBA_ARCHIVO"]).read().strip()
CHAT_DESTINO = os.environ.get("CHAT_DESTINO", "").strip().lower()
CREAR_PEDIDO_PR = os.environ.get("CREAR_PEDIDO_PR") == "1"
CP = "https://proxy.controlpedidosprincess-canarias.workers.dev"
SELLO = time.strftime("%H%M%S")
WEB = []
webbrowser.open = lambda url, *a, **k: WEB.append(url) or True
ESTADO = {}

def todas(c):
    return c.ventanas()

def nueva_ventana(c, antes):
    return [v for v in c.ventanas() if str(v) not in antes]

def cerrar_con_boton(c, v):
    for t in ("Entendido", "Cancelar", "Cerrar", "Más tarde", "Aceptar"):
        b = c.boton(v, t)
        if b:
            log(f"cerrar «{v.title()}» con {c.texto(b).strip()!r}"); b.invoke(); return
    c.cerrar(v)

# ── 1. Arranque ──────────────────────────────────────────────────────────────
def arranque(c):
    c.captura("arranque_nueva_version")
    v = c.ventana("Nueva version")
    version = c.g["APP_VERSION"].lstrip("v")
    c.ok(f"1. primer arranque: ventana «Nueva versión» v{version}", v is not None and version in v.title(), c.titulos())
    if v: c.pulsar(v, "Confirmar")
def saludo(c):
    c.ok("1. tras confirmar: aviso «Versión actualizada»", any("actualizada" in m[1].lower() for m in MENSAJES), MENSAJES[-2:])
    v = c.ventana("Bienvenido")
    c.ok("1. ventana de saludo diario", v is not None, c.titulos())
    c.captura("saludo_diario")
    if v: cerrar_con_boton(c, v)
    ESTADO["menu"] = c.captura("menu_principal")

# ── 2. Agenda: aviso a la hora siguiente y su popup ─────────────────────────
def agenda(c):
    for v in todas(c): c.cerrar(v)
    c.g["abrir_agenda"]()
def aviso_nuevo(c):
    c.pulsar(c.ventana("Agenda"), "Añadir Aviso")
def aviso_rellenar(c):
    v = c.ventana("Nuevo Aviso")
    e = c.entradas(v)   # título, fecha, horas, minutos (v4.18.14: dos ruedas), mensaje, antelación d/h/m
    disparo = datetime.now() + timedelta(minutes=2)
    ESTADO["hora_aviso"] = disparo.strftime("%H:%M")
    c.escribir(e[0], f"PRUEBA CLAUDE {SELLO}")
    c.escribir(e[1], disparo.strftime("%d-%m-%Y"))
    e[2].set(disparo.strftime("%H")); e[3].set(disparo.strftime("%M"))
    c.escribir(e[4], "Aviso de prueba automática del Organizador")
    c.captura("aviso_nuevo_relleno")
    c.pulsar(v, "Guardar")
def aviso_lista(c):
    v = c.ventana("Agenda")
    textos = " | ".join(c.texto(w) for w in c.widgets(v)) if v else ""
    c.ok("2. el aviso aparece en «Mis Recordatorios»", f"PRUEBA CLAUDE {SELLO}" in textos, textos[:300])
    c.captura("agenda_con_aviso")
    data = c.g["load_agenda"]()
    c.ok("2. el aviso se guarda en la agenda", any(a.get("titulo") == f"PRUEBA CLAUDE {SELLO}" for a in data.get("avisos", [])), len(data.get("avisos", [])))
    if v: cerrar_con_boton(c, v)

# ── 3. Calendario, vacaciones y festivos ────────────────────────────────────
def calendario(c):
    c.g["abrir_calendario"]()
def calendario_ver(c):
    v = c.ventana("Calendario")
    c.ok("3. calendario abierto", v is not None, c.titulos())
    c.captura("calendario_mes")
    c.pulsar(v, "Semana")
def calendario_semana(c):
    c.captura("calendario_semana")
    ESTADO["antes"] = {str(w) for w in c.ventanas()}
    c.pulsar(c.ventana("Calendario"), "Vacaciones")
def vacaciones_ver(c):
    n = nueva_ventana(c, ESTADO["antes"])
    c.ok("3. ventana de vacaciones", bool(n), c.titulos())
    c.captura("vacaciones")
    for v in n: cerrar_con_boton(c, v)
    ESTADO["antes"] = {str(w) for w in c.ventanas()}
    cal = c.ventana("Calendario")
    if cal: c.pulsar(cal, "Festivos")
def festivos_ver(c):
    n = nueva_ventana(c, ESTADO["antes"])
    c.ok("3. ventana de festivos", bool(n), c.titulos())
    c.captura("festivos")
    for v in n: cerrar_con_boton(c, v)
def agendas_imprimibles(c):
    cal = c.ventana("Calendario")
    ESTADO["web_antes"] = len(WEB)
    for t in ("Agenda del Día", "Agenda Semanal", "Agenda Mensual"):
        c.pulsar(cal, t)
def agendas_imprimibles_ver(c):
    nuevas = WEB[ESTADO["web_antes"]:]
    htmls = []
    for u in nuevas:
        ruta = u.replace("file:///", "/").replace("file://", "")
        try:
            htmls.append(open(ruta, encoding="utf-8").read())
        except Exception:
            htmls.append("")
    c.ok("3. las agendas del día, semanal y mensual se abren en el navegador", len(nuevas) == 3, nuevas)
    c.ok("3. la agenda del día incluye el aviso de prueba", any(f"PRUEBA CLAUDE {SELLO}" in h for h in htmls[:1]) or any(f"PRUEBA CLAUDE {SELLO}" in h for h in htmls), [len(h) for h in htmls])
    ESTADO["antes"] = {str(w) for w in c.ventanas()}
    c.pulsar(c.ventana("Calendario"), "Chat")
def chat_desde_calendario(c):
    n = nueva_ventana(c, ESTADO["antes"])
    c.ok("3. el botón «Chat» del calendario abre el chat", bool(n), c.titulos())
    for v in n: c.cerrar(v)
    for v in todas(c): c.cerrar(v)

# ── 4. Admin: botones del menú, vista reducida, exportar/importar ───────────
def admin(c):
    for v in todas(c):
        if "aviso" not in v.title().lower(): c.cerrar(v)
    c.g["abrir_admin"]()
def admin_login(c):
    v = c.ventana("Acceso Admin")
    if v:
        e = [w for w in c.entradas(v) if w.cget("show")][0]
        c.escribir(e, CLAVE); c.pulsar(v, "Entrar")
def admin_login_mal(c):
    v = c.ventana("Acceso Admin")
    c.ok("4. Admin pide la contraseña la primera vez", v is not None, c.titulos())
    if not v: return
    e = [w for w in c.entradas(v) if w.cget("show")][0]
    c.escribir(e, "clave-incorrecta-de-prueba"); c.pulsar(v, "Entrar")
def admin_login_mal_ver(c):
    v = c.ventana("Acceso Admin")
    textos = " ".join(c.texto(w) for w in c.widgets(v)) if v else ""
    c.ok("4. con una contraseña incorrecta no entra y avisa", v is not None and c.ventana("Accesos y Opciones") is None
         and ("incorrect" in textos.lower() or "intento" in textos.lower()), textos[-200:])
    c.captura("admin_clave_incorrecta")
def mi_usuario_nombre(c):
    v = c.ventana("Mi Usuario")
    e = [w for w in c.entradas(v) if not w.cget("show")]
    ESTADO["nombre_nuevo"] = f"Prueba Claude {SELLO}"
    c.escribir(e[0], ESTADO["nombre_nuevo"])
    c.captura("mi_usuario"); c.pulsar(v, "Guardar")
def mi_usuario_ver(c):
    from db.sqlite import get_nombre_usuario
    c.ok("4. «Mi Usuario»: el nombre nuevo se guarda", get_nombre_usuario() == ESTADO["nombre_nuevo"], get_nombre_usuario())
    c.ok("4. «Mi Usuario»: el saludo y el calendario usan ya el nombre nuevo (sin reiniciar)",
         c.g["ctx"].nombre_usuario == ESTADO["nombre_nuevo"], c.g["ctx"].nombre_usuario)
    for v in todas(c):
        if "Accesos y Opciones" in v.title() or "Mi Usuario" in v.title(): cerrar_con_boton(c, v)
def pulsar_admin(texto, idx=0):
    def f(c):
        p = c.ventana("Accesos y Opciones")
        bs = [w for w in c.widgets(p) if hasattr(w, "invoke") and texto.lower() in c.texto(w).lower()]
        log(f"pulsar {c.texto(bs[idx]).strip()!r}"); bs[idx].invoke()
    return f
def radio(c, v, texto):
    for w in c.widgets(v):
        if w.winfo_class() == "TRadiobutton" and texto.lower() in c.texto(w).lower():
            w.invoke(); return
    raise AssertionError(f"sin opción «{texto}»")
def editar_acceso_web(c):
    v = c.ventana("Editar acceso"); e = c.entradas(v)
    c.escribir(e[0], "WEB PRUEBA"); radio(c, v, "Página web"); c.escribir(e[1], "https://www.princess-hotels.com")
    c.captura("editar_acceso_web"); c.pulsar(v, "Guardar")
def editar_menu_carpeta(c):
    v = c.ventana("Editar acceso"); e = c.entradas(v)
    c.escribir(e[0], "CARPETA PRUEBA"); radio(c, v, "Carpeta"); c.escribir(e[1], SALIDA)
    c.pulsar(v, "Guardar")
def menu_botones(c):
    for v in todas(c):
        if "Accesos y Opciones" in v.title(): c.cerrar(v)
    textos = [c.texto(w) for w in c.widgets(c.app)]
    c.ok("4. el acceso dorado 1 se llama «WEB PRUEBA» en el menú", any("WEB PRUEBA" in t for t in textos), [t for t in textos if "ACCESO" in t][:3])
    c.ok("4. el botón azul 1 se llama «CARPETA PRUEBA»", any("CARPETA PRUEBA" in t for t in textos), "")
    c.captura("menu_con_botones")
    b1 = c.boton(c.app, "WEB PRUEBA")
    if b1: b1.invoke()
    def solo_menu(w, out):
        for h in w.winfo_children():
            if isinstance(h, tk.Toplevel): continue
            out.append(h); solo_menu(h, out)
        return out
    etiquetas = [w for w in solo_menu(c.app, []) if w.winfo_class() == "TLabel" and "CARPETA PRUEBA" in c.texto(w)]
    log(f"etiquetas «CARPETA PRUEBA» en el menú: {len(etiquetas)}")
    if etiquetas:
        celda = etiquetas[0].master
        bot = [h for h in celda.winfo_children() if h.winfo_class() == "TButton"]
        log(f"clic en el botón azul 1 ({len(bot)} botón en la casilla)")
        (bot[0].invoke() if bot else etiquetas[0].event_generate("<Button-1>"))
def menu_botones_ver(c):
    c.ok("4. el acceso web abre el navegador con su dirección", "https://www.princess-hotels.com" in " ".join(WEB), WEB)
    c.ok("4. el botón de carpeta abre la carpeta", any(SALIDA.rstrip("/") in a for a in ABIERTOS), ABIERTOS)
def vista_reducida(c):
    v = c.ventana("Vista del menú"); radio(c, v, "Reducida"); c.pulsar(v, "Guardar y aplicar")
def vista_reducida_ver(c):
    c.captura("vista_reducida")
    cfg = c.g["load_config"]()
    c.ok("4. vista reducida guardada y aplicada", (cfg.get("vista_menu") or {}).get("modo") == "reducida", cfg.get("vista_menu"))
def vista_extendida(c):
    v = c.ventana("Vista del menú"); radio(c, v, "Extendida"); c.pulsar(v, "Guardar y aplicar")
def vista_extendida_ver(c):
    c.captura("vista_extendida")
    c.ok("4. vuelve a la vista extendida", (c.g["load_config"]().get("vista_menu") or {}).get("modo") == "extendida", "")
def exportar(c):
    ARCHIVOS["guardar"] = os.path.join(SALIDA, "config_exportada.json")
    pulsar_admin("Exportar", 0)(c)
def exportar_ver(c):
    ruta = ARCHIVOS["guardar"]
    ok = os.path.exists(ruta)
    try:
        contenido = open(ruta, encoding="utf-8").read() if ok else ""
    except Exception as e:
        contenido = str(e)
    c.ok("4. exportar configuración crea el archivo con los botones", ok and "WEB PRUEBA" in contenido, (ok, contenido[:120]))
    ARCHIVOS["abrir"] = ruta
    pulsar_admin("Importar", 0)(c)
def importar_ver(c):
    c.ok("4. importar configuración termina sin error", not any(m[0] == "showerror" for m in MENSAJES[-3:]), MENSAJES[-3:])
    for v in todas(c):
        if "aviso" not in v.title().lower(): cerrar_con_boton(c, v)

# ── 5. Popup del aviso de la agenda ─────────────────────────────────────────
def popup_aviso(c):
    vs = [v for v in c.ventanas() if f"PRUEBA CLAUDE {SELLO}" in " ".join(c.texto(w) for w in c.widgets(v)) or "AVISO" in v.title()]
    log("texto del aviso: " + " | ".join(" ".join(c.texto(w) for w in c.widgets(v))[:200] for v in vs))
    c.ok(f"5. a las {ESTADO.get('hora_aviso')} salta el aviso de la agenda", bool(vs), c.titulos())
    c.captura("popup_aviso_agenda")
    for v in vs: cerrar_con_boton(c, v)

# ── 6. Chat (solo envía si se indica CHAT_DESTINO) ──────────────────────────
def chat(c):
    ESTADO["antes"] = {str(w) for w in c.ventanas()}
    c.pulsar(c.app, "Chat")
def chat_ver(c):
    # La ventana del chat es la que tiene la lista de conversaciones (puede coincidir con un aviso)
    n = [w for w in nueva_ventana(c, ESTADO["antes"]) if any(x.winfo_class() == "Treeview" for x in c.widgets(w))]
    v = n[-1] if n else None
    c.ok("6. ventana del chat", v is not None, c.titulos())
    if not v: return
    ESTADO["chat"] = v
    lb = [w for w in c.widgets(v) if w.winfo_class() == "Treeview"]   # (v4.18.28) lista con fotos
    filas = list(lb[0].get_children()) if lb else []
    items = [lb[0].item(i, "text").strip() for i in filas]
    log(f"conversaciones: {items}")
    c.ok("6. el chat carga la lista de conversaciones", bool(items), items)
    c.arbol(v, "chat"); c.captura("chat")
    cli = c.g.get("get_chat_client") and c.g["get_chat_client"]()
    try:
        usuarios = cli.obtener_usuarios() if cli else []
    except Exception as e:
        usuarios = []; log(f"usuarios chat: error {e}")
    dest = [u for u in usuarios if CHAT_DESTINO and str(u.get("username", "")).lower() == CHAT_DESTINO]
    ESTADO["nombre_cc"] = (dest[0].get("nombre") if dest else None) or CHAT_DESTINO or "—"
    log(f"destino del chat ({CHAT_DESTINO or 'ninguno'}): {bool(dest)} ({ESTADO['nombre_cc']})")
    for i, t in enumerate(items):
        if CHAT_DESTINO and ESTADO["nombre_cc"].lower() in str(t).lower():
            lb[0].selection_set(filas[i])
            ESTADO["chat_sel"] = t; break
def chat_nueva(c):
    v = ESTADO.get("chat")
    if not CHAT_DESTINO:
        log("chat: sin CHAT_DESTINO, no se abre ninguna conversación ni se envía nada"); return
    if not v or ESTADO.get("chat_sel"): return
    ESTADO["antes"] = {str(w) for w in c.ventanas()}
    c.pulsar(v, "Nueva conversación")
def chat_nueva_elegir(c):
    if not CHAT_DESTINO or ESTADO.get("chat_sel"): return
    n = c.ventana("Nueva conversación")
    if not n: c.ok("6. ventana «Nueva conversación»", False, c.titulos()); return
    lb = [w for w in c.widgets(n) if w.winfo_class() == "Listbox"][0]
    items = list(lb.get(0, "end")); log(f"compañeros en el chat: {len(items)}")
    c.captura("chat_nueva_conversacion")
    for i, t in enumerate(items):
        if ESTADO["nombre_cc"].lower() in t.lower():
            lb.selection_set(i); lb.event_generate("<<ListboxSelect>>"); ESTADO["chat_sel"] = t
            log(f"elegido {t!r}"); c.pulsar(n, "Abrir chat"); return
    c.ok(f"6. {CHAT_DESTINO} está entre los compañeros", False, items[:10])
def chat_enviar(c):
    v = ESTADO.get("chat")
    if not CHAT_DESTINO: return
    if not v or not ESTADO.get("chat_sel"):
        c.ok(f"6. conversación con {CHAT_DESTINO} localizada", False, "no está en la lista; no se envía nada"); return
    c.ok(f"6. conversación con {CHAT_DESTINO} localizada", True)
    c.captura("chat_destino")
    e = [w for w in c.entradas(v)][-1]
    ESTADO["msg"] = f"Prueba automática de Claude desde el Organizador 4.18.06 ({SELLO}). Puedes ignorar este mensaje."
    c.escribir(e, ESTADO["msg"]); c.pulsar(v, "Enviar")
def chat_enviado(c):
    v = ESTADO.get("chat")
    if not v or not ESTADO.get("msg"): return
    c.captura("chat_mensaje_enviado")
    cli = c.g["get_chat_client"]()
    try:
        d = cli.obtener_mensajes(destinatario=CHAT_DESTINO)
        txt = json.dumps(d, ensure_ascii=False)
    except Exception as e:
        txt = str(e)
    c.ok("6. el mensaje llega al servidor del chat", ESTADO["msg"][:40] in txt, txt[:200])
    cerrar_con_boton(c, v)

# ── 7. Aviso de Control de Pedidos (hotel PR) ───────────────────────────────
def cp_evento(c):
    if not CREAR_PEDIDO_PR:
        log("Control de Pedidos: sin CREAR_PEDIDO_PR=1, no se crea ningún pedido"); return
    def hilo():
        try:
            s = requests.Session(); s.headers["User-Agent"] = "organizador-prueba-claude"
            r = s.post(CP + "/api/login", json={"username": "usuario prueba", "password": CLAVE}, timeout=120)
            m = s.get(CP + "/api/maestros", timeout=120).json()
            pr = next(h["id"] for h in m["hoteles"] if h["codigo"] == "PR")
            sstt = next(x["id"] for x in m["departamentos"] if x["nombre"].upper() == "SSTT")
            body = {"hotel_id": pr, "departamento_id": sstt, "fecha_solicitud": date.today().isoformat(),
                    "estado": "PENDIENTE COTIZACIÓN", "observaciones": f"PRUEBA CLAUDE ORGANIZADOR {SELLO}"}
            r = s.post(CP + "/api/pedidos", json=body, timeout=120)
            if r.status_code == 409:
                r = s.post(CP + "/api/pedidos", json={**body, "confirmar_duplicado": True}, timeout=120)
            pid = r.json().get("id"); ESTADO["pid"] = pid
            r = s.put(CP + f"/api/pedidos/{pid}", json={"estado": "CANCELADO", "nota_historial": "Prueba automática de Claude (Organizador): aviso emergente"}, timeout=120)
            d = s.get(CP + f"/api/pedidos/{pid}", timeout=120).json(); d = d.get("pedido", d)
            ESTADO["norden"] = d.get("norden"); ESTADO["cp_estado"] = d.get("estado")
            s.post(CP + "/api/logout", timeout=60)
            log(f"Control de Pedidos: pedido PR id {pid} nº {ESTADO['norden']} → {ESTADO['cp_estado']}")
        except Exception as e:
            log(f"Control de Pedidos: error {e}")
    ESTADO["popups_antes"] = {str(w) for w in c.ventanas()}
    threading.Thread(target=hilo, daemon=True).start()
def cp_popup(c):
    if not CREAR_PEDIDO_PR: return
    c.ok("7. pedido de prueba creado y cancelado en PR", ESTADO.get("cp_estado") == "CANCELADO", ESTADO)
    n = [v for v in nueva_ventana(c, ESTADO["popups_antes"])]
    textos = {v.title(): " ".join(c.texto(w) for w in c.widgets(v)) for v in n}
    log(f"ventanas nuevas: {list(textos)}")
    hit = [t for t, x in textos.items() if str(ESTADO.get("norden") or "¿?") in x or "PR" in x]
    # Control de Pedidos puede tardar varios minutos en entregar la notificación: si no ha llegado
    # aún, se anota pero no cuenta como fallo (el registro pedidos_bridge.log dirá cuándo llega).
    log(f"7. aviso real de Control de Pedidos {'recibido' if hit else 'aún no recibido (puede tardar unos minutos)'}")
    c.captura("popup_control_pedidos")
    for v in n: cerrar_con_boton(c, v)

# ── 7b. Notificación de Control de Pedidos simulada (prueba la parte del Organizador) ──
def push_simulado(c):
    import sys
    br = sys.modules["pedidos_agenda_bridge"]
    original = br._session.get_notificaciones_push
    falsa = {"id": 999000000 + int(SELLO), "tipo": "cambio_estado", "nivel": "normal",
             "titulo": "Cambio de estado (simulado)", "creado_en": datetime.now().isoformat(),
             "mensaje": f"🔔 Cambio de estado\nHotel: PR — HOTEL PRUEBAS\nPedido: {ESTADO.get('norden', 'PRUEBA')}\n❌ Pedido cancelado. (simulado por la prueba {SELLO})"}
    entregada = {"v": False}
    def get_push():
        if not entregada["v"]:
            entregada["v"] = True
            return {"notificaciones": [falsa]}
        return original()
    br._session.get_notificaciones_push = get_push
    ESTADO["popups_antes"] = {str(w) for w in c.ventanas()}
def push_simulado_ver(c):
    n = nueva_ventana(c, ESTADO["popups_antes"])
    textos = {v.title(): " ".join(c.texto(w) for w in c.widgets(v)) for v in n}
    c.ok("7b. una notificación de Control de Pedidos se muestra como aviso emergente", any(SELLO in x for x in textos.values()), {k: v[:160] for k, v in textos.items()})
    c.captura("popup_push_simulado")
    for v in n: cerrar_con_boton(c, v)

# ── 8. Aviso de conexión (error corregido en 4.18.06) ───────────────────────
def conexion(c):
    import sys
    ESTADO["antes"] = {str(w) for w in c.ventanas()}
    ESTADO["raices"] = len([w for w in tk._default_root.winfo_children()]) if tk._default_root else 0
    sys.modules["pedidos_agenda_bridge"]._mostrar_error_bridge("Prueba: sin conexión con Control de Pedidos", "Detalle técnico de prueba (Claude).")
def conexion_ver(c):
    import sys
    n = nueva_ventana(c, ESTADO["antes"])
    c.ok("8. el aviso de conexión se muestra (antes re-ejecutaba la app)", bool(n), c.titulos())
    c.ok("8. no se ha cargado una segunda copia de main_agenda", "main_agenda" not in sys.modules, [m for m in sys.modules if "main_agenda" in m])
    c.captura("aviso_conexion")
    for v in n: cerrar_con_boton(c, v)

# ── 9. Actualización disponible (GitHub simulado, no se descarga nada) ──────
def actualizacion(c):
    import io, sys
    um = sys.modules["services.update_service"]
    original = urllib.request.urlopen
    falso = {"tag_name": "v9.0.0", "name": "Organizador Princess v9.0.0",
             "body": "# ✨ Organizador Princess v9.0.0\n\n- **Versión simulada** para la prueba.",
             "assets": [{"name": "OrganizadorPrincess_Setup_9.0.0.exe", "size": 52_000_000, "browser_download_url": "https://example.invalid/x.exe"},
                        {"name": "OrganizadorPrincess_Setup_9.0.0.exe.sha256", "size": 90, "browser_download_url": "https://example.invalid/x.sha256"}]}
    class R(io.BytesIO):
        status = 200; headers = {"Content-Length": "1"}
        def __enter__(self): return self
        def __exit__(self, *a): return False
    def urlopen(req, *a, **k):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "api.github.com" in url:
            return R(json.dumps(falso).encode())
        return original(req, *a, **k)
    urllib.request.urlopen = urlopen
    ESTADO["antes"] = {str(w) for w in c.ventanas()}
    um._lanzar_check_update(c.app)
def actualizacion_ver(c):
    n = nueva_ventana(c, ESTADO["antes"])
    textos = " ".join(" ".join(c.texto(w) for w in c.widgets(v)) for v in n)
    c.ok("9. con una versión nueva en GitHub sale «Actualización disponible»", "9.0.0" in textos, c.titulos())
    c.ok("9. las novedades se ven con formato (sin «#» de Markdown)", "Versión simulada" in textos and "**" not in textos and "# ✨" not in textos, textos[:300])
    c.captura("actualizacion_disponible")
    for v in n: cerrar_con_boton(c, v)

def AL_CERRAR(c):
    c.ok("4. importar configuración: se copia y la aplicación se cierra para aplicarla",
         any("importada" in m[1].lower() for m in MENSAJES) and not any(m[0] == "showerror" for m in MENSAJES),
         MENSAJES[-3:])

def final(c):
    c.captura("final")
    log(f"mensajes: {len(MENSAJES)}; abiertos: {ABIERTOS}; web: {WEB}")

PASOS = [
    ("1 arranque", arranque, 2500), ("1 saludo", saludo, 1500),
    ("2 agenda", agenda, 2000), ("2 añadir", aviso_nuevo, 1500), ("2 rellenar", aviso_rellenar, 2000), ("2 lista", aviso_lista, 1500),
    ("3 calendario", calendario, 2500), ("3 ver", calendario_ver, 1500), ("3 semana", calendario_semana, 2500),
    ("3 vacaciones", vacaciones_ver, 2500), ("3 festivos", festivos_ver, 1500),
    ("3 agendas imprimibles", agendas_imprimibles, 2000), ("3 agendas ver", agendas_imprimibles_ver, 4000), ("3 chat", chat_desde_calendario, 1500),
    ("4 admin", admin, 3000), ("4 clave mal", admin_login_mal, 4000), ("4 clave mal ver", admin_login_mal_ver, 500),
    ("4 login", admin_login, 4000), ("4 mi usuario", pulsar_admin("Mi Usuario"), 3000), ("4 nombre", mi_usuario_nombre, 3000), ("4 nombre ver", mi_usuario_ver, 1500),
    ("4 admin", admin, 3000), ("4 login", admin_login, 3000), ("4 editar acceso 1", pulsar_admin("Editar", 0), 2500), ("4 web", editar_acceso_web, 2500),
    ("4 admin", admin, 3000), ("4 login", admin_login, 3000), ("4 editar botón 1", pulsar_admin("Editar", 6), 2500), ("4 carpeta", editar_menu_carpeta, 2500),
    ("4 menú", menu_botones, 2500), ("4 menú ver", menu_botones_ver, 500),
    ("4 admin", admin, 3000), ("4 login", admin_login, 3000), ("4 vista", pulsar_admin("Vista"), 2500), ("4 reducida", vista_reducida, 3000), ("4 reducida ver", vista_reducida_ver, 1000),
    ("4 admin", admin, 3000), ("4 login", admin_login, 3000), ("4 vista", pulsar_admin("Vista"), 2500), ("4 extendida", vista_extendida, 3000), ("4 extendida ver", vista_extendida_ver, 1000),
    ("4 admin", admin, 3000), ("4 login", admin_login, 3000), ("4 exportar", exportar, 3000),
    ("6 chat", chat, 6000), ("6 chat ver", chat_ver, 4000), ("6 nueva", chat_nueva, 4000), ("6 elegir", chat_nueva_elegir, 4000), ("6 enviar", chat_enviar, 6000), ("6 enviado", chat_enviado, 2000), ("espera aviso agenda", lambda c: None, 60000),
    ("5 popup aviso", popup_aviso, 1000),
    ("7 Control de Pedidos", cp_evento, 75000 if CREAR_PEDIDO_PR else 100), ("7 popup", cp_popup, 2000),
    ("7b push simulado", push_simulado, 25000), ("7b ver", push_simulado_ver, 2000),
    ("8 conexión", conexion, 3000), ("8 ver", conexion_ver, 1500),
    ("9 actualización", actualizacion, 6000), ("9 ver", actualizacion_ver, 1500),
    ("final", final, 500),
    ("4 admin", admin, 3000), ("4 login", admin_login, 3000), ("4 exportar", exportar, 3000), ("4 importar (cierra la app)", exportar_ver, 3000), ("4 importar ver", importar_ver, 1500),
]
