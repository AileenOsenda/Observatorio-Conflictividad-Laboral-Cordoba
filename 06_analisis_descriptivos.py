# -*- coding: utf-8 -*-
"""
06_analisis_descriptivos.py
=============================
FASE 3 del pipeline — Análisis descriptivos simples (exploratorios).

# Descripción:
#   Funciones de exploración básica sobre `df_limpio`: vista general,
#   frecuencia por Diario, frecuencia por Dinámica Conflictual (con
#   tabla cruzada), evolución temporal simple por fecha, gráficos de
#   barras, serie temporal en línea, heatmap Diario x Dinámica, nube
#   de palabras extraída de Título, y resumen ejecutivo del corpus.
#
# Uso:
#   No son obligatorias de correr (así lo indica el notebook original):
#   son exploratorias, pensadas para un primer acercamiento al corpus
#   antes de pasar al motor gráfico paramétrico (módulo 09). Todas
#   reciben `df_limpio` como parámetro; ninguna depende de las demás,
#   salvo `resumen_ejecutivo_corpus`, que reutiliza `freq_dinamica` y
#   `freq_diario` ya calculados (para no recalcular dos veces).
#
# Interpretación:
#   Sirven como línea de base antes de cualquier análisis comparativo:
#   una distribución muy desigual entre diarios indica que los análisis
#   posteriores deben normalizarse por proporción, no por valor absoluto.
#
# Dependencias:
#   pandas, matplotlib, seaborn, wordcloud, y la función `tokens()`
#   del módulo 02_limpieza_corpus (para la nube de palabras).
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud


def vista_general(df_limpio: pd.DataFrame):
    """Imprime info() y head() del corpus limpio (chequeo rápido de tipos y nulos)."""
    print("== ESTRUCTURA DEL DATASET ======================")
    print(df_limpio.info())
    print("\n-- Primeras filas --")
    print(df_limpio.head())


def frecuencia_por_diario(df_limpio: pd.DataFrame) -> pd.Series:
    """Cuenta notas por Diario y muestra también la proporción porcentual."""
    print("== NOTAS POR DIARIO =============================")
    freq_diario = df_limpio["Diario"].value_counts()
    print(freq_diario)

    print("\n-- Proporcion (%) --")
    print((freq_diario / freq_diario.sum() * 100).round(2))
    return freq_diario


def frecuencia_por_dinamica(df_limpio: pd.DataFrame, top_n: int = 10):
    """
    Cuenta notas por Dinámica Conflictual y arma una tabla cruzada
    Diario x Dinámica (agrupando todo lo que no está en el top_n como "Otras").
    """
    print("== NOTAS POR DINAMICA CONFLICTUAL ===============")
    freq_dinamica = df_limpio["Dinámica Conflictual"].value_counts()
    print(freq_dinamica.head(20))

    print(f"\n-- Diario x Dinamica Conflictual (top {top_n}) --")
    top_dinamicas = freq_dinamica.head(top_n).index
    tabla_cruzada = pd.crosstab(
        df_limpio["Diario"],
        df_limpio["Dinámica Conflictual"].where(
            df_limpio["Dinámica Conflictual"].isin(top_dinamicas), "Otras"
        ),
    )
    print(tabla_cruzada)
    return freq_dinamica, tabla_cruzada


def evolucion_temporal_simple(df_limpio: pd.DataFrame) -> pd.Series:
    """Serie de notas por fecha (día calendario) con estadísticas básicas."""
    print("== NOTAS POR FECHA ===============================")
    serie_temporal = df_limpio.groupby(df_limpio["Fecha"].dt.date).size().rename("n_notas")
    print(serie_temporal.describe().round(1))

    print(f"\n  Dia mas activo   : {serie_temporal.idxmax()} ({serie_temporal.max()} notas)")
    print(f"  Dia menos activo : {serie_temporal.idxmin()} ({serie_temporal.min()} notas)")
    return serie_temporal


def graficos_dinamica_diario(freq_dinamica: pd.Series, freq_diario: pd.Series):
    """Panel de dos barras: top 15 dinámicas conflictuales y notas por diario."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Panel izquierdo: dinámicas más frecuentes, orientación horizontal
    # (mejor legibilidad para etiquetas de texto largas)
    freq_dinamica.head(15).plot(kind="barh", ax=axes[0], color="steelblue", edgecolor="white")
    axes[0].set_title("Top 15 dinámicas conflictuales", fontsize=13, fontweight="bold")
    axes[0].set_xlabel("Cantidad de notas")
    axes[0].invert_yaxis()  # la más frecuente arriba

    # Panel derecho: comparación simple entre diarios
    freq_diario.plot(kind="bar", ax=axes[1], color="coral", edgecolor="white")
    axes[1].set_title("Notas por diario", fontsize=13, fontweight="bold")
    axes[1].set_ylabel("Cantidad de notas")
    axes[1].tick_params(axis="x", rotation=30)

    plt.tight_layout()
    plt.show()


def serie_temporal_linea(serie_temporal: pd.Series):
    """Grafica la serie diaria como línea con área rellena bajo la curva."""
    fig, ax = plt.subplots(figsize=(12, 4))
    serie_temporal.plot(ax=ax, marker="o", linewidth=1.5, color="darkblue", markersize=3)
    ax.fill_between(serie_temporal.index, serie_temporal.values, alpha=0.15, color="darkblue")
    ax.set_title("Evolución diaria de notas de conflictividad laboral", fontsize=13, fontweight="bold")
    ax.set_xlabel("Fecha")
    ax.set_ylabel("Cantidad de notas")
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.show()


def heatmap_diario_dinamica(tabla_cruzada: pd.DataFrame):
    """Mapa de calor Diario x Dinámica Conflictual (matriz de frecuencias)."""
    fig, ax = plt.subplots(figsize=(13, 5))
    sns.heatmap(tabla_cruzada, annot=True, fmt="d", cmap="YlOrRd", linewidths=0.5, ax=ax)
    ax.set_title("Mapa de calor: Diario x Dinámica Conflictual (top 10)", fontsize=13, fontweight="bold")
    ax.set_xlabel("Dinámica Conflictual")
    ax.set_ylabel("Diario")
    plt.xticks(rotation=35, ha="right")
    plt.tight_layout()
    plt.show()


def nube_palabras_titulo(df_limpio: pd.DataFrame, tokens_func):
    """
    Genera una nube de palabras a partir de los tokens (palabras
    significativas, sin stopwords) extraídos de la columna Título.

    Parámetros
    ----------
    tokens_func : callable
        La función `tokens()` definida en 02_limpieza_corpus.py, pasada
        como parámetro para no crear una dependencia de import circular
        entre módulos independientes.
    """
    todas_las_palabras = []
    for titulo in df_limpio["Título"].dropna():
        todas_las_palabras.extend(tokens_func(str(titulo)))

    texto_nube = " ".join(todas_las_palabras)

    nube = WordCloud(
        width=900, height=450, background_color="white",
        colormap="Blues", max_words=80, collocations=False,  # sin bigramas repetidos
    ).generate(texto_nube)

    plt.figure(figsize=(12, 6))
    plt.imshow(nube, interpolation="bilinear")
    plt.axis("off")
    plt.title("Nube de palabras más frecuentes en los títulos", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.show()


def resumen_ejecutivo_corpus(
    df_limpio: pd.DataFrame, freq_dinamica: pd.Series, freq_diario: pd.Series
) -> pd.DataFrame:
    """Tabla compacta con las métricas centrales del corpus limpio."""
    resumen = pd.DataFrame({
        "metrica": [
            "Total de notas", "Diarios presentes", "Dinámicas conflictuales distintas",
            "Departamentos cubiertos", "Rango de fechas", "Dinámica dominante", "Diario más activo",
        ],
        "valor": [
            len(df_limpio),
            df_limpio["Diario"].nunique(),
            df_limpio["Dinámica Conflictual"].nunique(),
            df_limpio["Departamento"].nunique(),
            f"{df_limpio['Fecha'].min().date()} - {df_limpio['Fecha'].max().date()}",
            freq_dinamica.idxmax(),
            freq_diario.idxmax(),
        ],
    })

    print("== RESUMEN EJECUTIVO =============================")
    print(resumen.to_string(index=False))
    return resumen
