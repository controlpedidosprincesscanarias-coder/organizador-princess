// Manual de usuario del Organizador Princess. Idea y desarrollo de la aplicación: Víctor Alejandro Martín Andrade.
const L = require("./lib");
const { p, vineta, pasos, h1, h2, imagen, leyenda, recuadro, tabla, portada, indice } = L;
const V = process.env.VERSION || "v4.18.34";

const s = [];
s.push(portada({ rol: "Uso diario", subtitulo: "Abre tus accesos, apunta avisos, consulta el calendario y chatea con tus compañeros",
  version: V, fecha: "Noviembre 2026", publico: "Para todas las personas de la Central de Compras que usan el Organizador en su PC con Windows" }));
s.push(indice([["1. El Organizador de un vistazo", "Qué puedes hacer y qué no"], ["2. Conoce la pantalla", "Menú principal, accesos y submenús"],
  ["3. Vista extendida y reducida", ""], ["4. Agenda de avisos", "Crear, editar, pausar y borrar avisos"],
  ["5. Calendario, vacaciones y festivos", "Mes, semana, detalle del día e impresión"], ["6. Avisos emergentes", "Agenda, vacaciones y festivos, pedidos y saludo del día"],
  ["7. Chat", "Conversaciones, grupos, adjuntos y burbuja flotante"], ["8. El chat en el móvil", "Chat Dpto. Compras Princess para Android: instalarla y actualizarla"],
  ["9. Actualizar la aplicación", ""], ["10. Problemas frecuentes", "Y referencia rápida"]]));

// 1
s.push(h1("1. El Organizador de un vistazo"));
s.push(p("**Organizador Princess** es el escritorio de trabajo de la Central de Compras: un menú de botones para abrir con un clic las carpetas, webs y programas que usas cada día, una **agenda de avisos**, un **calendario** con vacaciones y festivos y un **chat interno** con tus compañeros. Se instala en tu PC con Windows y te reconoce por tu usuario de Windows."));
s.push(p("La agenda y los botones son **de cada PC**: lo que apuntas en tu Organizador lo ves tú, no los demás. El **chat** y los **avisos de pedidos** vienen de Control de Pedidos, por eso necesitan tu cuenta (capítulos 6 y 7)."));
s.push(h2("Qué puedes hacer"));
for (const t of ["Abrir con un clic **carpetas de red, páginas web, programas y documentos**.",
  "Apuntar **avisos** únicos o repetidos (cada 30 minutos, cada hora, a diario, cada semana, cada mes o cada año), con aviso previo si quieres.",
  "Consultar el **calendario** con tus avisos, vacaciones y festivos, e **imprimir** la agenda del día, la semana o el mes.",
  "Preparar el **correo de aviso** de vacaciones o de cierre por festivo.",
  "Recibir los **avisos de tus pedidos** de Control de Pedidos.",
  "**Chatear** con compañeros, crear grupos y enviar imágenes y documentos, también desde el **móvil** con Chat Dpto. Compras Princess (capítulo 8)."]) s.push(vineta(t));
s.push(h2("Qué no se hace aquí"));
for (const t of ["Cambiar los botones, su orden o la vista del menú: se hace en el panel **Admin** (Manual de administrador).",
  "Ver la agenda de otro compañero: cada agenda es local de su PC.",
  "Borrar mensajes del chat para los demás: «Limpiar chat» solo oculta el historial en tu equipo.",
  "Usarlo en el móvil o en un Mac: el Organizador es una aplicación de Windows."]) s.push(vineta(t));
s.push(...recuadro("nota", "Si algo no cuadra", ["Si un botón no abre lo que debería, la ruta puede estar mal o no tienes acceso a esa carpeta: avisa a quien administra el Organizador de tu equipo (capítulo 9)."]));

// 2
s.push(h1("2. Conoce la pantalla"));
s.push(p("Al abrir el Organizador ves el **Menú Principal**. Así es la vista completa (la extendida, capítulo 3). Los nombres de los botones son un ejemplo: en tu PC pueden ser otros."));
s.push(...imagen("u_menu", 17, "Menú Principal, vista extendida (datos de ejemplo)."));
s.push(...leyenda([[1, "**Cabecera**: «Menú Principal», el nombre del centro y un saludo con tu nombre. Si aún no lo has puesto, verás en amarillo «Configura tu nombre en Admin → Mi Usuario»."],
  [2, "**Admin**: panel de administración del menú (botones, vista, tu usuario y copias). Pide tu contraseña de Control de Pedidos; lo explica el Manual de administrador."],
  [3, "**Manual**: abre este manual en PDF."],
  [4, "**Accesos rápidos** (dorados): seis botones para lo que más usas. Los nombres largos se cortan, así que conviene ponerles nombres cortos."],
  [5, "**Agenda**, **Calendario** y **Chat**: los tres botones de trabajo diario (capítulos 4, 5 y 7)."],
  [6, "**Botones del menú** (azules): hasta 30 accesos en 6 columnas. Al pasar el ratón por encima cambian de color."],
  [7, "**Versión** instalada."]]));
s.push(h2("Abrir un acceso"));
s.push(p("Pulsa el botón. Según cómo esté configurado, se abre una **carpeta de red** en el Explorador, una **página web** en tu navegador, o un **programa o documento** (un Excel, un PDF, un .exe…)."));
s.push(...imagen("u_submenu", 13, "Un botón con submenú abre una ventana con sus subopciones."));
for (const t of ["Si el botón tiene **submenú**, se abre una ventana pequeña con sus subopciones (hasta 10): pulsa la que necesites y se abre igual que un botón normal.",
  "Si el botón está sin configurar (**«POR DEFINIR»**), al pulsarlo se abre la ventana para configurarlo (nombre, tipo de enlace y ruta)."]) s.push(vineta(t));

// 3
s.push(h1("3. Vista extendida y reducida"));
s.push(p("El menú tiene dos vistas. La **extendida** es la de siempre; la **reducida** es una ventana más pequeña con lo imprescindible, pensada para dejarla a un lado de la pantalla. Se cambia en **Admin → Vista** (Manual de administrador) y se aplica al guardar, sin reiniciar."));
s.push(...imagen("u_vista_reducida", 17, "Vista reducida con 10 botones azules marcados."));
s.push(...tabla(["", "Extendida", "Reducida"], [["Cabecera", "Completa", "Logo y cabecera"], ["Accesos dorados", "Los 6", "Los 4 primeros"],
  ["Agenda / Calendario / Chat", "Sí", "Sí"], ["Botones azules", "Los 30", "Hasta 10, en 2 filas de 5, en su orden numérico"], ["Tamaño de la ventana", "Grande", "Más pequeña"]], [3200, 3200, 3238]));
s.push(...recuadro("consejo", "Los botones que no ves no desaparecen", ["En la vista reducida solo se ocultan: siguen configurados y vuelven a aparecer al pasar a la vista extendida."]));

// 4
s.push(h1("4. Agenda de avisos"));
s.push(p("La **Agenda** («Mis Recordatorios») es tu lista de avisos. Cada uno muestra su fecha u horario, la antelación (⏰) y el título, y a la derecha su repetición."));
s.push(...imagen("u_agenda", 16, "Agenda de avisos (datos de ejemplo)."));
s.push(...leyenda([[1, "✏ **Editar** el aviso: abre el formulario con sus datos."], [2, "🗑 **Borrar** el aviso definitivamente."],
  [3, "▶ **Reactivar** un aviso desactivado."], [4, "**DESACTIVADO**: el aviso está en pausa; aparece tachado y no saltará hasta que lo reactives."],
  [5, "**Repetición** (Diario, Semanal, Mensual…). Los avisos sin repetición no llevan etiqueta."], [6, "**+ Añadir Aviso** abre el formulario de un aviso nuevo."]]));
s.push(h2("Pausar un aviso sin perderlo"));
s.push(p("Se hace desde la propia ventana emergente del aviso, con **Desactivar evento** (capítulo 6). El aviso queda en la lista, tachado y marcado como DESACTIVADO, hasta que pulses ▶. Es la forma más cómoda de pausar un aviso repetitivo."));
s.push(h2("Crear un aviso"));
s.push(...imagen("u_aviso_nuevo", 9, "Formulario «Nuevo Aviso»."));
s.push(...leyenda([[1, "**Título** del aviso: es lo que verás en la ventana emergente."], [2, "**Repetición**: cuándo se repite (tabla siguiente)."],
  [3, "**Fecha de inicio**. Por defecto, hoy. Se puede escribir (DD-MM-AAAA; también vale 15112026 o 15/11/26)…"],
  [4, "…o elegir en el **calendario 📅** (siguiente imagen)."],
  [5, "**Hora**: dos ruedas, horas y minutos, sin escribir los dos puntos. Se cambian con las flechas, con la rueda del ratón o escribiendo el número. Las flechas de los minutos van de 5 en 5, pero se puede escribir cualquier minuto."],
  [6, "**Mensaje** (opcional): un texto de apoyo que sale en el aviso."],
  [7, "**Avisar con antelación**: días, horas y minutos antes de la hora del aviso."], [8, "**Guardar** crea el aviso; **Cancelar** descarta los cambios."]]));
s.push(...imagen("u_selector_fecha", 6, "Calendario para elegir la fecha."));
s.push(...leyenda([[1, "**◀** mes anterior."], [2, "**▶** mes siguiente (también con Re Pág / Av Pág)."],
  [3, "**Hoy**, en dorado; la fecha que ya estaba elegida, en azul. Un clic en un día lo elige y cierra el calendario."],
  [4, "**Hoy** elige la fecha de hoy. **Cancelar** (o Esc) cierra sin cambiar nada."]]));
s.push(...tabla(["Repetición", "Cuándo salta"], [["Sin repetición", "Una sola vez, en la fecha y hora indicadas."],
  ["Cada 30 minutos / Cada hora", "Desde la fecha de inicio, en el minuto indicado: con :15, a las :15 y a las :45, o a las :15 de cada hora (la rueda de las horas se desactiva)."],
  ["Diariamente", "Todos los días a esa hora, desde la fecha de inicio."], ["Semanalmente", "El mismo día de la semana que la fecha de inicio."],
  ["Mensualmente", "El mismo día del mes."], ["Anualmente", "El mismo día y mes cada año."]], [2800, 6838]));
s.push(...recuadro("consejo", "Ejemplo de antelación", ["Un aviso «Llamar a Suministros Atlántico» el 11-11-2026 a las 11:30 con 1 hora de antelación te avisa ese día a las 10:30. En la lista se ve como «⏰-1h»."]));
s.push(...recuadro("importante", "Deja el Organizador abierto", ["Un aviso sin antelación salta justo a su hora, así que el Organizador tiene que estar abierto en ese momento.",
  "Los avisos con antelación son más permisivos: si abres el Organizador más tarde ese mismo día, el aviso aparece al abrirlo."]));

// 5
s.push(h1("5. Calendario, vacaciones y festivos"));
s.push(p("El **Calendario** muestra el mes (o la semana) con todo lo que tienes apuntado. Cada día usa un color:"));
s.push(...tabla(["Color", "Significado"], [["Dorado", "Hoy."], ["Azul", "Día con algún aviso (puntual o repetitivo)."], ["Verde", "Día de vacaciones."],
  ["Rojo", "Día festivo."], ["Gris", "Día sin nada apuntado."]], [2200, 7438]));
s.push(...imagen("u_calendario_mes", 16, "Calendario del mes (datos de ejemplo)."));
s.push(...leyenda([[1, "**◀ ▶**: mes (o semana) anterior y siguiente. Entre las flechas, el periodo que estás viendo."], [2, "**Mes / Semana**: cambia la forma de ver el calendario. «Semana» abre la semana de hoy o la del día que hayas elegido."],
  [3, "**Chat**: abre el chat."], [4, "**Festivos**: la lista de festivos, donde se añaden y editan."], [5, "**Vacaciones**: la lista de periodos de vacaciones."],
  [6, "**Leyenda** de los iconos: aviso único, repetitivo, vacaciones, festivo y hoy."], [7, "**Hoy**, en dorado. Pulsa cualquier día para ver su detalle."],
  [8, "**Imprimir**: Agenda del Día, Semanal o Mensual (se abre una página lista para imprimir en tu navegador)."], [9, "La Agenda Mensual imprime el mes que estás viendo."]]));
s.push(...imagen("u_calendario_semana", 16, "Vista Semana: cada día con sus avisos, vacaciones y festivos."));
s.push(h2("Detalle de un día"));
s.push(...imagen("u_detalle_dia", 6, "Detalle del día."));
s.push(p("Al pulsar un día se abre un panel con todo lo de esa fecha: primero las vacaciones (verde) y los festivos (rojo), con el botón **Enviar correo sobre este aviso**, y debajo los avisos de la agenda con su hora. La **Agenda del Día** que se imprime es la del día que hayas elegido (o la de hoy)."));
s.push(h2("Vacaciones y festivos"));
s.push(p("Desde los botones **Vacaciones** y **Festivos** del calendario se gestionan las dos listas. Se agrupan por año y al final muestran el total de días programados."));
s.push(...imagen("u_vacaciones", 12, "Periodos de vacaciones."));
s.push(...leyenda([[1, "✏ **Editar** el periodo."], [2, "🗑 **Borrar** el periodo."], [3, "**+ Nuevo Periodo**: título (por ejemplo «Vacaciones de verano»), fechas de inicio y fin (escritas o con el calendario 📅) y, si quieres, con cuánta antelación te avisa el Organizador."]]));
s.push(...imagen("u_festivos", 12, "Días festivos."));
s.push(...leyenda([[1, "**+ Nuevo Festivo**: título, fecha (escrita o con el calendario 📅) y antelación del aviso. Cada fila tiene también ✏ editar y 🗑 borrar."]]));

// 6
s.push(h1("6. Avisos emergentes"));
s.push(p("Cuando llega la hora de un aviso se abre una **ventana emergente** en el centro de la pantalla, con un sonido. Si coinciden varios, salen de uno en uno."));
s.push(h2("Aviso de la agenda"));
s.push(...imagen("u_popup_aviso", 10, "Aviso de la agenda (repetitivo y con antelación)."));
s.push(...leyenda([[1, "**Silenciar hoy** (avisos repetitivos) o **No recordar hoy** (avisos con antelación): lo calla hasta mañana. Los avisos únicos sin antelación no tienen este botón."],
  [2, "**Desactivar evento**: lo pone en pausa en la Agenda; no saltará más hasta que lo reactives con ▶."],
  [3, "**Entendido** cierra la ventana. Si el aviso se repite, volverá a saltar en su próxima ocurrencia."]]));
s.push(h2("Vacaciones y festivos: correo de aviso"));
s.push(...imagen("u_popup_vacaciones", 10, "Aviso de unas vacaciones próximas."));
s.push(...leyenda([[1, "**Enviar correo** abre un borrador con el asunto y el texto ya redactados."], [2, "**Entendido** cierra el aviso."]]));
s.push(...imagen("u_correo", 12, "Borrador de correo de ausencia por vacaciones."));
s.push(...leyenda([[1, "**Asunto**, ya escrito."], [2, "**Cuerpo del correo**: puedes cambiar lo que quieras antes de enviarlo."],
  [3, "**Abrir en cliente de correo**: lo pasa a tu programa de correo, listo para elegir destinatarios y enviar."], [4, "**Copiar**: copia el texto para pegarlo donde quieras."]]));
s.push(h2("Avisos de tus pedidos"));
s.push(...imagen("u_popup_pedidos", 10, "Aviso que llega de Control de Pedidos (ejemplo)."));
s.push(p("Si has guardado tu usuario y contraseña de Control de Pedidos en **Admin → Mi Usuario**, el Organizador te avisa de lo que pasa con **tus pedidos**: cambios de estado y pedidos que llevan días sin avance (con el pedido, el hotel, el estado, el proveedor, el artículo y los días). Se repiten cada cierto tiempo según lo decida Control de Pedidos y solo se cierran con **Entendido**: no se pueden desactivar desde aquí."));
s.push(h2("Saludo del día"));
s.push(...imagen("u_saludo", 10, "Saludo del día."));
s.push(p("La primera vez que abres el Organizador cada día aparece un saludo con tu nombre, cuántos eventos tienes hoy y, si los hay, cuántos pedidos tienen alerta. **Ver eventos** abre el detalle de hoy. Solo sale una vez al día."));

// 7
s.push(h1("7. Chat"));
s.push(p("El **Chat** te conecta con los compañeros que tienen cuenta en Control de Pedidos. Para usarlo hace falta haber guardado tu usuario y contraseña en **Admin → Mi Usuario**. Se abre con el botón **Chat** del menú o del calendario."));
s.push(...imagen("u_chat", 16, "Ventana del chat (datos de ejemplo)."));
s.push(...leyenda([[1, "**Estado** de la conexión: «Conectado» en verde cuando todo va bien."],
  [2, "**Conversaciones**: el canal General, los chats privados y los grupos, cada uno con su foto (o sus iniciales sobre un círculo de color si no tiene). El número entre paréntesis son los mensajes sin leer."],
  [3, "**Nueva conversación**."], [4, "**Limpiar chat**: oculta el historial de esa conversación en tu equipo (no se borra para los demás)."],
  [5, "**Mensajes**: los tuyos, a la derecha en verde; los de los demás, a la izquierda. Cada burbuja lleva la fecha y la hora. Un adjunto se abre haciendo clic en él."],
  [6, "Escribe aquí y pulsa **Intro** o **Enviar**."], [7, "😊 **Emoticonos** y respuestas rápidas (siguiente imagen)."],
  [8, "📎 **Adjuntar** una imagen o un documento."], [9, "**Enviar**."],
  [10, "🖼 **Fotos**: cambiar o quitar tu foto de perfil y, en un grupo, la foto del grupo (siguiente apartado)."]]));
s.push(h2("Emoticonos y respuestas rápidas"));
s.push(...imagen("u_chat_emoticonos", 8, "Panel de emoticonos."));
s.push(...leyenda([[1, "**Emoticonos**: un clic añade el emoticono a lo que estás escribiendo y cierra el panel. Con **Mayús + clic** el panel se queda abierto para poner varios."],
  [2, "**Respuestas rápidas** («👍 Ok», «👌 Perfecto», «🙏 Gracias», «✅ Hecho»…): se añaden igual; luego pulsa Enviar. **Esc** o hacer clic fuera cierran el panel."]]));
s.push(p("El botón 😊 está también en la burbuja flotante. Los emoticonos se ven en color en el panel y en los mensajes. Viajan como texto normal: los ven todos los compañeros, también en el móvil o con una versión anterior del Organizador (en ese caso, de un solo color)."));
s.push(h2("Nueva conversación"));
s.push(...imagen("u_chat_nueva", 9, "Elegir compañeros."));
s.push(...leyenda([[1, "Elige a quién quieres escribir. **Un compañero** → chat privado. **Dos o más** (con Ctrl) → se crea un grupo y te pide un nombre para él."], [2, "**Abrir chat** para empezar."]]));
s.push(h2("Fotos de perfil"));
s.push(p("Cada persona puede poner **su propia foto**, y cualquier miembro de un grupo puede poner **la foto del grupo**. Se ven en la lista de conversaciones, en la cabecera de la conversación, junto a los mensajes de los demás en General y en los grupos, y en la burbuja flotante. Quien no tiene foto aparece con sus **iniciales** sobre un círculo de color (el mismo color en el Organizador y en el móvil)."));
for (const t of ["**Tu foto**: botón **🖼 Fotos** → «Cambiar mi foto…» y elige una imagen (jpg, png, webp…). Se recorta sola en cuadrado. «Quitar mi foto» vuelve a las iniciales.",
  "**Foto de un grupo**: abre el grupo y pulsa **🖼 Fotos** → «Cambiar la foto del grupo…» (o «Quitar la foto del grupo»). Solo aparece con un grupo abierto.",
  "Los cambios se ven al momento en los equipos y móviles de todos. La foto que pongas en el móvil es la misma que en el Organizador, y al revés."]) s.push(vineta(t));
s.push(h2("Enviar imágenes y documentos"));
s.push(p("Hay tres formas de adjuntar. En todas, el Organizador pregunta antes «¿Enviar a …?» con la lista de archivos, y solo se envía si contestas **Sí**:"));
for (const t of ["**📎**: elige el archivo en el Explorador (imágenes png, jpg, gif, bmp, webp y documentos pdf, doc, docx, xls, xlsx).",
  "**Arrastrar y soltar**: arrastra uno o varios archivos desde el Explorador de Windows sobre la ventana del chat o sobre una burbuja.",
  "**Pegar (Ctrl+V)**: con el cursor en la caja de texto, pega una captura de pantalla o archivos copiados en el Explorador. Si lo copiado es texto, se pega como siempre."]) s.push(vineta(t));
s.push(...recuadro("nota", "Límites de los archivos", ["Las imágenes se reducen solas antes de enviarlas. Los documentos se envían tal cual y no pueden pasar de **10 MB**. Al arrastrar o pegar, hasta **5 archivos** a la vez.",
  "Por seguridad, el chat rechaza programas, scripts y archivos con macros (por ejemplo .exe, .bat, .ps1, .lnk, .html, .xlsm o .docm)."]));
s.push(h2("La burbuja flotante"));
s.push(...imagen("u_chat_burbuja", 6, "Burbuja flotante con un mensaje nuevo."));
s.push(p("Cuando te escriben aparece una **burbuja** pequeña abajo a la derecha de la pantalla, con un aviso sonoro. Desde ella puedes leer y responder, poner emoticonos con 😊, adjuntar con 📎, **arrastrar archivos** encima o pegarlos con **Ctrl+V**, y enviar con ➤. **✕** la cierra y **⤢** abre la ventana completa del chat. Si te escriben varias personas, se apilan varias burbujas."));
s.push(...recuadro("consejo", "La conversación sigue en la burbuja", ["Si tienes abierta la ventana grande del chat en una conversación y la otra persona contesta, la ventana grande se cierra y la conversación sigue en la burbuja. Lo que estuvieras escribiendo pasa a la burbuja, no se pierde. Para volver a la ventana grande, pulsa ⤢."]));

// 8
s.push(h1("8. El chat en el móvil"));
s.push(p("**Chat Dpto. Compras Princess** es el mismo chat en un móvil Android: las mismas conversaciones, la misma cuenta de Control de Pedidos y los mismos emoticonos. Puedes estar conectado **a la vez** en el Organizador y en el móvil: los mensajes llegan a los dos, también los que escribes tú desde el otro."));
s.push(...tabla(["", "Organizador (Windows)", "Chat Dpto. Compras Princess (Android)"], [
  ["Conversaciones, privados y grupos", "Sí", "Sí"], ["Emoticonos y respuestas rápidas", "Sí", "Sí"],
  ["Enviar fotos y documentos", "📎, arrastrar o Ctrl+V", "Cámara, galería o documento"],
  ["Foto de perfil (tuya y de los grupos)", "🖼 Fotos, en la ventana del chat", "Ajustes → Mi foto (galería o cámara); la del grupo, en su cabecera"],
  ["Avisos de mensajes nuevos", "Burbuja flotante con sonido", "Notificación del móvil, también con la app cerrada"],
  ["Agenda, calendario, accesos y avisos de pedidos", "Sí", "No: solo el chat"],
  ["Actualizaciones", "Aviso «Actualizar ahora»", "Aviso al abrir la app"]], [3300, 3169, 3169]));
s.push(h2("Instalarla la primera vez"));
s.push(p("En el Organizador, abre el **Chat** y pulsa **📱 Chat en el móvil**: se abre esta ventana con un código QR."));
s.push(...imagen("u_chat_movil", 13, "Ventana «Chat en el móvil»."));
s.push(...leyenda([[1, "**Código QR**: escanéalo con la cámara del móvil. Lleva a la página de descarga de la última versión."],
  [2, "**Los pasos** para instalarla y dejarla lista."], [3, "**El enlace**, por si prefieres abrirlo a mano o enviártelo al móvil."],
  [4, "**Cómo se actualiza** (apartado siguiente)."]]));
s.push(...pasos(["En la página que se abre, toca el archivo **ChatPrincess_….apk** para descargarlo. Si el navegador avisa de que el archivo **«puede ser dañino»**, pulsa **Descargar de todas formas**.",
  "Abre el archivo descargado (desde la notificación de descarga o la app **Archivos**). La primera vez, Android pregunta si permites **«Instalar apps desconocidas»** desde el navegador o la app de archivos: actívalo, vuelve atrás y pulsa **Instalar**.",
  "Si aparece **Google Play Protect** («App no segura», «App desconocida» o «Bloqueada por Play Protect»), toca **Más detalles** y después **Instalar de todas formas** (en algunos móviles, **Instalar sin analizar**). Si pregunta si quieres **enviar la app para analizarla**, puedes contestar lo que prefieras: no cambia nada en la instalación.",
  "Abre **Chat Dpto. Compras Princess** y entra con tu **usuario y contraseña de Control de Pedidos**, los mismos del Organizador.",
  "Acepta las **notificaciones**.",
  "En **Ajustes** de la app, pulsa **«Quitar el ahorro de batería»**. En algunos móviles (Xiaomi, Huawei, Oppo…) hay que permitir además el «inicio automático»."]));
s.push(...recuadro("importante", "¿Por qué avisa Android de que puede ser peligrosa?", ["Android y Google Play Protect avisan de **cualquier app que no se instala desde Google Play**, y más si la usa poca gente y pide permisos para funcionar en segundo plano, arrancar con el móvil o instalar sus propias actualizaciones. Chat Dpto. Compras Princess necesita esos permisos para avisarte de los mensajes con la app cerrada y para actualizarse sola.",
  "Es la app del departamento, publicada en su repositorio oficial, y cada versión va firmada siempre con la misma clave. Descárgala **solo** desde el código QR del Organizador o desde su enlace; si alguien te la pasa por otro medio (WhatsApp, correo…), no la instales."]));
s.push(...recuadro("nota", "El aviso fijo «Chat conectado»", ["Mientras la app mantiene la conexión verás un aviso fijo «Chat conectado» en la barra de notificaciones. Es lo que permite que te avise de los mensajes con la app cerrada; al encender el móvil se vuelve a conectar solo."]));
s.push(h2("Cómo se actualiza"));
s.push(...pasos(["Al abrir la app, si hay una versión nueva, aparece el aviso **«Nueva versión…»** con sus novedades.",
  "Pulsa **Descargar e instalar**: la app la descarga y comprueba que es la publicada (SHA-256).",
  "Android muestra su pantalla de instalación: pulsa **Actualizar**. La primera vez pedirá permitir que **Chat Dpto. Compras Princess** instale apps. Si vuelve a salir **Play Protect**, igual que al instalarla: **Más detalles → Instalar de todas formas**.",
  "No se pierde nada: la sesión y las conversaciones siguen igual."]));
s.push(p("También puedes buscarla cuando quieras en **Ajustes → Buscar actualización**. Android no deja instalar sin confirmar, por eso el último paso siempre lo haces tú."));
s.push(...recuadro("consejo", "Cerrar sesión en el móvil", ["En **Ajustes → Cerrar sesión** se borran del móvil el usuario y la contraseña y deja de avisar. Hazlo si cambias de móvil o si el móvil no es solo tuyo."]));

s.push(h1("9. Actualizar la aplicación"));
s.push(p("Al arrancar, y después cada 2 horas aproximadamente, el Organizador comprueba si hay una **versión nueva** publicada. Si la hay, se abre la ventana «Actualización disponible»."));
s.push(...imagen("u_actualizacion", 11, "Actualización disponible (ejemplo)."));
s.push(...leyenda([[1, "**Novedades** de la versión nueva."], [2, "**Actualizar ahora**: lo hace todo solo (pasos siguientes)."], [3, "**Recordar después**, si prefieres hacerlo más tarde."]]));
s.push(...pasos(["Pulsa **Actualizar ahora**. El Organizador descarga la versión nueva y comprueba que el archivo es el publicado (SHA-256); si no coincide, lo borra y te pide reintentar.",
  "Windows pregunta si permites que el instalador haga cambios: contesta **Sí**.",
  "El Organizador se cierra, se instala la versión nueva (solo verás una barra de progreso) y **vuelve a abrirse solo**, con un mensaje «Organizador actualizado». Tu configuración y tu agenda se mantienen."]));
s.push(...recuadro("nota", "Si algo no va", ["Si contestas **No** a la pregunta de Windows, la ventana ofrece **Instalar** para volver a intentarlo y **Abrir carpeta** para ver el instalador descargado y abrirlo a mano."]));
s.push(h2("Nueva versión detectada"));
s.push(p("Si la versión nueva se instaló con **Actualizar ahora**, no aparece nada más: se mantienen tu configuración y tu agenda. Si el instalador se abrió a mano, la primera vez que abres la versión nueva aparece esta ventana, que pregunta cómo continuar:"));
s.push(...imagen("u_nueva_version", 10, "Nueva versión detectada."));
s.push(...leyenda([[1, "**Solo actualizar versión**: mantiene tu configuración y tu agenda. Es la opción normal."],
  [2, "**Instalación desde cero**: borra la configuración y la agenda."], [3, "Con «desde cero», puedes hacer antes una **copia de seguridad** de la agenda (vacaciones y festivos incluidos) en la carpeta que elijas."],
  [4, "**Confirmar**."]]));
s.push(...recuadro("importante", "Elige «Solo actualizar versión»", ["La instalación desde cero es una restauración completa: úsala solo si te lo pide quien administra el Organizador."]));
s.push(...recuadro("nota", "Una sola ventana a la vez", ["Solo puede haber un Organizador abierto. Si lo arrancas por segunda vez, se cierra el anterior y continúa el nuevo, para evitar avisos duplicados."]));

// 9
s.push(h1("10. Problemas frecuentes"));
s.push(...tabla(["Problema", "Qué hacer"], [
  ["Un botón no abre nada o da error", "Comprueba que tienes acceso a la red (carpetas) o a Internet (webs). Si sigue igual, la ruta puede estar mal: díselo a quien administra el Organizador."],
  ["Un botón dice «POR DEFINIR»", "Está sin configurar. Púlsalo para configurarlo (o pide que lo configuren)."],
  ["No me salta un aviso", "Revisa en la Agenda que no esté DESACTIVADO, que la fecha y la hora son correctas y que el Organizador estaba abierto a esa hora. Puede haberse callado con «Silenciar hoy»."],
  ["No me sale el saludo", "Solo aparece la primera vez que abres el Organizador cada día."],
  ["No me llegan avisos de pedidos", "Revisa Admin → Mi Usuario: tu usuario y contraseña de Control de Pedidos deben estar guardados y ser los que usas allí."],
  ["El chat dice que no hay credenciales", "Guarda tus credenciales en Admin → Mi Usuario y reinicia el Organizador."],
  ["El móvil no avisa de los mensajes", "Comprueba que la app tiene permiso de notificaciones, que se ve el aviso «Chat conectado» y quita el ahorro de batería (Ajustes de la app)."],
  ["«Admin» me pide una contraseña", "Es la de tu cuenta de Control de Pedidos. Tras 3 fallos se bloquea 5 minutos. Si no tienes cuenta, pulsa «Crear acceso» (Manual de administrador)."],
  ["Error al comprobar actualizaciones", "Pulsa «Copiar texto» en la ventana de error y envíaselo a informática. No impide trabajar."]], [3300, 6338]));
s.push(h2("Referencia rápida"));
s.push(...tabla(["Quiero…", "Cómo"], [["Abrir una carpeta, web o programa", "Pulsar su botón del menú"], ["Apuntar un recordatorio", "Agenda → + Añadir Aviso"],
  ["Pausar un aviso", "En su ventana emergente, «Desactivar evento»"], ["Ver vacaciones y festivos", "Calendario → Vacaciones / Festivos"],
  ["Imprimir la agenda", "Calendario → Agenda del Día / Semanal / Mensual"], ["Escribir a un compañero", "Chat → Nueva conversación"],
  ["Enviar un archivo por el chat", "📎, arrastrarlo a la ventana o Ctrl+V"], ["Cambiar mi nombre o mis credenciales", "Admin → Mi Usuario"],
  ["Tener el chat en el móvil", "Chat → 📱 Chat en el móvil (código QR)"],
  ["Abrir este manual", "Botón Manual del menú, o «Manual de Usuario» en el menú Inicio de Windows"]], [4000, 5638]));

L.generar(process.argv[2] || "salida/Manual_Usuario_OrganizadorPrincess.docx", "Manual de usuario — Organizador Princess", "de usuario", s);
