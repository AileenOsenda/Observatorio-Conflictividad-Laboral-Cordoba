# -*- coding: utf-8 -*-
"""
08_perfil_editorial_redes.py
==============================
FASE 5 del pipeline — Perfil editorial, redes y actores.

# Descripción:
#   Cuatro análisis que caracterizan la cobertura por diario y por
#   actor: (1) perfil temático por diario (Dinámica Conflictual
#   normalizada por fila, barras apiladas al 100%); (2) red de
#   co-ocurrencia de palabras extraídas de Título con NetworkX; (3)
#   diversidad temática por diario mediante entropía de Shannon sobre
#   Dinámica Conflictual; (4) ranking de organizaciones más mencionadas.
#
# Uso:
#   Todas operan directamente sobre df_limpio; no dependen entre sí ni
#   de la Fase 4. `red_coocurrencia_titulos` requiere la función
#   tokens() del módulo 02_limpieza_corpus (pasada como parámetro para
#   evitar un import circular entre módulos independientes).
#
# Interpretación:
#   Un diario con entropía cercana al máximo teórico (log2(n_dinámicas))
#   cubre todos los tipos de conflicto con frecuencias similares;
#   entropía baja indica cobertura concentrada en pocas dinámicas.
#
# Dependencias:
#   pandas, numpy, matplotlib, networkx.
"""

import itertools
from collections import Counter

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx


def perfil_tematico_por_diario(df_limpio: pd.DataFrame, n_top: int = 10):
    """
    Distribución porcentual de Dinámica Conflictual dentro de cada
    Diario (normalizada por fila), visualizada como barras apiladas
    al 100%. Las dinámicas fuera del top_n se agrupan en "Otras".
    """
    print("== PERFIL TEMATICO POR DIARIO ====================")

    # normalize="index" divide cada fila por su propio total: permite
    # comparar diarios con distinta cantidad de notas en pie de igualdad
    perfil = pd.crosstab(df_limpio["Diario"], df_limpio["Dinámica Conflictual"], normalize="index") * 100
    print(perfil.round(1).to_string())

    top_dinamicas_global = df_limpio["Dinámica Conflictual"].value_counts().head(n_top).index
    perfil_plot = perfil[[c for c in perfil.columns if c in top_dinamicas_global]].copy()
    perfil_plot["Otras"] = 100 - perfil_plot.sum(axis=1)  # completa a 100% lo no incluido en el top

    perfil_plot.plot(kind="bar", stacked=True, figsize=(13, 6), colormap="tab20", edgecolor="white", linewidth=0.5)
    plt.title(f"Perfil temático por diario\n(top {n_top} dinámicas conflictuales, % del total de cada diario)",
              fontsize=13, fontweight="bold")
    plt.xlabel("Diario")
    plt.ylabel("% de notas")
    plt.xticks(rotation=30, ha="right")
    plt.legend(title="Dinámica Conflictual", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)
    plt.tight_layout()
    plt.show()

    # Dinámica que más pesa en cada diario (columna con el % máximo por fila)
    dominante_por_diario = perfil.idxmax(axis=1)
    print("\n-- Dinámica conflictual dominante por diario --")
    for diario_nombre, dinamica in dominante_por_diario.items():
        pct = perfil.loc[diario_nombre, dinamica]
        print(f"  {diario_nombre:<30} -> {dinamica}  ({pct:.1f}%)")

    return perfil


def red_coocurrencia_titulos(df_limpio: pd.DataFrame, tokens_func, umbral: int = 3):
    """
    Construye un grafo no dirigido: cada nodo es una palabra
    significativa extraída de Título, y cada arista conecta dos
    palabras que co-ocurrieron en el mismo título al menos `umbral` veces.

    Parámetros
    ----------
    tokens_func : callable
        La función tokens() de 02_limpieza_corpus.py (pasada como
        parámetro, no importada, para mantener el módulo independiente).
    """
    print("== RED DE CO-OCURRENCIA DE PALABRAS EN TITULOS ==")

    pares_raw = []
    for titulo in df_limpio["Título"].dropna():
        kws = sorted(tokens_func(str(titulo)))
        if len(kws) > 1:
            # todas las combinaciones de a 2 dentro del mismo título
            pares_raw.extend(itertools.combinations(kws, 2))

    conteo_pares = Counter(pares_raw)

    G = nx.Graph()
    for (p1, p2), peso in conteo_pares.items():
        if peso >= umbral:
            G.add_edge(p1, p2, weight=peso)

    print(f"Nodos (palabras únicas en red): {G.number_of_nodes()}")
    print(f"Aristas (pares co-ocurrentes)  : {G.number_of_edges()}")

    if G.number_of_nodes() == 0:
        print("Sin aristas con el umbral actual. Probar bajar `umbral`.")
        return G

    # Centralidad de grado: qué palabras co-ocurren con vocabulario más variado
    centralidad = nx.degree_centrality(G)
    top_centrales = sorted(centralidad.items(), key=lambda x: x[1], reverse=True)[:10]
    print("\n-- Top 10 palabras más centrales en la red --")
    for palabra, cent in top_centrales:
        print(f"  {palabra:<25} centralidad: {cent:.3f}")

    fig, ax = plt.subplots(figsize=(14, 10))
    pos = nx.spring_layout(G, seed=42, k=1.5)  # seed fija para reproducibilidad del layout

    grados = dict(G.degree())
    node_sizes = [grados[n] * 200 for n in G.nodes()]  # nodo más grande = más conectado
    pesos_aristas = [G[u][v]["weight"] for u, v in G.edges()]
    max_peso = max(pesos_aristas) if pesos_aristas else 1

    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color="steelblue", alpha=0.85, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=8, font_color="white", font_weight="bold", ax=ax)
    nx.draw_networkx_edges(G, pos, width=[p / max_peso * 4 for p in pesos_aristas],
                            alpha=0.4, edge_color="gray", ax=ax)

    ax.set_title(f"Red de co-ocurrencia de palabras en títulos\n(umbral: >={umbral} co-ocurrencias)",
                 fontsize=13, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    plt.show()

    return G


def diversidad_shannon_por_diario(df_limpio: pd.DataFrame) -> pd.Series:
    """
    Índice de diversidad temática por diario (entropía de Shannon sobre
    la distribución de Dinámica Conflictual dentro de cada medio).
    """
    print("== INDICE DE DIVERSIDAD TEMATICA (SHANNON) ======")

    def entropia_shannon(serie):
        proporciones = serie / serie.sum()
        proporciones = proporciones[proporciones > 0]  # log(0) es indefinido, se excluyen ceros
        return -(proporciones * np.log2(proporciones)).sum()

    entropia_por_diario = (
        df_limpio.groupby("Diario")["Dinámica Conflictual"]
        .value_counts()
        .unstack(fill_value=0)
        .apply(entropia_shannon, axis=1)
        .rename("entropia_shannon")
        .sort_values(ascending=False)
    )

    n_dinamicas = df_limpio["Dinámica Conflictual"].nunique()
    entropia_max = np.log2(n_dinamicas)  # máximo teórico: distribución perfectamente uniforme

    print(f"Entropía máxima posible (con {n_dinamicas} dinámicas conflictuales): {entropia_max:.2f} bits\n")
    print(entropia_por_diario.round(3).to_string())
    print("\n-- Interpretación --")
    print(f"  Más diverso  : {entropia_por_diario.idxmax()} ({entropia_por_diario.max():.2f} bits)")
    print(f"  Menos diverso: {entropia_por_diario.idxmin()} ({entropia_por_diario.min():.2f} bits)")

    fig, ax = plt.subplots(figsize=(9, 5))
    colores = ["#2ecc71" if v == entropia_por_diario.max()
               else "#e74c3c" if v == entropia_por_diario.min()
               else "steelblue"
               for v in entropia_por_diario]
    entropia_por_diario.plot(kind="barh", ax=ax, color=colores, edgecolor="white")
    ax.axvline(x=entropia_max, color="black", linestyle="--", linewidth=1.2,
               label=f"Máximo teórico ({entropia_max:.2f} bits)")
    ax.set_title("Diversidad temática por diario\n(entropía de Shannon sobre Dinámica Conflictual)",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Entropía (bits) - más alto = más diverso")
    ax.legend()
    ax.invert_yaxis()
    plt.tight_layout()
    plt.show()

    return entropia_por_diario


def organizaciones_mas_mencionadas(df_limpio: pd.DataFrame, col_org: str = "Organización detallada", n_top: int = 15) -> pd.DataFrame:
    """
    Ranking de las organizaciones más mencionadas, con conteo de en
    cuántos diarios distintos aparece cada una (proxy de alcance mediático).
    """
    print("== ORGANIZACIONES MAS MENCIONADAS ================")

    freq_org = df_limpio[col_org].value_counts().head(n_top)

    filas_org = []
    for org in freq_org.index:
        mask = df_limpio[col_org] == org
        diarios_que_lo_cubren = df_limpio[mask]["Diario"].unique().tolist()
        filas_org.append({
            "organizacion": org,
            "menciones": freq_org[org],
            "n_diarios": len(diarios_que_lo_cubren),
            "diarios": ", ".join(diarios_que_lo_cubren),
        })

    df_orgs = pd.DataFrame(filas_org)
    print(df_orgs.to_string(index=False))

    fig, ax = plt.subplots(figsize=(10, 7))
    colores_org = plt.cm.RdYlGn(np.linspace(0.2, 0.9, len(df_orgs)))
    bars = ax.barh(df_orgs["organizacion"], df_orgs["menciones"], color=colores_org[::-1], edgecolor="white")

    # Anotar cuántos diarios distintos cubren cada organización
    for bar, n_d in zip(bars, df_orgs["n_diarios"]):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                f"{n_d} diario{'s' if n_d != 1 else ''}", va="center", fontsize=8, color="dimgray")

    ax.set_title(f"Top {n_top} organizaciones más mencionadas\n(número a la derecha = diarios que las cubren)",
                 fontsize=13, fontweight="bold")
    ax.set_xlabel("Número de notas")
    ax.invert_yaxis()
    plt.tight_layout()
    plt.show()

    return df_orgs
