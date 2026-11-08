"""
utils/fechas.py
Conversión y formateo de fechas para la agenda.
Extraído de main_agenda.py en Fase 2 del sprint de estabilización.
"""
from datetime import datetime, date, timedelta
import calendar as _cal_mod
import re

def _iso_a_ui(fecha_iso: str) -> str:
    """Convierte 'YYYY-MM-DD' → 'DD-MM-YYYY' para mostrar en la UI."""
    try:
        return datetime.strptime(fecha_iso, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return fecha_iso


def _ui_a_iso(fecha_ui: str) -> str:
    """Convierte 'DD-MM-YYYY' → 'YYYY-MM-DD' para guardar internamente."""
    try:
        return datetime.strptime(fecha_ui, "%d-%m-%Y").strftime("%Y-%m-%d")
    except Exception:
        return fecha_ui


def _dias_entre(f_ini, f_fin):
    """Días naturales entre dos fechas AAAA-MM-DD (ambas inclusive)."""
    try:
        d0 = datetime.strptime(f_ini, "%Y-%m-%d").date()
        d1 = datetime.strptime(f_fin, "%Y-%m-%d").date()
        return max(0, (d1 - d0).days + 1)
    except Exception:
        return 0


    def _nombre_dia_largo(fecha_dt):
        nombres = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
        return nombres[fecha_dt.weekday()]


def _parse_version(tag: str):
    """Convierte 'v4.2.1' → (4, 2, 1) para comparación numérica."""
    import re
    nums = re.findall(r"\d+", tag)
    return tuple(int(n) for n in nums)
