# Fuentes de los manuales del Organizador Princess

> **Autoría:** la idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de **Víctor Alejandro Martín Andrade**, para el Departamento de Central de Compras de Princess Hotels en Canarias. Ver `AUTORIA.md`.

Con estos archivos se generan los dos manuales, con el mismo estilo que los de Control de Pedidos:

- **Manual de usuario**: `docs/Manual_Usuario_OrganizadorPrincess.{docx,pdf}` y la copia de la raíz, `Manual_Usuario_OrganizadorPrincess.pdf`. Esa copia es la que abre el botón «Manual» y la que copia el instalador junto al programa: **el nombre del archivo no se puede cambiar**.
- **Manual de administrador**: `docs/Manual_Administrador_OrganizadorPrincess.{docx,pdf}` (menú Inicio → Manual de Administrador).

Las capturas son del **Organizador de verdad**, arrancado en Linux con pantalla virtual, con **datos de ejemplo inventados** y **sin red**: no se conecta a Control de Pedidos, al chat ni a GitHub, y nunca toca una carpeta de datos real.

| Archivo | Para qué sirve |
|---|---|
| `capturas.sh` | Crea un perfil temporal, arranca el Organizador en Xvfb con la simulación y guarda las capturas en `cap/`. |
| `perfil_demo.py` | Botones, avisos, vacaciones, festivos y el nombre «Ana Demo» del perfil de ejemplo. |
| `simulacion/sitecustomize.py` | Corta la red, sustituye el chat por conversaciones inventadas y acepta la contraseña «demo» en Admin. Solo se carga desde `capturas.sh` (va en `PYTHONPATH`). |
| `pasos_capturas.py` | Recorre las pantallas con `pruebas_uso/conductor.py`: recorta cada ventana al doble de tamaño, le pone una barra de título como la de Windows y dibuja los números de referencia en naranja. |
| `lib.js` | Maquetación común (portada, índice, leyendas numeradas, recuadros, tablas) con la librería `docx` de Node, adaptada de la de Control de Pedidos. |
| `manual_usuario.js`, `manual_admin.js` | Texto de cada manual. |
| `badges/` | Números redondos de las leyendas. |
| `generar.sh` | Genera el `.docx` y el `.pdf` (LibreOffice) de un manual. |

## Cómo actualizar los manuales

Requisitos: los de `pruebas_uso/` (Python 3 con tkinter, Xvfb e ImageMagick, y los paquetes de `compilacion/requisitos.txt` salvo PyInstaller), Node con el paquete `docx` y LibreOffice.

```bash
PYTHON=/ruta/al/python docs/manuales_fuente/capturas.sh
```
```bash
docs/manuales_fuente/generar.sh usuario
```
```bash
docs/manuales_fuente/generar.sh admin
```

`SOLO=a_` repite solo las capturas que empiezan por ese prefijo y `VOLCAR=1` guarda, junto a cada captura, la lista de widgets con su posición (sirve para colocar las marcas). Las capturas (`cap/`) y la salida (`salida/`) no se guardan en el repositorio.

Antes de copiar los manuales a `docs/` (y el de usuario también a la raíz), revisar el PDF página a página. Al cambiar de versión, ajustar `VERSION` (variable de entorno o valor por defecto en cada `manual_*.js`). Los manuales nuevos llegan a los equipos con el instalador de la versión siguiente.
