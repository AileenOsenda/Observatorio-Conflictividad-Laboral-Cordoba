# -*- coding: utf-8 -*-
"""
05_resumen_ejecutivo.py
=========================
FASE 2.4 del pipeline — Resumen ejecutivo de impacto de la limpieza.

# Descripción:
#   Imprime un cuadro compacto (estilo caja de texto) con: volumen
#   inicial y final del corpus, tasa de retención (%), total de notas
#   descartadas desglosado en duplicados vs. falsos positivos temáticos,
#   y advertencias sobre pares semánticos sospechosos aún no eliminados.
#
# Uso:
#   *** CORRECCIÓN respecto a la versión anterior ***
#   La celda original volvía a llamar a `limpiar_corpus(df, ...)` al
#   final, duplicando el procesamiento (la limpieza ya se había hecho en
#   la Fase 2.3). Ahora `generar_resumen_ejecutivo()` recibe el
#   `resultado` de `limpiar_corpus()` ya calculado, sin recalcularlo:
#
#       resultado = limpiar_corpus(df)              # una sola vez
#       generar_resumen_ejecutivo(df, resultado)     # reutiliza el resultado
#
# Interpretación:
#   El desglose "duplicados vs. falsos positivos" se calcula por resta
#   (total_removidos - falsos_positivos_removidos), asumiendo que toda
#   la diferencia corresponde a duplicados de Título/Link. Es una
#   aproximación: si se agregan otros criterios de descarte al pipeline
#   de limpieza, este cálculo debería revisarse.
#
# Dependencias:
#   pandas (solo para el type hint de DataFrame; toda la lógica interna
#   usa los objetos ya calculados, sin volver a operar sobre pandas).
"""

import pandas as pd

# ══════════════════════════════════════════════════════════════
# C) RESUMEN EJECUTIVO DE IMPACTO
# ══════════════════════════════════════════════════════════════
def generar_resumen_ejecutivo(df_original: pd.DataFrame, resultado_limpieza: dict):
    """Genera un cuadro resumen de alto nivel sobre los registros eliminados y retenidos."""

    df_limpio = resultado_limpieza["df_limpio"]
    df_falsos = resultado_limpieza["falsos_positivos"]
    df_duplicados = resultado_limpieza["duplicados_entre_fuentes"]

    total_orig = len(df_original)
    total_limpio = len(df_limpio)
    total_removidos = total_orig - total_limpio

    # Desglose de descartes
    falsos_positivos_removidos = len(df_falsos)
    # Por descarte matemático, lo que se borró que NO es falso positivo, son los duplicados de Título/Link
    duplicados_exactos_removidos = total_removidos - falsos_positivos_removidos

    # Cálculos de porcentaje
    pct_retenido = (total_limpio / total_orig) * 100 if total_orig > 0 else 0
    pct_removido = (total_removidos / total_orig) * 100 if total_orig > 0 else 0

    print(f"\n╔════════════════════════════════════════════════════════════╗")
    print(f"║               RESUMEN EJECUTIVO DE LIMPIEZA                ║")
    print(f"╠════════════════════════════════════════════════════════════╣")
    print(f"║  Volumen inicial del corpus   : {total_orig:>7} noticias           ║")
    print(f"║  Volumen final (Corpus Limpio): {total_limpio:>7} noticias           ║")
    print(f"║  Tasa de retención            : {pct_retenido:>7.1f}%                   ║")
    print(f"╠════════════════════════════════════════════════════════════╣")
    print(f"║  TOTAL NOTICIAS DESCARTADAS   : {total_removidos:>7} ({pct_removido:>4.1f}%)           ║")
    print(f"║    ├─ Duplicados (Link/Título): {duplicados_exactos_removidos:>7}                    ║")
    print(f"║    └─ Falsos Positivos (Temas): {falsos_positivos_removidos:>7}                    ║")
    print(f"╠════════════════════════════════════════════════════════════╣")
    print(f"║  ADVERTENCIAS POST-LIMPIEZA                                ║")
    print(f"║    ├─ Pares semánticos sospechosos : {len(df_duplicados):>5}                 ║")
    print(f"║    └─ (Mismo evento en distintos diarios - NO eliminados)  ║")
    print(f"╚════════════════════════════════════════════════════════════╝\n")
