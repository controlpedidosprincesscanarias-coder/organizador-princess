"""
negocio/alertas.py
Monitor de avisos, cola de popups y construcción de ventanas de alerta.
Extraído de main_agenda.py en Fase 2 del sprint de estabilización.

Dependencias inyectadas desde main_agenda (ver bloque al final del arranque):
    app           = alertas_mod.app
    agenda_data   = alertas_mod.agenda_data
    save_agenda   = alertas_mod.save_agenda
"""
import queue
import time                                          # ANTI-REGRESION: necesario para time.sleep en monitor_avisos
import logging
import os
from datetime import datetime, timedelta
import ttkbootstrap as ttk
from utils.fechas import _iso_a_ui
from utils.sonido import _reproducir_sonido_aviso
from db.sqlite import load_agenda, save_agenda       # ANTI-REGRESION: importar directamente, no depender de inyección desde main_agenda
from negocio.correo import (                         # ANTI-REGRESION: usadas en _construir_popup para botón de correo
    _enriquecer_evento_correo,
    _abrir_ventana_correo,
)

# ── Logger de diagnóstico del monitor de avisos ───────────────────────────────
# Escribe en %APPDATA%\OrganizadorPrincess\monitor_avisos.log
# Rotación automática: máximo 200 KB, 1 backup → nunca ocupa más de ~400 KB.
# Para silenciar en producción: cambiar setLevel(logging.DEBUG) → setLevel(logging.WARNING)
def _init_logger() -> logging.Logger:
    try:
        from logging.handlers import RotatingFileHandler
        _appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        _log_dir = os.path.join(_appdata, "OrganizadorPrincess")
        os.makedirs(_log_dir, exist_ok=True)
        _log_path = os.path.join(_log_dir, "monitor_avisos.log")
        _logger = logging.getLogger("monitor_avisos")
        if not _logger.handlers:            # evitar duplicar handlers en reimports
            _h = RotatingFileHandler(
                _log_path, maxBytes=200_000, backupCount=1, encoding="utf-8"
            )
            _h.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            ))
            _logger.addHandler(_h)
            _logger.setLevel(logging.DEBUG)
        return _logger
    except Exception:
        return logging.getLogger("monitor_avisos")  # fallback silencioso

_log = _init_logger()

# Inyectados desde main_agenda al arrancar (late binding)
app           = None   # tk root
agenda_data   = None   # dict mutable
on_agenda_changed = None  # callback inyectado desde main_agenda para refrescar la lista de avisos
# save_agenda importada directamente desde db.sqlite — ANTI-REGRESION (bug Fase 3.7c): inyección vía main_agenda era frágil y podía quedar None
# ANTI-REGRESION: _apply_icon se inyecta desde main_agenda igual que app/agenda_data/save_agenda.
# En main_agenda.py debe existir: _alertas_mod._apply_icon = _apply_icon
_apply_icon   = lambda win: None  # noqa: E731 — default no-op hasta que main_agenda lo inyecte

# Constantes de color usadas en _construir_popup
# ANTI-REGRESION: en el monolito eran globals de main_agenda; al extraer alertas.py no se llevaron.
GOLD  = "#C9A84C"
LIGHT = "#D8E8F0"

# Lista de días en español usada en _descripcion_aviso (rep == semanal)
# ANTI-REGRESION: en el monolito era un local de abrir_agenda(); aquí se define como global de módulo.
_DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

# Estado interno
# Prefijo "HOY:" → silenciado solo hoy (repetición cancelada).
# Prefijo "OFF:" → aviso desactivado permanentemente (ya guardado en JSON).
_avisos_silenciados: set = set()

# ── Cola de popups ─────────────────────────────────────────────────────────────
# Garantiza que los popups se muestren uno a uno aunque lleguen varios a la vez
# (p.ej. cuando el bridge detecta N alertas simultáneas al arrancar).
_popup_queue: queue.Queue = queue.Queue()
_popup_activo: bool = False



def _descripcion_aviso(aviso):
    """Genera la línea descriptiva de un aviso para mostrarlo en lista."""
    rep  = aviso.get("repeticion", "ninguna")
    hora = aviso["hora"]
    fecha_ui = _iso_a_ui(aviso.get("fecha", ""))
    # Badge de antelación
    ant = aviso.get("antelacion", {})
    ant_d = int(ant.get("dias", 0))
    ant_h = int(ant.get("horas", 0))
    ant_m = int(ant.get("minutos", 0))
    partes = []
    if ant_d: partes.append(f"{ant_d}d")
    if ant_h: partes.append(f"{ant_h}h")
    if ant_m: partes.append(f"{ant_m}min")
    ant_badge = f"  ⏰-{' '.join(partes)}" if partes else ""

    if rep == "ninguna":
        return f"🕐 {fecha_ui}  {hora}{ant_badge}   —   {aviso['titulo']}"
    if rep == "cada_30min":
        mm = hora.split(":")[1]
        return f"🕐 :{mm} / :{(int(mm) + 30) % 60:02d} cada hora   —   {aviso['titulo']}"
    if rep == "cada_hora":
        mm = hora.split(":")[1]
        return f"🕐 :{mm} de cada hora   —   {aviso['titulo']}"
    if rep == "diario":
        return f"🕐 {hora} cada día{ant_badge}   —   {aviso['titulo']}"
    if rep == "semanal":
        try:
            dow = datetime.strptime(aviso["fecha"], "%Y-%m-%d").weekday()
            # (v4.18.12) «Lunes» a «Viernes» no cambian en plural: antes salía «Luness»
            dia = _DIAS_ES[dow] + ("s" if dow >= 5 else "")
        except Exception:
            dia = "?"
        return f"🕐 {dia}  {hora}{ant_badge}   —   {aviso['titulo']}"
    if rep == "mensual":
        try:
            dia = datetime.strptime(aviso["fecha"], "%Y-%m-%d").day
        except Exception:
            dia = "?"
        return f"🕐 Día {dia} de cada mes  {hora}{ant_badge}   —   {aviso['titulo']}"
    if rep == "anual":
        try:
            _f = datetime.strptime(aviso["fecha"], "%Y-%m-%d")
            dia_mes = f"{_f.day:02d}/{_f.month:02d}"
        except Exception:
            dia_mes = "?"
        return f"🕐 {dia_mes} de cada año  {hora}{ant_badge}   —   {aviso['titulo']}"
    return f"🕐 {fecha_ui}  {hora}{ant_badge}   —   {aviso['titulo']}"


def _debe_disparar(aviso, ahora):
    """Devuelve True si el aviso debe dispararse en el minuto 'ahora'.
    Si tiene antelación configurada, el disparo ocurre (fecha/hora - antelación).
    """
    rep      = aviso.get("repeticion", "ninguna")
    hora_cfg = aviso["hora"]           # "HH:MM" almacenado
    hh_cfg, mm_cfg = hora_cfg.split(":")

    # Calcular el momento real de disparo aplicando la antelación
    ant = aviso.get("antelacion", {})
    ant_total_min = (int(ant.get("dias", 0)) * 1440
                     + int(ant.get("horas", 0)) * 60
                     + int(ant.get("minutos", 0)))

    if ant_total_min > 0 and rep in ("ninguna", "semanal", "mensual", "anual", "diario"):
        # Para avisos con fecha/hora concreta, calculamos cuándo disparar
        try:
            dt_evento = datetime.strptime(
                f"{aviso['fecha']} {hora_cfg}", "%Y-%m-%d %H:%M")
            dt_disparo = dt_evento - timedelta(minutes=ant_total_min)
        except Exception:
            dt_disparo = None

        if dt_disparo is not None:
            hora_hoy2 = ahora.strftime("%H:%M")
            fecha_hoy2 = ahora.strftime("%Y-%m-%d")
            disparo_fecha = dt_disparo.strftime("%Y-%m-%d")
            disparo_hora  = dt_disparo.strftime("%H:%M")

            # ANTI-REGRESION (reportado 2026-07-21): antes se exigía coincidencia
            # EXACTA de minuto (disparo_hora == hora_hoy2). Si el Organizador no
            # estaba abierto justo en ese minuto (PC apagado, app cerrada), el
            # aviso de ese día/semana/mes se perdía sin remedio hasta la
            # siguiente ocurrencia. Ahora "a partir de esa hora" (>=), y el
            # anti-repetición pasa a ser por día (ver monitor_avisos) para que
            # no reaparezca cada minuto del resto del día una vez mostrado.
            if rep == "ninguna":
                return disparo_fecha == fecha_hoy2 and hora_hoy2 >= disparo_hora

            # ANTI-REGRESION (reportado 2026-07-24): faltaba comprobar que ya se
            # hubiera alcanzado la fecha de inicio del aviso (aviso["fecha"]).
            # Al comparar solo hora/día-semana/día-mes, un aviso "Diariamente"
            # (o semanal/mensual/anual) con fecha de inicio futura (p.ej.
            # 15-01-2027) disparaba igualmente hoy en cuanto coincidía la hora,
            # porque nunca se miraba si "hoy" ya era >= la fecha configurada.
            # Ahora se exige fecha_hoy2 >= aviso["fecha"] como suelo, además
            # de la coincidencia de hora/patrón de recurrencia.
            if fecha_hoy2 < aviso.get("fecha", fecha_hoy2):
                return False

            if rep == "diario":
                return hora_hoy2 >= disparo_hora

            if rep == "semanal":
                try:
                    dow_cfg = datetime.strptime(aviso["fecha"], "%Y-%m-%d").weekday()
                    # El día de la semana del disparo puede variar si la antelación cruza medianoche
                    dow_dis = dt_disparo.weekday()
                except Exception:
                    return False
                return ahora.weekday() == dow_dis and hora_hoy2 >= disparo_hora

            if rep == "mensual":
                try:
                    dia_dis = dt_disparo.day
                except Exception:
                    return False
                return ahora.day == dia_dis and hora_hoy2 >= disparo_hora

            if rep == "anual":
                try:
                    dia_dis = dt_disparo.day
                    mes_dis = dt_disparo.month
                except Exception:
                    return False
                return (ahora.day == dia_dis and ahora.month == mes_dis
                        and hora_hoy2 >= disparo_hora)

    # Sin antelación (o tipos no aplicables): lógica original
    hora_hoy  = ahora.strftime("%H:%M")
    fecha_hoy = ahora.strftime("%Y-%m-%d")

    if rep == "ninguna":
        return aviso["fecha"] == fecha_hoy and hora_cfg == hora_hoy

    # ANTI-REGRESION (reportado 2026-07-24): mismo fix que en la rama con
    # antelación — diario/semanal/mensual/anual no comprobaban que ya se
    # hubiera alcanzado la fecha de inicio del aviso, así que un aviso
    # "Diariamente" guardado con fecha de inicio futura disparaba igualmente
    # hoy en cuanto coincidía la hora. Se exige fecha_hoy >= aviso["fecha"]
    # como suelo antes de evaluar el patrón de recurrencia.
    if rep in ("diario", "semanal", "mensual", "anual") and fecha_hoy < aviso.get("fecha", fecha_hoy):
        return False

    if rep == "diario":
        return hora_cfg == hora_hoy

    if rep == "semanal":
        try:
            dow_cfg = datetime.strptime(aviso["fecha"], "%Y-%m-%d").weekday()
        except Exception:
            return False
        return ahora.weekday() == dow_cfg and hora_cfg == hora_hoy

    if rep == "mensual":
        try:
            dia_cfg = datetime.strptime(aviso["fecha"], "%Y-%m-%d").day
        except Exception:
            return False
        return ahora.day == dia_cfg and hora_cfg == hora_hoy

    if rep == "anual":
        try:
            _f = datetime.strptime(aviso["fecha"], "%Y-%m-%d")
        except Exception:
            return False
        return ahora.day == _f.day and ahora.month == _f.month and hora_cfg == hora_hoy

    if rep == "cada_hora":
        # ANTI-REGRESION (bug Fase 3.7e): refrescar ahora aquí para evitar drift acumulado del sleep
        ahora = datetime.now()
        # Con antelación: disparar solo dentro de la ventana [dt_inicio, dt_evento)
        if ant_total_min > 0:
            try:
                dt_evento = datetime.strptime(f"{aviso['fecha']} {hora_cfg}", "%Y-%m-%d %H:%M")
                dt_inicio = dt_evento - timedelta(minutes=ant_total_min)
                # Fuera de la ventana de aviso → no disparar
                if ahora < dt_inicio or ahora >= dt_evento:
                    return False
            except Exception:  # noqa: BLE001
                import sys as _sys, traceback as _tb
                print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
        else:
            # Sin antelación: nunca disparar antes de la fecha+hora de inicio configurada
            try:
                dt_inicio = datetime.strptime(f"{aviso['fecha']} {hora_cfg}", "%Y-%m-%d %H:%M")
                if ahora < dt_inicio:
                    return False
            except Exception:  # noqa: BLE001
                import sys as _sys, traceback as _tb
                print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
        return ahora.minute == int(mm_cfg)

    if rep == "cada_30min":
        # ANTI-REGRESION (bug Fase 3.7e): refrescar ahora aquí para evitar drift acumulado del sleep
        ahora = datetime.now()
        # Con antelación: disparar solo dentro de la ventana [dt_inicio, dt_evento)
        if ant_total_min > 0:
            try:
                dt_evento = datetime.strptime(f"{aviso['fecha']} {hora_cfg}", "%Y-%m-%d %H:%M")
                dt_inicio = dt_evento - timedelta(minutes=ant_total_min)
                # Fuera de la ventana de aviso → no disparar
                if ahora < dt_inicio or ahora >= dt_evento:
                    return False
            except Exception:  # noqa: BLE001
                import sys as _sys, traceback as _tb
                print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
        else:
            # Sin antelación: nunca disparar antes de la fecha+hora de inicio configurada
            try:
                dt_inicio = datetime.strptime(f"{aviso['fecha']} {hora_cfg}", "%Y-%m-%d %H:%M")
                if ahora < dt_inicio:
                    return False
            except Exception:  # noqa: BLE001
                import sys as _sys, traceback as _tb
                print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)
        mm0 = int(mm_cfg)
        mm1 = (mm0 + 30) % 60
        return ahora.minute in (mm0, mm1)

    return False


def _procesar_cola_popups():
    """Abre el siguiente popup en cola si no hay ninguno visible ahora mismo.
    Debe llamarse siempre desde el hilo principal de Tkinter.

    ANTI-REGRESION (bug estructural detectado tras revisión de logs 2026-06-22):
    si _construir_popup() lanza cualquier excepción a medias de su construcción,
    _popup_activo quedaba fijado en True para siempre (solo se resetea dentro de
    _on_close, que nunca llega a registrarse como callback). Esto bloqueaba la
    cola de popups de forma permanente, aunque el poller siguiera vivo. Ahora se
    captura cualquier excepción, se libera el flag y se descarta ese aviso
    concreto (queda registrado en agenda.json/eventos igualmente, solo se pierde
    el popup de ESE aviso) para no bloquear los siguientes.
    """
    global _popup_activo
    if _popup_activo:
        _log.debug("_procesar_cola: popup ya activo, esperando")
        return
    try:
        aviso, clave_silencio = _popup_queue.get_nowait()
    except queue.Empty:
        return
    _popup_activo = True
    try:
        _construir_popup(aviso, clave_silencio)
    except Exception:  # noqa: BLE001
        _log.exception(
            "_procesar_cola_popups: fallo construyendo popup '%s' — se libera "
            "el flag y se descarta este popup para no bloquear la cola",
            aviso.get("titulo", "?")
        )
        _popup_activo = False


def poll_alertas():
    """Poller que el hilo principal ejecuta cada 500 ms via app.after().

    Vacía la cola de popups pendientes y se re-registra a sí mismo.
    Debe arrancarse UNA sola vez desde main_agenda.py con:
        app.after(500, poll_alertas)

    Por qué existe esto
    -------------------
    Con PyInstaller console=False, el bootloader lanza el script Python
    en un hilo secundario (el hilo principal del proceso Windows es el
    message loop de la subsystem GUI). Tkinter solo acepta app.after()
    desde el mismo hilo que creó la ventana; llamarlo desde el hilo monitor
    lanza RuntimeError: main thread is not in main loop.
    La solución es: el hilo monitor solo encola en _popup_queue (thread-safe)
    y este poller, ejecutado siempre en el hilo correcto, vacía la cola.

    ANTI-REGRESION (bug estructural detectado tras revisión de logs 2026-06-22):
    antes, app.after(500, poll_alertas) solo se ejecutaba si _procesar_cola_popups()
    no lanzaba excepción. Como este poller se registra UNA sola vez al arrancar
    (main_agenda.py), cualquier excepción no capturada mataba el ciclo de polling
    para siempre en esa sesión — sin traceback visible porque la app corre con
    console=False. El re-registro ahora va en un finally, así que el poller
    sobrevive a cualquier fallo interno.
    """
    try:
        _procesar_cola_popups()
    except Exception:  # noqa: BLE001
        _log.exception("poll_alertas: fallo inesperado en _procesar_cola_popups")
    finally:
        if app is not None:
            app.after(500, poll_alertas)   # re-registrar SIEMPRE, incluso tras fallo


def monitor_avisos():
    """Hilo daemon: se sincroniza con el reloj y comprueba avisos al inicio de cada minuto.
    ANTI-REGRESION (bug Fase 3.7d): el primer ciclo se ejecuta inmediatamente para capturar
    disparos que ocurrieron en el minuto de arranque, evitando perder el primer aviso si la
    app se inicia dentro del minuto exacto de disparo de un aviso cada_hora/cada_30min.
    """
    _log.info("── MONITOR ARRANCADO (hilo daemon) ──────────────────────────────")
    mostrados = set()
    ciclo = 0
    # Limpiar mostrados a medianoche para no crecer indefinidamente
    _ultimo_dia_mostrados = datetime.now().strftime("%Y-%m-%d")
    while True:
        ciclo += 1
        try:
            # ANTI-REGRESION (bug Fase 3.7e): capturar ahora AQUÍ para tener el tiempo más fresco.
            # El sleep puede acumular drift de hasta 1s; si el ciclo empieza a las 08:18:00
            # pero ahora se capturó antes del sleep con valor 08:17:xx, _debe_disparar devuelve
            # False incorrectamente al comparar con dt_inicio=08:18. Recapturar aquí lo evita.
            ahora     = datetime.now()
            # Limpiar mostrados al cambiar de día
            fecha_actual = ahora.strftime("%Y-%m-%d")
            if fecha_actual != _ultimo_dia_mostrados:
                mostrados.clear()
                _ultimo_dia_mostrados = fecha_actual
                _log.info("  mostrados limpiado para nuevo día %s", fecha_actual)
            fecha_hoy = ahora.strftime("%Y-%m-%d")
            hora_hoy  = ahora.strftime("%H:%M")
            _log.debug("CICLO #%d  %s %s", ciclo, fecha_hoy, hora_hoy)
            data = load_agenda()
            n_avisos = len(data.get("avisos", []))
            n_vac    = len(data.get("vacaciones", []))
            n_fest   = len(data.get("festivos", []))
            _log.debug("  agenda cargada: %d avisos, %d vac, %d festivos", n_avisos, n_vac, n_fest)

            # ── Avisos normales ──────────────────────────────────
            for aviso in data.get("avisos", []):
                if not aviso.get("activo", True):
                    continue
                # Los avisos del bridge tienen su propio ciclo de popups
                # gestionado por pedidos_agenda_bridge; el monitor no los toca.
                if aviso.get("_bridge_gestionado"):
                    continue
                rep   = aviso.get("repeticion", "ninguna")
                # ANTI-REGRESION (reportado 2026-07-21): los avisos con antelación
                # configurada (ver _debe_disparar) ahora se mantienen "debe=True"
                # desde su hora de disparo hasta medianoche, no solo un minuto
                # exacto — así se recupera el aviso si la app no estaba abierta
                # justo en ese minuto. Por eso, para ESTOS, la clave anti-repetición
                # es por DÍA (no por minuto): si fuera por minuto, volvería a
                # saltar cada minuto del resto del día tras el primer disparo.
                # Los demás tipos (cada_hora, cada_30min, o estos mismos sin
                # antelación) siguen siendo estrictamente por minuto, como antes.
                ant_cfg = aviso.get("antelacion", {})
                ant_min_total = (int(ant_cfg.get("dias", 0)) * 1440
                                 + int(ant_cfg.get("horas", 0)) * 60
                                 + int(ant_cfg.get("minutos", 0)))
                if ant_min_total > 0 and rep in ("ninguna", "diario", "semanal", "mensual", "anual"):
                    clave = f"ANT:{aviso['titulo']}_{aviso['hora']}_{rep}_{fecha_hoy}"
                else:
                    clave = f"{aviso['titulo']}_{aviso['hora']}_{rep}_{fecha_hoy}_{hora_hoy}"
                # Clave de silencio-hoy: cubre todas las horas del día para este aviso
                clave_hoy = f"HOY:{aviso['titulo']}_{aviso['hora']}_{rep}_{fecha_hoy}"
                debe = _debe_disparar(aviso, ahora)
                ya_mostrado = clave in mostrados
                silenciado  = clave_hoy in _avisos_silenciados
                # ANTI-REGRESION (bug Fase 3.7d): usar INFO para que sea visible en log normal
                # sin necesidad de activar DEBUG — facilita diagnóstico de avisos que no saltan
                _log.info("  aviso '%s' %s → debe=%s ya_mostrado=%s silenciado=%s",
                           aviso.get("titulo","?"), aviso.get("hora","?"),
                           debe, ya_mostrado, silenciado)
                if debe and not ya_mostrado and not silenciado:
                    _log.info("  ▶ DISPARANDO aviso '%s' a las %s", aviso.get("titulo","?"), hora_hoy)
                    mostrar_alerta(aviso, clave_silencio=clave_hoy)
                    mostrados.add(clave)

            # ── Avisos de vacaciones: antelacion + aviso el dia del evento ──
            for vac in data.get("vacaciones", []):
                ant = vac.get("antelacion", {})
                ant_d = int(ant.get("dias", 0))
                ant_h = int(ant.get("horas", 0))
                ant_m = int(ant.get("minutos", 0))
                ant_total_min = ant_d * 1440 + ant_h * 60 + ant_m
                try:
                    dt_ini = datetime.strptime(vac["fecha_inicio"], "%Y-%m-%d")
                    dt_evento = dt_ini.replace(hour=9, minute=0, second=0)
                    # Aviso anticipado (solo si hay antelacion configurada)
                    if ant_total_min > 0:
                        dt_disparo = dt_evento - timedelta(minutes=ant_total_min)
                        if (dt_disparo.strftime("%Y-%m-%d") == fecha_hoy
                                and dt_disparo.strftime("%H:%M") == hora_hoy):
                            clave_vac = f"VAC_ANT_{vac['titulo']}_{vac['fecha_inicio']}_{fecha_hoy}_{hora_hoy}"
                            if clave_vac not in mostrados:
                                aviso_vac = {
                                    "titulo":    f"🏖 Vacaciones próximas: {vac['titulo']}",
                                    "mensaje":   f"Inicio: {_iso_a_ui(vac['fecha_inicio'])} → {_iso_a_ui(vac['fecha_fin'])}",
                                    "antelacion": ant,
                                    "_tipo_popup": "vacaciones",
                                    "_permite_correo": True,
                                    "_vac_ref": vac,
                                }
                                mostrar_alerta(aviso_vac)
                                mostrados.add(clave_vac)
                    # Aviso el propio dia de inicio a las 09:00
                    if (dt_evento.strftime("%Y-%m-%d") == fecha_hoy
                            and dt_evento.strftime("%H:%M") == hora_hoy):
                        clave_vac_hoy = f"VAC_HOY_{vac['titulo']}_{vac['fecha_inicio']}_{fecha_hoy}"
                        if clave_vac_hoy not in mostrados:
                            aviso_vac_hoy = {
                                "titulo":  f"🏖 ¡Hoy comienzan las vacaciones! {vac['titulo']}",
                                "mensaje": f"Periodo: {_iso_a_ui(vac['fecha_inicio'])} → {_iso_a_ui(vac['fecha_fin'])}",
                                "_tipo_popup": "vacaciones",
                                "_permite_correo": True,
                                "_vac_ref": vac,
                            }
                            mostrar_alerta(aviso_vac_hoy)
                            mostrados.add(clave_vac_hoy)
                except Exception:  # noqa: BLE001
                    import sys as _sys, traceback as _tb
                    print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)

            # ── Avisos de festivos: antelacion + aviso el dia del evento ──
            for fest in data.get("festivos", []):
                ant = fest.get("antelacion", {})
                ant_d = int(ant.get("dias", 0))
                ant_h = int(ant.get("horas", 0))
                ant_m = int(ant.get("minutos", 0))
                ant_total_min = ant_d * 1440 + ant_h * 60 + ant_m
                try:
                    dt_ini = datetime.strptime(fest["fecha"], "%Y-%m-%d")
                    dt_evento = dt_ini.replace(hour=9, minute=0, second=0)
                    # Aviso anticipado (solo si hay antelacion configurada)
                    if ant_total_min > 0:
                        dt_disparo = dt_evento - timedelta(minutes=ant_total_min)
                        if (dt_disparo.strftime("%Y-%m-%d") == fecha_hoy
                                and dt_disparo.strftime("%H:%M") == hora_hoy):
                            clave_fest = f"FEST_ANT_{fest['titulo']}_{fest['fecha']}_{fecha_hoy}_{hora_hoy}"
                            if clave_fest not in mostrados:
                                aviso_fest = {
                                    "titulo":    f"🎉 Festivo próximo: {fest['titulo']}",
                                    "mensaje":   f"Fecha: {_iso_a_ui(fest['fecha'])}",
                                    "antelacion": ant,
                                    "_tipo_popup": "festivo",
                                    "_permite_correo": True,
                                    "_fest_ref": fest,
                                }
                                mostrar_alerta(aviso_fest)
                                mostrados.add(clave_fest)
                    # Aviso el propio dia del festivo a las 09:00
                    if (dt_evento.strftime("%Y-%m-%d") == fecha_hoy
                            and dt_evento.strftime("%H:%M") == hora_hoy):
                        clave_fest_hoy = f"FEST_HOY_{fest['titulo']}_{fest['fecha']}_{fecha_hoy}"
                        if clave_fest_hoy not in mostrados:
                            aviso_fest_hoy = {
                                "titulo":  f"🎉 ¡Hoy es festivo! {fest['titulo']}",
                                "mensaje": f"Fecha: {_iso_a_ui(fest['fecha'])}",
                                "_tipo_popup": "festivo",
                                "_permite_correo": True,
                                "_fest_ref": fest,
                            }
                            mostrar_alerta(aviso_fest_hoy)
                            mostrados.add(clave_fest_hoy)
                except Exception:  # noqa: BLE001
                    import sys as _sys, traceback as _tb
                    print(f"[WARNING] {_tb.format_exc().splitlines()[-1]}", file=_sys.stderr)

        except Exception:  # noqa: BLE001
            import traceback as _tb
            _log.error("ERROR en ciclo #%d del monitor:\n%s", ciclo, _tb.format_exc())

        # Dormir hasta el inicio del próximo minuto (± ~0,1 s de margen)
        # ANTI-REGRESION (bug Fase 3.7d): si estamos en los primeros 5s del minuto
        # (arranque o ciclo recién sincronizado), dormimos el ciclo completo hasta :00
        # del siguiente minuto. Si estamos a mitad de minuto (arranque tardío),
        # el ciclo ya evaluó correctamente ahora.minute y dormimos el resto.
        ahora = datetime.now()
        segundos_restantes = 60 - ahora.second - ahora.microsecond / 1_000_000
        _log.debug("  durmiendo %.1f s hasta el próximo minuto", segundos_restantes)
        time.sleep(max(segundos_restantes, 1.0))


def mostrar_alerta(aviso, clave_silencio: str = None):
    """Encola un popup de aviso. El popup se muestra en el hilo principal (thread-safe)
    y siempre de uno en uno: si ya hay un popup abierto, el nuevo espera en cola.

    Parámetros
    ----------
    aviso          : dict del aviso tal como sale de la agenda / monitor.
    clave_silencio : clave HOY:... que se añade a _avisos_silenciados cuando
                     el usuario pulsa "Silenciar hoy".  Solo se pasa para
                     avisos normales con repetición o antelación.

    NOTA DE THREADING
    -----------------
    Esta función puede llamarse desde el hilo monitor (daemon thread).
    Con PyInstaller console=False, el exe corre en un hilo secundario, por lo que
    app.after() llamado aquí lanzaría:
        RuntimeError: main thread is not in main loop
    SOLUCIÓN: solo encolamos en _popup_queue (thread-safe).
    El hilo principal vacía la cola mediante el poller _poll_alertas(),
    registrado con app.after() desde main_agenda.py al arrancar.
    """
    _log.info("ENCOLAR popup '%s'  (cola_size=%d  popup_activo=%s)",
              aviso.get("titulo","?"), _popup_queue.qsize(), _popup_activo)
    _popup_queue.put((aviso, clave_silencio))
    # NO llamar app.after() aquí — se haría desde un hilo secundario con console=False
    # El poller registrado en main_agenda.py procesa la cola desde el hilo principal.


def _construir_popup(aviso, clave_silencio: str = None):
    """Construye y muestra un popup. Al cerrarse procesa el siguiente en cola."""
    _log.info("CONSTRUIR popup '%s'", aviso.get("titulo","?"))

    tipo_popup   = aviso.get("_tipo_popup", "aviso")   # "aviso" | "vacaciones" | "festivo"
    es_vac_fest  = tipo_popup in ("vacaciones", "festivo")
    rep          = aviso.get("repeticion", "ninguna")
    es_repeticion = rep != "ninguna"

    # Antelación configurada
    ant   = aviso.get("antelacion", {})
    ant_d = int(ant.get("dias", 0))
    ant_h = int(ant.get("horas", 0))
    ant_m = int(ant.get("minutos", 0))
    tiene_antelacion = bool(ant_d or ant_h or ant_m)

    # ── Ancho del popup fijo; el alto se autoajusta al contenido real ──────
    # ANTI-REGRESION (bug reportado 2026-07): la fórmula fija anterior
    # (_ph = 270 + lineas_extra*42) no tenía en cuenta el número real de
    # líneas del mensaje (avisos bridge/push con varios campos podían
    # generar 6-8 líneas), dejando el botón "Entendido" fuera de la
    # ventana al ser resizable(False, False). Ahora se calcula el alto
    # real tras construir todos los widgets, con winfo_reqheight().
    _pw = 460

    pop = ttk.Toplevel()
    pop.withdraw()  # ocultar inmediatamente para evitar ventana ciega/vacía
    pop.title("🔔 AVISO")
    pop.resizable(False, False)
    pop.attributes("-topmost", True)
    _apply_icon(pop)
    pop.geometry(f"{_pw}x100")  # alto provisional; se recalcula más abajo

    f = ttk.Frame(pop, padding=(20, 16, 20, 14))
    f.pack(fill="both", expand=True)

    # ── Título ────────────────────────────────────────────
    ttk.Label(f, text=aviso["titulo"],
              font=("Segoe UI", 12, "bold"),
              foreground=GOLD,
              wraplength=_pw - 48,
              justify="center").pack(pady=(0, 6))

    # ── Mensaje opcional ──────────────────────────────────
    if aviso.get("mensaje"):
        ttk.Label(f, text=aviso["mensaje"],
                  wraplength=_pw - 48,
                  font=("Segoe UI", 10),
                  justify="center").pack(pady=(0, 6))

    # ── Badge de antelación ───────────────────────────────
    if tiene_antelacion:
        partes = []
        if ant_d: partes.append(f"{ant_d}d")
        if ant_h: partes.append(f"{ant_h}h")
        if ant_m: partes.append(f"{ant_m}min")
        ttk.Label(f, text=f"⏰ Aviso con {' '.join(partes)} de antelación",
                  font=("Segoe UI", 8),
                  foreground=LIGHT).pack(pady=(0, 8))

    ttk.Separator(f).pack(fill="x", pady=(4, 10))

    # ── Callback al cerrar: liberar flag y procesar siguiente ─────────────
    def _on_close(silenciar=False):
        """Cierra el popup y libera la cola.
        Solo añade clave_silencio a _avisos_silenciados si silenciar=True
        (el usuario pulsó explícitamente 'Silenciar hoy' o 'No recordar hoy').
        'Entendido' y la X cierran sin silenciar: el aviso volverá en su
        próximo disparo programado (siguiente :MM para cada_hora/cada_30min).
        ANTI-REGRESION (bug Fase 3.7b corregido): el silenciado automático
        bloqueaba todos los disparos de avisos repetitivos tras el primero.
        """
        global _popup_activo
        if clave_silencio and silenciar:
            _avisos_silenciados.add(clave_silencio)
            _log.debug("_on_close: silenciado '%s'", clave_silencio)
        _popup_activo = False
        pop.destroy()
        app.after(0, _procesar_cola_popups)

    # ── Botones ───────────────────────────────────────────
    # Vacaciones / Festivos → solo correo + Entendido
    if es_vac_fest:
        permite_correo = aviso.get("_permite_correo", False)
        if permite_correo:
            # Construir evento enriquecido para el módulo de correo
            if tipo_popup == "vacaciones":
                vac_ref = aviso.get("_vac_ref", aviso)
                ev_enr = _enriquecer_evento_correo(
                    vac_ref, "VACACIONES",
                    vac_ref.get("fecha_inicio", ""), vac_ref.get("fecha_fin", "")
                )
            else:
                fest_ref = aviso.get("_fest_ref", aviso)
                ev_enr = _enriquecer_evento_correo(
                    fest_ref, "FESTIVO", fest_ref.get("fecha", "")
                )
            btn_row = ttk.Frame(f)
            btn_row.pack(fill="x")
            ttk.Button(
                btn_row,
                text="  ✉  Enviar correo  ",
                bootstyle="info-outline",
                command=lambda e=ev_enr: (_abrir_ventana_correo(e, parent=pop))
            ).pack(side="left", padx=(0, 8))
            ttk.Button(btn_row, text="  ✔  Entendido  ",
                       bootstyle="warning",
                       command=_on_close).pack(side="left")
        else:
            ttk.Button(f, text="  ✔  Entendido  ",
                       bootstyle="warning", command=_on_close).pack()

    # Avisos normales → botones de cancelación inteligentes
    else:
        # Avisos gestionados por el bridge de Control de Pedidos:
        # solo se pueden eliminar desde el origen; no se ofrece cancelación local.
        if aviso.get("_bridge_gestionado"):
            ttk.Button(f, text="  ✔  Entendido  ",
                       bootstyle="warning",
                       command=_on_close).pack(anchor="e")
        else:
            # ── Fila superior: Silenciar hoy / Desactivar evento ──
            cancel_row = ttk.Frame(f)
            cancel_row.pack(fill="x", pady=(0, 6))

            def _silenciar_hoy():
                """Silencia el aviso para hoy y cierra el popup."""
                _on_close(silenciar=True)  # ANTI-REGRESION: _on_close ya gestiona el add a _avisos_silenciados

            def _desactivar_evento():
                """Marca el aviso como inactivo en el JSON → ya no disparará más."""
                titulo_aviso = aviso.get("titulo", "")
                hora_aviso   = aviso.get("hora", "")
                data = load_agenda()
                for a in data.get("avisos", []):
                    if a.get("titulo") == titulo_aviso and a.get("hora") == hora_aviso:
                        a["activo"] = False
                        break
                save_agenda(data)
                # Recargar en memoria
                agenda_data.clear()
                agenda_data.update(data)
                # ANTI-REGRESION (Fase 3.7g): refrescar lista visible si la ventana Agenda está abierta
                if callable(on_agenda_changed):
                    app.after(0, on_agenda_changed)
                _on_close()

            # Etiqueta del botón de silencio según el contexto
            if es_repeticion:
                lbl_silencio = "⏸  Silenciar hoy"
            elif tiene_antelacion:
                lbl_silencio = "⏭  No recordar hoy"
            else:
                lbl_silencio = None  # aviso de disparo único sin repetición → no tiene sentido silenciar

            if lbl_silencio:
                ttk.Button(
                    cancel_row,
                    text=f"  {lbl_silencio}  ",
                    bootstyle="secondary-outline",
                    command=_silenciar_hoy
                ).pack(side="left", padx=(0, 8), fill="x", expand=True)

            ttk.Button(
                cancel_row,
                text="  🚫  Desactivar evento  ",
                bootstyle="danger-outline",
                command=_desactivar_evento
            ).pack(side="left", fill="x", expand=True)

            # ── Fila inferior: Entendido (cierra sin silenciar — el aviso volverá en su próximo disparo) ──
            # ANTI-REGRESION (bug Fase 3.7b corregido): NO silenciar aquí;
            # el usuario usa 'Silenciar hoy' si quiere suprimir todos los avisos del día.
            ttk.Button(f, text="  ✔  Entendido  ",
                       bootstyle="warning",
                       command=_on_close).pack(anchor="e")

    # ── Cierre con la X de la ventana también libera la cola ─────────────
    pop.protocol("WM_DELETE_WINDOW", _on_close)

    # ── Mostrar ahora que todo está construido + sonido ───────────────────
    # Recalcular alto real según contenido (título/mensaje largos, badge,
    # filas de botones) y luego centrar en pantalla con ese alto definitivo.
    pop.update_idletasks()
    _ph = f.winfo_reqheight() + 32          # + margen del padding del Toplevel
    _ph_min, _ph_max_ratio = 220, 0.85      # alto mínimo y tope (% pantalla)
    _sw = pop.winfo_screenwidth()
    _sh = pop.winfo_screenheight()
    _ph = max(_ph_min, min(_ph, int(_sh * _ph_max_ratio)))
    pop.geometry(f"{_pw}x{_ph}+{(_sw - _pw)//2}+{(_sh - _ph)//2}")
    pop.update_idletasks()
    pop.deiconify()
    pop.lift()          # traer al frente sobre la ventana principal
    pop.focus_force()   # forzar foco para evitar popup ciego/invisible
    pop.grab_set()      # ANTI-REGRESION: existía en v4.4.0 — sin esto el popup no recibe
                        # eventos si hay otra ventana con grab activo (ej: abrir_agenda)
    _reproducir_sonido_aviso(tipo_popup)

    # ── Auto-cierre si el usuario no está presente ─────────────────────────
    # Un popup de un aviso CON repetición que nadie cierra se queda abierto
    # (grab_set incluido) hasta el próximo disparo de ESE MISMO aviso, y con
    # _popup_activo=True bloquea además la cola de popups de cualquier otro
    # aviso mientras tanto. Para que dos disparos de la misma cosa nunca se
    # solapen, se cierra solo — sin silenciar, como si el usuario hubiera
    # pulsado "Entendido" — pasada la MITAD del intervalo de repetición:
    # cada 30 min → se cierra a los 15 min; cada hora → a los 30 min;
    # diario/semanal/mensual, proporcionalmente igual. Los avisos de disparo
    # único ("ninguna") no tienen próxima ocurrencia con la que solaparse,
    # así que se dejan abiertos indefinidamente, como hasta ahora — EXCEPTO
    # los que vienen de Control de Pedidos (2026-07-24): esos siempre traen
    # repeticion="ninguna" (su propio recordatorio lo gestiona el bridge, no
    # este mecanismo), pero igualmente pueden quedarse abiertos indefinida-
    # mente si nadie está delante, bloqueando el resto de la cola. Para esos
    # se fuerza un tope fijo de 10 min (v4.18.04; antes 30), se marquen o no con repetición.
    _INTERVALO_REPETICION_MIN = {
        "cada_30min": 30,
        "cada_hora":  60,
        "diario":     1440,
        "semanal":    1440 * 7,
        "mensual":    1440 * 30,   # aproximado (mes ≈ 30 días)
        "anual":      1440 * 365,
    }
    _AUTOCIERRE_BRIDGE_MIN = 10  # popups de Control de Pedidos (pedidos_agenda_bridge.py); v4.18.04: 30 → 10 min

    if aviso.get("_bridge_gestionado"):
        _autocierre_ms = _AUTOCIERRE_BRIDGE_MIN * 60 * 1000
    else:
        _intervalo_min = _INTERVALO_REPETICION_MIN.get(rep)
        _autocierre_ms = int(_intervalo_min * 60 * 1000 / 2) if _intervalo_min else None

    if _autocierre_ms:
        def _autocierre():
            if pop.winfo_exists():
                _log.info("Auto-cierre popup '%s' tras %d min sin respuesta (rep=%s, bridge=%s)",
                           aviso.get("titulo", "?"), _autocierre_ms // 60000, rep,
                           bool(aviso.get("_bridge_gestionado")))
                _on_close(silenciar=False)

        pop.after(_autocierre_ms, _autocierre)
