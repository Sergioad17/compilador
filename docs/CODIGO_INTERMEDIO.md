# Codigo intermedio de Python

Miezee genera una representacion de tres direcciones (TAC) a partir del AST del archivo Python activo. Esta salida sirve para estudiar el proceso de compilacion: no es Python ejecutable, no reemplaza el archivo original y no se envia a `exec`.

## Formato

```text
indice | (operacion, argumento1, argumento2, resultado) | linea de origen
```

Ejemplo:

```text
0001 | (MULT, precio, cantidad, t1) | 1
0002 | (ADD, t1, impuesto, t2) | 1
0003 | (ASSIGN, t2, _, total) | 1
```

Los nombres `t1`, `t2`, etc. son temporales. Las etiquetas `L_*` delimitan bifurcaciones y ciclos.

## Operaciones principales

- Aritmetica, comparacion y logica: `ADD`, `SUB`, `MULT`, `DIV`, `EQ`, `GT`, `NOT`, entre otras.
- Datos: `ASSIGN`, `ASSIGN_TYPED`, `BUILD_LIST`, `BUILD_DICT`, `GET_ITEM`, `SET_ITEM`, `GET_ATTR`, `SET_ATTR` y operaciones de desempaquetado.
- Control: `LABEL`, `GOTO`, `IF_FALSE_GOTO`, `IF_TRUE_GOTO`, `ITER_INIT`, `ITER_NEXT` y sus variantes asincronas.
- Funciones: `FUNC_BEGIN`, tipos de parametros, valores predeterminados, `*args`, `**kwargs`, `ARG`, `CALL`, `RETURN` y decoradores.
- Estructuras: clases, `match/case`, `try/except/else/finally`, recursos `with`, comprensiones, lambdas, f-strings, `await` y `yield`.
- Compatibilidad: `PYTHON_STMT` y `PYTHON_EXPR` conservan construcciones nuevas sin descartarlas.

Los booleanos usan saltos para conservar el cortocircuito de Python. Las comparaciones encadenadas evaluan una sola vez cada operando y detienen la cadena al fallar. En ciclos con `else`, los saltos por `break` evitan correctamente el bloque `else`.

Las colecciones evaluan sus elementos en orden, las asignaciones aumentadas no repiten la evaluacion de atributos o indices y las excepciones distinguen las rutas atendida, no atendida, `else` y `finally`.

Cada resultado incluye metadatos de formato, version, lenguaje de origen, cantidad de lineas e instrucciones. Antes de entregar el TAC se comprueba que no existan etiquetas duplicadas ni saltos hacia etiquetas inexistentes.

## Condiciones de generacion

El generador y el backend ejecutan primero los analisis lexico, sintactico y semantico. Si existe un error, devuelven un resultado fallido y no producen instrucciones TAC. Las advertencias semanticas conservadoras no bloquean la generacion. La compilacion a AST y bytecode se realiza sin ejecutar el programa del usuario.

La salida TAC es una representacion educativa, no un bytecode ejecutable. Las construcciones futuras que todavia no tengan una reduccion dedicada se conservan explicitamente como `PYTHON_STMT` o `PYTHON_EXPR` en lugar de desaparecer.
