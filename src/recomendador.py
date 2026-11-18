"""Recomendador de perfumes por similitud de acordes (coseno).

Cómo funciona
-------------
- Cada perfume es un vector de 90 acordes. El peso de cada acorde depende de su posición en Fragrantica
  (1.º = 1.0, 2.º = 0.9 ... 10.º = 0.1): el dataset trae el orden de los acordes, no su intensidad.
- Entrada A (acordes y/o notas que te gustan):
    * acorde elegido -> peso 1 en ese acorde.
    * nota elegida -> se traduce a acordes con el perfil promedio de los perfumes que llevan esa nota
      (asociación aprendida del dataset, no una regla de perfumería).
- Entrada B (perfumes que te gustan): el perfil es el promedio de sus vectores. Se muestra al usuario.
- Penalización opcional: lo que no te gusta (acordes, notas o perfumes) forma un perfil negativo.
    puntaje = parecido(perfil, x) - LAMBDA * parecido(perfil_negativo, x)
  Se ordena por puntaje, pero se muestra el % de parecido sin penalizar y aparte la penalización.
- Salida: los mejores de cada categoría (Diseñador, Árabe, Nicho, Catálogo), excluyendo los perfumes de entrada.
- modo: "portafolio" (por defecto) usa todo; "publico" deja solo la capa propia y quita los datos de Kaggle
  y las filas con notas de Fragrantica. Aun así, los acordes estimados vienen de un modelo entrenado con
  Kaggle (licencia CC BY-NC-SA): revisar eso antes de monetizar.
- Perfumes de la capa propia (2024+, catálogo): entran con acordes ESTIMADOS a partir de sus notas
  (columna fuente_acordes = "estimado"); solo los de confianza alta o media. Los de Kaggle llevan
  "comunidad" (votos de Fragrantica).

Importante: el % es parecido de acordes, NO probabilidad de que te guste.

Filtros
-------
- genero: por defecto masculino + unisex.
- min_votos: por defecto 50. Con pocos votos los acordes de Fragrantica son inestables; es un umbral de
  confiabilidad del dato, no de calidad del perfume.
- clima (opcional, None por defecto): 'calor' baja los perfumes de perfil cálido; 'frio' baja los frescos.
  El índice cálido = proporción del peso del perfume en acordes cálidos/dulces. Es criterio propio y solo
  se aplica si el usuario lo pide: cada quien decide cuándo usar su perfume.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
DB = RAIZ / "data/processed/perfumes.duckdb"
LAMBDA = 0.5
# En la validación temporal (perfumes 2023-2024), el parecido calculado con acordes estimados salió en
# promedio ~3 puntos más alto que con los acordes reales. Se corrige restándolo a los estimados.
AJUSTE_ESTIMADO = 0.03
MAX_NOTAS = 6
CATEGORIAS = ["Diseñador", "Árabe", "Nicho", "Catálogo"]
ACORDES_CALIDOS = {"sweet", "vanilla", "amber", "warm spicy", "caramel", "honey", "tobacco", "coffee",
                   "cacao", "chocolate", "cinnamon", "balsamic", "oud", "rum", "whiskey", "almond",
                   "gourmand", "leather", "smoky"}

ACORDE_ES = {
    "woody": "amaderado", "powdery": "atalcado", "citrus": "cítrico", "sweet": "dulce", "aromatic": "aromático",
    "warm spicy": "especiado cálido", "floral": "floral", "fresh spicy": "especiado fresco", "amber": "ámbar",
    "fruity": "frutal", "musky": "almizclado", "white floral": "floral blanco", "vanilla": "vainilla",
    "fresh": "fresco", "green": "verde", "rose": "rosa", "earthy": "terroso", "patchouli": "pachulí",
    "balsamic": "balsámico", "animalic": "animálico", "soft spicy": "especiado suave", "leather": "cuero",
    "aquatic": "acuático", "lavender": "lavanda", "herbal": "herbal", "violet": "violeta", "iris": "iris",
    "oud": "oud", "yellow floral": "floral amarillo", "mossy": "musgoso", "smoky": "ahumado",
    "tropical": "tropical", "ozonic": "ozónico", "lactonic": "lácteo", "cinnamon": "canela", "tuberose": "nardo",
    "tobacco": "tabaco", "marine": "marino", "honey": "miel", "caramel": "caramelo", "almond": "almendra",
    "nutty": "a nuez", "coconut": "coco", "aldehydic": "aldehídico", "salty": "salado", "metallic": "metálico",
    "cacao": "cacao", "anis": "anís", "coffee": "café", "chocolate": "chocolate", "cherry": "cereza",
    "conifer": "conífera", "terpenic": "terpénico", "savory": "salado-umami", "champagne": "champaña", "oily": "aceitoso",
    "alcohol": "alcohólico", "beeswax": "cera de abeja", "sand": "arena", "wine": "vino", "foresty": "boscoso", "rum": "ron", "soapy": "jabonoso", "sour": "ácido", "mineral": "mineral",
    "camphor": "alcanforado", "whiskey": "whisky", "bitter": "amargo", "gourmand": "gourmand",
}


def es(acorde: str) -> str:
    return ACORDE_ES.get(acorde, acorde)


@dataclass
class Datos:
    meta: pd.DataFrame          # una fila por perfume (índice = fragrantica_id)
    X: np.ndarray               # matriz normalizada perfume x acorde
    acordes: list[str]
    notas: pd.DataFrame         # fragrantica_id, nota (canónica), nota_es
    idx: dict[int, int]         # fragrantica_id -> fila de X
    calido: np.ndarray          # índice cálido 0..1 por perfume


def cargar() -> Datos:
    con = duckdb.connect(str(DB), read_only=True)
    a = con.execute("SELECT fragrantica_id, acorde, peso FROM acordes_kaggle").df()
    meta = con.execute("""
        SELECT k.fragrantica_id, k.nombre,
               COALESCE(ra.marca_correcta, ms.marca, replace(k.marca_slug, '-', ' ')) AS marca,
               COALESCE(mc.categoria, 'Otra') AS categoria, NULLIF(mc.grupo, '') AS grupo, k.genero, k.anio, k.rating, k.votos
        FROM perfumes_kaggle k
        LEFT JOIN marca_slug ms ON ms.marca_slug = k.marca_slug
        LEFT JOIN reasignacion_marca ra ON ra.fragrantica_id = k.fragrantica_id
        LEFT JOIN marcas_categorias mc ON mc.marca = COALESCE(ra.marca_correcta, ms.marca)""").df()
    notas = con.execute("""SELECT DISTINCT CAST(id AS INTEGER) AS fragrantica_id, nota, nota_es
                           FROM v_notas WHERE fuente_datos = 'kaggle'""").df()
    meta["fuente_acordes"] = "comunidad"
    meta["uso_permitido"] = "solo_portafolio"
    meta["confianza_acordes"] = None

    # Capa propia: acordes ESTIMADOS por el modelo notas -> acordes (07_estimar_acordes_propios.py).
    # Se les da un id interno negativo (-N para P0000N) para que convivan con los fragrantica_id.
    tablas = {t[0] for t in con.execute("SHOW TABLES").fetchall()}
    if "acordes_estimados_propios" in tablas:
        ap = con.execute("""SELECT -CAST(substr(id_propio, 2) AS INTEGER) AS fragrantica_id, acorde,
                                   peso, confianza FROM acordes_estimados_propios""").df()
        mp = con.execute("""
            SELECT -CAST(substr(p.id_propio, 2) AS INTEGER) AS fragrantica_id, lower(p.perfume) AS nombre, p.marca,
                   COALESCE(mc.categoria, 'Otra') AS categoria, NULLIF(mc.grupo, '') AS grupo, p.genero,
                   TRY_CAST(p.anio AS INTEGER) AS anio, NULL AS rating, NULL AS votos, p.uso_permitido
            FROM perfumes_propios p LEFT JOIN marcas_categorias mc ON mc.marca = p.marca""").df()
        conf = ap.drop_duplicates("fragrantica_id").set_index("fragrantica_id").confianza
        mp = mp[mp.fragrantica_id.isin(conf.index)]
        mp["fuente_acordes"] = "estimado"
        mp["confianza_acordes"] = mp.fragrantica_id.map(conf)
        npr = con.execute("""SELECT DISTINCT -CAST(substr(id, 2) AS INTEGER) AS fragrantica_id, nota, nota_es
                             FROM v_notas WHERE fuente_datos = 'propia'""").df()
        a = pd.concat([a, ap[["fragrantica_id", "acorde", "peso"]]])
        meta = pd.concat([meta, mp], ignore_index=True)
        notas = pd.concat([notas, npr], ignore_index=True)
    con.close()

    acordes = sorted(a.acorde.unique())
    meta = meta[meta.fragrantica_id.isin(a.fragrantica_id.unique())].reset_index(drop=True)
    idx = {fid: i for i, fid in enumerate(meta.fragrantica_id)}
    col = {ac: j for j, ac in enumerate(acordes)}
    M = np.zeros((len(meta), len(acordes)), dtype=np.float32)
    a = a[a.fragrantica_id.isin(idx)]
    M[a.fragrantica_id.map(idx).values, a.acorde.map(col).values] = a.peso.values
    calidos = [col[c] for c in ACORDES_CALIDOS if c in col]
    calido = M[:, calidos].sum(1) / np.maximum(M.sum(1), 1e-9)
    X = M / np.maximum(np.linalg.norm(M, axis=1, keepdims=True), 1e-9)
    return Datos(meta.set_index("fragrantica_id", drop=False), X, acordes, notas, idx, calido)


def _unit(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 0 else v


def perfil_desde_acordes_y_notas(d: Datos, acordes: list[str] = (), notas: list[str] = ()) -> np.ndarray:
    v = np.zeros(len(d.acordes), dtype=np.float32)
    for ac in acordes:
        if ac not in d.acordes:
            raise ValueError(f"Acorde desconocido: {ac}")
        v[d.acordes.index(ac)] += 1.0
    for nota in notas:
        ids = d.notas.loc[d.notas.nota == nota, "fragrantica_id"]
        filas = [d.idx[i] for i in ids if i in d.idx]
        if not filas:
            raise ValueError(f"Nota sin perfumes en el dataset: {nota}")
        v += _unit(d.X[filas].mean(0))
    return _unit(v)


def perfil_desde_perfumes(d: Datos, ids: list[int]) -> np.ndarray:
    filas = [d.idx[i] for i in ids if i in d.idx]
    return _unit(d.X[filas].mean(0)) if filas else np.zeros(len(d.acordes))


def describir_perfil(d: Datos, v: np.ndarray, n: int = 8) -> pd.DataFrame:
    """Peso relativo de cada acorde en el perfil (suma 100 % sobre los acordes mostrados)."""
    s = pd.Series(v, index=d.acordes)
    s = s[s > 0].sort_values(ascending=False)
    return pd.DataFrame({"acorde": [es(a) for a in s.index[:n]],
                         "peso_%": (s.iloc[:n].astype(float) / float(s.sum()) * 100).round(1).values})


def recomendar(d: Datos, *, perfumes: list[int] = (), acordes: list[str] = (), notas: list[str] = (),
               no_perfumes: list[int] = (), no_acordes: list[str] = (), no_notas: list[str] = (),
               generos=("masculino", "unisex"), min_votos: int = 50, clima: str | None = None,
               n_por_categoria: int = 5, categorias=CATEGORIAS, incluir_estimados: bool = True,
               modo: str = "portafolio") -> dict:
    if modo not in ("portafolio", "publico"):
        raise ValueError("modo debe ser 'portafolio' o 'publico'")
    partes = []
    if perfumes:
        partes.append(perfil_desde_perfumes(d, list(perfumes)))
    if acordes or notas:
        partes.append(perfil_desde_acordes_y_notas(d, list(acordes), list(notas)))
    if not partes:
        raise ValueError("Pon al menos un perfume, acorde o nota que te guste.")
    perfil = _unit(np.sum(partes, axis=0))

    negativos = []
    if no_perfumes:
        negativos.append(perfil_desde_perfumes(d, list(no_perfumes)))
    if no_acordes or no_notas:
        negativos.append(perfil_desde_acordes_y_notas(d, list(no_acordes), list(no_notas)))
    neg = _unit(np.sum(negativos, axis=0)) if negativos else None

    parecido = d.X @ perfil
    parecido = np.where(d.meta.fuente_acordes.eq("estimado").values, np.clip(parecido - AJUSTE_ESTIMADO, 0, None),
                        parecido)
    penal = (d.X @ neg) if neg is not None else np.zeros_like(parecido)
    puntaje = parecido - LAMBDA * penal
    if clima == "calor":
        puntaje = puntaje - 0.5 * d.calido
    elif clima == "frio":
        puntaje = puntaje - 0.5 * (1 - d.calido)

    m = d.meta.copy()
    m["parecido_%"] = (parecido.astype(float) * 100).round(1)
    m["penalizacion_%"] = (penal.astype(float) * 100).round(1)
    m["puntaje"] = puntaje
    m["indice_calido"] = d.calido.round(2)
    excluir = set(perfumes) | set(no_perfumes)
    es_estimado = m.fuente_acordes.eq("estimado")
    confiable = (m.votos.fillna(0) >= min_votos) | (es_estimado & m.confianza_acordes.isin(["alta", "media"]))
    if not incluir_estimados:
        confiable &= ~es_estimado
    if modo == "publico":
        confiable &= m.uso_permitido.eq("capa_propia")
    m = m[~m.fragrantica_id.isin(excluir) & m.genero.isin(generos) & confiable]

    # notas de referencia, ordenadas por cuántos perfumes de entrada las llevan (más compartidas primero)
    frec = d.notas.loc[d.notas.fragrantica_id.isin(perfumes)].groupby("nota").size()
    frec = pd.concat([frec, pd.Series(len(perfumes) + 1, index=list(notas), dtype=int)])
    frec = frec.groupby(level=0).max()
    nota_es = d.notas.drop_duplicates("nota").set_index("nota").nota_es.dropna()

    salida = {}
    for cat in categorias:
        top = m[m.categoria == cat].nlargest(n_por_categoria, "puntaje").copy()
        comunes = []
        for fid in top.fragrantica_id:
            suyas = set(d.notas.loc[d.notas.fragrantica_id == fid, "nota"])
            compartidas = sorted(suyas & set(frec.index), key=lambda x: (-frec[x], x))[:MAX_NOTAS]
            comunes.append(", ".join(nota_es.get(x, x) for x in compartidas) or "—")
        top["notas_en_comun"] = comunes
        acs = [", ".join(es(d.acordes[j]) for j in np.argsort(-d.X[d.idx[fid]])[:4]) for fid in top.fragrantica_id]
        top["acordes_principales"] = acs
        salida[cat] = top[["nombre", "marca", "anio", "parecido_%", "penalizacion_%", "fuente_acordes",
                           "acordes_principales", "notas_en_comun", "votos", "rating"]].reset_index(drop=True)
    return {"perfil": describir_perfil(d, perfil), "recomendaciones": salida}
