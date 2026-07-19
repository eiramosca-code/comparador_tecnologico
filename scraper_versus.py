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

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://versus.com"

# CABECERAS ROBUSTAS: Se añadieron parámetros de control para simular comportamiento humano real
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

PUNTAJE_REGEX = re.compile(r"(\d{1,3})\s*puntos")


def obtener_score_por_slug(slug: str) -> int | None:
    """
    Descarga la ficha individual de un producto (ej. slug="intel-core-i5-12400f",
    que corresponde a https://versus.com/es/intel-core-i5-12400f) y devuelve
    su Puntuación Versus (0-100), o None si no se pudo obtener.
    """
    url = urljoin(BASE_URL, f"/es/{slug}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
    except requests.RequestException as e:
        print(f"[ERROR] Falló la petición a versus.com ({slug}): {e}")
        return None

    if resp.status_code == 404:
        print(f"[AVISO] versus.com no tiene una ficha para el slug '{slug}' (404). Revisa que esté bien escrito.")
        return None

    try:
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] versus.com devolvió un error para '{slug}': {e}")
        return None

    soup = BeautifulSoup(resp.text, "lxml")
    texto = soup.get_text(" ", strip=True)

    # El puntaje aparece muy al inicio de la página, pegado como "49puntos".
    match = PUNTAJE_REGEX.search(texto)
    if not match:
        print(f"[AVISO] No se encontró el patrón de puntaje para '{slug}'. Puede que versus.com haya cambiado el diseño.")
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