# -*- coding: utf-8 -*-
"""
02_limpieza_corpus.py
======================
FASE 2 del pipeline — Control de calidad del corpus.

# Descripción:
#   Dos mecanismos de limpieza independientes sobre la columna `Título`:
#     A) EXCEPCIONES: diccionario de expresiones regulares agrupadas que
#        detecta títulos que activarían un filtro laboral por ambigüedad
#        léxica (ej. "corte de luz" vs "corte de ruta") pero que en
#        realidad no corresponden a conflictividad laboral.
#     B) SIMILITUD DE JACCARD: compara títulos publicados por distintos
#        diarios en una ventana de ±1 día, y marca como potencial "mismo
#        evento" a los pares con similitud léxica >= umbral (0.6 default).
#   Además, antes de aplicar A y B, `limpiar_corpus()` elimina duplicados
#   exactos de Título+Link y de Link solo (deduplicación básica previa).
#
# Uso:
#   `limpiar_corpus(df)` se ejecuta UNA VEZ, inmediatamente después de la
#   carga (Fase 1), y ANTES que cualquier otro módulo del pipeline —
#   todos los módulos siguientes (reporte de incidencias, resumen
#   ejecutivo, análisis, motor gráfico) dependen de su resultado.
#
# Interpretación:
#   El log impreso indica cuántos duplicados exactos, falsos positivos y
#   pares de duplicados semánticos se detectaron. Los duplicados
#   semánticos NO se eliminan automáticamente del corpus limpio: quedan
#   a criterio del investigador (útiles para análisis de agenda
#   comparada entre medios).
#
# Justificación:
#   A diferencia de un corpus generado por scraping (donde el filtro de
#   ingreso es un regex sobre texto libre), esta base ya fue codificada
#   manualmente. El control de calidad aquí audita la consistencia del
#   corpus codificado (duplicados, ambigüedad léxica residual) más que
#   filtrar contenido no laboral.
"""

import pandas as pd
import re
import itertools
import numpy as np

# ══════════════════════════════════════════════════════════════
# A) DICCIONARIO DE EXCEPCIONES (falsos positivos)
# ══════════════════════════════════════════════════════════════
EXCEPCIONES = {
    "cortes_servicios": re.compile(
        r'\bcorte[s]?\s+(de\s+)?(luz|agua|gas|electricidad|suministro|servicio[s]?|energia|energía)\b|'
        r'\bcorte[s]?\s+program[a-zA-Z]*\b',
        re.IGNORECASE
    ),
    "cortes_viales": re.compile(
        r'\bcorte[s]?\s+(de\s+)?(tránsito|transito|circulacion|circulación|autopista|acceso)\b|'
        r'\bcorte\s+vial\b',
        re.IGNORECASE
    ),
    "cortes_estetica": re.compile(
        r'\bcorte[s]?\s+(de\s+)?(cabello|pelo|carne|madera|césped|cesped)\b',
        re.IGNORECASE
    ),
    "trabajo_obra": re.compile(
        r'\btrabajos?\s+(de\s+)?(obra[s]?|construcci[oó]n|pavimentaci[oó]n|'
        r'repavimentaci[oó]n|bacheo|asfalto|mantenimiento|refacci[oó]n|cloacas?|'
        r'desag[üu]e[s]?|viales?)\b|'
        r'\btrabajos?\s+municipales?\b',
        re.IGNORECASE
    ),
    "paro_medico": re.compile(
        r'\bparo\s+(cardíaco|cardiaco|card[íi]aco|respiratorio|'
        r'cerebro[a-zA-Z]*|fulminante)\b',
        re.IGNORECASE
    ),
    "transporte_vial": re.compile(
        r'\baccidente[s]?\s+de\s+transporte\b|'
        r'\btransporte\s+(vial|de\s+carga\s+no\s+sindical|escolar\b)',
        re.IGNORECASE
    ),
    "crisis_no_laboral": re.compile(
        r'\bcrisis\s+(clim[aá]tica|energ[eé]tica|h[íi]drica|ambiental|'
        r'pol[íi]tica\b(?!\s+y\s+laboral))\b',
        re.IGNORECASE
    ),
    "aplicaciones_tech": re.compile(
        r'\baplicacion(?:es)?\s+(m[oó]vil(?:es)?|de\s+celular|android|ios|'
        r'inform[aá]tic[ao]|web|bancaria[s]?(?!\s+en\s+conflicto))\b',
        re.IGNORECASE
    ),
    "industria_no_laboral": re.compile(
        r'\bindustria\s+(cultural|del\s+entretenimiento|agropecuaria|'
        r'navide[ñn][ao]|discogr[aá]fica)\b',
        re.IGNORECASE
    ),
    "suspension_no_laboral": re.compile(
        r'\bsuspen[a-zA-Z]*\s+(el\s+partido|el\s+evento|por\s+lluvia|'
        r'por\s+mal\s+tiempo|cl[aá]sico|show|recital|concierto)\b',
        re.IGNORECASE
    ),
    "marcha_no_protesta": re.compile(
        r'\bmarcha\s+(atl[eé]tica|olímpica|olimpica|militar|fúnebre|funébre|'
        r'de\s+antorchas|blanca(?!\s+de\s+trabajadores))\b',
        re.IGNORECASE
    ),
    "derechos_no_laborales": re.compile(
        r'\bderechos?\s+(de\s+autor|de\s+admisi[oó]n|de\s+propiedad\s+intelectual|'
        r'reales?\b)\b',
        re.IGNORECASE
    ),
}

def es_falso_positivo(titular: str) -> tuple[bool, str]:
    """Evalúa si un titular pertenece a una categoría de excepción."""
    for nombre_exc, patron_exc in EXCEPCIONES.items():
        if patron_exc.search(titular):
            return True, nombre_exc
    return False, ""

# ══════════════════════════════════════════════════════════════
# B) DETECCIÓN DE MISMO EVENTO EN DISTINTAS FUENTES
# ══════════════════════════════════════════════════════════════
STOPWORDS_ES = {
    "de", "la", "el", "en", "y", "a", "los", "las", "del", "un", "una",
    "es", "se", "por", "con", "para", "que", "al", "lo", "su", "sus",
    "le", "más", "pero", "como", "si", "sobre", "este", "esta", "son",
    "ha", "fue", "ser", "no", "hay", "ya", "entre", "donde", "también",
}

def tokens(texto: str) -> set:
    """Convierte un texto en un conjunto de palabras significativas."""
    palabras = re.findall(r'\b[a-záéíóúüñ]{3,}\b', texto.lower())
    return {p for p in palabras if p not in STOPWORDS_ES}

def similitud_jaccard(texto_a: str, texto_b: str) -> float:
    """J(A, B) = |A ∩ B| / |A ∪ B|. Rango: 0.0 a 1.0."""
    set_a = tokens(texto_a)
    set_b = tokens(texto_b)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)

def detectar_duplicados_entre_fuentes(
    df: "pd.DataFrame",
    umbral: float = 0.6,
    col_titular: str = "Título",
    col_diario: str = "Diario",
    col_fecha: str = "Fecha",
) -> "pd.DataFrame":
    """Detecta noticias que cubren el mismo evento en distintos diarios (±1 día)."""
    df = df.copy()
    df[col_fecha] = pd.to_datetime(df[col_fecha], errors="coerce")

    pares_duplicados = []
    fechas_unicas = sorted(df[col_fecha].dropna().dt.date.unique())

    for fecha in fechas_unicas:
        ventana = pd.to_datetime([
            pd.Timestamp(fecha) - pd.Timedelta(days=1),
            pd.Timestamp(fecha),
            pd.Timestamp(fecha) + pd.Timedelta(days=1),
        ])
        mask = df[col_fecha].dt.normalize().isin(ventana)
        grupo = df[mask]

        indices = grupo.index.tolist()
        for idx_a, idx_b in itertools.combinations(indices, 2):
            fila_a, fila_b = grupo.loc[idx_a], grupo.loc[idx_b]

            if fila_a[col_diario] == fila_b[col_diario]:
                continue

            sim = similitud_jaccard(str(fila_a[col_titular]), str(fila_b[col_titular]))

            if sim >= umbral:
                pares_duplicados.append({
                    "idx_a": idx_a, "diario_a": fila_a[col_diario],
                    "fecha_a": fila_a[col_fecha].date(), "titular_a": fila_a[col_titular],
                    "idx_b": idx_b, "diario_b": fila_b[col_diario],
                    "fecha_b": fila_b[col_fecha].date(), "titular_b": fila_b[col_titular],
                    "similitud": round(sim, 3),
                })

    df_pares = pd.DataFrame(pares_duplicados)
    if not df_pares.empty:
        df_pares["par_key"] = df_pares.apply(
            lambda r: tuple(sorted([r["idx_a"], r["idx_b"]])), axis=1
        )
        df_pares = df_pares.drop_duplicates("par_key").drop(columns="par_key")
        df_pares = df_pares.sort_values("similitud", ascending=False).reset_index(drop=True)

    return df_pares

# ══════════════════════════════════════════════════════════════
# FUNCIÓN PRINCIPAL — integra A + B
# ══════════════════════════════════════════════════════════════
def limpiar_corpus(df: "pd.DataFrame", umbral_similitud: float = 0.6) -> dict:
    """Aplica el pipeline completo de control de calidad sobre el DataFrame."""
    df = df.copy()

    print(f"{'═'*55}")
    print(f"  Control de calidad del corpus")
    print(f"{'─'*55}")
    print(f"  Noticias originales         : {len(df)}")

    # ▼▼▼▼▼▼▼▼▼▼ NUEVO BLOQUE DE CÓDIGO ▼▼▼▼▼▼▼▼▼▼

    if "Link" in df.columns:
        # 1. Eliminar filas donde TÍTULO y LINK estén duplicados al mismo tiempo
        # (se exige que el link no sea un valor nulo para evitar falsos borrados)
        if "Título" in df.columns:
            duplicados_tit_link = df.duplicated(subset=["Título", "Link"], keep="first") & df["Link"].notna()
            df = df[~duplicados_tit_link]
            if duplicados_tit_link.sum() > 0:
                print(f"  Duplicados Título+Link elim.: {duplicados_tit_link.sum()}")

        # 2. Eliminar filas donde SOLO EL LINK esté duplicado (dejando el primero que aparece)
        duplicados_link = df.duplicated(subset=["Link"], keep="first") & df["Link"].notna()
        df = df[~duplicados_link]
        if duplicados_link.sum() > 0:
            print(f"  Links duplicados eliminados : {duplicados_link.sum()}")

    # ▲▲▲▲▲▲▲▲▲▲ FIN NUEVO BLOQUE ▲▲▲▲▲▲▲▲▲▲

    df[["es_falso_positivo", "excepcion_detectada"]] = df["Título"].apply(
        lambda t: pd.Series(es_falso_positivo(str(t)))
    )

    df_falsos = df[df["es_falso_positivo"]].copy()
    df_limpio = df[~df["es_falso_positivo"]].copy()

    print(f"  Falsos positivos descartados: {len(df_falsos)}")
    if not df_falsos.empty:
        print(f"\n  Excepciones activadas:")
        for exc, n in df_falsos["excepcion_detectada"].value_counts().items():
            print(f"    · {exc:<30} {n} casos")

    print(f"\n  Detectando duplicados semánticos (umbral={umbral_similitud})...")
    df_duplicados = detectar_duplicados_entre_fuentes(df_limpio, umbral=umbral_similitud)
    print(f"  Pares de noticias similares : {len(df_duplicados)}")

    if not df_duplicados.empty:
        print(f"\n  Muestra de duplicados detectados:")
        for _, row in df_duplicados.head(3).iterrows():
            print(f"\n    sim={row['similitud']}  fecha={row['fecha_a']}")
            print(f"    [{row['diario_a']}] {str(row['titular_a'])[:70]}…")
            print(f"    [{row['diario_b']}] {str(row['titular_b'])[:70]}…")

    print(f"{'═'*55}")
    print(f"  Corpus limpio final         : {len(df_limpio)} noticias")

    return {
        "df_limpio": df_limpio.drop(columns=["es_falso_positivo", "excepcion_detectada"]),
        "falsos_positivos": df_falsos,
        "duplicados_entre_fuentes": df_duplicados
    }
