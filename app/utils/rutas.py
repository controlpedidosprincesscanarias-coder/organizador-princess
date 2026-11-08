"""
utils/rutas.py
Lanzamiento de rutas (carpeta de red, web, ejecutable) con validación y mensajes de error.
Extraído de main_agenda.py — compartido entre main_agenda y ui/ventana_config.
"""
import os
from tkinter import messagebox


def _lanzar_ruta(ruta, tipo):
    """Lanza una ruta según su tipo, con validación y mensajes de error elegantes."""
    import webbrowser

    if tipo == "web":
        ruta_limpia = ruta.strip()
        if not ruta_limpia:
            messagebox.showerror(
                "Dirección web no definida",
                "⚠️  No se ha configurado ninguna dirección web para este acceso.\n\n"
                "Por favor, edite el botón desde el panel de Administración\n"
                "e introduzca una URL válida (por ejemplo: https://www.ejemplo.com).",
            )
            return
        if not (ruta_limpia.startswith("http://") or ruta_limpia.startswith("https://")
                or ruta_limpia.startswith("ftp://") or ruta_limpia.startswith("file://")):
            messagebox.showerror(
                "URL no válida",
                f"⚠️  La dirección configurada no parece una URL válida:\n\n"
                f"    {ruta_limpia}\n\n"
                "Las direcciones web deben comenzar por  https://  o  http://\n"
                "Edite el botón desde el panel de Administración para corregirlo.",
            )
            return
        try:
            webbrowser.open(ruta_limpia)
        except Exception as e:
            messagebox.showerror(
                "Error al abrir la página web",
                f"⚠️  No se pudo abrir la dirección web:\n\n"
                f"    {ruta_limpia}\n\n"
                f"Detalle del error:  {e}\n\n"
                "Compruebe que dispone de conexión a Internet y que\n"
                "el navegador predeterminado está correctamente configurado.",
            )
    else:
        ruta_limpia = ruta.strip()
        if not ruta_limpia:
            messagebox.showerror(
                "Ruta no definida",
                "⚠️  No se ha configurado ninguna ruta para este acceso.\n\n"
                "Por favor, edite el botón desde el panel de Administración\n"
                "e introduzca la ruta correcta.",
            )
            return
        ruta_norm = os.path.normpath(ruta_limpia)
        if not os.path.exists(ruta_norm):
            if tipo == "carpeta":
                detalle = (
                    "La carpeta de red especificada no está disponible en este momento.\n\n"
                    "Posibles causas:\n"
                    "  • El servidor de red no es accesible desde este equipo.\n"
                    "  • La ruta de red ha cambiado o fue eliminada.\n"
                    "  • No tiene permisos suficientes para acceder a esa ubicación.\n\n"
                    "Compruebe la conectividad de red o contacte con el administrador\n"
                    "de sistemas para verificar la ruta."
                )
            else:
                detalle = (
                    "El archivo o ejecutable especificado no existe en la ruta indicada.\n\n"
                    "Posibles causas:\n"
                    "  • El programa fue desinstalado o movido a otra ubicación.\n"
                    "  • La ruta configurada contiene un error tipográfico.\n"
                    "  • El archivo se encuentra en una unidad de red no disponible.\n\n"
                    "Edite el botón desde el panel de Administración\n"
                    "para actualizar la ruta al archivo correcto."
                )
            messagebox.showerror(
                "Ruta no encontrada",
                f"⚠️  No se puede acceder a la ruta configurada:\n\n"
                f"    {ruta_limpia}\n\n"
                f"{detalle}",
            )
            return
        try:
            os.startfile(ruta_norm)
        except OSError as e:
            messagebox.showerror(
                "Error al abrir el recurso",
                f"⚠️  La ruta existe pero no se pudo abrir:\n\n"
                f"    {ruta_limpia}\n\n"
                f"Detalle del error:  {e}\n\n"
                "Es posible que no tenga permisos de ejecución o que el archivo\n"
                "esté dañado. Contacte con el administrador si el problema persiste.",
            )
