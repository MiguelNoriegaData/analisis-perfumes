"""Huella Olfativa: recomendador de perfumes por similitud de acordes.

Versión gratuita y no comercial. Datos: Fragrantica.com Fragrance Dataset (Olga G, Kaggle), CC BY-NC-SA 4.0,
más una capa propia de lanzamientos 2024–2026 con acordes estimados a partir de sus notas.
Textos, nombre, colores de acordes y catálogos editables en app/textos.py; tema en .streamlit/config.toml.
"""
from __future__ import annotations

import html
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent / "src"))
sys.path.insert(0, str(AQUI))
import recomendador as r  # noqa: E402
import textos as T  # noqa: E402

DATOS = AQUI / "datos"
CATEGORIAS = ["Diseñador", "Árabe", "Nicho", "Catálogo"]
GENEROS = {"masculino": "Masculino", "unisex": "Unisex", "femenino": "Femenino"}
N_INICIAL, N_PASO, N_MAX = 6, 6, 30  # perfumes por categoría: se muestran 6 y "Ver más" agrega 6, hasta 30

st.set_page_config(page_title=T.NOMBRE, page_icon="🫧", layout="wide")

# ---------- estilo (azul noche y plata) ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Jost:wght@200;300;400;500&display=swap');
:root { --fondo:#0B1020; --tarjeta:#141A2E; --borde:#232B45; --texto:#E6E9F0; --suave:#9AA3B8; --plata:#B8C2D6; }
.stApp { background:
  radial-gradient(1100px 520px at 8% -8%, rgba(126,146,196,.20), transparent 60%),
  radial-gradient(800px 480px at 105% 4%, rgba(150,128,206,.10), transparent 60%),
  radial-gradient(900px 600px at 50% 120%, rgba(90,155,213,.08), transparent 60%), #0B1020; }
html, body, [class*="css"], .stMarkdown, p, label, input, textarea, button { font-family:'Jost', sans-serif !important; }
h1, h2, h3 { font-family:'Jost', sans-serif !important; font-weight:300 !important; letter-spacing:.01em; }
h1 { font-size:2.8rem !important; background:linear-gradient(90deg,#F1F3F8,#AEB9D2 60%,#F1F3F8);
  -webkit-background-clip:text; background-clip:text; color:transparent !important; background-size:200% auto;
  animation:brillo 8s linear infinite; }
@keyframes brillo { to { background-position:200% center } }
.marca { font-size:.95rem; color:var(--plata); margin-bottom:-.5rem; display:flex; align-items:center; gap:.45rem; }
.sub { color:var(--suave); font-size:1.08rem; margin-top:-.3rem; max-width:52rem; }
.paso { display:flex; gap:.8rem; align-items:flex-start; margin:1.6rem 0 .3rem; }
.num { flex:0 0 2rem; height:2rem; border-radius:50%; border:1px solid var(--plata); color:var(--plata);
  display:grid; place-items:center; font-size:.95rem; }
.paso-t { font-size:1.35rem; font-weight:300; line-height:1.2; }
.nota-fina { color:var(--suave); font-size:.88rem; }
.aviso { background:rgba(184,194,214,.07); border:1px solid var(--borde); border-radius:12px; padding:.6rem .9rem;
  color:var(--texto); font-size:.92rem; margin:.4rem 0 .8rem; animation:aparece .4s ease-out; }
[data-testid="stBaseButton-primary"] { background:linear-gradient(100deg,#8F9BB6,#D7DDEA 50%,#8F9BB6) !important;
  background-size:200% auto !important; color:#0B1020 !important; border:none !important; font-weight:500 !important;
  letter-spacing:.06em; transition:background-position .6s, transform .15s, box-shadow .3s; }
[data-testid="stBaseButton-primary"]:hover { background-position:100% center !important; transform:translateY(-1px);
  box-shadow:0 6px 24px rgba(184,194,214,.25); }
.vivo { background:rgba(20,26,46,.75); border:1px solid var(--borde); border-radius:18px; padding:1rem 1.1rem;
  backdrop-filter:blur(6px); }
.barra { height:.35rem; background:var(--borde); border-radius:1rem; overflow:hidden; margin:.5rem 0 .2rem; }
.barra span { display:block; height:100%; background:linear-gradient(90deg,#6E7A96,#D7DDEA); transition:width .6s; }
.leyenda { display:flex; align-items:center; gap:.5rem; margin:.22rem 0; font-size:.92rem; }
.punto { width:.65rem; height:.65rem; border-radius:50%; flex:0 0 .65rem; }
.nivel { margin-left:auto; color:var(--suave); font-size:.8rem; }
.huella-svg .cresta { animation:tinta .7s ease-out both; }
@keyframes tinta { from { opacity:0; stroke-width:0 } }
.lema { font-style:italic; color:var(--plata); font-size:1.05rem; margin:.2rem 0 .3rem; letter-spacing:.02em; }
.cierre { text-align:center; font-size:1.35rem; font-weight:300; color:var(--texto); margin:2rem 0 1rem; animation:aparece .8s ease-out both; }
.cierre span { color:var(--plata); font-style:italic; }
@keyframes aparece { from { opacity:0; transform:translateY(10px) } to { opacity:1; transform:none } }
.tarjeta { position:relative; background:linear-gradient(160deg,#18203A,#121829); border:1px solid var(--borde);
  border-radius:18px; padding:1rem 1.1rem; margin-bottom:1rem; animation:aparece .5s ease-out both;
  transition:border-color .25s, transform .25s, box-shadow .25s; min-height:13rem; overflow:hidden; }
.tarjeta:hover { border-color:var(--acento, #B8C2D6); transform:translateY(-4px);
  box-shadow:0 10px 30px -12px var(--acento, #B8C2D6); }
.tarjeta::before { content:""; position:absolute; inset:0 0 auto 0; height:3px; background:var(--acento, #B8C2D6); opacity:.8; }
.t-arriba { display:flex; justify-content:space-between; align-items:flex-start; gap:.6rem; }
.t-izq { display:flex; gap:.7rem; align-items:flex-start; }
.t-nombre { font-size:1.12rem; font-weight:400; line-height:1.25; }
.t-marca { color:var(--suave); font-size:.85rem; margin-top:.15rem; }
.insignia { display:inline-block; font-size:.72rem; color:#0B1020; background:var(--plata); border-radius:1rem;
  padding:.05rem .55rem; margin-bottom:.35rem; }
.anillo { flex:0 0 62px; height:62px; border-radius:50%; display:grid; place-items:center; }
.anillo span { width:50px; height:50px; border-radius:50%; background:#141A2E; display:grid; place-items:center;
  font-size:.95rem; color:var(--texto); }
.porque { font-size:.88rem; margin:.65rem 0 .4rem; color:var(--texto); }
.chips { margin:.2rem 0 .4rem; }
.chip { display:inline-block; border-radius:1rem; padding:.08rem .6rem; margin:0 .3rem .3rem 0; font-size:.78rem; }
.t-notas { font-size:.84rem; color:var(--suave); }
.t-notas b { color:var(--plata); font-weight:400; }
.t-fuente { font-size:.72rem; color:var(--suave); margin-top:.45rem; }
.par { display:flex; align-items:center; justify-content:space-between; gap:.8rem; }
[data-testid="stButtonGroup"] > div { flex-wrap:wrap !important; overflow:visible !important; row-gap:.4rem; }
[data-testid="stExpander"] details { border:1px solid #2E3858 !important; border-radius:14px !important;
  background:linear-gradient(160deg,rgba(24,32,58,.9),rgba(18,24,41,.9)); transition:border-color .25s, box-shadow .25s; }
[data-testid="stExpander"] details:hover { border-color:#8F9BB6 !important; }
[data-testid="stExpander"] summary p { font-size:1.02rem; }
[class*="st-key-destacado"] [data-testid="stExpander"] details { border-color:#8F9BB6 !important;
  box-shadow:0 0 0 1px rgba(184,194,214,.15), 0 8px 28px -14px rgba(184,194,214,.6); }
[class*="st-key-destacado"] [data-testid="stExpander"] summary p { font-size:1.2rem; font-weight:400; }
[class*="st-key-destacado"] [data-testid="stExpander"] summary { padding-top:.9rem; padding-bottom:.9rem; }
.st-key-selector_modo [data-testid="stWidgetLabel"] p { font-size:1.1rem; color:var(--plata); }
.st-key-selector_modo button { font-size:1rem !important; padding:.45rem 1.1rem !important; }
.pie { color:var(--suave); font-size:.8rem; text-align:center; margin-top:2.5rem; }
</style>""", unsafe_allow_html=True)


# ---------- datos ----------
def _sin_acentos(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(t).lower()) if unicodedata.category(c) != "Mn")


def bonito(t) -> str:
    t = str(t)
    return t.title() if t == t.lower() else t


@st.cache_resource(show_spinner="Cargando 70 mil perfumes…")
def cargar():
    d = r.cargar_archivos(DATOS)
    m = d.meta.copy()
    m["etiqueta"] = (m.marca.map(bonito) + " – " + m.nombre.map(bonito)
                     + m.anio.map(lambda a: f" ({int(a)})" if pd.notna(a) else ""))
    m["busqueda"] = (m.marca.astype(str) + " " + m.nombre.astype(str)).map(_sin_acentos)
    m["orden"] = m.votos.fillna(0)
    etiquetas = m.set_index("fragrantica_id").etiqueta.to_dict()
    acorde_lbl = {a: r.es(a).capitalize() for a in sorted(d.acordes, key=lambda a: _sin_acentos(r.es(a)))}
    conteo = d.notas.groupby("nota").fragrantica_id.nunique()
    nombres = d.notas.drop_duplicates("nota").set_index("nota").nota_es
    nota_lbl = {n: (nombres.get(n) if isinstance(nombres.get(n), str) else n).capitalize()
                for n in conteo[conteo >= 30].index}
    nota_lbl = dict(sorted(nota_lbl.items(), key=lambda kv: _sin_acentos(kv[1])))
    notas_por_id = d.notas.groupby("fragrantica_id").nota.apply(set).to_dict()
    clones = pd.read_csv(DATOS / "clones.csv") if (DATOS / "clones.csv").exists() else None
    return d, m, etiquetas, acorde_lbl, nota_lbl, notas_por_id, clones


d, M, ETIQ, ACORDE_LBL, NOTA_LBL, NOTAS_ID, CLONES = cargar()
ES_A_ACORDE = {r.es(a): a for a in d.acordes}
FAMILIAS = {f: [n for n in ns if n in NOTA_LBL] for f, ns in T.FAMILIAS_NOTAS.items()}
RAPIDOS = [a for a in T.ACORDES_RAPIDOS if a in ACORDE_LBL]


def color(acorde: str) -> str:
    return T.COLOR_ACORDE.get(acorde, T.COLOR_OTRO)


def buscar(texto: str, n: int = 25) -> list[int]:
    """Busca por palabras que empiezan igual (no por pedazos sueltos) y ordena por relevancia y votos."""
    txt = " " + _sin_acentos(texto) + " "
    for corto, largo in T.ALIAS_BUSQUEDA.items():
        txt = txt.replace(f" {corto} ", f" {largo} ")
    palabras = txt.split()
    if not palabras:
        return []
    ok = pd.Series(True, index=M.index)
    exactas = pd.Series(0, index=M.index)
    for p in palabras:
        ok &= M.busqueda.str.contains(r"(?:^|[\s\-&'])" + re.escape(p), regex=True)
        exactas += M.busqueda.str.contains(r"(?:^|[\s\-&'])" + re.escape(p) + r"(?:$|[\s\-&'])", regex=True)
    if not ok.any():  # si no hay nada por palabras, se busca por pedazos
        ok = pd.Series(True, index=M.index)
        for p in palabras:
            ok &= M.busqueda.str.contains(p, regex=False)
    r_ = M[ok].assign(_ex=exactas[ok])
    return r_.sort_values(["_ex", "orden"], ascending=False).head(n).fragrantica_id.tolist()


def paso(numero: str, titulo: str, detalle: str = ""):
    det = f"<div class='nota-fina'>{html.escape(detalle)}</div>" if detalle else ""
    st.markdown(f"<div class='paso'><div class='num'>{numero}</div><div><div class='paso-t'>{html.escape(titulo)}"
                f"</div>{det}</div></div>", unsafe_allow_html=True)


# ---------- piezas de entrada ----------
def _agregar(clave: str, fid: int):
    lista = st.session_state.setdefault(clave, [])
    if fid not in lista:
        lista.append(fid)
    st.session_state[f"{clave}_txt"] = ""


def _quitar(clave: str):
    quitar = st.session_state.get(f"{clave}_quitar") or []
    st.session_state[clave] = [i for i in st.session_state.get(clave, []) if i not in quitar]
    st.session_state[f"{clave}_quitar"] = []


def selector_perfumes(clave: str, titulo: str, ejemplo: str = "Ej.: bleu de chanel, khamrah, hawas…") -> list[int]:
    lista = st.session_state.setdefault(clave, [])
    texto = st.text_input(titulo, key=f"{clave}_txt", placeholder=ejemplo)
    if texto:
        res = [i for i in buscar(texto) if i not in lista]
        if res:
            c1, c2 = st.columns([4, 1])
            elegido = c1.selectbox("Resultados", res, format_func=ETIQ.get, key=f"{clave}_sel",
                                   label_visibility="collapsed")
            c2.button("Agregar", key=f"{clave}_add", use_container_width=True, on_click=_agregar,
                      args=(clave, elegido))
        else:
            st.caption("No lo encontré. Prueba con menos palabras o solo la marca.")
    if lista:
        st.pills(f"Elegidos ({len(lista)}) · toca uno para quitarlo", lista, selection_mode="multi",
                 format_func=lambda i: f"{ETIQ.get(i, i)}  ✕", key=f"{clave}_quitar", on_change=_quitar,
                 args=(clave,))
    return list(st.session_state[clave])


def selector_acordes(clave: str, titulo: str, describir: bool = True) -> list[str]:
    rapidos = st.pills(titulo, RAPIDOS, selection_mode="multi", format_func=ACORDE_LBL.get, key=f"{clave}_pills")
    otros = st.multiselect("¿Otro aroma?", [a for a in ACORDE_LBL if a not in RAPIDOS], format_func=ACORDE_LBL.get,
                           key=f"{clave}_otros", placeholder="Busca más aromas…")
    elegidos = list(rapidos or []) + list(otros)
    if describir and elegidos:
        filas = "".join(f"<div class='leyenda'><span class='punto' style='background:{color(a)}'></span>"
                        f"<span><b style='font-weight:500'>{html.escape(ACORDE_LBL[a])}</b> · "
                        f"<span class='nota-fina'>{html.escape(T.ACORDES_DESC.get(a, ''))}</span></span></div>"
                        for a in elegidos)
        st.markdown(filas, unsafe_allow_html=True)
    return elegidos


def selector_notas(clave: str, titulo: str) -> list[str]:
    if titulo:
        st.markdown(f"<div class='nota-fina'>{html.escape(titulo)}</div>", unsafe_allow_html=True)
    elegidas: list[str] = []
    familias = st.tabs(list(FAMILIAS))
    for tab, (fam, notas) in zip(familias, FAMILIAS.items()):
        with tab:
            sel = st.pills(fam, notas, selection_mode="multi", format_func=NOTA_LBL.get, key=f"{clave}_{fam}",
                           label_visibility="collapsed")
            elegidas += list(sel or [])
    otras = st.multiselect("¿Otra nota?", list(NOTA_LBL), format_func=NOTA_LBL.get, key=f"{clave}_otras",
                           placeholder="Busca entre más de 400 notas…")
    return list(dict.fromkeys(elegidas + list(otras)))


def selector_favoritos(clave: str, perfumes: list[int], acordes: list[str], notas: list[str]):
    """Intensidad: lo marcado como favorito cuenta doble."""
    opciones = ([("p", i) for i in perfumes] + [("a", a) for a in acordes] + [("n", n) for n in notas])
    if not opciones:
        return perfumes, acordes, notas

    def nombre(o):
        tipo, v = o
        if tipo == "p":
            return ETIQ.get(v, str(v)).split(" – ", 1)[-1]
        return ACORDE_LBL.get(v, v) if tipo == "a" else NOTA_LBL.get(v, v)

    favs = st.pills("¿Alguno es tu favorito absoluto? Cuenta doble.", opciones, selection_mode="multi",
                    format_func=lambda o: f"★ {nombre(o)}", key=f"{clave}_favs") or []
    extra = {"p": [], "a": [], "n": []}
    for tipo, v in favs:
        extra[tipo].append(v)
    return perfumes + extra["p"], acordes + extra["a"], notas + extra["n"]


def filtros(clave: str, anidado: bool = False) -> dict:
    caja = st.popover("Ajustes", icon=":material/tune:") if anidado else st.expander("Ajustes")
    with caja:
        f1, f2, f3 = st.columns(3)
        generos = f1.multiselect("Género", list(GENEROS), default=["masculino", "unisex"], format_func=GENEROS.get,
                                 key=f"{clave}_gen")
        clima = f2.radio("Clima (opcional)", [None, "calor", "frio"], horizontal=True, key=f"{clave}_clima",
                         format_func=lambda c: {None: "Sin filtro", "calor": "Calor", "frio": "Frío"}[c],
                         help="Baja en la lista los perfumes de perfil cálido (calor) o fresco (frío). "
                              "Es un criterio propio: cada quien decide cuándo usar su perfume.")
        estimados = f3.toggle("Incluir lanzamientos 2024–2026", value=True, key=f"{clave}_est",
                              help="Sus acordes los estima un modelo a partir de sus notas.")
    return dict(generos=tuple(generos), clima=clima, incluir_estimados=estimados, n_por_categoria=N_MAX)


# ---------- la huella (visual propia) ----------
def perfil_vivo(perfumes: list[int], acordes: list[str], notas: list[str]) -> pd.DataFrame | None:
    partes = []
    if perfumes:
        partes.append(r.perfil_desde_perfumes(d, perfumes))
    if acordes or notas:
        try:
            partes.append(r.perfil_desde_acordes_y_notas(d, acordes, notas))
        except ValueError:
            pass
    if not partes:
        return None
    v = np.sum(partes, axis=0)
    n = np.linalg.norm(v)
    return r.describir_perfil(d, v / n) if n > 0 else None


def nivel(rel: float) -> str:
    return "Alto" if rel >= .66 else "Medio" if rel >= .33 else "Bajo"


def huella_svg(perfil: pd.DataFrame, tam: int = 250, centro: str = "") -> str:
    """Huella dactilar: cada acorde son dos crestas de su color; los más fuertes, afuera y más completas."""
    top = perfil.head(8)
    if top.empty:
        return ""
    tope = float(top["peso_%"].max())
    acs = [(color(ES_A_ACORDE.get(f.acorde, "")), float(f["peso_%"]) / tope) for _, f in top.iterrows()]
    n = 2 * len(acs)
    W, H = 300, 360
    cx, cy = W / 2, H / 2 + 10
    piezas = [f"<svg class='huella-svg' viewBox='0 0 {W} {H}' width='100%' style='max-width:{tam}px'>"]
    for i in range(n):
        col, w = acs[(n - 1 - i) // 2]
        k = 16 / n  # con pocos acordes, las crestas se separan para llenar el mismo tamaño
        rx, ry = 8 + i * 8.2 * k, 11 + i * 10.5 * k
        frac = .55 + .4 * w
        a0 = np.radians(90 + (1 - frac) * 180 + (i % 3) * 6)
        a1 = np.radians(90 + 360 - (1 - frac) * 180 - (i % 2) * 8)
        t = np.linspace(a0, a1, 70)
        x = cx + rx * np.cos(t) * (1 + .04 * np.sin(3 * t + i))
        y = cy + ry * np.sin(t) * (1 + .03 * np.cos(2 * t + i))
        pts = " ".join(f"{a:.1f},{b:.1f}" for a, b in zip(x, y))
        piezas.append(f"<polyline class='cresta' points='{pts}' fill='none' stroke='{col}' stroke-width='4.2' "
                      f"stroke-linecap='round' stroke-dasharray='{60 + i * 7 * k:.0f} 6' "
                      f"style='animation-delay:{i * 0.05:.2f}s'/>")
    piezas.append("</svg>")
    return "".join(piezas)


def leyenda_html(perfil: pd.DataFrame, n: int = 8) -> str:
    top = perfil.head(n)
    tope = float(top["peso_%"].max()) if len(top) else 1
    return "".join(f"<div class='leyenda'><span class='punto' style='background:{color(ES_A_ACORDE.get(f.acorde, ''))}'>"
                   f"</span>{html.escape(f.acorde.capitalize())}<span class='nivel'>{nivel(f['peso_%'] / tope)}</span></div>"
                   for _, f in top.iterrows())


def frase_huella(perfil: pd.DataFrame, sujeto: str = "Tu huella") -> str:
    top = list(perfil.acorde.head(3))
    if not top:
        return ""
    texto = ", ".join(top[:-1]) + (" y " if len(top) > 1 else "") + top[-1]
    return f"{sujeto} es sobre todo <b>{html.escape(texto)}</b>."


def panel_vivo(perfumes: list[int], acordes: list[str], notas: list[str]):
    senales = len(perfumes) + len(acordes) + len(notas)
    msg = [m for umbral, m in T.MENSAJES_PROGRESO if senales >= umbral][-1]
    perfil = perfil_vivo(perfumes, acordes, notas)
    progreso = min(100, senales * 20)
    cuerpo = ""
    if perfil is not None and not perfil.empty:
        cuerpo = (f"<div style='display:flex;justify-content:center;margin:.6rem 0'>{huella_svg(perfil, 220)}</div>"
                  f"{leyenda_html(perfil, 6)}<div class='nota-fina' style='margin-top:.5rem'>"
                  f"{frase_huella(perfil)}</div>")
    st.markdown(f"<div class='vivo'><div class='paso-t' style='font-size:1.1rem'>Tu huella en vivo</div>"
                f"<div class='barra'><span style='width:{progreso}%'></span></div>"
                f"<div class='nota-fina'>{html.escape(msg)}</div>{cuerpo}</div>", unsafe_allow_html=True)


# ---------- resultados ----------
def anillo(p: float) -> str:
    p = max(0.0, min(100.0, float(p)))
    return (f"<div class='anillo' style='background:conic-gradient(#D7DDEA {p:.1f}%, #232B45 0)'>"
            f"<span>{p:.0f}%</span></div>")


def frasco(col: str) -> str:
    return (f"<svg width='34' height='46' viewBox='0 0 34 46'><rect x='12' y='2' width='10' height='7' rx='1.5' "
            f"fill='#C9D1E2'/><rect x='14' y='9' width='6' height='5' fill='#8F9BB6'/><rect x='3' y='14' width='28' "
            f"height='30' rx='7' fill='{col}' fill-opacity='.85'/><rect x='7' y='18' width='5' height='20' rx='2.5' "
            f"fill='#ffffff' fill-opacity='.25'/></svg>")


def aportes(fid: int, v: np.ndarray) -> pd.Series:
    x = d.X[d.idx[fid]]
    a = pd.Series(x * v, index=d.acordes)
    return a[a > 0].sort_values(ascending=False)


def tarjeta(fila: pd.Series, fid: int, cat: str, v: np.ndarray, primero: bool) -> str:
    anio = f" · {int(fila.anio)}" if pd.notna(fila.anio) else ""
    principal = d.acordes[int(np.argmax(d.X[d.idx[fid]]))]
    col = color(principal)
    comp = [r.es(a) for a in aportes(fid, v).head(3).index]
    porque = (", ".join(comp[:-1]) + (" y " if len(comp) > 1 else "") + comp[-1]) if comp else ""
    chips = "".join(f"<span class='chip' style='border:1px solid {color(ES_A_ACORDE.get(a, ''))}66;"
                    f"color:{color(ES_A_ACORDE.get(a, ''))}'>{html.escape(a)}</span>"
                    for a in str(fila.acordes_principales).split(", "))
    notas = fila.notas_en_comun if fila.notas_en_comun != "—" else ""
    notas_html = f"<div class='t-notas'><b>Notas en común:</b> {html.escape(notas)}</div>" if notas else ""
    insignia = "<div class='insignia'>El más parecido</div>" if primero else ""
    fuente = "acordes votados por la comunidad" if fila.fuente_acordes == "comunidad" else "acordes estimados (2024–2026)"
    return (f"<div class='tarjeta' style='--acento:{col}'>{insignia}<div class='t-arriba'><div class='t-izq'>"
            f"{frasco(col)}<div><div class='t-nombre'>{html.escape(bonito(fila.nombre))}</div>"
            f"<div class='t-marca'>{html.escape(bonito(fila.marca))}{anio} · {cat}</div></div></div>"
            f"{anillo(fila['parecido_%'])}</div>"
            f"<div class='porque'>Comparte contigo: <b style='font-weight:500'>{html.escape(porque)}</b></div>"
            f"<div class='chips'>{chips}</div>{notas_html}<div class='t-fuente'>{fuente}</div></div>")


def _contenido_calculo(salida: dict):
        v = salida["vector"]
        s = pd.Series(v, index=d.acordes)
        s = s[s > 0].sort_values(ascending=False).head(12)
        st.markdown("**1. Tu huella como números.** Cada acorde tiene un peso; la huella completa tiene "
                    f"{len(d.acordes)} acordes y mide 1 de largo (se normaliza).")
        st.dataframe(pd.DataFrame({"Acorde": [r.es(a).capitalize() for a in s.index], "Peso": s.values.round(3)}),
                     hide_index=True, use_container_width=False)
        st.markdown("**2. Por qué salió cada perfume.** Parecido = suma, acorde por acorde, de *tu peso × su peso* "
                    "(similitud coseno). Abajo, qué acordes aportan más a ese parecido. Lo que no te gusta resta "
                    f"la mitad de su parecido ({r.LAMBDA}) para ordenar, pero el % que ves es sin restar. "
                    f"A los acordes estimados se les restan {r.AJUSTE_ESTIMADO * 100:.0f} puntos. "
                    "Lo marcado como favorito cuenta doble.")
        filas = []
        vis = salida.get("_vis", {})
        for cat, ids in salida["ids"].items():
            t = salida["recomendaciones"][cat]
            n = vis.get(cat, N_INICIAL)
            for fid, (_, f) in zip(ids[:n], t.head(n).iterrows()):
                a = aportes(fid, v)
                total = float(a.sum()) or 1
                top = ", ".join(f"{r.es(k)} {val / total * 100:.0f}%" for k, val in a.head(3).items())
                filas.append({"Categoría": cat, "Perfume": bonito(f.nombre), "Parecido %": f["parecido_%"],
                              "Parecido con lo que no te gusta %": f["penalizacion_%"],
                              "Acordes que más aportan": top})
        st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)


def ver_calculo(salida: dict, clave: str = "x", anidado: bool = False):
    titulo = ":material/calculate: **Ver cálculo** · por qué salió cada perfume"
    with st.container(key=f"destacado_calc_{clave}"):
        if anidado:  # Streamlit no permite un desplegable dentro de otro
            if st.toggle(titulo, key=f"{clave}_calc"):
                with st.container(border=True):
                    _contenido_calculo(salida)
        else:
            with st.expander(titulo):
                _contenido_calculo(salida)


def _ver_mas(salida: dict, cat: str):
    vis = salida.setdefault("_vis", {})
    vis[cat] = vis.get(cat, N_INICIAL) + N_PASO


def mostrar_resultados(salida: dict, titulo_huella: str = "Tu huella olfativa", sujeto: str = "Tu huella",
                       evitas: list[str] = (), cierre: bool = True, clave: str = "x", anidado: bool = False):
    st.divider()
    perfil = salida["perfil"]
    c1, c2 = st.columns([1, 1], gap="large")
    with c1:
        st.subheader(titulo_huella)
        st.markdown(f"<div style='display:flex;justify-content:center'>{huella_svg(perfil, 280, '')}</div>",
                    unsafe_allow_html=True)
    with c2:
        st.subheader(" ")
        st.markdown(f"<div style='font-size:1.15rem;margin-bottom:.6rem'>{frase_huella(perfil, sujeto)}</div>"
                    f"{leyenda_html(perfil)}", unsafe_allow_html=True)
        if evitas:
            chips = "".join(f"<span class='chip' style='border:1px solid #5A6380;color:#9AA3B8'>✕ "
                            f"{html.escape(x)}</span>" for x in evitas)
            st.markdown(f"<div class='nota-fina' style='margin-top:.8rem'>Lo que prefieres evitar</div>"
                        f"<div class='chips'>{chips}</div>", unsafe_allow_html=True)
        st.markdown("<div class='nota-fina' style='margin-top:.6rem'>Cada color de tu huella es un acorde: los que más "
                    "pesan van por fuera y con crestas más completas. El % de cada perfume es <b>parecido de acordes</b>: no es la probabilidad de "
                    "que te guste ni prueba que huelan igual.</div>", unsafe_allow_html=True)
    st.subheader("Los que más se parecen")
    tabs = st.tabs(CATEGORIAS)
    for tab, cat in zip(tabs, CATEGORIAS):
        with tab:
            t = salida["recomendaciones"][cat]
            if t.empty:
                st.caption("Sin resultados con estos ajustes. Prueba incluir más géneros o quitar filtros.")
                continue
            vis = salida.setdefault("_vis", {})
            n = vis.get(cat, N_INICIAL)
            cols = st.columns(3)
            for i, (fid, (_, f)) in enumerate(zip(salida["ids"][cat][:n], t.head(n).iterrows())):
                cols[i % 3].markdown(tarjeta(f, fid, cat, salida["vector"], i == 0), unsafe_allow_html=True)
            restantes = len(t) - n
            if restantes > 0:
                _, centro, _ = st.columns([1, 1, 1])
                centro.button(f"Ver {min(N_PASO, restantes)} más de {cat}", key=f"{clave}_mas_{cat}",
                              icon=":material/expand_more:", use_container_width=True, on_click=_ver_mas,
                              args=(salida, cat))
            else:
                st.caption(f"Estos son los {len(t)} más parecidos de {cat}.")
    if cierre:
        a, b = T.CIERRE.split(". ", 1)
        st.markdown(f"<div class='cierre'>{html.escape(a)}. <span>{html.escape(b)}</span></div>",
                    unsafe_allow_html=True)
    ver_calculo(salida, clave, anidado)


def recomendar(**kw) -> dict | None:
    try:
        return r.recomendar(d, categorias=CATEGORIAS, **kw)
    except ValueError as e:
        st.warning(str(e))
        return None


# ---------- secciones ----------
def seccion_parecidos(clave: str):
    paso("1", "¿Qué perfume te gusta?", "Te muestro los que más se parecen en acordes, aunque no sean clones")
    texto = st.text_input("Busca por nombre o marca", key=f"{clave}_txt", placeholder="Ej.: sauvage, club de nuit…")
    res = buscar(texto) if texto else []
    if texto and not res:
        st.caption("No lo encontré. Prueba con menos palabras o solo la marca.")
    if not res:
        return
    fid = st.selectbox("Elige el perfume", res, format_func=ETIQ.get, key=f"{clave}_sel")
    paso("2", "¿Quieres que además lleven ciertas notas?", "Opcional · elige entre las notas de este perfume")
    sus_notas = sorted(NOTAS_ID.get(fid, set()) & set(NOTA_LBL), key=lambda n: _sin_acentos(NOTA_LBL[n]))
    con = st.pills("Notas", sus_notas, selection_mode="multi", format_func=NOTA_LBL.get, key=f"{clave}_con",
                   label_visibility="collapsed") or []
    aj = filtros(clave, anidado=True)
    if st.button("Buscar parecidos", type="primary", use_container_width=True, key=f"{clave}_btn"):
        if not aj["generos"]:
            st.warning("Elige al menos un género en Ajustes.")
        else:
            st.session_state[f"{clave}_out"] = recomendar(perfumes=[fid], notas=list(con), con_notas=list(con), **aj)
            st.session_state[f"{clave}_fid"] = fid
    if st.session_state.get(f"{clave}_out"):
        nombre = ETIQ.get(st.session_state.get(f"{clave}_fid"), "")
        mostrar_resultados(st.session_state[f"{clave}_out"], f"Huella de {nombre}", "Su huella", cierre=False,
                           clave=clave, anidado=True)


@st.cache_resource(show_spinner=False)
def famosos(para: str) -> dict[str, int]:
    out = {}
    for nombre, q in T.FAMOSOS.get(para, T.FAMOSOS["Hombre"]):
        res = buscar(q)
        if res:
            out[nombre] = res[0]
    return out


def seccion_facil(clave: str = "f"):
    st.markdown("<div class='aviso'>Sin términos raros: contesta como si platicaras. Nosotros traducimos tus "
                "respuestas al lenguaje de los perfumes.</div>", unsafe_allow_html=True)
    izq, der = st.columns([3, 2], gap="large")
    with izq:
        paso("1", "¿Para quién es el perfume?")
        para = st.segmented_control("Para quién", list(T.FACIL_PARA), default="Hombre", key=f"{clave}_para",
                                    label_visibility="collapsed") or "Hombre"
        paso("2", "¿Qué olores disfrutas en la vida diaria?", "Elige de 1 a 3, los que más te gusten")
        olores = st.pills("Olores", list(T.FACIL_OLORES), selection_mode="multi", key=f"{clave}_olores",
                          label_visibility="collapsed") or []
        if len(olores) > 3:
            st.caption("Puedes elegir más, pero con 1 a 3 sale una huella más clara.")
        paso("3", "¿Para cuándo lo usarías más?")
        ocasion = st.pills("Ocasión", list(T.FACIL_OCASION), key=f"{clave}_ocasion", label_visibility="collapsed")
        paso("4", "¿Cómo quieres que se sienta?")
        intensidad = st.pills("Intensidad", list(T.FACIL_INTENSIDAD), key=f"{clave}_int",
                              label_visibility="collapsed")
        paso("5", "¿Conoces algún perfume que te guste?", "Opcional · aunque sea porque alguien cercano lo usa")
        fam = famosos(para if para in T.FAMOSOS else "Hombre")
        conocidos = st.pills("Conocidos", list(fam), selection_mode="multi", key=f"{clave}_conocidos",
                             label_visibility="collapsed") or []
    acordes: list[str] = []
    for o in olores:
        acordes += T.FACIL_OLORES[o] * 2  # lo que dices que te gusta pesa más
    if ocasion:
        acordes += T.FACIL_OCASION[ocasion]
    if intensidad:
        acordes += T.FACIL_INTENSIDAD[intensidad]
    acordes = [a for a in acordes if a in ACORDE_LBL]
    perfumes = [fam[c] for c in conocidos]
    with der:
        panel_vivo(perfumes, acordes, [])
        if acordes:
            unicos = list(dict.fromkeys(acordes))
            chips = "".join(f"<span class='chip' style='border:1px solid {color(a)}66;color:{color(a)}'>"
                            f"{html.escape(ACORDE_LBL[a])}</span>" for a in unicos)
            st.markdown(f"<div class='nota-fina' style='margin-top:.8rem'>Así traducimos tus respuestas:</div>"
                        f"<div class='chips'>{chips}</div><div class='nota-fina'>Es una traducción aproximada "
                        "para empezar; la duración o qué tanto se nota un perfume no vienen en los datos.</div>",
                        unsafe_allow_html=True)
    if st.button("Ver mis perfumes", type="primary", use_container_width=True, key=f"{clave}_btn"):
        if not (acordes or perfumes):
            st.warning("Elige al menos un olor que te guste o un perfume que conozcas.")
        else:
            st.session_state[f"{clave}_out"] = recomendar(
                perfumes=perfumes, acordes=acordes, generos=T.FACIL_PARA.get(para, ("masculino", "unisex")),
                clima="calor" if ocasion == "Deporte o calor" else None, incluir_estimados=True,
                n_por_categoria=N_MAX)
    if st.session_state.get(f"{clave}_out"):
        mostrar_resultados(st.session_state[f"{clave}_out"], clave=clave)
        st.markdown("<div class='nota-fina' style='text-align:center'>¿Te animaste? Cambia arriba a "
                    "<b>Sé un poco de perfumes</b> para afinar con notas y aromas.</div>", unsafe_allow_html=True)


def seccion_clones():
    paso("✓", "¿Qué tanto se parecen los clones a su original?",
         "Tabla propia armada con tiendas, prensa, reseñas y el autor. Para comparar: dos perfumes al azar "
         "se parecen 33 % en acordes (mediana).")
    if CLONES is None:
        return
    c = CLONES.sort_values("parecido_acordes_pct", ascending=False)
    cols = st.columns(2)
    for i, (_, f) in enumerate(c.iterrows()):
        fuente = "señalado por el autor" if f.fuente_equivalencia == "autor" else f"señalado por: {f.fuente_equivalencia}"
        enlace = (f" · <a href='{html.escape(f.fuente_url)}' target='_blank'>ver fuente</a>"
                  if isinstance(f.fuente_url, str) and f.fuente_url else "")
        est = " · acordes del clon estimados" if f.acordes_del_clon == "estimado" else ""
        p = float(f.parecido_acordes_pct)
        acento = "#8FBF9A" if p >= 85 else "#E0A96D" if p >= 60 else "#D97A99"
        veredicto = "Muy parecido" if p >= 85 else "Parecido a medias" if p >= 60 else "Poco parecido en acordes"
        cols[i % 2].markdown(
            f"<div class='tarjeta' style='min-height:auto;--acento:{acento}'><div class='par'><div>"
            f"<div class='insignia' style='background:{acento}'>{veredicto}</div><div class='t-nombre'>"
            f"{html.escape(f.clon)}</div><div class='t-marca'>se compara con</div><div class='t-nombre'>"
            f"{html.escape(f.original)}</div></div>{anillo(p)}</div>"
            f"<div class='t-fuente'>{html.escape(fuente)}{est}{enlace}</div></div>", unsafe_allow_html=True)
    st.caption("El parecido de acordes no prueba que dos perfumes huelan igual.")


def seccion_como():
    st.markdown(f"""
**Cómo funciona**

1. **Cada perfume tiene una huella.** Es su lista de hasta 10 acordes en orden de importancia: el primero pesa
   1.0, el segundo 0.9 y así hasta 0.1.
2. **Tus gustos forman tu huella.** Si eliges perfumes, es el promedio de sus huellas. Si eliges un aroma, ese
   acorde suma. Si eliges una nota, se usa la huella promedio de los perfumes que la llevan. Lo que marcas como
   favorito cuenta doble.
3. **Se compara tu huella con la de cada perfume** (similitud coseno). 100 % = mismas proporciones de
   acordes; 0 % = nada en común. Dos perfumes al azar se parecen como 33 %.
4. **Lo que no te gusta resta** puntos para ordenar, pero el % que ves es el parecido sin restar.
5. **Se filtra y se agrupa.** Puedes buscar entre 70 mil perfumes, pero solo se recomiendan los que tienen 50
   votos o más (con menos, sus acordes son poco confiables) y son de las 94 marcas clasificadas: casi 10 mil,
   separados en diseñador, árabes, nicho y catálogo.

Los lanzamientos 2024–2026 todavía no tienen acordes votados: un modelo los estima a partir de sus notas
(86 % de parecido con los acordes reales en una prueba con 3,984 perfumes que no vio).

**Límites**

- El % es parecido de acordes, no la probabilidad de que te guste ni prueba de que dos perfumes huelan igual.
- Los datos de la comunidad llegan a septiembre de 2024.

**Datos y licencia**

- Fragrantica.com Fragrance Dataset (Olga G, Kaggle), licencia
  [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Esta página y sus datos derivados se
  comparten bajo la misma licencia: uso no comercial y con atribución.
- Lanzamientos 2024–2026: sitios oficiales de las marcas, tiendas y prensa.

Hecho por [{T.AUTOR}]({T.GITHUB}) · código y análisis completo en GitHub.
""")


# ---------- página ----------
st.markdown(f"<div class='marca'>{frasco('#B8C2D6')}<span>{html.escape(T.NOMBRE)}</span></div>",
            unsafe_allow_html=True)
st.title(T.TITULO)
st.markdown(f"<div class='lema'>{html.escape(T.LEMA)}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='sub'>{html.escape(T.SUBTITULO)}</div>", unsafe_allow_html=True)

st.markdown("<div style='height:.6rem'></div>", unsafe_allow_html=True)
with st.container(key="selector_modo"):
    modo = st.segmented_control("¿Cómo quieres empezar?", ["Sé un poco de perfumes", "No sé nada de perfumes"],
                                default="Sé un poco de perfumes", key="modo")

if modo == "No sé nada de perfumes":
    seccion_facil("f")
else:
    paso("✦", "Cuéntanos qué te gusta", "Perfumes, aromas o notas: lo que tengas a la mano")
    izq, med, der = st.columns([2, 2, 1.6], gap="large")
    with izq:
        b_perf = selector_perfumes("b_si", "Perfumes que te encantan")
        b_ac = selector_acordes("b_ac", "Aromas que te atraen", describir=False)
    with med:
        st.markdown("<div class='nota-fina'>Notas favoritas</div>", unsafe_allow_html=True)
        b_no = selector_notas("b_no", "")
        with st.expander("Lo que prefieres evitar (opcional)"):
            b_noac = st.multiselect("Aromas", list(ACORDE_LBL), format_func=ACORDE_LBL.get, key="b_noac")
            b_nono = st.multiselect("Notas", list(NOTA_LBL), format_func=NOTA_LBL.get, key="b_nono")
            b_noperf = selector_perfumes("b_noperf", "Perfumes")
        bp, ba, bn = selector_favoritos("b", b_perf, b_ac, b_no)
    with der:
        panel_vivo(bp, ba, bn)
    aj = filtros("b")
    if st.button("Descubrir mi huella", type="primary", use_container_width=True, key="b_btn"):
        if not (b_perf or b_ac or b_no):
            st.warning("Elige al menos un perfume, aroma o nota que te guste.")
        elif not aj["generos"]:
            st.warning("Elige al menos un género en Ajustes.")
        else:
            st.session_state["b_out"] = recomendar(perfumes=bp, acordes=ba, notas=bn, no_perfumes=b_noperf,
                                                   no_acordes=b_noac, no_notas=b_nono, **aj)
            st.session_state["b_evitas"] = [ACORDE_LBL[a] for a in b_noac] + [NOTA_LBL[n] for n in b_nono]
    if st.session_state.get("b_out"):
        mostrar_resultados(st.session_state["b_out"], evitas=st.session_state.get("b_evitas", []), clave="b")

st.divider()
if modo != "No sé nada de perfumes":
    with st.container(key="destacado_parecidos"), st.expander(
            ":material/search: **Parecidos a un perfume** · elige uno y te muestro los que más se le parecen"):
        seccion_parecidos("p")
with st.container(key="destacado_clones"), st.expander(
        ":material/compare_arrows: **Clones vs originales** · ¿qué tan fiel es cada clon a su original?"):
    seccion_clones()
with st.container(key="destacado_como"), st.expander(
        ":material/help: **Cómo funciona** · el algoritmo explicado sin rodeos"):
    seccion_como()

st.markdown(f"<div class='pie'>{html.escape(T.NOMBRE)} · Datos: Fragrantica.com Fragrance Dataset (Olga G, Kaggle), "
            "CC BY-NC-SA 4.0 · Uso no comercial</div>", unsafe_allow_html=True)
