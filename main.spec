# -*- mode: python ; coding: utf-8 -*-
# ============================================================
# main.spec — Organizador de Escritorio
# Central Compras Princess Canarias — © VAMA 2026
# Revisado para Fase 2: estructura modular con carpeta app/
# ============================================================
from PyInstaller.utils.hooks import collect_all, collect_data_files
import os

datas = []
binaries = []
hiddenimports = []

# ── ttkbootstrap: temas, estilos y fuentes incrustadas ──────
tmp = collect_all('ttkbootstrap')
datas     += tmp[0]
binaries  += tmp[1]
hiddenimports += tmp[2]

# ── Pillow: formatos de imagen necesarios ───────────────────
tmp = collect_all('PIL')
datas     += tmp[0]
binaries  += tmp[1]
hiddenimports += tmp[2]

# ── cryptography (Fernet): cifrado local de credenciales Admin ─────
# Tiene extensión C (cffi/openssl bindings) que PyInstaller no detecta
# con un simple hiddenimport si no se usa collect_all — sin esto el .exe
# arranca pero el login Admin falla en silencio con ImportError la
# primera vez que alguien abre esa ventana.
try:
    tmp = collect_all('cryptography')
    datas     += tmp[0]
    binaries  += tmp[1]
    hiddenimports += tmp[2]
except Exception:
    print("[AVISO] No se pudo recolectar 'cryptography' — instálala con el "
          "mismo Python que ejecuta PyInstaller: python -m pip install cryptography")

# ── Icono .ico (barra de título Windows) ────────────────────
datas += [('assets/logo.ico', 'assets')]

# (v4.18.54) Manual y notas de las versiones DENTRO del .exe, para la copia portátil (sin instalar), que no
# los tiene al lado. El instalador los sigue copiando junto al programa (se usan primero los de fuera).
datas += [('Manual_Usuario_OrganizadorPrincess.pdf', 'documentos'),
          ('release_notes/release_notes.md', 'documentos/release_notes')]

# ── Módulos propios de app/ ──────────────────────────────────
# PyInstaller no detecta automáticamente los imports dinámicos
# (sys.path.insert). Se declaran explícitamente aquí.
hiddenimports += [
    'db.sqlite',
    'ui.dnd_windows',    # v4.18.00: arrastrar y soltar archivos en el chat
    'db.dpapi',          # v4.16.9: cifrado de la contraseña del puente con DPAPI
    'utils.fechas',
    'utils.sonido',
    'utils.rutas',       # ANTI-REGRESION: _lanzar_ruta movida aquí desde main_agenda
    'negocio.correo',
    'negocio.alertas',
    'services.update_service',
    'services.portatil',     # v4.18.54: copia portátil (sin instalar) y su actualización
    'services.vinculo_navegador',  # v4.18.60: navegador de este PC vinculado con Control Pedidos
    'ui.primer_arranque_portatil',  # v4.18.54: carpeta, arranque con Windows y escritorio de la portátil
    'services.admin_auth',   # ANTI-REGRESION: nuevo — sistema de login Admin sin hardcode
    'ui.assets',
    'ui.saludo',
    'ui.agenda',         # v4.18.08: ventana Agenda de Avisos (antes en main_agenda)
    'ui.colores',        # v4.18.08: colores comunes
    'ui.calendario',     # v4.18.08: ventana Calendario (antes en main_agenda)
    'ui.admin',          # v4.18.08: Administración (antes en main_agenda)
    'ui.disposicion',    # v4.18.08: constantes del menú y vista
    'ui.markdown_texto', # v4.18.10: novedades con formato en «Actualización disponible»
    'ui.selector_fecha_hora',  # v4.18.14: calendario 📅 y ruedas de hora en los formularios
    'ui.emoticonos',     # v4.18.18: panel 😊 del chat
    'ui.chat_movil',     # v4.18.24: ventana «Chat en el móvil» (QR de la app Android)
    'ui.avatares',       # v4.18.28: fotos de perfil del chat
    'ui.miniaturas',     # v4.18.44: miniaturas de las imágenes del chat
    'ui.notas_version',  # v4.18.44: notas de la versión al pulsar el número de versión
    'ui.acciones_chat',  # v4.18.46: responder citando, reenviar y eliminar en el chat
    'ui.grupo_info',     # v4.18.48: integrantes y gestión de los grupos del chat
    'ui.agenda_helpers',
    'ui.importexport',
    'ui.vacaciones',
    'ui.festivos',
    'ui.ventana_config',
    'ui.ventana_chat',
    'services.chat_client',
    'context',
]

# ── Chat en tiempo real (v4.8.0): python-socketio + engineio + requests ─────
# collect_all es necesario porque engineio elige el driver de transporte
# (websocket / polling) de forma dinámica según lo que detecte instalado;
# sin esto, PyInstaller no empaqueta esos módulos y el chat falla en
# silencio solo en el .exe (funciona en `python main_agenda.py` porque ahí
# sí ve el entorno completo).
for _pkg in ('socketio', 'engineio', 'requests', 'websocket', 'urllib3', 'idna',
             'certifi', 'charset_normalizer'):
    try:
        tmp = collect_all(_pkg)
        datas     += tmp[0]
        binaries  += tmp[1]
        hiddenimports += tmp[2]
    except Exception:
        # Si el paquete no está instalado en el entorno donde corre
        # PyInstaller, collect_all() lanza excepción y PARA la compilación
        # entera sin generar ningún .exe. Si ves este bloque saltarse en
        # la consola de compilar.bat, es la prueba de que ese paquete no
        # está instalado en el Python que usa PyInstaller — instálalo con
        # el MISMO intérprete: python -m pip install requests
        # "python-socketio[client]" websocket-client
        print(f"[AVISO] No se pudo recolectar '{_pkg}' — revisa que esté "
              f"instalado con el mismo Python que ejecuta PyInstaller.")

# Refuerzo explícito (no está de más aunque collect_all ya los incluya):
# submódulos que a veces quedan fuera si el árbol de imports de requests/
# engineio se resuelve de forma perezosa (try/except ImportError) en vez
# de con un "import" estático que PyInstaller pueda ver por sí solo.
hiddenimports += [
    'requests', 'requests.adapters', 'requests.models', 'requests.sessions',
    'requests.compat', 'requests.utils',
    'urllib3', 'urllib3.util', 'urllib3.util.retry',
    'idna', 'certifi', 'charset_normalizer',
    'engineio', 'engineio.client', 'engineio.async_client',
    'socketio', 'socketio.client',
    'websocket', 'websocket._app',
]

# ── Incluir la carpeta app/ entera en el bundle ──────────────
# Se añade como dato para que los módulos sean localizables
# en runtime dentro del ejecutable empaquetado.
app_root = 'app'
for folder in ['db', 'utils', 'negocio', 'services', 'ui']:
    src = os.path.join(app_root, folder)
    datas += [(src, folder)]          # destino: carpeta raíz del bundle

# ── Imports ocultos adicionales ──────────────────────────────
hiddenimports += [
    'PIL._tkinter_finder',
    'ttkbootstrap.themes',
    'tkinter',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'json',
    'base64',
    'subprocess',
    'threading',
    'winsound',
    'sqlite3',
    'queue',
    'urllib.parse',
    'urllib.request',
    'ssl',
    'socket',
    'shutil',
    'tempfile',
    'zipfile',
]

a = Analysis(
    ['main_agenda.py'],
    pathex=['app'],              # ← añadido: PyInstaller busca imports en app/
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'scipy', 'pandas',
        'PyQt5', 'PyQt6', 'wx',
    ],
    noarchive=False,
    optimize=0,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='OrganizadorPrincess',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo.ico',
    version_file=None,
)
