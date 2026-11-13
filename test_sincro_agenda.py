"""Agenda sincronizada con el usuario de Control de Pedidos (v4.18.66).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_sincro_agenda.py  (en cualquier sistema; no se conecta a ningún servidor).

Simula dos PC con el mismo usuario y un servidor en memoria con las mismas reglas que Control de Pedidos
v12.34.36 (GET/POST /api/bridge/agenda: gana el cambio más reciente, un empate no sobrescribe, nunca una hora
futura). Cada vuelta usa el código real del bridge (_sincronizar_agenda) y de services/sincro_agenda.py:
primera vez con agendas en los dos PC (fusión sin duplicados), cambios, borrados, conflictos, sin red,
cambio de usuario, «Importar agenda», los avisos de Control de Pedidos (no se suben) y el guardado real.
"""
import copy
import json
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from unittest import mock

RAIZ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(RAIZ, "app"))
sys.path.insert(0, RAIZ)

try:
    import tkinter  # noqa: F401
except ImportError:   # sin Tkinter (Linux de pruebas): se simula, como en test_chat_fase1.py
    import importlib.abc
    import importlib.machinery

    class _Simulado(importlib.abc.MetaPathFinder, importlib.abc.Loader):
        def find_spec(self, name, path, target=None):
            if name.split(".")[0] in ("tkinter", "_tkinter", "ttkbootstrap"):
                return importlib.machinery.ModuleSpec(name, self, is_package=True)
        def create_module(self, spec):
            m = mock.MagicMock()
            m.__path__, m.__name__, m.__spec__ = [], spec.name, spec
            return m
        def exec_module(self, m):
            pass
    sys.meta_path.insert(0, _Simulado())

import urllib.error  # noqa: E402

import pedidos_agenda_bridge as bridge  # noqa: E402
from services import sincro_agenda as sincro  # noqa: E402

fallos = []


def ok(nombre, cond, det=""):
    print(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
    if not cond:
        fallos.append(nombre)


# ── Servidor en memoria (mismas reglas que servicios/agenda_organizador.py de Control de Pedidos) ──────────
class Servidor:
    def __init__(self):
        self.filas = {}      # (usuario, sid) → dict
        self.seq = 0
        self.caido = False
        self.por_pagina = 1000

    def _dt(self, v):
        return sincro._dt(v)

    def get(self, usuario, desde):
        if self.caido:
            raise urllib.error.URLError("sin red")
        filas = sorted((f for (u, _s), f in self.filas.items() if u == usuario and f["version"] > desde),
                       key=lambda f: f["version"])
        mas = len(filas) > self.por_pagina
        filas = filas[:self.por_pagina]
        return {"elementos": copy.deepcopy(filas), "version": filas[-1]["version"] if filas else desde, "mas": mas}

    def post(self, usuario, elementos):
        if self.caido:
            raise urllib.error.URLError("sin red")
        aceptados, rechazados = [], []
        ahora = datetime.now(timezone.utc)
        for e in elementos:
            cuando = min(self._dt(e["cambiado_en"]), ahora)
            clave = (usuario, e["sid"])
            actual = self.filas.get(clave)
            if actual and not (self._dt(actual["cambiado_en"]) < cuando):
                rechazados.append(copy.deepcopy(actual))
                continue
            self.seq += 1
            self.filas[clave] = {"sid": e["sid"], "tipo": e["tipo"], "borrado": bool(e.get("borrado")),
                                 "datos": {} if e.get("borrado") else copy.deepcopy(e["datos"]),
                                 "cambiado_en": cuando.isoformat(), "version": self.seq}
            aceptados.append({"sid": e["sid"], "version": self.seq})
        return {"aceptados": aceptados, "rechazados": rechazados}

    def vivos(self, usuario):
        return {s: f for (u, s), f in self.filas.items() if u == usuario and not f["borrado"]}


class SesionFalsa:
    def __init__(self, servidor, usuario):
        self.servidor, self.username, self._logged_in = servidor, usuario, True

    def get_agenda(self, desde=0):
        return self.servidor.get(self.username, desde)

    def post_agenda(self, elementos):
        return self.servidor.post(self.username, json.loads(json.dumps(elementos)))


def guardar(data):
    """Lo mismo que hace db.sqlite.save_agenda, sin escribir archivo."""
    with sincro.CERROJO:
        sincro.marcar_cambios(data)


def sincronizar(pc, servidor, usuario="compras prueba"):
    with mock.patch.object(bridge, "_session", SesionFalsa(servidor, usuario)), \
         mock.patch.object(bridge, "_app_root", None):
        bridge._sincronizar_agenda(pc, guardar)


def visibles(pc, lista):
    return sorted(json.dumps(sincro.contenido(i), sort_keys=True, ensure_ascii=False)
                  for i in pc.get(lista, []) if sincro.sincronizable(i))


def iguales(a, b):
    return all(visibles(a, l) == visibles(b, l) for l in sincro.LISTAS)


def aviso(titulo, hora="09:00"):
    return {"titulo": titulo, "fecha": "2026-11-20", "hora": hora, "mensaje": "", "repeticion": "una_vez",
            "activo": True, "antelacion": {"dias": 0, "horas": 0, "minutos": 0}}


FESTIVO = {"titulo": "Día de Canarias", "fecha": "2027-05-30", "antelacion": {"dias": 1, "horas": 0, "minutos": 0}}
VACACION = {"titulo": "Vacaciones", "fecha_inicio": "2026-12-22", "fecha_fin": "2027-01-02",
            "antelacion": {"dias": 0, "horas": 0, "minutos": 0}}
DE_PEDIDOS = {"titulo": "Pedido #123 en alerta", "fecha": "2026-11-13", "hora": "10:00", "_bridge_gestionado": True}

srv = Servidor()

print("1. Primera vez, con agenda en los dos PC (de antes de esta versión, sin ids):")
pc1 = {"avisos": [aviso("Reunión"), aviso("Inventario", "12:00"), dict(DE_PEDIDOS)], "festivos": [dict(FESTIVO)]}
pc2 = {"festivos": [dict(FESTIVO)], "vacaciones": [dict(VACACION)]}
sincronizar(pc1, srv)
ok("el PC 1 sube sus 3 elementos", len(srv.vivos("compras prueba")) == 3, srv.vivos("compras prueba"))
ok("…pero no el aviso de Control de Pedidos", all(f["datos"].get("titulo") != DE_PEDIDOS["titulo"]
                                                 for f in srv.vivos("compras prueba").values()))
ok("…y no le queda nada pendiente", not sincro.hay_pendientes(pc1), sincro.pendientes(pc1))
ok("el aviso de Control de Pedidos sigue en su agenda, sin id", any(a.get("_bridge_gestionado") and "_sid" not in a
                                                                    for a in pc1["avisos"]))
sincronizar(pc2, srv)
ok("el PC 2 recibe los avisos del PC 1 y sube su vacación", len(srv.vivos("compras prueba")) == 4)
ok("el festivo que estaba en los dos no se duplica", len(pc2["festivos"]) == 1 and len(srv.vivos("compras prueba")) == 4,
   pc2["festivos"])
sincronizar(pc1, srv)
ok("el PC 1 recibe la vacación del PC 2", visibles(pc1, "vacaciones") == visibles(pc2, "vacaciones") != [])
ok("las dos agendas quedan iguales", iguales(pc1, pc2), (pc1, pc2))
ok("con el mismo id en los dos PC", sorted(i["_sid"] for l in sincro.LISTAS for i in pc1.get(l, [])
                                          if sincro.sincronizable(i))
   == sorted(i["_sid"] for l in sincro.LISTAS for i in pc2.get(l, [])))

print("2. Un cambio en un PC llega al otro (y sigue siendo el mismo elemento):")
original = next(a for a in pc2["avisos"] if a["titulo"] == "Reunión")
editado = dict(aviso("Reunión de compras", "09:30"))
sincro.reemplazar(pc2["avisos"], original, editado, 0)
guardar(pc2)
sincronizar(pc2, srv)
sincronizar(pc1, srv)
titulos = [a["titulo"] for a in pc1["avisos"] if sincro.sincronizable(a)]
ok("el PC 1 tiene el aviso cambiado", "Reunión de compras" in titulos and "Reunión" not in titulos, titulos)
ok("con el mismo id de antes", editado["_sid"] == original["_sid"])
for a in pc1["avisos"]:
    if a.get("titulo") == "Inventario":
        a["activo"] = False
guardar(pc1)
sincronizar(pc1, srv)
sincronizar(pc2, srv)
ok("…el aviso desactivado en el PC 1 queda desactivado en el PC 2",
   any(a["titulo"] == "Inventario" and a["activo"] is False for a in pc2["avisos"]))

print("3. Los borrados se propagan:")
fest = pc1["festivos"][0]
ok("quitar() lo borra por su id", sincro.quitar(pc1["festivos"], fest) and pc1["festivos"] == [])
guardar(pc1)
sincronizar(pc1, srv)
sincronizar(pc2, srv)
ok("el PC 2 ya no tiene el festivo", pc2["festivos"] == [], pc2["festivos"])
ok("y en el servidor consta como borrado", srv.filas[("compras prueba", fest["_sid"])]["borrado"] is True)
ok("quitar() de algo que ya no está no borra otra cosa", sincro.quitar(pc2["festivos"], fest) is False)

print("4. Conflicto: los dos PC cambian lo mismo sin conexión, gana el más reciente:")
srv.caido = True
v1 = next(v for v in pc1["vacaciones"])
v2 = next(v for v in pc2["vacaciones"])
sincro.reemplazar(pc1["vacaciones"], v1, dict(VACACION, titulo="Vacaciones (PC 1)"))
guardar(pc1)
time.sleep(0.01)
sincro.reemplazar(pc2["vacaciones"], v2, dict(VACACION, titulo="Vacaciones (PC 2, después)"))
guardar(pc2)
try:
    sincronizar(pc1, srv)
    ok("sin red, la sincronización falla (el bucle lo reintenta)", False)
except urllib.error.URLError:
    ok("sin red, la sincronización falla (el bucle lo reintenta)", True)
ok("…y el cambio sigue en el PC, pendiente de subir", sincro.hay_pendientes(pc1)
   and pc1["vacaciones"][0]["titulo"] == "Vacaciones (PC 1)")
srv.caido = False
sincronizar(pc2, srv)    # el PC 2 sube primero el suyo (más reciente)
sincronizar(pc1, srv)    # el del PC 1 es más antiguo: el servidor lo rechaza y el PC 1 toma el del PC 2
sincronizar(pc2, srv)
ok("los dos se quedan con el cambio más reciente", pc1["vacaciones"][0]["titulo"] == "Vacaciones (PC 2, después)"
   == pc2["vacaciones"][0]["titulo"], (pc1["vacaciones"], pc2["vacaciones"]))
ok("sin nada pendiente", not sincro.hay_pendientes(pc1) and not sincro.hay_pendientes(pc2))

srv.caido = True
v1 = pc1["vacaciones"][0]
sincro.reemplazar(pc2["vacaciones"], pc2["vacaciones"][0], dict(VACACION, titulo="Vacaciones (PC 2, antes)"))
guardar(pc2)
time.sleep(0.01)
sincro.reemplazar(pc1["vacaciones"], v1, dict(VACACION, titulo="Vacaciones (PC 1, después)"))
guardar(pc1)
srv.caido = False
sincronizar(pc2, srv)    # ahora sube primero el más antiguo…
sincronizar(pc1, srv)    # …y el más reciente lo sustituye
sincronizar(pc2, srv)
ok("también si el más reciente llega el último", pc1["vacaciones"][0]["titulo"] == "Vacaciones (PC 1, después)"
   == pc2["vacaciones"][0]["titulo"], (pc1["vacaciones"], pc2["vacaciones"]))

print("5. Borrado en un PC y cambio en otro, sin conexión:")
srv.caido = True
inv1 = next(a for a in pc1["avisos"] if a.get("titulo") == "Inventario")
inv2 = next(a for a in pc2["avisos"] if a.get("titulo") == "Inventario")
sincro.quitar(pc1["avisos"], inv1)
guardar(pc1)
time.sleep(0.01)
sincro.reemplazar(pc2["avisos"], inv2, dict(aviso("Inventario anual", "12:00")))
guardar(pc2)
srv.caido = False
sincronizar(pc1, srv)
sincronizar(pc2, srv)
sincronizar(pc1, srv)
ok("el cambio, más reciente que el borrado, vuelve al PC 1", any(a.get("titulo") == "Inventario anual"
                                                               for a in pc1["avisos"]), pc1["avisos"])
ok("las dos agendas quedan iguales", iguales(pc1, pc2), (pc1, pc2))

print("6. Paginación (la agenda llega en varias páginas):")
pc3 = {}
srv.por_pagina = 1
sincronizar(pc3, srv)
srv.por_pagina = 1000
ok("un PC nuevo recibe la agenda completa", iguales(pc3, pc1), (pc3, pc1))
ok("…sin los borrados", all(i.get("titulo") != FESTIVO["titulo"] for i in pc3.get("festivos", [])))

print("7. Otro usuario en el mismo PC:")
antes = len(srv.vivos("compras prueba"))
filas_antes = {k: dict(v) for k, v in srv.filas.items() if k[0] == "compras prueba"}
pc3["avisos"].append(aviso("Nota sin subir"))
guardar(pc3)
pc3[sincro.CLAVE_ESTADO]["usuario"] = "compras prueba"
nuevo = next(a for a in pc3["avisos"] if a["titulo"] == "Nota sin subir")
for a in pc3["avisos"]:
    if a is not nuevo:
        a.pop("_nuevo", None)
sincronizar(pc3, srv, usuario="admin prueba")
ok("se quita la agenda del anterior (sigue en el servidor)", len(srv.vivos("compras prueba")) == antes
   and [a["titulo"] for a in pc3["avisos"]] == ["Nota sin subir"], pc3["avisos"])
ok("lo que nunca llegó a subirse pasa al nuevo usuario", [f["datos"]["titulo"] for f in srv.vivos("admin prueba").values()]
   == ["Nota sin subir"], srv.vivos("admin prueba"))
ok("y no se toca nada del anterior en el servidor", {k: v for k, v in srv.filas.items() if k[0] == "compras prueba"}
   == filas_antes)

print("8. «Importar agenda» reemplaza también la de los otros PC:")
copia = {"avisos": [aviso("De la copia de seguridad")], "festivos": [dict(FESTIVO)],
         sincro.CLAVE_ESTADO: {"version": 1, "usuario": "otro", "conocidos": {}, "borrados": {}}}
importada = sincro.preparar_importacion(copia, pc1)
pc1.clear()
pc1.update(importada)
guardar(pc1)
ok("se conserva el estado de sincronización de este PC (no el del archivo)",
   pc1[sincro.CLAVE_ESTADO]["usuario"] == "compras prueba")
sincronizar(pc1, srv)
sincronizar(pc2, srv)
ok("el PC 2 queda con lo importado", iguales(pc1, pc2) and [a["titulo"] for a in pc2["avisos"]]
   == ["De la copia de seguridad"], (pc1, pc2))

print("9. Las ventanas: posición por id y refresco de las abiertas:")
lista = [{"_sid": "a" * 32, "titulo": "A"}, {"_sid": "b" * 32, "titulo": "B"}]
b = lista[1]
lista.pop(0)    # llega un borrado de otro PC mientras está abierta la edición de B (pintada en la posición 1)
sincro.reemplazar(lista, b, {"titulo": "B editado"}, 1)
ok("se guarda en su sitio aunque haya cambiado la posición", lista == [{"titulo": "B editado", "_sid": "b" * 32}], lista)
sincro.reemplazar(lista, {"_sid": "c" * 32, "titulo": "C"}, {"titulo": "C editado"}, 0)
ok("si otro PC lo borró mientras se editaba, se añade de nuevo", len(lista) == 2 and lista[1]["_sid"] == "c" * 32, lista)
llamadas = []


class _Ventana:
    def __init__(self, viva): self.viva = viva
    def winfo_exists(self): return self.viva


abierta, cerrada = _Ventana(True), _Ventana(False)
sincro.registrar_refresco(abierta, lambda: llamadas.append("abierta"))
sincro.registrar_refresco(cerrada, lambda: llamadas.append("cerrada"))
sincro.refrescar_ventanas()
ok("se repinta la ventana abierta y se olvida la cerrada", llamadas == ["abierta"] and len(sincro._refrescos) == 1, llamadas)
abierta.viva = False
sincro.refrescar_ventanas()
ok("…y la abierta, cuando se cierra", sincro._refrescos == [])

print("10. El guardado real (db/sqlite.save_agenda) marca los cambios y despierta la sincronización:")
import db.sqlite as sqlite  # noqa: E402
with tempfile.TemporaryDirectory() as tmp:
    ruta = os.path.join(tmp, "agenda.json")
    with mock.patch.object(sqlite, "AGENDA_FILE", ruta):
        sincro.CAMBIO_LOCAL.clear()
        datos = {"avisos": [aviso("Guardado real")]}
        sqlite.save_agenda(datos)
        guardado = json.load(open(ruta, encoding="utf-8"))
        a = guardado["avisos"][0]
        ok("con id, huella y pendiente", a.get("_sid") and a.get("_h") and a.get("_pendiente") is True, a)
        ok("y avisa al hilo de sincronización", sincro.CAMBIO_LOCAL.is_set())
        sincro.CAMBIO_LOCAL.clear()
        a2 = dict(datos["avisos"][0])
        sqlite.save_agenda(datos)
        ok("guardar sin cambios no vuelve a marcar nada", not sincro.CAMBIO_LOCAL.is_set()
           and datos["avisos"][0]["_cambiado"] == a2["_cambiado"])
        datos["avisos"] = []
        sqlite.save_agenda(datos)
        ok("borrar algo deja anotado el borrado", a["_sid"] in datos[sincro.CLAVE_ESTADO]["borrados"]
           and sincro.CAMBIO_LOCAL.is_set())
        ok("y load_agenda lo lee como siempre", sqlite.load_agenda().get("avisos") == [])

print("11. Control de Pedidos sin la ruta (versión anterior): sigue con la copia local, sin errores:")


class _Sesion404(SesionFalsa):
    def get_agenda(self, desde=0):
        raise urllib.error.HTTPError("/api/bridge/agenda", 404, "Not Found", {}, None)


pc4 = {"avisos": [aviso("Local")]}
with mock.patch.object(bridge, "_session", _Sesion404(srv, "compras prueba")), \
     mock.patch.object(bridge, "_app_root", None):
    try:
        bridge._sincronizar_agenda(pc4, guardar)
        ok("lanza el 404 para que el bucle espere una hora", False)
    except urllib.error.HTTPError as exc:
        ok("lanza el 404 para que el bucle espere una hora", exc.code == 404)
ok("la agenda local sigue intacta", [a["titulo"] for a in pc4["avisos"]] == ["Local"])

print("12. Las ventanas que editan conservan el id y se repintan (código):")
for archivo in ("app/ui/agenda.py", "app/ui/vacaciones.py", "app/ui/festivos.py"):
    texto = open(os.path.join(RAIZ, archivo), encoding="utf-8").read()
    ok(f"{archivo}: edita con reemplazar(), borra con quitar() y se registra para repintarse",
       "sincro_agenda.reemplazar(" in texto and "sincro_agenda.quitar(" in texto
       and "sincro_agenda.registrar_refresco(" in texto and "].pop(idx)" not in texto
       and "[idx] = editado" not in texto)
texto = open(os.path.join(RAIZ, "app/ui/calendario.py"), encoding="utf-8").read()
ok("app/ui/calendario.py se repinta al llegar cambios", "sincro_agenda.registrar_refresco(win, renderizar)" in texto)

print()
if fallos:
    print(f"FALLOS ({len(fallos)}): {fallos}")
    sys.exit(1)
print("Todas las comprobaciones de la agenda sincronizada son correctas.")
