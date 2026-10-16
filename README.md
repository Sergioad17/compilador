# MakeitEasy Miezee

MakeitEasy Miezee es un prototipo academico de IDE low-code. La version actual usa **Python como lenguaje principal** para que la IA local pueda generar programas, interfaces sencillas, logica de consola, manejo de archivos y bases de datos con menos friccion.

El lenguaje Miezee original ya no es el flujo principal. Se conserva como apoyo educativo: el IDE traduce codigo Python a una representacion Miezee estructurada para explicar que hace el programa.

## Estado actual

- Lenguaje principal: Python.
- Interfaz de escritorio: Tauri + React + TypeScript + Monaco Editor.
- Analizador local: revisa sintaxis, importaciones permitidas, llamadas peligrosas y tabla de simbolos.
- IA local opcional: Ollama.
- Modelo sugerido: `qwen3:14b`.
- Ejecucion: consola integrada e interfaces graficas.
- Vista previa: detecta interfaces Python y abre la pantalla en una ventana real.
- Traduccion: Python a Miezee educativo y no ejecutable, mostrada en un visor de codigo de solo lectura con lineas y resaltado.
- Backend: Python, conectado mediante comandos nativos de Tauri.

La IA ayuda a generar, corregir y explicar codigo, pero la validacion final del programa la hace el analizador local.

## Frontend principal

La interfaz principal usa Tauri + React + TypeScript + Monaco y sigue una separacion MVC.
Incluye archivos y carpetas, analisis, simbolos, traduccion, consola interactiva,
vista previa, chat Ollama, temas y menus. El frontend anterior de PySide6 fue retirado.

Con Node, Rust y las herramientas C++ instaladas:

```powershell
cd frontend
npm install
cd ..
python app.py
```

El detalle de arquitectura, pruebas y paridad esta en [frontend/README.md](frontend/README.md).
Durante el desarrollo, `app.py` inicia Tauri y conecta el backend con el mismo
interprete de Python activo. La distribucion autocontenida sigue pendiente.

## Instalacion en Windows

```powershell
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
cd frontend
npm install
cd ..
python app.py
```

## Configuracion de IA local

El proyecto usa Ollama de forma opcional. Edita `.env`:

```env
AI_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:14b
```

Instalacion sugerida:

```powershell
winget install Ollama.Ollama
ollama pull qwen3:14b
ollama run qwen3:14b
```

Si Ollama no esta disponible, el analizador, la consola, los menus, la tabla de simbolos y los comandos locales siguen funcionando. Lo unico que se desactiva es el chat generativo.

## Uso principal

1. Abre la aplicacion con `python app.py`.
2. Escribe codigo Python en el editor o pide al chat que lo genere.
3. Usa **Analizar** para validar el codigo.
4. Usa **Ejecutar programa** para correr programas de consola.
5. Usa **Vista previa** para abrir interfaces graficas generadas con `tkinter`, `customtkinter` o `PySide6`.
6. Usa **Traducir codigo** para ver una traduccion educativa estructurada a Miezee.
7. Selecciona un fragmento en el editor o en la traduccion y usa el menu contextual **¿Que hace, para que sirve?** para cargarlo en el chat sin enviarlo todavia.

Ejemplo de programa interactivo:

```python
base = float(input("Ingresa la base: "))
altura = float(input("Ingresa la altura: "))
area = base * altura / 2
print("Area:", area)
```

Ejemplo de pantalla sencilla:

```python
import tkinter as tk
from tkinter import messagebox

def calcular():
    base = float(entry_base.get())
    altura = float(entry_altura.get())
    area = base * altura / 2
    messagebox.showinfo("Resultado", f"Area: {area}")

root = tk.Tk()
root.title("Calculadora de area")

tk.Label(root, text="Base").pack()
entry_base = tk.Entry(root)
entry_base.pack()

tk.Label(root, text="Altura").pack()
entry_altura = tk.Entry(root)
entry_altura.pack()

tk.Button(root, text="Calcular", command=calcular).pack()
root.mainloop()
```

## Analizador Python seguro

El analizador local realiza fases lexica, sintactica y semantica sin ejecutar el programa durante el analisis. La fase lexica usa `tokenize` y la sintactica usa `ast`, ambos componentes oficiales de la version de Python instalada.

Funciones actuales:

- Clasifica tokens de Python con lexema, tipo, linea y columna.
- Reconoce palabras reservadas, palabras clave contextuales, operadores exactos, comentarios, sangria y segmentos de f-strings.
- Detecta caracteres y operadores invalidos, cadenas sin cerrar e indentacion lexicamente incorrecta como `PY-LEXICO` (`PY00`).
- Detecta tambien literales numericos mal formados mediante los diagnosticos oficiales de CPython y mantiene separadas las fases lexica y sintactica.
- Detecta estructuras que incumplen la gramatica de Python como `PY-SINTAXIS` (`PY01`).
- Construye el AST oficial de Python y resume nodos, sentencias, expresiones y construcciones sin ejecutar el programa.
- Permite ejecutar las fases por separado con `python -m miezee.backend.cli lexical`, `python -m miezee.backend.cli syntax` y `python -m miezee.backend.cli semantic`.
- El analisis semantico distingue mayusculas en identificadores, construye ambitos, valida firmas locales, contexto de instrucciones y politicas de ejecucion segura.
- Los nombres no resueltos y las anotaciones incompatibles se presentan como advertencias conservadoras, porque Python permite resolucion dinamica y no obliga los tipos anotados en tiempo de ejecucion.
- Bloquea importaciones peligrosas como `os`, `sys`, `subprocess`, `socket`, `requests`, `urllib`, `ctypes` y similares.
- Bloquea llamadas dinamicas o peligrosas como `eval`, `exec`, `compile`, `__import__`, `globals`, `locals` y `vars`.
- Permite librerias utiles para el prototipo: `tkinter`, `customtkinter`, `PySide6`, `sqlite3`, `json`, `csv`, `math`, `pathlib`, `datetime` y `random`.
- Construye una tabla de simbolos con variables, funciones y clases.
- Infiere tipos comunes: `Int`, `Double`, `Texto`, `Boolean`, `Funcion`, `Clase` e `Inferido`.

La traduccion educativa cubre bloques anidados, `if/elif/else`, `match/case`, ciclos, colecciones, modulos, clases, excepciones, interfaces, SQLite, archivos y consola. Las construcciones avanzadas o futuras se preservan mediante una representacion universal, por lo que nunca se presentan como codigo ejecutable Miezee. Consulta [la especificacion de Miezee educativo](docs/MIEZEE_EDUCATIVO.md).

### Analisis semantico y codigo intermedio

El panel **Semantico** muestra el estado de las validaciones, los ambitos producidos por `symtable`, los identificadores y sus roles, las advertencias de nombres y los errores de contexto detectados por el compilador oficial de Python. Incluye restricciones de importaciones y llamadas del modo seguro.

El panel **Lexico** muestra la secuencia completa de tokens del archivo: categoria, tipo general, tipo exacto, lexema y posiciones inicial y final. Los errores lexicos se muestran en el mismo panel y tambien en **Problemas**; al seleccionar un token, el editor navega a su linea.

El panel **Sintactico** muestra el estado independiente de la fase, los errores gramaticales, un resumen con cantidades de nodos, sentencias y expresiones, las construcciones detectadas y el arbol de sintaxis abstracta (AST) completo. Si existen errores lexicos, indica que la construccion del AST no fue ejecutada.

El comando **Generar codigo intermedio** (`F10`) produce TAC para el archivo Python actual. Incluye temporales, etiquetas, saltos, cortocircuito, comparaciones encadenadas, ciclos, funciones, llamadas, colecciones, comprensiones, clases, excepciones, recursos y construcciones asincronas. Solo se genera cuando el archivo supera los analisis previos y cuando la integridad de etiquetas y saltos es correcta. Consulta [la especificacion del codigo intermedio](docs/CODIGO_INTERMEDIO.md).

## Consola interactiva

La pestana **Consola** permite ejecutar programas que usan `input()` y `print()`.

Ejemplo:

```python
numero1 = int(input("Primer numero: "))
numero2 = int(input("Segundo numero: "))
print("Resultado:", numero1 + numero2)
```

Al presionar **Ejecutar programa**, la consola muestra los mensajes del programa y permite ingresar datos paso a paso.

## Vista previa de pantallas

La pestana **Vista previa** detecta si el codigo contiene una interfaz grafica con `tkinter`, `customtkinter` o `PySide6`.

Si hay una interfaz valida:

- muestra que se detecto una interfaz Python;
- permite abrir la pantalla con **Abrir vista previa**;
- tambien puede abrirse desde el menu **Ver > Mostrar vista previa** o con `F7`;
- agrega automaticamente `mainloop()` para `tkinter/customtkinter` si falta, solo durante la ejecucion.

La vista previa no guarda archivos temporales visibles en el proyecto. La ejecucion se hace en memoria.

## Chat con IA

El panel derecho funciona como chat educativo y generador de codigo.

Puede:

- responder dudas de programacion general;
- explicar errores seleccionados;
- corregir codigo del editor;
- generar programas Python;
- generar funciones;
- generar interfaces;
- adaptar el codigo abierto en el editor;
- leer documentos adjuntos y usarlos como contexto de la solicitud;
- recibir fragmentos seleccionados desde el editor Python o desde la traduccion;
- explicar cada fragmento con conocimiento de su archivo completo, lineas, clase, funcion, estado y dependencias;
- enviar el codigo generado directamente al editor.

El boton de clip y el arrastre permiten adjuntar hasta cinco archivos por consulta. Se admite texto, Markdown, CSV/TSV, JSON, RTF, HTML, XML, YAML, codigo, DOCX, XLSX, PPTX, OpenDocument y PDF. PNG, JPEG y WebP se envian a Ollama para modelos con vision. Adjuntar no ejecuta una accion por si mismo: el usuario debe indicar que desea analizar, resumir, comparar, extraer o generar a partir del contenido.

El editor y el visor de traduccion tienen un menu contextual propio. Al elegir **¿Que hace, para que sirve?**, la seleccion aparece como contenido cargado en el compositor del chat, pero no se envia automaticamente. El usuario puede completar o cambiar su pregunta antes de pulsar **Enviar**. Este mecanismo no guarda respuestas ni ejemplos predefinidos: en cada consulta construye un contexto nuevo con la seleccion y una captura del archivo completo. Para selecciones hechas en la traduccion educativa tambien adjunta el Python original relacionado.

Las explicaciones contextuales usan una ventana total de hasta `32768` tokens, dentro de la cual se reservan como maximo `4096` tokens para la respuesta. Los archivos normales se entregan completos; si un archivo excede el limite interno, el backend conserva obligatoriamente la seleccion y concentra el contexto alrededor de ella. La conversacion general mantiene un limite menor y la generacion de archivos Python usa su configuracion especializada.

Cuando la IA genera codigo, el chat no debe pegar todo el codigo como respuesta principal. Debe colocarlo en el editor y mostrar un mensaje breve de confirmacion.

Comandos disponibles:

- `/ayuda`
- `/tipos`
- `/reglas`
- `/analizar`
- `/errores`
- `/tabla`
- `/explicar`
- `/corregir`
- `/GenerarPantalla`
- `/GenerarFuncion`
- `/ArreglarPantalla`
- `/AjustarPantalla`: agrega elementos a la pantalla actual y rechaza resultados que eliminen, modifiquen o reordenen codigo existente.
- `/limpiar`
- `/estado`

Tambien puede detectar peticiones naturales como:

- "quiero que hagas una pantalla para clientes"
- "crea un programa que pida dos numeros y los sume"
- "arregla el codigo actual"
- "implementa una calculadora con interfaz"

## Menus y atajos

Menus principales:

- **Archivo**: nuevo, abrir, guardar, guardar como y salir.
- **Editar**: limpiar resultados y cambiar tamano de fuente.
- **Ver**: vista previa, tabla de simbolos, analisis lexico, analisis sintactico, analisis semantico y controles para mostrar u ocultar chat, explorador y panel inferior.
- **Ejecutar**: analizar, ejecutar programa, traducir codigo y generar codigo intermedio.
- **Terminal**: mostrar consola y ejecutar en consola.
- **Ayuda**: configuracion y explicar error seleccionado con IA.

Atajos:

- `Ctrl+N`: nuevo archivo.
- `Ctrl+O`: abrir archivo.
- `Ctrl+K`: abrir carpeta.
- `Ctrl+S`: guardar.
- `Ctrl+Shift+S`: guardar como.
- `F5`: analizar.
- `F6`: ejecutar programa.
- `F7`: vista previa.
- `F8`: mostrar consola.
- `F9`: traducir codigo.
- `F10`: generar codigo intermedio.
- `Ctrl+L`: limpiar resultados.
- `Ctrl+Shift+P`: paleta de comandos generales de Miezee.
- `F1`: paleta interna de acciones del editor Monaco cuando el editor tiene el foco.
- `Ctrl+Shift+C`: mostrar u ocultar chat.
- `Ctrl+B`: mostrar u ocultar explorador.
- `Ctrl+J`: mostrar u ocultar panel inferior.

## Miezee como traduccion educativa

El boton **Traducir codigo** genera una traduccion educativa estructurada desde Python hacia Miezee.

El resultado se presenta como codigo coloreado, numerado y no modificable. Su menu contextual permite actualizar solo la traduccion actual o cargar una seleccion en el chat para solicitar una explicacion contextual.

Ejemplo:

```python
area = base * altura / 2
print(area)
```

Traduccion educativa:

```miezee
GUARDAR (base * altura / 2) EN area
MOSTRAR area
```

Esta traduccion es explicativa, no reemplaza el codigo Python real.

## Lenguaje Miezee original

El analizador Miezee original sigue dentro del proyecto para compatibilidad academica y pruebas. Incluye soporte para:

- declaraciones y asignaciones;
- entrada y salida por consola;
- funciones simples;
- flujo condicional y repetitivo;
- operaciones aritmeticas, logicas y comparativas;
- instrucciones visuales declarativas;
- guardado de datos en archivos TXT, RTF/Word, JSON y CSV.

En la aplicacion actual, el flujo recomendado para el usuario final es Python.

### Instrucciones soportadas de Miezee

Declaracion y asignacion:

```miezee
DEFINIR nombre COMO TIPO = expresion
CAMBIAR nombre A expresion
```

Entrada y salida:

```miezee
PEDIR nombre COMO TIPO
PEDIR nombre COMO TIPO CON MENSAJE "Texto para el usuario"
MOSTRAR expresion
```

Flujo de control:

```miezee
IF condicion
ELSE
FOR i DESDE 1 HASTA 10
WHILE condicion
SWITCH expresion
BREAK
CONTINUE
```

Funciones:

```miezee
FUNCION nombre RETORNA TIPO
PARAMETRO nombre COMO TIPO
RETORNAR expresion
FIN FUNCION
```

Pantallas declarativas:

```miezee
CREAR PANTALLA "Titulo"
AGREGAR CAMPO nombre COMO TIPO
AGREGAR BOTON "Texto"
AGREGAR BOTON "Texto" GUARDAR COMO TXT "archivo.txt"
AGREGAR BOTON "Texto" GUARDAR COMO WORD "archivo.rtf"
AGREGAR BOTON "Texto" GUARDAR COMO JSON "archivo.json"
AGREGAR BOTON "Texto" GUARDAR COMO CSV "archivo.csv"
MOSTRAR PANTALLA
```

### Tipos de datos de Miezee

- `ENTERO`: numeros sin decimales.
- `DECIMAL`: numeros con decimales.
- `BYTE`: entero de -128 a 127.
- `SHORT`: entero de -32768 a 32767.
- `INT`: entero de -2147483648 a 2147483647.
- `LONG`: entero de -9223372036854775808 a 9223372036854775807.
- `FLOAT`: numero de punto flotante.
- `DOUBLE`: numero decimal de mayor precision.
- `TEXTO`: cadena entre comillas.
- `CHAR`: un caracter.
- `BOOLEANO`: `VERDADERO` o `FALSO`.
- `BOOLEAN`: alias booleano; tambien acepta `true` y `false`.
- `FECHA`: valor creado con `FECHA("2026-09-10")`.
- `ARCHIVO`: valor creado con `ARCHIVO("documento.pdf")`.

### Operadores y funciones soportadas

- Aritmeticos: `+`, `-`, `*`, `/`, `^`, `**`.
- Comparacion: `<`, `<=`, `>`, `>=`, `==`, `!=`.
- Logicos: `Y`, `O`, `NO`.
- Funcion matematica: `sqrt(valor)`.

### Reglas semanticas de Miezee

- `RT01`: `ENTERO` con `ENTERO` mediante `+`, `-` o `*` produce `ENTERO`; la division produce `DECIMAL`.
- `RT02`: una operacion entre `ENTERO` y `DECIMAL` produce `DECIMAL`.
- `RT03`: `TEXTO + TEXTO` produce `TEXTO`.
- `RT04`: comparaciones numericas e igualdad compatible producen `BOOLEANO`.
- `RT05`: operadores logicos `Y`, `O`, `NO` requieren valores booleanos.
- `RT06`: `ARCHIVO` y `FECHA` no pueden utilizarse en operaciones aritmeticas.
- `RT07`: `BYTE`, `SHORT`, `INT` y `LONG` respetan sus rangos permitidos.
- `RT08`: `sqrt(valor)` requiere exactamente un argumento numerico y produce `DOUBLE`.
- `RI01`: un identificador debe declararse antes de utilizarse.
- `RI02`: no se puede declarar dos veces el mismo identificador.
- `RI03`: las palabras reservadas no pueden utilizarse como identificadores.
- `RI04`: el valor inicial y las asignaciones deben ser compatibles con el tipo declarado.
- `RI05`: el tipo del identificador permanece fijo despues de la declaracion.
- `RV01`: una pantalla debe crearse antes de agregar campos o botones.
- `RV02`: los campos visuales deben tener nombres validos y tipos permitidos.
- `RV03`: `MOSTRAR PANTALLA` requiere una pantalla creada.
- `RV04`: un boton puede guardar datos en `TXT`, `WORD`, `JSON` o `CSV`.
- `RF01`: `IF` y `WHILE` requieren condiciones booleanas.
- `RF02`: `FOR` requiere limites numericos.
- `RF04`: `SWITCH` requiere un valor discreto o comparable.
- `RF05`: `BREAK` y `CONTINUE` controlan el flujo dentro de bucles o selecciones.
- `RFN01`: una funcion debe declararse con nombre y tipo de retorno.
- `RFN02`: los parametros pertenecen a una funcion activa.
- `RFN03`: `RETORNAR` debe ser compatible con el tipo de retorno de la funcion.
- `RFN04`: `FIN FUNCION` cierra una funcion activa.
- `RIN01`: `PEDIR` declara una entrada que se captura desde la consola interactiva.

### Errores semanticos de Miezee

- `ES01`: identificador no declarado o instruccion usada sin contexto requerido. Ejemplos: usar una variable no declarada, agregar un campo sin pantalla o usar `RETORNAR` fuera de una funcion.
- `ES02`: identificador duplicado. Ejemplos: declarar dos veces la misma variable, funcion, parametro o campo visual.
- `ES03`: operacion, estructura o sintaxis minima incompatible. Ejemplos: sumar `ARCHIVO`, usar tipos incorrectos en una condicion, declarar una funcion dentro de otra o usar una forma invalida de instruccion.
- `ES04`: asignacion o retorno incompatible. Ejemplos: iniciar una variable con un tipo incorrecto, retornar un tipo diferente al declarado o usar valores fuera del rango de `BYTE`, `SHORT`, `INT` o `LONG`.
- `ES05`: uso de una palabra reservada como identificador. Ejemplos: usar `IF`, `MOSTRAR`, `ENTERO` o `FUNCION` como nombre de variable, campo, parametro o funcion.

Cada error incluye codigo, linea, instruccion, explicacion, regla incumplida, sugerencia, identificadores relacionados, tipos involucrados y operador cuando aplica.

### Ejemplo Miezee completo

```miezee
PEDIR base COMO double CON MENSAJE "Ingresa la base:"
PEDIR altura COMO double CON MENSAJE "Ingresa la altura:"
DEFINIR area COMO double = base * altura / 2
MOSTRAR area
```

## Estructura del proyecto

- `app.py`: punto de entrada de desarrollo para la aplicacion Tauri.
- `frontend/src/`: interfaz React, modelos, controladores, vistas y servicios.
- `frontend/src/views/CodeEditor.tsx`: editor Python y menu contextual de edicion y explicacion.
- `frontend/src/views/TranslationView.tsx`: visor educativo de solo lectura y seleccion contextual.
- `frontend/src-tauri/`: ventana nativa, dialogos, procesos y puente con Python.
- `miezee/core/python_analyzer.py`: analizador seguro para Python.
- `miezee/core/python_executor.py`: ejecutor auxiliar para pruebas de consola.
- `miezee/core/python_translator.py`: traduccion educativa estructurada de Python a Miezee.
- `miezee/core/semantic_analyzer.py`: analizador del lenguaje Miezee original.
- `miezee/core/parser.py`: parser del lenguaje Miezee original.
- `miezee/core/lexer.py`: lexer del lenguaje Miezee original.
- `miezee/core/data_types.py`: tipos y compatibilidad.
- `miezee/core/symbol_table.py` y `miezee/core/symbol.py`: tabla de simbolos.
- `miezee/core/errors.py`: errores semanticos.
- `miezee/ai/ai_client.py`: cliente local de Ollama.
- `miezee/backend/chat_service.py`: construccion de contexto, generacion validada y explicaciones de selecciones.
- `miezee/ai/chat_commands.py`: comandos locales del chat.
- `miezee/ai/system_prompt.py`: instrucciones base para la IA local.
- `miezee/services/settings_service.py`: carga de `.env`.
- `miezee/services/file_service.py`: lectura y escritura de archivos.
- `examples/`: casos de prueba Python renovados, de 10 a 15 lineas cada uno.

## Casos de prueba incluidos

Los ejemplos principales del proyecto estan en Python:

- `examples/correcto_consola.py`: programa interactivo con calculos numericos.
- `examples/correcto_funciones.py`: funcion con parametros, retorno y salida.
- `examples/pantalla_empleados.py`: pantalla sencilla con `tkinter`.
- `examples/error_importacion.py`: caso invalido por importacion no permitida.
- `examples/error_llamada_peligrosa.py`: caso invalido por uso de `eval`.
- `examples/error_sintaxis.py`: caso invalido por sintaxis Python incorrecta.

## Archivos temporales

El IDE no debe dejar archivos temporales visibles en el proyecto. La ejecucion actual usa memoria con `python -c`.

Si aparecen archivos antiguos como:

- `.miezee_run_tmp.py`
- `.miezee_preview_tmp.py`

pueden eliminarse. Estan incluidos en `.gitignore`.

## Verificacion

Ejecuta desde la raiz del proyecto:

```powershell
cd frontend
npm run build
cargo test --manifest-path src-tauri/Cargo.toml
```

Estas comprobaciones cubren:

- compilacion de React y TypeScript;
- integracion nativa de Tauri;
- ejecucion interactiva con entrada y salida Unicode;
- detencion de procesos;
- proteccion del codigo fuente en el explorador.

## Limitaciones actuales

- La IA local no tiene acceso a Internet desde la aplicacion.
- La vista previa abre interfaces como ventana separada; no incrusta la GUI dentro del panel.
- La traduccion a Miezee es educativa, estructurada y no ejecutable; Python sigue siendo el lenguaje original.
- El modo seguro bloquea librerias y llamadas peligrosas, por lo que no todo codigo Python arbitrario sera aceptado.
- Las bases de datos estan pensadas para `sqlite3`; no hay conexion visual avanzada a motores externos.

## Guion sugerido para demostracion

1. Abrir la aplicacion con `python app.py`.
2. Explicar que Python es el lenguaje principal y Miezee queda como traduccion educativa.
3. Pedir al chat una calculadora o un programa de consola.
4. Mostrar que el codigo aparece en el editor.
5. Analizar con `F5`.
6. Ejecutar con `F6` y usar la consola interactiva.
7. Pedir una pantalla sencilla y abrirla con `F7`.
8. Mostrar la tabla de simbolos.
9. Usar **Traducir codigo** para ver la representacion educativa en Miezee.
10. Verificar el frontend con `npm run build` desde `frontend`.

## Estado verificado

Ultima verificacion local:

```powershell
cd frontend
npm run build
cargo test --manifest-path src-tauri/Cargo.toml
```

Resultado esperado actual: frontend y puente nativo compilando correctamente.
