# MakeitEasy Miezee

Prototipo academico de analizador semantico para el lenguaje MakeitEasy, tambien llamado Miezee. La aplicacion es de escritorio, usa Python y PySide6, y mantiene la validacion semantica de forma local y determinista. La IA solo explica, propone correcciones y genera ejemplos: no decide si un programa es valido.

## Instalacion en Windows

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Para ejecutar pruebas:

```powershell
python -m unittest discover -s tests -v
```

## Configuracion de IA local con Ollama

Edita el archivo `.env` local, que no debe entregarse ni subirse al repositorio:

```env
AI_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:14b
```

Para usar la IA local instala Ollama y descarga un modelo:

```powershell
winget install Ollama.Ollama
ollama pull qwen3:14b
ollama run qwen3:14b
```

Si Ollama no esta corriendo o el modelo no esta instalado, la aplicacion muestra un mensaje comprensible. El analizador semantico, la tabla de simbolos, los errores y los comandos locales siguen funcionando sin Internet.

## Sintaxis minima

```miezee
DEFINIR edad COMO ENTERO = 25
CAMBIAR edad A edad + 1
MOSTRAR edad >= 18
```

Instrucciones soportadas:

- `DEFINIR <identificador> COMO <TIPO> = <expresion>`
- `CAMBIAR <identificador> A <expresion>`
- `MOSTRAR <expresion>`
- `IF <condicion>`
- `ELSE`
- `FOR i DESDE 1 HASTA 10`
- `WHILE <condicion>`
- `SWITCH <expresion>`
- `BREAK`
- `CONTINUE`
- `CREAR PANTALLA "Titulo"`
- `AGREGAR CAMPO <identificador> COMO <TIPO>`
- `AGREGAR BOTON "Texto"`
- `AGREGAR BOTON "Texto" GUARDAR COMO TXT "archivo.txt"`
- `AGREGAR BOTON "Texto" GUARDAR COMO WORD "archivo.rtf"`
- `AGREGAR BOTON "Texto" GUARDAR COMO JSON "archivo.json"`
- `AGREGAR BOTON "Texto" GUARDAR COMO CSV "archivo.csv"`
- `MOSTRAR PANTALLA`

Tipos: `ENTERO`, `DECIMAL`, `TEXTO`, `BOOLEANO`, `FECHA`, `ARCHIVO`.

Tipos extendidos: `byte`, `short`, `int`, `long`, `float`, `double`, `char`, `boolean`.

Operadores: `+`, `-`, `*`, `/`, `^`, `**`, `<`, `<=`, `>`, `>=`, `==`, `!=`, `Y`, `O`, `NO`.

## Reglas semanticas implementadas

- `RT01`: ENTERO con ENTERO mediante `+`, `-` o `*` produce ENTERO. La division produce DECIMAL.
- `RT02`: ENTERO con DECIMAL produce DECIMAL.
- `RT03`: TEXTO + TEXTO produce TEXTO.
- `RT04`: comparaciones numericas e igualdad compatible producen BOOLEANO.
- `RT05`: operadores logicos `Y`, `O`, `NO` requieren BOOLEANO.
- `RT06`: FECHA y ARCHIVO no pueden usarse en operaciones aritmeticas.
- `RT07`: los tipos `byte`, `short`, `int` y `long` tienen rangos definidos.
- `RI01`: un identificador debe declararse antes de usarse.
- `RI02`: no se permite declarar dos veces el mismo identificador.
- `RI03`: no se pueden usar palabras reservadas como identificadores.
- `RI04`: el valor inicial y las asignaciones deben ser compatibles.
- `RI05`: el tipo de una variable permanece fijo.
- `RF01`: IF y WHILE requieren condiciones booleanas.
- `RF02`: FOR requiere limites numericos.
- `RF04`: SWITCH requiere un valor discreto o comparable.
- `RF05`: BREAK y CONTINUE controlan flujo.

## Errores semanticos

- `ES01`: identificador no declarado.
- `ES02`: identificador duplicado.
- `ES03`: operacion entre tipos incompatibles.
- `ES04`: asignacion incompatible.
- `ES05`: uso de palabra reservada como identificador.

Cada error incluye codigo, linea, instruccion, identificadores, tipos, operador, explicacion, regla incumplida y sugerencia.

## Interfaz

La aplicacion usa modo oscuro y una distribucion similar a un editor de codigo:

- Barra superior con acciones de archivo, analisis, pruebas, limpieza y configuracion.
- Explorador lateral con archivos `.miezee`, casos de prueba y archivos abiertos.
- Editor central con pestanas, fuente monoespaciada, numeros de linea, resaltado y marcas en lineas con errores.
- Panel inferior con Problemas, Resultado, Tabla de simbolos y Vista previa.
- Pestaña Vista previa para pantallas creadas con instrucciones visuales de Miezee.
- Panel derecho de chat con comandos locales y solicitudes asincronas a Ollama local.
- Barra de estado con archivo, linea/columna, errores, estado del analizador, estado IA y UTF-8.

## Atajos

- `Ctrl+N`: nuevo archivo.
- `Ctrl+O`: abrir archivo.
- `Ctrl+S`: guardar.
- `Ctrl+Shift+S`: guardar como.
- `F5`: analizar programa.
- `Ctrl+L`: limpiar panel de resultados.
- `Ctrl+Shift+P`: abrir paleta de comandos.
- `Ctrl+Shift+C`: colocar el cursor en el chat.
- `Ctrl+B`: mostrar u ocultar explorador.
- `Ctrl+J`: mostrar u ocultar panel inferior.

## Comandos locales del chat

- `/ayuda`
- `/tipos`
- `/reglas`
- `/ejemplo`
- `/ejemplo correcto`
- `/ejemplo error`
- `/analizar`
- `/errores`
- `/tabla`
- `/explicar`
- `/corregir`
- `/GenerarPantalla descripcion de la pantalla o programa`
- `/limpiar`
- `/estado`

Los comandos `/analizar`, `/errores`, `/tabla`, `/tipos` y `/reglas` funcionan sin conexion.
El comando `/GenerarPantalla` usa Ollama local para crear codigo Miezee, lo coloca en el editor y ejecuta el analizador semantico.
Cuando genera instrucciones `CREAR PANTALLA`, `AGREGAR CAMPO`, `AGREGAR BOTON` y `MOSTRAR PANTALLA`, la pestaña Vista previa muestra un formulario basico. Si el boton incluye `GUARDAR COMO`, al presionarlo guarda los datos en `outputs/` como TXT, RTF editable en Word, JSON o CSV.
Ademas de Miezee, el chat puede responder dudas de programacion general, logica, algoritmos e investigacion academica basica usando el modelo local. No tiene acceso a Internet desde la aplicacion.

## Estructura del proyecto

- `app.py`: punto de entrada de la aplicacion.
- `miezee/core/lexer.py`: divide cada linea en tokens simples.
- `miezee/core/parser.py`: construye instrucciones y expresiones sin usar `eval` ni `exec`.
- `miezee/core/ast_nodes.py`: define los nodos del arbol de sintaxis.
- `miezee/core/data_types.py`: enumera tipos y compatibilidad de asignacion.
- `miezee/core/symbol_table.py` y `symbol.py`: administran identificadores declarados.
- `miezee/core/semantic_analyzer.py`: aplica reglas semanticas y genera errores.
- `miezee/core/errors.py`: formato de error semantico.
- `miezee/core/semantic_rules.py`: palabras reservadas, reglas y textos de ayuda.
- `miezee/ui/main_window.py`: ventana principal y conexion entre botones, editor y analizador.
- `miezee/ui/code_editor.py`: editor con numeros de linea y marcas de error.
- `miezee/ui/syntax_highlighter.py`: resaltado con `QSyntaxHighlighter`.
- `miezee/ui/explorer_panel.py`: explorador de archivos.
- `miezee/ui/problems_panel.py`: tabla de errores.
- `miezee/ui/symbol_table_panel.py`: tabla de simbolos visual.
- `miezee/ui/command_palette.py`: paleta de comandos.
- `miezee/ui/chat_panel.py`: chat, botones y comandos locales.
- `miezee/ui/dark_theme.py`: hoja de estilos oscura.
- `miezee/ai/ai_client.py`: cliente Ollama local con manejo de errores.
- `miezee/ai/ai_worker.py`: solicitudes de IA en `QRunnable` para no congelar la UI.
- `miezee/ai/chat_commands.py`: comandos que funcionan sin Internet.
- `miezee/ai/system_prompt.py`: instruccion educativa interna.
- `miezee/services/file_service.py`: lectura y escritura UTF-8.
- `miezee/services/settings_service.py`: lectura de variables `.env`.
- `examples/`: cinco programas de prueba.
- `tests/`: pruebas con `unittest`.

## Ejemplos incluidos

- `examples/correcto_1.miezee`: declaracion, asignacion y muestra de ENTERO.
- `examples/correcto_2.miezee`: compatibilidad ENTERO a DECIMAL.
- `examples/error_no_declarado.miezee`: produce `ES01`.
- `examples/error_duplicado.miezee`: produce `ES02`.
- `examples/error_tipos.miezee`: produce `ES03` por `ARCHIVO` en suma.
- `examples/pantalla_empleados.miezee`: crea una pantalla visual simple con campos y boton.

## Guion para video de 3 a 5 minutos

1. Presentar Miezee como lenguaje academico sencillo orientado a instrucciones cercanas al espanol.
2. Mostrar la estructura del proyecto y explicar que el analizador local es determinista.
3. Abrir la aplicacion con `python app.py` y describir las zonas: explorador, editor, panel inferior y chat.
4. Ejecutar `correcto_1.miezee` con F5 y mostrar que no hay errores.
5. Ejecutar `error_tipos.miezee` y explicar el error `ES03`, la linea marcada y la regla `RT06`.
6. Abrir la tabla de simbolos y explicar identificador, tipo y linea.
7. Usar `/tipos`, `/reglas` y `/analizar` en el chat sin conexion.
8. Explicar que con Ollama configurado el chat puede pedir a la IA local explicaciones, pero la decision final sigue siendo del analizador.
9. Ejecutar `python -m unittest discover -s tests -v` y cerrar mostrando que las pruebas pasan.

## Capturas sugeridas para el PDF

- Estructura de carpetas del proyecto.
- Ventana principal en modo oscuro.
- Editor con un programa correcto.
- Panel Resultado despues de analizar.
- Panel Problemas mostrando un error `ES03`.
- Tabla de simbolos con `edad`, `sueldo` o `contrato`.
- Un ejemplo abierto desde `examples/` y analizado individualmente.
- Chat usando `/ayuda`, `/tipos` o `/reglas`.
- Archivo `.env.example` sin clave real.
- Salida de pruebas unitarias en consola.

## Estado verificado

Comandos ejecutados durante la preparacion:

```powershell
python -m compileall .
python -m unittest discover -s tests -v
python -c "import PySide6, dotenv; print('dependencias principales disponibles')"
```

Tambien se instancio la ventana en modo offscreen y se ejecuto un analisis de prueba para comprobar que la UI se conecta con el analizador.
