#una lista es una coleccion de datos que pueden ser de diferentes tipos.

mi_lista = [1, 2, 3, "cuatro", "cinco",[1,22,55,], 6.0, True]  #se crea una lista con diferentes tipos de datos
print(mi_lista)  #se imprime la lista completa
print(mi_lista[3])  #se imprime el cuarto elemento de la lista
print(mi_lista[5][2])  #se imprime el tercer elemento de la sublista    


#tuplas son similares a las listas pero son inmutables (no se pueden modificar).
#y se crean con parentesis ().

mi_tupla = (1, 2, 3, "cuatro", "cinco", (1, 22, 55), 6.0, True)  #se crea una tupla con diferentes tipos de datos
print(mi_tupla)  #se imprime la tupla completa  
print(mi_tupla[3])  #se imprime el cuarto elemento de la tupla
print(mi_tupla[5][2])  #se imprime el tercer elemento de la subtupla

#conjuntos son colecciones desordenadas de elementos unicos.
#se crean con llaves {}.    
mi_conjunto = {1, 2, 3, "cuatro", "cinco", 6.0, True}  #se crea un conjunto con diferentes tipos de datos
print(mi_conjunto)  #se imprime el conjunto completo
#no se puede acceder a los elementos de un conjunto por su indice ya que no tienen orden.

#diccionarios son colecciones de pares clave-valor.
#se crean con llaves {} y los pares clave-valor se separan con dos puntos :.
mi_diccionario = {"nombre": "Juan", "edad": 30, "ciudad": "Madrid"}  #se crea un diccionario con pares clave-valor
print(mi_diccionario)  #se imprime el diccionario completo  
print(mi_diccionario["nombre"])  #se imprime el valor asociado a la clave "nombre"
print(mi_diccionario["edad"])  #se imprime el valor asociado a la clave "edad"
print(mi_diccionario["ciudad"])  #se imprime el valor asociado a la clave "ciudad"
#se pueden agregar nuevos pares clave-valor al diccionario
mi_diccionario["pais"] = "España"  #se agrega un nuevo par clave-valor
print(mi_diccionario)  #se imprime el diccionario completo con el nuevo par clave-valor


