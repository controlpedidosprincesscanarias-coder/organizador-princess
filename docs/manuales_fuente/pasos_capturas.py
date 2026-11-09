# Capturas de los manuales del Organizador Princess (ver README.md de esta carpeta).
# La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
# Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.
#
# Lo ejecuta pruebas_uso/conductor.py dentro del bucle de Tkinter (capturas.sh lo prepara todo).
# Cada captura es la ventana recortada, al doble de tamaño, con una barra de título como la de
# Windows y los números de referencia en naranja, como en los manuales de Control de Pedidos.
import io, os, subprocess, sys, unicodedata, webbrowser
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont

ESPERA_INICIAL = 7000
SOLO = os.environ.get("SOLO", "")
VOLCAR = os.environ.get("VOLCAR") == "1"
RAIZ_ORG = os.environ["ORG_RAIZ"]
NARANJA = (232, 89, 12)
E = 2  # escala de las capturas
FUENTE = "/usr/share/fonts/opentype/inter/Inter-Bold.otf"
FUENTE_TIT = "/usr/share/fonts/opentype/inter/Inter-Regular.otf"
WEB = []
webbrowser.open = lambda url, *a, **k: WEB.append(url) or True
ESTADO = {}


# ── utilidades ───────────────────────────────────────────────────────────────
def pantalla():
    datos = subprocess.run(["import", "-window", "root", "png:-"], capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(datos)).convert("RGB")


def buscar(c, raiz, texto, clase=None, n=0):
    """El n-ésimo widget de `raiz` cuyo texto contiene `texto` (y de la clase indicada)."""
    hits = [w for w in c.widgets(raiz) if (clase is None or w.winfo_class() == clase)
            and texto.lower() in c.texto(w).lower() and w.winfo_ismapped()]
    if len(hits) <= n:
        log(f"   ⚠ sin widget «{texto}» ({clase}) n={n}")
        return None
    return hits[n]


def de_clase(c, raiz, clase, n=0):
    hits = [w for w in c.widgets(raiz) if w.winfo_class() == clase and w.winfo_ismapped()]
    return hits[n] if len(hits) > n else None


def volcar(c, v, nombre):
    if not VOLCAR:
        return
    with open(os.path.join(SALIDA, f"arbol_{nombre}.txt"), "w", encoding="utf-8") as f:
        def rec(w, n=0):
            try:
                g = f"{w.winfo_rootx() - v.winfo_rootx()},{w.winfo_rooty() - v.winfo_rooty()} {w.winfo_width()}x{w.winfo_height()}"
                oculto = w.winfo_class() in ("TEntry", "Entry") and bool(w.cget("show"))
                f.write("  " * n + f"{w.winfo_class()} {'«oculto»' if oculto else repr(c.texto(w)[:60])} @{g}\n")
            except tk.TclError:
                pass
            for h in w.winfo_children():
                if not isinstance(h, tk.Toplevel):
                    rec(h, n + 1)
        rec(v)


def _barra_titulo(img, titulo):
    W = img.width
    h = 32 * E
    barra = Image.new("RGB", (W, h), (32, 32, 32))
    d = ImageDraw.Draw(barra)
    try:
        ico = Image.open(os.path.join(RAIZ_ORG, "assets", "logo.png")).convert("RGBA")
        ico.thumbnail((18 * E, 18 * E))
        barra.paste(ico, (10 * E, (h - ico.height) // 2), ico)
    except Exception:  # noqa: BLE001
        pass
    f = ImageFont.truetype(FUENTE_TIT, 12 * E)
    titulo = "".join(ch for ch in titulo if unicodedata.category(ch) not in ("So", "Mn", "Cn", "Co", "Cs")).strip()
    d.text((36 * E, h // 2), titulo, font=f, fill=(235, 235, 235), anchor="lm")
    # Minimizar, maximizar y cerrar, dibujados como en Windows 11
    y = h // 2
    xc = W - 23 * E
    d.line((xc - 5 * E, y - 5 * E, xc + 5 * E, y + 5 * E), fill=(235, 235, 235), width=E)
    d.line((xc - 5 * E, y + 5 * E, xc + 5 * E, y - 5 * E), fill=(235, 235, 235), width=E)
    xm = W - 69 * E
    d.rectangle((xm - 5 * E, y - 5 * E, xm + 5 * E, y + 5 * E), outline=(235, 235, 235), width=E)
    xn = W - 115 * E
    d.line((xn - 5 * E, y, xn + 5 * E, y), fill=(235, 235, 235), width=E)
    out = Image.new("RGB", (W, img.height + h))
    out.paste(barra, (0, 0)); out.paste(img, (0, h))
    return out, h


def _marca(d, caja, n, lado="tl", borde=True, W=0, H=0):
    x0, y0, x1, y1 = caja
    if borde:
        d.rounded_rectangle((x0 - 4 * E, y0 - 4 * E, x1 + 4 * E, y1 + 4 * E), radius=8 * E, outline=NARANJA, width=int(2.5 * E))
    if n is None:
        return
    s = 26 * E
    bw, bh = x1 - x0, y1 - y0
    pos = {"l": (x0 - s - 8 * E, y0 + bh / 2 - s / 2), "r": (x1 + 8 * E, y0 + bh / 2 - s / 2),
           "t": (x0 + bw / 2 - s / 2, y0 - s - 8 * E), "b": (x0 + bw / 2 - s / 2, y1 + 8 * E),
           "tr": (x1 - s / 2, y0 - s / 2 - 4 * E), "ir": (x1 - s - 6 * E, y0 + bh / 2 - s / 2),
           "in": (x0 + 4 * E, y0 + bh / 2 - s / 2)}.get(lado, (x0 - s / 2 - 2 * E, y0 - s / 2 - 2 * E))
    x, y = max(2, min(W - s - 2, pos[0])), max(2, min(H - s - 2, pos[1]))
    d.ellipse((x - 2 * E, y - 2 * E, x + s + 2 * E, y + s + 2 * E), fill=(255, 255, 255))
    d.ellipse((x, y, x + s, y + s), fill=NARANJA)
    d.text((x + s / 2, y + s / 2), str(n), font=ImageFont.truetype(FUENTE, 14 * E), fill=(255, 255, 255), anchor="mm")


def foto(c, v, nombre, marcas=(), titulo=None, recorte=None, barra=True):
    """Guarda la ventana `v` como <nombre>.png. marcas: [(widget, n, lado, borde)], recorte: (x, y, w, h) en la ventana."""
    if SOLO and not nombre.startswith(SOLO):
        return
    if v is None:
        log(f"   ⚠ sin ventana para {nombre}")
        return
    try:
        v.lift()
    except tk.TclError:
        pass
    c.app.update_idletasks(); c.app.update()
    volcar(c, v, nombre)
    vx, vy, W, H = v.winfo_rootx(), v.winfo_rooty(), v.winfo_width(), v.winfo_height()
    img = pantalla().crop((vx, vy, vx + W, vy + H)).resize((W * E, H * E), Image.LANCZOS)
    dy = 0
    if barra and not recorte:
        img, dy = _barra_titulo(img, titulo if titulo is not None else v.title())
    d = ImageDraw.Draw(img)
    rx, ry = (recorte[0], recorte[1]) if recorte else (0, 0)
    for m in marcas:
        w, n = m[0], m[1]
        if w is None:
            log(f"   ⚠ {nombre}: falta el widget de la marca {n}")
            continue
        if isinstance(w, tuple):           # caja a mano (x, y, ancho, alto) en la ventana
            x, y, ww, hh = w
        else:
            x, y, ww, hh = w.winfo_rootx() - vx, w.winfo_rooty() - vy, w.winfo_width(), w.winfo_height()
        x -= rx; y -= ry
        _marca(d, (x * E, y * E + dy, (x + ww) * E, (y + hh) * E + dy), n, m[2] if len(m) > 2 else "tl",
               m[3] if len(m) > 3 else True, img.width if not recorte else recorte[2] * E, img.height if not recorte else recorte[3] * E)
    if recorte:
        img = img.crop((recorte[0] * E, recorte[1] * E, (recorte[0] + recorte[2]) * E, (recorte[1] + recorte[3]) * E))
    img.save(os.path.join(SALIDA, nombre + ".png"))
    log(f"  ✓ {nombre}")


def caja_de(c, v, ws):
    """Caja (x, y, ancho, alto) que envuelve varios widgets, en coordenadas de la ventana."""
    ws = [w for w in ws if w.winfo_ismapped()]
    if not ws:
        return None
    x0 = min(w.winfo_rootx() for w in ws) - v.winfo_rootx(); y0 = min(w.winfo_rooty() for w in ws) - v.winfo_rooty()
    x1 = max(w.winfo_rootx() + w.winfo_width() for w in ws) - v.winfo_rootx()
    y1 = max(w.winfo_rooty() + w.winfo_height() for w in ws) - v.winfo_rooty()
    return (x0, y0, x1 - x0, y1 - y0)


def nuevas(c, antes):
    return [v for v in c.ventanas() if str(v) not in antes]


def guardar_ventanas():
    ESTADO["antes"] = {str(w) for w in C.ventanas()}


def cerrar_todo(c, excepto=()):
    for v in c.ventanas():
        if not any(e in v.title() for e in excepto):
            c.cerrar(v)


# ── 1. Arranque: «Nueva versión» y saludo ────────────────────────────────────
def arranque(c):
    v = c.ventana("Nueva version")
    if v:   # la carpeta de la copia, como se ve en Windows
        for e in c.entradas(v):
            if "organizador" in e.get().lower():
                st = str(e.cget("state")); e.configure(state="normal")
                c.escribir(e, r"C:\Users\ana.demo\AppData\Roaming\OrganizadorPrincess"); e.configure(state=st)
    foto(c, v, "u_nueva_version", [(buscar(c, v, "Solo actualizar"), 1, "r"), (buscar(c, v, "desde cero"), 2, "r"),
                                     (buscar(c, v, "Copia de seguridad", "TLabelframe"), 3, "tr"),
                                     (buscar(c, v, "Confirmar"), 4, "l")] if v else [])
    sys.modules["pedidos_agenda_bridge"]._bridge_listo.set()   # sin Control de Pedidos: el saludo no espera
    if v:
        c.pulsar(v, "Confirmar")


def saludo(c):
    v = c.ventana("Bienvenido")
    log(f"ventanas: {c.titulos()}")
    foto(c, v, "u_saludo")
    if v:
        c.cerrar(v)


# ── 2. Menú principal ────────────────────────────────────────────────────────
def menu(c):
    cerrar_todo(c)
    a = c.app
    foto(c, a, "u_menu", [
        (buscar(c, a, "Menú Principal"), 1, "l"),
        (buscar(c, a, "Admin", "TButton"), 2, "b"),
        (buscar(c, a, "Manual", "TButton"), 3, "b"),
        (buscar(c, a, "PEDIDOS WEB"), 4, "tl"),
        (buscar(c, a, "Agenda", "TButton"), 5, "l"),
        (buscar(c, a, "PEDIDOS 2026"), 6, "tl"),
        (buscar(c, a, "v4."), 7, "t"),
    ])


def submenu(c):
    guardar_ventanas()
    b = buscar(c, c.app, "HOTELES")
    celda = b.master if b is not None else None
    bot = [h for h in celda.winfo_children() if hasattr(h, "invoke")] if celda is not None else []
    (bot[0].invoke() if bot else b.event_generate("<Button-1>"))


def submenu_ver(c):
    n = nuevas(c, ESTADO["antes"])
    foto(c, n[-1] if n else None, "u_submenu")
    for v in n:
        c.cerrar(v)


# ── 3. Agenda ────────────────────────────────────────────────────────────────
def agenda(c):
    cerrar_todo(c)
    c.g["abrir_agenda"]()


def agenda_ver(c):
    v = c.ventana("Agenda")
    foto(c, v, "u_agenda", [(buscar(c, v, "✏", n=1), 1, "l"), (buscar(c, v, "🗑", n=1), 2, "r"),
                             (buscar(c, v, "▶", "TButton"), 3, "t"), (buscar(c, v, "DESACTIVADO"), 4, "t"),
                             (buscar(c, v, "Semanal"), 5, "l"), (buscar(c, v, "Añadir"), 6, "r")])
    c.pulsar(v, "Añadir")


def aviso_nuevo(c):
    v = c.ventana("Nuevo Aviso")
    e = c.entradas(v)   # título, fecha, horas, minutos, mensaje, antelación
    c.escribir(e[0], "Enviar el resumen de pedidos a Dirección")
    c.escribir(e[1], (datetime.now() + timedelta(days=3)).strftime("%d-%m-%Y"))
    e[2].set("13"); e[3].set("00")
    c.escribir(e[4], "Adjuntar el Excel de faltantes")
    foto(c, v, "u_aviso_nuevo", [(e[0], 1, "ir"), (caja_de(c, v, [w for w in c.widgets(v) if w.winfo_class() == "TRadiobutton"]), 2, "ir"),
                                  (e[1], 3, "ir"), (buscar(c, v, "📅"), 4, "r"), (caja_de(c, v, [e[2], e[3]]), 5, "tr"),
                                  (e[4], 6, "ir"), (caja_de(c, v, e[5:8]), 7, "r"), (buscar(c, v, "Guardar"), 8, "tr")])
    guardar_ventanas()
    c.pulsar(v, "📅")


def selector_fecha(c):
    p = c.ventana("Elegir fecha")
    hoy = [w for w in c.widgets(p) if w.winfo_class() == "TButton" and c.texto(w).strip() == str(datetime.now().day)] if p else []
    foto(c, p, "u_selector_fecha", [(buscar(c, p, "◀"), 1, "r"), (buscar(c, p, "▶"), 2, "l"), (hoy[0] if hoy else None, 3, "tr"),
                                     (buscar(c, p, "Hoy", "TButton"), 4, "r")] if p else [])
    if p:
        c.cerrar(p)
    c.cerrar(c.ventana("Nuevo Aviso"))


# ── 4. Calendario ────────────────────────────────────────────────────────────
def calendario(c):
    cerrar_todo(c)
    c.g["abrir_calendario"]()


def calendario_ver(c):
    v = c.ventana("Calendario")
    hoy = [w for w in c.widgets(v) if w.winfo_class() == "TLabel" and c.texto(w).strip() == str(datetime.now().day) and w.winfo_ismapped()]
    foto(c, v, "u_calendario_mes", [(buscar(c, v, "◀"), 1, "b"), (buscar(c, v, "Mes", "TRadiobutton"), 2, "b"),
                                     (buscar(c, v, "Chat", "TButton"), 3, "b"), (buscar(c, v, "Festivos", "TButton"), 4, "b"),
                                     (buscar(c, v, "Vacaciones", "TButton"), 5, "b"), (buscar(c, v, "Aviso único"), 6, "l"),
                                     (hoy[0].master if hoy else None, 7, "ir"), (buscar(c, v, "Agenda del Día"), 8, "t"),
                                     (buscar(c, v, "Agenda Mensual"), 9, "t")])
    c.pulsar(v, "Semana")


def calendario_semana(c):
    foto(c, c.ventana("Calendario"), "u_calendario_semana")
    c.pulsar(c.ventana("Calendario"), "Mes")


def calendario_dia(c):
    v = c.ventana("Calendario")
    # Un día con vacaciones y un aviso (el de «Asuntos propios» del perfil de ejemplo), si cae en este mes
    dia = datetime.now() + timedelta(days=10)
    hoy = str(dia.day if dia.month == datetime.now().month else datetime.now().day)
    etiqueta = [w for w in c.widgets(v) if c.texto(w).strip() == hoy and w.winfo_ismapped()]
    guardar_ventanas()
    if etiqueta:
        etiqueta[0].event_generate("<Button-1>")


def calendario_dia_ver(c):
    n = nuevas(c, ESTADO["antes"])
    foto(c, n[-1] if n else None, "u_detalle_dia")
    for v in n:
        c.cerrar(v)
    guardar_ventanas()
    c.pulsar(c.ventana("Calendario"), "Vacaciones")


def vacaciones_ver(c):
    n = nuevas(c, ESTADO["antes"])
    v = n[-1] if n else None
    foto(c, v, "u_vacaciones", [(buscar(c, v, "✏"), 1, "t"), (buscar(c, v, "🗑"), 2, "t"),
                                 (buscar(c, v, "Nuevo Periodo"), 3, "r")] if v else [])
    for v in n:
        c.cerrar(v)
    guardar_ventanas()
    c.pulsar(c.ventana("Calendario"), "Festivos")


def festivos_ver(c):
    n = nuevas(c, ESTADO["antes"])
    v = n[-1] if n else None
    foto(c, v, "u_festivos", [(buscar(c, v, "Nuevo Festivo"), 1, "r")] if v else [])
    for v in n:
        c.cerrar(v)


# ── 5. Avisos emergentes ─────────────────────────────────────────────────────
def popup(aviso, clave=None):
    def f(c):
        cerrar_todo(c)
        guardar_ventanas()
        c.g["mostrar_alerta"](aviso, clave)
    return f


def popup_ver(nombre, marcas=()):
    def f(c):
        n = nuevas(c, ESTADO["antes"])
        v = n[-1] if n else None
        foto(c, v, nombre, [(buscar(c, v, t), i, lado) for t, i, lado in marcas] if v else [])
        for v in n:
            for t in ("Entendido", "Cerrar", "Aceptar"):
                b = c.boton(v, t)
                if b:
                    b.invoke(); break
            else:
                c.cerrar(v)
    return f


AVISO_AGENDA = {"titulo": "Reunión semanal de compras", "fecha": datetime.now().strftime("%Y-%m-%d"), "hora": "10:00",
                "mensaje": "Sala de reuniones 2", "repeticion": "semanal", "activo": True,
                "antelacion": {"dias": 0, "horas": 0, "minutos": 15}}


def popup_vacaciones(c):
    vac = c.g["agenda_data"]["vacaciones"][0]
    i, f = (datetime.strptime(vac[k], "%Y-%m-%d").strftime("%d-%m-%Y") for k in ("fecha_inicio", "fecha_fin"))
    popup({"titulo": f"🏖 Vacaciones próximas: {vac['titulo']}", "mensaje": f"Inicio: {i} → {f}", "antelacion": vac["antelacion"],
           "_tipo_popup": "vacaciones", "_permite_correo": True, "_vac_ref": vac})(c)


def popup_vacaciones_ver(c):
    n = nuevas(c, ESTADO["antes"])
    v = n[-1] if n else None
    ESTADO["popup"] = v
    foto(c, v, "u_popup_vacaciones", [(buscar(c, v, "Enviar correo"), 1, "b"), (buscar(c, v, "Entendido"), 2, "b")] if v else [])
    guardar_ventanas()
    b = buscar(c, v, "Enviar correo") if v else None
    if b:
        b.invoke()


def correo_ver(c):
    n = nuevas(c, ESTADO["antes"])
    v = n[-1] if n else None
    if v:   # con la letra de Linux los botones no caben en el ancho pensado para Segoe UI
        v.geometry(f"{v.winfo_width() + 70}x{v.winfo_height()}"); c.app.update()
    foto(c, v, "u_correo", [(de_clase(c, v, "TEntry"), 1, "ir"), (de_clase(c, v, "Text"), 2, "ir"),
                            (buscar(c, v, "Abrir en cliente"), 3, "t"), (buscar(c, v, "Copiar"), 4, "t")] if v else [])
    for v in n + [ESTADO.get("popup")]:
        if v is not None and v.winfo_exists():
            b = c.boton(v, "Entendido")
            b.invoke() if b else c.cerrar(v)


def aviso_pedidos(c):
    cerrar_todo(c)
    guardar_ventanas()
    br = sys.modules["pedidos_agenda_bridge"]
    av = br._popup_desde_push({"titulo": "🔔 Cambio de estado · Pedido Nº1024", "nivel": "normal", "pedido_id": 1,
                               "mensaje": "Hotel: PR — HOTEL DEMO\nPedido: Nº1024 · Suministros Atlántico S.L.\n"
                                          "✅ El pedido ha pasado a ENVIADO AL PROVEEDOR."})
    c.g["mostrar_alerta"](av)


# ── 6. Chat ──────────────────────────────────────────────────────────────────
def chat(c):
    cerrar_todo(c)
    guardar_ventanas()
    c.pulsar(c.app, "Chat")


def chat_privado(c):
    v = [w for w in nuevas(c, ESTADO["antes"]) if any(x.winfo_class() == "Listbox" for x in c.widgets(w))]
    ESTADO["chat"] = v[-1] if v else None
    if not v:
        return
    lb = de_clase(c, v[-1], "Listbox")
    lb.selection_set(1); lb.event_generate("<<ListboxSelect>>")


def chat_ver(c):
    v = ESTADO.get("chat")
    foto(c, v, "u_chat", [(buscar(c, v, "Conectado"), 1, "r"), (de_clase(c, v, "Listbox"), 2, "ir"),
                          (buscar(c, v, "Nueva conversación"), 3, "t"), (buscar(c, v, "Limpiar"), 4, "l"),
                          (buscar(c, v, "Oferta_", n=0) or de_clase(c, v, "Canvas"), 5, "l"),
                          (de_clase(c, v, "TEntry"), 6, "t"), (boton_emoticonos(c, v), 7, "t"), (buscar(c, v, "📎"), 8, "t"),
                          (buscar(c, v, "Enviar"), 9, "t")])
    guardar_ventanas()
    boton_emoticonos(c, v).invoke()


def boton_emoticonos(c, v):
    """El botón 😊 (desde la v4.18.26 es una imagen en color, sin texto)."""
    return next((w for w in c.widgets(v) if w.winfo_class() == "TButton" and str(w.cget("image"))), None) or buscar(c, v, "😊")


def chat_emoticonos(c):
    n = nuevas(c, ESTADO["antes"])
    p = n[-1] if n else None
    foto(c, p, "u_chat_emoticonos", [(next((w for w in c.widgets(p) if getattr(w, "emoticono", None) == "👍"), None), 1, "l"), (buscar(c, p, "Respuestas rápidas"), 2, "r")] if p else [], barra=False)
    if p:
        c.cerrar(p)
    v = ESTADO.get("chat")
    guardar_ventanas()
    c.pulsar(v, "Chat en el móvil")


def chat_movil_ver(c):
    n = nuevas(c, ESTADO["antes"])
    m = n[-1] if n else None
    qr = next((w for w in c.widgets(m) if w.winfo_class() == "Label" and str(w.cget("image"))), None) if m else None
    foto(c, m, "u_chat_movil", [(qr, 1, "tl"), (caja_de(c, m, [w for w in c.widgets(m) if c.texto(w)[:3] in ("1. ", "2. ", "3. ", "4. ")]), 2, "tr"),
                                (buscar(c, m, "github.com"), 3, "r"), (buscar(c, m, "Actualizaciones"), 4, "l")] if m else [])
    if m:
        c.cerrar(m)
    v = ESTADO.get("chat")
    guardar_ventanas()
    c.pulsar(v, "Nueva conversación")


def chat_nueva_ver(c):
    v = c.ventana("Nueva conversación")
    lb = de_clase(c, v, "Listbox") if v else None
    if lb is not None:
        lb.selection_set(0); lb.event_generate("<<ListboxSelect>>")
    foto(c, v, "u_chat_nueva", [(lb, 1, "ir"), (buscar(c, v, "Abrir chat"), 2, "l")] if v else [])
    c.cerrar(v)
    c.cerrar(ESTADO.get("chat"))


def burbuja(c):
    cerrar_todo(c)
    guardar_ventanas()
    cli = c.g["get_chat_client"]()
    cli.eventos.put({"tipo": "nuevo_mensaje", "mensaje": {
        "id": 99, "remitente": "economato.demo", "canal_id": "dm:compras.demo:economato.demo",
        "contenido": "¿Me confirmas si mañana llega el pedido de menaje?", "creado_en": datetime.utcnow().isoformat() + "Z"}})


def burbuja_ver(c):
    n = nuevas(c, ESTADO["antes"])
    foto(c, n[-1] if n else None, "u_chat_burbuja", barra=False)
    for v in n:
        c.cerrar(v)


# ── 7. Actualización disponible (GitHub simulado) ───────────────────────────
def actualizacion(c):
    import json, urllib.request
    um = sys.modules["services.update_service"]
    falso = {"tag_name": "v4.18.26", "name": "Organizador Princess v4.18.26",
             "body": "# ✨ Organizador Princess v4.18.26\n\n## 🛠 Mejoras\n\n- Mejoras en la agenda y el calendario.\n- Correcciones menores.",
             "assets": [{"name": "OrganizadorPrincess_Setup_4.18.26.exe", "size": 34_400_000, "browser_download_url": "https://example.invalid/x.exe"},
                        {"name": "OrganizadorPrincess_Setup_4.18.26.exe.sha256", "size": 90, "browser_download_url": "https://example.invalid/x.sha256"}]}

    class R(io.BytesIO):
        status = 200
        headers = {"Content-Length": "1"}
        def __enter__(self): return self
        def __exit__(self, *a): return False
    urllib.request.urlopen = lambda req, *a, **k: R(json.dumps(falso).encode())
    cerrar_todo(c)
    guardar_ventanas()
    um._lanzar_check_update(c.app)


def actualizacion_ver(c):
    n = nuevas(c, ESTADO["antes"])
    v = n[-1] if n else None
    foto(c, v, "u_actualizacion", [(de_clase(c, v, "Text"), 1, "ir"), (buscar(c, v, "Actualizar ahora"), 2, "t"),
                                    (buscar(c, v, "Recordar"), 3, "t")] if v else [])
    for v in n:
        c.cerrar(v)


# ── 8. Administración ────────────────────────────────────────────────────────
def admin(c):
    cerrar_todo(c)
    c.g["abrir_admin"]()


def admin_login(c):
    v = c.ventana("Acceso Admin")
    if not v:
        return
    e = [w for w in c.entradas(v) if w.cget("show")][0]
    c.escribir(e, "demo")
    foto(c, v, "a_login", [(buscar(c, v, "compras.demo"), 1, "r"), (e, 2, "ir"), (buscar(c, v, "Crear acceso"), 3, "r"),
                           (buscar(c, v, "Entrar"), 4, "tr")])
    c.pulsar(v, "Entrar")


def admin_login_sin_foto(c):
    v = c.ventana("Acceso Admin")
    if v:
        e = [w for w in c.entradas(v) if w.cget("show")][0]
        c.escribir(e, "demo"); c.pulsar(v, "Entrar")


def admin_panel(c):
    v = c.ventana("Accesos y Opciones")
    foto(c, v, "a_panel", [(buscar(c, v, "Vista", "TButton"), 1, "b"), (buscar(c, v, "Mi Usuario", "TButton"), 2, "b"),
                           (buscar(c, v, "Limpiar todo"), 3, "b"), (buscar(c, v, "Accesos Rápidos"), 4, "r"),
                           (buscar(c, v, "Editar", "TButton"), 5, "l"), (buscar(c, v, "Opciones del Menú"), 6, "r"),
                           (buscar(c, v, "07 ·"), 7, "l"), (buscar(c, v, "Exportar", "TButton"), 8, "t"),
                           (buscar(c, v, "Exportar", "TButton", 1), 9, "t")])


def admin_editar(c):
    p = c.ventana("Accesos y Opciones")
    bs = [w for w in c.widgets(p) if hasattr(w, "invoke") and "editar" in c.texto(w).lower()]
    guardar_ventanas()
    if len(bs) > 12:
        bs[12].invoke()   # botón azul 7 (HOTELES, con submenú)


def admin_editar_ver(c):
    v = c.ventana("Editar acceso") or (nuevas(c, ESTADO["antes"]) or [None])[-1]
    foto(c, v, "a_editar_acceso", [(c.entradas(v)[0], 1, "ir"),
                                   (caja_de(c, v, [w for w in c.widgets(v) if w.winfo_class() == "TRadiobutton"]), 2, "ir"),
                                   (c.entradas(v)[1], 3, "ir"), (buscar(c, v, "Explorar"), 4, "b"),
                                   (buscar(c, v, "Activar submenú"), 5, "r"), (de_clase(c, v, "TSpinbox"), 6, "b"),
                                   (buscar(c, v, "Configurar subopciones"), 7, "r"), (buscar(c, v, "Guardar"), 8, "tr")] if v else [])
    guardar_ventanas()
    b = buscar(c, v, "Configurar subopciones") if v else None
    if b:
        b.invoke()


def admin_subopciones_ver(c):
    n = nuevas(c, ESTADO["antes"])
    v = n[-1] if n else None
    foto(c, v, "a_subopciones", [(buscar(c, v, "Editar", "TButton"), 1, "b")] if v else [])
    for v in n:
        c.cerrar(v)
    c.cerrar(c.ventana("Editar acceso"))


def admin_vista(c):
    p = c.ventana("Accesos y Opciones")

    b = buscar(c, p, "Vista", "TButton")
    if b:
        b.invoke()


def admin_vista_ver(c):
    v = c.ventana("Vista del menú")
    foto(c, v, "a_vista", [(buscar(c, v, "Extendida", "TRadiobutton"), 1, "r"), (buscar(c, v, "Reducida", "TRadiobutton"), 2, "r"),
                           (caja_de(c, v, [w for w in c.widgets(v) if w.winfo_class() == "TCheckbutton"]), 3, "tr"),
                           (buscar(c, v, " de 10"), 4, "t"), (buscar(c, v, "Guardar y aplicar"), 5, "tr")] if v else [])
    c.cerrar(v)


def admin_usuario(c):
    p = c.ventana("Accesos y Opciones")

    b = buscar(c, p, "Mi Usuario", "TButton")
    if b:
        b.invoke()


def admin_usuario_ver(c):
    v = c.ventana("Mi Usuario")
    if v:
        e = c.entradas(v)
        claro = [w for w in e if not w.cget("show")]
        oculto = [w for w in e if w.cget("show")]
        if len(claro) > 1:
            c.escribir(claro[1], "compras.demo")
        for w in oculto:
            c.escribir(w, "ejemplo-de-clave")
        v.geometry(f"{v.winfo_width() + 110}x{v.winfo_height()}"); c.app.update()
        foto(c, v, "a_mi_usuario", [(buscar(c, v, "compras.demo", "TLabel"), 1, "r"), (claro[0], 2, "ir"),
                                    (claro[1] if len(claro) > 1 else None, 3, "ir"), (oculto[0] if oculto else None, 4, "ir"),
                                    (buscar(c, v, "Guardar"), 5, "tr")])
    c.cerrar(v)


def reducida(c):
    cerrar_todo(c)
    cfg = c.g["load_config"]()
    cfg["vista_menu"] = {"modo": "reducida", "reducida_opciones": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}
    c.g["config"].update(cfg)
    c.g["ctx"].aplicar_vista()


def reducida_ver(c):
    foto(c, c.app, "u_vista_reducida")


def final(c):
    log(f"web: {WEB}; abiertos: {ABIERTOS}")


PASOS = [
    ("arranque", arranque, 4000), ("saludo", saludo, 1500), ("menú", menu, 800),
    ("submenú", submenu, 1500), ("submenú ver", submenu_ver, 800),
    ("agenda", agenda, 2000), ("agenda ver", agenda_ver, 1500), ("aviso nuevo", aviso_nuevo, 1500), ("selector de fecha", selector_fecha, 800),
    ("calendario", calendario, 2500), ("calendario ver", calendario_ver, 2000), ("semana", calendario_semana, 2000),
    ("día", calendario_dia, 2000), ("día ver", calendario_dia_ver, 2000), ("vacaciones", vacaciones_ver, 2000), ("festivos", festivos_ver, 1500),
    ("popup agenda", popup(AVISO_AGENDA, "HOY:demo"), 2500), ("popup agenda ver", popup_ver("u_popup_aviso", [("Silenciar", 1, "b"), ("Desactivar", 2, "tr"), ("Entendido", 3, "l")]), 1500),
    ("popup vacaciones", popup_vacaciones, 2500), ("popup vacaciones ver", popup_vacaciones_ver, 2500), ("correo ver", correo_ver, 1000),
    ("popup pedidos", aviso_pedidos, 2500), ("popup pedidos ver", popup_ver("u_popup_pedidos"), 1500),
    ("chat", chat, 2500), ("chat privado", chat_privado, 2500), ("chat ver", chat_ver, 1500), ("chat emoticonos", chat_emoticonos, 2000), ("chat móvil", chat_movil_ver, 2000), ("chat nueva", chat_nueva_ver, 1500),
    ("burbuja", burbuja, 2500), ("burbuja ver", burbuja_ver, 1000),
    ("actualización", actualizacion, 5000), ("actualización ver", actualizacion_ver, 1000),
    ("admin", admin, 2500), ("admin login", admin_login, 3000), ("panel", admin_panel, 500),
    ("editar", admin_editar, 2000), ("editar ver", admin_editar_ver, 2000), ("subopciones", admin_subopciones_ver, 1000),
    ("admin otra vez", admin, 2500), ("admin login", admin_login_sin_foto, 3000), ("vista", admin_vista, 2000), ("vista ver", admin_vista_ver, 1000),
    ("admin otra vez", admin, 2500), ("admin login", admin_login_sin_foto, 3000), ("mi usuario", admin_usuario, 2000), ("mi usuario ver", admin_usuario_ver, 1000),
    ("reducida", reducida, 2500), ("reducida ver", reducida_ver, 500),
    ("final", final, 300),
]
