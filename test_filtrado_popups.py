"""
Simulación en memoria de la lógica de _filtrar_popups_no_vistos()
(v12.29.46) para validar el algoritmo sin depender de Postgres real.

No es un test de integración del endpoint Flask -- reproduce el mismo
razonamiento (filtrar por vistos, marcar como vistos, purgar
inactivos) sobre estructuras Python equivalentes a las filas de
bridge_popup_visto.
"""

class FakeDB:
    def __init__(self):
        self.visto = set()  # {(usuario, pedido_id, nivel)}

    def leer_vistos(self, usuario):
        return {(pid, nivel) for (u, pid, nivel) in self.visto if u == usuario}

    def marcar_visto(self, usuario, pid, nivel):
        self.visto.add((usuario, pid, nivel))

    def purgar(self, usuario, pedido_ids_activos):
        self.visto = {
            (u, pid, nivel) for (u, pid, nivel) in self.visto
            if not (u == usuario and pid not in pedido_ids_activos)
        }

    def limpiar_usuario(self, usuario):
        self.visto = {t for t in self.visto if t[0] != usuario}


def filtrar_popups_no_vistos(db, usuario, alertas):
    if not alertas:
        db.limpiar_usuario(usuario)
        return []

    pedido_ids_activos = list({a["id"] for a in alertas})
    vistos = db.leer_vistos(usuario)
    nuevas = [a for a in alertas if (a["id"], a["nivel_alerta"]) not in vistos]

    db.purgar(usuario, pedido_ids_activos)
    for a in nuevas:
        db.marcar_visto(usuario, a["id"], a["nivel_alerta"])

    return nuevas


def run():
    db = FakeDB()
    user = "comprador_insire"

    # Ciclo 1: pedido 100 en aviso -> debe entregarse
    r1 = filtrar_popups_no_vistos(db, user, [{"id": 100, "nivel_alerta": "aviso"}])
    assert [a["id"] for a in r1] == [100], r1
    print("OK ciclo1: primera vez se entrega ->", r1)

    # Ciclo 2 (15 min despues, mismo estado, app reiniciada o no): NO debe repetirse
    r2 = filtrar_popups_no_vistos(db, user, [{"id": 100, "nivel_alerta": "aviso"}])
    assert r2 == [], r2
    print("OK ciclo2: no se repite aunque siga activo ->", r2)

    # Ciclo 3: escala a urgente -> SI debe avisar de nuevo (clave distinta)
    r3 = filtrar_popups_no_vistos(db, user, [{"id": 100, "nivel_alerta": "urgente"}])
    assert [a["id"] for a in r3] == [100], r3
    print("OK ciclo3: escalada aviso->urgente reavisa ->", r3)

    # Ciclo 4: sigue urgente -> no se repite
    r4 = filtrar_popups_no_vistos(db, user, [{"id": 100, "nivel_alerta": "urgente"}])
    assert r4 == [], r4
    print("OK ciclo4: urgente ya visto no se repite ->", r4)

    # Ciclo 5: se resuelve (desaparece de alertas) -> se purga su historial
    r5 = filtrar_popups_no_vistos(db, user, [])
    assert r5 == []
    assert db.leer_vistos(user) == set()
    print("OK ciclo5: al resolverse se purga el historial")

    # Ciclo 6: vuelve a alertar (reabierto) -> se trata como nuevo
    r6 = filtrar_popups_no_vistos(db, user, [{"id": 100, "nivel_alerta": "aviso"}])
    assert [a["id"] for a in r6] == [100], r6
    print("OK ciclo6: tras purgarse, reaparece como aviso nuevo ->", r6)

    # Multi-pedido: 100 ya visto, 200 nuevo -> solo se entrega 200
    r7 = filtrar_popups_no_vistos(db, user, [
        {"id": 100, "nivel_alerta": "aviso"},
        {"id": 200, "nivel_alerta": "urgente"},
    ])
    assert [a["id"] for a in r7] == [200], r7
    print("OK ciclo7: solo se entrega el pedido nuevo, no el ya visto ->", r7)

    print("\nTodas las comprobaciones OK.")


if __name__ == "__main__":
    run()
