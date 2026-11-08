"""
app/ui/agenda_helpers.py
Helpers de consulta de agenda para una fecha concreta.
Extraído de main_agenda.py en Fase 3B.

Sin UI — funciones puras que leen ctx.agenda_data.
"""
from datetime import datetime


def _eventos_del_dia(ctx, fecha_dt):
    """Devuelve los avisos que dispararán en la fecha dada (date object)."""
    fecha_str = fecha_dt.strftime("%Y-%m-%d")
    resultado = []
    for aviso in ctx.agenda_data.get("avisos", []):
        rep = aviso.get("repeticion", "ninguna")
        fecha_inicio = aviso.get("fecha", "")
        if rep == "ninguna":
            if aviso["fecha"] == fecha_str:
                resultado.append(aviso)
        elif rep == "diario":
            if fecha_str >= fecha_inicio:
                resultado.append(aviso)
        elif rep == "semanal":
            try:
                if (fecha_str >= fecha_inicio and
                        datetime.strptime(fecha_inicio, "%Y-%m-%d").weekday() == fecha_dt.weekday()):
                    resultado.append(aviso)
            except Exception:  # noqa: BLE001
                import sys as _sys, traceback as _tb
                print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
        elif rep == "mensual":
            try:
                if (fecha_str >= fecha_inicio and
                        datetime.strptime(fecha_inicio, "%Y-%m-%d").day == fecha_dt.day):
                    resultado.append(aviso)
            except Exception:  # noqa: BLE001
                import sys as _sys, traceback as _tb
                print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
        elif rep in ("cada_hora", "cada_30min"):
            if fecha_str >= fecha_inicio:
                resultado.append(aviso)
    return resultado


def _vacaciones_del_dia(ctx, fecha_dt):
    """Devuelve periodos de vacaciones que cubren esta fecha."""
    fecha_str = fecha_dt.strftime("%Y-%m-%d")
    return [v for v in ctx.agenda_data.get("vacaciones", [])
            if v["fecha_inicio"] <= fecha_str <= v["fecha_fin"]]


def _festivos_del_dia(ctx, fecha_dt):
    """Devuelve festivos que coinciden con esta fecha."""
    fecha_str = fecha_dt.strftime("%Y-%m-%d")
    return [f for f in ctx.agenda_data.get("festivos", [])
            if f["fecha"] == fecha_str]


def get_nombre(ctx, opcion, idx):
    """Devuelve el nombre de una opción del grid de botones."""
    if opcion in ctx.config and "nombre" in ctx.config[opcion]:
        return ctx.config[opcion]["nombre"]
    return f"{idx}. POR DEFINIR"
