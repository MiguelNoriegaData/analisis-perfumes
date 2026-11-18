"""Paso 11: tablas de las páginas 5 (clones y originales) y 6 (caso de uso del recomendador).

Página 5 · clones.csv: una fila por pareja clon-original, juntando las dos tablas propias de equivalencias:
  datos/equivalencias_clones.csv (lo que dice el autor del ranking) y datos/equivalencias_fuentes_externas.csv (tiendas, prensa,
  reseñas). La relación clon-original NO viene del dataset: es una tabla propia, documentada como tal.
  parecido_acordes_pct = coseno entre vectores de acordes (el mismo del recomendador). Si el clon tiene acordes
  estimados se restan 3 puntos (sesgo medido en la validación). Es parecido de acordes, no prueba de que huelan igual.
  referencia.csv: parecido típico entre dos perfumes masculinos/unisex al azar, para poner los porcentajes en contexto.
Página 6 · caso_perfil.csv y caso_recomendaciones.csv: perfil de acordes de los 12 favoritos del autor y las
  5 mejores opciones por categoría (penalizando el almizclado). Exploratorio: es un ejemplo de uso, no un hallazgo.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import recomendador as rec  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
PROC = RAIZ / "data/processed"
SALIDA = PROC / "powerbi_tablero"


def main() -> None:
    d = rec.cargar()
    ranking = pd.read_csv(PROC / "ranking_emparejado.csv")
    import duckdb
    con = duckdb.connect(str(rec.DB), read_only=True)
    capa = con.execute("""SELECT r.rank, -CAST(substr(p.id_propio, 2) AS INTEGER) AS id
                          FROM ranking_personal r JOIN perfumes_propios p ON r.fragrantica_id IS NULL
                          AND lower(p.marca) = lower(r.marca) AND lower(p.perfume) = lower(r.perfume)""").df()
    con.close()
    id_por_rank = dict(zip(ranking["rank"], ranking.fragrantica_id))
    id_por_rank.update({k: v for k, v in zip(capa["rank"], capa.id)})
    marca_por_rank = dict(zip(ranking["rank"], ranking.marca))
    nombre_por_rank = dict(zip(ranking["rank"], ranking.nombre_original))

    m = pd.read_csv(PROC / "equivalencias_clones.csv")
    m = m.assign(segun_ranking_personal=m.certeza_usuario)[["rank", "original_marca", "original_perfume",
                                                  "original_fragrantica_id", "segun_ranking_personal"]]
    e = pd.read_csv(PROC / "equivalencias_fuentes_externas.csv")
    e = e.assign(segun_fuente_externa=e.tipo_fuente)[["rank", "original_marca", "original_perfume",
                                                      "original_fragrantica_id", "segun_fuente_externa", "fuente_url"]]
    pares = m.merge(e, on=["rank", "original_fragrantica_id"], how="outer", suffixes=("", "_e"))
    pares["original_marca"] = pares.original_marca.fillna(pares.original_marca_e)
    pares["original_perfume"] = pares.original_perfume.fillna(pares.original_perfume_e)
    pares = pares.drop(columns=["original_marca_e", "original_perfume_e"])

    filas = []
    for r in pares.itertuples():
        cid, oid = id_por_rank.get(r.rank), r.original_fragrantica_id
        pct, fuente = None, None
        if pd.notna(cid) and pd.notna(oid) and int(cid) in d.idx and int(oid) in d.idx:
            pct = float(d.X[d.idx[int(cid)]] @ d.X[d.idx[int(oid)]])
            fuente = d.meta.loc[int(cid), "fuente_acordes"]
            if fuente == "estimado":
                pct = max(pct - rec.AJUSTE_ESTIMADO, 0)
        filas.append({"clon": nombre_por_rank.get(r.rank), "clon_marca": marca_por_rank.get(r.rank),
                      "original": f"{r.original_marca} {r.original_perfume}", "original_marca": r.original_marca,
                      "parecido_acordes_pct": round(pct * 100, 1) if pct is not None else None,
                      "acordes_del_clon": fuente or "sin datos",
                      "segun_ranking_personal": r.segun_ranking_personal if pd.notna(r.segun_ranking_personal) else "no lo mencionó",
                      "segun_fuente_externa": r.segun_fuente_externa if pd.notna(r.segun_fuente_externa) else "sin fuente",
                      "fuente_url": r.fuente_url if pd.notna(r.fuente_url) else "", "rank_personal": r.rank})
    clones = pd.DataFrame(filas).sort_values("parecido_acordes_pct", ascending=False)
    clones.to_csv(SALIDA / "clones.csv", index=False, encoding="utf-8-sig")

    # Referencia: parecido entre parejas al azar de perfumes masculinos/unisex con acordes de la comunidad.
    ok = np.where(d.meta.genero.isin(["masculino", "unisex"]).values & d.meta.fuente_acordes.eq("comunidad").values
                  & (d.meta.votos.fillna(0) >= 50).values)[0]
    rng = np.random.default_rng(42)
    a, b = rng.choice(ok, 20000), rng.choice(ok, 20000)
    sim = (d.X[a] * d.X[b]).sum(1) * 100
    pd.DataFrame({"referencia": ["mediana al azar", "percentil 90 al azar"],
                  "parecido_acordes_pct": [round(float(np.median(sim)), 1), round(float(np.percentile(sim, 90)), 1)]}
                 ).to_csv(SALIDA / "referencia.csv", index=False, encoding="utf-8-sig")

    # Página 6: mismo caso que 05_recomendaciones_caso_personal.py
    favs = [int(id_por_rank[k]) for k in sorted(id_por_rank) if k <= 12 and pd.notna(id_por_rank[k])]
    res = rec.recomendar(d, perfumes=favs, no_acordes=["musky"], n_por_categoria=5)
    res["perfil"].to_csv(SALIDA / "caso_perfil.csv", index=False, encoding="utf-8-sig")
    reco = pd.concat([v.assign(categoria=k, puesto=range(1, len(v) + 1)) for k, v in res["recomendaciones"].items()])
    reco.to_csv(SALIDA / "caso_recomendaciones.csv", index=False, encoding="utf-8-sig")
    print(clones[["clon", "original", "parecido_acordes_pct", "acordes_del_clon", "segun_ranking_personal",
                  "segun_fuente_externa"]].to_string(index=False))
    print(pd.read_csv(SALIDA / "referencia.csv").to_string(index=False), "| favoritos usados:", len(favs))


if __name__ == "__main__":
    main()
