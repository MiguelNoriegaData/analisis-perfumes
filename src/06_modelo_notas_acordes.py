"""Paso 6: modelo que estima los acordes de un perfume a partir de sus notas.

Para qué: los perfumes de la capa propia (lanzamientos 2024+, catálogo) solo tienen notas; el recomendador
necesita acordes. Este modelo aprende de Kaggle qué notas suelen ir con qué acordes.

Datos: perfumes de Kaggle con notas y acordes (~46.9k).
  X = notas canónicas (multi-hot, sin distinguir nivel, porque muchas fuentes de la capa propia no traen
      pirámide), ponderadas con TF-IDF.
  y = vector de 90 acordes con peso por posición (1.º = 1.0 … 10.º = 0.1), igual que en el recomendador.
Validación temporal: se entrena con perfumes hasta 2022 (o sin año) y se prueba con 2023–2024, que es
lo más parecido a "un lanzamiento nuevo que el modelo no vio".

Modelos comparados:
  base   = vector promedio de acordes (no usa notas)
  knn    = promedio ponderado de los acordes de los 25 perfumes con notas más parecidas (coseno)
  ridge  = regresión lineal regularizada multi-salida
  mezcla = promedio de knn y ridge
  (también se probó una red neuronal de una capa: 86.3 % de coseno, prácticamente igual que ridge; se
   eligió ridge por ser más simple y explicable)
Métricas (en prueba):
  coseno   = parecido entre el vector estimado y el real (0–100 %)
  top5     = de los 5 acordes principales reales, cuántos aparecen en los 5 estimados
  calidad_vecinos = qué tan buenos son los 10 perfumes que el recomendador elegiría con el vector
             estimado, medidos con el vector real: 100 % = igual de parecidos que los 10 ideales
             (catálogo de referencia: 8,000 perfumes de entrenamiento al azar)

Salidas: data/processed/modelo_notas_acordes_metricas.csv, models/modelo_notas_acordes.joblib
"""
from pathlib import Path

import duckdb
import joblib
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.linear_model import Ridge
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import MultiLabelBinarizer, normalize

RAIZ = Path(__file__).resolve().parents[1]
DB = RAIZ / "data/processed/perfumes.duckdb"
MIN_FREQ = 15
K = 25
SEED = 42


def cargar():
    con = duckdb.connect(str(DB), read_only=True)
    notas = con.execute("""SELECT DISTINCT CAST(id AS INTEGER) AS fid, nota FROM v_notas
                           WHERE fuente_datos = 'kaggle'""").df()
    acordes = con.execute("SELECT fragrantica_id AS fid, acorde, peso FROM acordes_kaggle").df()
    meta = con.execute("SELECT fragrantica_id AS fid, anio, votos FROM perfumes_kaggle").df()
    con.close()
    ids = sorted(set(notas.fid) & set(acordes.fid))
    return notas[notas.fid.isin(ids)], acordes[acordes.fid.isin(ids)], meta.set_index("fid").loc[ids], ids


class ModeloNotasAcordes:
    def __init__(self, vocab_notas, acordes):
        self.mlb = MultiLabelBinarizer(classes=vocab_notas)
        self.mlb.fit([])
        self.tfidf = TfidfTransformer()
        self.acordes = acordes
        self.ridge = Ridge(alpha=3.0)

    def _x(self, listas, fit=False):
        B = self.mlb.transform(listas).astype(np.float32)
        return self.tfidf.fit_transform(B) if fit else self.tfidf.transform(B)

    def fit(self, listas, Y):
        X = self._x(listas, fit=True)
        self.Y = Y
        self.nn = NearestNeighbors(n_neighbors=K, metric="cosine").fit(X)
        self.ridge.fit(X, Y)
        self.media = Y.mean(0)
        return self

    def predecir(self, listas, modo="mezcla"):
        X = self._x(listas)
        if modo == "base":
            return np.tile(self.media, (X.shape[0], 1))
        dist, idx = self.nn.kneighbors(X)
        w = np.clip(1 - dist, 1e-6, None)
        knn = (self.Y[idx] * w[..., None]).sum(1) / w.sum(1, keepdims=True)
        if modo == "knn":
            return knn
        rid = np.clip(self.ridge.predict(X), 0, None)
        if modo == "ridge":
            return rid
        return (knn + rid) / 2

    def estimar(self, notas_por_perfume):
        """Vector de acordes estimado (modelo final = ridge, el mejor en la validación)."""
        return self.predecir(notas_por_perfume, "ridge")


def metricas(P, Y, R, n_vecinos=10):
    Pu, Yu = normalize(P), normalize(Y)
    cos = (Pu * Yu).sum(1)
    top_real = np.argsort(-Y, 1)[:, :5]
    top_est = np.argsort(-P, 1)[:, :5]
    n_real = (Y > 0).sum(1).clip(max=5)
    top5 = np.array([len(set(a[:n]) & set(b)) / n for a, b, n in zip(top_real, top_est, n_real)])
    S = Yu @ R.T
    ideal = np.sort(S, 1)[:, -n_vecinos:].mean(1)
    elegidos = np.argsort(-(Pu @ R.T), 1)[:, :n_vecinos]
    vec = np.take_along_axis(S, elegidos, 1).mean(1) / ideal
    return cos, top5, vec


def main():
    notas, acordes, meta, ids = cargar()
    lista_acordes = sorted(acordes.acorde.unique())
    col = {a: j for j, a in enumerate(lista_acordes)}
    pos = {f: i for i, f in enumerate(ids)}
    Y = np.zeros((len(ids), len(lista_acordes)), dtype=np.float32)
    Y[acordes.fid.map(pos).values, acordes.acorde.map(col).values] = acordes.peso.values

    freq = notas.nota.value_counts()
    vocab = sorted(freq[freq >= MIN_FREQ].index)
    por_perfume = notas[notas.nota.isin(vocab)].groupby("fid").nota.apply(list).reindex(ids)
    por_perfume = por_perfume.apply(lambda v: v if isinstance(v, list) else [])
    n_notas = por_perfume.apply(len).values

    anio = meta.anio.astype("Float64").fillna(0).values
    prueba = (anio >= 2023) & (n_notas > 0)
    entren = ~prueba & (n_notas > 0)
    print(f"vocabulario de notas: {len(vocab)} | entrenamiento: {entren.sum():,} | prueba (2023–2024): {prueba.sum():,}")

    L = por_perfume.values
    m = ModeloNotasAcordes(vocab, lista_acordes).fit(list(L[entren]), Y[entren])
    rng = np.random.default_rng(SEED)
    R = normalize(Y[entren])[rng.choice(entren.sum(), 8000, replace=False)]

    filas = []
    for modo in ["base", "knn", "ridge", "mezcla"]:
        P = m.predecir(list(L[prueba]), modo)
        cos, top5, vec = metricas(P, Y[prueba], R)
        pocas = n_notas[prueba] <= 5
        filas.append({"modelo": modo, "coseno_%": cos.mean() * 100, "top5_%": top5.mean() * 100,
                      "calidad_vecinos_%": vec.mean() * 100, "coseno_%_pocas_notas": cos[pocas].mean() * 100,
                      "n_prueba": int(prueba.sum()), "n_pocas_notas": int(pocas.sum())})
    res = pd.DataFrame(filas).round(1)
    print(res.to_string(index=False))
    res.to_csv(RAIZ / "data/processed/modelo_notas_acordes_metricas.csv", index=False)

    # Modelo final: entrenado con todo, para aplicar a la capa propia.
    final = ModeloNotasAcordes(vocab, lista_acordes).fit(list(L[n_notas > 0]), Y[n_notas > 0])
    (RAIZ / "models").mkdir(exist_ok=True)
    joblib.dump(final, RAIZ / "models/modelo_notas_acordes.joblib")
    print("modelo guardado:", RAIZ / "models/modelo_notas_acordes.joblib")


if __name__ == "__main__":
    main()
