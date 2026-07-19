"""
scraper_versus.py
Extrae el "Puntuación Versus" (score_benchmark, 0-100) de procesadores desde
versus.com/es.

CAMBIO IMPORTANTE (v2):
La primera versión de este scraper descargaba el ranking completo
(/es/cpu) y trataba de emparejar cada producto de Knasta con un nombre del
ranking usando fuzzy matching. Eso falló para casi todos los procesadores
de gama media/entrada (i5-12400F, Ryzen 5700X, etc.) porque esa página SOLO
carga sin JavaScript los ~100 productos con MAYOR puntaje (Threadripper,
i9, Ryzen 9, etc.) — los modelos de gama media están mucho más abajo en el
ranking y solo se cargan haciendo clic en "Mostrar más" (JavaScript).

En vez de pelear con eso, usamos algo mucho más simple y confiable: cada
producto en versus.com tiene su propia página de ficha con una URL
predecible, por ejemplo:
    https://versus.com/es/intel-core-i5-12400f
    https://versus.com/es/amd-ryzen-7-5700x
Esa página siempre muestra el puntaje justo al inicio, en un formato como
"49puntos" (confirmado). Así que en vez de descargar el ranking entero y
adivinar con fuzzy matching, simplemente construimos/recibimos el slug
exacto del modelo que queremos y pedimos esa página directamente.

Esto significa que YA NO hace falta fuzzy matching: en main.py, cada
componente que quieras cargar debe traer su propio "slug_versus" (el
nombre tal como aparece en la URL de versus.com). Si no estás seguro del
slug de un modelo, búscalo en Google: "site:versus.com <modelo>" o entra a
versus.com/es/cpu y usa el buscador del sitio.
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://versus.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
}

PUNTAJE_REGEX = re.compile(r"(\d{1,3})\s*puntos")


def obtener_score_por_slug(slug: str) -> int | None:
    """
    Descarga la ficha individual usando ScraperAPI con reintentos automáticos
    y mayor tolerancia a caídas de red o timeouts.
    """
    url = urljoin(BASE_URL, f"/es/{slug}")
    
    API_KEY = os.environ.get("SCRAPERAPI_KEY")
    if not API_KEY or API_KEY in ["TU_API_KEY_REAL_AQUI", "00000000000000000000000000000000"]:
        API_KEY = "7fecc11e8d8bd6671ece63ac84dd6f3e" 

    payload = {'api_key': API_KEY, 'url': url}

    resp = None
    # Intentamos la petición hasta 2 veces si hay problemas de timeout/red
    for intento in range(2):
        try:
            # Subimos el timeout a 60 segundos para darle más margen a ScraperAPI
            resp = requests.get('https://api.scraperapi.com/', params=payload, timeout=60)
            break  # Si la petición no dio excepción, salimos del ciclo de reintento
        except requests.RequestException as e:
            if intento == 0:
                print(f"[AVISO] Timeout o error de red en intento 1 para '{slug}'. Reintentando en 3 segundos...")
                time.sleep(3)
            else:
                print(f"[ERROR] Fallaron todos los intentos para ScraperAPI ({slug}): {e}")
                return None

    if resp is None:
        return None

    if resp.status_code == 401:
        print(f"[ERROR] Clave de ScraperAPI inválida o no configurada para '{slug}'.")
        return None

    if resp.status_code == 404:
        print(f"[AVISO] versus.com no tiene una ficha para el slug '{slug}' (404).")
        return None

    try:
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] La API devolvió un error para '{slug}': {e}")
        return None

    soup = BeautifulSoup(resp.text, "lxml")
    texto = soup.get_text(" ", strip=True)

    match = PUNTAJE_REGEX.search(texto)
    if not match:
        print(f"[AVISO] No se encontró el patrón de puntaje para '{slug}'.")
        return None

    score = int(match.group(1))
    if not (0 <= score <= 100):
        return None

    return score


if __name__ == "__main__":
    # Prueba rápida y aislada del scraper
    for slug_prueba in ["intel-core-i5-12400f", "amd-ryzen-7-5700x", "slug-que-no-existe"]:
        score = obtener_score_por_slug(slug_prueba)
        print(f"{slug_prueba} -> {score}")