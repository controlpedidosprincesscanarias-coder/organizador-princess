"""
app/context.py
Contenedor central de dependencias compartidas entre módulos UI.

En lugar de importar globals directamente desde main_agenda,
todos los módulos UI reciben un AppContext con todo lo que necesitan.

Uso:
    # En main_agenda.py, tras crear app y cargar datos:
    from context import AppContext
    ctx = AppContext(app, config, agenda_data, save_config, save_agenda, NOMBRE_USUARIO_ACTUAL)

    # En cada módulo UI:
    from ui.saludo import mostrar_saludo_diario
    mostrar_saludo_diario(ctx)
"""


class AppContext:
    """
    Contenedor inmutable de dependencias de la aplicación.
    Se crea una sola vez en main_agenda.py y se pasa a todos los módulos.
    """
    __slots__ = (
        'app',               # ttk.Window — ventana raíz Tkinter
        'config',            # dict mutable — configuración persistida en JSON
        'agenda_data',       # dict mutable — datos de agenda en memoria
        'save_config',       # callable(config) — persiste config
        'save_agenda',       # callable(agenda_data) — persiste agenda
        'nombre_usuario',    # str — nombre real del usuario actual
        'apply_icon',        # callable(win) — aplica icono a ventana Tk
        'get_crown_tk',      # callable(size) — devuelve PhotoImage de corona
        'btn_labels',        # dict — StringVar de botones del grid
        'btn_widgets',       # dict — widgets de botones del grid
        'ar_labels',         # dict — StringVar de accesos rápidos
        'ar_widgets',        # dict — widgets de accesos rápidos
        'app_version',       # str — versión de la aplicación (v4.18.08)
        'aplicar_vista',     # callable() — recoloca el menú tras cambiar la vista (v4.18.08)
    )

    def __init__(self,
                 app,
                 config,
                 agenda_data,
                 save_config,
                 save_agenda,
                 nombre_usuario,
                 apply_icon=None,
                 get_crown_tk=None,
                 btn_labels=None,
                 btn_widgets=None,
                 ar_labels=None,
                 ar_widgets=None,
                 app_version="",
                 aplicar_vista=None):
        self.app           = app
        self.config        = config
        self.agenda_data   = agenda_data
        self.save_config   = save_config
        self.save_agenda   = save_agenda
        self.nombre_usuario = nombre_usuario
        self.apply_icon    = apply_icon    or (lambda win: None)
        self.get_crown_tk  = get_crown_tk  or (lambda size=40: None)
        self.btn_labels    = btn_labels    if btn_labels    is not None else {}  # ANTI-REGRESIÓN: "or {}" rompía la referencia cuando el dict se pasaba vacío (Fase 3.7)
        self.btn_widgets   = btn_widgets   if btn_widgets   is not None else {}  # ANTI-REGRESIÓN: idem
        self.ar_labels     = ar_labels     if ar_labels     is not None else {}  # ANTI-REGRESIÓN: idem
        self.ar_widgets    = ar_widgets    if ar_widgets    is not None else {}  # ANTI-REGRESIÓN: idem
        self.app_version   = app_version
        self.aplicar_vista = aplicar_vista or (lambda: None)   # main_agenda la fija al definirla

    def refresh_agenda(self):
        """Recarga agenda desde disco y actualiza el contexto en memoria."""
        from db.sqlite import load_agenda
        self.agenda_data.clear()
        self.agenda_data.update(load_agenda())

    def refresh_config(self):
        """Recarga config desde disco y actualiza el contexto en memoria."""
        from db.sqlite import load_config
        self.config.clear()
        self.config.update(load_config())
