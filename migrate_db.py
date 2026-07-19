"""
migrate_db.py
Corre esto UNA SOLA VEZ antes de volver a usar main.py o app.py, para
actualizar la estructura de tu tabla 'precios_mercado' en AWS RDS:

  1. Agrega la columna imagen_url (para mostrar la foto del producto en la
     nueva interfaz).
  2. Agrega un índice UNIQUE (componente_id, tienda, url_producto) para que
     insertar_precio() pueda hacer UPSERT en vez de crear filas duplicadas
     cada vez que corres main.py (el problema de "Plazavea x3" que salía
     en tu captura de pantalla).

Es seguro correrlo más de una vez: si la columna o el índice ya existen,
simplemente lo avisa y sigue.

Uso:
    python migrate_db.py
"""

from db import get_connection

conexion = get_connection()
cursor = conexion.cursor()

# --- 1. Columna imagen_url -------------------------------------------------
try:
    cursor.execute("ALTER TABLE precios_mercado ADD COLUMN imagen_url VARCHAR(500) NULL")
    print("✅ Columna 'imagen_url' agregada.")
except Exception as e:
    if "Duplicate column name" in str(e):
        print("ℹ️  La columna 'imagen_url' ya existía, no se hizo nada.")
    else:
        print(f"[ERROR] No se pudo agregar 'imagen_url': {e}")

# --- 2. (Opcional pero recomendado) limpiar duplicados existentes ---------
# Antes de crear el índice único, si ya tienes filas duplicadas (como las
# 3 de Plazavea en tu captura), hay que borrarlas o el ALTER va a fallar.
cursor.execute(
    """
    DELETE p1 FROM precios_mercado p1
    INNER JOIN precios_mercado p2
    WHERE
        p1.id < p2.id
        AND p1.componente_id = p2.componente_id
        AND p1.tienda = p2.tienda
        AND p1.url_producto = p2.url_producto
    """
)
print(f"🧹 Filas duplicadas eliminadas: {cursor.rowcount}")

# --- 3. Índice único --------------------------------------------------------
try:
    cursor.execute(
        """ALTER TABLE precios_mercado
           ADD UNIQUE KEY uq_componente_tienda_url (componente_id, tienda, url_producto(255))"""
    )
    print("✅ Índice único agregado (evita futuros duplicados).")
except Exception as e:
    if "Duplicate key name" in str(e):
        print("ℹ️  El índice único ya existía, no se hizo nada.")
    else:
        print(f"[ERROR] No se pudo agregar el índice único: {e}")

conexion.commit()
cursor.close()
conexion.close()
print("\nMigración terminada.")
