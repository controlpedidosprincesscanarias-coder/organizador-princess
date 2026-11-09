"""
utils/fechas.py
Conversión y formateo de fechas para la agenda.
Extraído de main_agenda.py en Fase 2 del sprint de estabilización.
"""
import re
from datetime import date, datetime


# (v4.18.14) Lo que escribe el usuario en las cajas de fecha y hora (ui/selector_fecha_hora.py;
# lo prueba test_fecha_hora.py)
def normalizar_fecha(texto: str) -> str:
    """Convierte lo que haya escrito el usuario en «DD-MM-AAAA» si es una fecha válida.
    Acepta separadores - / . o espacio, o los números seguidos (DDMMAAAA o DDMMAA), y años
    de dos cifras (26 → 2026). Si no es una fecha válida, devuelve el texto tal cual."""
    t = (texto or "").strip()
    if re.fullmatch(r"\d{8}", t):
        d, m, a = t[:2], t[2:4], t[4:]
    elif re.fullmatch(r"\d{6}", t):
        d, m, a = t[:2], t[2:4], t[4:]
    else:
        partes = re.split(r"[-/. ]+", t)
        if len(partes) != 3 or not all(p.isdigit() for p in partes):
            return texto
        d, m, a = partes
    if len(a) == 2:
        a = "20" + a
    try:
        return date(int(a), int(m), int(d)).strftime("%d-%m-%Y")
    except ValueError:
        return texto


def normalizar_hora(texto: str) -> str:
    """«9» → 09:00, «930» → 09:30, «0930» → 09:30, «9.30» / «9:30» / «9 30» → 09:30.
    Si no es una hora válida, devuelve el texto tal cual."""
    t = (texto or "").strip()
    m = re.fullmatch(r"(\d{1,2})(?:[:.,h ]+(\d{1,2}))?", t)
    if m:
        h, mi = int(m.group(1)), int(m.group(2) or 0)
    elif re.fullmatch(r"\d{3,4}", t):
        h, mi = int(t[:-2]), int(t[-2:])
    else:
        return texto
    if 0 <= h <= 23 and 0 <= mi <= 59:
        return f"{h:02d}:{mi:02d}"
    return texto


def _iso_a_ui(fecha_iso: str) -> str:
    """Convierte 'YYYY-MM-DD' → 'DD-MM-YYYY' para mostrar en la UI."""
    try:
        return datetime.strptime(fecha_iso, "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return fecha_iso


def _ui_a_iso(fecha_ui: str) -> str:
    """Convierte 'DD-MM-YYYY' → 'YYYY-MM-DD' para guardar internamente."""
    try:
        # (v4.18.14) acepta también lo que normalizar_fecha() sabe leer: 15112026, 15/11/26…
        return datetime.strptime(normalizar_fecha(fecha_ui), "%d-%m-%Y").strftime("%Y-%m-%d")
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
