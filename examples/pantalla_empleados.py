import tkinter as tk

root = tk.Tk()
root.title("Registro de empleados")
tk.Label(root, text="Nombre").pack()
nombre = tk.Entry(root)
nombre.pack()
tk.Label(root, text="Edad").pack()
edad = tk.Entry(root)
edad.pack()
tk.Button(root, text="Guardar").pack()
root.mainloop()
