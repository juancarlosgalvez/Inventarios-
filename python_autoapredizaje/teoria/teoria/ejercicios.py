"""
Escriba un programa que pregunte una
y otra vez si desea continuar
con el programa, siempre que se conteste exactamente sí
"""

"""
ejercicios.py #1
respuesta = "si"
while respuesta == "si":
    respuesta = input("¿Desea continuar con el programa? (sí/no): ")
    
    if respuesta != "si":
        print("Respuesta no válida. Por favor, responda 'sí' o 'no'.")
        
    else:
        print("Continuando con el programa...")
"""
        
# ejercicios.py #2
"""Escriba un programa que simule una hucha. 
El programa solicitará primero una cantidad, que será la cantidad de dinero que 
queremos ahorrar.
A continuación, el programa solicitará una y otra 
vez las cantidades que se irán ahorrando, hasta que el total ahorrado iguale o
supere al objetivo. 
El programa no comprobará que las cantidades sean positivas."""

"""objetivo= float(input("¿Cuál es la cantidad que desea ahorrar? "))

ahorrado = 0.0

while ahorrado <= objetivo:
    cantidad = float(input("Ingrese la cantidad a ahorrar: "))
    ahorrado += cantidad #se incrementa ahorrado en la cantidad ingresada
    print(f"Total ahorrado hasta ahora: {ahorrado}")    """
    
    
    
    
numer = 50

while numer != 0:
    print("El número es:", numer, "y bajando a 0")
    numer -= 1