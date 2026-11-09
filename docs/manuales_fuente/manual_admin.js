// Manual de administrador del Organizador Princess. Idea y desarrollo de la aplicación: Víctor Alejandro Martín Andrade.
const L = require("./lib");
const { p, vineta, pasos, h1, h2, imagen, leyenda, recuadro, tabla, portada, indice } = L;
const V = process.env.VERSION || "v4.18.26";

const s = [];
s.push(portada({ rol: "Administración", subtitulo: "Configura los botones y la vista del menú, el usuario y las copias, e instala y publica versiones",
  version: V, fecha: "Noviembre 2026", publico: "Para quien configura y mantiene el Organizador en los equipos de la Central de Compras" }));
s.push(indice([["1. Qué se hace en Administración", "Y qué no"], ["2. Acceder al panel Admin", "Contraseña, bloqueo y solicitud de acceso"],
  ["3. El panel Admin de un vistazo", ""], ["4. Configurar botones y accesos rápidos", "Tipos de enlace, submenús y «Limpiar todo»"],
  ["5. Vista del menú", "Extendida o reducida"], ["6. Mi Usuario", "Nombre y credenciales de Control de Pedidos"],
  ["7. Copias de seguridad y traslado a otro PC", "Exportar, importar y dónde están los datos"], ["8. Instalar, actualizar y publicar versiones", ""],
  ["9. Incidencias y comprobaciones", ""]]));

// 1
s.push(h1("1. Qué se hace en Administración"));
s.push(p("Quien administra el Organizador de un equipo decide **qué botones tiene el menú**, **cómo se ve**, **con qué usuario trabaja** y cómo se **protegen y actualizan** sus datos. Todo eso se hace desde el panel **Admin**; la instalación y las versiones, con el instalador. Para el uso diario (agenda, calendario, chat y avisos) está el **Manual de usuario**."));
s.push(h2("Qué puedes hacer"));
for (const t of ["Entrar al panel Admin con tu usuario de Windows y tu contraseña de Control de Pedidos.",
  "Configurar los **6 accesos rápidos** y los **30 botones** del menú: nombre, tipo (carpeta, web o programa) y ruta.",
  "Añadir **submenús** de hasta 10 subopciones a cualquier botón.", "Elegir la **vista** del menú: extendida o reducida.",
  "Guardar tu **nombre** y tus **credenciales** de Control de Pedidos (chat y avisos de pedidos).",
  "Hacer **copias** de la configuración y de la agenda, y restaurarlas o llevarlas a otro PC.", "**Instalar, actualizar y publicar** versiones nuevas."]) s.push(vineta(t));
s.push(h2("Qué no se hace aquí"));
for (const t of ["Crear o aprobar cuentas de Control de Pedidos: lo hace un administrador de Control de Pedidos.",
  "Cambiar cuándo y cada cuánto se repiten los avisos de pedidos: se configura en Control de Pedidos.",
  "Gestionar la agenda de otros compañeros: cada agenda es local de su PC.", "Administrar el servidor del chat: es un servicio aparte."]) s.push(vineta(t));
s.push(...recuadro("nota", "Una configuración por PC", ["Los botones, la vista, tu nombre y la agenda se guardan en cada equipo y usuario de Windows. Para dejar varios PC iguales, configura uno, exporta la configuración e impórtala en los demás (capítulo 7)."]));

// 2
s.push(h1("2. Acceder al panel Admin"));
s.push(p("Pulsa **Admin** en el menú principal. El acceso no usa un usuario y una contraseña fijos: te identifica por tu **usuario de Windows** y se valida con tu **cuenta de Control de Pedidos**."));
s.push(...imagen("a_login", 10, "Acceso a Administración."));
s.push(...leyenda([[1, "**Usuario Windows**: se toma solo; no se escribe."], [2, "**Contraseña**: la de tu cuenta de Control de Pedidos."],
  [3, "**¿Todavía no tienes cuenta en Control de Pedidos? Crear acceso**: cambia a la solicitud de alta (más abajo)."], [4, "**Entrar** (también vale la tecla Intro)."]]));
s.push(p("La contraseña se comprueba contra Control de Pedidos, así que hace falta conexión; si ya entraste antes en este equipo con esa contraseña, se acepta aunque Control de Pedidos no responda. Una vez dentro, el panel no vuelve a pedirla mientras el Organizador siga abierto."));
s.push(...recuadro("importante", "Tres intentos y 5 minutos", ["Tras 3 contraseñas incorrectas el acceso se bloquea unos 5 minutos («Demasiados intentos fallidos»). Espera y vuelve a probar."]));
s.push(h2("Si tu usuario aún no tiene cuenta"));
s.push(...pasos(["En el acceso pulsa **Crear acceso**.", "Rellena nombre, apellidos, correo, teléfono móvil de empresa y marca tu hotel o hoteles (puedes marcar varios).",
  "Pulsa **Enviar solicitud**. Un administrador de Control de Pedidos la revisa y te envía tus credenciales por correo.",
  "Mientras llega, vuelve a pulsar **Admin** y elige una **contraseña provisional**: te da acceso al panel de este equipo (incluido Mi Usuario), pero todavía no al chat ni a los avisos de pedidos.",
  "Cuando llegue el correo, entra en **Mi Usuario** y sustituye la contraseña provisional por la que te enviaron."]));

// 3
s.push(h1("3. El panel Admin de un vistazo"));
s.push(...imagen("a_panel", 17, "Panel «Administrar Accesos y Opciones del Menú» (datos de ejemplo)."));
s.push(...leyenda([[1, "**Vista**: menú extendido o reducido (capítulo 5)."], [2, "**Mi Usuario**: tu nombre y tus credenciales de Control de Pedidos (capítulo 6)."],
  [3, "**Limpiar todo**: deja todos los botones y accesos rápidos sin configurar (capítulo 4)."],
  [4, "**Accesos rápidos del header**: los 6 botones dorados."], [5, "**Editar**: abre la configuración de ese botón."],
  [6, "**Opciones del menú principal**: los 30 botones azules, numerados 01–30."], [7, "El triángulo **▶** junto al nombre indica que el botón tiene submenú."],
  [8, "**Configuración**: Exportar / Importar (capítulo 7)."], [9, "**Agenda**: Exportar / Importar (capítulo 7)."]]));
s.push(...recuadro("consejo", "Los cambios se ven al momento", ["Al guardar un botón, su nombre cambia enseguida en el menú principal."]));

// 4
s.push(h1("4. Configurar botones y accesos rápidos"));
s.push(p("En el panel, pulsa **Editar** en el botón que quieras cambiar (o, en el menú principal, pulsa un botón «POR DEFINIR»). Se abre la ventana de configuración."));
s.push(...imagen("a_editar_acceso", 12, "Configurar un acceso (aquí, un botón con submenú)."));
s.push(...leyenda([[1, "**Nombre del botón**: el texto que se ve en el menú. En los accesos dorados conviene que sea corto (los largos se cortan)."],
  [2, "**Tipo de enlace**: Carpeta de red, Página web o Archivo ejecutable."], [3, "**Ruta / Dirección** a la que lleva el botón."],
  [4, "**Explorar…** para elegir la carpeta o el archivo (en carpeta y ejecutable)."], [5, "**Activar submenú**: el botón abrirá una ventana con subopciones."],
  [6, "**Número de subopciones** (1–10)."], [7, "**Configurar subopciones…** (apartado siguiente)."], [8, "**Guardar** aplica el cambio."]]));
s.push(...tabla(["Tipo", "Qué escribir", "Ejemplo"], [["📁 Carpeta de red", "Ruta de la carpeta (usa «Explorar…»)", "\\\\servidor\\compras\\Tarifas"],
  ["🌐 Página web", "Dirección completa", "https://intranet.ejemplo.com"],
  ["⚙ Archivo ejecutable", "Programa o documento: .exe, .bat, .cmd, .lnk, .rdp, .ps1, Excel, Word, PDF…", "C:\\Informes\\mensual.xlsx"]], [2400, 4200, 3038]));
s.push(...recuadro("consejo", "Accesos rápidos y botones azules", ["Los 6 accesos rápidos (dorados) y los 30 botones (azules) se configuran igual. Pon en los rápidos lo que más se usa: en la vista reducida solo se ven los 4 primeros."]));
s.push(h2("Submenús"));
s.push(p("Cualquier botón puede abrir una ventana con **hasta 10 subopciones** en lugar de un único destino. Es útil para agrupar, por ejemplo, las carpetas de cada isla o de cada hotel."));
s.push(...pasos(["En la ventana del botón, activa **Activar submenú**.", "Elige el **número de subopciones** (1–10).",
  "Pulsa **Configurar subopciones…**: verás una cuadrícula con cada subopción y su botón Editar.",
  "Configura cada subopción igual que un botón (nombre, tipo y ruta) y pulsa **Guardar**."]));
s.push(...imagen("a_subopciones", 14, "Subopciones de un botón."));
s.push(...leyenda([[1, "**Editar** cada subopción."]]));
s.push(...recuadro("importante", "Con submenú activo, la ruta del botón no se usa", ["Mientras el submenú esté activado, pulsar el botón abre las subopciones y no su ruta. Desactívalo si quieres que el botón vuelva a abrir un destino directo."]));
s.push(h2("Limpiar todo"));
s.push(p("**Limpiar todo** elimina la configuración de todos los botones y accesos rápidos (incluidos sus submenús) y los deja en «POR DEFINIR». Pide confirmación. No toca la agenda, la vista, tu nombre ni tus credenciales. Si no estás seguro, exporta antes la configuración (capítulo 7)."));

// 5
s.push(h1("5. Vista del menú: extendida o reducida"));
s.push(p("En el panel, pulsa **Vista** para elegir cómo se ve el menú principal en este equipo."));
s.push(...imagen("a_vista", 10, "Ventana «Vista del menú principal»."));
s.push(...leyenda([[1, "**Extendida**: la de siempre; cabecera completa, 6 accesos dorados y los 30 botones azules."],
  [2, "**Reducida**: logo y cabecera, los 4 primeros accesos dorados, Agenda / Calendario / Chat y solo los botones azules que marques abajo, en 2 filas de 5. La ventana se hace más pequeña."],
  [3, "**Botones azules de la vista reducida**: marca los que quieras ver (máximo 10). Siempre salen en su orden numérico."],
  [4, "**Contador** («10 de 10»). Al llegar al máximo no deja marcar más: desmarca uno antes."],
  [5, "**Guardar y aplicar** cambia la vista al momento, sin reiniciar. **Cancelar** la deja como estaba."]]));
s.push(...recuadro("nota", "No se pierde nada", ["Cambiar de vista solo oculta o muestra botones: la configuración de los 30 se conserva. Si no has marcado ninguno, la vista reducida usa los 10 primeros."]));

// 6
s.push(h1("6. Mi Usuario: nombre y credenciales"));
s.push(p("**Mi Usuario** guarda dos cosas de este equipo: cómo quieres que te llamen y con qué cuenta de Control de Pedidos trabaja el Organizador."));
s.push(...imagen("a_mi_usuario", 11, "Mi Usuario (datos de ejemplo)."));
s.push(...leyenda([[1, "**Usuario Windows** de este equipo."], [2, "**Nombre a mostrar**: sale en el saludo y en el chat. No puede quedar vacío."],
  [3, "**Usuario (login)** de Control de Pedidos."], [4, "**Contraseña** de Control de Pedidos (se guarda cifrada). Debajo, el estado: verde si hay sesión; naranja si todavía no (se activa al guardar o al reiniciar)."],
  [5, "**Guardar**."]]));
s.push(p("Estas credenciales son las que usan el **chat** y los **avisos de pedidos**: deben coincidir exactamente con las de Control de Pedidos. Al guardar, el Organizador las aplica sin reiniciar."));
s.push(...recuadro("nota", "Cómo se protege la contraseña", ["Se guarda cifrada con Windows (DPAPI): solo el mismo usuario de Windows en el mismo equipo puede descifrarla. Si copias la carpeta de datos a otro PC u otro usuario, habrá que volver a escribirla en Mi Usuario."]));

// 7
s.push(h1("7. Copias de seguridad y traslado a otro PC"));
s.push(p("En el pie del panel hay dos pares de botones, cada uno con **Exportar** e **Importar**:"));
s.push(...tabla(["Qué", "Exportar", "Importar"], [
  ["**Configuración** (botones, accesos rápidos, submenús, vista)", "Guarda una copia como OrganizadorPrincess_config.json donde elijas.", "Sustituye la configuración actual. El Organizador se cierra: vuelve a abrirlo para ver los cambios."],
  ["**Agenda** (avisos, vacaciones y festivos)", "Guarda una copia de la agenda. Si aún no hay agenda, lo avisa.", "Sustituye la agenda actual (se pierden los eventos, vacaciones y festivos de ahora). Se aplica sin reiniciar."]], [2900, 3300, 3438]));
s.push(...recuadro("importante", "Importar sustituye, no mezcla", ["Antes de importar pide confirmación, pero no hay deshacer: exporta primero lo que tengas si te interesa conservarlo."]));
s.push(h2("Dónde se guardan los datos"));
s.push(p("Todo vive en la carpeta de datos del usuario de Windows, **%APPDATA%\\OrganizadorPrincess**:"));
s.push(...tabla(["Archivo", "Contenido"], [["config.json", "Botones, accesos rápidos, submenús y vista del menú."], ["agenda.json", "Avisos, vacaciones y festivos."],
  ["usuarios.db", "Tu nombre y las credenciales de Control de Pedidos (la contraseña, cifrada con DPAPI)."],
  ["version.json", "Última versión con la que se arrancó (para detectar actualizaciones)."], ["admin_auth.*", "Datos locales del acceso a Admin."]], [2600, 7038]));
s.push(...recuadro("consejo", "Para clonar un PC", ["Exporta la configuración del PC de referencia e impórtala en el nuevo. El nombre y las credenciales no viajan en la exportación: cada persona los guarda en su propio Mi Usuario."]));
s.push(...recuadro("importante", "Desinstalar borra los datos", ["El desinstalador elimina también la carpeta de datos del usuario (configuración, agenda y credenciales). Exporta antes si quieres conservarlos."]));

// 8
s.push(h1("8. Instalar, actualizar y publicar versiones"));
s.push(h2("Instalar"));
s.push(...pasos(["Ejecuta **OrganizadorPrincess_Setup_<versión>.exe** con permisos de administrador de Windows (el instalador los pide).",
  "Sigue el asistente (en español). Se instala en Archivos de programa; marca la casilla si quieres un acceso directo en el escritorio.",
  "Al terminar puedes iniciar el Organizador. En el menú Inicio quedan el programa, el **Manual de Usuario**, el **Manual de Administrador** y el desinstalador."]));
s.push(p("Si ya había una versión instalada, el instalador cierra el Organizador antes de sustituirla; la configuración y la agenda se conservan. El botón **Manual** del menú abre el manual de usuario instalado junto al programa."));
s.push(h2("Cuando el usuario actualiza"));
s.push(p("Los equipos reciben el aviso «Actualización disponible» al arrancar y cada 2 horas aproximadamente (Manual de usuario, capítulo 9). En el primer arranque tras instalar, «Nueva versión detectada» ofrece **Solo actualizar versión** (mantiene configuración y agenda) o **Instalación desde cero** (borra ambas, con copia opcional de la agenda). Recomienda siempre la primera."));
s.push(h2("Publicar una versión nueva"));
s.push(p("El Organizador busca la **última release** del repositorio de GitHub controlpedidosprincesscanarias-coder/organizador-princess. Ese repositorio tiene que seguir siendo **público** (los equipos consultan sin iniciar sesión) y no se borran ni se renombran releases ni etiquetas antiguas."));
s.push(...pasos(["Sube el número en **APP_VERSION** (main_agenda.py) y en **MyAppVersion** del instalador (OrganizadorPrincess_Setup.iss): deben coincidir y terminar en número par. Añade arriba las novedades en release_notes/release_notes.md y release_notes_actual.txt, y sube los cambios a main.",
  "En GitHub, pestaña **Actions → Compilar Organizador → Run workflow**, con destino **borrador**. Pasa las pruebas, compila el programa, genera el instalador y su .sha256 y crea la release en **borrador**: los equipos todavía no la ven. (Con el destino **solo-descarga** se compila para probar, sin crear ninguna release.)",
  "Descarga el instalador del borrador (en Releases) y pruébalo en tu equipo.",
  "Cuando quieras que se actualicen todos, abre el borrador y pulsa **Publish release**.",
  "Los equipos la detectan al arrancar o en unas 2 horas como máximo. Con **Actualizar ahora** (desde la 4.18.20) se descarga, se comprueba el hash, se instala en silencio y el Organizador se vuelve a abrir solo; solo hay que aceptar el permiso de Windows."]));
s.push(p("Si compilas a mano (compilar.bat e Inno Setup), crea tú la release con la etiqueta v<versión>, el instalador y su .sha256, que se obtiene con este comando de PowerShell:"));
s.push(p("(Get-FileHash .\\OrganizadorPrincess_Setup_4.18.26.exe -Algorithm SHA256).Hash.ToLower() + \"  OrganizadorPrincess_Setup_4.18.26.exe\" | Out-File -Encoding ascii OrganizadorPrincess_Setup_4.18.26.exe.sha256", { color: "374151" }));
s.push(...recuadro("importante", "Sube siempre el .sha256", ["Sin él, los equipos pueden descargar igualmente pero verán «Esta versión no publica hash: integridad sin verificar»."]));
s.push(h2("El chat para Android (Chat Dpto. Compras Princess)"));
s.push(p("La app del chat para móviles Android está en otro repositorio público, **chat-movil-princess**, y se publica igual que el Organizador: **Actions → «Compilar Chat Princess» → Run workflow** con destino **borrador**, se prueba la .apk del borrador y se pulsa **Publish release**. Los móviles avisan al abrir la app."));
for (const t of ["En cada versión: **versionName** (terminado en número par) y **versionCode** en app/build.gradle.kts y la entrada en CHANGELOG.md.",
  "Todas las versiones se firman con **la misma clave**, guardada en los secretos FIRMA_* del repositorio. Guarda la copia de seguridad (firma_chat_princess.jks y sus claves) fuera de GitHub: sin ella, las versiones nuevas no se podrían instalar encima de las anteriores.",
  "Para instalarla por primera vez, cada persona usa el botón **📱 Chat en el móvil** del chat del Organizador (código QR) o el capítulo 8 del Manual de usuario."]) s.push(vineta(t));

// 9
s.push(h1("9. Incidencias y comprobaciones"));
s.push(...tabla(["Síntoma", "Causa probable y qué hacer"], [
  ["Un botón no abre su destino", "Ruta mal escrita, o sin acceso a la red o sin permisos. Edita el botón y prueba la ruta a mano en el Explorador o el navegador. Con submenú activo, el botón no abre su ruta."],
  ["«Demasiados intentos fallidos» en Admin", "Espera unos 5 minutos. La contraseña es la de tu cuenta de Control de Pedidos: si la olvidaste, pide allí un restablecimiento."],
  ["«Sin conexión con Control de Pedidos» al entrar o al solicitar acceso", "Comprueba la red y reintenta: el acceso a Admin se valida contra Control de Pedidos."],
  ["Mi Usuario en naranja «Sin sesión activa»", "Aún no hay sesión con Control de Pedidos. Comprueba usuario y contraseña, guarda y espera al siguiente ciclo o reinicia el Organizador."],
  ["Chat y avisos de pedidos no funcionan tras copiar la carpeta de datos a otro PC", "La contraseña cifrada con DPAPI no se puede leer en otro equipo o usuario. Vuelve a escribirla en Mi Usuario."],
  ["Error de conexión con Control de Pedidos (HTTP 401/403)", "Credenciales incorrectas o cuenta inactiva. Revisa Mi Usuario y el estado de la cuenta en Control de Pedidos."],
  ["«Error al comprobar actualizaciones»", "El equipo no llega a GitHub (proxy, cortafuegos o red). Usa «Copiar texto» y pásalo a informática. El resto de la aplicación sigue funcionando."],
  ["Avisos o ventanas duplicadas", "Solo debe haber un Organizador por usuario: al abrirlo por segunda vez se cierra el anterior. Si persiste, reinicia el equipo."],
  ["Tras importar la configuración no cambia nada", "La importación cierra el Organizador: ábrelo de nuevo."]], [3500, 6138]));
s.push(...recuadro("consejo", "Lista de comprobación tras instalar un PC nuevo", ["1. Entrar en Admin (o solicitar el acceso).  2. Importar la configuración de referencia o configurar los botones.  3. Elegir la vista.  4. Guardar Mi Usuario con nombre y credenciales de Control de Pedidos.  5. Probar un botón de cada tipo, crear un aviso de prueba y abrir el chat."]));

L.generar(process.argv[2] || "salida/Manual_Administrador_OrganizadorPrincess.docx", "Manual de administrador — Organizador Princess", "de administrador", s);
