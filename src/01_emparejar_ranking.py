"""Paso 1: emparejar el ranking personal con el dataset de Fragrantica (Kaggle).

Entrada:  data/raw/ranking_perfumes.csv, data/raw/fra_perfumes.csv
Salida:   data/processed/ranking_emparejado.csv

Método:
  1. Se filtra el dataset por la marca del ranking (tabla MARCA_SLUG).
  2. Se compara el nombre normalizado contra los nombres de esa marca (rapidfuzz WRatio).
  3. Las decisiones que no salen solas del puntaje (versión, concentración, género)
     se fijan a mano en DECISIONES_MANUALES con su justificación.
Confianza: alta = nombre idéntico o decisión inequívoca; media = equivalencia de nombre
plausible que conviene confirmar; baja / sin_match = revisar a mano o no está en el dataset.
"""
import re
import unicodedata
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

RAIZ = Path(__file__).resolve().parents[1]

MARCA_SLUG = {
    "Maison Alhambra": ["Maison-Alhambra"],
    "Lattafa": ["Lattafa-Perfumes"],
    "Armaf": ["Armaf"],
    "Rasasi": ["Rasasi"],
    "Afnan": ["Afnan", "Zimaya"],
    "Giorgio Armani": ["Giorgio-Armani"],
    "Al Haramain": ["Al-Haramain-Perfumes"],
    "Dumont": ["Dumont"],
    "Nautica": ["Nautica"],
    "Ésika": ["Esika"],
}

# rank -> (slug elegido o None, método, confianza, justificación)
DECISIONES_MANUALES = {
    2: ("Lattafa-Perfumes/Fakhar-Black-70465", "manual", "alta",
        "'Fakhar Men' = Fakhar Black (versión masculina); confirmado por el usuario"),
    3: ("Armaf/Club-de-Nuit-Blue-Iconic-", "manual", "alta",
        "Club de Nuit Iconic = 'Club de Nuit Blue Iconic'; confirmado por el usuario"),
    8: ("Lattafa-Perfumes/Ramz-Lattafa-Silver-", "manual", "alta",
        "En Fragrantica el nombre incluye la marca: 'Ramz Lattafa Silver'"),
    12: ("Rasasi/Hawas-Ice-for-Him-", "manual", "alta", "Nombre oficial 'Hawas Ice for Him'"),
    15: ("Giorgio-Armani/Acqua-di-Gio-", "manual", "alta",
         "Usuario confirmó el clásico; se toma la versión masculina (hay homónima femenina)"),
    19: ("Armaf/Odyssey-Aqua-Edition-", "manual", "alta", "Nombre oficial 'Odyssey Aqua Edition'"),
    20: ("Nautica/Nautica-Voyage-913", "manual", "alta", "Voyage clásico EDT"),
    21: ("Zimaya/Ghyoom-", "manual", "alta", "Registrado bajo la marca Zimaya (sublínea de Afnan)"),
    30: ("Armaf/Hunter-Men-27695", "manual", "alta",
         "Hunter EDT masculino = 'Hunter Men' (el 'Hunter' a secas es femenino); confirmado por el usuario"),
    33: (None, "sin_match", "baja",
         "Solo existen 'Magnat' y 'Magnat Imperium'; no se asume que 'Magnat Select' sea el mismo"),
    34: ("Rasasi/Hawas-for-Him-46890", "manual", "alta", "Usuario confirmó: 'original' = Hawas for Him"),
    35: ("Armaf/Club-De-Nuit-Urban-Elixir-77860", "manual", "alta", "Nombre oficial 'Club de Nuit Urban Elixir'"),
}
UMBRAL_EXACTO = 100
UMBRAL_MIN = 95  # por debajo, sin decisión manual, se marca sin_match


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def main() -> None:
    p = pd.read_csv(RAIZ / "data/raw/fra_perfumes.csv")
    p["slug"] = p.url.str.extract(r"/perfume/(.+)\.html$")[0]
    p["fragrantica_id"] = p.url.str.extract(r"-(\d+)\.html$")[0].astype(int)
    p["brand_slug"] = p.slug.str.split("/").str[0]
    p["nombre_norm"] = p.slug.str.split("/").str[1].str.replace(r"-\d+$", "", regex=True).map(norm)
    p["votos"] = pd.to_numeric(p["Rating Count"].astype(str).str.replace(",", ""), errors="coerce")

    r = pd.read_csv(RAIZ / "data/raw/ranking_perfumes.csv")
    filas = []
    for _, x in r.iterrows():
        rank = int(x["rank"])
        sub = p[p.brand_slug.isin(MARCA_SLUG[x.marca])]
        mejor = process.extractOne(norm(x.perfume), sub.nombre_norm.to_dict(), scorer=fuzz.WRatio)
        cand = sub.loc[mejor[2]] if mejor else None
        puntaje = round(mejor[1], 1) if mejor else None

        if rank in DECISIONES_MANUALES:
            slug_pref, metodo, conf, nota = DECISIONES_MANUALES[rank]
            if slug_pref is None:
                elegido = None
            else:
                m = sub[sub.slug.str.startswith(slug_pref)]
                if len(m) > 1:  # homónimos: se prefiere masculino y luego más votos
                    m = m.assign(_h=m.Gender.eq("for men")).sort_values(["_h", "votos"], ascending=False)
                elegido = m.iloc[0] if len(m) else None
        elif puntaje is not None and puntaje >= UMBRAL_EXACTO:
            elegido, metodo, conf, nota = cand, "exacto_normalizado", "alta", ""
        elif puntaje is not None and puntaje >= UMBRAL_MIN:
            elegido, metodo, conf, nota = cand, "difuso", "media", "revisar"
        else:
            elegido, metodo, conf = None, "sin_match", "baja"
            nota = f"No está en el dataset (mejor candidato de la marca: {cand.slug if cand is not None else '-'}, {puntaje})"

        filas.append({
            "rank": rank,
            "nombre_original": x.nombre_original,
            "marca": x.marca,
            "perfume": x.perfume,
            "fragrantica_id": None if elegido is None else int(elegido.fragrantica_id),
            "registro_elegido": None if elegido is None else elegido.slug,
            "genero_dataset": None if elegido is None else elegido.Gender,
            "votos": None if elegido is None else elegido.votos,
            "metodo": metodo,
            "puntaje_difuso": puntaje,
            "confianza": conf,
            "nota": nota,
        })

    out = pd.DataFrame(filas)
    out["fragrantica_id"] = out.fragrantica_id.astype("Int64")
    out["votos"] = out.votos.astype("Int64")
    (RAIZ / "data/processed").mkdir(parents=True, exist_ok=True)
    out.to_csv(RAIZ / "data/processed/ranking_emparejado.csv", index=False, encoding="utf-8")
    print(out[["rank", "perfume", "registro_elegido", "votos", "metodo", "confianza"]].to_string(index=False))
    print("\nResumen:", out.confianza.value_counts().to_dict(), "| emparejados:", out.fragrantica_id.notna().sum(), "de", len(out))


if __name__ == "__main__":
    main()
