# Prueba de uso del Organizador (Linux, pantalla virtual)

> **Autoría:** la idea y el desarrollo de la aplicación Organizador Princess, incluidas sus pruebas, son de **Víctor Alejandro Martín Andrade**, para el Departamento de Central de Compras de Princess Hotels en Canarias. Ver `AUTORIA.md`.

Arranca el Organizador **de verdad** (`main_agenda.py`, Tkinter + ttkbootstrap) en una pantalla virtual (Xvfb) y lo maneja como lo haría una persona: abre ventanas, rellena campos, pulsa botones, hace una captura de cada pantalla y comprueba el resultado. Se conecta a Control de Pedidos y al chat reales con **«usuario prueba»**.

Lo propio de Windows se simula: el bloqueo de instancia única (`ctypes.windll`), los sonidos (`winsound`), `os.startfile` y el cifrado DPAPI (en Linux la contraseña se guarda sin cifrar, pero en un perfil temporal que se borra al terminar). Los mensajes de `messagebox` se anotan en el registro y se responden solos con «Aceptar» o «Sí».

## Qué comprueba (23 comprobaciones)
1. Primer arranque: ventana «Nueva versión», aviso «Versión actualizada» y saludo diario.
2. Agenda: crear un aviso, verlo en «Mis Recordatorios» y en `agenda.json`.
3. Calendario (mes y semana), vacaciones y festivos.
4. Administración: entrar con la contraseña; configurar un acceso dorado (web) y un botón azul (carpeta) y comprobar que abren lo suyo; vista reducida y extendida; exportar e importar la configuración (la importación cierra la aplicación a propósito).
5. El aviso de la agenda salta a su hora («🔔 AVISO», se cierra con «Entendido»).
6. Chat: abre la ventana y carga las conversaciones. Solo envía un mensaje si se indica `CHAT_DESTINO`.
7. Control de Pedidos: con `CREAR_PEDIDO_PR=1` crea un pedido en el hotel PR y lo cancela (el aviso real puede tardar unos minutos en llegar); siempre comprueba con una notificación simulada que el Organizador la muestra como aviso emergente.
8. Aviso de conexión con Control de Pedidos (error corregido en 4.18.06: no vuelve a cargar `main_agenda`).
9. «Actualización disponible» con una versión simulada en GitHub (no se descarga nada).

## Cómo lanzarla
Requisitos: `python3` con `tkinter`, `xvfb-run`, ImageMagick (`import`) y los paquetes de `compilacion/requisitos.txt` (PyInstaller no hace falta).

```bash
CLAVE_PRUEBA_ARCHIVO=/ruta/a/clave.txt pruebas_uso/ejecutar.sh
```

- `CLAVE_PRUEBA_ARCHIVO`: archivo con la contraseña de «usuario prueba» (nunca se imprime ni se guarda en la salida).
- `CHAT_DESTINO=usuario`: envía **un** mensaje de prueba a ese usuario del chat. Sin esta variable no se envía nada.
- `CREAR_PEDIDO_PR=1`: crea y cancela un pedido de prueba en el hotel PR. Sin ella no se toca Control de Pedidos.
- `PYTHON=/ruta/python` y `TIEMPO=segundos` (600 por defecto).

Las capturas (`NN_nombre.png`), el registro del conductor y los de la aplicación quedan en `pruebas_uso/salida/`. El script termina con código 0 solo si todo está bien.

## Qué no cubre
El aspecto exacto en Windows (fuentes Segoe UI, escalado), el `.exe` compilado, el instalador, arrastrar y soltar archivos en el chat (`dnd_windows.py`) y el cifrado DPAPI real. Eso se prueba con el instalador en borrador de «Compilar Organizador».
