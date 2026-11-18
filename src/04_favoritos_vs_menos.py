"""Paso 4 (exploratorio): acordes y notas de mis favoritos vs los que menos me gustan.

Dos lecturas de los mismos tercios del ranking (primero / en medio / último):
  A) solo_kaggle: perfumes con acordes votados por la comunidad.
  B) ranking_completo: los 37, sumando los de la capa propia con acordes ESTIMADOS a partir de sus notas.
Control por clima: se repite solo con los que el autor marcó "todo el año" (el clima es su opinión personal).

Muestra pequeña: describe MI gusto, no generaliza y no implica causalidad. Presencia = en cuántos perfumes del
grupo aparece el acorde o la nota. Los acordes estimados no son votos de la comunidad.

Salidas en data/processed/: analisis_acordes_grupos.csv, analisis_notas_grupos.csv,
analisis_acordes_todo_el_anio.csv, analisis_ranking_detalle.csv
"""
from pathlib import Path

import duckdb
import pandas as pd
from scipy.stats import spearmanr

RAIZ = Path(__file__).resolve().parents[1]
PROC = RAIZ / "data/processed"
con = duckdb.connect(str(PROC / "perfumes.duckdb"), read_only=True)

r = con.execute("""
    SELECT r.rank, r.nombre_original, r.uso,
           CASE WHEN r.fragrantica_id IS NULL THEN 'propia' ELSE 'kaggle' END AS fuente_datos,
           COALESCE(CAST(CAST(r.fragrantica_id AS BIGINT) AS VARCHAR), p.id_propio) AS id,
           k.rating, k.votos
    FROM ranking_personal r
    LEFT JOIN perfumes_kaggle k ON k.fragrantica_id = r.fragrantica_id
    LEFT JOIN perfumes_propios p ON r.fragrantica_id IS NULL AND lower(p.marca) = lower(r.marca)
         AND lower(p.perfume) = lower(r.perfume)
    ORDER BY r.rank""").df()
faltan = r[r.id.isna()].nombre_original.tolist()
if faltan:
    print("Sin datos en la base:", faltan)
r = r.dropna(subset=["id"]).reset_index(drop=True)
r.to_csv(PROC / "analisis_ranking_detalle.csv", index=False, encoding="utf-8")
acordes = con.execute("SELECT fuente_datos, id, acorde, peso FROM v_acordes").df()
notas = con.execute("SELECT DISTINCT fuente_datos, id, COALESCE(nota_es, nota) AS nota FROM v_notas").df()


def tercios(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("rank").reset_index(drop=True).copy()
    n = len(df) // 3
    df["grupo"] = ["favoritos"] * n + ["medio"] * (len(df) - 2 * n) + ["menos"] * n
    return df


def presencia(g: pd.DataFrame, tabla: pd.DataFrame, col: str, muestra: str) -> pd.DataFrame:
    m = tabla.merge(g[["fuente_datos", "id", "grupo"]], on=["fuente_datos", "id"])
    t = pd.crosstab(m[col], m.grupo).reindex(columns=["favoritos", "medio", "menos"], fill_value=0)
    t["n_por_grupo"] = int((g.grupo == "favoritos").sum())
    t["dif"] = t.favoritos - t.menos
    t.insert(0, "muestra", muestra)
    return t.sort_values("dif", ascending=False).reset_index()


muestras = {"solo_kaggle": tercios(r[r.fuente_datos == "kaggle"]), "ranking_completo": tercios(r)}
print({k: (len(v), int((v.grupo == "favoritos").sum())) for k, v in muestras.items()})
pd.concat(presencia(g, acordes, "acorde", k) for k, g in muestras.items()).to_csv(
    PROC / "analisis_acordes_grupos.csv", index=False, encoding="utf-8")
pd.concat(presencia(g, notas, "nota", k) for k, g in muestras.items()).to_csv(
    PROC / "analisis_notas_grupos.csv", index=False, encoding="utf-8")

ta = r[r.uso == "todo el año"]
clima = {"solo_kaggle": tercios(ta[ta.fuente_datos == "kaggle"]), "ranking_completo": tercios(ta)}
print("todo el año:", {k: len(v) for k, v in clima.items()})
pd.concat(presencia(g, acordes, "acorde", k) for k, g in clima.items()).to_csv(
    PROC / "analisis_acordes_todo_el_anio.csv", index=False, encoding="utf-8")

# Solo perfumes con rating de la comunidad; los de la capa propia no traen rating.
rk = r.dropna(subset=["rating"])
rho, p = spearmanr(rk["rank"], rk.rating)
print(f"Spearman mi ranking vs rating de la comunidad: rho={rho:.2f}, p={p:.2f}, n={len(rk)}, "
      f"votos por perfume: {int(rk.votos.min()):,}-{int(rk.votos.max()):,}")
con.close()
