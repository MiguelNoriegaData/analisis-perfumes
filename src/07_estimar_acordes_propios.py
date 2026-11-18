"""Paso 7: estimar acordes de la capa propia con el modelo notas → acordes y cargarlos a la base.

Entrada: data/processed/perfumes_propios.csv (capa propia), models/modelo_notas_acordes.joblib
Salida:  data/processed/acordes_estimados_propios.csv y tabla acordes_estimados_propios en perfumes.duckdb
         (id_propio, posicion, acorde, peso_estimado, notas_usadas, notas_totales, confianza)

Las notas de la capa propia vienen de tiendas y marcas, escritas de muchas formas ("italian bergamot",
"virginia cedarwood"). Se llevan al vocabulario del modelo así:
  1) sinónimos de 03_normalizar_notas.py; 2) quitar palabras de origen/calidad (italian, absolute…);
  3) quitar el plural. Lo que no se reconoce se ignora y se reporta.
Formato igual al de Kaggle: se guardan los 8 acordes con mayor valor del modelo, con peso por posición
(1.º = 1.0 … 8.º = 0.3). En la validación esto reduce el sesgo de parecido (los vectores del modelo son más
"suaves" que los reales y sobreestiman el parecido): de +11 a +3 puntos; el recomendador resta esos 3 puntos.
Confianza del estimado: alta (≥5 notas reconocidas y ≥70 % de las notas), media (≥3), baja (1–2).
Los acordes estimados se etiquetan como estimados en todo lo que se muestre: no son votos de la comunidad.
"""
import importlib.util
import re
import sys
from pathlib import Path

import duckdb
import joblib
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
SRC = RAIZ / "src"
sys.path.insert(0, str(SRC))
spec = importlib.util.spec_from_file_location("norm", SRC / "03_normalizar_notas.py")
norm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(norm)
spec6 = importlib.util.spec_from_file_location("modelo", SRC / "06_modelo_notas_acordes.py")
mod6 = importlib.util.module_from_spec(spec6)
spec6.loader.exec_module(mod6)
sys.modules["__main__"].ModeloNotasAcordes = mod6.ModeloNotasAcordes  # para cargar el joblib

ORIGEN = r"\b(italian|calabrian|sicilian|bulgarian|turkish|egyptian|indian|madagascar|bourbon|haitian|java|" \
         r"indonesian|virginia|virginian|atlas|texas|tunisian|moroccan|french|brazilian|mexican|tahitian|" \
         r"australian|mysore|cambodian|laotian|chinese|ceylon|guatemalan|nigerian|spanish|persian|omani|" \
         r"absolute|absolu|oil|essence|extract|accord|concrete|co2|leaf oil|heart|pure|fresh|green|white|" \
         r"black|red|pink|sweet|wild|dark|natural|precious|rare|smoked|smoky)\b"


# Variantes frecuentes en tiendas que no estaban en Kaggle con ese nombre.
EXTRA = {"floral": "floral notes", "fruity": "fruity notes", "woody": "woody notes", "woods": "woody notes",
         "soft woods": "woody notes", "marine": "marine notes", "aquatic": "water notes", "passion fruit": "passionfruit",
         "cocoa": "cacao", "ambrox": "ambroxan", "ambrofix": "ambroxan", "dry amber": "amber", "amber": "amber",
         "aromatic herbs": "herbal notes", "herbs": "herbal notes", "cistus": "labdanum", "smoky notes": "smoke",
         "spicy": "spicy notes", "citrus": "citrus notes", "musky": "musk", "musks": "musk", "lavandin": "lavender",
         "sweet": "sweet notes", "powdery": "powdery notes", "leather accord": "leather", "oud accord": "oud"}


N_ACORDES = 8


def canon(nota: str, vocab: set) -> str | None:
    n = nota.strip().lower()
    if EXTRA.get(n) in vocab:
        return EXTRA[n]
    for cand in [n, norm.SINONIMOS.get(n, n)]:
        if cand in vocab:
            return cand
    base = re.sub(r"\s+", " ", re.sub(ORIGEN, " ", n)).strip()
    for cand in [base, norm.SINONIMOS.get(base, base), EXTRA.get(base, ""), base.rstrip("s"),
                 norm.SINONIMOS.get(base.rstrip("s"), "")]:
        if cand and cand in vocab:
            return cand
    return None


def main():
    modelo = joblib.load(RAIZ / "models/modelo_notas_acordes.joblib")
    vocab = set(modelo.mlb.classes_)
    con = duckdb.connect(str(RAIZ / "data/processed/perfumes.duckdb"))
    # Se lee de la base para usar los mismos id_propio que creó el paso 2.
    p = con.execute("SELECT * FROM perfumes_propios ORDER BY id_propio").df()

    filas, no_reconocidas = [], []
    for _, r in p.iterrows():
        crudas = [x for c in ["notas_salida", "notas_corazon", "notas_fondo"]
                  for x in re.split(r",\s*", r[c]) if x.strip()]
        if not crudas:
            continue
        ok = []
        for x in crudas:
            c = canon(x, vocab)
            (ok.append(c) if c else no_reconocidas.append(x.strip().lower()))
        ok = sorted(set(ok))
        filas.append((r.id_propio, r.marca, r.perfume, ok, len(ok), len(crudas)))

    est = pd.DataFrame(filas, columns=["id_propio", "marca", "perfume", "notas", "notas_usadas", "notas_totales"])
    est = est[est.notas_usadas > 0].reset_index(drop=True)
    V = modelo.estimar(list(est.notas))
    salida = []
    for i, r in est.iterrows():
        top = np.argsort(-V[i])[:N_ACORDES]
        top = [j for j in top if V[i][j] > 0.02]
        cobertura = r.notas_usadas / r.notas_totales
        conf = "alta" if r.notas_usadas >= 5 and cobertura >= 0.7 else "media" if r.notas_usadas >= 3 else "baja"
        for k, j in enumerate(top, start=1):
            salida.append((r.id_propio, r.marca, r.perfume, k, modelo.acordes[j], round((11 - k) / 10, 1),
                           round(float(V[i][j]), 3), r.notas_usadas, r.notas_totales, conf))
    out = pd.DataFrame(salida, columns=["id_propio", "marca", "perfume", "posicion", "acorde", "peso",
                                        "valor_modelo", "notas_usadas", "notas_totales", "confianza"])
    out.to_csv(RAIZ / "data/processed/acordes_estimados_propios.csv", index=False, encoding="utf-8")

    con.register("tmp", out)
    con.execute("CREATE OR REPLACE TABLE acordes_estimados_propios AS SELECT * FROM tmp")
    con.unregister("tmp")
    con.close()

    conf = out.drop_duplicates("id_propio").confianza.value_counts()
    print(f"perfumes de la capa propia: {len(p)} | con notas: {len(filas)} | con acordes estimados: {out.id_propio.nunique()}")
    print("confianza:", conf.to_dict())
    nr = pd.Series(no_reconocidas).value_counts()
    print(f"notas no reconocidas: {len(nr)} distintas ({nr.sum()} apariciones). Más comunes:", nr.head(15).to_dict())


if __name__ == "__main__":
    main()
