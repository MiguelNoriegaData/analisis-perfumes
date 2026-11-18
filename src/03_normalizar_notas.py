"""Paso 3: unificar sinónimos de notas y traducirlas al español.

Criterio (documentado para el README):
- Se unifican: errores de escritura (vanille, vetyver, myrhh...), sinónimos (cassis = black currant,
  olibanum = frankincense, agarwood = oud) y variantes de origen (bulgarian rose, calabrian bergamot,
  madagascar vanilla -> rose, bergamot, vanilla). El origen describe calidad/procedencia, no un olor distinto
  que el análisis pueda distinguir con estos datos.
- Se mantienen separadas notas con olor claramente distinto aunque compartan palabra:
  bitter orange vs orange, white musk vs musk, green tea vs black tea, moss vs oakmoss, incense vs frankincense.
- Cobertura: las 400 notas más frecuentes (96 % de las apariciones). El resto conserva su nombre y queda sin
  traducción hasta que se revise.

Salida: data/processed/notas_normalizacion.csv y tabla notas_normalizacion en perfumes.duckdb,
más la vista v_notas (notas de Kaggle y propias ya canónicas y traducidas).
"""
from pathlib import Path

import duckdb
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
DB = RAIZ / "data/processed/perfumes.duckdb"

# variante -> nota canónica
SINONIMOS = {
    # typos / spelling
    "vanille": "vanilla", "vanila": "vanilla", "sandalowood": "sandalwood", "sandal": "sandalwood",
    "myrhh": "myrrh", "vetyver": "vetiver", "hiacynth": "hyacinth", "ylang ylang": "ylang-ylang",
    "lily of the valley": "lily-of-the-valley", "oak moss": "oakmoss", "cloves": "clove",
    "woodsy notes": "woody notes", "wood": "woody notes", "tonka": "tonka bean", "orris": "iris",
    "orris root": "iris", "iris flower": "iris", "tuscan iris": "iris", "cassis": "black currant",
    "olibanum": "frankincense", "citruses": "citrus notes", "agarwood (oud)": "oud", "agarwood": "oud",
    "cambodian oud": "oud", "indian oud": "oud", "laotian oud": "oud", "juniper berries": "juniper",
    "violet leaves": "violet leaf", "ambrette (musk mallow)": "ambrette", "elemi resin": "elemi",
    "resins": "resin", "fruits": "fruity notes", "flowers": "floral notes", "white flowers": "white floral notes",
    "wildflowers": "floral notes", "sea water": "marine notes", "sea notes": "marine notes",
    "watery notes": "water notes", "pine tree": "pine", "pine needles": "pine", "cedar needles": "cedar",
    "spices": "spicy notes", "big strawberry": "strawberry", "wild strawberry": "strawberry",
    "virginian cedar": "cedar", "virginia cedar": "cedar", "cedarwood": "cedar", "atlas cedar": "cedar",
    "texas cedar": "cedar", "white cedar extract": "cedar", "haitian vetiver": "vetiver",
    "palisander rosewood": "rosewood", "brazilian rosewood": "rosewood",
    "australian sandalwood": "sandalwood", "indonesian patchouli leaf": "patchouli", "patchouli leaf": "patchouli",
    "french labdanum": "labdanum", "siam benzoin": "benzoin", "guatemalan cardamom": "cardamom",
    "lime (linden) blossom": "linden blossom", "carambola (star fruit)": "star fruit",
    "cypriol oil or nagarmotha": "cypriol", "mastic or lentisque": "mastic",
    "natural musk": "musk", "cashmere musk": "musk", "white wood": "white woods",
    "dark chocolate": "chocolate", "cacao pod": "cacao", "vanilla absolute": "vanilla",
    "vanilla bean": "vanilla", "madagascar vanilla": "vanilla", "bourbon vanilla": "vanilla",
    "tahitian vanilla": "vanilla", "vanilla orchid": "vanilla", "vanilla flower": "vanilla",
    "red apple": "apple", "granny smith apple": "apple", "green apple": "apple",
    "amalfi lemon": "lemon", "sicilian lemon": "lemon", "italian lemon": "lemon", "lemon zest": "lemon",
    "calabrian bergamot": "bergamot", "sicilian bergamot": "bergamot",
    "tangerine": "mandarin orange", "italian mandarin": "mandarin orange", "sicilian mandarin": "mandarin orange",
    "yellow mandarin": "mandarin orange", "green mandarin": "mandarin orange",
    "sweet orange": "orange", "blood orange": "orange", "brazilian orange": "orange",
    "pink grapefruit": "grapefruit", "tunisian neroli": "neroli",
    "african orange flower": "orange blossom",
    "bulgarian rose": "rose", "turkish rose": "rose", "damask rose": "rose", "may rose": "rose",
    "rose de mai": "rose", "taif rose": "rose", "moroccan rose": "rose", "grasse rose": "rose",
    "white rose": "rose", "red rose": "rose", "wild rose": "rose", "rose petals": "rose", "rose oil": "rose",
    "tincture of rose": "rose", "rose water": "rose", "tea rose": "rose",
    "jasmine sambac": "jasmine", "egyptian jasmine": "jasmine", "indian jasmine": "jasmine",
    "water jasmine": "jasmine", "indian tuberose": "tuberose", "white lily": "lily",
    "pink peony": "peony", "black orchid": "orchid", "bourbon geranium": "geranium",
    "white amber": "amber", "black amber": "amber", "crystal amber": "amber",
    "white honey": "honey", "brown sugar": "sugar", "sugar cane": "sugar",
    "red fruits": "red berries", "wild berries": "red berries",
    "black currant leaf": "black currant", "tobacco leaf": "tobacco", "tobacco blossom": "tobacco",
    "dry wood": "woody notes", "precious woods": "woody notes", "pimento": "allspice",
    # variantes frecuentes en tiendas y marcas (capa propia)
    "mandarin": "mandarin orange", "passion fruit": "passionfruit", "citrus": "citrus notes",
    "blackcurrant": "black currant", "lavandin": "lavender", "virginia cedarwood": "cedar",
    "italian bergamot": "bergamot", "floral accord": "floral notes", "floral": "floral notes",
    "amber woods": "amberwood", "amber wood": "amberwood", "oud accord": "oud", "dry woods": "woody notes",
    "woods": "woody notes", "soft woods": "woody notes", "orange flower": "orange blossom",
    "aromatic herbs": "herbal notes", "dry amber": "amber", "ambery": "amber", "fruity": "fruity notes",
    "fruity accord": "fruity notes", "chinese black tea": "black tea", "ambrox": "ambroxan", "cocoa": "cacao",
    "lychee": "litchi", "musks": "musk", "white florals": "white floral notes", "sicilian orange": "orange",
    "cypriol oil": "cypriol", "juniper berry": "juniper",
    "cuir velours": "leather", "ambrostar": "ambroxan", "gin tonic": "gin",
    "muguet": "lily-of-the-valley", "guaiacwood": "guaiac wood", "fir balsam": "balsam fir", "oud wood": "oud",
    "oakwood": "oak", "ambery woods": "amberwood", "warm spices": "spicy notes", "mineral accord": "mineral notes",
}

# nota canónica -> español
ES = {
    "musk": "almizcle", "white musk": "almizcle blanco", "bergamot": "bergamota", "amber": "ámbar",
    "jasmine": "jazmín", "sandalwood": "sándalo", "patchouli": "pachulí", "vanilla": "vainilla", "rose": "rosa",
    "cedar": "cedro", "vetiver": "vetiver", "mandarin orange": "mandarina", "lemon": "limón",
    "tonka bean": "haba tonka", "lavender": "lavanda", "orange blossom": "azahar",
    "lily-of-the-valley": "lirio de los valles", "violet": "violeta", "grapefruit": "toronja",
    "cardamom": "cardamomo", "iris": "iris", "pink pepper": "pimienta rosa", "leather": "cuero",
    "geranium": "geranio", "ylang-ylang": "ylang-ylang", "oakmoss": "musgo de roble", "peach": "durazno",
    "orange": "naranja", "freesia": "fresia", "cinnamon": "canela", "oud": "oud", "black currant": "grosella negra",
    "woody notes": "notas amaderadas", "saffron": "azafrán", "neroli": "neroli", "benzoin": "benjuí",
    "nutmeg": "nuez moscada", "pear": "pera", "ginger": "jengibre", "labdanum": "ládano", "tuberose": "nardo",
    "raspberry": "frambuesa", "peony": "peonía", "incense": "incienso", "apple": "manzana",
    "citrus notes": "notas cítricas", "magnolia": "magnolia", "ambergris": "ámbar gris", "mint": "menta",
    "pepper": "pimienta", "green notes": "notas verdes", "heliotrope": "heliotropo", "gardenia": "gardenia",
    "coriander": "cilantro (semilla)", "black pepper": "pimienta negra", "pineapple": "piña", "plum": "ciruela",
    "guaiac wood": "madera de guayaco", "moss": "musgo", "lime": "lima", "sage": "salvia", "tobacco": "tabaco",
    "caramel": "caramelo", "lily": "lirio", "rosemary": "romero", "carnation": "clavel",
    "violet leaf": "hoja de violeta", "orchid": "orquídea", "basil": "albahaca", "floral notes": "notas florales",
    "honey": "miel", "aldehydes": "aldehídos", "frankincense": "olíbano", "galbanum": "gálbano",
    "clove": "clavo", "petitgrain": "petitgrain", "cashmere wood": "madera de cachemira", "coconut": "coco",
    "osmanthus": "osmanto", "clary sage": "salvia esclarea", "marine notes": "notas marinas",
    "litchi": "lichi", "cypress": "ciprés", "almond": "almendra", "artemisia": "artemisa", "praline": "praliné",
    "apricot": "chabacano", "ambroxan": "ambroxan", "cashmeran": "cashmeran", "mimosa": "mimosa",
    "lotus": "loto", "melon": "melón", "fruity notes": "notas frutales", "myrrh": "mirra", "cyclamen": "ciclamen",
    "coffee": "café", "bitter orange": "naranja amarga", "juniper": "enebro", "spicy notes": "notas especiadas",
    "honeysuckle": "madreselva", "red berries": "frutos rojos", "cypriol": "cypriol (nagarmotha)",
    "thyme": "tomillo", "tea": "té", "elemi": "elemí", "anise": "anís", "blackberry": "zarzamora",
    "narcissus": "narciso", "passionfruit": "maracuyá", "lilac": "lila", "amberwood": "madera ambarada",
    "ambrette": "ambreta", "water lily": "nenúfar", "suede": "gamuza", "hyacinth": "jacinto", "styrax": "estoraque",
    "strawberry": "fresa", "rum": "ron", "rosewood": "palo de rosa", "rhubarb": "ruibarbo",
    "water notes": "notas acuáticas", "fig": "higo", "green leaves": "hojas verdes", "civet": "civeta",
    "frangipani": "flor de mayo (frangipani)", "birch": "abedul", "cherry": "cereza", "mango": "mango",
    "green tea": "té verde", "star anise": "anís estrella", "yuzu": "yuzu", "powdery notes": "notas atalcadas",
    "cumin": "comino", "cacao": "cacao", "sugar": "azúcar", "watermelon": "sandía", "licorice": "regaliz",
    "opoponax": "opopónaco", "pomegranate": "granada", "caraway": "alcaravea", "sweet notes": "notas dulces",
    "tolu balsam": "bálsamo de tolú", "castoreum": "castóreo", "tiare flower": "flor de tiaré",
    "angelica": "angélica", "milk": "leche", "chamomile": "manzanilla", "tarragon": "estragón",
    "white woods": "maderas blancas", "ozonic notes": "notas ozónicas", "citron": "cidra", "coumarin": "cumarina",
    "peru balsam": "bálsamo del Perú", "herbal notes": "notas herbales", "oak": "roble",
    "red currant": "grosella roja", "chocolate": "chocolate", "resin": "resinas", "lemon verbena": "cedrón",
    "bamboo": "bambú", "pomelo": "pomelo", "papyrus": "papiro", "nectarine": "nectarina", "mate": "mate",
    "immortelle": "siempreviva", "salt": "sal", "fig leaf": "hoja de higuera", "clementine": "clementina",
    "hazelnut": "avellana", "pine": "pino", "balsam fir": "abeto balsámico", "bay leaf": "laurel",
    "eucalyptus": "eucalipto", "davana": "davana", "black tea": "té negro", "white pepper": "pimienta blanca",
    "cherry blossom": "flor de cerezo", "peach blossom": "flor de durazno", "teak wood": "teca", "grass": "pasto",
    "hibiscus": "jamaica (hibisco)", "amyris": "amyris", "wormwood": "ajenjo", "marigold": "cempasúchil",
    "hedione": "hedione", "fir": "abeto", "tagetes": "tagetes", "smoke": "humo", "whipped cream": "crema batida",
    "apple blossom": "flor de manzano", "blueberry": "mora azul", "sichuan pepper": "pimienta de Sichuan",
    "hay": "heno", "cognac": "coñac", "myrtle": "mirto", "gurjan balsam": "bálsamo de gurjun", "kiwi": "kiwi",
    "beeswax": "cera de abeja", "seaweed": "algas", "driftwood": "madera de deriva", "mahogany": "caoba",
    "ivy": "hiedra", "white peach": "durazno blanco", "dried fruits": "frutos secos",
    "bitter almond": "almendra amarga", "guava": "guayaba", "solar notes": "notas solares",
    "cotton candy": "algodón de azúcar", "hawthorn": "espino blanco", "sea salt": "sal marina",
    "cassia": "casia", "champaca": "champaca", "kumquat": "kumquat", "grapes": "uva",
    "carrot seeds": "semilla de zanahoria", "marshmallow": "malvavisco", "quince": "membrillo",
    "white tea": "té blanco", "verbena": "verbena", "animal notes": "notas animálicas", "cannabis": "cannabis",
    "peppermint": "hierbabuena", "iso e super": "iso e super", "cranberry": "arándano rojo",
    "coconut milk": "leche de coco", "linden blossom": "flor de tilo", "whiskey": "whisky",
    "sweet pea": "chícharo de olor", "cucumber": "pepino", "passion flower": "pasiflora",
    "sour cherry": "guinda", "champagne": "champaña", "mastic": "almáciga", "papaya": "papaya",
    "cotton flower": "flor de algodón", "green accord": "acorde verde", "almond blossom": "flor de almendro",
    "fern": "helecho", "fennel": "hinojo", "lemongrass": "té limón", "mineral notes": "notas minerales",
    "star fruit": "carambola", "rice": "arroz", "wisteria": "glicina", "tomato leaf": "hoja de jitomate",
    "white chocolate": "chocolate blanco", "toffee": "toffee", "tropical fruits": "frutas tropicales",
    "akigalawood": "akigalawood", "dates": "dátiles", "calone": "calone", "pistachio": "pistache",
    "balsamic notes": "notas balsámicas", "ginger flower": "flor de jengibre", "sorbet": "sorbete",
    "chestnut": "castaña", "metallic notes": "notas metálicas", "earthy notes": "notas terrosas",
    "lemon blossom": "flor de limón", "exotic fruits": "frutas exóticas", "absinthe": "absenta",
    "pear blossom": "flor de pera", "gin": "ginebra", "banana": "plátano", "sand": "arena",
    "carrot": "zanahoria", "oregano": "orégano", "broom": "retama", "olive tree": "olivo", "liquor": "licor",
    "palo santo": "palo santo", "clover": "trébol", "white floral notes": "notas de flores blancas",
    "allspice": "pimienta gorda", "oriental notes": "notas orientales",
}


def main() -> None:
    con = duckdb.connect(str(DB))
    freq = con.execute("""
        SELECT nota, count(*) AS ocurrencias FROM (
            SELECT nota FROM notas_kaggle UNION ALL SELECT nota FROM notas_propias)
        GROUP BY nota ORDER BY ocurrencias DESC""").df()
    freq["nota_canonica"] = freq.nota.map(lambda n: SINONIMOS.get(n, n))
    freq["nota_es"] = freq.nota_canonica.map(ES)
    freq["unificada"] = freq.nota != freq.nota_canonica
    freq = freq.rename(columns={"nota": "nota_original"})

    sin_trad = freq[freq.nota_es.isna()].head(400)
    con.execute("DROP TABLE IF EXISTS notas_normalizacion")
    con.register("tmp", freq)
    con.execute("CREATE TABLE notas_normalizacion AS SELECT * FROM tmp")
    con.execute("""
        CREATE OR REPLACE VIEW v_notas AS
        SELECT 'kaggle' AS fuente_datos, CAST(n.fragrantica_id AS VARCHAR) AS id, n.nivel,
               nn.nota_canonica AS nota, nn.nota_es
        FROM notas_kaggle n JOIN notas_normalizacion nn ON nn.nota_original = n.nota
        UNION ALL
        SELECT 'propia', p.id_propio, p.nivel, nn.nota_canonica, nn.nota_es
        FROM notas_propias p JOIN notas_normalizacion nn ON nn.nota_original = p.nota
    """)
    freq.to_csv(RAIZ / "data/processed/notas_normalizacion.csv", index=False, encoding="utf-8")

    total = freq.ocurrencias.sum()
    print("notas originales:", len(freq), "| canónicas:", freq.nota_canonica.nunique())
    print("apariciones con traducción:", round(freq[freq.nota_es.notna()].ocurrencias.sum() / total * 100, 1), "%")
    print("notas del top 400 sin traducción:", sin_trad.nota_original.tolist()[:40])
    con.close()


if __name__ == "__main__":
    main()
