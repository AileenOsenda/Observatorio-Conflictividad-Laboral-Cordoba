# -*- coding: utf-8 -*-
"""
main.py
========
Orquestador del pipeline completo — ORDEN DE EJECUCIÓN CORREGIDO.

# Descripción:
#   Este script importa cada módulo numerado (01 a 09) y ejecuta el
#   pipeline completo en el orden correcto de dependencias. Reemplaza
#   la ejecución celda-por-celda del notebook original, donde el
#   reporte de incidencias (Fase 2.2) podía correr ANTES que la
#   limpieza (Fase 2.3) y romper con NameError.
#
# Orden corregido (a diferencia del notebook original):
#   1) Cargar datos                              (módulo 01)
#   2) Limpiar el corpus                         (módulo 02) — UNA sola vez
#   3) Test de calidad pre/post                  (módulo 03) — usa el resultado de (2)
#   4) Reporte de incidencias (.xlsx)             (módulo 04) — usa el resultado de (2), NUNCA antes
#   5) Resumen ejecutivo de impacto               (módulo 05) — reutiliza (2), no la recalcula
#   6) Análisis descriptivos (opcional)           (módulo 06)
#   7) Análisis avanzados (opcional)              (módulo 07)
#   8) Perfil editorial y redes (opcional)        (módulo 08)
#   9) Motor gráfico interactivo (opcional)       (módulo 09)
#
# Uso:
#   Ejecutar como script (`python main.py`) desde la carpeta que
#   contiene todos los módulos numerados, con las librerías del
#   proyecto instaladas (ver requirements.txt). Los pasos 6 a 9 son
#   opcionales — comentar sus llamadas si solo interesa el pipeline de
#   limpieza y control de calidad (pasos 1 a 5).
#
# Dependencias:
#   Todos los módulos de este mismo paquete, importados dinámicamente
#   con importlib porque sus nombres de archivo llevan prefijo numérico.
"""

import importlib

# ── Import dinámico de cada módulo (nombres con prefijo numérico) ──
carga_datos = importlib.import_module("01_carga_datos")
limpieza_corpus = importlib.import_module("02_limpieza_corpus")
test_calidad = importlib.import_module("03_test_calidad")
reporte_incidencias = importlib.import_module("04_reporte_incidencias")
resumen_ejecutivo = importlib.import_module("05_resumen_ejecutivo")
analisis_descriptivos = importlib.import_module("06_analisis_descriptivos")
analisis_avanzados = importlib.import_module("07_analisis_avanzados")
perfil_editorial_redes = importlib.import_module("08_perfil_editorial_redes")
motor_grafico = importlib.import_module("09_motor_grafico")


def ejecutar_pipeline(
    ruta_archivo: str,
    nombre_hoja,
    umbral_similitud: float = 0.6,
    correr_analisis_opcionales: bool = False,
    correr_motor_grafico: bool = False,
):
    """
    Corre el pipeline completo en el orden correcto.

    Parámetros
    ----------
    ruta_archivo : str
        Ruta al Excel de origen.
    nombre_hoja : str | int
        Nombre o índice de la hoja a leer.
    umbral_similitud : float
        Umbral de similitud de Jaccard para detectar duplicados semánticos.
    correr_analisis_opcionales : bool
        Si True, corre también las Fases 3 (descriptivos), 4 (avanzados)
        y 5 (perfil editorial/redes) — no obligatorias para el control
        de calidad, pero sí para el análisis sustantivo del corpus.
    correr_motor_grafico : bool
        Si True, al final abre el menú interactivo de la Fase 6.

    Retorna
    -------
    dict con las variables centrales generadas por el pipeline:
    df, df_limpio, df_falsos, df_duplicados, tabla_resumen,
    tabla_faltantes, hojas_incidencias.
    """
    # ── Paso 1: carga de datos ──────────────────────────────────
    carga_datos.montar_drive()
    df = carga_datos.cargar_base(ruta_archivo, nombre_hoja)
    print(f"Base cargada: {len(df)} filas, {len(df.columns)} columnas.\n")

    # ── Paso 2: limpieza del corpus — SE EJECUTA UNA SOLA VEZ ───
    resultado = limpieza_corpus.limpiar_corpus(df, umbral_similitud=umbral_similitud)
    df_limpio = resultado["df_limpio"]
    df_falsos = resultado["falsos_positivos"]
    df_duplicados = resultado["duplicados_entre_fuentes"]

    # ── Paso 3: test de calidad — usa df_limpio ya calculado ────
    tabla_resumen, tabla_faltantes = test_calidad.test_calidad_corpus(df, df_limpio)

    # ── Paso 4: reporte de incidencias — CORRIDO DESPUÉS de (2) ─
    # Esta es la corrección central pedida: antes, en el notebook, esta
    # llamada podía dispararse antes de tener df_limpio/df_falsos/
    # df_duplicados definidos. Acá el orden está forzado por el propio
    # flujo del script: es físicamente imposible llegar a esta línea
    # sin haber pasado antes por el Paso 2.
    hojas_incidencias = reporte_incidencias.generar_reporte_incidencias(
        df, df_limpio, df_falsos, df_duplicados
    )
    # Descarga automática si se corre en Colab; en local, el archivo ya
    # quedó guardado en el disco por generar_reporte_incidencias().
    import os
    archivo_generado = sorted(
        f for f in os.listdir(".") if f.startswith("reporte_incidencias_")
    )[-1]
    reporte_incidencias.descargar_reporte(archivo_generado)

    # ── Paso 5: resumen ejecutivo — REUTILIZA `resultado`, no lo recalcula ──
    resumen_ejecutivo.generar_resumen_ejecutivo(df, resultado)

    salida = {
        "df": df,
        "df_limpio": df_limpio,
        "df_falsos": df_falsos,
        "df_duplicados": df_duplicados,
        "tabla_resumen": tabla_resumen,
        "tabla_faltantes": tabla_faltantes,
        "hojas_incidencias": hojas_incidencias,
    }

    # ── Pasos 6-8: análisis opcionales (Fases 3, 4 y 5) ─────────
    if correr_analisis_opcionales:
        # Fase 3 — descriptivos simples
        analisis_descriptivos.vista_general(df_limpio)
        freq_diario = analisis_descriptivos.frecuencia_por_diario(df_limpio)
        freq_dinamica, tabla_cruzada = analisis_descriptivos.frecuencia_por_dinamica(df_limpio)
        serie_temporal = analisis_descriptivos.evolucion_temporal_simple(df_limpio)
        analisis_descriptivos.graficos_dinamica_diario(freq_dinamica, freq_diario)
        analisis_descriptivos.serie_temporal_linea(serie_temporal)
        analisis_descriptivos.heatmap_diario_dinamica(tabla_cruzada)
        analisis_descriptivos.nube_palabras_titulo(df_limpio, limpieza_corpus.tokens)
        analisis_descriptivos.resumen_ejecutivo_corpus(df_limpio, freq_dinamica, freq_diario)

        # Fase 4 — avanzados (requieren correr notas_vs_tiempo primero)
        df_temp, serie_diaria, media_movil_7 = analisis_avanzados.notas_vs_tiempo(df_limpio)
        analisis_avanzados.comparacion_periodos(df_temp, fecha_corte="2024-12-10")
        analisis_avanzados.deteccion_picos(df_temp, serie_diaria, media_movil_7)
        analisis_avanzados.evolucion_organizaciones(df_limpio, df_temp)
        analisis_avanzados.directa_vs_indirecta(df_temp)

        # Fase 5 — perfil editorial, redes y actores
        perfil_editorial_redes.perfil_tematico_por_diario(df_limpio)
        perfil_editorial_redes.red_coocurrencia_titulos(df_limpio, limpieza_corpus.tokens)
        perfil_editorial_redes.diversidad_shannon_por_diario(df_limpio)
        perfil_editorial_redes.organizaciones_mas_mencionadas(df_limpio)

    # ── Paso 9: motor gráfico interactivo (Fase 6) ──────────────
    if correr_motor_grafico:
        motor_grafico.menu_graficos(df_limpio)

    return salida


if __name__ == "__main__":
    # Ajustar estos dos parámetros antes de correr
    RUTA_ARCHIVO = "/content/drive/MyDrive/Colab Notebooks/base_2022_2026.xlsx"
    NOMBRE_HOJA = "Base"

    resultados_pipeline = ejecutar_pipeline(
        ruta_archivo=RUTA_ARCHIVO,
        nombre_hoja=NOMBRE_HOJA,
        umbral_similitud=0.6,
        correr_analisis_opcionales=False,  # cambiar a True para correr Fases 3-5
        correr_motor_grafico=False,        # cambiar a True para abrir el menú interactivo
    )
