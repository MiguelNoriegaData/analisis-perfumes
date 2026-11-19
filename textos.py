"""Textos y catálogos de la página: nombre, acordes explicados y familias de notas.

Todo lo que se ve en la página y se quiere cambiar rápido (nombre, títulos, descripciones) está aquí.
"""

NOMBRE = "Huella Olfativa"
TITULO = "Conoce tu huella olfativa"
SUBTITULO = ("Dinos qué perfumes y aromas te gustan y te mostramos cuáles se parecen a ti. "
             "Buscas entre 70 mil perfumes; te recomendamos entre casi 10 mil de diseñador, árabes, nicho y catálogo.")
GITHUB = "https://github.com/MiguelNoriegaData/analisis-perfumes"
AUTOR = "MiguelNoriegaData"

# Acordes explicados con palabras sencillas (clave = acorde en inglés, como viene en los datos)
ACORDES_DESC = {
    "fresh": "Limpio y ligero, como ropa recién lavada.",
    "citrus": "Limón, naranja, toronja: chispeante y alegre.",
    "aquatic": "Agua, brisa marina, sensación húmeda y fresca.",
    "marine": "Sal y mar abierto.",
    "ozonic": "Aire limpio, como después de la lluvia.",
    "aromatic": "Hierbas como lavanda, romero o salvia. El clásico 'olor a hombre arreglado'.",
    "lavender": "Lavanda: limpia, herbal y un poco floral.",
    "herbal": "Hierbas verdes y frescas.",
    "green": "Hojas, pasto recién cortado, tallos.",
    "fresh spicy": "Especias frescas: pimienta, jengibre, cardamomo.",
    "warm spicy": "Especias cálidas: canela, clavo, nuez moscada.",
    "soft spicy": "Especias suaves y redondas.",
    "woody": "Maderas como cedro o sándalo: seco, elegante.",
    "mossy": "Musgo, bosque húmedo.",
    "earthy": "Tierra mojada, raíces.",
    "patchouli": "Pachulí: terroso, oscuro y profundo.",
    "leather": "Cuero: elegante, un poco rudo.",
    "smoky": "Humo, madera quemada, incienso.",
    "oud": "Oud: madera densa y oscura, típica de los perfumes árabes.",
    "tobacco": "Tabaco: cálido, seco, a veces dulce.",
    "sweet": "Dulce en general.",
    "vanilla": "Vainilla: cálida, cremosa, envolvente.",
    "caramel": "Caramelo, azúcar quemada.",
    "honey": "Miel.",
    "coffee": "Café.",
    "cacao": "Cacao, chocolate amargo.",
    "almond": "Almendra, un poco a pan dulce.",
    "nutty": "Nueces y frutos secos.",
    "amber": "Ámbar: cálido, resinoso, envolvente. No es una piedra, es una mezcla.",
    "balsamic": "Resinas dulces, como bálsamo.",
    "musky": "Almizcle: piel limpia, suave. A algunas personas les huele a jabón.",
    "powdery": "Talco, polvo cosmético.",
    "animalic": "Notas animales, cálidas y sensuales.",
    "fruity": "Frutas en general.",
    "tropical": "Frutas tropicales: piña, mango, coco.",
    "floral": "Flores en general.",
    "white floral": "Flores blancas: jazmín, azahar, nardo.",
    "yellow floral": "Flores amarillas: ylang-ylang, osmanto.",
    "rose": "Rosa.",
    "iris": "Iris: atalcado, elegante.",
    "violet": "Violeta.",
    "lactonic": "Lácteo, cremoso.",
    "salty": "Salado.",
    "soapy": "Jabón.",
    "metallic": "Metálico, frío.",
    "aldehydic": "Aldehídos: brillo jabonoso, clásico de perfumes antiguos.",
    "cinnamon": "Canela.",
    "coconut": "Coco.",
    "rum": "Ron.",
    "whiskey": "Whisky.",
    "conifer": "Pino, abeto.",
}

# Acordes que se muestran como botones rápidos (los demás se buscan en la lista)
ACORDES_RAPIDOS = ["fresh", "citrus", "aquatic", "aromatic", "fresh spicy", "woody", "warm spicy", "sweet",
                   "vanilla", "amber", "leather", "oud", "smoky", "fruity", "floral", "musky", "powdery", "green"]

# Notas agrupadas por familia (clave = nota en inglés, como viene en los datos)
FAMILIAS_NOTAS = {
    "Cítricos": ["bergamot", "lemon", "mandarin orange", "grapefruit", "orange", "lime", "neroli", "petitgrain",
                 "citrus notes"],
    "Frutas": ["apple", "pineapple", "pear", "peach", "black currant", "raspberry", "plum", "red berries",
               "coconut", "litchi"],
    "Hierbas y verdes": ["lavender", "mint", "sage", "rosemary", "basil", "geranium", "violet leaf", "green notes",
                         "galbanum", "clary sage"],
    "Especias": ["pink pepper", "black pepper", "cardamom", "ginger", "cinnamon", "nutmeg", "saffron", "clove",
                 "coriander"],
    "Flores": ["rose", "jasmine", "iris", "orange blossom", "violet", "ylang-ylang", "tuberose", "lily-of-the-valley",
               "magnolia", "freesia"],
    "Maderas y musgos": ["cedar", "sandalwood", "vetiver", "patchouli", "oud", "guaiac wood", "cypress", "oakmoss",
                         "cashmere wood", "woody notes"],
    "Dulces": ["vanilla", "tonka bean", "caramel", "honey", "almond", "heliotrope", "benzoin"],
    "Ámbar, resinas y piel": ["amber", "ambergris", "ambroxan", "musk", "white musk", "labdanum", "incense",
                              "frankincense", "myrrh", "leather", "tobacco"],
    "Marinos y frescos": ["marine notes", "juniper", "aldehydes"],
}

# Color de cada acorde (tonos apagados para el fondo azul noche); se usa en la huella, chips y frascos
COLOR_ACORDE = {
    "fresh": "#9ED8DB", "citrus": "#E8D27A", "aquatic": "#6FB7E0", "marine": "#5A9BD5", "ozonic": "#A9C8E8",
    "aromatic": "#8FBF9A", "lavender": "#A99BD6", "herbal": "#7FAF7A", "green": "#7CC48A", "conifer": "#6FA58A",
    "fresh spicy": "#E0A96D", "warm spicy": "#C9774A", "soft spicy": "#D99A7A", "cinnamon": "#C46A3F",
    "woody": "#B08A6A", "mossy": "#7F9C78", "earthy": "#8C7058", "patchouli": "#8E6A58", "leather": "#9A6650",
    "smoky": "#9A9AA6", "oud": "#8A5C70", "tobacco": "#A8744E",
    "sweet": "#E39BB5", "vanilla": "#E8CFA0", "caramel": "#C98E5A", "honey": "#E0B45A", "almond": "#D8BFA0",
    "coffee": "#9C7A62", "cacao": "#8E6A5A", "amber": "#D9A25F", "balsamic": "#B5835A",
    "musky": "#C9C3D9", "powdery": "#D6C6E0", "animalic": "#B0907A", "lactonic": "#EDE3D0",
    "fruity": "#E58A8A", "tropical": "#F0B36A", "coconut": "#EDE6DA",
    "floral": "#E6A3C8", "white floral": "#EDE6F2", "yellow floral": "#E8D08A", "rose": "#D97A99",
    "iris": "#9E9AD1", "violet": "#8E7CC3", "tuberose": "#E9D6E6",
}
COLOR_OTRO = "#B8C2D6"

MENSAJES_PROGRESO = [
    (0, "Empieza eligiendo un perfume o un aroma que te guste."),
    (1, "¡Buen comienzo! Ya tenemos una pista de tus gustos."),
    (3, "Tu huella está tomando forma."),
    (5, "¡Listo! Tenemos una huella bastante clara."),
]

LEMA = "Adondequiera que vayas, deja tu huella."
CIERRE = "Ya conoces tu huella. Adondequiera que vayas, déjala."

# Abreviaturas que la gente usa al buscar (se reemplazan por el nombre completo)
ALIAS_BUSQUEDA = {
    "ysl": "yves saint laurent", "cdn": "club de nuit", "cdni": "club de nuit intense", "jpg": "jean paul gaultier",
    "ck": "calvin klein", "adg": "acqua di gio", "dg": "dolce&gabbana", "d&g": "dolce&gabbana",
    "mfk": "maison francis kurkdjian", "tf": "tom ford", "ch": "carolina herrera", "lv": "louis vuitton",
    "pr": "paco rabanne", "rabanne": "paco rabanne", "edp": "eau de parfum", "edt": "eau de toilette",
}

# ---------- Modo fácil ("No sé de perfumes") ----------
# Cada respuesta se traduce a acordes. Es una traducción propia y aproximada, se explica en la página.
FACIL_OLORES = {
    "🍋 Limón o naranja": ["citrus"],
    "🌊 El mar, la brisa": ["aquatic", "marine"],
    "👕 Ropa recién lavada": ["fresh", "ozonic"],
    "🌿 Hierbas: romero, menta, lavanda": ["aromatic", "herbal"],
    "🌲 Bosque, madera": ["woody", "mossy"],
    "🍎 Frutas": ["fruity"],
    "☕ Café, postres, vainilla": ["sweet", "vanilla", "coffee"],
    "🌶️ Canela, pimienta": ["warm spicy", "fresh spicy"],
    "🌸 Flores": ["floral"],
    "🧳 Cuero, tabaco": ["leather", "tobacco"],
}
FACIL_OCASION = {
    "Diario u oficina": ["fresh", "citrus", "aromatic"],
    "Salidas de noche": ["amber", "warm spicy", "sweet"],
    "Deporte o calor": ["aquatic", "citrus", "fresh"],
    "Ocasiones especiales": ["woody", "amber", "leather"],
}
FACIL_INTENSIDAD = {
    "Ligero y discreto": ["fresh", "citrus"],
    "Que se note": ["amber", "warm spicy"],
}
FACIL_PARA = {"Hombre": ("masculino", "unisex"), "Mujer": ("femenino", "unisex"), "Cualquiera": ("masculino", "femenino", "unisex")}
FAMOSOS = {
    "Hombre": [("Sauvage", "dior sauvage"), ("Bleu de Chanel", "chanel bleu de chanel"),
               ("Acqua di Giò", "armani acqua di gio"), ("Invictus", "paco rabanne invictus"),
               ("1 Million", "paco rabanne 1 million"), ("Le Male", "jpg le male"), ("Eros", "versace eros"),
               ("Polo", "ralph lauren polo"), ("212 Men", "carolina herrera 212 men"), ("CK One", "ck one"),
               ("Hawas", "rasasi hawas for him"), ("Club de Nuit Intense", "armaf club de nuit intense man")],
    "Mujer": [("Coco Mademoiselle", "chanel coco mademoiselle"), ("La Vie Est Belle", "lancome la vie est belle"),
              ("Good Girl", "carolina herrera good girl"), ("J'adore", "dior j adore"),
              ("Black Opium", "ysl black opium"), ("Light Blue", "dolce gabbana light blue"),
              ("Chanel N°5", "chanel no 5"), ("212 VIP Rosé", "carolina herrera 212 vip rose"),
              ("Yara", "lattafa yara"), ("CK One", "ck one")],
}
