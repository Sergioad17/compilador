base = float(input("Ingresa la base: "))
altura = float(input("Ingresa la altura: "))
area = base * altura / 2
hipotenusa = (base ** 2 + altura ** 2) ** 0.5
perimetro = base + altura + hipotenusa
print("Area:", area)
print("Hipotenusa:", hipotenusa)
print("Perimetro:", perimetro)
if area > 0:
    print("Calculo correcto")
