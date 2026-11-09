"""Fechas y horas escritas a mano en los formularios de avisos, vacaciones y festivos (v4.18.14).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Uso: python test_fecha_hora.py   (no necesita Tkinter)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))
from utils.fechas import normalizar_fecha, normalizar_hora, _ui_a_iso, _dias_entre  # noqa: E402

fallos = []
def ok(nombre, cond, det=""):
    print(("OK    " if cond else "FALLO ") + nombre + ("" if cond else f"  → {det}"))
    if not cond:
        fallos.append(nombre)

for entrada, esperado in [("15-11-2026", "15-11-2026"), ("15112026", "15-11-2026"), ("151126", "15-11-2026"),
                          ("15/11/2026", "15-11-2026"), ("5/1/27", "05-01-2027"), (" 5.1.2027 ", "05-01-2027"),
                          ("31-02-2026", "31-02-2026"), ("mañana", "mañana"), ("", "")]:
    r = normalizar_fecha(entrada)
    ok(f"fecha «{entrada}» → «{esperado}»", r == esperado, r)

for entrada, esperado in [("9", "09:00"), ("930", "09:30"), ("0930", "09:30"), ("9:30", "09:30"), ("9.30", "09:30"),
                          ("9 30", "09:30"), ("2359", "23:59"), ("24:00", "24:00"), ("9:75", "9:75"), ("abc", "abc")]:
    r = normalizar_hora(entrada)
    ok(f"hora «{entrada}» → «{esperado}»", r == esperado, r)

ok("al guardar, una fecha escrita sin guiones se entiende", _ui_a_iso("15112026") == "2026-11-15", _ui_a_iso("15112026"))
ok("al guardar, una fecha imposible no se convierte (el formulario avisa)", _ui_a_iso("31-02-2026") == "31-02-2026")
ok("los días de unas vacaciones escritas con barras se cuentan", _dias_entre(_ui_a_iso("24/12/2026"), _ui_a_iso("31/12/2026")) == 8)

print(f"\n{'Todas las comprobaciones OK.' if not fallos else str(len(fallos)) + ' fallo(s)'}")
sys.exit(1 if fallos else 0)
