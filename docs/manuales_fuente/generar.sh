#!/bin/bash
# Genera un manual del Organizador Princess (docx + pdf) a partir de las capturas de ./cap
# La idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de
# Víctor Alejandro Martín Andrade, para el Departamento de Central de Compras de Princess Hotels en Canarias.
# Uso: ./generar.sh usuario|admin      (necesita Node con el paquete «docx» y LibreOffice)
set -e
cd "$(dirname "$0")"
case "$1" in
  usuario) JS=manual_usuario.js; NOMBRE=Manual_Usuario_OrganizadorPrincess ;;
  admin)   JS=manual_admin.js;   NOMBRE=Manual_Administrador_OrganizadorPrincess ;;
  *) echo "Uso: $0 usuario|admin"; exit 1 ;;
esac
mkdir -p salida
node "$JS" "salida/$NOMBRE.docx"
(cd salida && zip -d "$NOMBRE.docx" '*/' >/dev/null 2>&1 || true)
soffice --headless --convert-to pdf --outdir salida "salida/$NOMBRE.docx" >/dev/null
echo "Listo: salida/$NOMBRE.docx y .pdf (revisarlos y copiarlos a docs/; el de usuario, también a la raíz)"
