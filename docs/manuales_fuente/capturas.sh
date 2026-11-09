#!/usr/bin/env bash
# Capturas de los manuales del Organizador Princess con datos inventados y sin red (ver README.md).
# La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
# Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.
#
# Uso: docs/manuales_fuente/capturas.sh [carpeta_salida]     (por defecto docs/manuales_fuente/cap)
# Variables: PYTHON (intérprete con los paquetes de compilacion/requisitos.txt), SOLO=prefijo, VOLCAR=1
# Requisitos: python3 con tkinter, Xvfb (xvfb-run) e ImageMagick (import), como pruebas_uso/.
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(cd "$AQUI/../.." && pwd)"
SALIDA="${1:-$AQUI/cap}"
PY="${PYTHON:-python3}"

# Perfil de usar y tirar: nunca toca la carpeta de datos real
PERFIL="$(mktemp -d -t organizador_manual_XXXX)"
trap 'rm -rf "$PERFIL"' EXIT
export APPDATA="$PERFIL" LOCALAPPDATA="$PERFIL" USERNAME="compras.demo" ORG_RAIZ="$RAIZ"
"$PY" "$AQUI/perfil_demo.py" "$RAIZ"

mkdir -p "$SALIDA"
set +e
PYTHONPATH="$AQUI/simulacion" timeout "${TIEMPO:-300}" xvfb-run -a -s "-screen 0 1400x900x24" \
    "$PY" "$RAIZ/pruebas_uso/conductor.py" "$RAIZ" "$SALIDA" "$AQUI/pasos_capturas.py" > "$SALIDA/salida_app.log" 2>&1
codigo=$?
set -e
cp "$PERFIL"/OrganizadorPrincess/*.log "$SALIDA/" 2>/dev/null || true
grep -E "✓|⚠|ERROR|EXCEPCIÓN" "$SALIDA/conductor.log" || true
echo "Capturas en: $SALIDA (código $codigo)"
