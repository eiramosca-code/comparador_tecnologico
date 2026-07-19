"""
db.py
Módulo centralizado para conectarse a la base de datos MySQL en AWS RDS.
Todos los scrapers importan get_connection() desde aquí en vez de
repetir la conexión en cada archivo.
"""

import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()  # lee el archivo .env

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "port": int(os.getenv("DB_PORT", 3306)),
}


def get_connection():
    """Crea y devuelve una nueva conexión a la base de datos."""
    try:
        conexion = mysql.connector.connect(**DB_CONFIG)
        return conexion
    except Error as e:
        print(f"[ERROR] No se pudo conectar a la base de datos: {e}")
        raise


def obtener_o_crear_componente(cursor, nombre_modelo, categoria):
    """
    Busca un componente por nombre_modelo (columna UNIQUE en tu tabla).
    Si no existe, lo crea. Devuelve el id del componente (para usarlo como
    componente_id en precios_mercado).

    Columnas reales verificadas en tu tabla 'componentes':
    id, nombre_modelo (UNIQUE), categoria, score_benchmark
    """
    cursor.execute(
        "SELECT id FROM componentes WHERE nombre_modelo = %s LIMIT 1",
        (nombre_modelo,),
    )
    fila = cursor.fetchone()
    if fila:
        return fila[0]

    cursor.execute(
        "INSERT INTO componentes (nombre_modelo, categoria) VALUES (%s, %s)",
        (nombre_modelo, categoria),
    )
    return cursor.lastrowid


def actualizar_score_benchmark(cursor, nombre_modelo, score):
    """Actualiza el score_benchmark de un componente ya existente."""
    cursor.execute(
        "UPDATE componentes SET score_benchmark = %s WHERE nombre_modelo = %s",
        (score, nombre_modelo),
    )


def insertar_precio(cursor, componente_id, tienda, precio_soles, url_producto, imagen_url=None):
    """
    Inserta o actualiza un registro de precio para un componente.

    Antes esto SIEMPRE hacía INSERT, así que si corrías main.py varias veces
    ibas acumulando filas duplicadas (mismo componente + misma tienda +
    mismo precio repetido, como se ve en tu captura con Plazavea 3 veces).
    Ahora hacemos un UPSERT: si ya existe una fila para ese
    (componente_id, tienda, url_producto), actualizamos el precio, la
    imagen y la fecha en vez de crear una fila nueva.

    Requiere un índice UNIQUE en (componente_id, tienda, url_producto).
    Si tu tabla todavía no lo tiene, corre migrate_db.py una vez.
    """
    cursor.execute(
        """INSERT INTO precios_mercado
           (componente_id, tienda, precio_soles, url_producto, imagen_url, fecha_registro)
           VALUES (%s, %s, %s, %s, %s, NOW())
           ON DUPLICATE KEY UPDATE
               precio_soles = VALUES(precio_soles),
               imagen_url = VALUES(imagen_url),
               fecha_registro = NOW()""",
        (componente_id, tienda, precio_soles, url_producto, imagen_url),
    )
