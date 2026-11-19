"""Exporta los archivos ligeros que usa la página del recomendador (app/), sin DuckDB.

Versión gratuita y no comercial: incluye datos derivados del dataset de Kaggle (CC BY-NC-SA 4.0) y la capa
propia; deja fuera las filas con notas tomadas de Fragrantica (uso_permitido = solo_portafolio en la capa
propia). Salida: app/datos/{perfumes,acordes,notas}.parquet
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recomendador import leer_base  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "app/datos"
SALIDA.mkdir(parents=True, exist_ok=True)

meta, a, notas = leer_base()
fuera = meta.fuente_acordes.eq("estimado") & meta.uso_permitido.eq("solo_portafolio")
meta = meta[~fuera & meta.fragrantica_id.isin(a.fragrantica_id)]
ids = set(meta.fragrantica_id)
a = a[a.fragrantica_id.isin(ids)]
notas = notas[notas.fragrantica_id.isin(ids)]

meta = meta.drop(columns=["uso_permitido"]).astype({"anio": "Int64", "votos": "Int64"})
meta["rating"] = meta.rating.astype(float)
meta.to_parquet(SALIDA / "perfumes.parquet", index=False)
a.astype({"peso": "float32"}).to_parquet(SALIDA / "acordes.parquet", index=False)
notas.to_parquet(SALIDA / "notas.parquet", index=False)
print(f"{len(meta):,} perfumes, {len(a):,} acordes, {len(notas):,} notas -> {SALIDA}")

# Tabla propia de clones (sin la opinión ni el ranking personal del autor)
clones = RAIZ / "data/processed/powerbi_tablero/clones.csv"
if clones.exists():
    import pandas as pd
    c = pd.read_csv(clones, encoding="utf-8-sig")
    c["fuente_equivalencia"] = c.segun_fuente_externa.where(c.segun_fuente_externa.ne("sin fuente"), "autor")
    c[["clon", "clon_marca", "original", "original_marca", "parecido_acordes_pct", "acordes_del_clon",
       "fuente_equivalencia", "fuente_url"]].to_csv(SALIDA / "clones.csv", index=False)
    print(f"{len(c)} parejas de clones")
