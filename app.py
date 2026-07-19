"""
app.py
Interfaz web del Comparador Tecnológico (Streamlit).

REDISEÑO (v3 - estilo "Versus"):
- Antes las tarjetas se apilaban una debajo de otra a lo ancho de la
  pantalla. Ahora se muestran en una grilla (3 por fila en desktop, se
  acomodan solas en pantallas chicas) con un círculo de puntaje superpuesto
  sobre la imagen, muy similar al grid de versus.com/es/cpu.
- Cada tarjeta: imagen del producto, círculo de score (verde/ámbar/rojo
  según rendimiento), nombre, mejor precio destacado y, si hay más de una
  oferta, la lista de tiendas debajo en texto chico.
- Si un producto no tiene imagen (knasta no la trajo), se muestra un
  ícono de la categoría como respaldo, para que la tarjeta nunca se vea
  vacía/rota.
"""

import html

import streamlit as st
import mysql.connector

from db import get_connection

st.set_page_config(
    page_title="Comparador Tecnológico",
    page_icon="💻",
    layout="wide",
)

TARJETAS_POR_FILA = 3

# ==============================================================================
# ESTILOS
# ==============================================================================
st.markdown(
    """
    <style>
    /* Fondo beige neutro para la aplicación */
    .main { background-color: #F5F5DC !important; }
    div[data-testid="stAppViewContainer"] { background-color: #F5F5DC; }

    .hero {
        background: linear-gradient(135deg, #6C63FF 0%, #FF6584 100%);
        padding: 2.2rem 2rem;
        border-radius: 18px;
        margin-bottom: 1.8rem;
        box-shadow: 0 8px 24px rgba(108, 99, 255, 0.25);
    }
    .hero h1 { color: white; font-size: 2.1rem; margin-bottom: 0.3rem; }
    .hero p  { color: rgba(255,255,255,0.9); font-size: 1.02rem; margin: 0; }

    .versus-card {
        position: relative;
        background: #FAFAFA; /* Tono crema muy suave para las tarjetas */
        border-radius: 16px;
        border: 1px solid #E0E0E0;
        padding: 1.1rem 1rem 1rem 1rem;
        margin-bottom: 1.3rem;
        min-height: 300px;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .versus-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 12px 26px rgba(0,0,0,0.1);
        border-color: #BDBDBD;
    }

    .score-circle {
        position: absolute;
        top: 10px;
        left: 10px;
        width: 54px;
        height: 54px;
        border-radius: 50%;
        background: #F5F5DC; /* Fondo beige a juego con el fondo principal */
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        z-index: 2;
        line-height: 1;
    }
    .score-circle .num { font-size: 1.05rem; font-weight: 800; }
    .score-circle .label { font-size: 0.5rem; opacity: 0.85; margin-top: 1px; color: #333333; }

    /* Colores de score adaptados para fondo claro */
    .score-alto  { border: 3px solid #17a877; }
    .score-alto  .num { color: #117a56; }
    .score-medio { border: 3px solid #e0a02c; }
    .score-medio .num { color: #a8761d; }
    .score-bajo  { border: 3px solid #e05a5a; }
    .score-bajo  .num { color: #a83f3f; }
    .score-sin   { border: 3px solid #a4a7b5; }
    .score-sin   .num { color: #6e7182; font-size: 0.8rem; }

    .card-img-wrap {
        width: 100%;
        height: 150px;
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 0.6rem;
    }
    .card-img-wrap img {
        max-height: 150px;
        max-width: 100%;
        object-fit: contain;
        border-radius: 8px;
    }
    .card-img-fallback { font-size: 3rem; opacity: 0.4; }

    .card-title {
        font-size: 0.92rem;
        font-weight: 700;
        color: #2D2D2D; /* Texto oscuro para legibilidad sobre el crema */
        min-height: 2.6em;
        margin-bottom: 0.5rem;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }

    .price-tag {
        background: linear-gradient(135deg, #1e7d4e 0%, #17a877 100%);
        color: white;
        padding: 0.5rem 0.7rem;
        border-radius: 10px;
        font-weight: 700;
        font-size: 0.92rem;
        margin-bottom: 0.4rem;
    }
    .price-tag a { color: white; text-decoration: none; }
    .price-tag .tienda { font-weight: 500; opacity: 0.9; font-size: 0.82rem; }

    .otras-tiendas { font-size: 0.78rem; color: #555555; line-height: 1.5; }
    .otras-tiendas a { color: #555555; }

    .sin-oferta { font-size: 0.8rem; color: #888888; font-style: italic; }
    
    /* Forzar que el texto general de Streamlit sea oscuro si el usuario lo tiene en modo oscuro */
    p, span, div { color: #333333; }
    </style>
    """,
    unsafe_allow_html=True,
)

CATEGORIA_CONFIG = {
    "procesador": {"icono": "🖥️", "titulo": "Procesadores"},
    "tarjeta_grafica": {"icono": "🎮", "titulo": "Tarjetas de Video"},
    "placa_madre": {"icono": "🔧", "titulo": "Placas Madre"},
}


def config_categoria(categoria: str) -> dict:
    return CATEGORIA_CONFIG.get(
        categoria, {"icono": "🔩", "titulo": categoria.replace("_", " ").title()}
    )


def clase_score(score):
    if score is None:
        return "score-sin", "—"
    if score >= 70:
        return "score-alto", str(score)
    if score >= 40:
        return "score-medio", str(score)
    return "score-bajo", str(score)


# ==============================================================================
# HERO
# ==============================================================================
# ==============================================================================
# HERO
# ==============================================================================
st.markdown(
    """
    <style>
    .hero {
        background-image: linear-gradient(rgba(20, 24, 36, 0.75), rgba(20, 24, 36, 0.85)), 
                          url('https://images.unsplash.com/photo-1591799264318-7e6ef8ddb7ea?ixlib=rb-4.0.3&auto=format&fit=crop&w=1280&q=80');
        background-size: cover;
        background-position: center;
        padding: 3.5rem 2rem;
        border-radius: 18px;
        margin-bottom: 1.8rem;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
        text-align: center;
    }
    .hero h1 { 
        color: #FFFFFF !important;
        font-size: 2.4rem; 
        margin-bottom: 0.5rem; 
        text-shadow: 3px 3px 10px rgba(0,0,0,0.9);
    }
    .hero p  { 
        color: #FFFFFF !important;
        font-size: 1.15rem; 
        margin: 0; 
        text-shadow: 2px 2px 6px rgba(0,0,0,0.9);
    }
    </style>
    
    <div class="hero">
        <h1>💻 Comparador Tecnológico & Localizador de Precios</h1>
        <p>Compara procesadores, tarjetas de video y placas madre: rendimiento real (Versus) vs. el mejor precio del mercado (Knasta).</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def obtener_categorias_disponibles(cursor) -> list[str]:
    cursor.execute("SELECT DISTINCT categoria FROM componentes ORDER BY categoria")
    return [fila["categoria"] for fila in cursor.fetchall()]


def obtener_componentes(cursor, categoria: str, busqueda: str):
    sql = "SELECT id, nombre_modelo, categoria, score_benchmark FROM componentes WHERE categoria = %s"
    params = [categoria]
    if busqueda:
        sql += " AND nombre_modelo LIKE %s"
        params.append(f"%{busqueda}%")
    sql += " ORDER BY score_benchmark IS NULL, score_benchmark DESC"
    cursor.execute(sql, tuple(params))
    return cursor.fetchall()


def obtener_ofertas(cursor, componente_id: int):
    # GROUP BY para blindarnos contra filas duplicadas heredadas de antes
    # de correr migrate_db.py (mismo tienda + precio + url repetidos).
    cursor.execute(
        """
        SELECT tienda, precio_soles, url_producto, MAX(imagen_url) AS imagen_url
        FROM precios_mercado
        WHERE componente_id = %s
        GROUP BY tienda, precio_soles, url_producto
        ORDER BY precio_soles ASC
        """,
        (componente_id,),
    )
    return cursor.fetchall()


def render_card_html(comp, ofertas, icono_categoria: str) -> str:
    nombre = html.escape(comp["nombre_modelo"])
    clase, texto_score = clase_score(comp["score_benchmark"])

    # Imagen: usamos la del precio más barato si existe; si no, buscamos
    # cualquier otra oferta que sí traiga imagen.
    imagen = next((o["imagen_url"] for o in ofertas if o.get("imagen_url")), None)
    if imagen:
        bloque_imagen = f'<img src="{html.escape(imagen)}" alt="{nombre}" loading="lazy">'
    else:
        bloque_imagen = f'<div class="card-img-fallback">{icono_categoria}</div>'

    if ofertas:
        mejor = ofertas[0]
        bloque_precio = (
            '<div class="price-tag">'
            f'<a href="{html.escape(mejor["url_producto"])}" target="_blank" rel="noopener">'
            f'S/ {mejor["precio_soles"]:.2f}</a>'
            f'<div class="tienda">en {html.escape(mejor["tienda"])}</div>'
            "</div>"
        )
        if len(ofertas) > 1:
            filas = "".join(
                f'<div>· {html.escape(o["tienda"])}: '
                f'<a href="{html.escape(o["url_producto"])}" target="_blank" rel="noopener">'
                f'S/ {o["precio_soles"]:.2f}</a></div>'
                for o in ofertas[1:]
            )
            bloque_precio += f'<div class="otras-tiendas">{filas}</div>'
    else:
        bloque_precio = '<div class="sin-oferta">Sin ofertas registradas todavía</div>'

    # OJO: todo en una sola línea por elemento, sin sangría. Streamlit usa
    # un parser de Markdown por debajo, y cualquier línea indentada con 4+
    # espacios se interpreta como un bloque de código (por eso antes salía
    # el HTML crudo en vez de renderizarse).
    return (
        '<div class="versus-card">'
        f'<div class="score-circle {clase}">'
        f'<span class="num">{texto_score}</span>'
        '<span class="label">PTS</span>'
        "</div>"
        f'<div class="card-img-wrap">{bloque_imagen}</div>'
        f'<div class="card-title">{nombre}</div>'
        f"{bloque_precio}"
        "</div>"
    )


# ==============================================================================
# CUERPO PRINCIPAL: PESTAÑAS POR CATEGORÍA
# ==============================================================================
try:
    conexion = get_connection()
    cursor = conexion.cursor(dictionary=True)

    categorias = obtener_categorias_disponibles(cursor)

    if not categorias:
        st.warning("Todavía no hay componentes cargados. Corre `python main.py` primero.")
    else:
        etiquetas_tabs = [f"{config_categoria(c)['icono']} {config_categoria(c)['titulo']}" for c in categorias]
        tabs = st.tabs(etiquetas_tabs)

        for tab, categoria in zip(tabs, categorias):
            cfg = config_categoria(categoria)
            with tab:
                busqueda = st.text_input(
                    f"🔍 Filtrar {cfg['titulo'].lower()} por modelo:",
                    key=f"busqueda_{categoria}",
                    placeholder="Ej: Ryzen 5, i5-12400F, B660...",
                ).strip()

                componentes = obtener_componentes(cursor, categoria, busqueda)

                if not componentes:
                    st.info(f"No se encontraron {cfg['titulo'].lower()} que coincidan con tu búsqueda.")
                else:
                    st.caption(f"{len(componentes)} componente(s) encontrado(s)")

                    for i in range(0, len(componentes), TARJETAS_POR_FILA):
                        fila = componentes[i : i + TARJETAS_POR_FILA]
                        columnas = st.columns(TARJETAS_POR_FILA)
                        for col, comp in zip(columnas, fila):
                            ofertas = obtener_ofertas(cursor, comp["id"])
                            with col:
                                st.markdown(
                                    render_card_html(comp, ofertas, cfg["icono"]),
                                    unsafe_allow_html=True,
                                )

    cursor.close()
    conexion.close()

except mysql.connector.Error as err:
    st.error(f"Error de conexión con la base de datos de AWS: {err}")
