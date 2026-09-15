import os

carpeta = "."
archivos = os.listdir(carpeta)
total = len(archivos)
print("Archivos encontrados:", total)
if total > 0:
    print("Hay archivos")
else:
    print("No hay archivos")
