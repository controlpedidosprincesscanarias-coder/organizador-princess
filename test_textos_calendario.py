"""Textos de Agenda, Calendario, Vacaciones y Festivos (rediseño v4.18.72): fechas cortas, antelación,
cuánto falta, estado de un periodo, resúmenes de cabecera y líneas de cada día del calendario.

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_textos_calendario.py   (no necesita Tkinter)
"""
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))
from utils import textos_calendario as T  # noqa: E402

fallos = []
def ok(nombre, cond, det=""):
    print(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
    if not cond:
        fallos.append(nombre)

HOY = date(2026, 11, 18)
AHORA = datetime(2026, 11, 18, 10, 0)

# Fechas
ok("fecha corta", T.fecha_corta("2026-11-28") == "sáb 28 nov", T.fecha_corta("2026-11-28"))
ok("fecha corta con año", T.fecha_corta("2026-12-24", con_anio=True) == "jue 24 dic 2026")
ok("una fecha que no se entiende se deja igual", T.fecha_corta("28-11-2026") == "28-11-2026")
ok("rango en el mismo año", T.rango("2026-11-28", "2026-11-29") == "sáb 28 nov → dom 29 nov 2026", T.rango("2026-11-28", "2026-11-29"))
ok("rango entre dos años lleva los dos años", T.rango("2026-12-30", "2027-01-02") == "mié 30 dic 2026 → sáb 2 ene 2027",
   T.rango("2026-12-30", "2027-01-02"))
ok("rango de un solo día", T.rango("2026-12-25", "2026-12-25") == "vie 25 dic 2026")
ok("días en singular y plural", (T.dias(1), T.dias(8)) == ("1 día", "8 días"))

# Antelación
ok("sin antelación, nada", T.antelacion({}) == "" and T.antelacion(None) == "")
ok("antelación en días", T.antelacion({"dias": 2}) == "Aviso 2 días antes")
ok("antelación combinada", T.antelacion({"dias": 1, "horas": 3, "minutos": 15}) == "Aviso 1 día, 3 h y 15 min antes",
   T.antelacion({"dias": 1, "horas": 3, "minutos": 15}))
ok("antelación con valores raros no rompe", T.antelacion({"dias": "x", "horas": "2"}) == "Aviso 2 h antes")

# Cuánto falta y estado
ok("hoy / mañana / en N días", (T.cuanto_falta("2026-11-18", HOY), T.cuanto_falta("2026-11-19", HOY),
                                T.cuanto_falta("2026-12-24", HOY)) == ("hoy", "mañana", "en 36 días"))
ok("lo pasado no dice cuánto falta", T.cuanto_falta("2026-11-01", HOY) == "")
ok("estado de un periodo", (T.estado_periodo("2026-11-01", "2026-11-05", HOY), T.estado_periodo("2026-11-17", "2026-11-20", HOY),
                            T.estado_periodo("2026-12-24", "2026-12-31", HOY)) == ("pasado", "en_curso", "proximo"))
ok("un festivo de hoy está en curso", T.estado_periodo("2026-11-18", "2026-11-18", HOY) == "en_curso")

# Resúmenes de cabecera
vacs = [{"titulo": "Asuntos propios", "fecha_inicio": "2026-11-28", "fecha_fin": "2026-11-29"},
        {"titulo": "Navidad", "fecha_inicio": "2026-12-24", "fecha_fin": "2026-12-31"},
        {"titulo": "Verano 2027", "fecha_inicio": "2027-08-01", "fecha_fin": "2027-08-15"}]
r = T.resumen_vacaciones(vacs, HOY)
ok("resumen de vacaciones: días del año y el próximo", r.startswith("2 periodos · 10 días en 2026") and "Próximo: Asuntos propios, en 10 días" in r, r)
r = T.resumen_vacaciones(vacs + [{"titulo": "Puente", "fecha_inicio": "2026-11-17", "fecha_fin": "2026-11-19"}], HOY)
ok("resumen de vacaciones: el periodo en curso manda", "En curso: Puente, hasta el jue 19 nov" in r, r)
ok("sin vacaciones", T.resumen_vacaciones([], HOY) == "Sin periodos programados.")
fests = [{"titulo": "Todos los Santos", "fecha": "2026-11-01"}, {"titulo": "Inmaculada", "fecha": "2026-12-08"},
         {"titulo": "Año Nuevo", "fecha": "2027-01-01"}]
r = T.resumen_festivos(fests, HOY)
ok("resumen de festivos", r.startswith("3 festivos · quedan 1 en 2026") and "Próximo: Inmaculada, en 20 días" in r, r)

# Líneas de cada día del calendario
ev = [{"titulo": "Reunión semanal de compras", "hora": "10:00", "repeticion": "semanal"},
      {"titulo": "Llamar", "hora": "09:00", "repeticion": "ninguna"}]
l = T.lineas_celda(ev, [{"titulo": "Asuntos propios"}], [{"titulo": "Navidad"}], maximo=3, ancho=10)
ok("orden: festivo, vacaciones y avisos por hora; lo que no cabe, «+N más»",
   [t for t, _ in l] == ["festivo", "vacaciones", "mas"] and l[2][1] == "+2 más", l)
l = T.lineas_celda(ev, [], [], maximo=3, ancho=10)
ok("avisos con su hora, recortados con «…»", l == [("aviso", "09:00 Llamar"), ("repetitivo", "10:00 Reunión s…")], l)

# Agenda
ok("hora en grande: normal y de cada hora", (T.hora_aviso({"hora": "09:30"}), T.hora_aviso({"hora": "09:15", "repeticion": "cada_hora"})) == ("09:30", ":15"))
casos = [({"repeticion": "ninguna", "fecha": "2026-11-20"}, "vie 20 nov 2026"), ({"repeticion": "diario"}, "Todos los días"),
         ({"repeticion": "semanal", "fecha": "2026-11-20"}, "Cada viernes"), ({"repeticion": "mensual", "fecha": "2026-11-05"}, "Día 5 de cada mes"),
         ({"repeticion": "anual", "fecha": "2026-03-19"}, "Cada 19 mar"), ({"repeticion": "cada_hora", "hora": "08:15"}, "Cada hora, en el minuto 15"),
         ({"repeticion": "cada_30min", "hora": "08:40"}, "Cada 30 minutos (:40 y :10)")]
for aviso, esperado in casos:
    ok(f"cuándo salta: {esperado}", T.cuando_aviso(aviso) == esperado, T.cuando_aviso(aviso))
ok("aviso único ya pasado", T.aviso_pasado({"fecha": "2026-11-18", "hora": "09:00"}, AHORA)
   and not T.aviso_pasado({"fecha": "2026-11-18", "hora": "11:00"}, AHORA)
   and not T.aviso_pasado({"fecha": "2026-01-01", "hora": "09:00", "repeticion": "diario"}, AHORA))
avisos = [{"titulo": "Pasado", "fecha": "2026-11-01", "hora": "09:00"},
          {"titulo": "Pausado", "fecha": "2026-11-19", "hora": "09:00", "activo": False},
          {"titulo": "Llamar a Suministros", "fecha": "2026-11-20", "hora": "11:30"},
          {"titulo": "Reunión", "fecha": "2026-11-17", "hora": "10:00", "repeticion": "semanal"}]
r = T.resumen_agenda(avisos, AHORA)
ok("resumen de la agenda: el próximo salta los pasados y los desactivados",
   r.startswith("3 avisos únicos · 1 repetitivo") and "Próximo: Llamar a Suministros, en 2 días a las 11:30" in r, r)
ok("agenda vacía", T.resumen_agenda([], AHORA) == "Sin avisos programados.")

print(f"\n{'Todas las comprobaciones OK.' if not fallos else str(len(fallos)) + ' fallo(s)'}")
sys.exit(1 if fallos else 0)
