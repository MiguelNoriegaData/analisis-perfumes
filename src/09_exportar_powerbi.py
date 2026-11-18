"""Paso 9: tablas para el tablero de Power BI (modelo estrella), solo con las 94 marcas de marcas_categorias.

Salida en data/processed/powerbi_tablero/ (CSV UTF-8 con BOM):
  perfumes.csv        una fila por perfume (id único: K + fragrantica_id para Kaggle, P##### para la capa propia)
  marcas.csv          una fila por marca, con su categoría y grupo
  perfume_acorde.csv  perfume x acorde (comunidad = votos de Fragrantica; estimado = modelo con las notas)
  perfume_nota.csv    perfume x nota (canónica en inglés y en español)
  fuente.csv          texto de la fuente y licencia para el pie del tablero

Relaciones en Power BI: marcas[marca] 1-* perfumes[marca]; perfumes[id] 1-* perfume_acorde[id];
perfumes[id] 1-* perfume_nota[id]. Filtro de una sola dirección.
"""
import sys
from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parents[1]
DB = RAIZ / "data/processed/perfumes.duckdb"
SALIDA = RAIZ / "data/processed/powerbi_tablero"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import recomendador as rec  # noqa: E402  (traducción de acordes al español)

CONSULTAS = {
    "perfumes": """
        SELECT CASE WHEN v.fuente_datos = 'kaggle' THEN 'K' || v.id ELSE v.id END AS id,
               v.nombre, v.marca, v.categoria, v.grupo, COALESCE(v.genero, 'sin dato') AS genero, v.anio,
               v.rating, v.votos,
               CASE v.fuente_datos WHEN 'kaggle' THEN 'Kaggle (Fragrantica)' ELSE 'Capa propia' END AS fuente_datos,
               CASE WHEN v.fuente_datos = 'kaggle' THEN 'comunidad' WHEN e.id_propio IS NOT NULL THEN 'estimado'
                    ELSE 'sin acordes' END AS fuente_acordes,
               e.confianza AS confianza_acordes, v.uso_permitido
        FROM v_perfumes v
        LEFT JOIN (SELECT DISTINCT id_propio, confianza FROM acordes_estimados_propios) e
               ON v.fuente_datos = 'propia' AND e.id_propio = v.id
        WHERE v.categoria IS NOT NULL""",
    "marcas": """
        SELECT marca, categoria, NULLIF(grupo, '') AS grupo FROM marcas_categorias""",
    "perfume_acorde": """
        SELECT CASE WHEN a.fuente_datos = 'kaggle' THEN 'K' || a.id ELSE a.id END AS id, a.acorde, a.posicion,
               a.peso, a.fuente_acordes
        FROM v_acordes a JOIN v_perfumes v ON v.fuente_datos = a.fuente_datos AND v.id = a.id
        WHERE v.categoria IS NOT NULL""",
    "perfume_nota": """
        SELECT DISTINCT CASE WHEN n.fuente_datos = 'kaggle' THEN 'K' || n.id ELSE n.id END AS id, n.nota,
               COALESCE(n.nota_es, n.nota) AS nota_es
        FROM v_notas n JOIN v_perfumes v ON v.fuente_datos = n.fuente_datos AND v.id = n.id
        WHERE v.categoria IS NOT NULL""",
}


def main() -> None:
    con = duckdb.connect(str(DB), read_only=True)
    SALIDA.mkdir(exist_ok=True)
    for nombre, sql in CONSULTAS.items():
        df = con.execute(sql).df()
        if nombre == "perfume_acorde":
            df.insert(2, "acorde_es", df.acorde.map(rec.es))
        df.to_csv(SALIDA / f"{nombre}.csv", index=False, encoding="utf-8-sig")
        print(f"{nombre:16s} {len(df):>8,} filas")
    (SALIDA / "fuente.csv").write_text(
        "texto\n\"Fuente: Fragrantica.com Fragrance Dataset (Olga G, Kaggle), licencia CC BY-NC-SA 4.0, "
        "y capa propia (sitios oficiales, tiendas y prensa, 2024-2026). Acordes de la capa propia estimados con "
        "un modelo a partir de sus notas. Solo las 94 marcas de la tabla propia.\"\n", encoding="utf-8-sig")
    con.close()


if __name__ == "__main__":
    main()
