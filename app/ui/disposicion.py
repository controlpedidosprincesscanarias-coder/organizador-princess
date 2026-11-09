"""
ui/disposicion.py
Constantes del menú principal y lectura de la vista elegida (extendida o reducida).
Compartido por main_agenda.py (maquetación del menú) y ui/admin.py (ventana «Vista»). v4.18.08.

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.
"""
NUM_OPCIONES = 30
NUM_ACCESOS_RAPIDOS = 6
MARGEN = 44   # px aprox. 2 dedos en cada borde

# Vista del menú principal — extendida (la de siempre) o reducida (v4.18.00)
VISTA_ACCESOS_REDUCIDA = 4    # accesos dorados que se ven en la reducida (los 4 primeros)
VISTA_MAX_AZULES       = 10   # botones azules de la reducida: 2 filas x 5


def vista_actual(config):
    """(modo, [números de botones azules de la reducida]). Valores por defecto
    seguros si falta o está mal la clave "vista_menu" del config."""
    cfg = config.get("vista_menu")
    if not isinstance(cfg, dict):
        cfg = {}
    modo = "reducida" if cfg.get("modo") == "reducida" else "extendida"
    sel = []
    for v in cfg.get("reducida_opciones") or []:
        try:
            n = int(v)
        except (TypeError, ValueError):
            continue
        if 1 <= n <= NUM_OPCIONES and n not in sel:
            sel.append(n)
    sel = sorted(sel)[:VISTA_MAX_AZULES] or list(range(1, VISTA_MAX_AZULES + 1))
    return modo, sel
