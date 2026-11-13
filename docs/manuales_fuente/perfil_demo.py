"""Perfil de demostración para las capturas de los manuales (datos inventados).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: APPDATA=<carpeta temporal> USERNAME=compras.demo python perfil_demo.py <raíz del Organizador>
Escribe config.json, agenda.json y el nombre «Ana Demo» en una carpeta de datos de usar y tirar:
nunca en la carpeta real de un usuario (capturas.sh crea una nueva cada vez).
"""
import os
import sys
from datetime import date, timedelta

RAIZ = sys.argv[1]
assert os.environ.get("APPDATA", "").startswith(("/tmp", os.environ.get("TMPDIR", "/tmp"))), "APPDATA debe ser una carpeta temporal"
sys.path.insert(0, os.path.join(RAIZ, "app"))
from db.sqlite import save_config, save_agenda, update_nombre_usuario_db  # noqa: E402

HOY = date.today()


def acc(nombre, tipo, ruta, sub=0):
    d = {"nombre": nombre, "tipo": tipo, "ruta": ruta, "submenu": {"enabled": bool(sub), "count": sub or 5}}
    return d


cfg = {"_saludo_ultimo_dia": "", "vista_menu": {"modo": "extendida", "reducida_opciones": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]}}
accesos = [("PEDIDOS WEB", "web", "https://proxy.controlpedidosprincess-canarias.workers.dev"),
           ("DALI", "web", "https://catalogo.example.com"),
           ("CORREO", "web", "https://correo.example.com"),
           ("SAP", "ejecutable", r"C:\Programas\SAP\saplogon.exe"),
           ("INTRANET", "web", "https://intranet.example.com"),
           ("TARIFAS", "carpeta", r"\\servidor-demo\compras\Tarifas")]
for i, (n, t, r) in enumerate(accesos, 1):
    cfg[f"acceso_rapido_{i:02d}"] = acc(n, t, r)

opciones = ["PEDIDOS 2026", "PROVEEDORES", "OFERTAS", "FACTURAS", "ALBARANES", "FICHAS TÉCNICAS",
            "HOTELES", "INVENTARIOS", "ECONOMATO", "MENAJE", "LIMPIEZA", "ALIMENTACIÓN",
            "BEBIDAS", "MANTENIMIENTO", "CONTRATOS", "PLANTILLAS", "INFORMES", "FORMACIÓN"]
for i, n in enumerate(opciones, 1):
    cfg[f"opcion_{i:02d}"] = acc(n, "carpeta", rf"\\servidor-demo\compras\{n.title()}", sub=4 if n == "HOTELES" else 0)
for j, isla in enumerate(["TENERIFE", "GRAN CANARIA", "FUERTEVENTURA", "LANZAROTE"], 1):
    cfg[f"opcion_07_sub_{j:02d}"] = {"nombre": isla, "tipo": "carpeta", "ruta": rf"\\servidor-demo\compras\Hoteles\{isla.title()}"}
save_config(cfg)


def iso(d):
    return d.strftime("%Y-%m-%d")


lunes = HOY - timedelta(days=HOY.weekday())
agenda = {
    "avisos": [
        {"titulo": "Revisar pedidos pendientes de firma", "fecha": iso(lunes + timedelta(days=4)), "hora": "09:00",
         "mensaje": "Mirar en Control de Pedidos los que llevan más de 2 días", "repeticion": "semanal", "activo": True,
         "antelacion": {"dias": 0, "horas": 0, "minutos": 0}},
        {"titulo": "Reunión semanal de compras", "fecha": iso(lunes + timedelta(days=1)), "hora": "10:00", "mensaje": "Sala de reuniones 2",
         "repeticion": "semanal", "activo": True, "antelacion": {"dias": 0, "horas": 0, "minutos": 15}},
        {"titulo": "Llamar a Suministros Atlántico", "fecha": iso(HOY + timedelta(days=2)), "hora": "11:30",
         "mensaje": "Confirmar la fecha de entrega del menaje", "repeticion": "ninguna", "activo": True,
         "antelacion": {"dias": 0, "horas": 1, "minutos": 0}},
        {"titulo": "Cierre de mes: listados DALI / SAP", "fecha": iso(HOY.replace(day=27)), "hora": "12:00",
         "mensaje": "Cargar los tres listados", "repeticion": "mensual", "activo": True,
         "antelacion": {"dias": 1, "horas": 0, "minutos": 0}},
        {"titulo": "Inventario del economato", "fecha": iso(HOY + timedelta(days=16)), "hora": "08:30",
         "mensaje": "", "repeticion": "ninguna", "activo": False, "antelacion": {"dias": 0, "horas": 0, "minutos": 0}},
    ],
    "vacaciones": [
        {"titulo": "Asuntos propios", "fecha_inicio": iso(HOY + timedelta(days=10)), "fecha_fin": iso(HOY + timedelta(days=11)),
         "antelacion": {"dias": 2, "horas": 0, "minutos": 0}},
        {"titulo": "Vacaciones de Navidad", "fecha_inicio": f"{HOY.year}-12-24", "fecha_fin": f"{HOY.year}-12-31",
         "antelacion": {"dias": 3, "horas": 0, "minutos": 0}},
    ],
    "festivos": [
        {"titulo": "Día festivo local (ejemplo)", "fecha": iso(HOY + timedelta(days=15)), "antelacion": {"dias": 1, "horas": 0, "minutos": 0}},
        {"titulo": "Inmaculada Concepción", "fecha": f"{HOY.year}-12-08", "antelacion": {"dias": 1, "horas": 0, "minutos": 0}},
        {"titulo": "Navidad", "fecha": f"{HOY.year}-12-25", "antelacion": {"dias": 0, "horas": 0, "minutos": 0}},
        {"titulo": "Año Nuevo", "fecha": f"{HOY.year + 1}-01-01", "antelacion": {"dias": 0, "horas": 0, "minutos": 0}},
        {"titulo": "Día de Reyes", "fecha": f"{HOY.year + 1}-01-06", "antelacion": {"dias": 0, "horas": 0, "minutos": 0}},
    ],
}
save_agenda(agenda)
# (v4.18.56) Con una versión anterior guardada sale «Nueva versión detectada» (sin ella, la primera vez no pregunta)
import json  # noqa: E402
from db.sqlite import VERSION_FILE  # noqa: E402
with open(VERSION_FILE, "w", encoding="utf-8") as f:
    json.dump({"version": "v4.18.60"}, f)
update_nombre_usuario_db(os.environ.get("USERNAME", "compras.demo").lower(), "Ana Demo")
print("perfil de demostración listo en", os.environ["APPDATA"])
