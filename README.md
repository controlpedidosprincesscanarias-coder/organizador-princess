# Organizador Princess
**Central de Compras Princess Canarias – © VAMA 2026**

Aplicación de escritorio desarrollada en **Python + ttkbootstrap**, que combina una agenda/calendario con avisos programados y un sistema de accesos rápidos a carpetas y aplicaciones internas. Se integra en tiempo real con **Control de Pedidos** (la app web del departamento) a través de un sistema de notificaciones en segundo plano (bridge), mostrando como popup en pantalla los mismos avisos que se envían por Telegram — solo para el usuario y rol correspondiente.

---

## 📌 Características principales

- 📅 Agenda con eventos, avisos recurrentes y calendario con colores, imprimible por día/semana/mes.
- 🏖 Gestión de Vacaciones y Festivos.
- 🔔 Sistema de notificaciones en segundo plano (bridge) conectado a Control de Pedidos: recibe los mismos avisos que Telegram (techo de gastos, familias repetidas, solicitudes de usuario, cambios de estado de pedidos…) como popup en pantalla, filtrados automáticamente según el usuario y su rol.
- 🔄 Actualizaciones automáticas desde GitHub Releases, con ventana de "novedades" al terminar de instalar.
- 🖼️ Interfaz basada en **ttkbootstrap**, con logo corporativo embebido e icono multirresolución para Windows.
- 📖 Manual de Usuario accesible desde la propia aplicación.
- 🗂️ Compatible con Windows 10/11, distribuido como instalador `.exe` (Inno Setup) — no requiere tener Python instalado en el equipo destino.

---

## 📁 Estructura del proyecto

```
/
├── main_agenda.py                 (punto de entrada de la aplicación)
├── pedidos_agenda_bridge.py       (sistema de notificaciones — conexión con Control de Pedidos)
├── app/
│   ├── context.py                 (AppContext — dependencias compartidas)
│   ├── db/sqlite.py                (persistencia local: config, credenciales del bridge…)
│   ├── negocio/
│   │   ├── alertas.py              (procesamiento de avisos y recordatorios)
│   │   └── correo.py
│   ├── services/update_service.py  (comprobación de versión y novedades vía GitHub Releases)
│   ├── ui/
│   │   ├── agenda_helpers.py, festivos.py, vacaciones.py, ventana_config.py, saludo.py, assets.py, importexport.py
│   │   └── __init__.py
│   └── utils/
│       ├── fechas.py, rutas.py, sonido.py
├── assets/                         (logo.ico multirresolución, imágenes del wizard de instalación)
├── release_notes/
│   ├── release_notes.md            (historial completo acumulado — nombre fijo, no lleva versión)
│   └── release_notes_actual.txt    (solo la versión actual, texto plano — se muestra en el instalador)
├── OrganizadorPrincess_Setup.iss   (script de Inno Setup)
├── Manual_Usuario_OrganizadorPrincess.pdf
└── README.md
```

---

## 🧩 Requisitos

### Para ejecutar en modo desarrollo
- Python 3.10 – 3.13
- pip actualizado
- Librerías necesarias:

```
pip install ttkbootstrap pillow pyinstaller requests "python-socketio[client]" websocket-client cryptography
```

---

## ▶️ Ejecución en modo desarrollo

```
python main_agenda.py
```

El sistema de notificaciones (bridge) arranca automáticamente junto con la aplicación principal; no requiere ejecutarse por separado. Las credenciales de conexión con Control de Pedidos se configuran desde **Admin → Mi Usuario** dentro de la propia app, y quedan guardadas localmente (SQLite).

Para depurar el bridge de forma aislada, su actividad (sincronizaciones, notificaciones push recibidas, errores internos) queda registrada en:

```
%APPDATA%\OrganizadorPrincess\pedidos_bridge.log
```

---

## 🛠️ Compilación a .EXE (Windows)

### 1. Compilar el ejecutable con PyInstaller

```
pyinstaller main.spec
```

El ejecutable resultante queda en `dist/OrganizadorPrincess.exe`.

### 2. Preparar las notas de la versión

Antes de generar el instalador, en cada release:

1. Antepón la nueva sección arriba de `release_notes/release_notes.md` (formato Markdown, historial acumulado).
2. Sustituye el contenido de `release_notes/release_notes_actual.txt` por esa misma sección, en texto plano (Inno Setup no renderiza Markdown).
3. Sube `APP_VERSION` en `main_agenda.py` y `MyAppVersion` en `OrganizadorPrincess_Setup.iss` al mismo número.

### 3. Compilar el instalador con Inno Setup

Abre `OrganizadorPrincess_Setup.iss` en Inno Setup Compiler y compila (`Ctrl+F9`). El instalador se genera en `dist_installer/`, y al terminar la instalación muestra automáticamente las novedades de `release_notes_actual.txt`.

### 4. Publicar el release en GitHub

Crea un release con el tag `vX.Y.Z` (debe coincidir exactamente con `APP_VERSION`) y pega como descripción la sección correspondiente de `release_notes.md` — es el `body` que lee `app/services/update_service.py` para mostrar la ventana de "novedades" dentro de la app.

---

## 🔔 Sistema de notificaciones (bridge)

`pedidos_agenda_bridge.py` sondea periódicamente Control de Pedidos (cada 15 segundos) para comprobar si hay avisos pendientes para el usuario conectado. El filtrado por destinatario lo hace el propio servidor (cada usuario solo recibe lo suyo); el bridge se limita a mostrar en pantalla lo que el servidor le entrega.

Se autentica mediante `/api/bridge/login`, una vía de acceso dedicada para procesos en segundo plano (distinta del login normal de la web), pensada para reconectar automáticamente sin intervención humana.

---

## 🖼️ Logo e icono

- El logo principal está incrustado en Base64 dentro de `main_agenda.py` — no depende de archivos externos.
- `assets/logo.ico` debe incluir las resoluciones 16, 24, 32, 48, 64, 128 y 256 px. Si falta alguna capa, Windows muestra una carpeta amarilla genérica en vez del icono.
