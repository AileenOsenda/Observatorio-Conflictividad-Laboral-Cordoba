# -*- coding: utf-8 -*-
"""
03_test_calidad.py
====================
FASE 2.1 del pipeline — Test de calidad pre/post limpieza.

# Descripción:
#   Compara el corpus original (`df`) contra el corpus limpio
#   (`df_limpio`, generado por 02_limpieza_corpus.limpiar_corpus) en:
#   total de registros, filas 100% duplicadas, links duplicados,
#   títulos duplicados exactos, valores faltantes por columna clave,
#   fechas no parseables (NaT), fechas fuera del rango 2012-2026,
#   inconsistencias Año != Año(Fecha), links con formato inválido, y
#   celdas vacías o con placeholder ("sin datos", "s/d") en
#   `Dinámica Conflictual`.
#
# Uso:
#   IMPORTANTE: requiere que `df_limpio` ya exista, es decir, debe
#   ejecutarse DESPUÉS de correr `limpiar_corpus()` (módulo 02) y NUNCA
#   antes. Se llama como:
#       tabla_resumen, tabla_faltantes = test_calidad_corpus(df, df_limpio)
#
# Interpretación:
#   Permite cuantificar exactamente qué mejoró (y en qué magnitud) tras
#   la limpieza — útil para justificar metodológicamente el proceso de
#   depuración en un informe de investigación.
#
# Dependencias:
#   Requiere pandas y numpy. No depende de otros módulos del proyecto
#   (solo recibe los DataFrames ya calculados como parámetros).
"""

import pandas as pd
import numpy as np


# ══════════════════════════════════════════════════════════════
# TEST DE CALIDAD
# ══════════════════════════════════════════════════════════════
def test_calidad_corpus(df_original: pd.DataFrame, df_limpio: pd.DataFrame) -> pd.DataFrame:
    """Compara métricas de calidad entre el corpus original y el corpus limpio."""
    reporte = {}

    reporte['Total de registros'] = (len(df_original), len(df_limpio))
    reporte['Filas 100% duplicadas'] = (df_original.duplicated().sum(), df_limpio.duplicated().sum())

    if 'Link' in df_original.columns:
        reporte['Links duplicados'] = (
            df_original['Link'].duplicated().sum(), df_limpio['Link'].duplicated().sum()
        )

    if 'Título' in df_original.columns:
        reporte['Títulos duplicados (exactos)'] = (
            df_original['Título'].duplicated().sum(), df_limpio['Título'].duplicated().sum()
        )

    columnas_clave = ['Título', 'Fecha', 'Diario', 'Dinámica Conflictual',
                       'Formato agregado', 'Departamento', 'Año']
    columnas_clave = [c for c in columnas_clave if c in df_original.columns]

    faltantes_pre  = df_original[columnas_clave].isna().sum()
    faltantes_post = df_limpio[columnas_clave].isna().sum()

    if 'Fecha' in df_original.columns:
        fechas_invalidas_pre  = df_original['Fecha'].isna().sum()
        fechas_invalidas_post = df_limpio['Fecha'].isna().sum()

        fecha_min, fecha_max = '2012-01-01', '2026-12-31'
        fuera_rango_pre = df_original[
            (df_original['Fecha'].notna()) &
            ((df_original['Fecha'] < fecha_min) | (df_original['Fecha'] > fecha_max))
        ].shape[0]
        fuera_rango_post = df_limpio[
            (df_limpio['Fecha'].notna()) &
            ((df_limpio['Fecha'] < fecha_min) | (df_limpio['Fecha'] > fecha_max))
        ].shape[0]

        reporte['Fechas no parseables (NaT)'] = (fechas_invalidas_pre, fechas_invalidas_post)
        reporte['Fechas fuera de rango 2012-2026'] = (fuera_rango_pre, fuera_rango_post)

    if 'Año' in df_original.columns and 'Fecha' in df_original.columns:
        def contar_inconsistencias_año(d):
            mask_valido = d['Fecha'].notna() & d['Año'].notna()
            return (d.loc[mask_valido, 'Fecha'].dt.year != d.loc[mask_valido, 'Año']).sum()

        reporte['Inconsistencias Año ≠ Año(Fecha)'] = (
            contar_inconsistencias_año(df_original), contar_inconsistencias_año(df_limpio)
        )

    if 'Link' in df_original.columns:
        def contar_links_invalidos(d):
            return d[d['Link'].notna() & ~d['Link'].astype(str).str.startswith('http')].shape[0]

        reporte['Links con formato inválido'] = (
            contar_links_invalidos(df_original), contar_links_invalidos(df_limpio)
        )

    if 'Dinámica Conflictual' in df_original.columns:
        placeholders = ['sin datos', 'sin dato', 's/d', 'nan', 'ninguna', '']
        def contar_placeholders(d, col):
            return d[col].astype(str).str.strip().str.lower().isin(placeholders).sum()

        reporte['"Dinámica Conflictual" vacía/placeholder'] = (
            contar_placeholders(df_original, 'Dinámica Conflictual'),
            contar_placeholders(df_limpio, 'Dinámica Conflictual')
        )

    tabla_resumen = pd.DataFrame(reporte, index=['Pre-limpieza', 'Post-limpieza']).T
    tabla_resumen['Diferencia'] = tabla_resumen['Pre-limpieza'] - tabla_resumen['Post-limpieza']
    tabla_resumen['% reducción'] = (
        (tabla_resumen['Diferencia'] / tabla_resumen['Pre-limpieza'].replace(0, np.nan)) * 100
    ).round(1)

    tabla_faltantes = pd.DataFrame({'Pre-limpieza': faltantes_pre, 'Post-limpieza': faltantes_post})
    tabla_faltantes['Diferencia'] = tabla_faltantes['Pre-limpieza'] - tabla_faltantes['Post-limpieza']

    print(f"{'═'*70}")
    print(f"  TEST DE CALIDAD — CORPUS PRE vs. POST LIMPIEZA")
    print(f"{'═'*70}\n")
    print(tabla_resumen.to_string())
    print(f"\n{'─'*70}")
    print(f"  VALORES FALTANTES POR COLUMNA CLAVE")
    print(f"{'─'*70}")
    print(tabla_faltantes.to_string())
    print(f"\n{'═'*70}")

    return tabla_resumen, tabla_faltantes
