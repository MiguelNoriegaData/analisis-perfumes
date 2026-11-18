"""Paso 2: construir la base analítica perfumes.duckdb.

Fuentes:
  data/raw/fra_perfumes.csv          Kaggle, ~70k perfumes, hasta 10 acordes ordenados (base principal)
  data/raw/fra_cleaned.csv           Kaggle, subconjunto ~24k con notas por nivel ya separadas y año
  data/processed/marcas_categorias.csv   tabla propia marca -> categoría
  data/processed/ranking_emparejado.csv  ranking personal emparejado (paso 1)
  data/processed/perfumes_propios.csv    capa propia (lanzamientos 2024+, catálogo)

Dataset de Kaggle: "Fragrantica.com Fragrance Dataset", Olga G (Miufana1), licencia CC BY-NC-SA 4.0.
Las tablas *_kaggle son datos derivados bajo esa misma licencia.

Tablas resultantes:
  perfumes_kaggle(fragrantica_id, slug, marca_slug, nombre, genero, rating, votos, anio, familia, perfumistas, url)
  acordes_kaggle(fragrantica_id, posicion, acorde, peso)        peso = (11 - posicion) / 10
  notas_kaggle(fragrantica_id, nivel, nota, fuente_notas)        nivel: salida/corazon/fondo/sin_nivel
  marcas_categorias(marca, categoria, grupo, ...) + marca_slug(marca, marca_slug)
  reasignacion_marca: perfumes que Fragrantica registró bajo otra marca (se corrigen por fragrantica_id)
  ranking_personal, perfumes_propios, notas_propias
  vista v_perfumes: perfumes de Kaggle con su categoría + capa propia, con columna fuente_datos
"""
import ast
import re
from pathlib import Path

import duckdb
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
RAW, PROC = RAIZ / "data/raw", RAIZ / "data/processed"
DB = PROC / "perfumes.duckdb"

GENERO = {"for men": "masculino", "for women": "femenino", "for women and men": "unisex"}


def lista_notas(texto: str) -> list[str]:
    """'Lemon, Mandarin Orange and Pink Pepper' -> ['lemon', 'mandarin orange', 'pink pepper']"""
    if not isinstance(texto, str) or not texto.strip():
        return []
    partes = re.split(r",\s*|\s+and\s+", texto.strip().rstrip("."))
    return [p.strip().lower() for p in partes if p.strip()]


def notas_desde_descripcion(desc: str) -> dict[str, list[str]]:
    out = {}
    if not isinstance(desc, str):
        return out
    for nivel, patron in [("salida", r"top notes? (?:are|is) (.*?)(?:;|\.(?:\s|$))"),
                          ("corazon", r"middle notes? (?:are|is) (.*?)(?:;|\.(?:\s|$))"),
                          ("fondo", r"base notes? (?:are|is) (.*?)(?:;|\.(?:\s|$)|$)")]:
        m = re.search(patron, desc, flags=re.I)
        if m:
            out[nivel] = lista_notas(m.group(1))
    return out


def cargar_kaggle() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    p = pd.read_csv(RAW / "fra_perfumes.csv")
    p["fragrantica_id"] = p.url.str.extract(r"-(\d+)\.html$")[0].astype(int)
    p = p.drop_duplicates("fragrantica_id").reset_index(drop=True)
    p["slug"] = p.url.str.extract(r"/perfume/(.+)-\d+\.html$")[0]
    p["marca_slug"] = p.slug.str.split("/").str[0]
    p["nombre"] = p.slug.str.split("/").str[1].str.replace("-", " ")
    p["genero"] = p.Gender.map(GENERO)
    p["rating"] = pd.to_numeric(p["Rating Value"], errors="coerce")
    p["votos"] = pd.to_numeric(p["Rating Count"].astype(str).str.replace(",", ""), errors="coerce").astype("Int64")
    p["anio"] = pd.to_numeric(p.Description.str.extract(r"launched in (\d{4})")[0], errors="coerce").astype("Int64")
    p["familia"] = p.Description.str.extract(r"is an? (.+?) fragrance for")[0].str.lower()

    c = pd.read_csv(RAW / "fra_cleaned.csv", sep=";", encoding="latin-1")
    c["fragrantica_id"] = c.url.str.extract(r"-(\d+)\.html$")[0].astype(int)
    anio_c = c.set_index("fragrantica_id").Year
    p["anio"] = p.anio.fillna(p.fragrantica_id.map(anio_c).astype("Int64"))
    p["perfumistas"] = p.Perfumers.apply(lambda s: ", ".join(ast.literal_eval(s)) if isinstance(s, str) and s.startswith("[") else None)
    p["perfumistas"] = p.perfumistas.replace("", None)

    perfumes = p[["fragrantica_id", "slug", "marca_slug", "nombre", "genero", "rating", "votos",
                  "anio", "familia", "perfumistas", "url"]]

    # Acordes: hasta 10, en el orden en que Fragrantica los muestra (de mayor a menor presencia).
    filas = []
    for fid, acc in zip(p.fragrantica_id, p["Main Accords"]):
        if isinstance(acc, str) and acc.startswith("["):
            for i, a in enumerate(ast.literal_eval(acc), start=1):
                filas.append((fid, i, a.strip().lower(), round((11 - i) / 10, 1)))
    acordes = pd.DataFrame(filas, columns=["fragrantica_id", "posicion", "acorde", "peso"])

    # Notas: estructuradas de fra_cleaned cuando existen; si no, extraídas de la descripción.
    notas, con_cleaned = [], set()
    for _, r in c.iterrows():
        for nivel, col in [("salida", "Top"), ("corazon", "Middle"), ("fondo", "Base")]:
            for n in lista_notas(r[col]):
                notas.append((r.fragrantica_id, nivel, n, "fra_cleaned"))
        con_cleaned.add(r.fragrantica_id)
    for fid, desc in zip(p.fragrantica_id, p.Description):
        if fid in con_cleaned:
            continue
        for nivel, lista in notas_desde_descripcion(desc).items():
            for n in lista:
                notas.append((fid, nivel, n, "descripcion"))
    notas = pd.DataFrame(notas, columns=["fragrantica_id", "nivel", "nota", "fuente_notas"]).drop_duplicates()
    notas = notas[notas.fragrantica_id.isin(set(perfumes.fragrantica_id))]
    return perfumes, acordes, notas


def notas_propias(prop: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for _, r in prop.iterrows():
        for nivel, col in [("salida", "notas_salida"), ("corazon", "notas_corazon"), ("fondo", "notas_fondo")]:
            for n in lista_notas(r.get(col)):
                filas.append((r.id_propio, nivel, n))
    return pd.DataFrame(filas, columns=["id_propio", "nivel", "nota"])


def main() -> None:
    perfumes, acordes, notas = cargar_kaggle()
    marcas = pd.read_csv(PROC / "marcas_categorias.csv", keep_default_na=False)
    marca_slug = (marcas.assign(marca_slug=marcas.slugs_dataset.str.split("|"))
                  .explode("marca_slug").query("marca_slug != ''")[["marca", "marca_slug"]])
    # Perfumes que Fragrantica registró bajo otra marca (p. ej. French Avenue bajo Fragrance-World).
    reasig = pd.read_csv(PROC / "reasignacion_marca.csv", keep_default_na=False)
    reasig = reasig[reasig.marca_correcta != reasig.marca_kaggle.str.replace("-", " ")].copy()
    # Las filas sin fragrantica_id se completan con el registro exacto del dataset (marca/nombre del slug).
    por_slug = perfumes.drop_duplicates("slug", keep=False).set_index("slug").fragrantica_id
    sin_id = reasig.fragrantica_id.astype(str).str.strip().eq("")
    reasig["fragrantica_id"] = pd.to_numeric(reasig.fragrantica_id, errors="coerce")
    reasig.loc[sin_id, "fragrantica_id"] = (reasig.marca_kaggle + "/" + reasig.nombre_kaggle)[sin_id].map(por_slug)
    no_hallados = reasig[reasig.fragrantica_id.isna()]
    if len(no_hallados):
        print("reasignaciones sin registro exacto en Kaggle (no se aplican):",
              (no_hallados.marca_kaggle + "/" + no_hallados.nombre_kaggle).tolist())
    reasig = reasig.dropna(subset=["fragrantica_id"]).drop_duplicates("fragrantica_id")
    reasig["fragrantica_id"] = reasig.fragrantica_id.astype("int64")
    ranking = pd.read_csv(PROC / "ranking_emparejado.csv")
    prop = pd.read_csv(PROC / "perfumes_propios.csv", keep_default_na=False)
    prop.insert(0, "id_propio", [f"P{i:05d}" for i in range(1, len(prop) + 1)])
    prop["anio"] = pd.to_numeric(prop.anio, errors="coerce").astype("Int64")
    # Notas tomadas de Fragrantica (decisión del autor): sirven para el portafolio, no para lo monetizable.
    prop["uso_permitido"] = prop.fuente_tipo.eq("fragrantica").map({True: "solo_portafolio", False: "capa_propia"})

    DB.unlink(missing_ok=True)
    con = duckdb.connect(str(DB))
    for nombre, df in [("perfumes_kaggle", perfumes), ("acordes_kaggle", acordes), ("notas_kaggle", notas),
                       ("marcas_categorias", marcas), ("marca_slug", marca_slug), ("reasignacion_marca", reasig), ("ranking_personal", ranking),
                       ("perfumes_propios", prop), ("notas_propias", notas_propias(prop))]:
        con.register("tmp", df)
        con.execute(f"CREATE TABLE {nombre} AS SELECT * FROM tmp")
        con.unregister("tmp")

    con.execute("""
        CREATE VIEW v_perfumes AS
        SELECT 'kaggle' AS fuente_datos, CAST(k.fragrantica_id AS VARCHAR) AS id, k.nombre,
               COALESCE(ra.marca_correcta, ms.marca, k.marca_slug) AS marca, mc.categoria, NULLIF(mc.grupo, '') AS grupo,
               k.genero, k.anio, k.rating, k.votos, 'solo_portafolio' AS uso_permitido
        FROM perfumes_kaggle k
        LEFT JOIN marca_slug ms ON ms.marca_slug = k.marca_slug
        LEFT JOIN reasignacion_marca ra ON ra.fragrantica_id = k.fragrantica_id
        LEFT JOIN marcas_categorias mc ON mc.marca = COALESCE(ra.marca_correcta, ms.marca)
        UNION ALL
        SELECT 'propia', p.id_propio, lower(p.perfume), p.marca, mc.categoria, NULLIF(mc.grupo, '') AS grupo, p.genero, p.anio,
               NULL, NULL, p.uso_permitido
        FROM perfumes_propios p
        LEFT JOIN marcas_categorias mc ON mc.marca = p.marca
    """)
    for t in ["perfumes_kaggle", "acordes_kaggle", "notas_kaggle", "marcas_categorias", "marca_slug",
              "ranking_personal", "perfumes_propios", "notas_propias"]:
        print(f"{t:20s} {con.execute(f'SELECT count(*) FROM {t}').fetchone()[0]:>8,}")
    con.close()


if __name__ == "__main__":
    main()
