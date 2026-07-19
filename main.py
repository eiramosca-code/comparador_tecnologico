"""
main.py
Orquesta el proceso ETL completo arreglando la unificación de componente_id.
"""

import time
import random

from db import get_connection, obtener_o_crear_componente, actualizar_score_benchmark, insertar_precio
from scraper_knasta import buscar_productos
from scraper_versus import obtener_score_por_slug

TERMINOS_A_BUSCAR = {
    "procesador": [
        {"busqueda_knasta": "procesador core i5 12400f", "slug_versus": "intel-core-i5-12400f"},
        {"busqueda_knasta": "procesador core i7 12700f", "slug_versus": "intel-core-i7-12700f"},
        {"busqueda_knasta": "procesador core i9 13900k", "slug_versus": "intel-core-i9-13900k"},
        {"busqueda_knasta": "procesador ryzen 5 5600", "slug_versus": "amd-ryzen-5-5600"},
        {"busqueda_knasta": "procesador ryzen 7 5700x", "slug_versus": "amd-ryzen-7-5700x"},
        {"busqueda_knasta": "procesador ryzen 7 7800x3d", "slug_versus": "amd-ryzen-7-7800x3d"},
        {"busqueda_knasta": "procesador core i3 12100f", "slug_versus": "intel-core-i3-12100f"},
        {"busqueda_knasta": "procesador core i5 13400f", "slug_versus": "intel-core-i5-13400f"},
        {"busqueda_knasta": "procesador ryzen 5 5600g", "slug_versus": "amd-ryzen-5-5600g"},
    ],
    "tarjeta_grafica": [
        {"busqueda_knasta": "tarjeta de video rtx 4060", "slug_versus": "nvidia-geforce-rtx-4060"},
        {"busqueda_knasta": "tarjeta de video rtx 3060", "slug_versus": "nvidia-geforce-rtx-3060"},
        {"busqueda_knasta": "tarjeta de video rx 7600", "slug_versus": "amd-radeon-rx-7600"},
    ],
    "placa_madre": [
        {"busqueda_knasta": "placa madre gigabyte b660 aorus master", "slug_versus": "gigabyte-b660-aorus-master", "nombre_manual": "Gigabyte B660 Aorus Master"},
        {"busqueda_knasta": "placa madre asus rog strix b660-a gaming wifi", "slug_versus": "asus-rog-strix-b660-a-gaming-wifi", "nombre_manual": "Asus ROG Strix B660-A Gaming WiFi"},
        {"busqueda_knasta": "placa madre msi b660m mortar", "slug_versus": "msi-mag-b660m-mortar-ddr4", "nombre_manual": "MSI MAG B660M Mortar DDR4"},
    ],
}


def procesar_categoria(categoria: str, items: list[dict], cursor):
    print(f"\n=== Procesando categoría: {categoria} ===")

    for item in items:
        termino_knasta = item["busqueda_knasta"]
        slug_versus = item["slug_versus"]
        
        # SOLUCIÓN: Definimos el molde único para este componente.
        # Si tiene nombre_manual lo usa, sino, limpia el término de búsqueda para que quede estético.
        nombre_componente_unico = item.get("nombre_manual") or termino_knasta.replace("procesador ", "").replace("tarjeta de video ", "").title()

        print(f"Buscando en Knasta: {termino_knasta}")
        productos_knasta = buscar_productos(termino_knasta)
        print(f"  Knasta devolvió {len(productos_knasta)} productos con precio.")

        print(f"Consultando en Versus: {slug_versus}")
        score = obtener_score_por_slug(slug_versus)
        print(f"  Versus devolvió: {score if score is not None else 'sin score'} puntos")

        # Registramos o recuperamos el ID ÚNICO del componente BASE antes de meter precios
        componente_id = obtener_o_crear_componente(
            cursor,
            nombre_modelo=nombre_componente_unico,
            categoria=categoria,
        )

        if score is not None:
            actualizar_score_benchmark(cursor, nombre_componente_unico, score)

        # Ahora asociamos todas las ofertas encontradas al mismo ID
        for producto in productos_knasta:
            insertar_precio(
                cursor,
                componente_id=componente_id,
                tienda=producto["tienda"],
                precio_soles=producto["precio"],
                url_producto=producto["url"],
                imagen_url=producto.get("imagen_url"),
            )

            estado_score = f"score={score}" if score is not None else "sin score"
            print(f"    Guardado Precio: [{nombre_componente_unico}] -> Tienda: {producto['tienda']} | S/ {producto['precio']:.2f}")

            time.sleep(random.uniform(0.3, 0.8))

        if not productos_knasta:
            print(f"    Guardado sin precio actual: {nombre_componente_unico} | score={score if score is not None else 'sin score'}")

        time.sleep(random.uniform(1.5, 3.0))


def main():
    conexion = get_connection()
    cursor = conexion.cursor()

    try:
        for categoria, items in TERMINOS_A_BUSCAR.items():
            procesar_categoria(categoria, items, cursor)
            conexion.commit() 
    except Exception as e:
        conexion.rollback()
        print(f"[ERROR] Se revirtieron los cambios por un error: {e}")
        raise
    finally:
        cursor.close()
        conexion.close()

    print("\n¡Proceso ETL terminado exitosamente! Tablas sincronizadas de forma relacional.")


if __name__ == "__main__":
    main()