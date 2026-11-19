"""Reconstruye todo desde cero, en orden: base, notas, modelo, acordes estimados, métricas, análisis, exportes y datos de la página.

Requisito: data/raw/fra_perfumes.csv y data/raw/fra_cleaned.csv (dataset de Kaggle) y los CSV de data/processed.
Uso: python src/correr_todo.py
"""
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent
for paso in ["02_construir_duckdb.py", "03_normalizar_notas.py", "06_modelo_notas_acordes.py",
             "07_estimar_acordes_propios.py", "08_metricas.py", "04_favoritos_vs_menos.py",
             "05_recomendaciones_caso_personal.py", "09_exportar_powerbi.py",
             "10_tendencias_powerbi.py", "11_clones_y_caso_powerbi.py",
             "12_exportar_app.py"]:
    print(f"\n=== {paso} ===", flush=True)
    subprocess.run([sys.executable, str(SRC / paso)], check=True)
