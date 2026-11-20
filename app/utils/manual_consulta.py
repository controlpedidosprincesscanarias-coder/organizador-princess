"""
utils/manual_consulta.py — contenido y búsqueda del manual consultable del botón «📖 Manual» (v4.18.76).

La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.

Petición de Víctor (20 nov 2026): «que el botón manual del organizador funcione como el del chat móvil, que al
pulsar se pueda realizar consultas y también descargar el manual completo». Como Ajustes → 📖 Manual de uso del
móvil (datos/Manual.kt): apartados que se abren y cierran, un buscador que no distingue tildes ni mayúsculas y,
al final, el manual completo en PDF (abrirlo o guardar una copia). Funciona sin conexión.

El texto resume el Manual de usuario (docs/manuales_fuente/manual_usuario.js). Si cambia una pantalla, cambiar
también aquí. Sin tkinter: la ventana está en ui/manual.py. Pruebas en test_manual_consulta.py.
"""
import re
import unicodedata

# (icono, título, líneas)
APARTADOS = [
    ("👋", "Qué es el Organizador", [
        "El escritorio de trabajo de la Central de Compras: botones para abrir con un clic carpetas, webs y "
        "programas, una agenda de avisos, un calendario con vacaciones y festivos y un chat con los compañeros.",
        "La agenda, las vacaciones y los festivos van con tu usuario de Control de Pedidos: los ves en cualquier PC "
        "donde entres con él. Los botones son de cada PC.",
        "El chat y los avisos de pedidos necesitan tu cuenta de Control de Pedidos, guardada en Admin → Mi Usuario.",
    ]),
    ("🖥", "La pantalla principal", [
        "Arriba, el saludo con tu nombre. Si no lo has puesto, se usa el de tu cuenta de Control de Pedidos; se "
        "cambia en Admin → Mi Usuario.",
        "Admin: panel de administración (botones, vista, tu usuario, sonidos del chat y copias). Pide tu contraseña "
        "de Control de Pedidos.",
        "Manual: esta ventana. Accesos rápidos (dorados): seis botones para lo que más usas.",
        "Agenda, Calendario y Chat: los tres botones de trabajo diario. Botones azules: hasta 30 accesos.",
        "Abajo a la derecha, la versión: al pulsarla se ven sus novedades.",
    ]),
    ("📂", "Abrir un acceso y submenús", [
        "Pulsa el botón: se abre la carpeta de red, la página web, el programa o el documento que tenga configurado.",
        "Si tiene submenú (▶ junto al nombre), se abre una ventana pequeña con sus subopciones.",
        "Un botón «POR DEFINIR» está sin configurar: al pulsarlo se abre la ventana para configurarlo.",
    ]),
    ("🔲", "Vista extendida y reducida", [
        "La extendida muestra todo; la reducida es una ventana más pequeña con los 4 primeros accesos dorados y "
        "hasta 10 botones azules.",
        "Se cambia en Admin → Vista y se aplica al guardar. Los botones que no se ven siguen configurados.",
    ]),
    ("📝", "Agenda de avisos", [
        "Agenda («Mis Recordatorios»): avisos únicos y repetitivos, cada uno con su hora, cuándo salta, cuánto falta "
        "y la antelación.",
        "+ Añadir Aviso: título, repetición, fecha (escrita o con el calendario 📅), hora, mensaje y antelación.",
        "Repetición: sin repetición, cada 30 minutos, cada hora, diaria, semanal, mensual o anual.",
        "✏ edita, 🗑 borra y ▶ reactiva un aviso desactivado.",
        "Deja el Organizador abierto: un aviso sin antelación salta justo a su hora.",
    ]),
    ("📅", "Calendario, vacaciones y festivos", [
        "El mes o la semana con tus avisos (azul y cian), vacaciones (verde) y festivos (rojo); hoy en dorado.",
        "Pulsa un día para ver su detalle. «Hoy» vuelve al mes actual.",
        "Imprimir: Agenda del Día, Semanal o Mensual (se abre lista para imprimir en el navegador).",
        "Vacaciones y Festivos: + Nuevo Periodo / + Nuevo Festivo, con la antelación del aviso.",
    ]),
    ("🔔", "Avisos emergentes", [
        "A la hora de un aviso sale una ventana en el centro de la pantalla, con sonido.",
        "Silenciar hoy (repetitivos) o No recordar hoy (con antelación) lo callan hasta mañana.",
        "Desactivar evento lo pone en pausa en la Agenda. Entendido cierra la ventana.",
        "Vacaciones y festivos: «Enviar correo» prepara el correo de aviso con el asunto y el texto.",
        "Avisos de tus pedidos: cambios de estado y pedidos sin avance de Control de Pedidos; se cierran con Entendido.",
    ]),
    ("🌐", "El Organizador y Control de Pedidos en el mismo PC", [
        "La primera vez en cada PC y navegador, pulsa «🖥️ Abrir el Organizador» en el aviso de la web y permite que "
        "el navegador lo abra: quedan vinculados.",
        "Desde entonces, la web solo avisa si en ese PC no tienes el Organizador abierto.",
    ]),
    ("💬", "Chat: conversaciones y mensajes", [
        "Botón Chat del menú. Hace falta tu cuenta guardada en Admin → Mi Usuario.",
        "A la izquierda, el canal General, tus chats privados y los grupos; el número son los mensajes sin leer.",
        "Escribe abajo y pulsa Intro o Enviar. 😊 emoticonos y respuestas rápidas; 📎 adjuntar.",
        "Nueva conversación: un compañero → chat privado; dos o más (con Ctrl) → un grupo.",
        "Pulsa la foto o el nombre de un grupo para ver sus integrantes, añadir, quitar o salir.",
    ]),
    ("↩️", "Responder, reenviar, copiar y eliminar", [
        "Clic derecho sobre un mensaje: ↩ Responder, ↪ Reenviar…, Copiar o 🗑 Eliminar (solo los tuyos).",
        "Doble clic copia el mensaje.",
        "⋮ → 🧹 Vaciar chat (solo para ti) y, en los privados, 🗑 Eliminar chat.",
    ]),
    ("🔊", "Sonido de los mensajes", [
        "Puedes elegir un sonido general y otro distinto para cada chat o grupo, o dejar alguno en silencio.",
        "En la ventana del chat, ⋮ → 🔔 Sonido de este chat…; en la burbuja, el botón 🔔.",
        "Todos a la vez: Admin → 🔔 Sonidos del chat.",
        "8 tonos (Clásico, Campanita, Burbuja, Ascendente, Suave, Triple toque, Gota, Timbre), un archivo .wav de "
        "tu PC o 🔕 Silencio. ▶ lo hace sonar.",
        "Se guarda solo en este PC. El móvil tiene sus propios sonidos en Ajustes.",
    ]),
    ("📎", "Enviar imágenes y documentos", [
        "📎, arrastrar archivos sobre la ventana o la burbuja, o pegarlos con Ctrl+V. Siempre pregunta antes de enviar.",
        "Hasta 10 MB por documento y 5 archivos a la vez. No se admiten programas ni archivos con macros.",
    ]),
    ("🎤", "Mensajes de voz, enlaces y vídeos", [
        "Los mensajes de voz se graban en el móvil; aquí se escuchan con un clic (otro clic los para).",
        "Los enlaces salen subrayados y se abren en el navegador. Los de TikTok, YouTube o Instagram llevan una tarjeta.",
        "Un vídeo enviado como archivo (🎬) se abre con el reproductor de Windows.",
    ]),
    ("🫧", "La burbuja flotante", [
        "Cuando te escriben aparece una burbuja abajo a la derecha, con sonido, para leer y responder sin abrir el chat.",
        "🔔 cambia el sonido de esa conversación, ✕ la cierra y ⤢ abre la ventana completa.",
    ]),
    ("📢", "Avisos de Control Pedidos en el chat", [
        "En la conversación «Control Pedidos» llegan tus avisos internos. En ella no se puede escribir.",
        "Un aviso se puede reenviar a un compañero (clic derecho → ↪ Reenviar…).",
    ]),
    ("🖼", "Fotos de perfil", [
        "🖼 Fotos → «Cambiar mi foto…» o «Quitar mi foto». En un grupo, también la foto del grupo.",
        "Quien no tiene foto sale con sus iniciales sobre un color. Se ve igual en el móvil.",
    ]),
    ("📱", "El chat en el móvil", [
        "Chat → 📱 Chat en el móvil: código QR para instalar Chat Dpto. Compras Princess en Android.",
        "Entra con tu usuario y contraseña de Control de Pedidos, acepta las notificaciones y quita el ahorro de batería.",
        "Si Play Protect avisa: Más detalles → Instalar de todas formas. Descárgala solo desde el QR o su enlace.",
        "En el móvil, el General y «Control Pedidos» van fijos arriba y debajo la última conversación usada.",
        "Sus sonidos se eligen en el propio móvil: Ajustes (el general) y ⋮ del chat → 🔔 Sonido de este chat.",
    ]),
    ("⬆️", "Actualizaciones y novedades", [
        "Al arrancar y cada 2 horas se busca una versión nueva. «Actualizar ahora» lo hace todo y se vuelve a abrir solo.",
        "Al pulsar el número de versión se ven sus novedades.",
        "Actualizar o desinstalar no borra tus datos. Para empezar de cero: Admin → ♻ Borrado completo.",
    ]),
    ("💼", "Versión portátil", [
        "Para los PC donde no se puede instalar: OrganizadorPrincess_Portatil_v….zip. Descomprímelo y abre "
        "OrganizadorPrincess.exe.",
        "La primera vez pregunta en qué carpeta guardarlo. Se actualiza sola, sin administrador.",
    ]),
    ("🛠", "Problemas frecuentes", [
        "Un botón no abre nada: comprueba la red o Internet; si sigue, la ruta puede estar mal.",
        "No salta un aviso: mira que no esté DESACTIVADO, la fecha y la hora, y que el Organizador estuviera abierto.",
        "No llegan avisos de pedidos o el chat no entra: revisa Admin → Mi Usuario.",
        "Admin pide contraseña: es la de Control de Pedidos; tras 3 fallos se bloquea 5 minutos.",
        "No me deja instalar: usa la versión portátil.",
    ]),
]


def normal(texto: str) -> str:
    """Sin tildes ni mayúsculas, para que «version» encuentre «versión»."""
    t = unicodedata.normalize("NFD", str(texto or ""))
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def buscar(consulta: str):
    """Apartados que contienen todas las palabras de la consulta (en el título o en el texto). Vacía → todos."""
    palabras = [p for p in re.split(r"\s+", normal(consulta)) if p]
    if not palabras:
        return list(APARTADOS)
    return [a for a in APARTADOS
            if all(p in normal(a[1] + " " + " ".join(a[2])) for p in palabras)]
