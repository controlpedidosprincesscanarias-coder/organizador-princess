"""Simulación para las capturas de los manuales: sin red y con un chat de ejemplo.

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Python carga este archivo solo al arrancar si su carpeta está en PYTHONPATH (lo hace capturas.sh).
- Corta toda conexión de red: ni Control de Pedidos, ni el chat, ni GitHub reciben nada.
- Sustituye el cliente del chat por uno con conversaciones inventadas.
- Acepta la contraseña «demo» en Administración (sin consultar Control de Pedidos).
Todos los nombres son de ejemplo, como en los manuales de Control de Pedidos.
"""
import os
import socket
import sys
from datetime import datetime, timedelta, timezone

# ── Sin red (los sockets locales de X11 los abre Tk en C, no pasan por aquí) ──
_connect_original = socket.socket.connect


def _sin_red(self, direccion, *a, **k):
    if self.family == getattr(socket, "AF_UNIX", None):
        return _connect_original(self, direccion, *a, **k)
    raise OSError("red desactivada en las capturas del manual")


socket.socket.connect = _sin_red
socket.socket.connect_ex = lambda self, direccion: 111

RAIZ = os.environ.get("ORG_RAIZ")
if RAIZ:
    sys.path.insert(0, os.path.join(RAIZ, "app"))

    USUARIOS = [
        {"username": "compras.demo", "rol": "COMPRAS", "nombre": "Ana Demo"},
        {"username": "compras2.demo", "rol": "COMPRAS", "nombre": "Compradora Demo 2"},
        {"username": "economato.demo", "rol": "HOTEL", "nombre": "Economato Demo"},
        {"username": "hotel.demo", "rol": "HOTEL", "nombre": "Recepción Mercancía Demo"},
        {"username": "admin.demo", "rol": "ADMIN", "nombre": "Administración Demo"},
    ]
    YO = "compras.demo"
    DM = "dm:compras.demo:compras2.demo"

    def _ts(horas_atras, minutos=0):
        return (datetime.now(timezone.utc) - timedelta(hours=horas_atras, minutes=minutos)).isoformat().replace("+00:00", "Z")

    MENSAJES = {
        "general": [
            {"id": 1, "remitente": "admin.demo", "contenido": "Buenos días. Hoy a las 12:00 se cargan los listados DALI / SAP de la semana.", "creado_en": _ts(4, 10)},
            {"id": 2, "remitente": "economato.demo", "contenido": "Recibido, gracias.", "creado_en": _ts(4, 2)},
            {"id": 3, "remitente": YO, "contenido": "Perfecto, lo reviso después.", "creado_en": _ts(3, 50)},
        ],
        DM: [
            {"id": 10, "remitente": "compras2.demo", "contenido": "Hola Ana, ¿te llegó la oferta de Suministros Atlántico?", "creado_en": _ts(1, 25)},
            {"id": 11, "remitente": YO, "contenido": "Sí, te la paso ahora.", "creado_en": _ts(1, 20)},
            {"id": 12, "remitente": YO, "contenido": "", "tipo": "archivo", "creado_en": _ts(1, 19),
             "adjunto": {"nombre_archivo": "Oferta_Suministros_Atlantico.pdf", "url": "/demo/oferta.pdf"}},
            {"id": 13, "remitente": "compras2.demo", "contenido": "¡Gracias! La subo al pedido y la mando a firmar.", "creado_en": _ts(0, 40)},
        ],
        "dm:compras.demo:economato.demo": [
            {"id": 20, "remitente": "economato.demo", "contenido": "¿Sabes si el pedido de menaje llega esta semana?", "creado_en": _ts(26)},
            {"id": 21, "remitente": YO, "contenido": "El proveedor lo confirma para el jueves.", "creado_en": _ts(25, 30)},
        ],
        "grp:demo": [
            {"id": 30, "remitente": "compras2.demo", "contenido": "Recordad revisar los pedidos pendientes de firma antes del viernes.", "creado_en": _ts(50)},
        ],
    }
    CANALES = [
        {"canal_id": "general", "tipo": "general", "no_leidos": 0},
        {"canal_id": DM, "tipo": "privado", "otro_usuario": "compras2.demo", "no_leidos": 2},
        {"canal_id": "dm:compras.demo:economato.demo", "tipo": "privado", "otro_usuario": "economato.demo", "no_leidos": 0},
        {"canal_id": "grp:demo", "tipo": "grupo", "nombre": "Compras Canarias", "no_leidos": 0},
    ]

    try:
        import services.chat_client as _cc

        def _login(self, username_win=None):
            self.username, self.nombre, self.rol, self._logged_in = YO, "Ana Demo", "compras", True
            return True

        def _conectar(self):
            self._demo_conectado = True
            self.eventos.put({"tipo": _cc.EVT_CONECTADO})

        def _mensajes(self, canal_id=None, destinatario=None):
            if destinatario:
                canal_id = next((c["canal_id"] for c in CANALES if c.get("otro_usuario") == destinatario), "dm:nuevo")
            return {"canal_id": canal_id or "general", "mensajes": [dict(m, canal_id=canal_id) for m in MENSAJES.get(canal_id or "general", [])]}

        _cc.ChatClient.login = _login
        _cc.ChatClient.conectar = _conectar
        _cc.ChatClient.conectado = property(lambda self: getattr(self, "_demo_conectado", False))
        _cc.ChatClient.desconectar = lambda self: None
        _cc.ChatClient.obtener_canales = lambda self: [dict(c) for c in CANALES]
        _cc.ChatClient.obtener_usuarios = lambda self: [u for u in USUARIOS if u["username"] != YO]
        _cc.ChatClient.obtener_mensajes = _mensajes
        _cc.ChatClient.unirse_canal = lambda self, canal_id: None
        _cc.ChatClient.enviar_mensaje = lambda self, contenido, canal_id=None, destinatario=None: None
        _cc.ChatClient.enviar_archivo = lambda self, ruta, canal_id=None, destinatario=None: {"ok": True}
        _cc.ChatClient.crear_grupo = lambda self, nombre, usuarios: {"canal_id": "grp:demo2", "nombre": nombre}

        _nombres_originales = _cc.ChatClient.__init__

        def _init(self, *a, **k):
            _nombres_originales(self, *a, **k)
            self._mapa_nombres.update({u["username"]: u["nombre"] for u in USUARIOS})
        _cc.ChatClient.__init__ = _init

        import services.admin_auth as _aa
        _aa.existe_en_plataforma = lambda username_win: True
        _aa.validar_en_plataforma = lambda username_win, password: (
            {"ok": True, "nombre": "Ana Demo", "rol": "compras", "error": ""} if password == "demo"
            else {"ok": False, "nombre": "", "rol": "", "error": "Contraseña incorrecta"})
    except Exception as exc:  # noqa: BLE001
        print(f"[simulación] no se pudo preparar el chat de ejemplo: {exc}", file=sys.stderr)
