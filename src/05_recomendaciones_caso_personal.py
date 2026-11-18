"""Paso 5: recomendaciones para el autor (entrada B) con sus favoritos, penalizando el acorde almizclado.

Favoritos = perfumes del ranking emparejados con rank <= 12. Salida: data/processed/recomendaciones_caso_personal.csv
"""
from pathlib import Path

import duckdb
import pandas as pd

from recomendador import DB, cargar, recomendar

RAIZ = Path(__file__).resolve().parents[1]
d = cargar()
con = duckdb.connect(str(DB), read_only=True)
# Los favoritos sin registro en Kaggle se buscan en la capa propia por marca y nombre exactos (id interno negativo).
fav = con.execute("""
    SELECT r.rank, r.nombre_original,
           COALESCE(CAST(r.fragrantica_id AS BIGINT), -CAST(substr(p.id_propio, 2) AS BIGINT)) AS id
    FROM ranking_personal r
    LEFT JOIN perfumes_propios p ON r.fragrantica_id IS NULL AND lower(p.marca) = lower(r.marca)
         AND lower(p.perfume) = lower(r.perfume)
    WHERE r.rank <= 12 ORDER BY r.rank""").df()
sin_datos = fav[fav.id.isna()].nombre_original.tolist()
print("Favoritos:", len(fav), "| sin datos en la base:", sin_datos)
res = recomendar(d, perfumes=fav.id.dropna().astype(int).tolist(), no_acordes=["musky"], n_por_categoria=5)
print("Perfil deducido:\n", res["perfil"].to_string(index=False))
salida = pd.concat([v.assign(categoria=k) for k, v in res["recomendaciones"].items()])
salida.to_csv(RAIZ / "data/processed/recomendaciones_caso_personal.csv", index=False, encoding="utf-8")
