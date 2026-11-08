# Historial de Cambios — Ecosistema Princess Compras (unificado)

> **Autoría:** la idea y el desarrollo de la aplicación Control Pedidos Princess Canarias, incluidas sus pruebas, son de **Víctor Alejandro Martín Andrade**, para el Departamento de Central de Compras de Princess Hotels en Canarias. Ver `AUTORIA.md`.

> Documento único de seguimiento. Se actualiza cambio a cambio, entrada
> más reciente arriba. Componentes: **Organizador** (main_agenda,
> desktop), **Control Pedidos** (backend Flask principal), **Chat**
> (backend Flask/SocketIO independiente), **DALI** (catálogo de
> artículos/materiales — repo `dali-sap-articulos-app`, aparte pero
> integrado con Control Pedidos vía SSO desde el 2026-08-14, ver más
> abajo), **Infra** (Render / Cloudflare / GitHub Actions, no es código
> de la app).

> **Normas de entrega (obligatorias para cualquier cambio, ya lo
> implemente Claude, otra IA o cualquier programador humano):**
> 1. No se entrega el proyecto completo (ni el ZIP entero): solo los
>    archivos individuales modificados o creados, indicando su ruta
>    dentro del proyecto.
> 2. Toda entrega debe registrar una entrada nueva aquí (más reciente
>    arriba) y en `CHANGELOG.md`, describiendo petición, causa/hallazgo
>    y corrección aplicada.
> 3. `README.md`: la línea "Versión actual" se actualiza en **todas**
>    las entregas, sin excepción (no solo cuando el cambio es visible) —
>    quedó desincronizada 2 versiones seguidas (v12.30.82 y v12.30.83) por
>    no tratarla como obligatoria, ver entrada de la v12.30.83. Además,
>    el resto del README (funcionalidades, requisitos, secciones como
>    "Rendimiento") se actualiza si el cambio afecta a algo que documenta.
> 4. Subir el número de versión en el badge de `templates/index.html`
>    (formato `V MAJOR.MINOR.PATCH`), coherente con el de `CHANGELOG.md`
>    y esta entrada.
> 5. Revisar en cada entrega si el cambio afecta a algún otro documento
>    de mantenimiento del proyecto — `GUIA_DESPLIEGUE.md`,
>    `PENDIENTES.md`, `INSTRUCCIONES_RESTAURACION.md`,
>    `docs/hallazgo-seguridad-princess.md` — y actualizarlo si es así.
>    Dejar constancia en la entrada de este historial de qué se revisó,
>    aunque la conclusión sea "no aplica" (para que quede claro que se
>    comprobó y no que se olvidó).
>    **Nota sobre `docs/hallazgo-seguridad-princess.md`** (aclarada en
>    v12.32.46, tras una auditoría que señaló la ambigüedad): el archivo
>    no existe en este repo desde antes de v12.30.93 — no hay una entrada
>    previa que registre cuándo ni por qué se quitó de aquí, lo cual es en
>    sí mismo un incumplimiento de esta misma norma 5 que quedó sin
>    detectar hasta ahora. Lo que sí consta, verificado en v12.30.74: el
>    fallo que describía (contraseñas en texto plano sin hash) llevaba
>    corregido desde v12.29.37, mucho antes de esa fecha. Este documento
>    era, en origen, un análisis del proyecto DALI usando este backend
>    como referencia de qué NO hacer — su versión completa (con el
>    recuadro "✅ RESUELTO" añadido) sigue existiendo fuera de este repo.
>    A partir de aquí, las entradas de norma 5 pueden limitarse a "no
>    existe en este repo" sin repetir la explicación completa.

---

## 2026-11-08 16:48 — [Organizador / Control Pedidos] Código del Organizador en GitHub e historial unificado (v4.18.04 / v12.33.94)

- **Petición**: Víctor sube el código del Organizador para guardarlo en GitHub y que el historial vuelva a ser el mismo en los dos proyectos.
- **Organizador** (repo `organizador-princess`, rama `codigo/v4.18.04`):
  - código de la v4.16.8 y, encima, el de la **v4.18.04** (la publicada en la Release v4.18.4), tal cual;
  - fuera del repositorio: `__pycache__`, `Thumbs.db` y los ZIP del Chat;
  - `.gitignore`: `main.spec` sí se versiona; se ignoran `*.exe`, `*.zip` y `Thumbs.db`;
  - nuevos `CLAUDE.md` (normas, y sobre todo la actualización automática) y `AUTORIA.md`; línea de autoría en el `README.md`;
  - `HISTORIAL_CAMBIOS.md` y `docs/archivo/` iguales a los de Control Pedidos.
- **Revisado en el código del Organizador**:
  - sin contraseñas ni tokens escritos: la del puente es la de cada usuario, cifrada en su equipo;
  - el actualizador solo usa las Releases públicas (`releases/latest` y el `.sha256`), así que el repositorio **debe seguir siendo público**; subir el código no le afecta.
- **Control Pedidos**: el historial recupera 8 entradas del Organizador y del Chat que solo estaban en el del Organizador, cada una en su fecha:
  - Organizador v4.16.6, v4.16.8, v4.16.9, v4.18.00, v4.18.02 y v4.18.04;
  - Chat v1.2.1 y v1.2.2.
- **Nota**: en notas antiguas (Organizador v4.10.6) aparece citada la antigua contraseña fija de Administración, eliminada en esa versión. Ya no la usa nada. No debe reutilizarse en ninguna cuenta.

---

## 2026-11-08 16:24 — [Control Pedidos] Manuales regenerados con «DALI / SAP» (v12.33.92)

- **Petición**: Víctor pide fusionar y regenerar los manuales.
- **Cambio**:
  - Capturas nuevas con `docs/manuales_fuente/` (datos inventados en Postgres local).
  - Textos de los manuales con «DALI / SAP».
  - Nota sobre las referencias deducidas en el manual del Comprador.
  - `docs/Manual_Usuario_*.docx/.pdf` sustituidos (16, 29 y 22 páginas).
- **Fusión**: PR #3 fusionado en `main`. Los PR #4 a #7 van juntos en el #7 (base `main`), pendientes de que Víctor lo fusione desde GitHub.

---

## 2026-11-08 16:16 — [Control Pedidos] Referencias del proveedor en pedidos sin PDF oficial (v12.33.90)

- **Petición**: en la copia del pedido en PDF (pedidos sin PDF oficial subido) faltaba la referencia del proveedor; Víctor propone sacarla de otros PDF ya subidos, porque cada código DALI corresponde a una referencia de cada proveedor.
- **Cambio**:
  - `servicios/formato.py`: nuevas `_completar_refs_proveedor()` y `_norm_codigo_articulo()`.
    - Rellenan `ref_proveedor` vacía con la de las líneas `origen='pdf'` de otros pedidos del mismo `proveedor_id` y el mismo código, comparado sin espacios ni ceros a la izquierda.
    - Prefieren las no leídas por OCR y, después, la más reciente.
    - Solo modifican los diccionarios en memoria; no escriben en la BD.
  - Se usan en `servicios/pdf_pedido._generar_pdf_pedido` (copia en PDF) y en `GET /api/pedidos/<id>/lineas`, que añade el campo `refs_deducidas`.
  - `static/js/app.js`: en la tabla de artículos, la referencia deducida sale en azul con «*» y una nota.
- **Pruebas**:
  - `tests/test_referencias_proveedor.py`, nueva (11 OK);
  - huellas regeneradas (2 funciones nuevas y el campo nuevo en `/lineas`);
  - flujo (60) y E2E (57) OK.

---

## 2026-11-08 16:11 — [Control Pedidos] «DALI / SAP» en textos y trazabilidad automática (v12.33.88)

- **Petición**: Víctor quiere que se lea «DALI / SAP» mientras dure la transición entre ambos sistemas, también en la trazabilidad de los procesos automáticos.
- **Cambio**:
  - Textos visibles en `templates/index.html`, `static/js/app.js` e `importar_pedidos.js`, y mensajes al usuario en `rutas/` y `servicios/` (carga de listados, albaranes, correos, Telegram, copia del pedido en PDF).
  - `servicios/sap_comun.py`: `_AUTOR_SAP_AUTO` pasa a «Carga automática DALI / SAP»; «Carga automática SAP» se añade a `_AUTORES_SAP_AUTO_ANTIGUOS`, que ya se unifican al arrancar. Observaciones y notas del historial en el nuevo formato.
  - JS: `_esAutorCargaAuto()` reconoce el nombre antiguo y el nuevo.
  - Las búsquedas por la nota «Pedido creado automáticamente desde el listado …» admiten los dos formatos.
- ⚠️ **Datos de producción** (`core/migraciones.py`, paso 125, idempotente): renombra en `pedidos.observaciones` y `historial_estados.nota` los textos automáticos con el formato antiguo. El autor lo renombra el paso de unificación ya existente. Probado en BD local con datos simulados, ejecutando la migración dos veces.
- **Sin cambiar**: «Código SAP» del proveedor (dato distinto del código DALI), mensajes internos del log y nombres de funciones.
- **Revisado**: huella sin BD, huella BD, migraciones, flujo (60), hotel de pruebas (19) y E2E (57): todo OK.

---

## 2026-11-08 15:59 — [Control Pedidos] Retirada la ventana «Comparar listado PDF» (v12.33.86)

- **Petición**: Víctor decide retirar la ventana, que quedó sin botón desde la carga unificada de v12.32.97.
- **Cambio**:
  - `templates/index.html`: fuera `modal-comparar-pdf`.
  - `static/js/app.js`: fuera las funciones que solo usaba esa ventana:
    - `abrirModalCompararListado`, `compararListadoPdf`, `_pollCompararListadoPdf`, `_renderCompararPdfResultado`, `enviarResumenComparacionPdf`;
    - el bloque «Pedidos + Albaranes» (`_pollCompararListadoAlbaranes`…);
    - el bloque «Crear pedidos desde SAP» (`_cargarPedidosPendientesCrearSap`…);
    - `_crearPedidoDesdeComparacion`.
  - Ninguna tenía llamadas fuera de la propia ventana.
  - El servidor no cambia: «Cargar listados SAP» (`servicios/sap_carga_unificada.py`) sigue usando `servicios/sap_comparar_pdf.py`.
- **Pendiente anotado en CLAUDE.md**:
  - 5 endpoints que ya nada llama desde la interfaz;
  - otras dos ventanas sin botón: «Actualizar departamentos» e «Importar albaranes».
- **Revisado**: sintaxis JS OK, huella sin BD idéntica, E2E navegador 57 pasos sin errores.

---

## 2026-11-08 13:30 — [Control Pedidos] Manuales de usuario Hotel, Comprador y Administrador (v12.33.84)

- **Petición**: actualizar los manuales (Hotel V 12.33.19 y Comprador V 12.33.25), crear el de Administrador y hacerlos ilustrativos y fáciles de entender, con una mención sencilla al hotel PR.
- **Cambio**:
  - `docs/Manual_Usuario_HOTEL_Control_Pedidos.docx/.pdf` y `docs/Manual_Usuario_COMPRADOR_Control_Pedidos.docx/.pdf`, rehechos.
  - `docs/Manual_Usuario_ADMINISTRADOR_Control_Pedidos.docx/.pdf`, nuevo.
  - Capturas anotadas con datos inventados sobre una Postgres local.
  - `docs/manuales_fuente/`, nueva:
    - `demo_datos.py`, `demo_privacidad.sql`, `capturas.py` (Playwright);
    - `lib.js` y `manual_*.js` (docx de Node), `generar.sh` (LibreOffice) y `README.md`.
    - Las capturas y la salida quedan fuera del repositorio (`.gitignore`).
- **Hallazgo (sin corregir, pendiente de decidir)**: la ventana «Comparar listado PDF» (`modal-comparar-pdf`, `abrirModalCompararListado()` en `static/js/app.js`) no tiene ningún botón que la abra desde v12.32.97, cuando se unificó en «Cargar listados SAP». El manual de Administrador ya no la menciona. Queda decidir si se retira el código o se vuelve a enlazar.
- **Revisado**: los tres PDF, página a página; huella sin BD OK.

---

## 2026-11-08 12:40 — [Control Pedidos] Revisión final: permisos de alertas, fase 2, traza SAP, comentarios y limpieza (v12.33.82)

- **Petición**: dejar la aplicación sin errores y bien documentada.
- **Hallazgos y correcciones**:
  - `rutas/alertas.py`: `alerta_email_preview`, `alerta_enviar_email`, `alerta_log_whatsapp` y `alerta_enviar_telegram` solo comprobaban la sesión. Nuevo `_sin_permiso_alertas()`: 403 si el rol no es admin/compras; 404 si el pedido es del hotel PR y el usuario no puede verlo.
  - `rutas/solicitudes_acceso.py`: `registrar_envio_fase2` pasa a `@admin_required`.
  - `servicios/sap_albaranes_compra.py`: el filtro de la traza buscaba `app.py`. Nuevo `_es_codigo_propio()`, que reconoce cualquier archivo del proyecto (no site-packages); el mensaje incluye la ruta relativa.
  - 83 comentarios con «en app.py» / «templates/index.html» actualizados al módulo o JS real. Verificado: AST idéntico salvo `sap_albaranes_compra`.
  - pyflakes: importaciones y variables sin uso retiradas. Solo quedan las importaciones intencionadas de `app.py`.
- **Pruebas**: `tests/test_flujo.py` secciones 12-13 (cola de correos y avisos por alerta). Huellas regeneradas (función nueva). Huella, huella BD, migraciones, rotación EmailJS, techo, flujo, hotel de pruebas, E2E y las 11 tareas programadas: OK.

---

## 2026-11-08 12:05 — [Control Pedidos] Autoría en toda la documentación y el código (v12.33.80)

- **Petición**: dejar constancia en toda la documentación de que la idea y el desarrollo de la aplicación, incluidas las pruebas, son de Víctor Alejandro Martín Andrade para el Dpto. Central de Compras Princess en Canarias.
- **Cambio**:
  - `AUTORIA.md` nuevo.
  - Línea «Autoría» al principio de `README.md`, `CLAUDE.md`, este historial, `GUIA_DESPLIEGUE.md`, `INSTRUCCIONES_RESTAURACION.md` (junto al «© VAMA 2026» que ya tenía), `PENDIENTES.md`, `tests/CHECKLIST_PRUEBAS_MANUALES_TECHO.md` y los dos archivos de `docs/archivo/`.
  - En `CHANGELOG.md`, al final: `/api/changelog` lee la primera línea como versión.
  - Docstrings de `app.py`, `core/`, `servicios/`, `jobs/` y `rutas/` (`__init__.py`).
  - `<meta name="author">` en `templates/index.html`.
  - `CLAUDE.md`: sección «Autoría» con la regla de conservarla y añadirla en documentos nuevos.
- **Organizador**: este historial es compartido; al copiar las entradas al del Organizador, copiar también la línea de autoría de la cabecera si corresponde a ese proyecto.
- **Revisado**: huella sin BD (comprueba `/api/version` y `/api/changelog`) OK; sin cambios de código funcional.

## 2026-11-08 11:45 — [Control Pedidos] ETag débil para el Worker, caché del id de PR y notas de versión legibles (v12.33.78)

- **Despliegue de v12.33.76 (fusión del PR #1, `774a0c7`)**: Render desplegó solo a las 11:40 UTC y `/api/version` = `9a3eacfe51da` (el esperado). El aviso de nueva versión saltó en el navegador de Víctor (captura).
- **Sonda de admin en producción, antes (v12.33.52) y después (v12.33.76)**:
  - mismos códigos en las 47 rutas y misma forma del JSON;
  - tiempos parecidos (`/api/exportar` de 13,6 a 10,9 s);
  - el CSS y los 7 JS con un año de caché y gzip; logos con 7 días; cabeceras de seguridad iguales.
  - Comparada con la sonda local de v12.33.76, solo difiere `/api/dali/sso` (secreto ausente en local).
- **Hallazgo**: por el Worker, `index` seguía llegando sin ETag aunque ya llevaba comillas (`index_304_con_etag` = 200).
  - Directo a Render: `content-encoding: gzip` y `etag: "9a3eacfe51da"`.
  - Por el Worker: `content-encoding: br` y sin ETag.
  - `app.js` (gzip, sin recomprimir) y `favicon.png` sí conservan el suyo.
  - Cloudflare elimina los ETag fuertes cuando recomprime y conserva los débiles. La explicación de v12.33.74 (comillas) era incompleta: las comillas eran necesarias, pero no suficientes.
- **Corrección**:
  - `index()` envía `ETag: W/"<hash>"`; la comparación ya aceptaba todas las formas.
  - `tests/huella_app.py` exige el ETag débil y el 304.
- **Mejora de consumo**: `_id_hotel_pruebas()` guarda en memoria el id de PR (no se guarda si el hotel no existe). `_hotel_es_de_pruebas(hotel_id)` deja de consultar y `_pedido_es_de_pruebas` hace una consulta sin JOIN. Motivo: `_resolver_notificacion` se llama desde las tareas de cada minuto.
- **Notas de versión**: `_renderChangelog` (`static/js/nueva_version.js`) trata `# v…` como `## v…` y convierte `**negrita**`, `` `código` `` y sublistas con sangría (`  - `). Probado con captura del aviso simulando un despliegue, sin errores de JS.
- **Prueba**: batería completa en verde (huella sin BD regenerada: función nueva `_id_hotel_pruebas`; flujo 51, hotel de pruebas 19, E2E 57).
- **Pendiente**:
  - Tras desplegar, comprobar por el Worker que llega `etag: W/"…"` y que el condicional da 304.
  - Hacer el flujo con escritura en PR (proveedor PRUEBAS, departamento SSTT).
  - Copiar las entradas al historial del Organizador.
- **Revisado**: `CLAUDE.md` (nota del Worker), `README.md`, `CHANGELOG.md` y badge actualizados.

## 2026-11-08 11:35 — [Control Pedidos] Hotel de pruebas: todos sus avisos a «usuario prueba» (v12.33.76)

- **Petición**: que todas las pruebas (departamentos, etc.) vayan siempre al correo del usuario de pruebas.
- **Contexto**: antes de probar con escritura en producción se comprobó a quién avisaría un pedido de PR. PR no tiene compradores ni correo de departamento, pero los 4 contactos adicionales (`notificacion_contacto_reglas`) son globales por departamento («no varía por hotel»). Administrativo A&B, Chef Ejecutivo y Director Alojamiento reciben ENVIADO AL PROVEEDOR en los departamentos 1-5 y 8, y Director Compras recibe el exceso de techo autorizado en los 14. Además, las tareas de alertas no excluían PR (al contrario de lo que decía el comentario de `core/config.py`).
- **Puntos de salida cubiertos**:
  - **Correos**: todos los de pedidos pasan por la cola (`_encolar_email_sistema`, `_encolar_email_pedido_retrasado`; `enviar_emails_estado` ya solo encola). Se redirigen si `pedido_id` es de PR o, con el nuevo parámetro `hotel_id`, si el hotel es PR (resúmenes de comparar listado PDF y de albaranes).
  - **Propuesta manual de alertas**: `alerta_email_preview` → para PR, Para = cuenta de pruebas, sin CC, compradores ni WhatsApp, y con el aviso en el cuerpo.
  - **Telegram y avisos emergentes por hotel**: `_resolver_notificacion(evento, canal, hotel_id)` → para PR devuelve solo `usuario prueba`. Cubre `_enviar_telegram_compradores`, `_telegram_cambio_estado` y las tareas.
  - **Copias de supervisión a admins por hotel**: nuevo `_destinatarios_supervision` en `jobs/techo.py` (techo urgente y pedido sin autorización previa, por pedido) y en `jobs/alertas.py` (familia repetida).
- **Helpers** (`servicios/destinatarios.py`): `_usuario_pruebas`, `_hotel_es_de_pruebas`, `_pedido_es_de_pruebas` y `_redirigir_correo_pruebas`.
  - `_redirigir_correo_pruebas` cambia Para, CC y Responder a por los correos de `usuario prueba`, antepone «[PRUEBAS]» al asunto y un recuadro con los destinatarios originales (HTML y texto).
  - Sin correo de pruebas → `None` y no se encola.
- **No cubierto, a propósito**: correos de solicitudes de acceso, códigos de login y restablecimiento de contraseña (no están ligados a pedidos), y el puente con DALI (`rutas/externo.py`, correos de Catálogo sin pedido de PR).
- **Prueba**:
  - `tests/test_hotel_pruebas.py` (19/19): con proveedor, comprador, contacto de departamento y admin con Telegram «reales», un pedido de PR enviado al proveedor deja sus 2 correos solo a la cuenta de pruebas con el aviso, y uno de GC los deja a los reales. También comprueba el resolutor por hotel, la supervisión, el resumen por `hotel_id`, la propuesta de alertas y que sin correo de pruebas no se encola nada.
  - Las 11 tareas programadas con freezegun OK.
  - Huellas (sin BD regenerada por 6 funciones nuevas; con BD idéntica), flujo 51/51, E2E 57/57, techo, migraciones y EmailJS OK.
- **Revisado**: `CLAUDE.md` (regla del hotel de pruebas y test), `README.md`, `core/config.py` (comentario), `CHANGELOG.md` y badge actualizados.
- **Pendiente**: copiar esta entrada al historial del Organizador.

## 2026-11-08 11:03 — [Control Pedidos] Cola de correos solo admin/compras + ETag de index.html entre comillas (v12.33.74)

- **Contexto**: Víctor pide pruebas reales en Render y da acceso con `usuario prueba` (rol hotel, PR). Producción, por el Worker `proxy.controlpedidosprincess-canarias.workers.dev`, sirve v12.33.52 (`/api/version` = md5 del `index.html` de `main`). Sonda de solo lectura: GET públicos, login, GET sin parámetros y logout. Antes de lanzarla se excluyeron 3 GET que escriben: `/api/bridge/notificaciones`, `/api/emails-sistema-pendientes` y `/api/externo/dali-sap/proveedores`.
- **Hallazgo 1 (seguridad)**: `GET /api/emails-sistema-pendientes` y `POST /api/emails-sistema-pendientes/<id>/marcar-enviado[-no-confirmado]` solo llevaban `@login_required`.
  - El GET devuelve y reserva hasta 20 correos (destinatario, asunto, cuerpo, CC) y les suma `intentos`.
  - Los POST los dan por enviados.
  - El frontend solo arranca el sondeo para admin/compras, pero el servidor no lo exigía.
  - **Corrección**: `_solo_admin_o_compras()` en `rutas/emails_sistema.py` → 403 para cualquier otro rol en las tres rutas.
- **Hallazgo 2 (egress)**: `index()` enviaba `ETag: e22f754850f2` sin comillas (inválido según RFC 7232).
  - Medido: directo a onrender llega el ETag y `If-None-Match` da 304. Por el Worker no llega ningún ETag (aunque un `If-None-Match` enviado a mano sí da 304). En cambio, el ETag de `/static/favicon.png` (Flask, entre comillas) sí atraviesa el Worker.
  - El navegador nunca revalidaba y descargaba `index.html` completo en cada carga. Con la Fase 2 son unas 3.300 líneas en lugar de 17.000, pero sigue siendo innecesario.
  - **Corrección**: `ETag: "<hash>"`; la comparación acepta el hash con o sin comillas, `W/` y listas; el 304 lleva también el ETag.
- **Otros datos de la sonda (v12.33.52 en producción, referencia para comparar tras desplegar)**: favicon y logos con `no-cache` (confirma el fallo de caché de v12.33.64); 10 bloques `<script>` en línea; `index` 1.011.626 bytes; cabeceras de seguridad presentes.
- **Bloqueo de la sonda**: `usuario prueba` tiene `debe_cambiar_password` activo, así que `_exigir_cambio_password` devuelve 403 en casi todas las rutas `/api/` (solo pasan `/api/me`, `/api/version`, `/ping` y `/`). Falta cambiar esa contraseña temporal para completar el resto.
- **Prueba**: `test_flujo.py` 51/51 (apartado 12: hotel → 403 en las 3 rutas; admin → 200). `huella_app` exige ETag entre comillas y 304. `huella_bd` regenerada: único cambio, `hotel GET /api/emails-sistema-pendientes` 200 → 403. E2E 57/57; migraciones, EmailJS y techo OK.
- **Revisado**: `CLAUDE.md` (URL del Worker y nota del ETag), `README.md` (versión), `CHANGELOG.md` y badge actualizados.
- **Pendiente**: copiar esta entrada al historial del Organizador.

## 2026-11-08 00:14 — [Control Pedidos] Rol hotel: solo ENTREGA PARCIAL / ENTREGADO, sin altas (v12.33.72)

- **Petición**: Víctor decide que el usuario de hotel solo pueda poner «entrega parcial y entregado» (pregunta abierta de v12.33.70).
- **Cambio**:
  - `rutas/pedidos.py`: `ESTADOS_PERMITIDOS_HOTEL = ("ENTREGA PARCIAL", "ENTREGADO")`. En la rama de hotel de `update_pedido()`, si el estado cambia y no está en esa lista → 403. Se conservan los mensajes específicos de CANCELADO y ENVIADO AL PROVEEDOR.
  - `create_pedido()`: 403 para el rol hotel.
  - `static/js/app.js` (modo hotel de la ficha): se desactivan todas las opciones del estado salvo esas dos (antes solo CANCELADO).
- **Hallazgos arreglados (ya existían)**:
  1. El bloqueo de ENVIADO AL PROVEEDOR de la rama de hotel (2026-09-09) comparaba el estado pedido, no el cambio. Como la interfaz envía siempre `val('p-estado')`, guardar un pedido ya enviado (p. ej. solo el albarán) daba 403. Detectado por `test_flujo.py`. Ahora los tres bloqueos van con `_cambia_estado_hotel`.
  2. `create_pedido()` no comprobaba el rol: un usuario de hotel podía crear pedidos por la API y para cualquier `hotel_id` (no se validaba contra `hoteles_ids`).
- **Prueba**:
  - `test_flujo.py`, apartado 11 con `usuario prueba` (hotel PR) sobre un pedido enviado: alta → 403; PENDIENTE COTIZACIÓN, firma hotel, Vº Bº DG, DENEGADO y CANCELADO → 403 sin cambiar nada; guardar el albarán sin cambiar de estado → 200; ENTREGA PARCIAL sin base imponible → 422; con ella → 200; ENTREGADO → 200. Total 47/47.
  - `e2e_navegador.py`: `usuario prueba` abre un pedido de PR y solo tiene activas ENTREGA PARCIAL y ENTREGADO (57/57).
  - Huellas, migraciones, EmailJS y techo OK.
- **Revisado**: `CLAUDE.md` (regla del rol HOTEL; quitada la pregunta abierta), `README.md` (versión), `CHANGELOG.md` y badge actualizados.
- **Pendiente**: copiar esta entrada al historial del Organizador.

## 2026-11-08 00:08 — [Control Pedidos] Rechazo de alta en estado de firma + pregunta de duplicado tapada en el simplificado (v12.33.70)

- **Petición**: «que el servidor rechace» (decisión sobre el hallazgo de v12.33.68).
- **Antes de cambiar**: se revisó quién crea pedidos con `POST /api/pedidos`.
  - El formulario «paso a paso» ya bloquea los estados de firma antes de guardar (`_pedirDatosFirma`: «Guarda primero el pedido…»).
  - El **«Pedido simplificado»** (`_spCrear`) creaba el pedido directamente en el estado de firma propuesto (`_spEstadoPropuesto`) y subía el `vb_eml` después: un rechazo a secas lo habría roto.
  - Las altas de Activo Operacional (`rutas/externo.py`) e Importar Excel insertan por su cuenta: no afectadas.
  - Ningún estado de cotización o firma envía correo ni Telegram (`ESTADOS_EMAIL_INTERNO`), así que crear y después cambiar de estado no genera avisos nuevos.
- **Cambio**:
  - `create_pedido`: estado por defecto `PENDIENTE COTIZACIÓN`; si `estado` está en `ESTADOS_PENDIENTE_FIRMA` → 422 con `estado_inicial_sugerido`.
  - `_spCrear` (`static/js/app.js`): con un estado de firma crea en PENDIENTE COTIZACIÓN, sube los archivos y hace `PUT` al estado elegido con `fecha_envio_visto_bueno`; despacha los `emails_pendientes` de las dos respuestas; si el `PUT` falla, muestra «Estado sin cambiar».
- **Hallazgo y arreglo (ya existía)**: `_preguntarPosibleDuplicado` usaba `z-index` 1300 y el asistente (`.cp-bloq`) 3000. La pregunta quedaba debajo, el `await` no terminaba nunca y la pantalla se quedaba en «Creando…». Detectado por la prueba E2E: el `POST` devolvía 409 `requiere_confirmacion` y no se veía ningún diálogo. Ahora `z-index` 3100.
- **Prueba**:
  - `test_flujo.py`: los tres estados de firma y ENVIADO → 422 sin crear nada; sin estado → PENDIENTE COTIZACIÓN; resto del ciclo igual. 34/34.
  - `e2e_navegador.py`, nuevo flujo «pedido simplificado del hotel PR en estado de firma»: justificante como `vb_eml`, respuesta «es otro pedido distinto» a la pregunta de duplicado, y en la BD estado PENDIENTE FIRMA DIRECCION COMPRAS, fecha Vº Bº, adjunto `vb_eml` e historial [PENDIENTE COTIZACIÓN → PENDIENTE FIRMA DIRECCION COMPRAS]. 57/57.
  - Huellas, migraciones, EmailJS y techo OK.
- **Pregunta abierta para Víctor (sin cambiar)**: la rama del rol **hotel** en `update_pedido()` solo bloquea CANCELADO y ENVIADO AL PROVEEDOR; acepta cualquier otro estado sin validar. Y la interfaz le ofrece todos menos CANCELADO, sin el diálogo de firma (`_alCambiarEstadoManual` sale para el rol hotel). Así, un usuario de hotel puede pasar un pedido a un estado de firma sin fecha ni justificante, o a PENDIENTE Vº Bº DIRECCIÓN GENERAL / DENEGADO. Falta decidir qué estados debe poder poner el hotel.
- **Revisado**: `CLAUDE.md` (regla de estados de firma, pregunta abierta), `README.md` (versión), `CHANGELOG.md` y badge actualizados.
- **Pendiente**: copiar esta entrada al historial del Organizador.

## 2026-11-07 23:53 — [Control Pedidos] Tests de techo y de flujo + checklist manual del techo (v12.33.68)

- **Petición**: crear los tests que citaba el `CLAUDE.md` y que no existían («posiblemente nunca se crearon»).
- **`tests/test_techo_gastos.py`**: ejecuta las funciones reales `_check_techo`, `_techo_snapshot`, `_resolver_fecha_entrega_prevista` y `_calcular_fecha_entrega_prevista` contra la Postgres local, con la configuración fijada en la BD (3000/6000/1/0). Cubre:
  - las 4 reglas del techo;
  - las 5 exclusiones (otro mes, otro hotel, no sujeto, el propio pedido, filtro por `mes_consumo_techo` y no por `creado_en`);
  - la foto presupuestaria;
  - 8 casos de fechas (prioridad de la fecha específica; date, datetime y texto; datos que faltan o ilegibles).
  - Resultado: 25/25.
- **`tests/test_flujo.py`**: el cliente de pruebas de Flask como admin recorre:
  - alta en PENDIENTE COTIZACIÓN;
  - a firma (422 sin `vb_eml`/fecha; OK con justificante subido por `/api/pedidos/<id>/adjuntos`);
  - a ENVIADO (422 sin proveedor/PDF; OK con contacto principal con email, `pedido_num`, `total_pedido`, `pedido_doc` y tarifa acordada; `mes_consumo_techo` = mes actual);
  - 2.º pedido de la familia → PENDIENTE Vº Bº DG + `expediente_exceso` pendiente (2000/4000); reintento → 422 con `expediente_pendiente_id`, sin duplicar;
  - aprobar tras consumir otros 1000 → la foto sigue en 2000/4000;
  - denegar sin motivo (rechazado) y con motivo;
  - ENTREGA PARCIAL/ENTREGADO con validación de albarán y base imponible;
  - CANCELADO (libera el techo) e historial.
  - Resultado: 28/28.
- **`tests/CHECKLIST_PRUEBAS_MANUALES_TECHO.md`**: pasos con resultado esperado para Render: arranque (`Auto-migración OK` / `[MIGRACION] Paso N`) y aviso de nueva versión; configuración; dentro del techo; desvío; aprobación con foto congelada e informe; denegación; cancelación; fechas; visibilidad de PR; limpieza.
- **Hallazgo (sin cambiar, pendiente de decisión)**: `create_pedido` usa por defecto el estado «PENDIENTE FIRMA DIRECCION COMPRAS» y acepta crear el pedido en un estado de firma sin fecha de envío ni justificante. La regla de v12.32.83 solo se comprueba en `update_pedido` al cambiar de estado. La interfaz sí lo pide (`_pedirDatosFirma`), así que afecta solo a llamadas directas a la API. No se cambia sin decidir antes cómo debe funcionar: al crear, el pedido aún no puede tener adjuntos. Anotado en `CLAUDE.md` → «Mejoras anotadas».
- **Revisado**: `CLAUDE.md` (sección Tests y mejoras anotadas), `README.md` (versión y tests), `CHANGELOG.md` y badge actualizados. Sin cambios de código de la app: huellas no afectadas.
- **Pendiente**: copiar esta entrada al historial del Organizador.

## 2026-11-07 23:47 — [Control Pedidos] CLAUDE.md actualizado y añadido al repositorio (v12.33.66)

- **Petición**: preparar el `CLAUDE.md` nuevo tras la reorganización.
- **Cambio**: `CLAUDE.md` en la raíz, a partir de la versión que tenía Víctor:
  - Se mantienen todas las reglas de trabajo (versionado +2, historial compartido, ramas, ⚠️ en cambios de datos) y las notas de los módulos delicados, con su ubicación nueva verificada con grep.
  - Se completan las partes marcadas con ⚠️: arranque en local, variables de entorno (solo nombres, sacados del código) y cómo lanzar los tests.
  - Se añaden la estructura por capas, las reglas de dependencia, las trampas al mover código, la regla de las migraciones con `_aviso_paso` y la regla 7 («los errores encontrados se reparan»).
- **Corrección de un dato**: tras releer `PENDIENTES.md`, el servicio de Render está creado con runtime Python nativo, no Docker (el `runtime: docker` de `render.yaml` se ignora y el Dockerfile no se usa). La versión anterior decía «Start Command» (correcto) y el borrador de esta entrega decía Docker (incorrecto, corregido antes del commit).
- **Sin cambios de código**: huellas no afectadas.
- **Pendiente**: copiar esta entrada al historial del Organizador. Los tests que citaba el `CLAUDE.md` anterior (`test_techo_gastos.py`, `test_flujo.py`, checklist manual de techo) siguen sin estar en el repositorio.

## 2026-11-07 23:50 — [Control Pedidos] Fase 3: archivo del CHANGELOG y del historial + caché de /static (v12.33.64)

- **Petición**: fase 3 del plan (archivar el CHANGELOG y el historial antiguos).
- **Archivo**:
  - Un solo corte por documento, sin reordenar: lo que hay desde la primera entrada anterior a 2026-10-01 hasta el final pasa tal cual a `docs/archivo/`. No se agrupa por meses porque hay una entrada fuera de orden en septiembre en cada documento (v12.32.64/65 y 2026-09-16/17) y la sección «Julio 2026 (antes de esta sesión)».
  - `CHANGELOG.md`: líneas 1-1201 en el principal (v12.33.64 a v12.32.70) y 1202-11744 en `docs/archivo/CHANGELOG_2026-06_a_2026-09.md`.
  - Historial: cabecera de normas + octubre y noviembre + «## Convenciones de este historial» en el principal; el resto en `docs/archivo/HISTORIAL_CAMBIOS_2026-07_a_2026-09.md`.
  - Cada archivo lleva una cabecera explicativa y el principal, una nota con el enlace. Verificado que principal + archivo reconstruyen el original exacto.
  - `/api/changelog` sigue leyendo la primera entrada (huella OK). El admin recibe ahora 156 KB en lugar de 1 MB.
- **Hallazgo (caché de /static)**: el arreglo de egress de julio estaba en un `@app.route("/static/<path:filename>")` propio con `max_age=604800`, pero Flask registra su ruta `/static` al crear la app y es la que atiende siempre. Comprobado en el monolito original y en la rama: logos y favicon salían con `no-cache`.
- **Corrección**:
  - Se quita la ruta propia, que no se usaba (huella regenerada: 171 rutas).
  - `_max_age_estaticos()` (`rutas/estaticas.py`) da 7 días al resto de `static/` y un año a `css/` y `js/`.
  - Solo cuando el endpoint es `static` y la ruta real del archivo está dentro de `static/`. Flask le pasa a veces la ruta absoluta: en el 404, que devuelve `templates/index.html`, la primera versión de esta función le daba 7 días; detectado y corregido antes del commit.
  - Comprobado: favicon, logos y ejemplos con 7 días; CSS/JS con un año; `/static/no-existe.png`, `/static/../app.py`, `/no-existe` y `/` con `no-cache`, como antes.
- **Prueba**: huellas (sin BD regenerada por la ruta quitada; con BD idéntica), E2E navegador 56/56, `test_migraciones` y `test_emailjs_rotacion` OK.
- **⚠️ Organizador**: este historial es compartido. Para que los dos sigan iguales hay que aplicar el mismo corte en el `HISTORIAL_CAMBIOS.md` de la raíz del Organizador (mover todo lo anterior a 2026-09-25 inclusive, salvo «## Convenciones de este historial», a un archivo equivalente) y copiar las entradas de hoy. Desde esta sesión no hay acceso de escritura a ese repositorio.
- **Revisado**: `README.md` (versión, estructura, documentos relacionados), `CHANGELOG.md` y badge actualizados. Los manuales de `docs/` (.docx y .pdf, ~15 MB) se dejan como están: son para los usuarios.

## 2026-11-07 23:35 — [Control Pedidos] Fase 2: CSS/JS fuera de index.html + pruebas E2E en navegador (v12.33.62)

- **Petición**: seguir con la fase 2 y hacer comprobaciones de funcionamiento real con el hotel PR.
- **Sobre probar en producción**: no se hizo. La rama no está desplegada (Render despliega `main`). Una segunda instancia contra la BD real ejecutaría migraciones y tareas programadas (correos y Telegram duplicados, ver `PENDIENTES.md`). El login con usuario y contraseña no debe pasar por el chat. En su lugar: navegador real (Chromium + Playwright) contra gunicorn y una Postgres local con datos del hotel PR.
- **`tests/e2e_navegador.py`** (nuevo):
  - Siembra `usuario prueba` (rol hotel, PR) además de los datos de `huella_bd.py`.
  - Recorre las vistas del menú de cada rol según `data-roles`: las permitidas deben mostrarse y las bloqueadas no deben abrirse.
  - Alta por «Nuevo pedido → paso a paso» (hotel PR, departamento, observaciones) y edición a «PENDIENTE DE FIRMA DIRECCION HOTEL». La app pide la fecha y el justificante (`cp-firma-file`) y se sube un PDF generado con reportlab.
  - Comprueba en la BD el estado, las observaciones, el adjunto `vb_eml` y `historial_estados`.
  - Visibilidad del hotel PR: `usuario prueba` lo ve y `hotel prueba` no.
  - Falla con cualquier `pageerror`, `console.error` o respuesta 5xx. Se ignoran solo los errores del CDN de EmailJS y de Google Fonts, bloqueados en el entorno de pruebas.
  - Resultado: 56/56 OK, igual con el monolito 0a0fbb5 que con la rama.
- **Fase 2**:
  - Los 8 bloques `<style>`/`<script>` en línea de `templates/index.html` (salvo el pequeño de configuración de EmailJS en `<head>`) pasan a `static/css/app.css` y a `static/js/` (`app.js`, `importar_pedidos.js`, `avisos_alerta.js`, `impresion_pedidos.js`, `impresion_techo_alertas.js`, `emails_sistema.js`, `nueva_version.js`). Cada uno se sustituye en la misma línea por `<link>`/`<script src>` sin `defer`, así que el orden de ejecución no cambia.
  - Reconstrucción byte a byte del `index.html` original verificada y `node --check` OK en los 7 JS.
  - Un primer intento cortó mal el último bloque (incluía HTML y otros 2 scripts): la prueba E2E lo detectó («Unexpected token '<'», `restoreCargarLista is not defined`) y se rehízo detectando todos los bloques automáticamente.
- **Caché**:
  - `rutas/estaticas.py`: `_versionar_estaticos()` cambia `?v=__V__` por el md5 (10 caracteres) de cada archivo de `static/`, al leer `index.html`, así que `/api/version` (md5 de lo servido) cambia si cambia cualquier CSS/JS.
  - `_max_age_estaticos()` da un año de caché solo a `static/css/` y `static/js/`. Logos y favicon siguen con el comportamiento de Flask.
  - Aviso de nueva versión probado: con la app abierta, al añadir una línea a un JS, `_pollVersion()` muestra el modal; sin cambios, no.
- **Pruebas**:
  - Capturas de las 51 pantallas con el `index.html` anterior y con el nuevo: las diferencias son píxeles sueltos de suavizado de letras (el 0,2 %). Dos ejecuciones del mismo `index.html` anterior ya difieren en 35 capturas por lo mismo.
  - Huellas (ampliadas: cada CSS/JS enlazado debe servirse y su `?v=` debe ser el hash del archivo), `test_emailjs_rotacion`, `test_migraciones` y E2E OK.
- **Pendiente**:
  - Probar en Render con el hotel PR tras fusionar (lo hace Víctor), sobre todo el primer arranque y el aviso de nueva versión.
  - `app.js` sigue teniendo ~8.500 líneas: partirlo por temas exige comprobar qué funciones se usan al cargar cada archivo (orden de declaración), así que se deja para más adelante.
  - Copiar esta entrada al historial del Organizador.
- **Revisado**: `README.md` (stack, estructura, versión en la URL de CSS/JS, tests), `CHANGELOG.md` y badge actualizados; `Dockerfile` (`COPY . .` incluye `static/`) y `GUIA_DESPLIEGUE.md` → no aplica.

## 2026-11-07 23:20 — [Control Pedidos] _auto_migrate: cada paso con su propio try/except (v12.33.60)

- **Petición**: seguir con la reorganización por `_auto_migrate` (pendiente del `CLAUDE.md`: fallo intermitente «Auto-migración omitida»).
- **Hallazgo**: 184 sentencias dentro de `with db.cursor()`, de las que 143 no tenían try/except. La conexión es autocommit (un fallo no arrastra la transacción), pero la excepción salía al `except` general y cortaba el resto de la función. Con el log anterior no se podía saber qué sentencia fallaba en producción. Reproducido inyectando un fallo en el `CREATE INDEX idx_prov_contactos`: «Auto-migración omitida» y, por ejemplo, `sap_albaranes_cab_hotel_albaran_uk` sin crear.
- **Corrección** (herramienta automática, sin reescribir a mano):
  - Cada sentencia se envuelve en `try: … except Exception as _exc_paso: _aviso_paso(N, descripción, _exc_paso)`.
  - Se agrupan en un mismo paso las sentencias inseparables: las que leen el resultado del cursor (`fetchone`/`rowcount`) o usan variables recién asignadas (9 grupos, p. ej. `SELECT COUNT(*)` + `fetchone` + `if`).
  - No se envuelven los 41 bloques que ya tenían try/except, las funciones internas ni las asignaciones triviales.
  - Las líneas de continuación de los textos SQL multilínea no se reindentan.
  - `_aviso_paso` acumula los pasos omitidos y el resumen final sustituye a «Auto-migración OK» cuando hay alguno. El `log.exception` general queda para fallos de conexión.
- **Prueba**: AST de las 184 sentencias idéntico al anterior quitando los try nuevos. BD nueva + segundo arranque: «Auto-migración OK», `pg_dump --schema-only` idéntico y datos iniciales de 7 tablas idénticos. `tests/test_migraciones.py` pasa con el código nuevo y falla con el anterior. Huellas, `test_emailjs_rotacion.py` y pyflakes OK.
- **⚠️ Producción**: no modifica datos. Solo cambia qué pasa cuando una migración falla (se sigue en vez de parar). Tras desplegar, conviene mirar el log de arranque: si aparece algún «[MIGRACION] Paso N», ese es el fallo intermitente que estaba pendiente.
- **Revisado**: `README.md` (regla de migraciones, tests), `CHANGELOG.md` y badge actualizados; `GUIA_DESPLIEGUE.md` → no aplica.
- **Pendiente**: copiar esta entrada al `HISTORIAL_CAMBIOS.md` del Organizador.

## 2026-11-07 23:10 — [Control Pedidos] Reorganización fase 1 completa: app.py → core/ servicios/ jobs/ rutas/ (v12.33.58)

- **Petición**: seguir ordenando el código (continuación de v12.33.54).
- **Método**:
  - Grafo de dependencias de las sentencias de nivel superior de `app.py`: 0 ciclos.
  - Cada función o constante se asigna a un módulo temático según su sección y unas reglas: las rutas van a `rutas/`; los helpers de rutas, a `servicios/`; los helpers genéricos (normalización, destinatarios, firma, config), a módulos propios.
  - Capas `core` < `servicios` < `jobs` < `rutas`. Si algo de capa inferior necesita algo de una superior, eso baja a la capa de quien lo usa. Comprobado: 0 ciclos entre los 69 módulos.
  - Extracción módulo a módulo con una herramienta que copia verbatim (con los comentarios previos de cada bloque) y se niega a mover código que dependa de algo que se queda en `app.py`. `tests/huella_app.py` se pasa tras cada módulo.
- **Cambios no verbatim (necesarios)**:
  - `core/aplicacion.py` crea `Flask("app", root_path=raíz)`: mismo nombre, raíz, plantillas, estáticos y configuración que `Flask(__name__)` en `app.py` (comparado).
  - Las rutas conservan `@app.route` importando ese `app`, así que los endpoints y su orden de registro no cambian (sin Blueprints).
  - `rutas/estaticas.py` usa `_RAIZ_PROYECTO` en lugar de `__file__` para leer `templates/index.html` y `CHANGELOG.md` (con `__file__`, `/api/version` devolvía «unknown»).
  - `app.py` reescrito como punto de entrada de 87 líneas: hooks en el mismo orden (`_cabeceras_seguridad`, `_comprimir_respuesta_gzip`, `_track_egress`; `_exigir_cambio_password`, `_limitar_sesion_puente`), migraciones, bucket, rutas y scheduler.
  - Importaciones de cada módulo agrupadas (biblioteca estándar, externas, proyecto).
- **Prueba**:
  - Las dos huellas idénticas a las generadas con el monolito original. Huella ampliada con el valor de `/api/version`, `GET /` y `/api/changelog`; detecta el fallo de `__file__` si se reintroduce.
  - `tests/test_emailjs_rotacion.py` OK.
  - Las 11 tareas programadas ejecutadas con freezegun (2026-11-04 10:00) y pedidos sembrados en 6 estados, con el código de v12.33.56 (worktree aparte) y con el nuevo: log idéntico (salvo el tamaño físico de la BD) y BD idéntica (salvo `NOW()` y la sal del hash de contraseña).
  - gunicorn con la orden de Render: «Auto-migración OK», login y 8 endpoints con 200, ETag correcto, gzip y cabeceras de seguridad presentes, 0 errores en el log.
  - pyflakes: 0 nombres sin definir.
- **Pendiente para las siguientes fases**: partir `core/migraciones.py` (2.594 líneas, una sola función) en bloques con try/except propio; separar CSS/JS de `templates/index.html`; archivar el CHANGELOG/historial antiguos. Algunos comentarios del código aún dicen «más abajo en app.py» (solo texto).
- **Revisado**: `README.md` (stack, estructura, tabla «Dónde está cada cosa», rutas de `_auto_migrate`/`login_required`/gzip), `GUIA_DESPLIEGUE.md`, `PENDIENTES.md`, `render.yaml` y `Dockerfile` (solo comentarios que apuntaban a `app.py`), `CHANGELOG.md` y badge actualizados.
- **Pendiente**: copiar esta entrada al `HISTORIAL_CAMBIOS.md` del Organizador.

## 2026-11-07 22:50 — [Control Pedidos] Arreglos: rotación automática de cuenta EmailJS y orden de migraciones en BD nueva (v12.33.56)

- **Petición**: reparar los fallos encontrados durante la reorganización, aunque ya estuvieran en la aplicación.
- **Hallazgo 1 (EmailJS)**: `_registrar_envio_emailjs_interno` usaba `pytz` sin importarlo, en la rama del cambio automático de cuenta. Reproducido con Postgres local: contador en 194, umbral en 195 y 2 cuentas completas → `NameError`; tras el rollback, el contador sigue en 194 y la cuenta en 1. El contador no podía pasar nunca del umbral − 1 y la rotación no se completaba.
- **Corrección 1**: `import pytz` local, como en el resto de `app.py`. Mismo escenario → cuenta 2, contador 0 y `emailjs_cambio_automatico_en` rellenado. Test de regresión `tests/test_emailjs_rotacion.py` (falla sin el arreglo y pasa con él).
- **Hallazgo 2 (migraciones)**: en una BD nueva, `_auto_migrate` hacía `ALTER TABLE sap_pedidos_listado` y `_SQL_FECHA_SOLICITUD_AUTO_SAP` antes del `CREATE TABLE sap_pedidos_listado`, y `idx_prov_codigo_dali_trgm` antes de `ADD COLUMN codigo_dali`. La conexión es autocommit, así que no arrastraba a otras sentencias, pero dejaba 3 avisos y el índice sin crear en el primer arranque.
- **Corrección 2**: el `CREATE TABLE`/`CREATE UNIQUE INDEX` de `sap_pedidos_listado` pasa justo antes de su primer uso, con try/except propio (antes no lo tenía), y el `ADD COLUMN codigo_dali` pasa antes del bucle de índices trigram. Se deja una nota en la posición antigua. Todo idempotente: en producción no hace nada.
- **Prueba**: arranque sobre BD nueva y segundo arranque sobre la misma → «Auto-migración OK» sin ningún aviso en los dos, 45 tablas, ambos índices creados. `tests/huella_app.py` y `tests/huella_bd.py` idénticas. pyflakes: ningún nombre sin definir en `app.py`.
- **Revisado**: `README.md` (versión y test nuevo), `CHANGELOG.md` y badge actualizados; `GUIA_DESPLIEGUE.md`, `PENDIENTES.md` → no aplica.

## 2026-11-07 22:45 — [Control Pedidos] Reorganización fase 1, paso 1: `core/config.py`, `core/db.py`, `core/storage.py` + huellas de seguridad (v12.33.54)

- **Petición**: ordenar el código porque ha crecido demasiado (`app.py` 30.123 líneas, `templates/index.html` 17.385).
- **Plan acordado**: fase 0, red de seguridad; fase 1, partir `app.py` en módulos con Blueprints sin cambiar URLs; fase 2, separar CSS y JS de `index.html`; fase 3, archivar el CHANGELOG y el historial antiguos. Rama `refactor/modulos`; `main` no se toca sin confirmación.
- **Fase 0**: `tests/huella_app.py` importa la app sin BD y fija rutas, jobs, orden de hooks, errorhandlers, respuesta anónima de cada endpoint e inventario de funciones. `tests/huella_bd.py` monta un esquema limpio en una Postgres LOCAL (rechaza cualquier host que no sea localhost porque borra el esquema), ejecuta `_auto_migrate`, siembra admin/compras/hotel (PR), un proveedor y un pedido, y recorre los 79 GET con cada rol.
- **Cambio**: movidos verbatim a `core/` los bloques de configuración (15 nombres), base de datos (14) y Storage (5), con una herramienta que se niega a mover código que dependa de algo que se queda en `app.py`. Los hooks `teardown_appcontext(close_db)` y `after_request(_track_egress)` se registran en `app.py` en la misma posición. `_db_pool` no se importa en `app.py`: el reintento de `/api/emails-sistema-pendientes` lo lee de `core.db`. Logger `"app"` en los módulos nuevos para que el log salga igual.
- **Prueba**: las dos huellas, generadas con el `app.py` original, salen idénticas tras el cambio (172 rutas, 11 jobs, 171 respuestas anónimas, 532 funciones; 240 respuestas con BD, 108 con 200 y ninguna 500). pyflakes sin nombres sin definir en `core/`.
- **Hallazgos (sin corregir en esta entrega)**:
  - `_registrar_envio_emailjs_interno` usa `pytz` sin importarlo: el cambio automático de cuenta EmailJS al llegar al tope lanza `NameError`. Ya estaba antes de este cambio.
  - En una BD vacía, `_auto_migrate` toca `sap_pedidos_listado` antes de que exista (2 avisos) y crea `idx_prov_codigo_dali_trgm` antes de la columna `codigo_dali`. No afecta a producción (las tablas ya existen), pero es un problema de orden a resolver al partir `_auto_migrate`.
  - El `CLAUDE.md` menciona `tests/test_techo_gastos.py` y `test_flujo.py`, que no están en el repositorio.
- **Pendiente**: este historial es compartido con el Organizador (`HISTORIAL_CAMBIOS.md` en su raíz). Copiar esta entrada allí; desde esta sesión no hay acceso de escritura a ese repositorio.
- **Revisado**: `README.md` (versión, estructura, cómo pasar las huellas), `CHANGELOG.md` y badge actualizados; `GUIA_DESPLIEGUE.md`, `Dockerfile`, `render.yaml` → no aplica (mismo comando de arranque, `COPY . .` incluye `core/`).

## 2026-11-07 17:45 — [Control Pedidos] Copia del pedido en PDF con diseño oficial + Admin → Datos de hoteles (v12.33.52)

- **Petición**: que los pedidos sin PDF subido (altas automáticas) tengan siempre su pedido en PDF para ver y descargar, generado con el diseño oficial a partir del listado detallado. Los datos de sociedad y hotel se introducen desde un apartado de Admin, precargado con «Datos de facturación y entrega» y con los teléfonos de los compradores.
- **Hallazgo**: `_generar_pdf_pedido` (v12.33.50) solo se usaba en los correos y con diseño propio. No conviene guardarla como `pedido_doc`, porque ese tipo es la «verdad absoluta» del pedido: manda sobre el Total Pedido, hace que `_volcar_lineas_sap_hotel` se salte el pedido y se lee para el proveedor y el almacén. La caja Sociedad y la dirección del hotel no estaban en la BD.
- **Corrección**:
  - `_generar_pdf_pedido` reescrita con reportlab imitando `static/ejemplos/pedido_pdf_ejemplo.jpg`. Almacén de cabecera = el único almacén de las líneas (sin código) o, si hay varios, el departamento. La columna Almacén de la línea solo se rellena si es distinta de la cabecera. Cantidad con 4 decimales y precio con 2, como el oficial.
  - `_CAMPOS_DATOS_HOTEL` / `_DATOS_HOTEL_INICIALES` + `ALTER TABLE hoteles` y precarga «solo vacíos» en `_auto_migrate`.
  - `GET/PUT /api/admin/hoteles-datos`, vista `view-hoteles-datos` (Datos maestros · Admin).
  - (17:45, a petición de Víctor) **Teléfono = móvil del comprador asignado**: no se guarda en `hoteles`. `_SQL_MOVIL_COMPRADOR_HOTEL` lo saca de `usuarios.movil` vía `usuario_comprador_hoteles` (índice único: un comprador por hotel, solo usuarios activos), tanto en el PDF como en Admin, donde se ve como campo `readonly` con el nombre del comprador. El PUT lo ignora. `_MOVIL_COMPRADORES_INICIAL` carga al arrancar el móvil de centralcompras1-6 (por `email`/`email2`, sin distinguir mayúsculas) solo si la ficha lo tiene vacío.
  - `GET /api/pedidos/<id>/pdf-generado` (con login y acceso al hotel) y `copia_generada` en `GET /api/pedidos/<id>/adjuntos` (sin PDF subido y con líneas). `cargarAdjuntos()` añade el elemento en `adj-pedido-list`.
- **Discrepancias en los PDF de origen (se usó «Datos de facturación y entrega»)**: Jandía C/ Gran Canaria **13** (en «Contactos» pone 11); razón social de Mogán «MOGAN RESORTS, S.L.» (en «Contactos», «MOGAN RESORT, S.L.»); «MASPALONAS» corregido a MASPALOMAS. Se pueden cambiar en Admin.
- **Prueba**: Postgres local con los pedidos reales de La Palma. PDF de 1 y de 2 páginas revisados visualmente; ruta inline y ruta de descarga; pedido sin líneas → sin copia y 404; sin login → 401; guardado en Admin y rearranque sin pisar lo editado. Teléfono: móvil vacío cargado por correo y móvil existente no pisado; cambiar el móvil del comprador cambia el PDF; hotel sin comprador → sin teléfono; el PUT no admite teléfono.
- **Revisado**: `GUIA_DESPLIEGUE.md`, `PENDIENTES.md`, `INSTRUCCIONES_RESTAURACION.md` → no aplica; `docs/hallazgo-seguridad-princess.md` no existe en el repo (ver nota de la norma 5) → no aplica. `README.md` (versión y funcionalidades), `CHANGELOG.md` y badge de `templates/index.html` actualizados.

## 2026-11-07 14:00 — [Control Pedidos] Cargar listados SAP: solo Pedidos resumido, Pedidos detallado y Albaranes por proveedor (v12.33.51)

- **Petición**: dejar el apartado de listados para automatización con solo tres tipos (pedidos resumido, pedidos detallado y albaranes por proveedor «COMPRA»), que se puedan subir juntos o por separado, y que todo lo cargado se guarde para actualizar control_pedidos siempre que se pueda.
- **Hallazgo**: con esos tres basta. Los listados antiguos de albaranes no aportan nada que no traiga el «COMPRA». El resumido sí hace falta: es la única fuente de `estado_sap` (Abierto/Cerrado) e importes exactos. Además, el resultado dependía del orden: con el detallado antes que el resumido, las altas nacían «Enviado al proveedor» con `importe` 0 y no se corregían al llegar el resumido.
- **Corrección**:
  - `_TIPOS_LISTADO_SAP` / `_ORDEN_CARGA_LISTADOS_SAP` solo con `pedidos_resumido`, `pedidos_detallado` y `albaranes_pedido`. Nuevo `_TIPOS_LISTADO_SAP_RETIRADOS` para rechazar con mensaje los antiguos. `_MAX_PDF_CARGA_SAP` = 20.
  - Nueva `_completar_estado_altas_con_resumido()` (paso 1a de `_cargar_listados_sap_logica`): altas automáticas sin intervención manual → estado por `_entrega_estado()` (solo hacia delante) e `importe` desde la base del resumido. Se muestra en el resultado («estado completado por el listado resumido»).
  - Aviso de listados que el hotel aún no tiene guardados.
  - `POST /api/albaranes/importar-listado` y `POST /api/pedidos/comparar-listado-albaranes` → 410.
  - `templates/index.html`: texto del modal, máximo 20, sin «Cargas por separado (avanzado)»; se conserva el botón de revisión de entregas pendientes.
- **Prueba**: Postgres local con los PDF reales de La Palma (resumido, detallado, PILSA y DELFIN): junto, por separado (albaranes → detallado → resumido, y resumido → DELFIN → detallado → PILSA) y carga repetida → los 151 pedidos idénticos (estado, entradas, total e importe). Rechazo de un listado de albaranes antiguo y de un PDF desconocido verificado.
- **Añadido (14:05) — fecha de solicitud de los pedidos automáticos**: `_SQL_FECHA_SOLICITUD_AUTO_SAP` = LEAST(tramitación, creación en SAP `fecha_hora_fecha`) − 1 día, solo con `fecha_solicitud` vacía y pedido automático (`creado_por_nombre` = autor SAP o nota de alta). Se aplica en `_crear_pedidos_sap_lote` (alta), en `_completar_estado_altas_con_resumido` (cada carga/regularización) y en `_auto_migrate` (relleno de los ya creados). Hallazgo: los avisos de Enviado/Entrega parcial usan `fecha_tramitacion`; la solicitud vacía afectaba al filtro por fechas de la lista, a la agrupación por mes y al Excel. Prueba: 152 altas → 121 con tramitación − 1 y 31 con creación − 1; relleno al arrancar idéntico; fecha manual y pedido manual intactos.
- **Añadido (14:38) — trazabilidad**: Víctor veía «duplicada» la trazabilidad de los pedidos recién creados (creación y última modificación con el mismo autor y hora, porque el alta rellena las dos). `_renderTrazabilidadPedido()` muestra una sola línea «Sin cambios desde la creación» cuando coinciden autor y hora (±60 s). Solo pantalla.
- **Revisado**: `GUIA_DESPLIEGUE.md`, `PENDIENTES.md`, `INSTRUCCIONES_RESTAURACION.md` → no aplica; `docs/hallazgo-seguridad-princess.md` no existe en el repo (ver nota de la norma 5) → no aplica. `README.md` (versión y funcionalidades), `CHANGELOG.md` y badge de `templates/index.html` actualizados.

## 2026-10-28 — [Control Pedidos] Copia del pedido en PDF para pedidos sin PDF oficial (v12.33.50)

- **Petición**: la reclamación del Pedido Nº 16756 llegó sin documento. Víctor pide generar un PDF con lo leído del Listado de Pedidos detallado y, si son pocas líneas, ponerlas en el cuerpo del correo.
- **Corrección**:
  - `_generar_pdf_pedido()` (reportlab) crea la copia a partir de `pedidos` + `pedido_lineas`.
  - Ruta pública `/descargas/pedido/<token>`: token itsdangerous firmado con SECRET_KEY, sal `pedido-pdf-generado`, 180 días, sin tabla.
  - `_enlaces_descarga_pedido_doc()` añade ese enlace (`generado=True`) cuando no hay PDF subido y sí hay líneas.
  - En `_email_template_enviado_proveedor`, sin PDF oficial y con hasta `_MAX_LINEAS_EN_CUERPO`=15 líneas, también van en el cuerpo.
- `requirements.txt`: `reportlab==4.4.10`.
- Prueba: `t_v50.py` (1 línea → botón + cuerpo; 32 líneas → solo botón, PDF de 2 páginas; PDF oficial → como antes; token alterado → 404).

## 2026-10-28 — [Control Pedidos] Reclamación al proveedor: referencias pendientes y botón de descarga del pedido (v12.33.49)

- **Petición**: en los avisos automáticos al proveedor, si es entrega parcial, indicar las referencias y cantidades aún no entregadas; si es enviado al proveedor, un botón con la descarga del pedido.
- **Hallazgo**: `_JOB_PEDIDO_SQL` y `PEDIDO_SELECT_ALERTA` no traían `entrada_albaran_num` ni `total_pedido`. La reclamación (automática y manual) salía sin el bloque de entregas ni el total, y `_datos_pendientes` no veía las entradas sin detalle.
- **Corrección**:
  - Se añaden las dos columnas a las dos consultas.
  - `_html_botones_descarga_pedido()` (reutiliza `_enlaces_descarga_pedido_doc`) va en `_email_template_enviado_proveedor`; sin PDF, va `_html_referencias_pedido()`.
  - En `_email_template_entrega_parcial`, si no hay tabla de pendientes fiable, se ponen las referencias del pedido y se pide confirmación.
  - `_obtener_o_crear_token_adjunto` solo reutiliza tokens con más de 30 días de vigencia.
- Prueba: `t_v49.py` con los pedidos de GY cargados desde los listados SAP reales.

## 2026-10-27 20:15 — [Control Pedidos] Cargar listados SAP con solo dos PDF: Pedidos detallado + Albaranes con su pedido (v12.33.48)

- **Petición**: automatizar pedidos y albaranes con dos listados en lugar de cuatro: el Listado de Pedidos detallado y el documento «COMPRA» de albaranes en bloque (un albarán por página, con «Pedido/s»). Regla de Víctor para las líneas: si coinciden el nº de pedido y la descripción, se dan por buenas aunque el código cambie.
- **Hallazgo**: el documento COMPRA es el mismo formato que la confirmación de un albarán suelto (`_extraer_albaran_confirmacion_individual`), pero con muchos albaranes; un albarán que no cabe sigue en la página siguiente repitiendo la cabecera («Página 2 de 1»). En los PDF reales de GY los códigos de artículo del albarán y del pedido no coinciden en 249 líneas (el pedido usa otro código interno), pero la descripción sí; y `_cruce_lineas_sap_hotel` no usaba `pedido_num_sap_confirmado`.
- **Corrección**:
  - `_detectar_tipo_listado_sap`: tipo `albaranes_pedido` (comprobado el primero; si no, se tomaba por Pedidos detallado). `_ORDEN_CARGA_LISTADOS_SAP` lo procesa antes que los listados antiguos de albaranes.
  - `_extraer_albaranes_con_pedido` (pdfplumber, agrupa por «Código», total: «Total (con Dtos.)» con decimales → «Total:» → suma de líneas) e `_importar_albaranes_con_pedido` (sustituye las líneas de cada albarán en `sap_albaranes_lineas` con `pedido_num_sap_confirmado` y hace upsert de la cabecera en `sap_albaranes_cab`; en albaranes de varios pedidos reparte cada línea por código/descripción y, si no puede, la deja sin pedido).
  - `_clave_desc_sap`, `_clave_cod_sap`, `_casar_linea_con_pedido_sap`: casado por código (sin ceros a la izquierda), descripción exacta o descripción que empieza por la otra (≥ 12 caracteres); solo si sale un único código del pedido.
  - `_cruce_lineas_sap_hotel`: primero asigna las líneas con pedido confirmado (con el código del pedido); lo recibido que falte se busca como antes entre las líneas sin pedido. Motivos nuevos para revisar: línea que no casa, albaranes que suman más de lo recibido, albaranes de un pedido sin nada recibido en SAP. Solo las asignaciones por proveedor+artículo entran en el desempate por fecha.
  - `_cargar_listados_sap_logica`: varios PDF del mismo tipo; aviso «sin fecha» por albarán sin cabecera. `_importar_albaranes_listado` ya no pisa albaranes con pedido. `/api/sap/cargar-listados` y la pantalla: hasta 10 PDF (`_MAX_PDF_CARGA_SAP`) y texto nuevo del modal.
- **Verificación** (Postgres local, PDF reales de GY): 33 creados, 31 aplicados, 0 para revisar, 2 sin recepción; base de entradas = recibido en SAP al céntimo en los 33; segunda pasada sin cambios. `t_v48.py`: 11 comprobaciones (casado por código/descripción/partida/ambigua, reparto de albarán con dos pedidos, el listado antiguo no pisa un albarán con pedido, listado de pedidos desactualizado → revisar y se aplica al actualizarlo). No probado: la pantalla en un navegador con la app desplegada.
- **Norma 5**: no aplica (sin tablas ni variables nuevas).
- **Documentos revisados**: `README.md` (versión y apartado «Cargar listados SAP»), `CHANGELOG.md`; `GUIA_DESPLIEGUE.md`, `PENDIENTES.md` e `INSTRUCCIONES_RESTAURACION.md` — no aplica.

## 2026-10-26 — [Control Pedidos] Los avisos diarios de pedidos ya no se repiten cada minuto (v12.33.46)

- **Petición**: el popup de alerta urgente del Pedido SAP 40861 (GY, Casa Delfín, 77 días) salía cada pocos minutos. Debe salir una vez el día que toca y, si ese día el Organizador está cerrado, perderse.
- **Causa**: `_job_alertas_diarias_inner` solo escribía el dedup `telegram_auto` con los resultados de Telegram. Si el hotel tiene destinatarios de popup y ninguno de Telegram, no se escribía nada y se encolaba un popup nuevo en cada pasada (cada 60 s). Lo mismo pasaba en `_job_techo_urgente_admins_inner` con un admin sin `telegram_chat_id`.
- **Corrección**:
  - `_log_alerta_solo_popup()` apunta `solo-popup` (enviado=1) o `sin-destinatarios` (enviado=0) en los dos caminos del job. `_enviar_telegram_compradores(..., info)` devuelve cuántos popups ha encolado.
  - En el techo urgente se apunta `solo-popup|usuario|hotel`.
  - `_encolar_bridge_notificacion` no encola un popup idéntico ya encolado hoy (hora de Canarias); se excluye `solicitud_acceso*`.
  - `GET /api/bridge/notificaciones` marca como leídos, sin devolverlos, los `alerta_auto`/`techo`/`familia_repetida`/`supervision` de días anteriores.
- Prueba: `t_v46.py` (5 pasadas del job → 1 popup; dedup; caducidad).

## 2026-10-24 — [Organizador] v4.18.04 — Los avisos de Control de Pedidos recibidos con la app cerrada se pierden, y los popups se cierran solos a los 10 minutos

- **Petición (Víctor):** «los envíos realizados los días que no se abre main agenda deberían desaparecer y no mostrarse el siguiente día que se abre, solo mostrar aquello que se programa directamente en el calendario, eventos propios y vacaciones y festivos»; y «cuando llegan popup de Control de Pedidos y main agenda está abierto, a los 10 minutos de mostrar en pantalla si no se pulsa cerrar se debería cerrar automáticamente».
- **Causa:** Control de Pedidos guarda lo pendiente de cada usuario (alertas por estado/plazo en `bridge_popup_visto`, notificaciones inmediatas en `bridge_notificaciones`) y lo entrega, marcándolo como entregado, en la primera consulta con sesión; todo lo acumulado con la app cerrada salía de golpe al abrirla.
- **`pedidos_agenda_bridge.py`:** la primera respuesta de `/api/bridge/alertas` y la primera de `/api/bridge/notificaciones` tras cada arranque se consultan (así el servidor las da por entregadas y no vuelven) pero **no se muestran** (`_descartar_alertas_acumuladas`, `_descartar_push_acumulado`; se rearman en `iniciar_bridge_pedidos`). Lo que llega después, con la app abierta, se muestra como siempre. El recuento del saludo (total/urgentes) sigue saliendo del servidor y no cambia. No se toca la agenda local: avisos programados, eventos, vacaciones y festivos funcionan igual.
- **`app/negocio/alertas.py`:** `_AUTOCIERRE_BRIDGE_MIN` 30 → 10. El plazo cuenta desde que el popup aparece en pantalla; solo afecta a los popups de Control de Pedidos (los avisos del calendario siguen con su regla).
- **Verificación:** `py_compile`; prueba con sesión simulada: la primera consulta de alertas y de notificaciones no muestra nada, las siguientes sí, y si la primera venía vacía la siguiente ya se muestra. Pendiente probar con el Control de Pedidos real en Windows. Matiz: si la primera consulta con éxito tarda (sin red al arrancar), lo que llegara entre medias con la app abierta también se descarta.
- `APP_VERSION` → "v4.18.04"; `MyAppVersion` → "4.18.04".

---

## 2026-10-24 — [Control Pedidos] Proveedor sin ficha: enlace a «Nuevo proveedor» en lugar de correo (v12.33.45)

**Petición de Víctor:** «Mejor, ¿por qué no se da un aviso en pantalla para que se cree el proveedor para poder crear el nuevo pedido? Con un enlace de apertura directa del apartado Proveedores en Control de Pedidos; enviar el correo no lo veo funcional.»

**Cambios:** fuera `_avisar_proveedores_sin_ficha_ao()` y `aviso_sin_ficha` de la respuesta de `_ao_vb_dividir()`. `templates/index.html`: `_enlaceProveedorInit` lee `?nuevo_proveedor=<nombre>` (máx. 200) y `_abrirProveedorEnlace` abre Proveedores, `openNuevoProveedorModal()` y rellena `pv-nombre-input` (si no es admin, toast de que solo un administrador puede crearlo). El aviso y el bloqueo del envío están en Activo Operacional v1.18.2.

**Verificación:** `t_v44` (14 comprobaciones; la del correo cambia a «no se encola ningún correo»); `vistoBueno.test.mjs` de Activo Operacional contra este Flask: TODO OK (36), incluidos aviso con enlace `?nuevo_proveedor=`, envío bloqueado con 409 y, tras crear los proveedores con otra escritura del nombre («CASA DELFIN, S.A.» frente a «CASA DELFIN SA»), «Volver a comprobar» ya no avisa. Los bloques `<script>` de `index.html` siguen compilando igual que antes. No probado: el enlace en un navegador con la app desplegada.

**Norma 5:** no aplica (sin tablas ni variables nuevas).

**Documentos revisados:** `README.md` (versión), `CHANGELOG.md`; `GUIA_DESPLIEGUE.md`, `PENDIENTES.md` e `INSTRUCCIONES_RESTAURACION.md` — no aplica.

## 2026-10-24 — [Control Pedidos] V.º B.º dividido: presupuesto adjunto en cada pedido y aviso de proveedor sin ficha (v12.33.44)

**Petición de Víctor** (sobre los criterios por defecto de la v12.33.39): original con el proveedor de mayor importe — OK; las copias mantienen pedido original, fecha de solicitud y fecha de envío a V.º B.º, cada una con su documento filtrado por sus referencias — OK (ya era así); importe sin rellenar — OK; «adjuntar cada presupuesto y Nº presupuesto a su correspondiente pedido en el apartado presupuesto»; proveedor sin ficha: «sí, pero notificarlo para crearlo».

**Cambios:**
- `_ao_vb_dividir()`: acepta `documentos[].presupuestos[].{nombre, pdf_base64}` (PDF, ≤ 5 MB, 400 si no lo es) y los inserta como `pedido_adjuntos.tipo='presupuesto_doc'` en el pedido de su proveedor, salvo si ya hay uno con el mismo contenido (`md5(datos)`). La respuesta añade `pedidos[].presupuestos_adjuntos` y `aviso_sin_ficha`.
- `_avisar_proveedores_sin_ficha_ao()` (nuevo): tras el commit, encola un correo de sistema (`ao_proveedor_sin_ficha`) a los compradores del hotel (`_get_compradores_cc` + email2) o, si no hay, al usuario del envío, con cada proveedor sin ficha y el enlace a su pedido.

**Verificación:** `t_v44` (Postgres 16 + Flask, 14 comprobaciones): dos documentos (proveedor con ficha y sin ella) → 2 pedidos con las mismas fechas, cada uno con su presupuesto (y no el del otro), su documento de V.º B.º, Nº y fecha de presupuesto; correo encolado a los compradores con el Nº del pedido; reenvío sin duplicar el PDF y añadiendo el documento nuevo; versión nueva del presupuesto sí se añade; un «presupuesto» que no es PDF → 400. Contrato con Activo Operacional v1.18.1 (`divisionPorProveedor.test.mjs` con `CP_TEST_URL`): 5/5. `t_v43` sigue en verde. No probado: despliegue real en Render.

**Norma 5:** no aplica (sin tablas, columnas ni variables nuevas).

**Documentos revisados:** `README.md` (versión), `CHANGELOG.md`; `GUIA_DESPLIEGUE.md`, `PENDIENTES.md` e `INSTRUCCIONES_RESTAURACION.md` — no aplica.

## 2026-10-24 — [Control Pedidos] El Nº de orden de un pedido eliminado no se reutiliza (v12.33.43)

**Petición de Víctor:** «¿Puedes revisarlo en la aplicación?» — en Pedidos Eliminados había dos «Nº 1006» (Maspalomas, eliminado a mano a las 15:20, y Guayarmina, creado a las 15:21 desde Activo Operacional).

**Causa:** `_next_norden()` = `MAX(norden)` de `pedidos` del año + 1; el pedido eliminado ya no está en `pedidos`, así que su número quedaba libre. Igual en la importación por Excel (`base_norden`).

**Cambios:**
- `_max_norden_anio(cur, year)`: `GREATEST` de `pedidos` (año de `creado_en`) y `pedidos_eliminados` (año de `COALESCE(pedido_creado_en, eliminado_en)`), tras `pg_advisory_xact_lock(724113)` (se suelta en el commit/rollback de la petición). Lo usan `_next_norden()` (alta manual, SAP, Activo Operacional, copias del V.º B.º) y la importación por Excel.
- `_auto_migrate()`: `ALTER TABLE pedidos_eliminados ADD COLUMN IF NOT EXISTS pedido_creado_en TIMESTAMPTZ`. `_guardar_y_borrar_pedido()` la rellena con `pedido.creado_en`.

**Verificación:** `t_v43` (Postgres 16 + Flask, 10 comprobaciones): alta → Nº 4, se elimina, la siguiente → Nº 5 (antes 4); un eliminado antiguo sin fecha de alta borrado este año cuenta; uno de otro año no; 4 altas simultáneas → 4 números distintos; `_next_norden` coincide. No probado: despliegue real en Render.

**Límite conocido:** los eliminados anteriores a esta versión no tienen fecha de alta y cuentan por el año en que se borraron; si alguno de 2025 con un Nº alto se borró en 2026, la numeración de 2026 saltaría por encima de él (salto, nunca repetición).

**Norma 5:** no aplica a `GUIA_DESPLIEGUE.md` ni a `PENDIENTES.md` (sin variables nuevas; la columna `pedidos_eliminados.pedido_creado_en` la crea `_auto_migrate()`). Restauración: si `restore_agent.py` (en el PC, fuera de este repo) copia `pedidos_eliminados` con una lista fija de columnas, la columna nueva queda vacía al restaurar, que equivale a un registro anterior a esta versión; no rompe nada.

**Documentos revisados:** `README.md` (versión), `CHANGELOG.md`; `GUIA_DESPLIEGUE.md`, `PENDIENTES.md` e `INSTRUCCIONES_RESTAURACION.md` — no aplica.

## 2026-10-24 — [Control Pedidos] Borrado de pedidos de prueba de Activo Operacional (v12.33.42)

**Petición de Víctor:** «Necesito poder eliminar los pedidos que estamos realizando de prueba en material operacional y poner contador a cero.» Elegido: los pedidos de Control de Pedidos vinculados van a «Pedidos Eliminados», con un botón en Activo Operacional.

**Cambios:**
- `_guardar_y_borrar_pedido(pedido, pid, motivo, uid, nombre)`: `INSERT pedidos_eliminados` + `DELETE pedidos`, sin `commit`. Lo usan `delete_pedido` y la ruta nueva.
- `api_externo_ao_eliminar_pedidos` → `POST /api/externo/activo-operacional/pedidos/eliminar`: firma `AO_BRIDGE_SECRET` (`_dali_bridge_firma_valida`, un solo uso), `refs` con `^AO-\d{1,9}$` (máx. 200), busca `ref = r OR ref LIKE r || '/%'` con `FOR UPDATE`, borra y hace un único `commit`; devuelve `eliminados` y `no_encontradas`.
- README: secciones «Seguridad» y «Copias de seguridad y restauración»; tabla de variables completa. `render.yaml`: variables del puente declaradas (`sync: false`).

**Verificación:** con Postgres 16 + Flask real (puerto 4301) y Activo Operacional v1.18.0 en local, `pedidosPrueba.test.mjs` (16 comprobaciones): borra `AO-175` y su copia `AO-175/2`, las dos quedan en `pedidos_eliminados` con el motivo, la referencia queda libre y repetir el borrado desde Activo Operacional da 404 (ya no existe). `python -W error -c "import ast; ast.parse(open('app.py').read())"` sin avisos. No probado: despliegue real en Render.

**Norma 5:** no aplica (sin tablas ni variables nuevas; las variables que ahora declara `render.yaml` ya existían en producción desde v12.33.36).

**Documentos revisados:** `README.md` (versión, variables, seguridad, copias), `CHANGELOG.md`, `render.yaml`; `GUIA_DESPLIEGUE.md`, `PENDIENTES.md` e `INSTRUCCIONES_RESTAURACION.md` — no aplica.

## 2026-10-24 — [Control Pedidos] Las peticiones firmadas del puente no se pueden reenviar (v12.33.41)

**Origen:** hallazgo N-2 de la revisión completa: dentro de la ventana de 5 minutos una firma capturada se podía repetir.

**Cambios:**
- `_bridge_firma_ya_usada()` + `_BRIDGE_FIRMAS_USADAS` (diccionario en memoria con candado, TTL = 2 × margen + 60 s, tope 20.000): `_dali_bridge_firma_valida()` registra cada firma válida de las peticiones que no son `GET`/`HEAD`/`OPTIONS` y rechaza (401 + `logging.warning`) la segunda vez. Solo se guardan firmas válidas, y las lecturas quedan fuera porque AO y Catálogo consultan con cuerpo vacío y dos llamadas del mismo segundo comparten firma sin ser un reenvío.
- Sin tablas ni variables nuevas. Límite: memoria por proceso (un worker en Render).

**Verificación:** `t_v41` (Postgres 16 + Flask, 12 comprobaciones): la misma petición dos veces → 200 y 401 (un solo correo encolado); otra petición en el mismo segundo y la misma con otra marca de tiempo → 200; firma con secreto equivocado y caducada → 401; `GET` repetido con la misma firma → pasa; `POST` de AO reenviado → 401; purga de entradas caducadas. `t_v35`, `t_v37`, `t_v38`, `t_v39` y `t_v40` siguen en verde (20, 33, 18, 41 y 9 comprobaciones). No probado: despliegue real en Render ni varios workers.

**Documentos revisados:** `README.md` (versión), `CHANGELOG.md`; `GUIA_DESPLIEGUE.md` (sin variables nuevas), `PENDIENTES.md` e `INSTRUCCIONES_RESTAURACION.md` — no aplica.

## 2026-10-24 — [Control Pedidos] IP del cliente fiable y errores internos sin detalle (v12.33.40)

**Origen:** revisión completa de las actualizaciones (N-1, CP-09 residual, N-4).

**Cambios:**
- `_ip_cliente()`: ya no toma el primer valor de `X-Forwarded-For` (lo controla el cliente); toma el N-ésimo por la derecha, con N = `IP_PROXIES_CONFIABLES` (por defecto 1; 0 usa `remote_addr`; si la cabecera trae menos valores, el primero). El límite por IP del login (`_RL_*`) y la IP de trazabilidad de las solicitudes de acceso dependen de ella.
- Nuevo `_error_interno(exc, contexto)`: referencia aleatoria de 6 hex, log con traceback y texto genérico al cliente. Sustituye a `str(exc)`/`str(e)` en 32 respuestas 500 de `api_*`; `server_error` y `unhandled_exception` ya no devuelven el texto de excepciones que no sean HTTP (las HTTP conservan el suyo). Se dejan los 400 con mensaje pensado para el usuario.
- Cadena de documentación con `\\` escapada (sin `SyntaxWarning`).

**Verificación:** `t_v40` (Postgres 16 + Flask): 1 y 2 proxies, cabecera corta, 0 y valor no numérico; 12 intentos con la cabecera cambiando → 8×401 y bloqueo desde el 9.º (antes 30); otra IP real entra; un fallo forzado de `query()` no devuelve su texto. `t_v35`, `t_v37`, `t_v38`, `t_v39` siguen en OK.

**Documentos revisados:** `README.md` (versión), `GUIA_DESPLIEGUE.md` (variable nueva en la tabla), `PENDIENTES.md` e `INSTRUCCIONES_RESTAURACION.md` — no aplica.

## 2026-10-24 — [Control Pedidos] Un pedido por proveedor al enviar a V.º B.º desde Activo Operacional (v12.33.39)

**Origen:** petición de Víctor: «cuando pulsemos enviar para visto bueno a dirección ... mantendríamos el ya creado y se realizarían 3 copias más con la misma info hasta ahora pero con la diferencia que ya tenemos nombre de proveedor ... y en cada una colocaremos el presupuesto correspondiente enviado para firma».

**Cambios:**
- `_auto_migrate` y `models.py`: columna `pedidos.proveedor_ao TEXT` (nombre del proveedor tal como lo manda Activo Operacional).
- `api_externo_ao_visto_bueno`: lee también `proveedor`, `presupuestos` y `total` de cada documento; con `dividir: true` delega en la nueva `_ao_vb_dividir()`; sin él, todo igual que en la v12.33.33.
- `_ao_vb_dividir`: bloquea (`FOR UPDATE`) el original y su grupo (`AO-<n>/%`); ordena los documentos por importe; empareja cada documento con un pedido del grupo (1.º por `proveedor_ao`, 2.º por ficha de proveedor, 3.º el original si aún no tiene proveedor) o crea una copia (`_next_norden`, solicitud_doc copiado, historial); rellena `proveedor_id` (si hay ficha), `proveedor_ao`, `presupuesto_num` (varios separados por coma), `fecha_presupuesto`, `fecha_envio_visto_bueno`, adjunta el documento (`vb_eml`) y aplica la misma transición de estado; devuelve `pedidos[]` (id, Nº, ref, creado, estado) y `huerfanos[]`. Todo en una transacción; los avisos de cambio de estado salen después del `commit`.
- No se rellena `importe` ni se adjunta el presupuesto original del proveedor (decisión por defecto, pendiente de confirmar con Víctor).

**Verificación:** `t_v39` (Postgres 16 + Flask, firma HMAC real): firma incorrecta → 401; ref con `/` → 400; ref inexistente → 404; 4 proveedores → 4 pedidos (original con el de mayor importe, 3 copias, Nº de orden distintos, estado, hotel/departamento/fecha/observaciones copiados, 1 solicitud_doc y 1 vb_eml cada uno, importe sin tocar); proveedor con ficha, sin ficha y sin presupuesto; reenvío idéntico → mismos pedidos y 2 vb_eml; reenvío con orden/importes distintos, proveedor nuevo y uno que desaparece (huérfano intacto); un solo proveedor → sin copias; modo antiguo (sin `dividir`) intacto; fallo simulado a mitad → 500 sin cambios. `t_v37` y `t_v38` siguen en OK.

**Documentos revisados:** `README.md` (versión), `GUIA_DESPLIEGUE.md`, `PENDIENTES.md`, `INSTRUCCIONES_RESTAURACION.md` — no aplica más allá de lo anotado (sin variables nuevas).

## 2026-10-23 — [Organizador] v4.18.02 — Corrección: al soltar un archivo en el chat se cerraba la aplicación

- **Síntoma (Víctor, Windows):** al arrastrar un archivo (PDF de 4,6 MB) sobre la ventana del chat se cerraba el Organizador entero. Con 📎 y con Ctrl+V no ocurría.
- **Causa probable (no reproducible fuera de Windows):** `app/ui/dnd_windows.py` v1.0 cambiaba el procedimiento de ventana con `SetWindowLongPtrW` en todas las ventanas del chat (unas 40) y, al cerrar el chat, liberaba los callbacks de `ctypes` mientras esas ventanas seguían apuntando a ellos; además tocaba tkinter desde dentro del callback nativo. Cualquiera de las dos cosas puede tumbar el proceso sin dejar mensaje (la app va sin consola).
- **Corrección (`dnd_windows.py` v2.0):** `SetWindowSubclass` / `DefSubclassProc` de comctl32 (la API documentada para esto, que encadena bien y se desengancha sola al destruir la ventana) solo sobre la ventana de nivel superior (marco de Tk y su área cliente; Windows busca el destino subiendo por las ventanas padre); los callbacks no se liberan nunca; el callback nativo solo lee las rutas con `DragQueryFileW` y las deja en una `queue.Queue` — nunca llama a tkinter — y un `after` de 150 ms las recoge en el hilo normal y llama a `_confirmar_y_enviar`; cualquier excepción dentro del callback se traga y devuelve 0.
- **Interruptor:** `"chat_arrastrar_soltar": false` en `%APPDATA%\OrganizadorPrincess\config.json` desactiva el arrastre sin tocar nada más (queda 📎 y Ctrl+V).
- **Verificación:** prueba de la lógica con la API nativa simulada (Tk 8.6, Xvfb): el callback responde 0 a `WM_DROPFILES`, reenvía el resto a `DefSubclassProc`, no llama a la función del chat dentro del callback, las rutas con ñ y espacios llegan enteras, una excepción en la función del chat no rompe el sondeo. **Sin probar: el arrastre real en Windows** — si volviera a cerrarse, usar el interruptor y avisar.
- `APP_VERSION` → "v4.18.02"; `MyAppVersion` → "4.18.02" (numeración par); manuales con la versión nueva.

---

## 2026-10-23 — [Organizador] v4.18.00 — Vista reducida del menú principal y chat con arrastrar/pegar archivos

- **Vista reducida/extendida (`main_agenda.py`).** Clave nueva en `config.json`: `vista_menu = {"modo": "extendida"|"reducida", "reducida_opciones": [n…]}` (sin ella, extendida; si faltan opciones, las 10 primeras). `_vista_actual()` valida y normaliza (1–30, sin repetidos, máx. 10). `_aplicar_vista()` reorganiza sin reiniciar: en reducida muestra los 4 primeros accesos dorados en 2×2 (`grid_remove` de los 5 y 6), los botones azules elegidos en 2×5 y ajusta tamaño y `wraplength`; la ventana se calcula con el tamaño real de la cabecera (`winfo_reqwidth/height`) y queda en la misma esquina (`WIN_X`, `WIN_Y`). En extendida restaura todo (6 columnas × 5 filas). Las celdas azules se guardan en `btn_cells`/`btn_lbls` y se colocan con `_colocar_celda()`. `_ventana_vista_menu()` + botón «Vista» en la cabecera del panel Admin: selector de modo, casillas de los 30 botones con contador «n de 10» y «Guardar y aplicar».
- **Chat: arrastrar y soltar y Ctrl+V.** `app/ui/dnd_windows.py` (nuevo): `hook_dropfiles(ventana, func)` activa `WM_DROPFILES` con `ctypes` (sin dependencias nuevas) en la ventana y en todos sus widgets con ventana propia, con tipos explícitos para 32 y 64 bits y `DragQueryFileW` (Unicode); fuera de Windows o ante cualquier error no hace nada. `app/ui/ventana_chat.py`: `_enviar_rutas()`, `_confirmar_y_enviar()` (solo archivos, máx. 5, pregunta «¿Enviar a …?»), `_pegar()` en `Ctrl+V` (`PIL.ImageGrab.grabclipboard()`: imagen → PNG temporal `captura_chat_*.png` que se borra tras enviar o cancelar; lista de rutas → archivos copiados; `None` → pegado de texto normal). El botón 📎 usa ahora `_enviar_rutas`. Los límites los sigue aplicando `chat_client.enviar_archivo` y el servidor (10 MB, extensiones prohibidas).
- `main.spec`: `ui.dnd_windows` en `hiddenimports`. `APP_VERSION` → "v4.18.00"; `MyAppVersion` → "4.18.00" (se salta la 4.16.10 y la 4.17.x: numeración par a petición de Víctor).
- **Verificación:** arranque real de `main_agenda.py` con Tk 8.6 y pantalla virtual (Xvfb): extendida 6 dorados + 30 azules; reducida 4 + 10 en 2×5, con ventana de 1518×411 frente a 1817×946; cambio en caliente en los dos sentidos; diálogo con 30 casillas, límite de 10 con aviso, guardado en memoria y en disco. Lectura de rutas de `DragQueryFileW` con ñ y espacios (simulada). **Sin probar aquí:** el arrastre real, `Ctrl+V` con imagen y archivos, y el aspecto con las fuentes de Windows.
- **Manuales nuevos (Usuario y Administrador).** `docs/Manual_Usuario_OrganizadorPrincess.(docx|pdf)` (14 págs.) y `docs/Manual_Administrador_OrganizadorPrincess.(docx|pdf)` (11 págs.), con el mismo estilo que los de Activo Operacional (portada, capítulos numerados, capturas con marcas rojas, avisos). El manual de usuario anterior (v4.12.6, con secciones de Telegram y alertas que ya no existen) se sustituye: el PDF nuevo ocupa su sitio en la raíz (`Manual_Usuario_OrganizadorPrincess.pdf`, el que abre el botón «Manual» y copia el instalador). El instalador copia además el manual de administrador (`docs\Manual_Administrador_OrganizadorPrincess.pdf`, `skipifsourcedoesntexist`) y crea el acceso «Manual de Administrador» en el menú Inicio. Las capturas son de la propia app con datos de ejemplo, generadas con Tk 8.6 en pantalla virtual (Linux): las fuentes y el aspecto exacto en Windows pueden variar algo.

---

## 2026-10-23 — [Organizador] v4.16.9 — Seguridad: adjuntos del chat, contraseña cifrada, actualizador (auditoría de octubre, anexo main_agenda)

- **MA-01 · `app/services/chat_client.py`.** Antes `descargar_adjunto` hacía `os.path.join(Descargas, nombre_archivo)` con el nombre que mandaba el remitente y `abrir_archivo` ejecutaba `os.startfile` sobre el resultado. Con `..\` o una ruta absoluta el archivo se escribía fuera de Descargas, y un `.bat`/`.exe`/`.lnk` se ejecutaba al pulsar la burbuja. Ahora: `nombre_adjunto_seguro()` (nombre base, sin caracteres de ruta/control, sin nombres reservados de Windows, máx. 120), `url_adjunto_permitida()` (https y host `*.supabase.co`, más los de `config.json` → `chat_hosts_adjuntos`), descarga en streaming con tope de 12 MB y sin seguir redirecciones, creación exclusiva (`"xb"`) comprobando que queda dentro de Descargas, y `abrir_archivo` solo abre con el programa por defecto una lista corta de extensiones (`EXT_ABRIR_DIRECTO`); el resto → `explorer /select,`.
- **MA-02 · `app/db/dpapi.py` (nuevo), `app/db/sqlite.py`, `pedidos_agenda_bridge.py`.** `config_usuarios.bridge_password` se guarda como `dpapi1:` + base64 del blob de `CryptProtectData` (solo el mismo usuario de Windows en el mismo equipo lo descifra). Una contraseña antigua en claro se migra al leerla y se hace `VACUUM` para no dejar restos. Si DPAPI falla al cifrar se guarda como antes; si falla al descifrar (otro equipo/usuario) devuelve vacío y hay que reescribirla en Admin → Mi Usuario. El puente (`_cargar_credenciales_desde_db`) ya no lee la columna por su cuenta: usa `get_bridge_credentials()`. `main.spec`: `db.dpapi` en `hiddenimports`.
- **MA-03 · `app/services/update_service.py`.** `_ssl_ctx()` ya no cae a un contexto sin verificación. Si el release publica `<instalador>.sha256` o `SHA256SUMS(.txt)` se calcula el SHA-256 durante la descarga y, si no coincide, se borra el archivo y se avisa; si no publica hash, se dice en pantalla que la integridad no está verificada. El hash del mismo release no protege frente a quien controle el release: lo que sí lo haría es firmar el `.exe` (pendiente).
- **MA-05 · `main_agenda.py`.** `_esc()` (`html.escape`) en el HTML de impresión (títulos, horas, usuario).
- **Extra · `app/services/admin_auth.py`.** `secrets.compare_digest` sobre bytes: con `str` lanzaba `TypeError` si la contraseña guardada o escrita llevaba ñ/tildes.
- **No se toca (decisión pendiente):** MA-04 (rama «1-bis» del panel Admin: es el flujo de «Crear acceso» mientras se aprueba el alta) y MA-06 (el desinstalador borra `%APPDATA%\OrganizadorPrincess`; `taskkill /IM` cierra la app de todas las sesiones; dependencias sin versión fijada; sin firma de código).
- **Verificación:** `t_ma` (Python 3.13 en Linux; el cifrado DPAPI se simuló porque la llamada real a Windows no se puede ejecutar aquí), 35 comprobaciones: nombres con `..\`, ruta absoluta, UNC, `:` y nombres reservados; URL con `http`, host ajeno, `supabase.co.evil.example` y `@`; descarga dentro de Descargas, colisión → `evil (1).pdf`, archivo grande con y sin `Content-Length` rechazado y sin restos; PDF → `startfile`, `.exe`/`.bat` → Explorador; migración de la contraseña antigua sin restos en el fichero, ida y vuelta con ñ, fallo de DPAPI → vacío sin excepción. `ast.parse` de todos los módulos modificados. **Pendiente de probar en un PC con Windows:** la llamada real a DPAPI, la descarga de un adjunto y el hash del instalador.
- `APP_VERSION` → "v4.16.9"; `MyAppVersion` → "4.16.9"; `release_notes.md` y `release_notes_actual.txt` actualizados. Al publicar el release hay que subir también el `.sha256` (comando en `release_notes.md`).

---

## 2026-10-23 — [Chat] v1.2.2 (`app.py`, `requirements.txt`, `.github/workflows/keep-alive-chat.yml`) — Seguridad: adjuntos, usuario activo, límites

- **CH-01.** `_sanear_nombre_archivo()` en `POST /api/chat/mensajes/archivo`: nombre base, sin caracteres de ruta/control/inversión de texto, máx. 120; rechaza (400) las extensiones de `EXTENSIONES_PROHIBIDAS` en cualquier segmento (`a.exe.pdf` y `a.pdf.exe`). `_mime_seguro()` deduce el tipo de la extensión. Ruta en Storage codificada y `x-upsert: false`.
- **CH-02.** `_error_sesion()` (REST y socket): comprueba `activo` en `usuarios` con caché de 60 s (fail-open si falla la consulta o no hay `DATABASE_URL`) y rechaza con 403 las sesiones con `debe_cambiar_password`.
- **CH-03.** `MAX_CONTENT_LENGTH`, límite de ritmo en memoria (60 mensajes/min, 10 archivos/min, 10 grupos/h), destinatario y miembros de grupo validados contra `usuarios` (máx. 50), 413 con mensaje claro.
- **CH-04.** Error 500 sin detalle, `CHAT_CORS_ORIGINS` opcional (por defecto `*`), `requirements.txt` con tope, cron del keep-alive válido en verano e invierno.
- **Verificación:** `t_chat` (Postgres 16 + cliente de Flask + cliente de Socket.IO), 47 comprobaciones.

---

## 2026-10-23 — [Control Pedidos] Solicitud de acceso: sin correos duplicados y con cuenta atrás (v12.33.38)

**Origen:** aviso de Víctor, dos correos idénticos de "Verificación de acceso" en una sola solicitud de prueba.

**Cambios:**
- `solicitar_usuario_fase1`: `pg_advisory_xact_lock` por correo + comprobación de solicitud abierta del mismo correo en los últimos `SOLICITUD_VENTANA_DUPLICADA_MIN` (10) minutos; si existe devuelve `{"duplicada": true, "sol_id": …}` sin insertar ni encolar nada.
- `admin_enviar_fase2`: espera `FASE2_REENVIO_ESPERA_S` (60 s) calculada desde `token_expira - 72 h` y desde `emails_sistema_pendientes.enviado_en`; 429 con `retry_after` si no ha pasado o si la fila de la cola está reservada (`en_proceso_desde` < 2 min). Al regenerar el token marca `descartado_en` la fila de cola `solicitud_acceso_fase2` pendiente (llevaba el token anterior).
- `admin_listar_solicitudes`: el LEFT JOIN ignora filas descartadas.
- `templates/index.html`: helper genérico de cuenta atrás (`_cdIniciar/_cdRestante/_cdPintar`, atributos `data-cd-key`/`data-cd-texto`, persistido en `localStorage` con try/catch) aplicado al botón del formulario público (60 s tras enviar, 5 s tras error, guarda contra doble clic) y al botón "Enviar/reenviar Fase 2" del panel; aviso `sol-f1-dup` cuando el servidor devuelve `duplicada`.
- No hay cambios de esquema ni de variables.

## 2026-10-23 — [Control Pedidos] Seguridad: sesión del puente limitada (v12.33.37)

**Origen:** hallazgo CP-10 de la auditoría de main_agenda (anexo de la auditoría de octubre).

**Cambios:**
- `_completar_login` marca `session["via_bridge"] = True` cuando `metodo == "bridge"`.
- `@app.before_request _limitar_sesion_puente`: con esa marca, en rutas `/api/` solo pasan `/api/bridge/*`, `/api/login*`, `/api/logout`, `/api/version` y `/ping`; el resto devuelve 403 y deja un aviso en el log.
- `bridge_login`: se elimina el aviso por no definir `BRIDGE_USUARIOS` (la variable opcional se mantiene). Corrige la recomendación de la v12.33.35.

**Verificación:** `t_v37` (Postgres 16 + Flask), con una cuenta de compras y una de administrador: tras `bridge/login`, `/api/bridge/alertas` y `/api/bridge/notificaciones` → 200; `/api/me`, `/api/pedidos`, `/api/usuarios`, `/api/maestros`, `/api/admin/solicitudes-acceso`, `/api/config-avisos/resolver` y `POST /api/cambiar-password` → 403; `logout` → 200 y después 401; el login normal no queda limitado y, tras una sesión de puente, entrar con `/api/login` en el mismo cliente quita la marca; `/ping` y `/` siguen respondiendo. `t_v34`, `t_v35` y `t_v36` siguen en TODO OK (en `t_v36` la comprobación de `bridge/login` ahora exige 403 en `/api/pedidos` y 200 en las alertas).

## 2026-10-23 — [Control Pedidos] Seguridad: cambio obligatorio de contraseña temporal y secretos por canal (v12.33.36)

**Origen:** pendientes de la v12.33.35, «cambio forzado de la contraseña temporal» (CP-04) y hallazgo X-01 (un solo `DALI_SSO_SECRET` para tres canales).

**Cambios:**
- **Columna.** `_auto_migrate`: `usuarios.debe_cambiar_password BOOLEAN NOT NULL DEFAULT FALSE` junto a `ultima_verificacion_login`.
- **Marca.** `admin_aprobar_solicitud`, `create_usuario` y `update_usuario` (solo si el administrador cambia la contraseña de OTRO usuario) ponen la columna a TRUE. `cambiar_password_con_token` y el nuevo endpoint la ponen a FALSE.
- **Sesión.** `_completar_login` guarda `session["debe_cambiar_password"]` (salvo `metodo="bridge"`) y lo devuelve en la respuesta; `/api/me` también lo informa.
- **Bloqueo.** `@app.before_request _exigir_cambio_password`: con la marca en sesión, solo pasan `/api/me`, `/api/logout`, `/api/cambiar-password`, `/api/login*`, `/api/password-reset/*`, `/api/version` y `/ping`; el resto devuelve 403 con `debe_cambiar_password`.
- **Endpoint.** `POST /api/cambiar-password` (`login_required`): comprueba la actual con `_verifica_y_migra_password`, valida la nueva con `_validar_password_nueva` (8–128 caracteres, letras y números, distinta de la actual y del usuario), límite de 5 fallos/15 min con el limitador de la v12.33.35, traza `password_cambiada`.
- **Pantalla.** `templates/index.html`: `_forzarCambioPassword()` (superposición con contraseña actual, nueva y repetición) llamada desde `_entrarEnApp()` y desde el arranque con sesión; botón para cerrar sesión.
- **X-01.** `_secretos_puente_ruta()` y `_dali_bridge_firma_valida()`: según la ruta (`/api/externo/activo-operacional/*` o `/api/externo/dali-sap/*`, y método para la lectura de AO) se admiten `AO_BRIDGE_SECRET` o `DALI_BRIDGE_SECRET`, más `DALI_SSO_SECRET` si `BRIDGE_ACEPTA_SSO_SECRET != "0"`. La comparación recorre todos los secretos sin cortocircuito.
- Correo de bienvenida (HTML y texto) y `GUIA_DESPLIEGUE.md` (variables).

**Verificación:** `t_v36` (Postgres 16 + Flask + Chromium), 42 comprobaciones: alta manual y aprobada marcadas; con la marca `/api/pedidos`, `/api/maestros` y `/api/usuarios` → 403 y `/api/me` → 200; actual errónea, nueva corta, igual a la actual, solo números, solo letras o igual al usuario → 400 y sigue marcada; cambio correcto → 200, marca fuera y la API vuelve; la temporal deja de entrar; 6.º intento con la actual errónea → 429; el administrador que fija la clave de otro lo marca y la suya no; restablecer por enlace quita la marca; `bridge/login` no queda bloqueado; por canal: el secreto de Catálogo no vale en Activo Operacional, el de Activo Operacional no vale para encolar correos, y con `BRIDGE_ACEPTA_SSO_SECRET=0` el `DALI_SSO_SECRET` deja de valer; en el navegador aparece la pantalla, avisa si no coinciden, desaparece al guardar y no reaparece al recargar. `t_v34` y `t_v35` siguen en TODO OK; `init_db.py` + dos arranques en base vacía correctos.

**Pendiente:** retirar el `DALI_SSO_SECRET` de los servicios que ya no lo necesitan y poner `BRIDGE_ACEPTA_SSO_SECRET=0` cuando Catálogo y Activo Operacional estén desplegados con los suyos; un tiempo máximo de vida para la contraseña temporal (hoy no caduca).

## 2026-10-22 — [Control Pedidos] Seguridad: límite de intentos, contraseñas temporales y dependencias (v12.33.35)

**Origen:** segunda parte de la auditoría de Control Pedidos. Hallazgos CP-04, CP-05, CP-08, CP-09 (parte) y vulnerabilidades de dependencias.

**Cambios:**
- **CP-04, sin límite de intentos.** Nuevo limitador en memoria (`_rl_segundos_bloqueo`, `_rl_registrar`, `_rl_limpiar`, `_rl_golpe`, `_rl_respuesta_429`, `_reglas_login`) junto a `_ip_cliente()`. `login`: 8 fallos/15 min por cuenta+IP, 30 por cuenta, 60 por IP. `verificar_codigo_login`: 5 fallos/10 min por cuenta (y 40 por IP); al excederse se marcan como usados los códigos vigentes. `solicitar_reset_password`: 3/h por usuario, 20/h por IP, con respuesta genérica. `cambiar_password_con_token`: 20 fallos/h por IP. Solicitudes públicas (`solicitar_usuario_fase1`, `_directo`, `_fase2`): 15/h por IP. Las claves combinan cuenta e IP para que un tercero no pueda bloquear a un usuario desde otra IP.
- **CP-04, contraseña temporal.** `admin_aprobar_solicitud` usa `secrets.choice` sobre un alfabeto sin ambiguos, 12 caracteres (antes `Princess` + `randint(1000, 9999)`).
- **CP-05, `bridge_login`.** Mismo límite de intentos; variable opcional `BRIDGE_USUARIOS` (lista de usernames) que restringe quién puede saltarse la verificación por email. Sin ella, igual que antes con aviso en el log. Documentada en `GUIA_DESPLIEGUE.md`.
- **CP-08, base vacía.** CREATE TABLE IF NOT EXISTS de `emails_sistema_pendientes` antes de sus primeros ALTER en `_auto_migrate`.
- **CP-09 (parte).** `login`, `verificar_codigo_login`, `bridge_login`, `solicitar_reset_password` y `cambiar_password_con_token` aplican `str()` a los campos recibidos.
- **Dependencias** (`requirements.txt`): Pillow 12.3.0→13.0.0, pypdf 6.16.2→6.21.2, cryptography 46.0.7→50.0.2, certifi→2026.10.19, urllib3 2.7.0→2.8.0, werkzeug 3.1.8→3.1.9.

**Verificación:** `t_v35` (Postgres 16 + cliente de Flask), 21 comprobaciones: 8 fallos → 401 y el noveno, con la clave correcta, → 429 con `Retry-After`; la misma cuenta desde otra IP entra; rotar `X-Forwarded-For` acaba bloqueado por cuenta; 5 códigos malos → 401 y el sexto, con el código correcto, → 429 y el código queda invalidado; 5 solicitudes de reset generan 3 tokens; solicitudes públicas 15 → 200, después 429; bridge: cuenta fuera de `BRIDGE_USUARIOS` → 401, dentro → 200, sin variable → 200, y 429 tras 8 fallos. `t_v34` sigue en TODO OK. En un entorno virtual limpio con las dependencias nuevas: pypdf, pdfplumber, miniaturas de Pillow y `pip check` correctos; `pip-audit` sin vulnerabilidades. Base nueva: `init_db.py` + dos arranques sin errores.

**Limitaciones conocidas:** el limitador se pierde al reiniciar y asume 1 worker; la IP sale de `X-Forwarded-For` (primer elemento), por eso hay también un umbral solo por cuenta. Los mensajes `str(exc)` de endpoints autenticados no se han tocado. Falta el cambio forzado de la contraseña temporal en el primer acceso (requiere pantalla).

## 2026-10-22 — [Control Pedidos] Seguridad: correcciones de la auditoría (v12.33.34)

**Origen:** auditoría completa de Control Pedidos, Catálogo Asignaciones y Activo Operacional pedida por Víctor («auditoría completa, si hay alguna vulnerabilidad»). Informe: «Auditoría de las tres aplicaciones Princess (octubre 2026)». Hallazgos CP-01, CP-02, CP-03, CP-06 y CP-07, más una parte de CP-09.

**Cambios:**
- **CP-01, XSS almacenado sin autenticación.** `adminCargarSolicitudes()` y unos 80 puntos más de `templates/index.html` pintaban datos de usuario con `innerHTML` sin escapar; ahora usan `_escHtmlCp()` (nombres, apellidos, correo, hoteles, usuario Windows, usuarios, adjuntos, historial, notas, observaciones, hoteles y proveedores). Los atributos `value="${esc(...)}"` pasan a `_escHtmlCp()` porque `esc()` solo escapa la comilla simple.
  - Segunda barrera en `app.py`: `_con_marcado()` rechaza `<`, `>`, `"` y caracteres de control en `solicitar_usuario_fase1`, `solicitar_usuario_directo`, `solicitar_usuario_fase2`, `bridge_solicitar_alta`, `create_usuario` y el cambio de nombre de usuario, con tope de 300 caracteres en las solicitudes.
  - `upload_adjunto` sustituye esos caracteres en el nombre del archivo.
- **CP-02, adjuntos sin control de hotel.** Nuevos `_hotel_accesible()`, `_sin_acceso_pedido()` y `_adjunto_hotel_id()`; los cinco endpoints (`get_adjuntos`, `upload_adjunto`, `download_adjunto`, `download_adjunto_thumb`, `delete_adjunto`) devuelven 403 si un usuario de rol hotel no tiene ese hotel. La descarga pública por token no se toca.
- **CP-03, `aprobar_expediente` y `denegar_expediente`** devuelven 403 si el rol no es admin ni compras.
- **CP-06, cabeceras y cookie.** Nuevo `after_request` `_cabeceras_seguridad`; `SESSION_COOKIE_SECURE` (variable `COOKIE_SECURE`, por defecto sí), `SESSION_COOKIE_SAMESITE=Lax`, `MAX_CONTENT_LENGTH` de 80 MB.
- **CP-07.** `solicitar_reset_password` ya no escribe el enlace en el log.
- **CP-09 (parte).** Observaciones escapadas con `_html_escape` en los correos HTML de estado y de alertas.

**Verificación:** contra Postgres 16 y el cliente de pruebas de Flask, con Chromium (Playwright):
- usuario hotel A: listar, descargar, miniatura, subir y borrar adjuntos del hotel B → 403 (antes 200/201); con su propio pedido → 200/201;
- usuario hotel: aprobar y denegar expediente → 403 y el expediente sigue pendiente; compras: denegar → 200 y aprobar pasa el control de rol;
- cookie con `Secure; SameSite=Lax; HttpOnly` y cinco cabeceras de seguridad presentes;
- solicitud pública con `<img onerror>` → 400; solicitud normal con apóstrofo → 200; admin que crea un usuario con HTML → 400;
- con datos ya envenenados en la base (solicitud, nombre de usuario, observaciones, historial, nombre de adjunto) la versión anterior ejecutaba 7 scripts; esta, ninguno, y la solicitud se ve como texto;
- `py_compile` correcto y sin errores de JavaScript en la página.

**Pendiente (otra versión):** límite de intentos de login, código y restablecimiento; contraseñas temporales con `secrets` y cambio forzado; `bridge/login`; actualizar Pillow, pypdf y cryptography; arranque en base vacía.

**Norma 5:** no aplica (sin variables obligatorias ni tablas nuevas; `COOKIE_SECURE=0` es opcional y solo para desarrollo local sin HTTPS).

## 2026-10-21 — [Control Pedidos] V.º B.º desde Activo Operacional: estado de firma y correo de Dirección (v12.33.33)

**Petición de Víctor:**
- «Si al enviar a Vº Bº se cambiara el ESTADO en control pedidos a PENDIENTE FIRMA DIRECCION HOTEL, se incluye la firma y se incluyen los PDF asociados a la firma pendiente.»
- «El correo de la dirección de los hoteles se encuentra en el apartado departamentos, cada uno en su hotel.»

**Cambios:**
- **`api_externo_ao_visto_bueno()`** acepta `cambiar_estado` (por defecto, sí).
  - Si el pedido está en `_AO_VB_ESTADOS_PREVIOS` (PENDIENTE COTIZACIÓN, PENDIENTE FIRMA DIRECCION COMPRAS), pasa a `_AO_VB_ESTADO_FIRMA` (PENDIENTE DE FIRMA DIRECCION HOTEL) en la misma transacción en que se ponen la fecha y los PDF `vb_eml`, que es lo que exige `_faltan_datos_envio_firma()`.
  - La fila de `historial_estados` recoge el cambio con la nota.
  - Después se llama a `_notificar_cambio_estado()`, como en un cambio a mano; si falla, solo se registra en el log.
  - Respuesta con `estado_antes`, `estado`, `estado_cambiado` y `estado_motivo` (cuando no se cambia porque el pedido ya va más adelante).
- **Nueva ruta `api_externo_ao_departamentos_hotel()`** → `GET /api/externo/activo-operacional/departamentos-hotel?hotel=<código>`.
  - Firma HMAC con cuerpo vacío, como el resto de GET del puente.
  - Lee `departamento_hotel_email` del hotel.
  - Devuelve `departamentos: [{nombre, emails}]` y `direccion` (los de la fila DIRECCION, sin tildes ni mayúsculas en la comparación).

**Verificación:** prueba de punta a punta desde Activo Operacional (`test/vistoBueno.test.mjs`) contra este Flask en local:
- sin fila DIRECCION en GY, Activo Operacional lo avisa; con ella, la usa;
- el pedido pasa de PENDIENTE COTIZACIÓN a PENDIENTE DE FIRMA DIRECCION HOTEL;
- al reenviar ya no cambia;
- en ENVIADO AL PROVEEDOR no se toca y se explica;
- hotel inexistente → 404 y firma incorrecta → 401.

**Norma 5:** no aplica (sin variables ni tablas nuevas).

## 2026-10-21 — [Control Pedidos] Envío a V.º B.º de Dirección desde Activo Operacional (v12.33.32)

**Petición de Víctor:** desde la comparativa de presupuestos de Activo Operacional, «enviar presupuestos para visto bueno de dirección» con un documento por proveedor; en Control de Pedidos, que quede la «Fecha de envío para V.º B.º» con los documentos adjuntos.

**Cambios:**
- Nueva ruta `api_externo_ao_visto_bueno()` → `POST /api/externo/activo-operacional/pedidos/visto-bueno`.
  - Comprueba la firma (`_dali_bridge_firma_valida`), `ref`, `fecha` y los PDF (hasta 30, cada uno ≤ `MAX_BYTES_DOCUMENTO`).
  - Busca el pedido por `ref_activo_operacional` (404 si no existe).
  - Pone `fecha_envio_visto_bueno` y `modificado_por`; inserta cada PDF en `pedido_adjuntos` con tipo `vb_eml` (`es_correo` falso).
  - Añade una fila en `historial_estados` con el mismo estado y la nota recibida. No cambia el estado.

**Verificación:** prueba de punta a punta desde Activo Operacional (`test/vistoBueno.test.mjs`) contra este Flask en local: fecha de hoy, los 2 PDF en el apartado «Envío para Vº Bº / firma», nota en el historial y estado sin tocar; pedido inexistente → 404; firma incorrecta → 401.

**Norma 5:** no aplica (sin variables ni tablas nuevas; usa columnas y tipos de adjunto que ya existían).

## 2026-10-20 — [Control Pedidos] Enlace directo a la ficha de un proveedor (v12.33.31)

**Petición de Víctor:** «cuando se va a solicitar presupuesto, si el proveedor no tiene correo electrónico asignado, se deberá dar la opción de abrir la ficha del proveedor directamente para cumplimentar la info».

**Cambios:**
- `api_externo_dali_proveedores` añade `id` a cada proveedor (campo nuevo; Catálogo Asignaciones no lo lee).
- `get_proveedores` acepta `?id=<id>`.
- **Frontend:**
  - `_enlaceProveedorInit()` guarda `?proveedor=<id>` al cargar la página y limpia la URL;
  - `_abrirProveedorEnlace()`, después del login o al restaurar la sesión, va a Proveedores, trae ese proveedor (`/api/proveedores?id=`), lo mete en `_provCache` y abre `openProveedorModal()` con el aviso «Completa los contactos (correo) del proveedor y guarda».

**Verificación:**
- Con el cliente de pruebas de Flask:
  - el puente devuelve el `id`;
  - `?id=` devuelve solo ese proveedor.
- En el navegador: `/?proveedor=<id>` → login → código de verificación → se abre «Editar proveedor» con su nombre, sin errores.

**Norma 5:** no aplica (sin variables ni tablas nuevas).

## 2026-10-20 — [Control Pedidos] Pedidos desde Activo Operacional en PENDIENTE COTIZACIÓN (v12.33.30)

Petición de Víctor: «desde que el comprador pulsa en crear en control de pedido, pase el estado a tramitación en activo operacional y el nuevo que se crea en control-pedidos el estado deberá ser pendiente de cotización».

Cambio: `api_externo_ao_crear_pedido()` crea el pedido con el estado `PENDIENTE COTIZACIÓN` en vez del estado inicial por defecto. El historial y `enviar_emails_estado()` usan ese estado. Si el pedido se vincula a uno existente (`vincular_a`), su estado no se toca. Activo Operacional v1.10.3 pasa a la vez su propio pedido a «En trámite».

Verificación: cliente de pruebas de Flask y prueba de punta a punta desde Activo Operacional. El pedido nace en PENDIENTE COTIZACIÓN y el resto de comprobaciones de la v12.33.28/29 siguen OK.

Norma 5: no aplica (sin variables ni tablas nuevas).

## 2026-10-20 — [Control Pedidos] Aviso de posible pedido duplicado al dar de alta (v12.33.29)

**Petición de Víctor:** «para evitar duplicidades en control-pedidos, cuando se vaya a crear un nuevo pedido tanto manual como automático, al introducir hotel y departamento, la aplicación debe verificar que no exista ningún pedido abierto con esta configuración y sin número de pedido aún adjudicado. Si existe, preguntar al usuario que compruebe que no es el mismo inicio de pedido nuevamente».

**Backend:**
- `_pedidos_abiertos_sin_numero(hotel_id, departamento_id)` busca los pedidos que cumplen todo esto (como mucho 20, los más recientes primero):
  - mismo hotel y departamento;
  - `pedido_num` vacío;
  - estado distinto de ENTREGADO, CANCELADO y DENEGADO POR DIRECCION GENERAL.
- Endpoint nuevo `GET /api/pedidos/abiertos-sin-numero`, que usa el formulario.
- `create_pedido()` devuelve 409 con `requiere_confirmacion`, `tipo: "posible_duplicado"` y la lista, salvo que llegue `confirmar_duplicado`. `api()` del frontend ya trata ese 409 como respuesta normal, así que no hace falta tocar nada más para que pase.
- `api_externo_ao_crear_pedido()`, con la misma comprobación y dos salidas:
  - `confirmar_duplicado` crea el pedido igualmente;
  - `vincular_a=<id de la lista>` enlaza ese pedido: pone `ref_activo_operacional`, adjunta el PDF como `solicitud_doc` y lo apunta en el historial. No crea otro pedido. Se niega si ese pedido ya está vinculado a otro del Activo Operacional.

**Frontend:**
- Aviso `#p-aviso-duplicados` en el modal al cambiar hotel o departamento, solo en altas.
- `_preguntarPosibleDuplicado()`, la pregunta en un modal propio, en `savePedido()` y `_spCrear()`. Si la respuesta es «es otro», se repite la petición con `confirmar_duplicado`.

**Verificación:**
- Cliente de pruebas de Flask:
  - el 1.º pedido GY·COCINA no pregunta;
  - el aviso lo encuentra;
  - el 2.º igual → 409;
  - confirmado → se crea;
  - otro departamento → no pregunta;
  - si los abiertos ya tienen Nº → no pregunta.
- Desde Activo Operacional:
  - 409;
  - vincular (referencia + PDF);
  - no se puede vincular a uno ya vinculado;
  - «es otro» → se crea.
- Navegador con la app levantada:
  - el aviso aparece al elegir GY + COCINA;
  - Guardar → la pregunta;
  - «Cancelar y revisarlo» no crea nada;
  - «Es otro pedido distinto» crea y abre el pedido;
  - con PISOS no hay aviso.

**Encontrado de paso** (sin tocar): en una base de datos vacía, `_auto_migrate()` hace `ALTER TABLE emails_sistema_pendientes` antes del `CREATE TABLE` de esa tabla y se detiene. No afecta a producción, donde la tabla ya existe; solo a una instalación nueva desde cero.

**Norma 5:** sin variables ni tablas nuevas. `GUIA_DESPLIEGUE.md`, `PENDIENTES.md` e `INSTRUCCIONES_RESTAURACION.md` no aplican.

## 2026-10-20 — [Control Pedidos] Pedidos iniciados desde Activo Operacional (v12.33.28)

**Petición de Víctor:** «una vez recibida la propuesta de pedido, el comprador/administrador deberá en caso de comenzar el proceso, añadir nuevo pedido a la aplicación control de pedidos, con la fecha de la solicitud y acceso al PDF del pedido en el apartado de solicitud, debería existir un botón que antes incluso de solicitar los presupuestos indique el comienzo y creación del pedido, se cumplimentan los campos hotel, departamento, fecha solicitud y se agrega el acceso al pdf del pedido en este punto, todo esto automáticamente».

**Cambio:** endpoint nuevo `POST /api/externo/activo-operacional/pedidos` (`api_externo_ao_crear_pedido`). Usa la firma HMAC de `_dali_bridge_firma_valida` sobre el cuerpo crudo.

Recibe:
- `ref` (AO-<nº>) y el nº del pedido;
- el código del hotel y el nombre del departamento;
- `fecha_solicitud` (la del envío del hotel);
- observaciones;
- el PDF en base64;
- el email y el nombre de quien lo inicia.

Hace lo mismo que `create_pedido()`:
- `_next_norden`, el estado inicial por defecto e `historial_estados` con la nota «Pedido creado desde Activo Operacional (pedido X)»;
- `enviar_emails_estado()`, es decir, los mismos correos internos que al crear un pedido;
- el PDF va a `pedido_adjuntos` con tipo `solicitud_doc`: el apartado de Fecha solicitud, «Solicitud del hotel»;
- «Creado por» es el usuario con ese email o email2; si no hay ninguno, solo el nombre.

Validaciones:
- el hotel tiene que existir y estar activo;
- el departamento se busca por nombre normalizado (`_normalizar_texto_generico`), así que «Temáticos» = TEMATICOS y «Restaurante & Bares» = RESTAURANTE & BARES; si no existe, devuelve 422 con instrucciones (crearlo en Administración → Departamentos);
- el PDF tiene que empezar por %PDF y no pasar de `MAX_BYTES_DOCUMENTO`.

**Idempotencia:** columna `pedidos.ref_activo_operacional` con índice único parcial (`_auto_migrate` y models.py). Repetir la llamada, aunque sea a la vez (UniqueViolation), devuelve el pedido existente con `ya_existia: true`.

**Verificación** con el cliente de pruebas de Flask y con la app levantada (Activo Operacional → este Flask, de punta a punta):
- firma mala → 401;
- se crea el pedido con GY · COCINA · fecha de solicitud · estado inicial;
- «Creado por» sale del usuario con ese email;
- el PDF real del pedido (21 KB) queda en solicitud_doc;
- el historial lo registra;
- repetir la llamada no duplica;
- TEMÁTICOS inexistente → 422 legible;
- «Restaurante & Bares» casa con su departamento;
- un PDF no válido → 400.

**Norma 5:**
- `GUIA_DESPLIEGUE.md`: sin variables nuevas (usa `DALI_SSO_SECRET`);
- `INSTRUCCIONES_RESTAURACION.md`: la columna nueva se crea sola al arrancar;
- `PENDIENTES.md`: no aplica.

## 2026-10-19 — [Control Pedidos] Contactos de proveedor por hotel para Activo Operacional (v12.33.27)

Pregunta de Víctor: «en control pedidos, ya se indican las cuentas de correo de cada proveedor por hotel, ¿se utiliza esto?». No: `GET /api/externo/dali-sap/proveedores` quitaba de cada contacto sus hoteles (`proveedor_contacto_hoteles`).

Cambio: cada contacto del endpoint lleva `hoteles` (códigos de hotel, todos los hoteles incluido el de pruebas; lista vacía = contacto general). Activo Operacional v1.7.1 elige con eso los destinatarios de las solicitudes de presupuesto con la misma regla que `_get_proveedor_emails_principales()`: los principales de ese hotel; si no hay ninguno, los principales sin hotel asignado. Campo nuevo y opcional: Catálogo Asignaciones no lo lee y sigue igual.

Verificación: probado con el cliente de pruebas de Flask contra la base de datos local: un proveedor con un contacto principal de GY, uno principal general y uno no principal devuelve `hoteles` = `['GY']`, `[]` y `[]`. Firma igual que antes.

Norma 5: `GUIA_DESPLIEGUE.md`, `PENDIENTES.md`, `INSTRUCCIONES_RESTAURACION.md`: no aplica (sin variables ni tablas nuevas); `docs/hallazgo-seguridad-princess.md`: no existe en este repo.

## 2026-10-18 — [Control Pedidos] Compradores por hotel para Activo Operacional (v12.33.26)

Petición de Víctor: «en mi aplicación control pedidos, los compradores tienen los hoteles seleccionados, ¿podríamos utilizar esta configuración? la idea es que si se cambia en control pedido la asignación de los compradores, también se cambie en [Activo Operacional], los correos se envían a los compradores asignados, pero la visualización de pedidos, al igual que pasa en catálogo de asignaciones, puede ser visualizada por todos los compradores y administradores».

Cambio: endpoint nuevo `GET /api/externo/dali-sap/compradores-hoteles` (servidor a servidor, misma firma HMAC con `DALI_SSO_SECRET` que el resto del puente con DALI). Devuelve cada hotel activo con su(s) comprador(es) de `usuario_comprador_hoteles` (rol compras o admin, activos, con email): nombre, email, email2 y móvil. Mismo criterio que `_get_todos_usuarios_hotel()`. Activo Operacional lo consulta en vivo al pasar cada pedido para avisar por correo al comprador del hotel, así que cambiar la asignación aquí se aplica al pedido siguiente. No cambia nada de lo existente.

Verificación: probado con el cliente de pruebas de Flask contra una base de datos local creada con `init_db.py`: sin firma → 401, firma mala → 401, firma buena → hoteles con su comprador (incluido un admin con hotel asignado y el email2), un comprador inactivo no sale, hoteles sin comprador con lista vacía.

Norma 5: `GUIA_DESPLIEGUE.md` actualizado (la fila de `DALI_SSO_SECRET` menciona Activo Operacional); `PENDIENTES.md`, `INSTRUCCIONES_RESTAURACION.md`: no aplica; `docs/hallazgo-seguridad-princess.md`: no existe en este repo.

---

## 2026-10-13 — [Control Pedidos] Manual de usuario del rol COMPRADOR (v12.33.25)

Petición de Víctor: manual del rol comprador igual que los del rol hotel (alcance completo, PDF + Word). Solo documentación: `docs/Manual_Usuario_COMPRADOR_Control_Pedidos.pdf` y `.docx` (15 capítulos con capturas numeradas hechas sobre datos de demostración, no reales). Contenido contrastado con el código: un comprador ve los pedidos de todos los hoteles (los hoteles asignados determinan a quién llegan los avisos); aprobar/denegar un expediente de techo está abierto al comprador y al aprobar el pedido se envía solo al proveedor; la nota solo es obligatoria al reabrir un CANCELADO o al denegar; ENTREGADO no queda en solo lectura para Compras. Cambio de código: solo la insignia `V 12.33.25` en `templates/index.html`.

---

## 2026-10-13 — [Control Pedidos] Administrador con hoteles asignados (v12.33.24)

Petición de Víctor: que un admin pueda tener hoteles asignados, sin obligación. Decisión (confirmada con él): el admin con hoteles actúa como comprador de ellos. `app.py`: las consultas que resuelven el comprador de un hotel (`_get_compradores_hotel`, `_get_todos_usuarios_hotel`, `/api/compradores-por-hotel`, comprobaciones de Integridad «hotel sin comprador» y duplicados, protecciones de huérfanos al reasignar/desactivar/eliminar) pasan de `rol='compras'` a `rol IN ('compras','admin')` — seguro porque un admin solo aparece en `usuario_comprador_hoteles` si se le han asignado hoteles; `_validar_cambio_activo` y `delete_usuario` aplican la protección también a admins; `/api/admin/config-avisos` devuelve `es_comprador`. `templates/index.html`: bloque de hoteles de compras visible para admin (opcional, con nota), guardado y columna Hoteles de la tabla, y pestaña «Compradores y Hoteles» de Config. Avisos con los admins que tengan hoteles. Sin hoteles asignados, el comportamiento del admin no cambia (sigue viendo todo; no se cuenta como «comprador sin hoteles»). Probado con Postgres real, API y Playwright. Documentos de norma 5 revisados: no aplica.


---

## 2026-10-13 — [Control Pedidos] Usuarios: trazabilidad de conexiones y activar/desactivar (v12.33.23)

Petición de Víctor: saber cuándo se conectó cada usuario por última vez y desde dónde, y que el admin pueda siempre activar/desactivar un usuario (ya existía algo equivalente en DALI: `conexiones_usuarios`, `TrazabilidadUsuarioModal`). Cambios: tabla `usuarios_trazabilidad` (en `_auto_migrate` y `models.py`) alimentada desde `_completar_login` (métodos `login`, `login_verificado`, `bridge`) con IP (`X-Forwarded-For`), país (`CF-IPCountry`) y dispositivo derivado del User-Agent; endpoint `GET /api/usuarios/<id>/trazabilidad`; `GET /api/usuarios` devuelve `ultimo_login` y último IP/dispositivo; `PUT /api/usuarios/<id>/activo` y la validación común `_validar_cambio_activo` (se elimina el bloqueo duro por hoteles huérfanos, que pasa a aviso con `forzar`; no autodesactivarse; debe quedar un admin activo); eventos «activado/desactivado» con el admin autor. `login_required`, `admin_required` y `/api/me` cortan la sesión de una cuenta desactivada (cache de 20 s, 1 worker); mensaje específico al intentar entrar con contraseña correcta. Interfaz: columna «Último acceso», botones 🔍 y Desactivar/Activar, modal de trazabilidad. Probado con Postgres real, API y Playwright. Documentos revisados (`GUIA_DESPLIEGUE.md`, `PENDIENTES.md`, `INSTRUCCIONES_RESTAURACION.md`, `docs/hallazgo-seguridad-princess.md`): no aplica, salvo que la tabla nueva se crea sola en el arranque.


---

## 2026-10-12 — [Control Pedidos] Pedido simplificado, Fase 3 y trazabilidad fuera de los correos al proveedor (v12.33.22)

Problema reportado por Víctor (captura de un correo de reclamación, pedido 16080 de La Palma Princess): en los pedidos creados automáticamente desde SAP, el campo Observaciones lleva una línea de trazabilidad interna («Alta automática · Carga automática SAP · fecha · Nº SAP … · Datos y artículos tomados de los listados de SAP…») y las plantillas de correo la mostraban al proveedor. Corrección en `app.py`: `_obs_para_proveedor` elimina las líneas que empiezan por «Alta automática ·» y `_pedido_para_proveedor` entrega una copia depurada; se aplica en `_email_template_enviado_proveedor`, `_email_template_entrega_parcial`, `_email_template_pendiente_cotizacion` y en el «motivo» de cancelación de `enviar_emails_estado`. Las observaciones escritas a mano se conservan; los correos internos (comprador/directores) mantienen la trazabilidad.

Fase 3 del pedido simplificado: `_extraer_datos_presupuesto_archivo` lee PDF, .docx (zip/XML, sin dependencias nuevas), .xlsx (openpyxl, ya en requirements) y .eml (asunto, cuerpo y adjuntos; fecha de cabecera como respaldo con confianza baja). `_pres_proveedor_sugerido` busca en el texto el nombre de un proveedor del catálogo (el más largo, solo si es único) o el dominio del remitente entre los correos de contacto. `simplificado_analizar` clasifica correos con presupuesto adjunto y Word/Excel por contenido. Nueva tabla `presupuesto_lecturas` (creada en `_auto_migrate` y en models.py) y endpoints `POST /api/pedidos/simplificado/lectura` y `GET /api/presupuestos/lecturas` (admin). `templates/index.html`: origen del documento, proveedor propuesto, aviso de proveedor distinto, registro de la lectura al crear y aviso de proveedor probable en el paso a paso.

Pruebas: Word, Excel, .eml con PDF adjunto y .eml con presupuesto en el cuerpo correctos; plantillas de correo comprobadas con una observación automática (no aparece) y con una manual añadida (se conserva).

---

## 2026-10-12 — [Control Pedidos] Pedido simplificado, Fase 2: lectura de presupuestos y fecha del presupuesto (v12.33.21)

Víctor envió 13 presupuestos reales (Casa Delfín, Pilsa, Mabecan, Ditenerife, Crisol, Dihova, Servicios Electrónicos, Lormacan, Vamac Sport —uno con texto y otro escaneado y girado—, TM Leader, Reverón y Aliseo —escaneado y firmado—). Formatos muy dispares: números sin etiqueta (justo antes de la fecha, o pegados a «Nº PROFORMA»), importes «1.234,56» y «1,234.56», cifras de totales pegadas («0,9713,89») y un proveedor con IVA mixto y sin base impresa.

Corrección/implementación (`app.py`): `_extraer_datos_presupuesto` (+ `_pres_*`): Nº por etiquetas habituales con respaldo «código antes de la fecha»; fecha tras «Fecha» ignorando validez/vencimiento/entrega; importe sin IGIC por **triple coherente base + impuesto = total** del propio documento (descartado si no cuadra con la cifra etiquetada como base) y, si no, por etiquetas (Base imponible, Importe neto, Subtotal…). Escaneados: OCR con Tesseract a 150 ppp con corrección de orientación (OSD), una sola pasada. Resultado: 13/13 correctos. Columna nueva `pedidos.fecha_presupuesto` (TEXT 'YYYY-MM-DD', como el resto de fechas; la primera prueba con DATE reproducía el problema de JSON de `_normalizar_fecha_entrega_especifica`). `create_pedido`/`update_pedido` la guardan; `upload_adjunto` (presupuesto_doc PDF) devuelve la propuesta sin escribirla; `simplificado_analizar` reutiliza una única lectura OCR para clasificar y leer.

`templates/index.html`: campo «Fecha del presupuesto» (ficha), autorrelleno de campos vacíos al adjuntar el presupuesto, y en el asistente simplificado bloque Presupuesto (Nº, fecha, importe editables, marca «compruebe»), techo de gasto con importe del presupuesto y aviso si no coincide con el total del PDF del pedido.

Limitaciones conocidas: presupuestos en Word/Excel/correo no se leen aún (Fase 3); el OCR puede equivocar una cifra (se avisa «compruebe»); la fecha del presupuesto aún no se incluye en exportaciones ni correos.

---

## 2026-10-12 — [Control Pedidos] Pedido simplificado, Fase 1: alta de pedido subiendo todos los archivos de una vez (v12.33.20)

Petición de Víctor: simplificar la creación manual de pedidos para no subir los archivos paso a paso. «Nuevo pedido» (solo comprador/admin) ofrece **Simplificado** o **Paso a paso** (sin cambios). Acordado con Víctor: fechas de solicitud y Vº Bº al inicio; todos los archivos de una vez; análisis sin escribir en BD; tabla editable de destino con «¿Dónde lo coloco?» solo para lo dudoso; con PDF oficial se dan por buenos hotel, departamento, proveedor y fecha de tramitación (= Fecha Pedido) y se pregunta la fecha de entrega, y el estado se elige en la ventana «Pedido cargado correctamente»; sin PDF se pregunta hotel → departamento y se propone estado según la documentación (cotización / firma de Dirección / Vº Bº DG si supera techo). Defaults de Fase 1: presupuesto sin Vº Bº → se pide fecha y documento de envío en la propia pantalla; techo con importe tecleado a mano.

Implementación: `app.py` — `simplificado_analizar` (clasifica PDF oficial reutilizando `_parsear_pdf_pedido_oficial`, presupuestos por palabras clave, correos por asunto, imágenes; máx. 12 archivos; OCR limitado a 2 PDF escaneados por análisis; detecta el pedido existente con `_detectar_pedido_num_duplicado`) y `simplificado_techo` (`_check_techo`, solo consulta). El alta es `POST /api/pedidos` + subida de cada archivo con su tipo por `/api/pedidos/<id>/adjuntos` (mismas validaciones del paso a paso); con PDF oficial el pedido nace en PENDIENTE COTIZACIÓN y se abre la ficha con la ventana de estado. `templates/index.html` — `nuevoPedido()`, asistente `_sp*`, estilos `.sp-*`. Sin migraciones.

Fase 2 (necesita presupuestos de ejemplo de los proveedores más frecuentes): nº de presupuesto y nueva fecha de presupuesto (columna + migración), importe → techo, comparación con el total del pedido. Fase 3: aprendizaje del formato por proveedor, fechas desde correos.

---

## 2026-10-11 — [Control Pedidos] Rol Hotel: se oculta el texto de «adjuntar PDF del pedido oficial» (v12.33.19)

Detectado al actualizar el manual del rol Hotel: el hotel no puede adjuntar el PDF del pedido pero veía sus instrucciones y el enlace «Ver ejemplo» (v12.33.18). Se oculta `#nota-pedido-doc` en la rama de rol Hotel, junto al botón. Comprobado con Playwright como usuario Hotel (el texto ya no aparece; el PDF adjunto sigue visible para consulta). Sin migraciones. Documentos de mantenimiento: no aplica. Manual del rol Hotel actualizado a esta versión.

---

## 2026-10-11 — [Control Pedidos] Imagen de ejemplo del PDF de albarán y de pedido antes de subirlo (v12.33.18)

Petición de Víctor: que cualquier usuario vea cuál es el documento exacto que se espera al subir un albarán (DALI «Compras» → Imprimir → PDF) o el PDF oficial del pedido. Se añaden dos imágenes de ejemplo (`static/ejemplos/`, generadas a partir de PDF reales con usuario y datos de contacto del proveedor tapados y los datos clave numerados) y la ventana `abrirAyudaPdf()` que se muestra antes del selector de archivo, con «No volver a mostrar» (localStorage, en try/catch) y enlaces «Ver ejemplo». Probado con Playwright: ventana del albarán y del pedido (imagen cargada, abre el selector con «Elegir el PDF…», sin ayuda tras marcar «No volver a mostrar», enlace «Ver ejemplo» solo informativo) y la subida del albarán sigue funcionando. Sin migraciones. Documentos de mantenimiento: no aplica. Pendiente opcional: añadir la imagen al manual del rol Hotel / comprador.

---

## 2026-10-11 — [Control Pedidos] Albaranes PDF: cantidades partidas en la celda leídas como 0 (v12.33.17)

Problema reportado por Víctor (pedido 00042523, albarán 81988): llegaban 1.008 copas y no se registraba ninguna, seguía figurando que faltaban 1.002; había que registrar las 1.008 e indicar el sobrante. Causa: la cantidad salía en dos líneas dentro de la celda del PDF («1.008,» / «0000»), no se convertía en número, valía 0 y la línea se ignoraba. Corrección: se quitan espacios/saltos de línea de cantidad, precio e importe al leer el albarán, y una cantidad ilegible rechaza el albarán con mensaje en lugar de ignorarse. Probado con el PDF real 81988 y Postgres real + Playwright (1.008 registradas, +6 de sobrante, 10 saleros pendientes, ENTREGA PARCIAL, guardado con detalle en BD); regresión de las pruebas anteriores sin cambios. Sin migraciones. Documentos de mantenimiento: no aplica.

---

## 2026-10-11 — [Control Pedidos] Completar las referencias de un albarán ya registrado sin ellas (v12.33.16)

Problema reportado por Víctor: el albarán 86886 del pedido 00015173 ya estaba guardado sin referencias y al volver a subir el PDF solo decía «ya registrado», sin dejar recargarlo. Corrección: `_entrada_sin_referencias()`; si la entrada está en este pedido pero sin detalle de referencias, el botón del pedido y la carga en lote la completan (sin duplicar la entrada y recalculando el estado); si ya tiene referencias o está en otro pedido, se mantiene el aviso de ya registrado / conflicto. Probado con Postgres real (botón y lote simulado/aplicado, segunda subida → ya registrado) y con Playwright (una sola fila, «1 ref. ✔», guardado con detalle en BD). Sin migraciones. Documentos de mantenimiento: no aplica.

---

## 2026-10-11 — [Control Pedidos] Albaranes PDF: referencias emparejadas por descripción cuando el código no coincide (v12.33.15)

Problema reportado por Víctor (pedido 00015173, albarán 86886): al subir el PDF se rellenaba la entrada pero las referencias no se registraban. Causa: el albarán trae el código interno de DALI (00010049) y el pedido lleva como código la referencia del proveedor (1900658); solo se comparaba el código. Corrección: `_emparejar_linea_albaran()` (código/ref. proveedor → misma descripción normalizada → descripción ≥ 90 % parecida con mismo precio ±0,01), usado en el botón del pedido, en la carga en lote y en la localización del pedido sin «Pedido/s»; las líneas emparejadas por descripción se avisan. Probado con el PDF real 86886 y Postgres real (descripción igual con otro caso/acentos, parecida con mismo precio, parecida con precio distinto → no empareja, sin coincidencia, lote simulado/aplicado, lote sin «Pedido/s» por proveedor) y con Playwright (botón «1 ref. ✔», ENTREGA PARCIAL, guardado y detalle en BD); regresión de las pruebas de v12.33.12–.14 sin cambios. Sin migraciones. Documentos de mantenimiento: no aplica.

---

## 2026-10-11 — [Control Pedidos] Carga de albaranes PDF en lote y ciclo completo desde el pedido (v12.33.14)

Petición de Víctor: desde «Confirmar albaranes sueltos» (admin) cargar varios albaranes a la vez, completando todo el ciclo (pedido, entrada, referencias, estado, historial, avisos, cruce con SAP); desde el pedido lo mismo para compras/hotel (admin en todos); un albarán ya registrado no se duplica y, si está en un pedido erróneo, se avisa para que el usuario decida. Nuevo `POST /api/albaranes/cargar-lote` (simula o aplica), `POST /api/pedidos/<id>/registrar-albaran-sap`, detección de albarán ya registrado (`_pedidos_con_albaran`) en el lote y en el botón del pedido, y nueva ventana de revisión/aplicación. Probado con el PDF real del albarán 87343 y Postgres real: simulación sin escribir, aplicación, re-subida (ya registrado), pedido completo (ENTREGADO), hotel equivocado, albarán en pedido erróneo, sin «Pedido/s» (único/ambiguo/conflicto), dos albaranes del mismo pedido en una carga y ficheros no PDF; y con Playwright (ventana de lote, botón del pedido, guardado y confirmación en el cruce con SAP). Sin migraciones. Documentos de mantenimiento: no aplica.

---

## 2026-10-11 — [Control Pedidos] Hoteles duplicados en el filtro de Pedidos (v12.33.13)

Hallazgo de Víctor: cada hotel salía dos veces en el desplegable de filtro de Pedidos. `loadMaestros()` añadía opciones a `f-hotel`/`f-estado`/`f-depto` sin vaciarlos, y se ejecuta de nuevo al volver a entrar sin recargar la página. Ahora se vacían antes de rellenarlos. Probado con Playwright (3 cargas seguidas, mismo número de opciones). Solo frontend; sin migraciones. Documentos de mantenimiento: no aplica.

---

## 2026-10-11 — [Control Pedidos] Subir el PDF de un albarán y rellenar la entrada solo (v12.33.12)

Petición de Víctor: botón para subir el PDF del albarán que la aplicación interprete y rellene Nº de entrada, fecha, base imponible y referencias; que verifique que corresponde al pedido (por «Pedido/s» o, si no lo trae, por las referencias) y marque ENTREGADO si completa el pedido o ENTREGA PARCIAL si no, manteniendo el modo manual. Nuevo endpoint de solo lectura `POST /api/pedidos/<id>/leer-albaran-pdf` (reutiliza el lector de «Confirmar un albarán suelto») y botón «📎 Subir albarán PDF» en la ficha: aplica el resultado sobre el formulario con el mismo tratamiento que una entrada manual (detalle de referencias, «Entrada final», avisos de faltantes/sobrantes y de diferencia de importe); no guarda hasta «Guardar». Probado con el PDF real del albarán 87343 y con Postgres real (pedido coincidente, pedido distinto, sin pedido en el PDF con y sin referencias incluidas, pedido completo y parcial). Documentos revisados (`GUIA_DESPLIEGUE.md`, `PENDIENTES.md`, `INSTRUCCIONES_RESTAURACION.md`): no aplica; sin migraciones.

---

## 2026-10-10 — [Control Pedidos] Los pedidos eliminados no se recrean con las altas automáticas (v12.33.11)

Petición de Víctor: la carga automática de listados SAP volvía a dar de alta pedidos que ya se habían eliminado (ej. 00041455). Ahora `pedidos_eliminados` guarda también `hotel_id` (rellenado en los registros antiguos), el detector `_pedidos_sap_no_registrados()` excluye los eliminados del hotel, `_crear_pedidos_sap_lote()` los omite con el motivo y la carga unificada avisa de cuáles se han saltado. Alta manual e importación Excel sin cambios. Archivos: `app.py`, `templates/index.html` (solo insignia), `CHANGELOG.md`, este historial, `README.md`. Revisado: `GUIA_DESPLIEGUE.md`, `PENDIENTES.md`, `INSTRUCCIONES_RESTAURACION.md`, `docs/hallazgo-seguridad-princess.md` — no aplica.

---

## 2026-10-10 — [Control Pedidos] Ordenar «Referencias de la entrada» por columnas (v12.33.10)

Petición de Víctor: al pulsar el título de una columna de la ventana de referencias de una entrada se ordena (texto A→Z / Z→A, números mayor→menor / menor→mayor, ☑ marcadas primero). Solo reordena las filas en pantalla, sin tocar cantidades ni lo guardado; vacíos («—») siempre al final y orden original a igualdad. Archivos: `templates/index.html`, `CHANGELOG.md`, este historial, `README.md`. Revisado: `GUIA_DESPLIEGUE.md`, `PENDIENTES.md`, `INSTRUCCIONES_RESTAURACION.md`, `docs/hallazgo-seguridad-princess.md` — no aplica.

---

## 2026-10-10 — [Control Pedidos] Silencio total de avisos durante la actualización de la base de datos (v12.33.09)

Petición de Víctor: la pausa del job diario no frenaba los avisos de cambio de estado (correo/Telegram/popup), que salían al instante durante las cargas masivas. Nueva casilla «SILENCIO TOTAL» (`silencio_total_avisos`, Parámetros de Alertas) que corta todos los canales en sus puntos únicos de salida y en el despacho de la cola, detiene los jobs de alertas, descarta al activarla lo ya encolado y muestra un aviso rojo fijo a los administradores. Excepciones: solicitudes de acceso, resúmenes enviados a mano, códigos/restablecimiento de contraseña y alertas del propio sistema (consumo, salud). Archivos: `app.py`, `templates/index.html`, `CHANGELOG.md`, este historial, `README.md`. Revisado: `GUIA_DESPLIEGUE.md`, `PENDIENTES.md`, `INSTRUCCIONES_RESTAURACION.md`, `docs/hallazgo-seguridad-princess.md` — no aplica.

---

## 2026-10-10 — [Control Pedidos] Departamento distinto al del PDF oficial: se pregunta cuál dejar (v12.33.08)

Pregunta «PDF o indicado a mano» al subir el PDF y al enviar al proveedor; columna `departamento_pdf_aceptado_id` y endpoint `/api/pedidos/<id>/departamento-pdf`; la validación del backend respeta la decisión. Detalle y pruebas en `CHANGELOG.md` (v12.33.08). Documentos revisados: `GUIA_DESPLIEGUE.md`, `PENDIENTES.md`, `INSTRUCCIONES_RESTAURACION.md` — no aplica (la columna se crea sola al arrancar).

---

## 2026-10-09 — [Control Pedidos] Candado anti-duplicados de Nº de pedido en la base de datos (v12.33.07)

Índice único (hotel, Nº de pedido normalizado) creado al arrancar si no hay duplicados; comprobación previa en la creación automática y en la importación Excel; manejador global 409. Detalle y pruebas en `CHANGELOG.md` (v12.33.07). Documentos revisados: `GUIA_DESPLIEGUE.md`, `PENDIENTES.md`, `INSTRUCCIONES_RESTAURACION.md` — no aplica (no cambia despliegue ni restauración; el índice se crea solo).

---

## 2026-10-09 — [Control Pedidos] Departamento de los pedidos automáticos desde SAP (v12.33.06)

- **Corrección**: `_completar_departamentos_sap_hotel` asigna el departamento (código del listado o de las líneas del detallado) a los pedidos automáticos que lo tengan vacío; se llama en alta, carga, regularización y apertura; avisos de lo que quede sin departamento.

---

## 2026-10-09 — [Control Pedidos] Corrección datetime/float en tareas de carga SAP (v12.33.05)

- **Corrección**: `regularizar_sap` guardaba `creado_en` como `datetime`; ahora `time.time()` y purga de tareas antiguas, como el resto de cargas.

---

## 2026-10-09 — [Control Pedidos] Regularizar con lo ya guardado en la base de datos, sin PDF (v12.33.04)

- **Novedad**: `POST /api/sap/regularizar` + botón en «Cargar listados SAP»; `_cargar_listados_sap_logica` admite `archivos=[]`; `_cruce_lineas_sap_hotel(solo_detalle=True)` y `_aplicar_cruce_lineas_pedido(solo_detalle=True)` completan el detalle de entradas de pedidos ya registrados; relleno de líneas al abrir un pedido antiguo.

---

## 2026-10-09 — [Control Pedidos] Líneas de SAP en los pedidos creados solos; PDF oficial opcional (v12.33.03)

- **Novedad**: `_volcar_lineas_sap_hotel` copia a `pedido_lineas` (origen='sap') las líneas del listado detallado en pedidos sin PDF; panel de líneas y nota «PDF opcional» en la ficha; `_validar_pedido_envio_proveedor` y `savePedido` no exigen el PDF a pedidos creados por «Carga automática SAP».

---

## 2026-10-09 — [Control Pedidos] Avisos de error del formulario de pedidos: persistentes y con detalle (v12.33.02)

- **Novedad**: `showFormAlert` se mantiene hasta pulsar una tecla / clic (salvo ✅ éxito o `persistente:false`); `_detalleGuardadoPedido` añade operación, hotel, estado, proveedor, importe, hora y error técnico al fallar `savePedido`. Solo front.

---

## 2026-10-09 — [Control Pedidos] Alertas: tiempo contado desde la fecha de entrega cuando existe (v12.33.01)

- **Corrección**: `_clasificar_alertas` expone `por_plazo` / `dias_exceso` y ordena por retraso sobre la fecha de entrega; la UI (Alertas, impresión, Dashboard) muestra «N días de retraso», «Vence hoy» o «Faltan N días» (`_alertaTiempo`) en vez de los días desde tramitación. La lógica de cuándo avisar no cambia.

---

## 2026-10-09 — [Control Pedidos] Trazabilidad de lo automático al estilo SAP (v12.33.00)

- **Novedad**: autor único «Carga automática SAP» (`_AUTOR_SAP_AUTO`) para altas y cambios de la carga de listados, con renombrado de los autores antiguos al arrancar; observación de alta automática en formato de trazabilidad (`_obs_alta_automatica_sap`, con migración de las antiguas); bloque «Trazabilidad» en Editar pedido (`_renderTrazabilidadPedido`) con autor y fecha de creación y de última modificación en formato SAP.

---

## 2026-10-09 — [Control Pedidos] Corrección «tuple index out of range» en Cargar listados SAP + errores concretos y persistentes (v12.32.99)

- **Corrección**: `%` sin escapar (`c % 2`) en la consulta de albaranes duplicados de `_cargar_listados_sap_logica` → `%%`; la comprobación pasa a ser opcional (no detiene la carga).
- **Novedad**: error de la carga con paso, tipo y función/línea (`_csl_paso`); caja roja en el modal y `toast(…, 0)` persistente hasta pulsar una tecla.

---

## 2026-10-09 — [Control Pedidos] Contador de tiempo en «Cargar listados SAP» (v12.32.98)

- **Novedad**: contador `mm:ss` junto al spinner de la carga (`_cslTimerStart`/`_cslTimerStop`, basado en `Date.now()`). Solo front (`templates/index.html`).

---

## 2026-10-09 — [Control Pedidos] Carga única de listados SAP con cruce por líneas (v12.32.97)

- **Petición**: simplificar la carga de listados (Comparar, Departamentos y líneas, Importar albaranes, Sugerencias) y que al cargar se actualicen solos estado, nº de albarán, fecha y base imponible, y se creen los pedidos de proveedores «Sujeto a seguimiento».
- **Corrección/novedad**: botón «Cargar listados SAP» (`/api/sap/cargar-listados`), detección del tipo de PDF por contenido, lector del listado de albaranes resumido (`sap_albaranes_cab`), cruce por líneas `_cruce_lineas_sap_hotel` y aplicación segura `_aplicar_cruce_lineas_pedido`; resto en «Para revisar» (ver CHANGELOG v12.32.97).

## 2026-10-09 — [Control Pedidos] Material recibido en exceso en correos y listados de pendientes (v12.32.96)

- **Origen**: Víctor: cuando llega más cantidad de la pedida (pedido 16134, +10/+5) debe constar en la reclamación al proveedor, en los correos internos y en los listados de faltantes, como sobrante / material entregado en exceso.
- **Hallazgo**: el cálculo solo contemplaba lo pendiente; las líneas con recibido > pedido se ignoraban.
- **Corrección**: `sobrantes` en `_datos_pendientes` y `_calcular_faltantes_pedido`; bloque «Material recibido en exceso» en correo a proveedor, internos (parcial y entregado) y en el listado/PDF de pendientes, con filtro `solo_exceso` (ver CHANGELOG v12.32.96).
- **Ficheros editados en este repo**: `app.py`, `templates/index.html`, `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables ni SQL de migración; resto: no aplica.
- **Pendiente / ideas**: opción de registrar la decisión sobre el exceso (devolución / abono / quedárselo) y exportar a Excel.

---

## 2026-10-09 — [Control Pedidos] Líneas con el mismo código en un pedido: cada una por separado (v12.32.95)

- **Origen**: Víctor: en el listado de pendientes, el pedido 28289 mostraba una sola referencia («DUNI», 6 uds.) en vez de las tres líneas del PDF; las referencias sin precio no salían como faltantes.
- **Hallazgo**: el proveedor usa el mismo código en todas sus líneas y la app agrupaba por código (4+1+1 = 6).
- **Corrección**: `_claves_lineas()` (código, o `CODIGO#n` si se repite en el pedido) aplicada a pendientes, entregas por referencia, líneas del pedido, buscador y correos de reclamación (ver CHANGELOG v12.32.95).
- **Ficheros editados en este repo**: `app.py`, `templates/index.html`, `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables ni SQL de migración; resto: no aplica.
- **Pendiente / ideas**: revisar si algún pedido existente con códigos repetidos tenía detalle de entregas guardado (se asigna a la primera línea del código).

---

## 2026-10-09 — [Control Pedidos] Buscar artículo: pedidos con entregas pendientes, listado y detallado en PDF (v12.32.94)

- **Origen**: Víctor: listar en pantalla y PDF los pedidos enviados al proveedor con entregas pendientes (totales o parciales) y poder imprimir el detalle de los faltantes de cada uno.
- **Hallazgo**: las referencias pendientes ya se calculaban para los correos de reclamación (`_datos_pendientes`), pero solo pedido a pedido y sin vista de conjunto.
- **Corrección**: endpoint `/api/pedidos/pendientes-entrega` con cálculo en bloque + modo nuevo en «Buscar artículo» con tabla desplegable e impresión (listado / detallado) — ver CHANGELOG v12.32.94.
- **Ficheros editados en este repo**: `app.py`, `templates/index.html`, `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables ni SQL; resto: no aplica.
- **Pendiente / ideas**: exportar a Excel; enviar este informe por correo a compras; sustituir el cálculo por el del Listado de Pedidos detallado de SAP cuando se automatice la entrega (ver conversación del 09/10).

---

## 2026-10-09 — [Control Pedidos] Ficha del pedido: tabla de líneas a todo el ancho (v12.32.93)

- **Origen**: Víctor: aprovechar el espacio libre a la derecha en la ficha y ocuparlo con el contenido del pedido.
- **Hallazgo**: la tabla de líneas estaba dentro de la columna izquierda (media anchura) y la derecha quedaba vacía bajo «Total Pedido».
- **Corrección**: tabla en fila propia a todo el ancho; «Nº Pedido» a la izquierda a doble altura con «Nº Presupuesto» y «Total Pedido» apilados a la derecha; rol hotel con «Nº Pedido» a fila completa (ver CHANGELOG v12.32.93).
- **Ficheros editados en este repo**: `templates/index.html`, `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables ni SQL; resto: no aplica.
- **Pendiente / ideas**: ensanchar el modal cuando el pedido tiene muchas líneas; comparar líneas del PDF con los listados SAP (ver conversación sobre automatización de entregas).

---

## 2026-10-08 — [Control Pedidos] Líneas del PDF oficial: cantidad y precio pegados (v12.32.92)

- **Origen**: Víctor: el PDF del pedido 16756 (Cube Root Cards) no leía las líneas (aviso de fiabilidad).
- **Hallazgo**: cantidad grande + precio corto salen sin hueco (`10.000,00000,26`) y el lector por posiciones no reconocía la palabra como número.
- **Corrección**: `_RE_NUM_ES_PEGADO` separa Cantidad y Precio antes de leer la fila; la comprobación de suma contra los importes del texto sigue siendo la garantía (ver CHANGELOG v12.32.92).
- **Ficheros editados en este repo**: `app.py`, `templates/index.html` (badge), `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables ni SQL; resto: no aplica.
- **Pendiente / ideas**: valorar guardar el precio exacto (Importe ÷ Cantidad) cuando el PDF lo imprime redondeado; reintento en bloque de PDF con 0 líneas.

---

## 2026-10-08 — [Control Pedidos] Alertas: pedidos con entrega vencida siempre visibles (v12.32.91)

- **Origen**: Víctor: el pedido 41152 (entrega prevista 25/09) no aparecía en Alertas; pidió que, vencido el plazo, la información quede siempre visible independientemente de que toque avisar.
- **Hallazgo**: la lista usaba `_alertas_plazo_entrega()`, que solo devuelve resultado los días de aviso (ciclo de 2 días tras el vencimiento); el resto de días el pedido vencido se ocultaba.
- **Corrección**: `_plazo_entrega_vencido()` + parámetro `solo_dias_de_aviso` en `_clasificar_alertas()`; pantalla, badge, dashboard y rol hotel muestran siempre los vencidos (urgente); el puente de popups y todos los avisos automáticos mantienen su ciclo (ver CHANGELOG v12.32.91).
- **Ficheros editados en este repo**: `app.py`, `templates/index.html` (badge), `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables ni SQL; resto: no aplica.
- **Pendiente / ideas**: mostrar en la fila el texto «vencido hace N días»; valorar el mismo criterio para el puente de popups si se prefiere.

---

## 2026-10-08 — [Control Pedidos] Techo de Gastos: apuntes pendientes de meses anteriores resolubles (v12.32.90)

- **Origen**: Víctor: el pedido 41699 (GY, ECUS SLEEP) se envió al proveedor el 28/09 sin cambiar el estado en la app; al intentarlo, el sistema exigía aceptar el techo de gastos, pero la pantalla solo mostraba octubre.
- **Hallazgo**: `techo_resumen` filtraba expedientes por el mes actual; `update_pedido` bloquea mientras haya un apunte `pendiente` de cualquier mes → apunte de septiembre invisible e irresoluble.
- **Corrección**: pendientes de cualquier mes visibles (con etiqueta de mes); al aprobar uno antiguo se puede marcar «ya enviado al proveedor» (no reenvía el correo al proveedor, imputa el consumo al mes del apunte y anota la regularización) (ver CHANGELOG v12.32.90).
- **Ficheros editados en este repo**: `app.py`, `templates/index.html`, `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables ni SQL; resto: no aplica.
- **Pendiente / ideas**: valorar un aviso automático a Dirección General cuando un apunte lleva más de N días pendiente.

---

## 2026-10-08 — [Control Pedidos] Líneas del PDF oficial: códigos alfanuméricos (v12.32.89)

- **Origen**: Víctor: el PDF del pedido 41862 (Redican) no leía las líneas (aviso de fiabilidad).
- **Hallazgo**: `_RE_CODIGO_LINEA` exigía números de 8 (luego 7) cifras; Redican usa códigos como `4487B` o `39-0000010B`.
- **Corrección**: la regla acepta palabras de 3-20 caracteres alfanuméricos con `- / . _`; filas sin terna de importes pasan a ser descripción; la comprobación de suma contra los importes sigue siendo la garantía (ver CHANGELOG v12.32.89).
- **Ficheros editados en este repo**: `app.py`, `templates/index.html` (badge), `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables ni SQL; resto: no aplica.
- **Pendiente / ideas**: los PDF que quedaron sin líneas por este motivo se recuperan pedido a pedido con «Reintentar la lectura»; valorar un reintento en bloque para todos los que tengan PDF oficial y 0 líneas.

---

## 2026-10-08 — [Control Pedidos] Reclamación manual al proveedor firmada por quien la realiza (v12.32.88)

- **Origen**: Víctor (pedido 40907, GY): la reclamación salía firmada como «Vacante»; debe firmar quien la realiza, sea admin o usuario de hotel, tenga o no el hotel asignado.
- **Hallazgo**: `_build_alerta_email` usaba siempre el primer comprador del hotel (firma y Reply-To); sin comprador con email la reclamación manual no se podía preparar.
- **Corrección**: `_firmante_usuario_sesion()` + parámetro `firmante` (vista previa manual); Reply-To del envío manual = firmante; automáticas sin cambios (ver CHANGELOG v12.32.88).
- **Ficheros editados en este repo**: `app.py`, `templates/index.html`, `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables ni SQL; resto: no aplica.
- **Pendiente / ideas**: revisar el puesto «Vacante» del hotel (a quién debe firmar la reclamación automática cuando el comprador asignado es un puesto vacante).

---

## 2026-10-08 — [Control Pedidos] Aviso interno de entrega parcial: enlace al pedido en la app y referencias pendientes (v12.32.87)

- **Origen**: Víctor: que el aviso interno a los departamentos por entrega parcial lleve el enlace al pedido y qué referencias y cantidades quedan pendientes.
- **Hallazgo**: el aviso ya tenía el botón de descarga del PDF y (v12.32.86) la tabla de pendientes solo con detalle completo y sin versión de texto; no existía ningún enlace que abriera un pedido en la app.
- **Corrección**: enlace `/?pedido=<id>` (captura en la página, apertura tras la sesión), tabla de pendientes también con detalle parcial y aviso (solo interno), y versión de texto; ver CHANGELOG v12.32.87.
- **Ficheros editados en este repo**: `app.py`, `templates/index.html`, `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables ni SQL; el enlace usa la variable `APP_URL` ya existente (debe apuntar a la URL real del servicio en Render).
- **Pendiente / ideas**: extender el enlace al resto de avisos internos; exportar a Excel los faltantes.

---

## 2026-10-08 — [Control Pedidos] Reclamación de entrega parcial con referencias y cantidades pendientes (v12.32.86)

- **Origen**: Víctor preguntó si la reclamación del pendiente al proveedor indica las referencias y cantidades que faltan (pedido con dos entradas parciales detalladas).
- **Hallazgo**: no; `_email_template_entrega_parcial` solo mostraba entradas e importes. El detalle por referencia (v12.32.82) ya estaba en `pedido_lineas_entregas`.
- **Corrección**: `_html_bloque_pendientes(pedido)` añade la tabla al correo de ENTREGA PARCIAL al proveedor (auto y manual) y al aviso interno; solo si todas las entradas tienen detalle (ver CHANGELOG v12.32.86).
- **Ficheros editados en este repo**: `app.py`, `templates/index.html` (badge), `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables ni SQL; resto: no aplica.
- **Pendiente / ideas**: exportar a Excel los faltantes; versión en texto plano de la tabla en el aviso interno.

---

## 2026-10-08 — [Control Pedidos] Ventana de referencias de la entrada: cantidad editable sin marcar la referencia (v12.32.85)

- **Origen**: Víctor: en la entrada parcial 101417 no podía cambiar 10 por 5 uds en la primera referencia.
- **Hallazgo**: el input de cantidad (`.mel-cant`) estaba `disabled` mientras la casilla no estuviera marcada (v12.32.82).
- **Corrección**: input siempre editable (salvo solo lectura); escribir una cantidad > 0 marca la referencia; desmarcar conserva el valor (ver CHANGELOG v12.32.85). Solo `templates/index.html`.
- **Ficheros editados en este repo**: `templates/index.html`, `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables ni SQL; resto: no aplica.
- **Pendiente / ideas**: ninguna nueva.

---

## 2026-10-08 — [Control Pedidos] Líneas del PDF oficial: códigos de artículo de 7 cifras (v12.32.84)

- **Origen**: Víctor adjuntó el PDF del pedido 41866 (Guayarmina, Dorta): Nº y Total bien, pero aviso de que las líneas no se podían leer con fiabilidad.
- **Hallazgo**: `_RE_CODIGO_LINEA` exigía 8 cifras exactas; el artículo `2060205` tiene 7 en el PDF, así que su línea se perdía y la comprobación cruzada con los importes (5 vs 4) descartaba todas.
- **Corrección**: la regla acepta 7 u 8 cifras (código guardado tal como se imprime). Reintentar la lectura en el pedido ya cargado. Ver CHANGELOG v12.32.84.
- **Ficheros editados en este repo**: `app.py`, `templates/index.html`, `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables ni SQL manual; resto: no aplica.
- **Pendiente / ideas**: la búsqueda de artículos distingue `2060205` de `02060205` si alguien escribe el código con un cero delante (valorar búsqueda tolerante a ceros iniciales).

---

## 2026-10-07 — [Control Pedidos] Revisión obligatoria del estado tras leer el PDF oficial y fecha + archivo en los estados de firma (v12.32.83)

- **Origen**: Víctor: al cargarse bien el PDF oficial, ventana que confirme la carga y obligue a revisar el estado antes de guardar (¿ENVIADO AL PROVEEDOR u otro?); si se marca pendiente de firma (Compras, Hotel o Dirección General), debe haber fecha y archivo en «enviado para firma», y lo mismo si el estado se cambia a mano.
- **Hallazgo**: la sección «enviado para firma» es «Fecha de envío para Vº Bº» (`fecha_envio_visto_bueno`) + adjuntos `vb_eml`; hasta ahora no era obligatoria para ningún estado. Nuevo problema detectado de paso: los ZIP de v12.32.81 y v12.32.82 llevaban `README.md` vacío (0 bytes).
- **Corrección**: ventana bloqueante (no usa `.modal-overlay`, para que Escape/clic fuera no la cierren) con elección obligatoria de estado; ventana «Envío para firma» que pide y sube fecha + archivo; comprobación en `savePedido`; validación 422 en `update_pedido` solo al cambiar de estado; README restaurado desde v12.32.80 (ver CHANGELOG v12.32.83).
- **Ficheros editados en este repo**: `app.py`, `templates/index.html`, `README.md` (restaurado), `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables ni SQL manual; resto de documentos de mantenimiento: no aplica.
- **Pendiente / ideas**: copiar al comprador responsable en los correos cuando firma otra persona; mostrar lo pendiente en el correo de entrega parcial; exportar a Excel los faltantes.

---

## 2026-10-07 — [Control Pedidos] Detalle opcional de referencias entregadas por entrada y dónde está la diferencia de importe (v12.32.82)

- **Origen**: Víctor: poder marcar, de forma opcional, las referencias y unidades entregadas en una entrada parcial (confirmando en pantalla y cambiando la cantidad) para ajustar y diagnosticar faltantes; y, en la entrega total con importe distinto del pedido, poder indicar dónde está la diferencia.
- **Hallazgo**: las entradas (`entrada_albaran_num`) solo guardan Nº, fecha e importe; desde v12.32.75 el pedido tiene líneas (`pedido_lineas`) sobre las que apoyarlo.
- **Corrección**: tabla `pedido_lineas_entregas` (por pedido + albarán + código), `GET /api/pedidos/<id>/entregas-lineas`, clave `entregas_lineas` en `PUT /api/pedidos/<id>` (misma transacción que el resto del formulario), botón 📋 Referencias por entrada, aviso/ventana de diferencia con comparación de importes (no hotel), columnas Entreg./Pend. en panel de líneas y buscador (ver CHANGELOG v12.32.82).
- **Ficheros editados en este repo**: `app.py`, `templates/index.html`, `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables ni SQL manual (tabla por `_auto_migrate`); resto de documentos de mantenimiento: no aplica.
- **Pendiente / ideas**: mostrar lo pendiente en el correo de entrega parcial; exportar a Excel los faltantes.

---

## 2026-10-07 — [Control Pedidos] OCR de pedidos escaneados: motivo del rechazo visible y respaldo de idioma (v12.32.81)

- **Origen**: Víctor, captura con el error de "16885.pdf" tras entregar la v12.32.80.
- **Hallazgo**: en pruebas se lee bien; sin detalle en el mensaje no se puede saber si es versión sin desplegar o diferencia del OCR del servidor.
- **Corrección**: detalle técnico del OCR en el error y en el log; respaldo a inglés si falla `spa` (ver CHANGELOG v12.32.81).
- **Ficheros editados en este repo**: `app.py`, `templates/index.html` (badge), `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables ni SQL; no aplica.

---

## 2026-10-07 — [Control Pedidos] PDF de pedido escaneado/firmado (16886): OCR por consenso + líneas verificadas (v12.32.80)

- **Origen**: Víctor, captura del error al subir el 16886 firmado (+ PDFs 16885, 16886 y 16886 original).
- **Hallazgo**: una sola pasada de OCR: Nº de pedido mal leído (16836) y totales sumados de líneas mal reconocidas (16885 → 1,07 €) — rechazo o dato equivocado sin aviso.
- **Corrección**: OCR en grises con hasta 3 pasadas; Nº y Total impreso por coincidencia entre pasadas (sin mayoría → rechazo); líneas reconstruidas con cantidad × precio = importe y aceptadas solo si suman el Total impreso; columna `pedido_adjuntos.lineas_ocr` + avisos en pantalla; lotes de lectura masiva de 4 (ver CHANGELOG v12.32.80).
- **Ficheros editados en este repo**: `app.py`, `templates/index.html`, `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables ni SQL manual (columna nueva por `_auto_migrate`). Tesseract + paquete `spa` ya estaban en el Dockerfile.
- **Pendiente / ideas**: mejorar la lectura de descripciones/referencias de escaneados con detección de la cuadrícula de la tabla.

---

## 2026-10-07 — [Control Pedidos] Correo al proveedor por cambio de estado firmado por quien gestiona el pedido (v12.32.79)

- **Origen**: Víctor: los correos de cambio de estado siempre salían firmados por el comprador responsable; si gestiona otro comprador o un administrador deben salir firmados por quien hace la gestión, para trazabilidad.
- **Hallazgo**: `enviar_emails_estado` usaba `compradores[0]` del hotel como firma y Reply-To del correo al proveedor (único correo de cambio de estado con firma de comprador; el interno ya incluye "Realizado por").
- **Corrección**: `_resolver_firmante_cambio_estado` — firma/Reply-To = usuario que hace el cambio manual si es comprador/admin activo con email; si no (automático, rol hotel, sin email) el comprador responsable. Los recordatorios automáticos a proveedores no cambian (ver CHANGELOG v12.32.79).
- **Ficheros editados en este repo**: `app.py`, `templates/index.html` (badge), `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables ni SQL; no aplica.
- **Pendiente / ideas**: si se quiere, copiar al comprador responsable cuando firme otra persona.

---

## 2026-10-07 — [Control Pedidos] Total Pedido: las etiquetas aproximado/real se veían a la vez (v12.32.78)

- **Origen**: Víctor, captura del pedido 41827 PILSA: "sale tanto aproximado como real ¿por qué?".
- **Hallazgo**: `display:inline-block` en línea anulaba el atributo `hidden` de ambas etiquetas; "≈ APROXIMADO" estaba siempre visible desde antes de v12.32.77 (el valor del total sí era correcto).
- **Corrección**: regla CSS que respeta `hidden` en las dos etiquetas (ver CHANGELOG v12.32.78).
- **Ficheros editados en este repo**: `templates/index.html`, `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin cambios de backend, variables ni SQL; no aplica.

---

## 2026-10-07 — [Control Pedidos] Total Pedido del PDF oficial: "REAL · SIN IGIC" en lugar de "≈ aproximado" (v12.32.77)

- **Origen**: Víctor: "detalle, si la lectura es del pedido real, ya el total no es aproximado, es real sin igic" (captura con 9196,44 € marcado ≈ APROXIMADO).
- **Hallazgo**: la marca `total_pedido_aproximado` solo se limpiaba al subir el PDF o al comparar el listado resumido; con el PDF ya cargado (o líneas leídas después, v12.32.75) quedaba visible aunque el total fuera el del PDF.
- **Corrección**: `get_lineas_pedido` fija total real (suma de líneas = base sin IGIC) y limpia la marca cuando hay PDF oficial con líneas cuadradas; etiqueta verde "✔ REAL · SIN IGIC" en el formulario (ver CHANGELOG v12.32.77).
- **Ficheros editados en este repo**: `app.py`, `templates/index.html`, `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables nuevas ni SQL manual; resto de documentos de mantenimiento: no aplica.

---

## 2026-10-07 — [Control Pedidos] Buscador de artículos en pedidos: hotel + referencia → nº pedido, cantidad y estado (v12.32.76)

- **Origen**: Víctor: "seria interezante un buscador en el que podamos buscar por hotel y referencia, nos indique nuemero de pedido, cantidad y estado".
- **Hallazgo**: con las líneas guardadas desde v12.32.75 (`pedido_lineas`) el buscador es una consulta directa; los pedidos con PDF anterior a esa versión no tienen líneas hasta que se abren o se lanza la lectura masiva.
- **Corrección**: `GET /api/pedidos/lineas/buscar` + `POST /api/pedidos/lineas/leer-pendientes` (admin, lotes de 10) + vista "🔎 Buscar artículo" (ver CHANGELOG v12.32.76). Rol hotel acotado a sus hoteles y sin precios; hotel `PR` oculto a quien no corresponde; límite 300 filas con aviso; aviso de cobertura (pedidos con PDF sin líneas leídas).
- **Ficheros editados en este repo**: `app.py`, `templates/index.html`, `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables de entorno nuevas ni SQL manual; revisados `GUIA_DESPLIEGUE.md`, `PENDIENTES.md`, `INSTRUCCIONES_RESTAURACION.md`: no aplica.
- **Pendiente / ideas**: contrastar cantidades pedidas con las recibidas; exportar resultados a Excel.

---

## 2026-10-07 — [Control Pedidos] PDF de pedido oficial: se leen y guardan las líneas (referencias, cantidades, precios) (v12.32.75)

- **Origen**: Víctor: "cuando se carga un pedido PDF, el sistema deberá leer el contenido del pedido, deberemos saber siempre referencias, cantidades etc; actualmente solo lee nombre proveedor almacén número pedido etc".
- **Hallazgo**: las líneas de artículo solo se leían para sumar su importe (Total Pedido) y se descartaban; `pypdf` desordena las columnas y pega la referencia del proveedor al importe ("298,801000664"), por lo que no es válido para extraerlas. Con `pdfplumber` (posición real de cada palabra) la tabla sale limpia: la línea con el código y los números va en el centro y su descripción se reparte en 1-4 líneas arriba y abajo, así que cada línea de solo texto se asigna al artículo más cercano en vertical.
- **Corrección**: lector de líneas + tabla `pedido_lineas` + endpoint `GET /api/pedidos/<id>/lineas` + panel en el formulario del pedido (ver CHANGELOG v12.32.75). Salvaguardas: las líneas solo se guardan si sus importes coinciden con los del lector antiguo; PDF escaneado (OCR) sin líneas; lectura retroactiva perezosa para pedidos ya cargados; rol hotel sin precios.
- **Ficheros editados en este repo**: `app.py`, `templates/index.html`, `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin variables de entorno nuevas ni SQL manual (la tabla se crea sola al arrancar). `pdfplumber` ya estaba en `requirements.txt`.
- **Pendiente / ideas**: buscar un artículo por código o referencia en todos los pedidos; contrastar cantidades con las entradas de mercancía.

---

## 2026-10-07 — [Control Pedidos] Excel de proveedores: código DALI, hoteles de cada contacto, servicio por hotel y rutómetro (v12.32.74)

- **Origen**: Víctor: "en control de pedidos, ficha proveedores, este es el excel que exporta actualmente, necesito incluir columna código DALI y también rutómetro, se debe poder identificar también los correos electrónicos por hoteles según esté configurada la ficha".
- **Hallazgo**: el Excel (`exportar_proveedores`) también sirve de plantilla de importación, y `_parse_excel_proveedores` lee por NOMBRE de cabecera, por lo que se pueden añadir columnas sin romperla. Los hoteles de cada contacto (`proveedor_contacto_hoteles`): sin filas = contacto "general"; con filas = solo esos hoteles; la ficha los crea todos marcados por defecto.
- **Corrección**: columnas CODIGO DALI, HOTELES DEL CONTACTO, SERVICIO EN HOTELES (v12.32.73) y RUTOMETRO (una línea por ciclo), más filtro automático. El hotel PR no se muestra en el texto de hoteles.
- **Limitación conocida (anterior a este cambio)**: la importación de proveedores sustituye los contactos y no lee asignaciones de hotel por contacto, ni las lee ahora tampoco; las columnas nuevas son informativas.
- **Ficheros editados en este repo**: `app.py`, `templates/index.html` (badge), `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: sin cambios de despliegue ni de base de datos.

---

## 2026-10-07 — [Control Pedidos / DALI] Rutómetro: servicio por hotel activo por defecto en los 10 hoteles (v12.32.73)

- **Origen**: Víctor, verbatim: "necesito que en la ficha de proveedores el rutómetro se active por defecto a los 10 hoteles y que solo el admin o comprador desmarque aquel o aquellos hoteles que el proveedor no tenga servicio, de esta manera automáticamente se realiza el filtro de materiales en la aplicación Catálogo Asignaciones según proveedores con rutómetro activo".
- **Hallazgo**: hasta v12.32.72 "tiene rutómetro" equivalía a "tiene filas en `proveedor_rutas`", así que para que DALI filtrara había que crear una ruta por hotel, y un proveedor nuevo no filtraba por omisión. Los días de pedido/reparto y el servicio por hotel son cosas distintas.
- **Corrección**: tabla `proveedor_hoteles_sin_servicio` (exclusiones: sin filas = todos los hoteles, y los hoteles nuevos nacen cubiertos); bloque "Servicio por hotel" en la ficha con todo marcado por defecto; guardado en `create_proveedor`/`update_proveedor` (si el formulario no manda la clave, se conserva lo guardado, para no borrar datos desde una página en caché); rutas de hoteles sin servicio rechazadas en formulario y backend; el puente DALI devuelve `hoteles_sin_servicio`/`hoteles_con_servicio`. El hotel `PR` queda fuera. Migración y carga inicial automáticas en `_auto_migrate()` (una sola vez, conserva las restricciones actuales: hoteles activos sin ruta de proveedores con rutómetro).
- **Ficheros editados en este repo**: `app.py`, `models.py` (solo nota), `templates/index.html`, `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md`.
- **Otros documentos (norma 5)**: `GUIA_DESPLIEGUE.md` y similares no existen/no afectan: sin variables de entorno nuevas ni SQL manual.
- **Despliegue**: primero esta app, después DALI v1.20.36.

---

## 2026-10-02 — [Control Pedidos / DALI] El Rutómetro decide qué artículos ve activos cada usuario según su hotel (v12.32.72)

- **Origen**: Víctor, verbatim: "necesito que cada usuario solo vea activo
  los articulos de los proveedores que tienen servicio en su hotel, por
  ejemplo, Fran y Chemi (1001411) solo tiene reparto en la isla de
  Fuerteventura (FV y JN); el sistema deberá verificar en la ficha del
  proveedor el rutómetro y si no tiene reparto en un hotel, los artículos
  asignados a este proveedor pasan a no activos automáticamente (...) si
  no tiene rutómetro activo, entonces no hay variación". También pidió
  una ficha lateral con el rutómetro al pulsar el nombre de un proveedor
  en el catálogo DALI — lo preparó dejando asignar un hotel a cada
  usuario de DALI (`usuarios.hoteles_ids`, 2026-10-02, entrega anterior
  ese mismo día) sin decir todavía para qué, "luego indicaré que función
  puede tener esto".
- **Dónde vive cada cosa**: el Rutómetro es un dato de Control Pedidos
  (`proveedor_rutas`); los artículos y los usuarios con hotel asignado
  son de DALI. Se cruzan por NOMBRE exacto de proveedor, por el puente ya
  existente entre las dos apps (`GET /api/externo/dali-sap/proveedores`,
  v12.30.26 y siguientes) — bastaba con que ese endpoint devolviera
  también el rutómetro de cada proveedor, sin crear uno nuevo.
- **Decisión de arquitectura**: se preguntó a Víctor si prefería que DALI
  guardara una copia sincronizada (botón manual o refresco automático) o
  consultara Control Pedidos en vivo en cada petición. Eligió **consulta
  en vivo**, explícitamente, porque además quiere la ficha lateral de
  detalle al pulsar el proveedor con el dato real del momento. Asumido a
  propósito: el catálogo de DALI pasa a depender de que Control Pedidos
  responda a tiempo; si no responde, DALI falla "abierto" (sin
  restricción, como si el proveedor no tuviera rutómetro) en vez de
  romper la carga del catálogo — ver el HISTORIAL.md de DALI.
- **Cambio en este repo**: `GET /api/externo/dali-sap/proveedores`
  (`app.py`) añade `rutas` a cada proveedor de la respuesta (uno por fila
  de `proveedor_rutas`: hotel, días de pedido, días de reparto,
  observaciones), reutilizando `_prov_with_contactos()` tal cual —
  `rutas: []` significa "sin rutómetro configurado" (Víctor: "si no tiene
  rutómetro activo, entonces no hay variación"), nunca "cubre cero
  hoteles". Sin cambios de base de datos ni de permisos aquí.
- **Cambio en DALI** (repo aparte, `dali-sap-articulos-app` — resumen,
  ver su propio HISTORIAL.md/CHANGELOG.md para el detalle): la sesión de
  cada usuario pasa a incluir `hoteles_ids`; el listado principal del
  catálogo (`GET /articulos`), para usuarios con rol 'hotel' (nunca para
  admin), excluye los artículos de un proveedor cuando ese proveedor SÍ
  tiene rutómetro en Control Pedidos pero ninguna de sus rutas cubre los
  hoteles del usuario — consulta en vivo al puente en cada petición, sin
  copia propia. Nueva ficha lateral (`ProveedorRutometroDetail.jsx`,
  consulta en vivo también) al pulsar el nombre de un proveedor, tanto en
  la tabla principal como en el detalle de artículo.
- **Revisión norma 5**: no aplica a `GUIA_DESPLIEGUE.md` /
  `INSTRUCCIONES_RESTAURACION.md` / `PENDIENTES.md` en este repo — el
  endpoint ya existía, solo se amplía su respuesta.
- **Verificación**: `python3 -m py_compile app.py` limpio en este repo.
  Comprobado a mano que `rutas` sale vacío para un proveedor sin ninguna
  fila en `proveedor_rutas` y con sus filas reales, agrupadas por hotel,
  para uno que sí tiene rutómetro. Lado DALI: `node --check` en los
  archivos backend tocados, `vite build` real (con y sin `VITE_API_URL`)
  y un script aparte verificando la lógica de intersección de hoteles —
  ver su propio HISTORIAL.md/CHANGELOG.md para el detalle completo.
- **Ficheros**: en este repo — `app.py`, `templates/index.html`,
  `README.md`, `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md` (este). En
  DALI — ver su propio HISTORIAL.md/CHANGELOG.md.

---

## 2026-10-02 — [Control Pedidos] Rutómetro: un hotel puede tener varios repartos distintos la misma semana (v12.32.71)

- **Origen**: corrección de Víctor sobre la v12.32.70 entregada unas horas
  antes el mismo día, verbatim: "un proveedor puede tener varios repartos
  en la misma semana y hotel".
- **Problema**: la v12.32.70 original diseñó el rutómetro como "una fila =
  el horario completo de un hotel" (`UNIQUE(proveedor_id, hotel_id)`), con
  un conjunto de días de pedido y otro de días de reparto sin relación
  entre sí. No permite expresar dos ciclos reales distintos en el mismo
  hotel la misma semana (p.ej. pedido L → reparto X, y también pedido J →
  reparto V) sin perder qué pedido corresponde a qué reparto — y el UNIQUE
  ni siquiera dejaba intentarlo con dos filas.
- **Corrección**: se quita la restricción de una fila por hotel. Cada fila
  pasa a ser un ciclo pedido→reparto independiente; el mismo hotel puede
  repetirse en tantas filas como ciclos reales tenga.
- **Cambio**: `models.py` (tabla `proveedor_rutas` sin el `UNIQUE` en
  instalaciones nuevas); `_auto_migrate()` en `app.py` (nuevo bloque
  protegido, `ALTER TABLE ... DROP CONSTRAINT IF EXISTS
  proveedor_rutas_proveedor_id_hotel_id_key`, por si alguna base de datos
  llegó a desplegar la v12.32.70 tal cual); `_guardar_rutas_proveedor()`
  ya no rechaza hoteles repetidos en el payload; `_prov_with_contactos()`
  reordena el rutómetro por hotel primero para que las filas de un mismo
  hotel salgan agrupadas; `templates/index.html` quita la lógica que
  deshabilitaba hoteles ya elegidos en otras filas (ya no aplica) y
  actualiza el texto de ayuda del apartado.
- **Revisión norma 5**: igual que la entrada anterior (v12.32.70) — no
  aplica a `GUIA_DESPLIEGUE.md`/`INSTRUCCIONES_RESTAURACION.md`/
  `PENDIENTES.md`.
- **Verificación**: `python3 -m py_compile app.py models.py init_db.py`
  limpio. Lógica de guardado reproducida aparte con el caso real de
  Víctor (mismo hotel, dos ciclos pedido→reparto) — las filas se
  conservan sin mezclar días entre ciclos. `node --check` limpio sobre
  los 7 `<script>` reales de `templates/index.html`. Sigue pendiente de
  probarse contra Postgres real.
- **Ficheros**: `models.py`, `app.py`, `templates/index.html`, `README.md`,
  `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md` (este).

---

## 2026-10-02 — [Control Pedidos] Rutómetro en la ficha de proveedor: días de pedido y reparto por hotel (v12.32.70)

- **Origen**: Víctor, verbatim: "Necesito que añadas a la ficha del
  proveedor un apartado para rutometro, de manera profesional y clara, la
  idea es que se pueda indicar dias de pedido y reparto correspondiente
  por hotel", con dos capturas del modal "Editar proveedor" (ficha de
  EMICELA SA) como referencia del sitio donde debía ir.
- **Diseño**: una fila por hotel (nunca dos para el mismo hotel — el
  select del hotel deshabilita en las demás filas el que ya está elegido
  en una, y el servidor aplica la misma regla por si acaso), con chips de
  días de la semana (L-M-X-J-V-S-D) independientes para "días de pedido"
  y "días de reparto", más una observación libre opcional por fila. Mismo
  patrón visual y de interacción que "Contactos", en la misma ficha, para
  que resulte familiar. Puramente informativo: no dispara avisos, no
  bloquea ni modifica ningún pedido, no interviene en "Comparar listado
  PDF" ni en ninguna otra lógica existente.
- **Cambio**:
  - Tabla nueva `proveedor_rutas` (`models.py` para instalaciones desde
    cero, `_auto_migrate()` en `app.py` para las ya desplegadas, puesta en
    el bloque protegido con su propio try/except — misma norma que
    `codigo_dali`/`sujeto_seguimiento`/`total_pedido`, ver esas entradas
    anteriores). `UNIQUE(proveedor_id, hotel_id)`: un proveedor no puede
    tener dos horarios distintos para el mismo hotel.
  - `_normalizar_dias_semana()`, `_guardar_rutas_proveedor()` (`app.py`,
    nuevas) — normalizan y guardan el rutómetro al crear/editar un
    proveedor, comprobando ANTES de tocar la base de datos que ningún
    hotel se repita en el payload (para no dejar la transacción abortada
    a mitad de guardar el resto de la ficha).
  - `_prov_with_contactos()` (`app.py`) ahora también adjunta `rutas` a
    cada proveedor — usada por los 4 endpoints que devuelven fichas
    completas, así que el rutómetro queda disponible en todos sin tocarlos
    uno por uno.
  - Permisos: admin y compras pueden editar el rutómetro (igual que
    contactos/observaciones), no solo admin — es logística operativa, no
    un dato de identidad del proveedor como nombre/código SAP/DALI.
  - `templates/index.html`: apartado nuevo "🚚 Rutómetro" en el modal
    "Editar proveedor" (entre Contactos y Observaciones), funciones `rt*`.
- **Revisión norma 5**: `GUIA_DESPLIEGUE.md` e
  `INSTRUCCIONES_RESTAURACION.md` solo refieren el schema de forma
  genérica ("ejecuta `models.py`"/`SQL_STATEMENTS`), sin listar tablas
  concretas — no aplica ningún cambio. `PENDIENTES.md` no aplica (no era
  una tarea ahí registrada, se implementa directamente en la misma
  petición).
- **Verificación**: `python3 -m py_compile app.py models.py init_db.py`
  limpio. `_normalizar_dias_semana()` y la detección de hotel duplicado
  extraídas a un script aparte, probadas con 9 casos (orden, mayúsculas/
  minúsculas, códigos inválidos, vacíos, duplicado real) — todos
  correctos. Los 7 `<script>` reales de `templates/index.html`
  (descartando coincidencias falsas de la palabra "script" dentro de
  comentarios HTML) extraídos y comprobados con `node --check`, limpio.
  No se ha podido probar contra una base de datos Postgres real — falta
  que Víctor pruebe en producción (crear/editar un proveedor con 2-3
  hoteles y días distintos, comprobar que persisten, que un hotel ya
  elegido no se puede repetir, y que compras puede editarlo).
- **Ficheros**: `models.py`, `app.py`, `templates/index.html`, `README.md`,
  `CHANGELOG.md`, `docs/HISTORIAL_CAMBIOS.md` (este).

---

> 📦 **Entradas anteriores** (julio a septiembre de 2026): ver
> `docs/archivo/HISTORIAL_CAMBIOS_2026-07_a_2026-09.md`.

---

## Convenciones de este historial
- Versionado de Organizador Princess: 3er dígito +2 (0,2,4,6,8) →
  al pasar de 8, 2º dígito +2 y 3º vuelve a 0 (4.10.8→4.12.0) → al
  llegar el 2º a 98, 1er dígito +1 y los otros dos a 0 (4.98.8→5.0.0).
- Cada release de Organizador actualiza `APP_VERSION` en
  `main_agenda.py`, `release_notes_actual.txt` (usuario) y
  `release_notes.md` (técnico) — ver esos ficheros para el detalle
  línea a línea; este historial es el resumen unificado entre
  proyectos.
