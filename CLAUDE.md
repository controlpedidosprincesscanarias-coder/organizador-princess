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
- `pedidos_agenda_bridge.py` — conexión con Control de Pedidos (`/api/bridge/login`, `/api/bridge/alertas`, `/api/bridge/notificaciones`) a través del Worker `proxy.controlpedidosprincess-canarias.workers.dev`.
- `app/services/` — `update_service.py` (actualizaciones: al arrancar y cada 2 h con margen al azar, `_programar_siguiente_check`; el límite de consultas de GitHub se espera en silencio, `_espera_por_limite_github`), `chat_client.py` (chat, Worker `proxy-chat.controlpedidosprincess-canarias.workers.dev`), `admin_auth.py` (acceso a Administración).
- `app/negocio/` — `alertas.py` (popups y recordatorios; `_AUTOCIERRE_BRIDGE_MIN`), `correo.py`.
- `app/ui/` — ventanas (chat, configuración, festivos, vacaciones, saludo…); `selector_fecha_hora.py` (calendario 📅 y ruedas de hora de los formularios de avisos, vacaciones y festivos; la lógica de lo escrito a mano, en `utils/fechas.py`); `dnd_windows.py` (arrastrar y soltar en el chat, desactivable con `"chat_arrastrar_soltar": false` en `config.json`).
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
- El repositorio guarda el **código** junto a las Releases. Añadir o cambiar archivos del código no afecta al actualizador.

## Seguridad
- **Nunca** escribir contraseñas, tokens ni claves en el código: el repositorio es público y el código se puede extraer del `.exe`.
- La conexión con Control de Pedidos usa el **usuario y la contraseña de cada persona**, guardados cifrados en su propio equipo. El código no lleva ninguna clave compartida.
- El acceso a Administración se valida contra Control de Pedidos (`admin_auth.py`). La antigua contraseña fija se eliminó en v4.10.6: no reintroducir credenciales fijas (comentario ANTI-REGRESION en `main_agenda.py`).

## Historial compartido
`HISTORIAL_CAMBIOS.md` es **el mismo documento** que `docs/HISTORIAL_CAMBIOS.md` de Control Pedidos (y `docs/archivo/` el mismo archivo antiguo). Entrada más reciente arriba, cabecera `## AAAA-MM-DD HH:MM — [Componente] Título (versión)`, componentes: Organizador / Control Pedidos / Chat / Infra. Cada cambio se anota en los dos repositorios con el mismo texto.

## Reglas de trabajo
1. Leer el código real antes de proponer cambios; buscar todos los usos de una función antes de modificarla.
2. Cada entrega: versión nueva (número par), `release_notes_actual.txt`, entrada arriba en `release_notes/release_notes.md` y en `HISTORIAL_CAMBIOS.md` (en los dos repositorios), y manuales si cambia algo visible.
3. Trabajar en rama y con PR; **no hacer push a `main` sin confirmación de Víctor**.
4. Los errores que se encuentren se reparan aunque ya estuvieran, en un commit propio.
5. Conservar siempre la línea de autoría en documentos y cabeceras, y añadirla en los nuevos.
6. Sin Windows no se puede probar la interfaz real: compilar con `python -m py_compile` y probar la lógica aislada (como en `test_filtrado_popups.py`), y decir claramente qué queda por probar en Windows.
7. Pruebas (se lanzan también en la compilación automática): `python test_filtrado_popups.py`, `python test_estructura.py`, `python test_limite_github.py`, `python test_bd_y_acceso.py`, `python test_markdown_texto.py` y `python test_fecha_hora.py`. `test_estructura` y `test_limite_github` simulan Tkinter si no está instalado.
   **Prueba de uso** (`pruebas_uso/`, ver su README): arranca el Organizador real en Linux con pantalla virtual y lo maneja con «usuario prueba» (31 comprobaciones y una captura por pantalla). Ejecutarla tras cambios en la interfaz. No envía mensajes de chat ni crea pedidos salvo que se pida (`CHAT_DESTINO`, `CREAR_PEDIDO_PR=1`).
8. **Nunca importar `main_agenda` desde otro módulo**: es el script de arranque (`__main__`) y el import vuelve a ejecutar la aplicación entera (pasó en `pedidos_agenda_bridge.py` hasta v4.18.06). Lo compartido va en `app/`. Lo vigila `test_estructura.py`.
