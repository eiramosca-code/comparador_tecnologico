from db import get_connection

# Conexión a tu BD AWS (usa las credenciales del .env, igual que main.py)
conexion = get_connection()
cursor = conexion.cursor()

# Borramos primero las tablas hijas por las restricciones de llave foránea (Foreign Keys)
cursor.execute("DELETE FROM precios_mercado")
cursor.execute("DELETE FROM componentes")

conexion.commit()
print("¡Base de datos limpia y lista para una nueva carga!")
cursor.close()
conexion.close()