# Miezee educativo

Miezee educativo es una representacion legible de un programa Python. No se ejecuta, no sustituye al archivo Python y no se usa para generar la interfaz final. Su finalidad es explicar al usuario que hace el programa original.

## Contrato

- La entrada debe superar el analisis lexico y sintactico oficial de Python.
- Cada instruccion Python produce una instruccion educativa o el contenedor universal `INSTRUCCION PYTHON '...'`.
- Cada expresion avanzada que no tiene una equivalencia sencilla se conserva como `PYTHON('...')`.
- Los bloques siempre tienen un final explicito y usan sangria de cuatro espacios.
- Las cadenas conservan su representacion para evitar interpretar su contenido como instrucciones.
- Los detalles internos de Python como `self`, `__init__`, `grid`, `pack`, `get` y `delete` se expresan por su intencion cuando el contexto permite identificarla.
- Las funciones sin valor de retorno se muestran como `PROCEDIMIENTO`; los constructores se muestran como `AL CREAR`.
- No se muestra `INFERIDO` como ruido visual: cuando el tipo no puede deducirse con seguridad, se explica la asignacion con `GUARDAR valor EN destino`.
- Las operaciones conocidas de interfaz, cuadros de dialogo, SQLite, archivos y conversiones usan frases educativas especificas.

## Gramatica estructural (EBNF)

La sangria se representa con `INDENT` y `DEDENT`, de la misma forma conceptual que Python.

```ebnf
programa       = bloque ;
bloque         = { instruccion } ;
instruccion    = simple | seleccion | para | mientras | casos | funcion | constructor
               | clase | excepcion | recurso | universal ;

seleccion      = "SI ", contenido, " ENTONCES", NL, INDENT, bloque, DEDENT,
                 { "SINO SI ", contenido, " ENTONCES", NL, INDENT, bloque, DEDENT },
                 [ "SINO", NL, INDENT, bloque, DEDENT ], "FIN SI", NL ;
para           = ( "PARA CADA " | "PARA CADA ASINCRONO " ), contenido, " HACER", NL,
                 INDENT, bloque, DEDENT,
                 [ "SI EL CICLO TERMINA SIN BREAK", NL, INDENT, bloque, DEDENT ],
                 "FIN PARA", NL ;
mientras       = "MIENTRAS ", contenido, " HACER", NL, INDENT, bloque, DEDENT,
                 [ "SI EL CICLO TERMINA SIN BREAK", NL, INDENT, bloque, DEDENT ],
                 "FIN MIENTRAS", NL ;
casos          = "SEGUN ", contenido, NL,
                 { "CASO ", contenido, NL, INDENT, bloque, DEDENT }, "FIN SEGUN", NL ;
funcion        = { "DECORADOR ", contenido, NL },
                 ( "FUNCION " | "FUNCION ASINCRONA " | "PROCEDIMIENTO "
                 | "PROCEDIMIENTO ASINCRONO " ), contenido, NL,
                 INDENT, bloque, DEDENT, ( "FIN FUNCION" | "FIN PROCEDIMIENTO" ), NL ;
constructor    = "AL CREAR ", contenido, NL, INDENT, bloque, DEDENT,
                 "FIN CREACION", NL ;
clase          = { "DECORADOR ", contenido, NL }, "CLASE ", contenido, NL,
                 INDENT, bloque, DEDENT, "FIN CLASE", NL ;
excepcion      = "INTENTAR", NL, INDENT, bloque, DEDENT,
                 { "CAPTURAR ", contenido, NL, INDENT, bloque, DEDENT },
                 [ "SI NO HAY ERROR", NL, INDENT, bloque, DEDENT ],
                 [ "FINALMENTE", NL, INDENT, bloque, DEDENT ], "FIN INTENTAR", NL ;
recurso        = ( "USAR RECURSO " | "USAR RECURSO ASINCRONO " ), contenido, NL,
                 INDENT, bloque, DEDENT, "FIN RECURSO", NL ;

simple         = palabra_simple, [ " ", contenido ], NL ;
palabra_simple = "DEFINIR" | "GUARDAR" | "ASIGNAR" | "PEDIR" | "MOSTRAR" | "IMPORTAR"
               | "DESDE" | "CAMBIAR" | "RETORNAR" | "LANZAR" | "VERIFICAR"
               | "ELIMINAR" | "USAR" | "ROMPER" | "CONTINUAR" | "NO"
               | "EVALUAR" | "LLAMAR" | "CREAR" | "UBICAR" | "CONFIGURAR"
               | "AGREGAR" | "CONECTAR" | "EJECUTAR" | "CONFIRMAR"
               | "DESHACER" | "CERRAR" | "ESCRIBIR" | "LEER" | "CONVERTIR"
               | "PREPARAR" | "INICIAR" | "ABRIR" ;
universal      = "INSTRUCCION PYTHON ", cadena, NL ;
expresion      = contenido | "PYTHON(", cadena, ")" ;
contenido      = caracter, { caracter } ;
comentario     = "#", { caracter }, NL ;
cadena         = cadena_python_escapada ;
caracter       = ? cualquier caracter Unicode excepto salto de linea ? ;
NL             = ? salto de linea ? ;
INDENT         = ? cuatro espacios adicionales ? ;
DEDENT         = ? regreso al nivel de sangria anterior ? ;
```

La alternativa universal hace que construcciones incorporadas por versiones futuras de Python sigan apareciendo sin perder el codigo original. Cuando una construccion obtiene una equivalencia educativa propia, puede reemplazarse sin cambiar el lenguaje ejecutable.

## Dominios explicados

- Interfaces: ventanas, etiquetas, botones, entradas, contenedores, posicionamiento y ciclo visual.
- Bases de datos: conexion SQLite, cursores, consultas, lectura de resultados y transacciones.
- Archivos: apertura mediante recursos, lectura, escritura y cierre.
- Consola: solicitud y presentacion de valores.
- Python general: modulos, colecciones, funciones, clases, excepciones, asincronia y control de flujo.
