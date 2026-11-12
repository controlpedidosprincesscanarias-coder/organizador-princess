# CLAUDE.md — Organizador Princess

> **Autoría:** la idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de **Víctor Alejandro Martín Andrade**, para el Departamento de Central de Compras de Princess Hotels en Canarias. Ver `AUTORIA.md`.

Instrucciones para Claude Code en este repositorio. Responde siempre en **español**.

## Qué es
Aplicación de escritorio para Windows 10/11 de la Central de Compras Princess Canarias: agenda con avisos programados, vacaciones y festivos, accesos rápidos, chat interno y popups con los avisos de **Control de Pedidos** (la app web del departamento, repo `control-pedidos-princess`).
- **Python 3.10–3.13 + ttkbootstrap (Tkinter).** Punto de entrada: `main_agenda.py`. Persistencia local en SQLite (`app/db/sqlite.py`) y en `%APPDATA%\OrganizadorPrincess\`.
- **Compilación:** `compilar.bat` (copia el proyecto a `C:\build_temp\OrganizadorPrincess` y lanza PyInstaller con `main.spec`). Un módulo nuevo que se importe de forma dinámica va en `hiddenimports` de `main.spec` (ya pasó con `ui.dnd_windows`).
- **Instalador:** Inno Setup con `OrganizadorPrincess_Setup.iss` → `OrganizadorPrincess_Setup_<versión>.exe`.
- **Compilación automática:** `.github/workflows/compilar.yml`, solo a mano desde la pestaña Actions (Windows de GitHub, Python 3.12, `compilacion/requisitos.txt`). Destino «solo-descarga» (instalador como descarga del workflow, sin Release) o «borrador» (Release en **borrador**, invisible para `/releases/latest`; se publica a mano con «Publish release»). Las comprobaciones previas están en `compilacion/preparar_release.py`. Nunca publicar una Release directamente desde el workflow ni lanzarlo al subir código.

## Estructura
- `main_agenda.py` — menú principal (maquetación, vista extendida/reducida) y arranque de los servicios. Desde v4.18.08 las ventanas Agenda, Calendario y Administración están en `app/ui/agenda.py`, `calendario.py` y `admin.py`; reciben el `AppContext` (`app/context.py`), y `main_agenda` solo tiene envoltorios `abrir_agenda()` / `abrir_calendario()` / `abrir_admin()`. Constantes del menú en `app/ui/disposicion.py`; colores en `app/ui/colores.py`. Un módulo nuevo de `app/` va también en `hiddenimports` de `main.spec`.
- `pedidos_agenda_bridge.py` — conexión con Control de Pedidos (`/api/bridge/login`, `/api/bridge/alertas`, `/api/bridge/notificaciones`) a través del Worker `proxy.controlpedidosprincess-canarias.workers.dev`. Desde v4.18.52 cada petición lleva la versión instalada (`X-Organizador-Version`): Control Pedidos (v12.34.26) sabe así que el Organizador de cada uno está abierto, no le muestra el aviso «abre o instala el Organizador» y enseña la versión en Usuarios. El instalador registra el enlace `organizadorprincess://` (`[Registry]` del `.iss`) para el botón «Abrir el Organizador» de ese aviso.
- `app/services/` — `update_service.py` (actualizaciones: al arrancar y cada 2 h con margen al azar, `_programar_siguiente_check`; el límite de consultas de GitHub se espera en silencio, `_espera_por_limite_github`; desde v4.18.20 «Actualizar ahora» descarga a una carpeta temporal, comprueba el SHA-256 y lanza el instalador con `/SILENT` (`_instalar_ya`), que se vuelve a abrir solo (`[Run]` con `Check: WizardSilent` en el `.iss`) sin preguntar «Nueva versión detectada» (`actualizacion_automatica_aplicada`). Lo ejecuta la versión **instalada**: el cambio de la ventana se nota a partir de la actualización siguiente), `chat_client.py` (chat, Worker `proxy-chat.controlpedidosprincess-canarias.workers.dev`), `admin_auth.py` (acceso a Administración).
- `app/negocio/` — `alertas.py` (popups y recordatorios; `_AUTOCIERRE_BRIDGE_MIN`), `correo.py`.
- `app/ui/` — ventanas (chat, configuración, festivos, vacaciones, saludo…); `selector_fecha_hora.py` (calendario 📅 y ruedas de hora de los formularios de avisos, vacaciones y festivos; la lógica de lo escrito a mano, en `utils/fechas.py`); `chat_movil.py` (ventana «📱 Chat en el móvil» con el QR de la app Android, `qr_chat_movil.png`, que se regenera con `compilacion/generar_qr_movil.py`); `emoticonos.py` (panel 😊 del chat; desde v4.18.22 los emoticonos van en color como imágenes de `emoticonos_color/`, porque Tk en Windows los dibuja de un solo color: se regeneran con `compilacion/generar_emoticonos.py` si cambia la lista; `chat_bubbles.py` los pinta también en color dentro de los mensajes); `avatares.py` (v4.18.28: fotos de perfil del chat en círculo, o iniciales sobre un color que coincide con el de la app del móvil; necesitan el servidor del chat v1.3.0); `miniaturas.py` (v4.18.44: miniaturas de las imágenes del chat, descargadas con `ChatClient.descargar_bytes`); `notas_version.py` (v4.18.44: al pulsar el número de versión del menú, Administración o Configuración se ven las notas de esa versión, sacadas de `release_notes/release_notes.md`, que el instalador copia junto al programa); `acciones_chat.py` (v4.18.46: responder citando, reenviar y eliminar mensajes en la ventana del chat y en la burbuja; necesita el servidor del chat v1.4.0); `grupo_info.py` (v4.18.48: integrantes de un grupo al pulsar su foto o su nombre; quien lo creó añade, quita, renombra y elimina, y cualquier miembro se sale; necesita el servidor del chat v1.5.0); `dnd_windows.py` (arrastrar y soltar en el chat, desactivable con `"chat_arrastrar_soltar": false` en `config.json`).
- `app/db/` — `sqlite.py` y `dpapi.py` (cifrado con la API de Windows).
- `release_notes/` — `release_notes.md` (todas las versiones) y `release_notes_actual.txt` (la actual; la muestra el instalador).
- `docs/` y `Manual_Usuario_OrganizadorPrincess.pdf` — manuales (el PDF de la raíz es el que abre el botón «Manual»). Se regeneran con `docs/manuales_fuente/` (v4.18.12): capturas reales del Organizador en Linux con datos inventados y sin red (`capturas.sh`), y maquetación con `docx` de Node en el estilo de los manuales de Control Pedidos (`generar.sh usuario|admin`); ver su README. Si un cambio altera una pantalla que sale en un manual, avisar de que conviene regenerarlo.

## Actualización automática — LO MÁS DELICADO
Todos los equipos se actualizan solos desde las **Releases de este repositorio**:
- `update_service.py` consulta `https://api.github.com/repos/controlpedidosprincesscanarias-coder/organizador-princess/releases/latest` **sin iniciar sesión** y descarga el `.exe` de la Release, comprobando el `.sha256` si se publica.
- Por eso **este repositorio nunca puede pasar a privado**: los equipos dejarían de actualizarse. Tampoco se borran ni renombran Releases ni etiquetas antiguas.
- La versión se compara como números (`_parse_version`: `v4.18.04` = `v4.18.4`). En cada versión:
  - `APP_VERSION` en `main_agenda.py` (línea ~117) y `#define MyAppVersion` en el `.iss` iguales;
  - etiqueta de la Release igual a esa versión;
  - subir el `.exe` y su `.sha256`;
  - numeración **par** en el último número (decisión de Víctor: 4.18.00, 4.18.02, 4.18.04…).
- **Copia portátil** (v4.18.54, `app/services/portatil.py`), para los PC que no permiten instalar:
  - Cada Release lleva también `OrganizadorPrincess_Portatil_v<versión>.zip` y su `.sha256`, con el mismo `OrganizadorPrincess.exe` que mete el instalador. Lo crea el workflow.
  - Se reconoce porque no tiene al lado el desinstalador `unins000.exe`. Se actualiza sola, como la Consola Registro Info y sin administrador: descarga el `.zip`, comprueba el SHA-256 (obligatorio), deja el `.exe` nuevo como «.nuevo.exe», cambia el actual a «.anterior.exe» y lo abre. Al arrancar, borra los restos y registra `organizadorprincess://` en HKCU.
  - El manual y `release_notes.md` van **dentro** del `.exe` (`main.spec`, carpeta `documentos`).
  - **Primer arranque** (`ui/primer_arranque_portatil.py`): pregunta la carpeta (por defecto `Documentos\Organizador Princess`), se copia allí y se reabre desde ella; acceso directo en la carpeta de Inicio (arranque al iniciar sesión) y en el escritorio con PowerShell, o `HKCU\…\Run` si PowerShell está bloqueado. La copia buena se guarda en `%APPDATA%\OrganizadorPrincess\portatil.json`; si se abre otra, ofrece abrir esa.
  - **ANTI-REGRESION:** la copia portátil va **siempre en un `.zip`**, nunca como `.exe` suelto en la Release. Los Organizadores instalados hasta la v4.18.52 cogen el **primer `.exe`** de la Release como instalador: con un segundo `.exe` podrían bajarse el portátil y no actualizarse nunca. Lo vigila `test_portatil.py`.
- El repositorio guarda el **código** junto a las Releases. Añadir o cambiar archivos del código no afecta al actualizador.

## Seguridad
- **Nunca** escribir contraseñas, tokens ni claves en el código: el repositorio es público y el código se puede extraer del `.exe`.
- La conexión con Control de Pedidos usa el **usuario y la contraseña de cada persona**, guardados cifrados en su propio equipo. El código no lleva ninguna clave compartida.
- El acceso a Administración se valida contra Control de Pedidos (`admin_auth.py`). La antigua contraseña fija se eliminó en v4.10.6: no reintroducir credenciales fijas (comentario ANTI-REGRESION en `main_agenda.py`).

## Historial compartido
`HISTORIAL_CAMBIOS.md` es **el mismo documento** que `docs/HISTORIAL_CAMBIOS.md` de Control Pedidos (y `docs/archivo/` el mismo archivo antiguo). Entrada más reciente arriba, cabecera `## AAAA-MM-DD HH:MM — [Componente] Título (versión)`, componentes: Organizador / Control Pedidos / Chat / Chat móvil / Infra. Cada cambio se anota en los dos repositorios con el mismo texto.

## Reglas de trabajo
1. Leer el código real antes de proponer cambios; buscar todos los usos de una función antes de modificarla.
2. Cada entrega: versión nueva (número par), `release_notes_actual.txt`, entrada arriba en `release_notes/release_notes.md` y en `HISTORIAL_CAMBIOS.md` (en los dos repositorios), y manuales si cambia algo visible.
3. Trabajar en rama y con PR; **no hacer push a `main` sin confirmación de Víctor**.
4. Los errores que se encuentren se reparan aunque ya estuvieran, en un commit propio.
5. Conservar siempre la línea de autoría en documentos y cabeceras, y añadirla en los nuevos.
6. Sin Windows no se puede probar la interfaz real: compilar con `python -m py_compile` y probar la lógica aislada (como en `test_filtrado_popups.py`), y decir claramente qué queda por probar en Windows.
7. Pruebas (se lanzan también en la compilación automática): `python test_filtrado_popups.py`, `python test_estructura.py`, `python test_limite_github.py`, `python test_bd_y_acceso.py`, `python test_markdown_texto.py`, `python test_fecha_hora.py`, `python test_actualizacion.py`, `python test_emoticonos.py`, `python test_avatares.py`, `python test_chat_fase1.py`, `python test_chat_fase2.py`, `python test_chat_fase3.py`, `python test_control_pedidos.py` y `python test_portatil.py`. `test_estructura` y `test_limite_github` simulan Tkinter si no está instalado.
   **Prueba de uso** (`pruebas_uso/`, ver su README): arranca el Organizador real en Linux con pantalla virtual y lo maneja con «usuario prueba» (31 comprobaciones y una captura por pantalla). Ejecutarla tras cambios en la interfaz. No envía mensajes de chat ni crea pedidos salvo que se pida (`CHAT_DESTINO`, `CREAR_PEDIDO_PR=1`).
8. **Nunca importar `main_agenda` desde otro módulo**: es el script de arranque (`__main__`) y el import vuelve a ejecutar la aplicación entera (pasó en `pedidos_agenda_bridge.py` hasta v4.18.06). Lo compartido va en `app/`. Lo vigila `test_estructura.py`.

## Pendientes para la próxima versión
1. **Quitar `USUARIOS_INICIALES`** (`app/db/sqlite.py`; acordado con Víctor el 11 nov 2026). Es una lista fija de usuarios de Windows del departamento con el nombre real de cada compañero, que solo sirve para el saludo del menú principal (`get_nombre_usuario`, `_init_db_usuarios`). No da acceso a nada, se queda desfasada (equipos nuevos o con otro usuario de Windows saludan con el usuario, p. ej. «victo») y deja datos personales en un repositorio público. Hacer:
   - quitar la lista y el `INSERT OR IGNORE` de `_init_db_usuarios`;
   - guardar como `nombre_real` el nombre que devuelve Control de Pedidos al entrar con la cuenta de cada uno (`/api/bridge/login` ya lo da: `admin_auth.py` y `chat_client.login`);
   - sin cuenta configurada, saludar con el usuario de Windows y seguir permitiendo cambiarlo en Administración → Mi Usuario;
   - los equipos que ya tienen el nombre guardado en `usuarios.db` no deben notar nada;
   - ampliar `test_bd_y_acceso.py`.
2. **Propuesto, sin decidir:** que el desinstalador no borre `%APPDATA%\OrganizadorPrincess` (`[UninstallDelete]` del `.iss`), para que una reinstalación conserve la configuración, «Mi Usuario», la agenda y sus copias.
