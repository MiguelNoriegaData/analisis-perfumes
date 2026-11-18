"""Paso 8: métricas por nota y acorde, y exportación para Power BI.

Crea en perfumes.duckdb las vistas:
  v_acordes            acordes de Kaggle (comunidad) y de la capa propia (estimados), con su fuente
  v_metricas_generales cuántos perfumes, marcas, notas y acordes hay
  v_metricas_notas     por nota: cuántos perfumes la tienen, en total y por fuente
  v_metricas_acordes   por acorde: lo mismo, separando comunidad y estimado
  v_metricas_marcas    por marca: categoría y número de perfumes
Exporta tablas a data/processed/powerbi/ en CSV (UTF-8 con BOM, para Excel y Power BI).

Lectura correcta: los conteos dicen cuántos perfumes del catálogo llevan una nota o acorde. No miden calidad ni
popularidad. Filtrar uso_permitido = 'capa_propia' para lo que se vaya a monetizar.
"""
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parents[1]
DB = RAIZ / "data/processed/perfumes.duckdb"
SALIDA = RAIZ / "data/processed/powerbi"

VISTAS = """
CREATE OR REPLACE VIEW v_acordes AS
SELECT 'kaggle' AS fuente_datos, CAST(fragrantica_id AS VARCHAR) AS id, posicion, acorde, peso, 'comunidad' AS fuente_acordes,
       CAST(NULL AS VARCHAR) AS confianza
FROM acordes_kaggle
UNION ALL
SELECT 'propia', id_propio, posicion, acorde, peso, 'estimado', confianza FROM acordes_estimados_propios;

CREATE OR REPLACE VIEW v_metricas_generales AS
SELECT 'perfumes' AS metrica, count(*) AS total FROM v_perfumes
UNION ALL SELECT 'perfumes_kaggle', count(*) FROM v_perfumes WHERE fuente_datos = 'kaggle'
UNION ALL SELECT 'perfumes_capa_propia', count(*) FROM v_perfumes WHERE fuente_datos = 'propia'
UNION ALL SELECT 'marcas_en_tabla', count(*) FROM marcas_categorias
UNION ALL SELECT 'notas', count(DISTINCT nota) FROM v_notas
UNION ALL SELECT 'acordes', count(DISTINCT acorde) FROM v_acordes;

CREATE OR REPLACE VIEW v_metricas_notas AS
SELECT nota, any_value(nota_es) AS nota_es, count(DISTINCT fuente_datos || id) AS perfumes,
       count(DISTINCT id) FILTER (WHERE fuente_datos = 'kaggle') AS perfumes_kaggle,
       count(DISTINCT id) FILTER (WHERE fuente_datos = 'propia') AS perfumes_capa_propia
FROM v_notas GROUP BY nota;

CREATE OR REPLACE VIEW v_metricas_acordes AS
SELECT acorde, count(DISTINCT fuente_datos || id) AS perfumes,
       count(DISTINCT id) FILTER (WHERE fuente_acordes = 'comunidad') AS perfumes_comunidad,
       count(DISTINCT id) FILTER (WHERE fuente_acordes = 'estimado') AS perfumes_estimado
FROM v_acordes GROUP BY acorde;

CREATE OR REPLACE VIEW v_metricas_marcas AS
SELECT marca, COALESCE(categoria, 'Otra') AS categoria, count(*) AS perfumes,
       count(*) FILTER (WHERE fuente_datos = 'kaggle') AS perfumes_kaggle,
       count(*) FILTER (WHERE fuente_datos = 'propia') AS perfumes_capa_propia
FROM v_perfumes GROUP BY 1, 2;
"""


def main() -> None:
    con = duckdb.connect(str(DB))
    con.execute(VISTAS)
    SALIDA.mkdir(exist_ok=True)
    for vista in ["v_perfumes", "v_notas", "v_acordes", "v_metricas_generales", "v_metricas_notas",
                  "v_metricas_acordes", "v_metricas_marcas", "ranking_personal"]:
        df = con.execute(f"SELECT * FROM {vista}").df()
        df.to_csv(SALIDA / f"{vista.removeprefix('v_')}.csv", index=False, encoding="utf-8-sig")
        print(f"{vista:24s} {len(df):>9,} filas")
    con.close()


if __name__ == "__main__":
    main()
