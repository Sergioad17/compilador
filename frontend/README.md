# Miezee IDE

Frontend principal de Miezee IDE.

Stack:

- Tauri
- React
- TypeScript
- Monaco Editor
- Backend Python mediante `python -m miezee.backend.cli`

El frontend anterior de PySide6 fue retirado. React/Tauri es la unica interfaz
de escritorio mantenida por el proyecto.

## Contrato backend disponible

Analizar codigo:

```powershell
python -m miezee.backend.cli analyze --file examples/correcto_consola.py
```

Traducir codigo:

```powershell
python -m miezee.backend.cli translate --file examples/correcto_consola.py
```

Ejecutar codigo de consola:

```powershell
python -m miezee.backend.cli run --file examples/correcto_consola.py
```

Todos los comandos devuelven JSON.

## Etapa actual: editor y analisis

- Monaco Editor local (sin descargar el editor desde un CDN).
- Documentos en pestanas, nuevos documentos y apertura de ejemplos Python.
- Analisis, diagnosticos en el editor, tabla de simbolos y reglas aplicadas.
- Traduccion educativa a Miezee.
- Reporte de analisis semantico con ambitos e identificadores.
- Generacion y visualizacion de codigo intermedio TAC para Python (`F10`).
- Bridge Tauri/Python asincrono, sin archivos temporales de codigo.

Se integraron tambien:

- Abrir archivos y carpetas, guardar y guardar como mediante dialogos nativos.
- Explorador recursivo filtrado, con examples al inicio y proteccion del codigo interno.
- Consola interactiva con input(), salida UTF-8, detener y limpiar.
- Vista previa en un proceso independiente, con errores visibles y arranque de GUI.
- Chat Ollama, comandos con slash y sugerencias, generacion y correccion al editor.
- Burbujas diferenciadas y Markdown, incluyendo negrita, cursiva, subrayado y tachado.
- Temas Default/Morado y sus iconos, fuente configurable y preferencias locales.
- Menus Archivo/Editar/Ver/Ejecutar/Terminal/Ayuda, atajos y paleta de comandos.
- Paneles ocultables y separadores ajustables con el raton.
- Confirmacion de descarte al cerrar documentos o la ventana.

`app.py` inicia esta aplicacion Tauri y conecta el backend con el interprete de
Python activo. El chat no persiste
mensajes ni soluciones pregrabadas: construye el prompt con la solicitud y el
archivo actual. Esto aporta contexto al modelo; no modifica sus pesos.

## Arquitectura MVC

- Modelos: `src/models/ide.ts`, contratos de documentos y analisis.
- Controlador: `src/controllers/useIdeController.ts`, estado y acciones del IDE.
- Controladores especializados: consola, chat y distribucion de paneles.
- Vistas: `src/App.tsx` y `src/views/CodeEditor.tsx`.
- Servicios: `src/services/backend.ts`, comunicacion tipada con Tauri.
- Controladores nativos: `src-tauri/src/controllers.rs`, comandos permitidos.
- Servicios nativos: `src-tauri/src/services.rs`, Python y lectura de examples.
- `src-tauri/src/files.rs`: dialogos, permisos de archivos y explorador.
- `src-tauri/src/runtime.rs`: procesos de consola y vista previa.
- `src-tauri/src/jobs.rs`: solicitudes de IA cancelables.
- `miezee/backend/chat_service.py`: generacion y validacion sin dependencia de Qt.

Las vistas no inician procesos Python. El controlador invalida resultados al
cambiar de documento o editarlo para evitar presentar analisis desactualizados.

## Desarrollo

Requisitos: Node/npm, Rust/Cargo, herramientas de compilacion C++ de Windows,
WebView2 y Python con las dependencias del proyecto instaladas.

Desde `frontend`:

```powershell
npm install
npm run desktop
```

`npm run desktop` encuentra Cargo incluso si la terminal aun no actualizo su PATH.
Tambien selecciona un puerto libre y configura Tauri para usar ese mismo puerto.
`npm run tauri dev` tambien funciona con Rust disponible en el PATH.
`npm run dev` permite revisar el aspecto en el navegador; el backend solo esta
conectado dentro de Tauri. `npm run build` comprueba TypeScript y genera el front.

En desarrollo, el backend se busca en la raiz del repositorio. Se puede indicar
otro directorio con `MIEZEE_PROJECT_ROOT` y otro ejecutable con `MIEZEE_PYTHON`.
El empaquetado del backend Python para distribucion aun esta pendiente.

## Verificacion

```powershell
npm run build
cargo test --manifest-path src-tauri/Cargo.toml
```

La compilacion valida React y TypeScript. Las pruebas Rust ejecutan procesos
Python reales para comprobar entrada interactiva, Unicode, detencion y acceso
seguro a archivos.

## Cobertura funcional

| Funcion | Implementacion actual |
| --- | --- |
| Edicion Python y pestanas | Monaco y documentos del modelo MVC |
| Abrir/guardar/abrir carpeta | Dialogos nativos y servicio de archivos |
| Analizar/problemas/reglas/simbolos | Mismo backend Python y paneles React |
| Tokens del analisis lexico | Panel Lexico con categorias, lexemas y posiciones |
| AST y resumen sintactico | Panel Sintactico con metricas, construcciones y arbol completo |
| Ejecutar, leer input, detener | Proceso Python separado y consola incremental |
| Traducir a Miezee | Mismo traductor Python |
| Vista previa GUI | Proceso separado con arranque automatico |
| Chat/generar/corregir/explicar | Ollama y aplicacion al documento de origen |
| Slash y formato de mensajes | Sugerencias navegables y Markdown |
| Default/Morado y logos | Variables CSS e iconos por tema |
| Atajos, menus, paleta | Menus y controladores React |
| Paneles ajustables/ocultables | Separadores y preferencias de visibilidad |

Se comprobo tambien dentro de la ventana Tauri la lectura por consola, Unicode,
una ventana tkinter real y generacion con Ollama aplicada al editor. La prueba
repetible esta en `scripts/native-smoke.mjs` y usa el puerto CDP configurado al
iniciar WebView2; no graba mensajes ni escribe archivos de codigo temporales.
Solo guarda capturas si se proporciona explicitamente `MIEZEE_CAPTURE_DIR`.

Queda pendiente la distribucion autocontenida del backend Python fuera del
repositorio. Los dialogos nativos y los flujos principales ya pertenecen
exclusivamente a esta interfaz.
