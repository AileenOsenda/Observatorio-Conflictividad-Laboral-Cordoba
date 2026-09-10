# -*- coding: utf-8 -*-
"""
04_reporte_incidencias.py
===========================
FASE 2.2 del pipeline — Reporte de incidencias (Excel).

# Descripción:
#   Compila TODOS los registros problemáticos detectados en el pipeline
#   de limpieza (falsos positivos, duplicados semánticos entre fuentes,
#   duplicados exactos de fila completa, duplicados por Título+Diario+
#   Fecha, fechas inválidas, fechas fuera de rango, inconsistencias
#   Año != Fecha, links con formato inválido, y Dinámica Conflictual
#   vacía/placeholder) en un único archivo .xlsx con una hoja por tipo
#   de incidencia, más una hoja de Resumen.
#
# Uso:
#   *** CORRECCIÓN respecto a la versión anterior ***
#   Esta función NO se ejecuta automáticamente al importar el módulo.
#   En la versión previa, la celda del notebook llamaba a
#   `generar_reporte_incidencias(df, df_limpio, df_falsos, df_duplicados)`
#   al final del archivo, lo que rompía si se corría antes de que
#   `limpiar_corpus()` (módulo 02) generara esas variables.
#   Ahora la función solo se define acá; quien la use (ej. main.py) debe
#   llamarla EXPLÍCITAMENTE después de haber ejecutado la limpieza:
#
#       resultado = limpiar_corpus(df)                       # 1) limpiar primero
#       df_limpio = resultado["df_limpio"]
#       df_falsos = resultado["falsos_positivos"]
#       df_duplicados = resultado["duplicados_entre_fuentes"]
#       hojas = generar_reporte_incidencias(                 # 2) reporte después
#           df, df_limpio, df_falsos, df_duplicados
#       )
#
# Interpretación:
#   Cada fila del reporte incluye `id` (índice original en la base),
#   `posición` (número de fila, 1-indexado), `Título`, `Link`, `Diario`,
#   `Fecha` y el dato específico de la incidencia — pensado para que el
#   equipo de investigación pueda revisar manualmente cada caso marcado
#   sin volver al notebook/script de limpieza.
#
# Dependencias:
#   pandas, openpyxl. No importa nada del módulo 02: recibe los
#   DataFrames ya calculados como parámetros (bajo acoplamiento).
"""

import pandas as pd

# ══════════════════════════════════════════════════════════════
# REPORTE DE INCIDENCIAS — falsos positivos, duplicados, inconsistencias
# ══════════════════════════════════════════════════════════════
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

def _cols_disponibles(df, cols):
    """Devuelve solo las columnas de `cols` que existen en `df`."""
    return [c for c in cols if c in df.columns]


def generar_reporte_incidencias(
    df_original: pd.DataFrame,
    df_limpio: pd.DataFrame,
    df_falsos: pd.DataFrame,
    df_duplicados: pd.DataFrame,
    nombre_archivo: str = None,
) -> dict:
    """
    Compila todos los registros problemáticos detectados en el pipeline
    (falsos positivos, duplicados semánticos entre fuentes, fechas inválidas,
    inconsistencias Año≠Fecha, links con formato inválido, y valores vacíos
    o placeholder en Dinámica Conflictual) en un único Excel con una hoja
    por tipo de incidencia, más una hoja de resumen.

    Retorna un dict con cada DataFrame de incidencias (por si se quiere
    inspeccionar directamente en el notebook sin abrir el Excel).
    """
    df_original = df_original.reset_index(drop=False).rename(columns={"index": "id"})
    df_original["posición"] = df_original.index + 1  # 1-indexado, orden de aparición en la base

    cols_base = _cols_disponibles(
        df_original, ["id", "posición", "Título", "Link", "Diario", "Fecha", "Año",
                      "Dinámica Conflictual", "Departamento"]
    )

    hojas = {}

    # ── 1) Falsos positivos ──────────────────────────────────────
    if df_falsos is not None and not df_falsos.empty:
        df_fp = df_falsos.reset_index(drop=False).rename(columns={"index": "id"})
        df_fp["posición"] = df_original.set_index("id").reindex(df_fp["id"])["posición"].values
        cols_fp = _cols_disponibles(df_fp, cols_base + ["excepcion_detectada"])
        hojas["Falsos_Positivos"] = df_fp[cols_fp].sort_values("posición")
    else:
        hojas["Falsos_Positivos"] = pd.DataFrame(columns=cols_base + ["excepcion_detectada"])

    # ── 2) Duplicados semánticos entre fuentes (pares) ───────────
    if df_duplicados is not None and not df_duplicados.empty:
        df_dup = df_duplicados.copy()
        # Agregar posición en la base original para cada elemento del par, si es posible
        mapa_pos = df_original.set_index("id")["posición"] if "id" in df_original.columns else None
        cols_dup = _cols_disponibles(
            df_dup,
            ["idx_a", "diario_a", "fecha_a", "titular_a",
             "idx_b", "diario_b", "fecha_b", "titular_b", "similitud"]
        )
        hojas["Duplicados_Semanticos"] = df_dup[cols_dup].sort_values("similitud", ascending=False)
    else:
        hojas["Duplicados_Semanticos"] = pd.DataFrame(
            columns=["idx_a", "diario_a", "fecha_a", "titular_a",
                     "idx_b", "diario_b", "fecha_b", "titular_b", "similitud"]
        )

    # ── 3) Fechas no parseables (NaT) ─────────────────────────────
    if "Fecha" in df_original.columns:
        mask_fecha_nula = df_original["Fecha"].isna()
        hojas["Fechas_Invalidas"] = df_original.loc[mask_fecha_nula, cols_base]
    else:
        hojas["Fechas_Invalidas"] = pd.DataFrame(columns=cols_base)

    # ── 4) Fechas fuera de rango esperado (2012-2026) ─────────────
    if "Fecha" in df_original.columns:
        fecha_min, fecha_max = "2012-01-01", "2026-12-31"
        mask_fuera_rango = (
            df_original["Fecha"].notna()
            & ((df_original["Fecha"] < fecha_min) | (df_original["Fecha"] > fecha_max))
        )
        hojas["Fechas_Fuera_De_Rango"] = df_original.loc[mask_fuera_rango, cols_base]
    else:
        hojas["Fechas_Fuera_De_Rango"] = pd.DataFrame(columns=cols_base)

    # ── 5) Inconsistencias Año ≠ Año(Fecha) ───────────────────────
    if "Año" in df_original.columns and "Fecha" in df_original.columns:
        mask_valido = df_original["Fecha"].notna() & df_original["Año"].notna()
        mask_incons = mask_valido & (df_original["Fecha"].dt.year != df_original["Año"])
        df_incons = df_original.loc[mask_incons, cols_base].copy()
        df_incons["año_real_segun_fecha"] = df_original.loc[mask_incons, "Fecha"].dt.year
        hojas["Inconsistencia_Anio"] = df_incons
    else:
        hojas["Inconsistencia_Anio"] = pd.DataFrame(columns=cols_base + ["año_real_segun_fecha"])

    # ── 6) Links con formato inválido ─────────────────────────────
    if "Link" in df_original.columns:
        mask_link_malo = (
            df_original["Link"].notna()
            & ~df_original["Link"].astype(str).str.startswith("http")
        )
        hojas["Links_Invalidos"] = df_original.loc[mask_link_malo, cols_base]
    else:
        hojas["Links_Invalidos"] = pd.DataFrame(columns=cols_base)

    # ── 7) Dinámica Conflictual vacía / placeholder ───────────────
    if "Dinámica Conflictual" in df_original.columns:
        placeholders = ["sin datos", "sin dato", "s/d", "nan", "ninguna", ""]
        mask_vacia = (
            df_original["Dinámica Conflictual"].astype(str).str.strip().str.lower().isin(placeholders)
        )
        hojas["Dinamica_Vacia"] = df_original.loc[mask_vacia, cols_base]
    else:
        hojas["Dinamica_Vacia"] = pd.DataFrame(columns=cols_base)

    # ── 8) Duplicados exactos de fila completa ────────────────────
    mask_dup_exacto = df_original.duplicated(subset=[c for c in df_original.columns if c not in ["id", "posición"]], keep=False)
    hojas["Duplicados_Exactos"] = df_original.loc[mask_dup_exacto, cols_base].sort_values("posición")

    # ── 9) Duplicados por Título + Diario + Fecha (probable mismo evento, misma fuente) ──
    if _cols_disponibles(df_original, ["Título", "Diario", "Fecha"]) == ["Título", "Diario", "Fecha"]:
        mask_dup_titulo = df_original.duplicated(subset=["Título", "Diario", "Fecha"], keep=False)
        hojas["Duplicados_Titulo_Diario_Fecha"] = df_original.loc[mask_dup_titulo, cols_base].sort_values("posición")
    else:
        hojas["Duplicados_Titulo_Diario_Fecha"] = pd.DataFrame(columns=cols_base)

    # ── Hoja de resumen ────────────────────────────────────────────
    resumen = pd.DataFrame({
        "Tipo de incidencia": [
            "Falsos positivos (excepciones)",
            "Duplicados semánticos entre fuentes (pares)",
            "Fechas no parseables (NaT)",
            "Fechas fuera de rango (2012-2026)",
            "Inconsistencia Año ≠ Año(Fecha)",
            "Links con formato inválido",
            "Dinámica Conflictual vacía/placeholder",
            "Duplicados exactos (fila completa)",
            "Duplicados por Título+Diario+Fecha",
        ],
        "Cantidad de casos": [
            len(hojas["Falsos_Positivos"]),
            len(hojas["Duplicados_Semanticos"]),
            len(hojas["Fechas_Invalidas"]),
            len(hojas["Fechas_Fuera_De_Rango"]),
            len(hojas["Inconsistencia_Anio"]),
            len(hojas["Links_Invalidos"]),
            len(hojas["Dinamica_Vacia"]),
            len(hojas["Duplicados_Exactos"]),
            len(hojas["Duplicados_Titulo_Diario_Fecha"]),
        ],
    })
    resumen["% sobre el corpus original"] = (resumen["Cantidad de casos"] / len(df_original) * 100).round(2)
    hojas["Resumen"] = resumen

    # ── Escribir el Excel ────────────────────────────────────────
    if nombre_archivo is None:
        nombre_archivo = f"reporte_incidencias_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.xlsx"

    orden_hojas = [
        "Resumen", "Falsos_Positivos", "Duplicados_Semanticos", "Duplicados_Exactos",
        "Duplicados_Titulo_Diario_Fecha", "Fechas_Invalidas", "Fechas_Fuera_De_Rango",
        "Inconsistencia_Anio", "Links_Invalidos", "Dinamica_Vacia",
    ]

    with pd.ExcelWriter(nombre_archivo, engine="openpyxl") as writer:
        for hoja in orden_hojas:
            hojas[hoja].to_excel(writer, sheet_name=hoja[:31], index=False)

    # ── Formato: encabezados en negrita + ancho de columna automático ──
    wb = writer.book if hasattr(writer, "book") else None
    from openpyxl import load_workbook
    wb = load_workbook(nombre_archivo)
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

    for nombre_hoja in wb.sheetnames:
        ws = wb[nombre_hoja]
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.freeze_panes = "A2"
        for col_cells in ws.columns:
            longitud_max = max((len(str(c.value)) for c in col_cells if c.value is not None), default=10)
            col_letra = get_column_letter(col_cells[0].column)
            ws.column_dimensions[col_letra].width = min(max(longitud_max + 2, 10), 60)

    wb.save(nombre_archivo)

    print(f"{'═'*60}")
    print(f"  REPORTE DE INCIDENCIAS GENERADO")
    print(f"{'═'*60}")
    print(resumen.to_string(index=False))
    print(f"\nArchivo: {nombre_archivo}")

    return hojas


def descargar_reporte(nombre_archivo: str):
    """
    Descarga el archivo generado al equipo local, si se corre en Colab.
    En un entorno local, no hace nada (el archivo ya quedó guardado en disco).
    """
    try:
        from google.colab import files as _files_download  # solo existe en Colab
        _files_download.download(nombre_archivo)
    except ImportError:
        print(f"Entorno local detectado; el archivo ya está en disco: {nombre_archivo}")
