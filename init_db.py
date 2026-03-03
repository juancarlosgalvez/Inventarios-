import mysql.connector

print("Conectando a MySQL...")

conn = mysql.connector.connect(
    host="localhost",
    user="admin",
    password="admin",
)

cursor = conn.cursor()

cursor.execute("CREATE DATABASE IF NOT EXISTS inventario_dbv1;")

print("Base de datos 'inventario_dbv1' creada o ya existente.")

cursor.close()
conn.close()
