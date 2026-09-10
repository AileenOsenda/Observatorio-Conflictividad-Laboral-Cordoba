# -*- coding: utf-8 -*-
"""
09_motor_grafico.py
=====================
FASE 6 del pipeline — Motor gráfico unificado y parametrizable.

# Descripción:
#   Sistema de dos capas: la función genérica `graficar()` (construye
#   tablas Período x Categoría a partir de cualquier columna de la base
#   y las visualiza como barras apiladas verticales/horizontales,
#   líneas, o barras apiladas al 100%), y siete funciones especializadas
#   (analisis_red_coocurrencia, analisis_diversidad_shannon,
#   analisis_organizaciones, analisis_evolucion_organizaciones,
#   analisis_picos, analisis_comparacion_periodos,
#   analisis_directa_vs_indirecta) para los análisis que no se reducen
#   a una tabla dinámica simple. Se integran en `menu_graficos()`, un
#   menú interactivo de 19 opciones.
#
# Mejoras de esta versión:
#   1) `_mostrar_valores_unicos()`: antes de pedir un filtro por texto
#      libre, muestra los valores reales presentes en esa columna
#      (hasta 40; si hay más, informa el total y muestra los 40 más
#      frecuentes) para evitar errores de tipeo ("Público" vs "público").
#   2) La opción 19 (gráfico personalizado) admite un segundo filtro
#      opcional además del primero.
#   3) `menu_graficos()` captura ValueError, KeyError y excepciones
#      genéricas al generar un gráfico, mostrando un mensaje legible en
#      vez de interrumpir la sesión con un traceback completo.
#   4) `_pedir_columna_valida()` y `_pedir_opcion_valida()` validan las
#      respuestas del usuario en el menú antes de proceder.
#
# Uso:
#   `menu_graficos(df_limpio)` pregunta interactivamente por consola:
#   qué análisis generar (1-19), granularidad temporal, rango de años
#   y, según el análisis, parámetros adicionales.
#
# Interpretación:
#   Cada gráfico generado corresponde a una configuración reproducible
#   de filtro + columna + período - facilita documentar en un informe
#   exactamente qué subconjunto de datos originó cada visualización.
#
# Dependencias:
#   pandas, numpy, matplotlib, networkx, itertools, collections.Counter.
#   Requiere la función tokens() del módulo 02_limpieza_corpus (se
#   importa de forma perezosa dentro de analisis_red_coocurrencia para
#   evitar un import obligatorio si no se usa esa opción del menú).
"""

import itertools
from collections import Counter

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
import importlib

# Import cruzado hacia el módulo de limpieza: como los archivos usan
# prefijo numérico (recomendado para orden de lectura en GitHub), no son
# identificadores Python válidos para "import 02_limpieza_corpus", así
# que se resuelve dinámicamente con importlib. Requiere que ambos
# archivos estén en la misma carpeta (o en el sys.path).
_modulo_limpieza = importlib.import_module("02_limpieza_corpus")
tokens = _modulo_limpieza.tokens  # reutiliza la misma tokenización que la Fase 2


# ══════════════════════════════════════════════════════════════
# NUEVO en esta versión (respecto a la anterior):
#
# 1) _mostrar_valores_unicos(): antes de pedirte "valores separados
#    por coma" para un filtro, el programa te MUESTRA los valores
#    reales que existen en esa columna (hasta 40; si hay más, te
#    avisa cuántos hay en total y te muestra los 40 más frecuentes).
#    Así no adivinás cómo está escrito "Público" vs "público" vs
#    "PUBLICO", lo ves tal cual está en los datos.
#
# 2) La opción 19 ahora admite un SEGUNDO filtro opcional (además
#    del primero). Por ejemplo: graficar 'Dinámica Conflictual',
#    filtrando por 'Pertenencia Sectorial' = Público Y ADEMÁS por
#    'Diario' = Clarín, La Nación.
#    Internamente: el primer filtro se aplica al DataFrame ANTES
#    de llamar a graficar(); el segundo filtro se pasa como el
#    filtro propio de graficar() (que sigue aceptando uno solo).
#    El resultado es equivalente a aplicar ambos filtros a la vez.
# ══════════════════════════════════════════════════════════════

TIPOS_GRAFICO_VALIDOS = ['apiladas_vertical', 'apiladas_horizontal', 'lineas', 'perfil_100']


def _pedir_columna_valida(df, mensaje):
    """Pide una columna por input() y reintenta hasta que exista en df.columns.
    Case-insensitive: si el usuario tipea distinto mayúsculas/minúsculas,
    se corrige automáticamente al nombre real de la columna."""
    columnas_lower = {c.lower(): c for c in df.columns}
    while True:
        entrada = input(mensaje).strip()
        if entrada.lower() in columnas_lower:
            return columnas_lower[entrada.lower()]
        print(f"  ✗ '{entrada}' no es una columna válida.")
        print(f"  Columnas disponibles: {list(df.columns)}\n")


def _pedir_opcion_valida(mensaje, opciones_validas):
    """Pide un valor por input() y reintenta hasta que esté dentro de
    opciones_validas (case-insensitive). Devuelve el valor normalizado
    tal como aparece en opciones_validas."""
    opciones_lower = {o.lower(): o for o in opciones_validas}
    while True:
        entrada = input(mensaje).strip()
        if entrada.lower() in opciones_lower:
            return opciones_lower[entrada.lower()]
        print(f"  ✗ '{entrada}' no es válido. Opciones: {opciones_validas}\n")


def _mostrar_valores_unicos(df, columna, max_mostrar=40):
    """Imprime los valores únicos presentes en `columna`, para que el
    usuario sepa exactamente qué escribir en el filtro (respeta mayúsculas,
    tildes, etc. tal como están en los datos)."""
    valores = df[columna].dropna().astype(str).str.strip()
    conteo = valores.value_counts()
    total_unicos = len(conteo)

    print(f"\n  Valores disponibles en '{columna}' ({total_unicos} distintos):")
    if total_unicos <= max_mostrar:
        for v in sorted(conteo.index):
            print(f"    • {v}  ({conteo[v]})")
    else:
        print(f"  (hay {total_unicos} valores distintos; se muestran los {max_mostrar} más frecuentes)")
        for v in conteo.head(max_mostrar).index:
            print(f"    • {v}  ({conteo[v]})")
    print()


def _pedir_filtro(df, etiqueta="filtro"):
    """Pide columna, modo (incluir/excluir) y valores para un filtro,
    mostrando primero los valores disponibles de esa columna.
    Devuelve (col_filtro, modo_filtro, valores_filtro) o (None, 'excluir', None)
    si el usuario no ingresa valores."""
    col_filtro = _pedir_columna_valida(df, f"Columna del {etiqueta}: ")
    _mostrar_valores_unicos(df, col_filtro)
    modo_filtro = _pedir_opcion_valida("Modo (incluir/excluir): ", ['incluir', 'excluir'])
    valores_filtro = [
        v.strip() for v in input("Valores (separados por coma, copiá los nombres de arriba): ").split(',')
        if v.strip()
    ]
    if not valores_filtro:
        print(f"  ⚠ No ingresaste valores para el {etiqueta}; se ignora.")
        return None, 'excluir', None
    return col_filtro, modo_filtro, valores_filtro


def _aplicar_filtro(df, col_filtro, modo, valores):
    """modo: 'excluir' o 'incluir'. valores: lista de strings (case-insensitive)."""
    if col_filtro is None or not valores:
        return df
    serie = df[col_filtro].astype(str).str.strip().str.lower()
    valores_low = [v.strip().lower() for v in valores]
    if modo == 'incluir':
        mask = serie.isin(valores_low)
    else:
        mask = ~serie.isin(valores_low)
    return df[mask]


def graficar(
    df_limpio: pd.DataFrame,
    col_categoria: str,
    titulo: str,
    tipo_grafico: str = 'apiladas_vertical',   # 'apiladas_vertical' | 'apiladas_horizontal' | 'lineas' | 'perfil_100'
    col_filtro: str = None,
    modo_filtro: str = 'excluir',
    valores_filtro: list = None,
    granularidad: str = 'año',                 # 'año' | 'trimestre' | 'mes'
    año_inicio: int = 2022,
    año_fin: int = 2026,
    n_top: int = None,
    categorias_fijas: list = None,
    tipo_valores: str = 'absoluto',             # 'absoluto' o 'porcentaje'
):
    # ── Validaciones tempranas (fail fast, con mensaje claro) ──
    if col_categoria not in df_limpio.columns:
        raise ValueError(
            f"'{col_categoria}' no es una columna válida de df_limpio. "
            f"Columnas disponibles: {list(df_limpio.columns)}"
        )
    if tipo_grafico not in TIPOS_GRAFICO_VALIDOS:
        raise ValueError(
            f"tipo_grafico='{tipo_grafico}' no es válido. "
            f"Opciones válidas: {TIPOS_GRAFICO_VALIDOS}"
        )
    if col_filtro is not None and col_filtro not in df_limpio.columns:
        raise ValueError(
            f"col_filtro='{col_filtro}' no es una columna válida de df_limpio. "
            f"Columnas disponibles: {list(df_limpio.columns)}"
        )
    # ─────────────────────────────────────────────────────────

    df_work = df_limpio.copy()
    df_work = _aplicar_filtro(df_work, col_filtro, modo_filtro, valores_filtro)
    df_work = df_work[(df_work['Año'] >= año_inicio) & (df_work['Año'] <= año_fin)].copy()

    if df_work.empty:
        print(f"⚠ Sin registros para '{titulo}' en el rango {año_inicio}-{año_fin} con los filtros aplicados.")
        return None

    if granularidad == 'año':
        df_work['periodo'] = df_work['Año'].astype('Int64').astype(str)
    elif granularidad == 'trimestre':
        df_work['periodo'] = df_work['Fecha'].dt.to_period('Q').astype(str)
    else:
        df_work['periodo'] = df_work['Fecha'].dt.to_period('M').astype(str)

    if categorias_fijas:
        categorias = [c for c in categorias_fijas if c in df_work[col_categoria].unique()]
        df_work = df_work[df_work[col_categoria].isin(categorias)]
    elif n_top:
        categorias = df_work[col_categoria].value_counts().head(n_top).index
        df_work = df_work[df_work[col_categoria].isin(categorias)]

    tabla = df_work.pivot_table(
        index='periodo', columns=col_categoria, values='Título', aggfunc='count', fill_value=0
    ).sort_index()

    if tipo_valores == 'porcentaje' or tipo_grafico == 'perfil_100':
        tabla_plot = tabla.div(tabla.sum(axis=1), axis=0) * 100
        ylabel = 'Porcentaje (%)'
    else:
        tabla_plot = tabla
        ylabel = 'Cantidad (valores absolutos)'

    n_periodos = len(tabla_plot)
    ancho = max(9, min(18, n_periodos * 1.3))
    fig, ax = plt.subplots(figsize=(ancho, 7))

    if tipo_grafico in ('apiladas_vertical', 'perfil_100'):
        tabla_plot.plot(kind='bar', stacked=True, ax=ax, colormap='tab20')
        ax.set_xlabel(granularidad.capitalize())
        ax.set_ylabel(ylabel)
        rot = 0 if granularidad == 'año' else 45
        plt.xticks(rotation=rot, ha='right' if rot else 'center')
        ax.legend(title=col_categoria, bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8)

    elif tipo_grafico == 'apiladas_horizontal':
        tabla_plot.plot(kind='barh', stacked=True, ax=ax, colormap='tab20')
        ax.set_ylabel(granularidad.capitalize())
        ax.set_xlabel(ylabel)
        ax.legend(title=col_categoria, bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8)

    elif tipo_grafico == 'lineas':
        tabla_plot.plot(kind='line', ax=ax, marker='o', linewidth=2)
        ax.set_xlabel(granularidad.capitalize())
        ax.set_ylabel(ylabel)
        rot = 0 if granularidad == 'año' else 45
        plt.xticks(rotation=rot, ha='right' if rot else 'center')
        ax.legend(title=col_categoria, bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8)

    ax.set_title(titulo)
    plt.tight_layout()
    plt.show()

    return tabla_plot


# ══════════════════════════════════════════════════════════════
# FUNCIONES DE LOS ANÁLISIS "NO REDUCIBLES" A pivot+plot
# ══════════════════════════════════════════════════════════════

def analisis_red_coocurrencia(df_limpio, año_inicio=2022, año_fin=2026, umbral=3):
    df_periodo = df_limpio[(df_limpio['Año'] >= año_inicio) & (df_limpio['Año'] <= año_fin)]
    pares_raw = []
    for titulo in df_periodo["Título"].dropna():
        kws = sorted(tokens(str(titulo)))
        if len(kws) > 1:
            pares_raw.extend(itertools.combinations(kws, 2))
    conteo_pares = Counter(pares_raw)

    G = nx.Graph()
    for (p1, p2), peso in conteo_pares.items():
        if peso >= umbral:
            G.add_edge(p1, p2, weight=peso)

    print(f"Nodos: {G.number_of_nodes()} | Aristas: {G.number_of_edges()}")
    if G.number_of_nodes() == 0:
        print("⚠ Sin aristas con ese umbral. Probá bajarlo.")
        return None

    fig, ax = plt.subplots(figsize=(14, 10))
    pos = nx.spring_layout(G, seed=42, k=1.5)
    grados = dict(G.degree())
    node_sizes = [grados[n] * 200 for n in G.nodes()]
    pesos_aristas = [G[u][v]["weight"] for u, v in G.edges()]
    max_peso = max(pesos_aristas) if pesos_aristas else 1
    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color="steelblue", alpha=0.85, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=8, font_color="white", font_weight="bold", ax=ax)
    nx.draw_networkx_edges(G, pos, width=[p / max_peso * 4 for p in pesos_aristas], alpha=0.4, edge_color="gray", ax=ax)
    ax.set_title(f"Red de co-ocurrencia ({año_inicio}-{año_fin}, umbral≥{umbral})", fontsize=13, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    plt.show()
    return G


def analisis_diversidad_shannon(df_limpio, año_inicio=2022, año_fin=2026):
    df_periodo = df_limpio[(df_limpio['Año'] >= año_inicio) & (df_limpio['Año'] <= año_fin)]

    def entropia_shannon(serie):
        p = serie / serie.sum()
        p = p[p > 0]
        return -(p * np.log2(p)).sum()

    entropia_por_diario = (
        df_periodo.groupby("Diario")["Dinámica Conflictual"]
        .value_counts().unstack(fill_value=0)
        .apply(entropia_shannon, axis=1).rename("entropia_shannon").sort_values(ascending=False)
    )
    n_dinamicas = df_periodo["Dinámica Conflictual"].nunique()
    entropia_max = np.log2(n_dinamicas) if n_dinamicas > 0 else 0
    print(entropia_por_diario.round(3).to_string())

    fig, ax = plt.subplots(figsize=(9, 5))
    colores = ["#2ecc71" if v == entropia_por_diario.max() else
               "#e74c3c" if v == entropia_por_diario.min() else "steelblue"
               for v in entropia_por_diario]
    entropia_por_diario.plot(kind="barh", ax=ax, color=colores, edgecolor="white")
    ax.axvline(x=entropia_max, color="black", linestyle="--", label=f"Máximo teórico ({entropia_max:.2f})")
    ax.set_title(f"Diversidad temática por diario ({año_inicio}-{año_fin})", fontsize=13, fontweight="bold")
    ax.set_xlabel("Entropía (bits)")
    ax.legend()
    ax.invert_yaxis()
    plt.tight_layout()
    plt.show()
    return entropia_por_diario


def analisis_organizaciones(df_limpio, año_inicio=2022, año_fin=2026, col_org="Organización detallada", n_top=15):
    df_periodo = df_limpio[(df_limpio['Año'] >= año_inicio) & (df_limpio['Año'] <= año_fin)]
    freq_org = df_periodo[col_org].value_counts().head(n_top)

    filas = []
    for org in freq_org.index:
        diarios = df_periodo[df_periodo[col_org] == org]["Diario"].unique().tolist()
        filas.append({"organizacion": org, "menciones": freq_org[org], "n_diarios": len(diarios)})
    df_orgs = pd.DataFrame(filas)
    print(df_orgs.to_string(index=False))

    fig, ax = plt.subplots(figsize=(10, 7))
    colores = plt.cm.RdYlGn(np.linspace(0.2, 0.9, len(df_orgs)))
    ax.barh(df_orgs["organizacion"], df_orgs["menciones"], color=colores[::-1], edgecolor="white")
    ax.set_title(f"Top {n_top} organizaciones ({año_inicio}-{año_fin})", fontsize=13, fontweight="bold")
    ax.set_xlabel("Número de notas")
    ax.invert_yaxis()
    plt.tight_layout()
    plt.show()
    return df_orgs


def analisis_evolucion_organizaciones(df_limpio, año_inicio=2022, año_fin=2026, n_top=8):
    df_periodo = df_limpio[(df_limpio['Año'] >= año_inicio) & (df_limpio['Año'] <= año_fin)].copy()
    top_orgs = df_periodo["Organización detallada"].value_counts().head(n_top).index
    df_o = df_periodo[df_periodo["Organización detallada"].isin(top_orgs)]
    evolucion = (
        df_o.groupby([pd.Grouper(key="Fecha", freq="ME"), "Organización detallada"])
        .size().unstack(fill_value=0)
    )
    fig, ax = plt.subplots(figsize=(14, 6))
    evolucion.plot(ax=ax, linewidth=2, marker="o", markersize=4, colormap="tab10")
    ax.set_title(f"Evolución mensual de organizaciones ({año_inicio}-{año_fin})", fontsize=13, fontweight="bold")
    ax.legend(title="Organización", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.show()
    return evolucion


def analisis_picos(df_limpio, año_inicio=2022, año_fin=2026, umbral_sigma=1.5):
    df_periodo = df_limpio[(df_limpio['Año'] >= año_inicio) & (df_limpio['Año'] <= año_fin)].copy()
    serie = df_periodo.groupby(df_periodo["Fecha"].dt.date).size().rename("notas")
    serie.index = pd.to_datetime(serie.index)
    media, sigma = serie.mean(), serie.std()
    umbral = media + umbral_sigma * sigma
    picos = serie[serie >= umbral].sort_values(ascending=False)
    print(f"Media: {media:.1f} | Umbral: {umbral:.1f} | Picos detectados: {len(picos)}")
    print(picos.to_string())

    fig, ax = plt.subplots(figsize=(14, 5))
    serie.plot(ax=ax, color="steelblue", linewidth=1, alpha=0.7, label="Notas/día")
    ax.axhline(umbral, color="crimson", linestyle=":", label=f"Umbral ({umbral:.0f})")
    ax.scatter(picos.index, picos.values, color="crimson", zorder=5, s=50, label="Pico")
    ax.set_title(f"Picos de conflictividad ({año_inicio}-{año_fin})", fontsize=13, fontweight="bold")
    ax.legend()
    plt.tight_layout()
    plt.show()
    return picos


def analisis_comparacion_periodos(df_limpio, fecha_corte, etiqueta_a="Antes", etiqueta_b="Después"):
    df_c = df_limpio.copy()
    fecha_corte_dt = pd.to_datetime(fecha_corte)
    df_c["periodo"] = df_c["Fecha"].apply(lambda f: etiqueta_a if f < fecha_corte_dt else etiqueta_b)

    metricas = df_c.groupby("periodo").agg(
        total_notas=("Título", "count"),
        dias_cubiertos=("Fecha", "nunique"),
        diarios_activos=("Diario", "nunique"),
    ).round(2)
    metricas["notas_por_dia"] = (metricas["total_notas"] / metricas["dias_cubiertos"]).round(2)
    metricas = metricas.reindex([etiqueta_a, etiqueta_b])
    print(metricas.T.to_string())

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    totales = metricas["total_notas"]
    axes[0].bar(totales.index, totales.values, color=["#4a90d9", "#e74c3c"], edgecolor="white", width=0.5)
    axes[0].set_title("Total de notas")
    x_dia = metricas["notas_por_dia"]
    axes[1].bar(x_dia.index, x_dia.values, color=["#4a90d9", "#e74c3c"], edgecolor="white", width=0.5)
    axes[1].set_title("Notas por día (intensidad)")
    plt.suptitle(f"Antes vs. después del {fecha_corte}", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.show()
    return metricas


def analisis_directa_vs_indirecta(df_limpio, año_inicio=2022, año_fin=2026, granularidad="mes"):
    df_periodo = df_limpio[(df_limpio['Año'] >= año_inicio) & (df_limpio['Año'] <= año_fin)].copy()
    df_periodo["tipo_accion"] = df_periodo["Formato agregado"].apply(
        lambda f: "Directa" if "directa" in str(f).lower()
        else ("Indirecta" if "indirecta" in str(f).lower() else "Sin datos")
    )
    freq_col = "ME" if granularidad == "mes" else ("Q" if granularidad == "trimestre" else "YE")
    tipo_tiempo = (
        df_periodo.groupby([pd.Grouper(key="Fecha", freq=freq_col), "tipo_accion"])
        .size().unstack(fill_value=0)
    )
    fig, ax = plt.subplots(figsize=(13, 5))
    COLORES_TIPO = {"Directa": "#2ecc71", "Indirecta": "#e74c3c", "Sin datos": "#bdc3c7"}
    cols_disp = [c for c in ["Directa", "Indirecta"] if c in tipo_tiempo.columns]
    tipo_tiempo[cols_disp].plot(ax=ax, linewidth=2, marker="o", color=[COLORES_TIPO[c] for c in cols_disp])
    ax.set_title(f"Directa vs. indirecta por {granularidad} ({año_inicio}-{año_fin})", fontsize=13, fontweight="bold")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.show()
    return tipo_tiempo


# ══════════════════════════════════════════════════════════════
# MENÚ INTERACTIVO — un único punto de entrada a TODOS los análisis
# ══════════════════════════════════════════════════════════════

def menu_graficos(df_limpio: pd.DataFrame):

    print("═" * 62)
    print("  ANÁLISIS Y GRÁFICOS DISPONIBLES")
    print("═" * 62)
    print(" 1  = Conflictos laborales según formato agregado (apiladas)")
    print(" 2  = Acciones directas según tipo de formato de protesta (líneas)")
    print(" 3  = Acciones directas según pertenencia sectorial (líneas)")
    print(" 4  = Demandas — todos los sectores (líneas)")
    print(" 5  = Demandas — sector público (líneas)")
    print(" 6  = Demandas — sectores no públicos (líneas)")
    print(" 7  = Participación de trabajadorxs — total (barras horiz. apiladas)")
    print(" 8  = Participación — sector público (barras horiz. apiladas)")
    print(" 9  = Participación — sectores no públicos (barras horiz. apiladas)")
    print("10  = Top dinámicas conflictuales por período (barras horiz. apiladas)")
    print("11  = Perfil temático por diario (barras apiladas al 100%)")
    print("12  = Red de co-ocurrencia de palabras en títulos")
    print("13  = Diversidad temática por diario (entropía de Shannon)")
    print("14  = Organizaciones más mencionadas")
    print("15  = Evolución mensual de organizaciones")
    print("16  = Detección de picos de conflictividad")
    print("17  = Comparación entre períodos (antes/después de una fecha)")
    print("18  = Acciones directas vs. indirectas en el tiempo")
    print("19  = Gráfico personalizado (elegís vos la columna y el tipo)")
    opcion = input("\nElegí una opción (1-19): ").strip()

    # ── Inputs comunes de período ──────────────────────────────
    print("\n¿Qué granularidad temporal querés usar? (no aplica a todas las opciones)")
    print("  1 = Anual   2 = Trimestral   3 = Mensual")
    g = input("Ingresá 1, 2 o 3 (default 1): ").strip() or '1'
    granularidad = {'1': 'año', '2': 'trimestre', '3': 'mes'}.get(g, 'año')

    año_inicio = int(input("Año de inicio (ej. 2022): ").strip() or 2022)
    año_fin    = int(input("Año de fin (ej. 2026): ").strip() or 2026)

    tipo_valores = 'absoluto'
    if opcion in ['1', '10']:
        t = input("¿Valores absolutos o porcentaje? (a/p, default a): ").strip().lower()
        tipo_valores = 'porcentaje' if t == 'p' else 'absoluto'

    if opcion == '1':
        df_ie = _aplicar_filtro(df_limpio, 'Iniciativa Estado', 'excluir', ['ninguna'])
        return graficar(
            df_ie, col_categoria='Formato agregado',
            titulo=f'Conflictos laborales según formato por {granularidad} ({año_inicio}-{año_fin})',
            tipo_grafico='apiladas_vertical',
            col_filtro='Formato agregado', modo_filtro='excluir', valores_filtro=['vacía', 'vacio', ''],
            granularidad=granularidad, año_inicio=año_inicio, año_fin=año_fin, tipo_valores=tipo_valores,
        )

    elif opcion == '2':
        return graficar(
            df_limpio, col_categoria='Tipo Formato AC',
            titulo=f'Acciones directas según formato de protesta por {granularidad} ({año_inicio}-{año_fin})',
            tipo_grafico='lineas',
            col_filtro='Formato agregado', modo_filtro='incluir', valores_filtro=['directa no paro', 'directa paro'],
            granularidad=granularidad, año_inicio=año_inicio, año_fin=año_fin,
        )

    elif opcion == '3':
        return graficar(
            df_limpio, col_categoria='Pertenencia Sectorial',
            titulo=f'Acciones directas según pertenencia sectorial por {granularidad} ({año_inicio}-{año_fin})',
            tipo_grafico='lineas',
            col_filtro='Formato agregado', modo_filtro='incluir', valores_filtro=['directa no paro', 'directa paro'],
            granularidad=granularidad, año_inicio=año_inicio, año_fin=año_fin,
        )

    elif opcion == '4':
        return graficar(
            df_limpio, col_categoria='Demanda principal agrupada',
            titulo=f'Demandas — todos los sectores por {granularidad} ({año_inicio}-{año_fin})',
            tipo_grafico='lineas',
            col_filtro='Demanda principal agrupada', modo_filtro='excluir', valores_filtro=['otros'],
            granularidad=granularidad, año_inicio=año_inicio, año_fin=año_fin,
        )

    elif opcion == '5':
        df_pub = _aplicar_filtro(df_limpio, 'Pertenencia Sectorial', 'incluir', ['Público'])
        return graficar(
            df_pub, col_categoria='Demanda principal agrupada',
            titulo=f'Demandas — sector público por {granularidad} ({año_inicio}-{año_fin})',
            tipo_grafico='lineas',
            col_filtro='Demanda principal agrupada', modo_filtro='excluir', valores_filtro=['otros'],
            granularidad=granularidad, año_inicio=año_inicio, año_fin=año_fin,
        )

    elif opcion == '6':
        df_nopub = _aplicar_filtro(df_limpio, 'Pertenencia Sectorial', 'excluir', ['Público'])
        return graficar(
            df_nopub, col_categoria='Demanda principal agrupada',
            titulo=f'Demandas — sectores no públicos por {granularidad} ({año_inicio}-{año_fin})',
            tipo_grafico='lineas',
            col_filtro='Demanda principal agrupada', modo_filtro='excluir', valores_filtro=['otros'],
            granularidad=granularidad, año_inicio=año_inicio, año_fin=año_fin,
        )

    elif opcion == '7':
        return graficar(
            df_limpio, col_categoria='Participación',
            titulo=f'Participación de trabajadorxs por {granularidad} ({año_inicio}-{año_fin})',
            tipo_grafico='apiladas_horizontal',
            granularidad=granularidad, año_inicio=año_inicio, año_fin=año_fin,
        )

    elif opcion == '8':
        df_pub = _aplicar_filtro(df_limpio, 'Pertenencia Sectorial', 'incluir', ['Público'])
        return graficar(
            df_pub, col_categoria='Participación',
            titulo=f'Participación — sector público por {granularidad} ({año_inicio}-{año_fin})',
            tipo_grafico='apiladas_horizontal',
            granularidad=granularidad, año_inicio=año_inicio, año_fin=año_fin,
        )

    elif opcion == '9':
        df_nopub = _aplicar_filtro(df_limpio, 'Pertenencia Sectorial', 'excluir', ['Público'])
        return graficar(
            df_nopub, col_categoria='Participación',
            titulo=f'Participación — sectores no públicos por {granularidad} ({año_inicio}-{año_fin})',
            tipo_grafico='apiladas_horizontal',
            granularidad=granularidad, año_inicio=año_inicio, año_fin=año_fin,
        )

    elif opcion == '10':
        n_top_input = input("¿Cuántas dinámicas conflictuales mostrar? (default 10): ").strip()
        n_top = int(n_top_input) if n_top_input else 10
        return graficar(
            df_limpio, col_categoria='Dinámica Conflictual',
            titulo=f'Dinámicas conflictuales con mayor actividad por {granularidad} ({año_inicio}-{año_fin})',
            tipo_grafico='apiladas_horizontal',
            granularidad=granularidad, año_inicio=año_inicio, año_fin=año_fin,
            n_top=n_top, tipo_valores=tipo_valores,
        )

    elif opcion == '11':
        n_top_input = input("¿Cuántas dinámicas mostrar? (default 10, el resto se agrupa en 'Otras'): ").strip()
        n_top = int(n_top_input) if n_top_input else 10
        return graficar(
            df_limpio, col_categoria='Dinámica Conflictual',
            titulo=f'Perfil temático por diario ({año_inicio}-{año_fin})',
            tipo_grafico='perfil_100',
            granularidad='año', año_inicio=año_inicio, año_fin=año_fin, n_top=n_top,
        )
        # Nota: para perfil por Diario en vez de por período, usar directamente
        # la celda de la Sección 5 ("Perfil temático por diario").

    elif opcion == '12':
        umbral_input = input("Umbral de co-ocurrencia (default 3): ").strip()
        umbral = int(umbral_input) if umbral_input else 3
        return analisis_red_coocurrencia(df_limpio, año_inicio, año_fin, umbral)

    elif opcion == '13':
        return analisis_diversidad_shannon(df_limpio, año_inicio, año_fin)

    elif opcion == '14':
        col_org = input("Columna de organización ('Organización detallada' / 'Organización Agregada', default detallada): ").strip()
        col_org = col_org if col_org else "Organización detallada"
        n_top_input = input("Top N organizaciones (default 15): ").strip()
        n_top = int(n_top_input) if n_top_input else 15
        return analisis_organizaciones(df_limpio, año_inicio, año_fin, col_org, n_top)

    elif opcion == '15':
        n_top_input = input("Top N organizaciones (default 8): ").strip()
        n_top = int(n_top_input) if n_top_input else 8
        return analisis_evolucion_organizaciones(df_limpio, año_inicio, año_fin, n_top)

    elif opcion == '16':
        sigma_input = input("Umbral en desvíos estándar (default 1.5): ").strip()
        sigma = float(sigma_input) if sigma_input else 1.5
        return analisis_picos(df_limpio, año_inicio, año_fin, sigma)

    elif opcion == '17':
        fecha_corte = input("Fecha de corte (YYYY-MM-DD): ").strip()
        etiqueta_a = input("Etiqueta período anterior (default 'Antes'): ").strip() or "Antes"
        etiqueta_b = input("Etiqueta período posterior (default 'Después'): ").strip() or "Después"
        return analisis_comparacion_periodos(df_limpio, fecha_corte, etiqueta_a, etiqueta_b)

    elif opcion == '18':
        return analisis_directa_vs_indirecta(df_limpio, año_inicio, año_fin, granularidad)

    elif opcion == '19':
        print("\nColumnas disponibles:", list(df_limpio.columns))

        col_categoria = _pedir_columna_valida(df_limpio, "Columna a graficar (categoría): ")
        tipo_grafico = _pedir_opcion_valida(
            f"Tipo de gráfico {TIPOS_GRAFICO_VALIDOS}: ", TIPOS_GRAFICO_VALIDOS
        )

        # ── Primer filtro (opcional) ────────────────────────────
        df_para_graficar = df_limpio
        usar_filtro1 = _pedir_opcion_valida("¿Aplicar un filtro? (s/n): ", ['s', 'n'])
        if usar_filtro1 == 's':
            col_f1, modo_f1, valores_f1 = _pedir_filtro(df_limpio, etiqueta="primer filtro")
            if col_f1 is not None:
                df_para_graficar = _aplicar_filtro(df_limpio, col_f1, modo_f1, valores_f1)

        # ── Segundo filtro (opcional) ───────────────────────────
        col_filtro2, modo_filtro2, valores_filtro2 = None, 'excluir', None
        usar_filtro2 = _pedir_opcion_valida("¿Aplicar un segundo filtro? (s/n): ", ['s', 'n'])
        if usar_filtro2 == 's':
            col_filtro2, modo_filtro2, valores_filtro2 = _pedir_filtro(
                df_para_graficar, etiqueta="segundo filtro"
            )

        n_top_input = input("Top N categorías (Enter = todas): ").strip()
        try:
            n_top = int(n_top_input) if n_top_input else None
        except ValueError:
            print("  ⚠ Valor no numérico para Top N, se ignora (se muestran todas las categorías).")
            n_top = None

        try:
            return graficar(
                df_para_graficar, col_categoria=col_categoria,
                titulo=f'{col_categoria} por {granularidad} ({año_inicio}-{año_fin})',
                tipo_grafico=tipo_grafico,
                col_filtro=col_filtro2, modo_filtro=modo_filtro2, valores_filtro=valores_filtro2,
                granularidad=granularidad, año_inicio=año_inicio, año_fin=año_fin,
                n_top=n_top, tipo_valores=tipo_valores,
            )
        except ValueError as e:
            print(f"\n✗ Error al generar el gráfico: {e}")
            return None
        except KeyError as e:
            print(f"\n✗ No se encontró la columna o valor {e} en los datos. Revisá el nombre exacto.")
            return None
        except Exception as e:
            print(f"\n✗ Ocurrió un error inesperado ({type(e).__name__}): {e}")
            return None

    else:
        print("Opción inválida.")
        return None
