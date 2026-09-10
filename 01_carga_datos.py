# -*- coding: utf-8 -*-
"""
01_carga_datos.py
==================
FASE 1 del pipeline — Carga de datos.

# Descripción:
#   Monta Google Drive (si se corre en Colab), lee el archivo Excel de la
#   base con pandas, limpia espacios sobrantes en los nombres de columna
#   (ej. " Grado Agrupación" -> "Grado Agrupación") y parsea la columna
#   `Fecha` a tipo datetime con formato día/mes/año.
#
# Uso:
#   Es el punto de entrada obligatorio del pipeline. Ajustar RUTA_ARCHIVO
#   y NOMBRE_HOJA según la ubicación real del archivo y el nombre exacto
#   de la hoja a usar (ver diagnóstico con pd.ExcelFile(...).sheet_names
#   si no se conoce el nombre de antemano).
#
# Interpretación:
#   df.info() confirma que `Fecha` quedó tipada como datetime64 (no texto)
#   y muestra la cantidad de valores nulos por columna.
#
# Justificación:
#   El formato .xlsx preserva estructura de múltiples hojas y es
#   directamente auditable por el equipo de investigación sin
#   herramientas adicionales.
"""

import pandas as pd


def cargar_base(ruta_archivo: str, nombre_hoja) -> pd.DataFrame:
    """
    Carga la base de notas periodísticas desde un archivo Excel.

    Parámetros
    ----------
    ruta_archivo : str
        Ruta al archivo .xlsx (local o de Google Drive montado en Colab).
    nombre_hoja : str | int
        Nombre exacto de la hoja a leer, o índice (0 = primera hoja).

    Retorna
    -------
    pd.DataFrame
        La base cargada, con columnas normalizadas (sin espacios sobrantes)
        y `Fecha` ya parseada como datetime.
    """
    # Leer el archivo Excel con pandas (motor openpyxl por defecto para .xlsx)
    df = pd.read_excel(ruta_archivo, sheet_name=nombre_hoja)

    # Limpiar espacios sobrantes al principio/final de los nombres de columna
    # (evita errores de tipo "columna no encontrada" por diferencias invisibles)
    df.columns = df.columns.str.strip()

    # Parsear la columna Fecha como datetime; dayfirst=True porque el
    # formato de origen es día/mes/año (estándar argentino), no mes/día/año.
    # errors="coerce" convierte fechas mal formateadas en NaT en vez de
    # interrumpir la carga completa.
    df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")

    return df


def montar_drive():
    """
    Monta Google Drive en el entorno de Colab. Solo aplica si el script
    corre dentro de Google Colab; en un entorno local no hace nada.
    """
    try:
        from google.colab import drive  # import local: solo existe en Colab
        drive.mount("/content/drive")
    except ImportError:
        # Si no estamos en Colab, no hay Drive que montar; se asume que
        # ruta_archivo ya apunta a una ruta local accesible.
        print("No se detectó entorno de Colab; se omite el montaje de Drive.")


if __name__ == "__main__":
    # Ejemplo de uso standalone (ajustar ruta y hoja antes de correr)
    montar_drive()
    RUTA_ARCHIVO = "/content/drive/MyDrive/Colab Notebooks/base_2022_2026.xlsx"
    NOMBRE_HOJA = "Base"
    df = cargar_base(RUTA_ARCHIVO, NOMBRE_HOJA)
    df.info()
    print(df.head())
