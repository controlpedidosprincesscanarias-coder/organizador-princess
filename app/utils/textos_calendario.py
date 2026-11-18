"""
utils/textos_calendario.py
Textos de las ventanas Calendario, Vacaciones y Festivos (rediseño v4.18.72): fechas cortas en español,
antelación del aviso, cuánto falta, estado de un periodo y resumen de cada lista. Sin Tkinter, para
poder probarlo (test_textos_calendario.py).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.
"""
from datetime import date, datetime

DIAS_CORTOS  = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
DIAS_LARGOS  = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def a_fecha(valor):
    """date desde 'AAAA-MM-DD' (o date). None si no se entiende."""
    if isinstance(valor, date):
        return valor
    try:
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def fecha_corta(valor, con_anio=False):
    """'sáb 28 nov' (o 'sáb 28 nov 2026'). Si no es una fecha, la devuelve tal cual."""
    d = a_fecha(valor)
    if d is None:
        return str(valor or "")
    txt = f"{DIAS_CORTOS[d.weekday()]} {d.day} {MESES_CORTOS[d.month - 1]}"
    return f"{txt} {d.year}" if con_anio else txt


def rango(ini, fin):
    """'sáb 28 nov → dom 29 nov 2026'; con el año en las dos si son de años distintos."""
    d0, d1 = a_fecha(ini), a_fecha(fin)
    if d0 is None or d1 is None:
        return f"{ini} → {fin}"
    if d0 == d1:
        return fecha_corta(d0, con_anio=True)
    return f"{fecha_corta(d0, con_anio=d0.year != d1.year)} → {fecha_corta(d1, con_anio=True)}"


def dias(n):
    return f"{n} día" if n == 1 else f"{n} días"


def antelacion(ant):
    """'Aviso 2 días antes', 'Aviso 1 día y 3 h antes', 'Aviso 30 min antes'; '' si no hay antelación."""
    ant = ant if isinstance(ant, dict) else {}
    partes = []
    for clave, fmt in (("dias", dias), ("horas", lambda n: f"{n} h"), ("minutos", lambda n: f"{n} min")):
        try:
            n = int(ant.get(clave, 0) or 0)
        except (TypeError, ValueError):
            n = 0
        if n > 0:
            partes.append(fmt(n))
    if not partes:
        return ""
    txt = partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + " y " + partes[-1]
    return f"Aviso {txt} antes"


def cuanto_falta(valor, hoy):
    """'hoy', 'mañana', 'en 36 días'; '' si ya pasó o no es una fecha."""
    d = a_fecha(valor)
    if d is None:
        return ""
    n = (d - hoy).days
    if n < 0:
        return ""
    return "hoy" if n == 0 else ("mañana" if n == 1 else f"en {n} días")


def estado_periodo(ini, fin, hoy):
    """'pasado', 'en_curso' o 'proximo' de un periodo (un festivo: ini == fin)."""
    d0, d1 = a_fecha(ini), a_fecha(fin)
    if d0 is None or d1 is None:
        return "proximo"
    if d1 < hoy:
        return "pasado"
    if d0 <= hoy:
        return "en_curso"
    return "proximo"


def num_dias(ini, fin):
    d0, d1 = a_fecha(ini), a_fecha(fin)
    if d0 is None or d1 is None or d1 < d0:
        return 0
    return (d1 - d0).days + 1


def resumen_vacaciones(vacaciones, hoy):
    """Línea de cabecera de Vacaciones: periodos y días del año actual, y el siguiente (o el que está en curso)."""
    vacs = [v for v in vacaciones if a_fecha(v.get("fecha_inicio")) and a_fecha(v.get("fecha_fin"))]
    if not vacs:
        return "Sin periodos programados."
    del_anio = [v for v in vacs if a_fecha(v["fecha_inicio"]).year == hoy.year]
    total = sum(num_dias(v["fecha_inicio"], v["fecha_fin"]) for v in del_anio)
    partes = [f"{len(del_anio)} periodo{'s' if len(del_anio) != 1 else ''} · {dias(total)} en {hoy.year}"]
    en_curso = [v for v in vacs if estado_periodo(v["fecha_inicio"], v["fecha_fin"], hoy) == "en_curso"]
    if en_curso:
        v = min(en_curso, key=lambda x: x["fecha_fin"])
        partes.append(f"En curso: {v.get('titulo') or 'Vacaciones'}, hasta el {fecha_corta(v['fecha_fin'])}")
    else:
        futuros = [v for v in vacs if estado_periodo(v["fecha_inicio"], v["fecha_fin"], hoy) == "proximo"]
        if futuros:
            v = min(futuros, key=lambda x: x["fecha_inicio"])
            partes.append(f"Próximo: {v.get('titulo') or 'Vacaciones'}, {cuanto_falta(v['fecha_inicio'], hoy)}")
    return "   ·   ".join(partes)


def resumen_festivos(festivos, hoy):
    """Línea de cabecera de Festivos: cuántos quedan este año y el siguiente."""
    fests = [f for f in festivos if a_fecha(f.get("fecha"))]
    if not fests:
        return "Sin festivos definidos."
    futuros = sorted((f for f in fests if a_fecha(f["fecha"]) >= hoy), key=lambda x: x["fecha"])
    quedan = [f for f in futuros if a_fecha(f["fecha"]).year == hoy.year]
    partes = [f"{len(fests)} festivo{'s' if len(fests) != 1 else ''} · quedan {len(quedan)} en {hoy.year}"]
    if futuros:
        f = futuros[0]
        partes.append(f"Próximo: {f.get('titulo') or 'Festivo'}, {cuanto_falta(f['fecha'], hoy)}")
    return "   ·   ".join(partes)


def recortar(texto, maximo):
    texto = str(texto or "")
    return texto if len(texto) <= maximo else texto[:maximo - 1].rstrip() + "…"


def lineas_celda(eventos, vacaciones, festivos, maximo=3, ancho=16):
    """Lo que cabe en la celda de un día del mes: [(tipo, texto)], con tipo festivo / vacaciones / aviso /
    repetitivo / mas. Primero festivos y vacaciones, luego los avisos por hora; lo que no cabe, «+N más»."""
    lineas = [("festivo", recortar(f.get("titulo") or "Festivo", ancho + 4)) for f in festivos]
    lineas += [("vacaciones", recortar(v.get("titulo") or "Vacaciones", ancho + 4)) for v in vacaciones]
    for ev in sorted(eventos, key=lambda x: x.get("hora", "")):
        tipo = "aviso" if ev.get("repeticion", "ninguna") == "ninguna" else "repetitivo"
        lineas.append((tipo, f"{ev.get('hora', '')} {recortar(ev.get('titulo', ''), ancho)}".strip()))
    if len(lineas) > maximo:
        resto = len(lineas) - (maximo - 1)
        lineas = lineas[:maximo - 1] + [("mas", f"+{resto} más")]
    return lineas


# ── Agenda de avisos (v4.18.72) ───────────────────────────────────────────────
NOMBRE_REPETICION = {"ninguna": "Único", "cada_30min": "Cada 30 min", "cada_hora": "Cada hora",
                     "diario": "Diario", "semanal": "Semanal", "mensual": "Mensual", "anual": "Anual"}


def _minuto(hora):
    try:
        return int(str(hora).split(":")[1])
    except (IndexError, ValueError):
        return 0


def hora_aviso(aviso):
    """Lo que va en grande a la izquierda de la tarjeta: '09:00', o ':15' en los de cada hora."""
    rep, hora = aviso.get("repeticion", "ninguna"), str(aviso.get("hora", ""))
    if rep in ("cada_hora", "cada_30min"):
        return f":{_minuto(hora):02d}"
    return hora


def cuando_aviso(aviso):
    """Cuándo salta, en palabras: 'jue 20 nov 2026', 'Todos los días', 'Cada lunes', 'Día 5 de cada mes'…"""
    rep = aviso.get("repeticion", "ninguna")
    d = a_fecha(aviso.get("fecha"))
    if rep == "ninguna":
        return fecha_corta(d, con_anio=True) if d else str(aviso.get("fecha", ""))
    if rep == "diario":
        return "Todos los días"
    if rep == "cada_hora":
        return f"Cada hora, en el minuto {_minuto(aviso.get('hora')):02d}"
    if rep == "cada_30min":
        m = _minuto(aviso.get("hora"))
        return f"Cada 30 minutos (:{m:02d} y :{(m + 30) % 60:02d})"
    if d is None:
        return NOMBRE_REPETICION.get(rep, rep)
    if rep == "semanal":
        return f"Cada {DIAS_LARGOS[d.weekday()]}"
    if rep == "mensual":
        return f"Día {d.day} de cada mes"
    if rep == "anual":
        return f"Cada {d.day} {MESES_CORTOS[d.month - 1]}"
    return NOMBRE_REPETICION.get(rep, rep)


def aviso_pasado(aviso, ahora):
    """Un aviso único cuya fecha y hora ya pasaron (ahora: datetime)."""
    if aviso.get("repeticion", "ninguna") != "ninguna":
        return False
    try:
        return datetime.strptime(f"{aviso.get('fecha')} {aviso.get('hora')}", "%Y-%m-%d %H:%M") < ahora
    except (TypeError, ValueError):
        return False


def resumen_agenda(avisos, ahora):
    """Cabecera de la Agenda: cuántos avisos hay y el siguiente aviso único pendiente."""
    if not avisos:
        return "Sin avisos programados."
    rep = [a for a in avisos if a.get("repeticion", "ninguna") != "ninguna"]
    unicos = [a for a in avisos if a.get("repeticion", "ninguna") == "ninguna"]
    partes = [f"{len(unicos)} aviso{'s' if len(unicos) != 1 else ''} único{'s' if len(unicos) != 1 else ''}"
              f" · {len(rep)} repetitivo{'s' if len(rep) != 1 else ''}"]
    pendientes = sorted((a for a in unicos if a.get("activo", True) and not aviso_pasado(a, ahora)
                         and a_fecha(a.get("fecha"))),
                        key=lambda a: (a.get("fecha", ""), a.get("hora", "")))
    if pendientes:
        a = pendientes[0]
        falta = cuanto_falta(a["fecha"], ahora.date())
        partes.append(f"Próximo: {a.get('titulo') or 'Aviso'}, {falta} a las {a.get('hora', '')}")
    return "   ·   ".join(partes)
