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
- Datos: `ASSIGN`, `ASSIGN_TYPED`, `BUILD_LIST`, `BUILD_DICT`, `GET_ITEM`.
- Control: `LABEL`, `GOTO`, `IF_FALSE_GOTO`, `IF_TRUE_GOTO`, `ITER_INIT`, `ITER_NEXT`.
- Funciones: `FUNC_BEGIN`, `PARAM_DEF`, `PARAM_DEFAULT`, `ARG`, `ARG_NAMED`, `CALL`, `RETURN`, `FUNC_END`.
- Estructuras: `CLASS_BEGIN`, `CLASS_END`, `TRY_BEGIN`, `CATCH`, `FINALLY`, `RESOURCE_OPEN`.
- Compatibilidad: `PYTHON_STMT` y `PYTHON_EXPR` conservan construcciones nuevas sin descartarlas.

Los booleanos usan saltos para conservar el cortocircuito de Python. En ciclos con `else`, los saltos por `break` evitan correctamente el bloque `else`.

## Condiciones de generacion

El backend ejecuta primero los analisis lexico, sintactico y semantico. Si existe un error, devuelve un resultado fallido y no produce instrucciones TAC. La compilacion a AST y bytecode se realiza sin ejecutar el programa del usuario.
