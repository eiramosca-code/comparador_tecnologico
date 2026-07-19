"""
scraper_knasta.py (Versión Optimizada para AWS e Identificación Relacional)
"""

import re
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://knasta.pe"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-PE,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": BASE_URL + "/",
}

PRECIO_REGEX = re.compile(r"S/\s?([\d,]+\.\d{2})")

_SESSION = requests.Session()
_SESSION.headers.update(HEADERS)
_sesion_calentada = False


def _calentar_sesion():
    global _sesion_calentada
    if _sesion_calentada:
        return
    try:
        _SESSION.get(BASE_URL, timeout=15)
    except requests.RequestException:
        pass
    _sesion_calentada = True


def _limpiar_precio(texto_precio: str) -> float:
    match = PRECIO_REGEX.search(texto_precio)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


_VARIANTES_GENERICAS = [
    ("placa madre", "tarjeta madre"),
    ("placa madre", ""),
    ("tarjeta madre", "placa madre"),
    ("tarjeta de video", "tarjeta grafica"),
    ("tarjeta de video", ""),
    ("procesador", ""),
]


def _generar_variantes_query(query: str) -> list[str]:
    variantes = [query]
    q_lower = query.lower()

    for frase_original, frase_nueva in _VARIANTES_GENERICAS:
        if frase_original in q_lower:
            nueva = q_lower.replace(frase_original, frase_nueva).strip()
            nueva = re.sub(r"\s+", " ", nueva)
            if nueva and nueva not in variantes:
                variantes.append(nueva)

    return variantes


def _primera_url_de_srcset(srcset: str) -> str | None:
    if not srcset:
        return None
    primera_entrada = srcset.split(",")[0].strip()
    return primera_entrada.split(" ")[0].strip() or None


def _extraer_url_imagen(img_tag, contenedor):
    candidatos = []
    if img_tag is not None:
        for atributo in ("data-src", "data-original", "data-lazy-src", "src"):
            valor = img_tag.get(atributo)
            if valor:
                candidatos.append(valor)
        srcset_img = img_tag.get("srcset") or img_tag.get("data-srcset")
        url_srcset = _primera_url_de_srcset(srcset_img)
        if url_srcset:
            candidatos.append(url_srcset)

    source_tag = contenedor.find("source") if contenedor is not None else None
    if source_tag is not None:
        url_source = _primera_url_de_srcset(source_tag.get("srcset")) or source_tag.get("src")
        if url_source:
            candidatos.append(url_source)

    for candidato in candidatos:
        if candidato and not candidato.startswith("data:"):
            return urljoin(BASE_URL, candidato)
    return None


def _validar_coincidencia(nombre_producto: str, query_original: str) -> bool:
    """
    Filtro de seguridad: Verifica que las palabras clave esenciales de tu búsqueda
    estén presentes en el título de la tienda para evitar emparejar componentes erróneos.
    """
    # Removemos conectores comunes de la búsqueda para quedarnos con el núcleo
    palabras_filtro = [p for p in query_original.lower().split() if p not in ["procesador", "tarjeta", "de", "video", "placa", "madre", "grafica"]]
    nombre_prod_lower = nombre_producto.lower()
    
    # Si al menos las palabras clave principales (ej: 'ryzen', '5', '5600') están, es válido
    return all(palabra in nombre_prod_lower for palabra in palabras_filtro)


def _buscar_una_pagina(query: str, pagina: int, query_original: str) -> list[dict]:
    params = {"q": query}
    if pagina > 1:
        params["page"] = pagina

    try:
        resp = _SESSION.get(f"{BASE_URL}/results", params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] Falló la petición a knasta ({query}): {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    enlaces_producto = soup.select('a[href*="/detail/"]')

    if not enlaces_producto:
        return []

    resultados = []
    vistos = set()
    for enlace in enlaces_producto:
        url_producto = urljoin(BASE_URL, enlace.get("href"))
        if url_producto in vistos:
            continue
        vistos.add(url_producto)

        nombre = enlace.get_text(strip=True)
        img_tag = enlace.find("img")
        if not nombre and img_tag:
            nombre = img_tag.get("alt", "").strip()
        if not nombre:
            continue

        # Aplicamos el filtro de seguridad inteligente
        if not _validar_coincidencia(nombre, query_original):
            continue

        contenedor = enlace.find_parent(["article", "li", "div"]) or enlace
        texto_contenedor = contenedor.get_text(" ", strip=True)

        precio = _limpiar_precio(texto_contenedor)
        if precio is None:
            continue

        if img_tag is None:
            img_tag = contenedor.find("img")
        imagen_url = _extraer_url_imagen(img_tag, contenedor)

        partes_url = url_producto.split("/")
        tienda = "Knasta"
        try:
            idx = partes_url.index("detail")
            tienda = partes_url[idx + 1].replace("_", " ").capitalize()
        except (ValueError, IndexError):
            pass

        resultados.append(
            {
                "nombre": nombre, # Mantenemos el nombre detallado de la tienda para referencia
                "precio": precio,
                "tienda": tienda,
                "url": url_producto,
                "imagen_url": imagen_url,
            }
        )
    return resultados


def buscar_productos(query: str, max_paginas: int = 1) -> list[dict]:
    _calentar_sesion()

    for intento, query_actual in enumerate(_generar_variantes_query(query)):
        resultados = []
        for pagina in range(1, max_paginas + 1):
            # Le pasamos la 'query' original para validar la coincidencia real
            resultados.extend(_buscar_una_pagina(query_actual, pagina, query_original=query))
            time.sleep(random.uniform(1.5, 3.0))

        if resultados:
            if intento > 0:
                print(f"    [ok] '{query}' no dio resultados, pero la variante '{query_actual}' sí.")
            return resultados

    return []


def scrapear_categoria(terminos_busqueda: list[str]) -> list[dict]:
    todos = []
    for termino in terminos_busqueda:
        print(f"Buscando en Knasta: {termino}")
        productos = buscar_productos(termino)
        todos.extend(productos)
        time.sleep(random.uniform(2.0, 4.0))
    return todos


if __name__ == "__main__":
    ejemplo = buscar_productos("procesador core i5 12400f")
    for p in ejemplo:
        print(p)