import unittest

from miezee.core.python_translator import PythonToMiezeeTranslator


class CompletePythonTranslatorTest(unittest.TestCase):
    def setUp(self):
        self.translator = PythonToMiezeeTranslator()

    def test_nested_if_elif_else_and_loops_have_explicit_boundaries(self):
        source = """for numero in range(5):
    if numero == 0:
        print('cero')
    elif numero > 2:
        while numero > 0:
            numero -= 1
    else:
        continue
"""
        text = self.translator.translate(source)
        self.assertIn("PARA CADA numero EN range(5) HACER", text)
        self.assertIn("SINO SI", text)
        self.assertIn("SINO", text)
        self.assertIn("FIN MIENTRAS", text)
        self.assertIn("FIN SI", text)
        self.assertIn("FIN PARA", text)

    def test_match_cases_classes_and_exceptions_are_translated(self):
        source = """class Servicio:
    def ejecutar(self, comando):
        try:
            match comando:
                case 'guardar':
                    return True
                case _:
                    raise ValueError('desconocido')
        except ValueError as error:
            print(error)
        finally:
            print('fin')
"""
        text = self.translator.translate(source)
        for phrase in ["CLASE Servicio", "FUNCION ejecutar", "INTENTAR", "SEGUN comando", "CASO 'guardar'", "CAPTURAR ValueError COMO error", "FINALMENTE", "FIN CLASE"]:
            self.assertIn(phrase, text)

    def test_collections_modules_and_comprehensions_remain_explainable(self):
        source = """from pathlib import Path
datos = [1, 2, 3]
config = {'activo': True}
unicos = {1, 2}
dobles = [n * 2 for n in datos]
"""
        text = self.translator.translate(source)
        self.assertIn("DESDE MODULO pathlib IMPORTAR Path", text)
        self.assertIn("COMO LISTA", text)
        self.assertIn("DICCIONARIO{'activo': VERDADERO}", text)
        self.assertIn("CONJUNTO{1, 2}", text)
        self.assertIn("PYTHON('[n * 2 for n in datos]')", text)
        self.assertNotIn("Sin traduccion directa", text)

    def test_interfaces_database_files_and_console_use_educational_terms(self):
        source = """import tkinter as tk
import sqlite3
nombre = input('Nombre: ')
ventana = tk.Tk()
etiqueta = tk.Label(ventana, text=nombre)
etiqueta.pack()
conexion = sqlite3.connect('datos.db')
cursor = conexion.cursor()
cursor.execute('SELECT * FROM personas')
with open('salida.txt', 'w') as archivo:
    archivo.write(nombre)
conexion.commit()
ventana.mainloop()
"""
        text = self.translator.translate(source)
        for phrase in ["PEDIR nombre COMO TEXTO", "CREAR VENTANA ventana", "CREAR ETIQUETA etiqueta", "UBICAR etiqueta", "ABRIR BASE_DATOS conexion", "CREAR CURSOR cursor", "EJECUTAR SQL", "USAR RECURSO open", "ESCRIBIR EN archivo", "CONFIRMAR CAMBIOS", "INICIAR CICLO DE INTERFAZ ventana"]:
            self.assertIn(phrase, text)

    def test_translation_is_explicitly_non_executable(self):
        text = self.translator.translate("valor = 1")
        self.assertTrue(text.startswith("# MIEZEE EDUCATIVO - traduccion no ejecutable"))

    def test_pyside_interface_and_function_defaults_are_explained(self):
        source = """from PySide6.QtWidgets import QApplication, QWidget, QPushButton
def crear(titulo: str = 'Demo', *, ancho: int = 400):
    app = QApplication([])
    ventana = QWidget()
    boton = QPushButton('Guardar')
    boton.clicked.connect(ventana.show)
    ventana.setWindowTitle(titulo)
    ventana.resize(ancho, 300)
    ventana.show()
    app.exec()
"""
        text = self.translator.translate(source)
        self.assertIn("titulo COMO TEXTO = 'Demo'", text)
        self.assertIn("ancho COMO ENTERO = 400", text)
        self.assertIn("CREAR APLICACION app", text)
        self.assertIn("CREAR VENTANA ventana", text)
        self.assertIn("CREAR BOTON boton", text)
        self.assertIn("CONECTAR EVENTO boton.clicked", text)
        self.assertIn("MOSTRAR INTERFAZ ventana", text)
        self.assertIn("INICIAR CICLO DE INTERFAZ app", text)

    def test_collection_methods_are_not_misidentified_as_interface_actions(self):
        text = self.translator.translate("datos = []\ndatos.append(1)\nvalor = datos.get(0)")
        self.assertIn("LLAMAR datos.append (1)", text)
        self.assertNotIn("CAMBIAR VALOR DE INTERFAZ datos", text)
        self.assertNotIn("LEER VALOR DE INTERFAZ datos", text)


if __name__ == "__main__":
    unittest.main()
