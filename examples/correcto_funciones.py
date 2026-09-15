def calcular_total(precio, cantidad, impuesto):
    subtotal = precio * cantidad
    total = subtotal + impuesto
    return total

producto = "Teclado"
precio = 350.50
cantidad = 2
impuesto = 56.08
total = calcular_total(precio, cantidad, impuesto)
print(producto, total)
