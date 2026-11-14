"""
app/ui/importexport.py
Exportar e importar config y agenda via diálogos de archivo.
Extraído de main_agenda.py en Fase 3B.

Todas las dependencias llegan via AppContext (ctx).
"""
import os
import json
import shutil
from tkinter import filedialog, messagebox

from db.sqlite import CONFIG_FILE, AGENDA_FILE


def exportar_config(ctx, parent_win=None):
    """Copia config.json a la ruta que elija el usuario."""
    dst = filedialog.asksaveasfilename(
        title="Exportar configuración",
        initialfile="OrganizadorPrincess_config.json",
        defaultextension=".json",
        filetypes=[("JSON", "*.json"), ("Todos los archivos", "*.*")],
        parent=parent_win,
    )
    if not dst:
        return
    try:
        shutil.copy2(CONFIG_FILE, dst)
        messagebox.showinfo(
            "Exportar configuración",
            f"Configuración exportada correctamente en:\n\n{dst}",
            parent=parent_win,
        )
    except Exception as exc:
        messagebox.showerror("Error al exportar", str(exc), parent=parent_win)


def importar_config(ctx, parent_win=None):
    """Reemplaza config.json con uno externo y cierra la app limpiamente."""
    src = filedialog.askopenfilename(
        title="Importar configuración",
        filetypes=[("JSON", "*.json"), ("Todos los archivos", "*.*")],
        parent=parent_win,
    )
    if not src:
        return
    try:
        with open(src, "r", encoding="utf-8") as f:
            json.load(f)
    except Exception as exc:
        messagebox.showerror(
            "Archivo inválido",
            f"El archivo no contiene un JSON válido:\n\n{exc}",
            parent=parent_win,
        )
        return
    ok = messagebox.askyesno(
        "Importar configuración",
        "Se reemplazará la configuración actual con la del archivo seleccionado.\n\n"
        "La aplicación se cerrará. Vuelva a abrirla para que los cambios surtan efecto.\n\n"
        "¿Continuar?",
        icon="warning",
        parent=parent_win,
    )
    if not ok:
        return
    try:
        shutil.copy2(src, CONFIG_FILE)
        if parent_win:
            try:
                parent_win.destroy()
            except Exception:
                pass  # UI — ignorar silenciosamente
        messagebox.showinfo(
            "Configuración importada",
            "La configuración se ha copiado correctamente.\n\n"
            "La aplicación se cerrará ahora.\n"
            "Vuelva a abrirla para que los cambios surtan efecto.",
        )
        try:
            from pedidos_agenda_bridge import detener_bridge
            detener_bridge()
        except Exception:
            pass  # UI — ignorar silenciosamente
        ctx.app.destroy()
    except Exception as exc:
        messagebox.showerror("Error al importar", str(exc), parent=parent_win)


def exportar_agenda(ctx, parent_win=None):
    """Copia agenda.json a la ruta que elija el usuario."""
    if not os.path.exists(AGENDA_FILE):
        messagebox.showwarning(
            "Sin agenda",
            "No existe ningún archivo de agenda que exportar.\n\n"
            "La agenda está vacía o aún no se ha guardado ningún evento.",
            parent=parent_win,
        )
        return
    dst = filedialog.asksaveasfilename(
        title="Exportar agenda",
        initialfile="OrganizadorPrincess_agenda.json",
        defaultextension=".json",
        filetypes=[("JSON", "*.json"), ("Todos los archivos", "*.*")],
        parent=parent_win,
    )
    if not dst:
        return
    try:
        shutil.copy2(AGENDA_FILE, dst)
        messagebox.showinfo(
            "Exportar agenda",
            f"Agenda exportada correctamente en:\n\n{dst}",
            parent=parent_win,
        )
    except Exception as exc:
        messagebox.showerror("Error al exportar", str(exc), parent=parent_win)


def importar_agenda(ctx, parent_win=None):
    """Reemplaza agenda.json con una copia externa y recarga los datos en memoria."""
    src = filedialog.askopenfilename(
        title="Importar agenda (copia de seguridad)",
        filetypes=[("JSON", "*.json"), ("Todos los archivos", "*.*")],
        parent=parent_win,
    )
    if not src:
        return
    try:
        with open(src, "r", encoding="utf-8") as f:
            datos = json.load(f)
    except Exception as exc:
        messagebox.showerror(
            "Archivo inválido",
            f"El archivo no contiene un JSON válido:\n\n{exc}",
            parent=parent_win,
        )
        return
    ok = messagebox.askyesno(
        "Importar agenda",
        "Se reemplazará la agenda actual con la del archivo seleccionado.\n\n"
        "⚠️  Los eventos, vacaciones y festivos actuales se perderán, también en tus otros equipos "
        "con el mismo usuario de Control de Pedidos.\n\n"
        "¿Continuar?",
        icon="warning",
        parent=parent_win,
    )
    if not ok:
        return
    try:
        # (v4.18.66) Con la agenda sincronizada, lo importado reemplaza también la de los otros PC de este
        # usuario: se sube como cambio nuevo y lo que no está en el archivo se borra (services/sincro_agenda.py).
        # Por eso ya no se copia el archivo tal cual, sino que se guarda con save_agenda.
        from services import sincro_agenda
        if not isinstance(datos, dict):
            raise ValueError("El archivo no tiene el formato de una agenda del Organizador.")
        with sincro_agenda.CERROJO:
            datos = sincro_agenda.preparar_importacion(datos, ctx.agenda_data)
            ctx.agenda_data.clear()
            ctx.agenda_data.update(datos)
            ctx.save_agenda(ctx.agenda_data)
            sincro_agenda.refrescar_ventanas()
        messagebox.showinfo(
            "Agenda importada",
            "✅  La agenda se ha restaurado correctamente.\n\n"
            "Los cambios ya están activos — no es necesario reiniciar la aplicación.",
            parent=parent_win,
        )
    except Exception as exc:
        messagebox.showerror("Error al importar", str(exc), parent=parent_win)
