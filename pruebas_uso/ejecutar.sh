#!/usr/bin/env bash
# Prueba de uso del Organizador Princess en Linux con pantalla virtual (Xvfb).
# La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
# Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.
#
# Uso: CLAVE_PRUEBA_ARCHIVO=/ruta/clave.txt pruebas_uso/ejecutar.sh [carpeta_salida] [pasos.py]
# Requisitos: python3 con tkinter, Xvfb (xvfb-run), ImageMagick (import) y los paquetes de
# compilacion/requisitos.txt (menos pyinstaller). Ver pruebas_uso/README.md.
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
SALIDA="${1:-$RAIZ/pruebas_uso/salida}"
PASOS="${2:-$RAIZ/pruebas_uso/pasos_uso.py}"
PY="${PYTHON:-python3}"
: "${CLAVE_PRUEBA_ARCHIVO:?indica el archivo con la contraseña de «usuario prueba» en CLAVE_PRUEBA_ARCHIVO}"

# Perfil limpio y aislado: nunca toca la carpeta de datos real
PERFIL="$(mktemp -d -t organizador_perfil_XXXX)"
trap 'rm -rf "$PERFIL"' EXIT
export APPDATA="$PERFIL" LOCALAPPDATA="$PERFIL" USERNAME="usuario prueba"
(cd "$RAIZ" && "$PY" -c "
import os, sys; sys.path.insert(0, 'app')
from db.sqlite import update_bridge_credentials
update_bridge_credentials('usuario prueba', 'usuario prueba', open(os.environ['CLAVE_PRUEBA_ARCHIVO']).read().strip())")

rm -rf "$SALIDA"; mkdir -p "$SALIDA"
set +e
timeout "${TIEMPO:-600}" xvfb-run -a -s "-screen 0 1400x900x24" \
    "$PY" "$RAIZ/pruebas_uso/conductor.py" "$RAIZ" "$SALIDA" "$PASOS" > "$SALIDA/salida_app.log" 2>&1
codigo=$?
set -e
cp "$PERFIL"/OrganizadorPrincess/*.log "$SALIDA/" 2>/dev/null || true
grep -E "OK |FALLO|RESUMEN|EXCEPCIÓN:" "$SALIDA/conductor.log" || true
echo "Capturas y registros en: $SALIDA (código $codigo)"
grep -q "RESUMEN: .* 0 fallos, 0 excepciones" "$SALIDA/conductor.log"
