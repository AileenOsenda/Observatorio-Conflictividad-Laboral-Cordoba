# -*- coding: utf-8 -*-
"""
07_analisis_avanzados.py
==========================
FASE 4 del pipeline — Análisis temporales avanzados.

# Descripción:
#   Cinco análisis: (1) evolución de notas por día/semana/mes con media
#   móvil de 7 días y composición mensual por dinámica conflictual
#   (área apilada, top 8); (2) comparación de métricas entre dos
#   períodos definidos por una fecha de corte; (3) detección de picos
#   de conflictividad (notas > media + N desvíos estándar); (4)
#   evolución mensual de las organizaciones más mencionadas, con
#   heatmap organización x mes; (5) clasificación y evolución de
#   acciones directas vs. indirectas según Formato agregado.
#
# Uso:
#   `notas_vs_tiempo()` debe correrse primero: genera `df_temp`
#   (df_limpio ordenado por Fecha), `serie_diaria` y `media_movil_7`,
#   que reutilizan `deteccion_picos()`. Las demás funciones son
#   independientes entre sí.
#
# Interpretación:
#   Un pico de conflictividad concentrado en una sola dinámica y un
#   solo diario sugiere un evento sectorial cubierto en profundidad por
#   ese medio; un pico distribuido entre múltiples dinámicas y diarios
#   sugiere un evento de impacto amplio (paro general, medida de
#   política económica).
#
# Dependencias:
#   pandas, matplotlib, seaborn.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


def notas_vs_tiempo(df_limpio: pd.DataFrame):
    """
    Evolución de notas por día/semana/mes, más composición mensual por
    dinámica conflictual (top 8, área apilada).

    Retorna (df_temp, serie_diaria, media_movil_7) para reutilizar en
    otras funciones de este módulo (ej. deteccion_picos).
    """
    # df_temp: copia ordenada cronológicamente, base para el resto de la fase
    df_temp = df_limpio.sort_values("Fecha").copy()

    serie_diaria = df_temp.groupby(df_temp["Fecha"].dt.date).size().rename("notas")
    serie_diaria.index = pd.to_datetime(serie_diaria.index)
    serie_semanal = df_temp.resample("W", on="Fecha").size().rename("notas")
    serie_mensual = df_temp.resample("ME", on="Fecha").size().rename("notas")

    print(f"Período cubierto: {serie_diaria.index.min().date()} - {serie_diaria.index.max().date()}")
    print(f"Mes con mayor cobertura: {serie_mensual.idxmax().strftime('%Y-%m')} ({serie_mensual.max()} notas)")

    fig, axes = plt.subplots(3, 1, figsize=(14, 12))

    # Panel A: serie diaria + media móvil de 7 días (suaviza el ciclo semanal)
    media_movil_7 = serie_diaria.rolling(7, center=True).mean()
    serie_diaria.plot(ax=axes[0], color="steelblue", linewidth=1, alpha=0.8)
    media_movil_7.plot(ax=axes[0], color="darkblue", linewidth=2, label="Media móvil 7 días")
    axes[0].set_title("Notas por día", fontsize=12, fontweight="bold")
    axes[0].legend()
    axes[0].grid(axis="y", linestyle="--", alpha=0.4)

    # Panel B: agregado semanal
    serie_semanal.plot(ax=axes[1], kind="bar", color="coral", edgecolor="white", width=0.85)
    axes[1].set_title("Notas por semana", fontsize=12, fontweight="bold")
    step = max(1, len(serie_semanal) // 10)  # no saturar el eje X con demasiadas etiquetas
    axes[1].set_xticks(axes[1].get_xticks()[::step])
    axes[1].tick_params(axis="x", rotation=45)

    # Panel C: agregado mensual (visión macro)
    serie_mensual.plot(ax=axes[2], kind="bar", color="mediumseagreen", edgecolor="white")
    axes[2].set_title("Notas por mes", fontsize=12, fontweight="bold")
    axes[2].set_xticklabels([idx.strftime("%b %Y") for idx in serie_mensual.index], rotation=45, ha="right")

    plt.tight_layout()
    plt.show()

    # Composición mensual por dinámica conflictual (top 8), área apilada
    top8 = df_temp["Dinámica Conflictual"].value_counts().head(8).index
    df_top8 = df_temp[df_temp["Dinámica Conflictual"].isin(top8)]
    pivot_din = (
        df_top8.groupby([pd.Grouper(key="Fecha", freq="ME"), "Dinámica Conflictual"])
        .size().unstack(fill_value=0)
    )

    fig, ax = plt.subplots(figsize=(14, 5))
    pivot_din.plot(kind="area", stacked=True, ax=ax, colormap="tab10", alpha=0.75, linewidth=0)
    ax.set_title("Composición temática mensual (top 8 dinámicas, área apilada)", fontsize=13, fontweight="bold")
    ax.set_xticklabels([t.strftime("%b %Y") for t in pivot_din.index], rotation=45, ha="right")
    ax.legend(title="Dinámica Conflictual", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)
    plt.tight_layout()
    plt.show()

    return df_temp, serie_diaria, media_movil_7


def comparacion_periodos(df_temp: pd.DataFrame, fecha_corte: str, etiqueta_a="Antes", etiqueta_b="Después"):
    """
    Compara métricas de cobertura entre dos períodos separados por
    `fecha_corte` (ej. cambio de gestión, paro general, reforma laboral).
    """
    fecha_corte_dt = pd.to_datetime(fecha_corte)
    # Clasificación binaria de cada nota según el lado de la fecha de corte
    df_temp = df_temp.copy()
    df_temp["periodo"] = df_temp["Fecha"].apply(lambda f: etiqueta_a if f < fecha_corte_dt else etiqueta_b)

    metricas_periodo = df_temp.groupby("periodo").agg(
        total_notas=("Título", "count"),
        dias_cubiertos=("Fecha", "nunique"),
        diarios_activos=("Diario", "nunique"),
        dinamicas_unicas=("Dinámica Conflictual", "nunique"),
    ).round(2)
    metricas_periodo["notas_por_dia"] = (
        metricas_periodo["total_notas"] / metricas_periodo["dias_cubiertos"]
    ).round(2)
    metricas_periodo = metricas_periodo.reindex([etiqueta_a, etiqueta_b])
    print(metricas_periodo.T.to_string())

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    totales = metricas_periodo["total_notas"]
    axes[0].bar(totales.index, totales.values, color=["#4a90d9", "#e74c3c"], edgecolor="white", width=0.5)
    for i, (idx, val) in enumerate(totales.items()):
        axes[0].text(i, val + 0.5, str(int(val)), ha="center", fontweight="bold")
    axes[0].set_title("Total de notas")

    x_dia = metricas_periodo["notas_por_dia"]
    axes[1].bar(x_dia.index, x_dia.values, color=["#4a90d9", "#e74c3c"], edgecolor="white", width=0.5)
    for i, (idx, val) in enumerate(x_dia.items()):
        axes[1].text(i, val + 0.02, f"{val:.1f}", ha="center", fontweight="bold")
    axes[1].set_title("Notas por día (intensidad)")

    plt.suptitle(f"Antes vs. después del {fecha_corte}", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.show()

    return metricas_periodo


def deteccion_picos(df_temp: pd.DataFrame, serie_diaria: pd.Series, media_movil_7: pd.Series, umbral_sigma: float = 1.5):
    """
    Detecta días con cobertura anormalmente alta: notas > media + umbral_sigma * desvío estándar.
    """
    media_diaria = serie_diaria.mean()
    sigma_diaria = serie_diaria.std()
    umbral_pico = media_diaria + umbral_sigma * sigma_diaria

    print(f"Media diaria: {media_diaria:.1f} | Umbral de pico: {umbral_pico:.1f} notas/día")

    dias_pico = serie_diaria[serie_diaria >= umbral_pico].sort_values(ascending=False)
    print(f"\nPicos detectados: {len(dias_pico)} días\n{dias_pico.to_string()}")

    # Detalle de los 5 picos más grandes: qué dinámicas y qué notas los explican
    print("\n-- Notas en cada pico (top 5) --")
    for fecha_pico, n in dias_pico.head(5).items():
        notas_pico = df_temp[df_temp["Fecha"].dt.date == fecha_pico.date()][
            ["Diario", "Dinámica Conflictual", "Título"]
        ]
        print(f"\n{fecha_pico.date()} -> {int(n)} notas")
        print(f"  Dinámicas: {notas_pico['Dinámica Conflictual'].value_counts().to_dict()}")
        for _, row in notas_pico.head(3).iterrows():
            print(f"    [{row['Diario']}] {str(row['Título'])[:75]}")

    fig, ax = plt.subplots(figsize=(14, 5))
    serie_diaria.plot(ax=ax, color="steelblue", linewidth=1.2, alpha=0.7, label="Notas/día")
    media_movil_7.plot(ax=ax, color="navy", linewidth=2, linestyle="--", label="Media móvil 7d")
    ax.axhline(umbral_pico, color="crimson", linewidth=1.5, linestyle=":", label=f"Umbral pico ({umbral_pico:.0f})")
    ax.scatter(dias_pico.index, dias_pico.values, color="crimson", zorder=5, s=60, label="Día pico")
    for fecha_pico, n in dias_pico.head(8).items():
        ax.annotate(fecha_pico.strftime("%d/%m"), xy=(fecha_pico, n), xytext=(0, 10),
                    textcoords="offset points", fontsize=7, color="crimson", ha="center")
    ax.set_title("Serie temporal con detección de picos", fontsize=13, fontweight="bold")
    ax.legend()
    plt.tight_layout()
    plt.show()

    return dias_pico


def evolucion_organizaciones(df_limpio: pd.DataFrame, df_temp: pd.DataFrame, n_top: int = 8):
    """Evolución mensual de menciones de las n_top organizaciones más frecuentes."""
    top_orgs = df_limpio["Organización detallada"].value_counts().head(n_top).index
    df_orgs_tiempo = df_temp[df_temp["Organización detallada"].isin(top_orgs)]

    evolucion_orgs = (
        df_orgs_tiempo.groupby([pd.Grouper(key="Fecha", freq="ME"), "Organización detallada"])
        .size().unstack(fill_value=0)
    )

    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    evolucion_orgs.plot(ax=axes[0], linewidth=2, marker="o", markersize=4, colormap="tab10")
    axes[0].set_title("Menciones mensuales por organización", fontsize=13, fontweight="bold")
    axes[0].set_xticklabels([t.strftime("%b %Y") for t in evolucion_orgs.index], rotation=45, ha="right")
    axes[0].legend(title="Organización", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=8)

    sns.heatmap(
        evolucion_orgs.T, ax=axes[1], cmap="YlOrRd", annot=True, fmt="d", linewidths=0.5,
        xticklabels=[t.strftime("%b %Y") for t in evolucion_orgs.index],
    )
    axes[1].set_title("Mapa de calor: organización x mes", fontsize=13, fontweight="bold")
    axes[1].tick_params(axis="x", rotation=45)

    plt.tight_layout()
    plt.show()

    print("\n-- Pico de visibilidad por organización --")
    for org in top_orgs:
        if org in evolucion_orgs.columns and evolucion_orgs[org].max() > 0:
            mes_pico = evolucion_orgs[org].idxmax()
            print(f"  {org:<35} pico: {mes_pico.strftime('%b %Y')} ({int(evolucion_orgs[org].max())} menciones)")

    return evolucion_orgs


def directa_vs_indirecta(df_temp: pd.DataFrame):
    """Clasifica cada nota como Directa/Indirecta/Sin datos según Formato agregado y grafica su evolución."""
    print("== ACCIONES DIRECTAS VS. INDIRECTAS EN EL TIEMPO ==")

    df_temp = df_temp.copy()
    df_temp["tipo_accion"] = df_temp["Formato agregado"].apply(
        lambda f: "Directa" if "directa" in str(f).lower()
        else ("Indirecta" if "indirecta" in str(f).lower() else "Sin datos")
    )

    distribucion_total = df_temp["tipo_accion"].value_counts()
    print(distribucion_total)
    print(f"\n  % directa   : {distribucion_total.get('Directa', 0) / len(df_temp) * 100:.1f}%")
    print(f"  % indirecta : {distribucion_total.get('Indirecta', 0) / len(df_temp) * 100:.1f}%")

    tipo_tiempo = (
        df_temp.groupby([pd.Grouper(key="Fecha", freq="ME"), "tipo_accion"])
        .size().unstack(fill_value=0)
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    colores_tipo = {"Directa": "#2ecc71", "Indirecta": "#e74c3c", "Sin datos": "#bdc3c7"}
    axes[0].pie(
        distribucion_total.values, labels=distribucion_total.index,
        colors=[colores_tipo.get(t, "gray") for t in distribucion_total.index],
        autopct="%1.1f%%", startangle=90, wedgeprops=dict(edgecolor="white", linewidth=1.5),
    )
    axes[0].set_title("Distribución general", fontsize=12, fontweight="bold")

    cols_disponibles = [c for c in ["Directa", "Indirecta"] if c in tipo_tiempo.columns]
    tipo_tiempo[cols_disponibles].plot(
        ax=axes[1], linewidth=2, marker="o", color=[colores_tipo[c] for c in cols_disponibles]
    )
    axes[1].set_title("Evolución mensual", fontsize=12, fontweight="bold")
    axes[1].set_xticklabels([t.strftime("%b %Y") for t in tipo_tiempo.index], rotation=45, ha="right")

    plt.suptitle("Acciones directas vs. indirectas en el tiempo", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.show()

    return tipo_tiempo
