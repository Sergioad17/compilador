RESERVED_WORDS = {
    "DEFINIR",
    "COMO",
    "CAMBIAR",
    "A",
    "MOSTRAR",
    "ENTERO",
    "DECIMAL",
    "TEXTO",
    "BOOLEANO",
    "BYTE",
    "SHORT",
    "INT",
    "LONG",
    "FLOAT",
    "DOUBLE",
    "CHAR",
    "BOOLEAN",
    "FECHA",
    "ARCHIVO",
    "VERDADERO",
    "FALSO",
    "Y",
    "O",
    "NO",
    "CREAR",
    "PANTALLA",
    "AGREGAR",
    "CAMPO",
    "BOTON",
    "GUARDAR",
    "TXT",
    "WORD",
    "JSON",
    "CSV",
    "TRUE",
    "FALSE",
    "IF",
    "ELSE",
    "FOR",
    "DESDE",
    "HASTA",
    "WHILE",
    "SWITCH",
    "BREAK",
    "CONTINUE",
    "FUNCION",
    "RETORNA",
    "PARAMETRO",
    "RETORNAR",
    "FIN",
    "PEDIR",
    "CON",
    "MENSAJE",
}

RULES = {
    "RT01": "ENTERO con ENTERO mediante +, - o * produce ENTERO. La division produce DECIMAL.",
    "RT02": "Una operacion entre ENTERO y DECIMAL produce DECIMAL.",
    "RT03": "TEXTO + TEXTO produce TEXTO.",
    "RT04": "Una comparacion entre valores numericos o igualdad entre tipos iguales produce BOOLEANO.",
    "RT05": "BOOLEANO Y/O BOOLEANO produce BOOLEANO. NO BOOLEANO produce BOOLEANO.",
    "RT06": "ARCHIVO y FECHA no pueden utilizarse en operaciones aritmeticas.",
    "RT07": "Los tipos enteros byte, short, int y long tienen rangos definidos.",
    "RI01": "El identificador debe declararse antes de utilizarse.",
    "RI02": "No se puede declarar dos veces el mismo identificador.",
    "RI03": "Las palabras reservadas no pueden utilizarse como identificadores.",
    "RI04": "El valor inicial y las asignaciones deben ser compatibles con el tipo declarado.",
    "RI05": "El tipo del identificador permanece fijo despues de la declaracion.",
    "RV01": "Una pantalla debe crearse antes de agregar campos o botones.",
    "RV02": "Los campos visuales deben tener nombres validos y tipos permitidos.",
    "RV03": "MOSTRAR PANTALLA requiere una pantalla creada.",
    "RV04": "Un boton puede guardar datos en TXT, WORD, JSON o CSV.",
    "RF01": "IF y WHILE requieren condiciones booleanas.",
    "RF02": "FOR requiere limites numericos.",
    "RF04": "SWITCH requiere un valor discreto o comparable.",
    "RF05": "BREAK y CONTINUE controlan el flujo dentro de bucles o selecciones.",
    "RFN01": "Una funcion debe declararse con nombre y tipo de retorno.",
    "RFN02": "Los parametros pertenecen a una funcion activa.",
    "RFN03": "RETORNAR debe ser compatible con el tipo de retorno de la funcion.",
    "RFN04": "FIN FUNCION cierra una funcion activa.",
    "RIN01": "PEDIR declara una entrada que se captura desde la consola interactiva.",
}

TYPE_HELP = """Tipos de datos de Miezee:
- ENTERO: numeros sin decimales, por ejemplo 25.
- DECIMAL: numeros con decimales, por ejemplo 8500.50.
- BYTE, SHORT, INT, LONG: enteros con diferentes rangos.
- FLOAT, DOUBLE: numeros de punto flotante.
- TEXTO: cadenas entre comillas, por ejemplo "Maria".
- CHAR: un caracter entre comillas, por ejemplo "A".
- BOOLEANO: VERDADERO o FALSO.
- BOOLEAN: alias de BOOLEANO; tambien acepta true y false.
- FECHA: FECHA("2026-09-10").
- ARCHIVO: ARCHIVO("contrato.pdf")."""

RULES_HELP = "\n".join(f"{code}: {text}" for code, text in RULES.items())
