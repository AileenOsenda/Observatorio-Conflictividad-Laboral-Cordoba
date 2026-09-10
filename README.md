# Observatorio de Conflictividad Laboral — Módulos independientes

Este repositorio divide el notebook original en **9 módulos independientes
pero correlacionados**, más un orquestador (`main.py`) que los ejecuta en
el orden correcto. Pensado para subir a GitHub como conjunto de scripts
reutilizables, no como notebook monolítico.

## Corrección aplicada

En el notebook original, la celda de **reporte de incidencias** (Fase 2.2)
podía ejecutarse antes que la celda de **limpieza del corpus** (Fase 2.3),
lo que producía `NameError: name 'df_limpio' is not defined` si se corría
en el orden numerado tal cual. En esta versión:

- El módulo `04_reporte_incidencias.py` **solo define la función** — ya no
  se auto-ejecuta al importarse.
- `main.py` fuerza el orden correcto por construcción: `02_limpieza_corpus`
  corre primero, y recién después se llama a `04_reporte_incidencias` con
  el resultado ya calculado.
- De paso, `05_resumen_ejecutivo.py` dejó de volver a llamar a
  `limpiar_corpus()` por su cuenta (antes se ejecutaba dos veces sobre el
  mismo corpus) — ahora reutiliza el `resultado` que ya generó el paso 2.

## Estructura de módulos

| Archivo | Fase | Contenido |
|---|---|---|
| `01_carga_datos.py` | 1 | Carga del Excel, montaje de Drive, parseo de fechas |
| `02_limpieza_corpus.py` | 2 | Excepciones (falsos positivos) + duplicados semánticos (Jaccard) |
| `03_test_calidad.py` | 2.1 | Comparación de métricas pre/post limpieza |
| `04_reporte_incidencias.py` | 2.2 | Genera el `.xlsx` con todas las incidencias detectadas |
| `05_resumen_ejecutivo.py` | 2.4 | Cuadro resumen de impacto de la limpieza |
| `06_analisis_descriptivos.py` | 3 | Frecuencias, heatmap, nube de palabras (opcional) |
| `07_analisis_avanzados.py` | 4 | Evolución temporal, picos, comparación de períodos (opcional) |
| `08_perfil_editorial_redes.py` | 5 | Perfil por diario, red de co-ocurrencia, Shannon, organizaciones (opcional) |
| `09_motor_grafico.py` | 6 | Motor gráfico unificado con menú interactivo de 19 opciones |
| `main.py` | — | Orquestador: ejecuta todo en el orden correcto |

## Cómo correrlo

```bash
pip install -r requirements.txt
python main.py
```

Ajustar `RUTA_ARCHIVO` y `NOMBRE_HOJA` en `main.py` antes de correr. Las
Fases 3-5 (análisis opcionales) y la Fase 6 (motor gráfico interactivo)
están desactivadas por defecto — activarlas con
`correr_analisis_opcionales=True` y `correr_motor_grafico=True` en la
llamada a `ejecutar_pipeline()`.

## Nota técnica sobre los imports

Los archivos usan prefijo numérico (`01_`, `02_`, etc.) para indicar el
orden de lectura/ejecución en GitHub, lo cual **no es un nombre de módulo
Python válido** para `import 02_limpieza_corpus`. Por eso `main.py` y
`09_motor_grafico.py` usan `importlib.import_module("02_limpieza_corpus")`
en vez de `import` directo. Si se prefiere usar `import` estándar, renombrar
los archivos sin el prefijo numérico (ej. `limpieza_corpus.py`) y ajustar
las llamadas a `importlib` en consecuencia.

## Dependencias

Ver `requirements.txt`. Se ejecuta también correctamente fuera de Colab
(`montar_drive()` detecta el entorno y no falla si no está disponible
`google.colab`; `descargar_reporte()` hace lo mismo con `files.download`).
