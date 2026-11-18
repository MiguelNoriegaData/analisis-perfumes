"""Paso 10: tabla de tendencias por año para la página 4 del tablero.

Solo perfumes de Kaggle (acordes votados por la comunidad), masculinos y unisex, de las 94 marcas, 2000-2024.
La capa propia no entra: sus acordes son estimados y sus años muchas veces son aproximados.
2024 está incompleto (el dataset se publicó en septiembre de 2024).

Salida: data/processed/powerbi_tablero/tendencias.csv
  anio, categoria ("Todas" o la categoría), acorde, acorde_es, perfumes_con_acorde, perfumes_del_anio, pct
Lectura: es el porcentaje de los perfumes de ese año registrados en Fragrantica que tienen el acorde.
No es el total de lanzamientos del mercado ni mide ventas.
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
D = RAIZ / "data/processed/powerbi_tablero"


def main() -> None:
    p = pd.read_csv(D / "perfumes.csv")
    a = pd.read_csv(D / "perfume_acorde.csv")
    p = p[p.fuente_acordes.eq("comunidad") & p.genero.isin(["masculino", "unisex"]) & p.anio.between(2000, 2024)]
    p = pd.concat([p, p.assign(categoria="Todas")])
    total = p.groupby(["anio", "categoria"]).id.nunique().rename("perfumes_del_anio")
    con = (a.merge(p[["id", "anio", "categoria"]], on="id")
           .groupby(["anio", "categoria", "acorde", "acorde_es"]).id.nunique().rename("perfumes_con_acorde"))
    t = con.reset_index().merge(total.reset_index(), on=["anio", "categoria"])
    t["pct"] = (t.perfumes_con_acorde / t.perfumes_del_anio).round(4)
    t["anio"] = t.anio.astype(int)
    t.sort_values(["categoria", "acorde", "anio"]).to_csv(D / "tendencias.csv", index=False, encoding="utf-8-sig")
    print(total.unstack().fillna(0).astype(int).to_string())


if __name__ == "__main__":
    main()
