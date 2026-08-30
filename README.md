# Observatorio-Conflictividad-Laboral-Córdoba
Desarrolo de análisis de datos para la Red de Observatorios de Conflictividad Laboral nodo Córdoba


#Documentación
# 📰 Observatorio de Conflictividad Laboral en Córdoba
### Documentación técnica del notebook `observatorio_conflictividad_laboral_final.ipynb`

> **Herramientas:** Python · Pandas · Matplotlib · Seaborn · NetworkX · openpyxl · Google Colab
> **Corpus:** Base de notas periodísticas codificadas de diarios de Córdoba
> **Última actualización:** Agosto 2026

---

## Índice

- [1. Estructura general del notebook](#1-estructura-general-del-notebook)
- [2. Esquema de columnas de la base](#2-esquema-de-columnas-de-la-base)
- [Fase 0 — Instalación de dependencias](#fase-0--instalación-de-dependencias)
- [Fase 1 — Carga de datos](#fase-1--carga-de-datos)
- [Fase 2 — Control de calidad del corpus](#fase-2--control-de-calidad-del-corpus)
  - [2.1 Test de calidad pre/post limpieza](#21-test-de-calidad--comparación-pre--post-limpieza)
  - [2.2 Reporte de incidencias (Excel)](#22-reporte-de-incidencias-falsos-positivos-duplicados-e-inconsistencias)
  - [2.3 Ejecución de la limpieza](#23-ejecución-de-limpieza)
  - [2.4 Resumen ejecutivo de impacto](#24-resumen-ejecutivo-volumen-inicial-final-tasa-de-retención-y-advertencias)
- [Fase 3 — Análisis descriptivos simples](#fase-3--análisis-descriptivos-simples)
- [Fase 4 — Análisis avanzados](#fase-4--análisis-avanzados)
- [Fase 5 — Perfil editorial, actores y diversidad temática](#fase-5--perfil-editorial-actores-y-diversidad-temática)
- [Fase 6 — Motor gráfico unificado y parametrizable](#fase-6--motor-gráfico-unificado-y-parametrizable)
  - [6.1 Ejecutar el menú interactivo](#61-ejecutar-el-menú-interactivo)
- [Advertencias de orden de ejecución](#⚠️-advertencias-de-orden-de-ejecución)
- [Referencias metodológicas](#referencias-metodológicas)

---

## 1. Estructura general del notebook

El notebook se organiza en seis fases numeradas (0 a 6), con sub-secciones dentro de la Fase 2 para separar diagnóstico, reporte y ejecución de la limpieza del corpus.

```
┌──────────────────────────────────────────────────────────────────┐
│  Fase 0   — Instalación                Dependencias externas     │
│  Fase 1   — Carga de datos              Excel desde Google Drive │
│  Fase 2   — Control de calidad          2.1 → 2.2 → 2.3 → 2.4    │
│  Fase 3   — Análisis descriptivos       Frecuencias, heatmap...  │
│  Fase 4   — Análisis avanzados          Picos, períodos, evol.   │
│  Fase 5   — Perfil editorial y redes    Shannon, co-ocurrencia   │
│  Fase 6   — Motor gráfico unificado     6 → 6.1 (menú interact.) │
└──────────────────────────────────────────────────────────────────┘
```

Como indica la celda de título del propio notebook: las secciones 3, 4 y 5 (análisis descriptivos y avanzados) **no son obligatorias de correr** — son exploratorias y pueden omitirse si el objetivo es ir directo al motor gráfico (Fase 6). La Fase 2, en cambio, sí es un prerrequisito estricto para todo lo demás, porque genera `df_limpio`, el DataFrame sobre el que operan absolutamente todas las fases posteriores.

---

## 2. Esquema de columnas de la base

| Columna | Tipo | Descripción |
|---|---|---|
| `Link` | `str` | URL de la nota original |
| `Palabras` | `str` | Palabra(s) clave que motivó la inclusión de la nota en el corpus |
| `Título` | `str` | Titular de la noticia (unidad de análisis) |
| `Contenido` | `str` | Cuerpo de la nota (cuando está disponible) |
| `Fecha` | `datetime` | Fecha de publicación |
| `Mes` / `Año` | `str` / `int` | Mes y año derivados de `Fecha` |
| `Diario` | `str` | Medio que publicó la nota |
| `Pertenencia Sectorial` | `str` | Público / Privado / Mixto / Multisectorial / etc. |
| `Código DC` / `Dinámica Conflictual` | `str` | Clasificación temática del conflicto |
| `Sector` / `Sub sector` | `str` | Rama de actividad económica |
| `Organización detallada` / `Organización Agregada` | `str` | Actor(es) laboral(es) mencionados |
| `Departamento` | `str` | Departamento de la provincia donde ocurre el hecho |
| `Antagonista` / `Actor Estatal` / `Nivel de Gobierno` | `str` | Contraparte del conflicto |
| `Iniciativa Estado` / `Resp. Estado` | `str` | Rol del Estado en el conflicto |
| `Participación` | `str` | Nivel de involucramiento de lxs trabajadorxs |
| `Demanda princ. Abierta` / `Demanda principal agrupada` | `str` | Reclamo central de la acción |
| `Formato principal` / `Formato agregado` / `Tipo Formato AC` | `str` | Tipo de acción (directa/indirecta, paro, movilización, etc.) |

---

## Fase 0 — Instalación de dependencias

**Descripción.** Instala `networkx` y `wordcloud` vía `!pip install`, las únicas librerías del proyecto no incluidas por defecto en el entorno de Colab.

**Uso.** Se ejecuta una sola vez por sesión; debe repetirse si se reinicia el entorno de ejecución.

**Interpretación.** No produce salida analítica. Un fallo de instalación bloqueará la celda de red de co-ocurrencia (Fase 5) y la nube de palabras (Fase 3).

**Justificación.** Explicitar dependencias en una celda separada es una práctica estándar de reproducibilidad: permite a cualquier colaborador replicar el entorno sin conocimiento previo del proyecto.

---

## Fase 1 — Carga de datos

**Descripción.** Monta Google Drive, importa todas las librerías del proyecto (`pandas`, `numpy`, `matplotlib`, `seaborn`, `networkx`, `wordcloud`), lee el archivo Excel definido en `RUTA_ARCHIVO` y `NOMBRE_HOJA`, limpia espacios sobrantes en los nombres de columna, y parsea `Fecha` a `datetime` con `dayfirst=True`.

**Uso.** Es la celda de entrada obligatoria. Los parámetros configurables al inicio de la celda son:

```python
RUTA_ARCHIVO = '/content/drive/MyDrive/Colab Notebooks/base_2022_2026.xlsx'
NOMBRE_HOJA  = 'Base'
```

Deben ajustarse según la ubicación real del archivo y el nombre exacto de la hoja a usar.

**Interpretación.** `df.info()` y `df.head()` confirman que la carga fue exitosa: que `Fecha` quedó tipada como `datetime64` y que las columnas coinciden con el esquema esperado. Si el nombre de hoja es incorrecto, esta celda arrojará `ValueError: Worksheet named '...' not found`.

**Justificación.** El formato `.xlsx` preserva estructura de múltiples hojas (útil si la base separa datos por año o tipo de análisis) y es directamente auditable por el equipo de investigación.

---

## Fase 2 — Control de calidad del corpus

Define las estructuras y funciones necesarias para limpiar el corpus: el diccionario `EXCEPCIONES` (patrones regex agrupados que detectan falsos positivos por ambigüedad léxica, ej. "corte de luz" vs. "corte de ruta"), la función `es_falso_positivo()`, y el mecanismo de detección de duplicados semánticos entre fuentes (`tokens()`, `similitud_jaccard()`, `detectar_duplicados_entre_fuentes()`), que compara títulos publicados por distintos diarios en una ventana de ±1 día. Todo se integra en `limpiar_corpus(df, umbral_similitud=0.6)`.

**Uso.** Esta celda solo define funciones — no ejecuta la limpieza todavía (eso ocurre recién en la sub-sección 2.3). Debe correrse antes que cualquier sub-sección posterior de la Fase 2.

**Justificación.** A diferencia de un corpus generado por scraping (donde el filtro de ingreso es un regex sobre texto libre), esta base ya fue codificada manualmente. El control de calidad aquí audita la consistencia del corpus codificado — duplicados, fechas, columnas vacías — más que filtrar contenido no laboral.

---

### 2.1 Test de calidad — comparación pre / post limpieza

**Descripción.** Define `test_calidad_corpus(df_original, df_limpio)`, que compara ambos DataFrames en: total de registros, filas 100% duplicadas, links duplicados, títulos duplicados exactos, valores faltantes por columna clave, fechas no parseables (NaT), fechas fuera del rango 2012-2026, inconsistencias entre `Año` y el año real de `Fecha`, links con formato inválido (que no arrancan con `http`), y celdas vacías o con placeholder (`"sin datos"`, `"s/d"`, etc.) en `Dinámica Conflictual`.

**Uso.** Solo define la función; se **ejecuta recién en la sub-sección 2.3**, después de correr `limpiar_corpus()`, porque necesita `df_limpio` como insumo.

**Interpretación.** La tabla resultante permite cuantificar exactamente qué mejoró (y en qué magnitud) tras la limpieza — útil para justificar metodológicamente el proceso de depuración en un informe de investigación.

---

### 2.2 Reporte de incidencias (falsos positivos, duplicados e inconsistencias)

**Descripción.** Define `generar_reporte_incidencias(df_original, df_limpio, df_falsos, df_duplicados)`, que compila en un único archivo `.xlsx` (con una hoja por tipo de problema) todos los registros marcados como incidencia: falsos positivos, duplicados semánticos entre fuentes, duplicados exactos de fila completa, duplicados por `Título`+`Diario`+`Fecha`, fechas inválidas, fechas fuera de rango, inconsistencias `Año`≠`Fecha`, links inválidos, y `Dinámica Conflictual` vacía/placeholder. Incluye una hoja `Resumen` con cantidad y porcentaje de casos por categoría. El Excel se formatea automáticamente (encabezados en negrita, ancho de columna ajustado, fila superior congelada) y se descarga al finalizar con `files.download()`.

**Uso.** Al final de la celda se **ejecuta directamente** (`hojas_incidencias = generar_reporte_incidencias(df, df_limpio, df_falsos, df_duplicados)`), lo que requiere que `df_limpio`, `df_falsos` y `df_duplicados` ya existan.

> ⚠️ **Ver la nota de orden de ejecución al final de este documento** — en la numeración actual del notebook, esta celda (2.2) aparece *antes* que la celda que genera esas variables (2.3), lo que puede causar un `NameError` si se corre en el orden numerado tal cual.

**Interpretación.** Cada fila del reporte incluye `id` (índice original en la base), `posición` (número de fila, 1-indexado), `Título`, `Link`, `Diario`, `Fecha` y el dato específico de la incidencia — pensado para que el equipo de investigación pueda revisar manualmente cada caso marcado sin tener que volver al notebook.

---

### 2.3 Ejecución de limpieza

**Descripción.** Corre efectivamente el pipeline de limpieza: `limpiar_corpus(df, umbral_similitud=0.6)`, seguido de `test_calidad_corpus(df, df_limpio)`. Genera las variables centrales que usa el resto del notebook: `df_limpio`, `df_falsos`, `df_duplicados`, `tabla_resumen`, `tabla_faltantes`.

**Uso.** Es el punto donde efectivamente se materializa `df_limpio`. Todas las fases posteriores (3 a 6) dependen de esta celda.

**Interpretación.** El log impreso por `limpiar_corpus()` indica cuántos falsos positivos se descartaron y por qué excepción, y cuántos pares de duplicados semánticos se detectaron (estos últimos **no se eliminan automáticamente** del corpus).

---

### 2.4 Resumen ejecutivo (volumen inicial, final, tasa de retención y advertencias)

**Descripción.** Define y ejecuta `generar_resumen_ejecutivo(df_original, resultado_limpieza)`, que imprime un cuadro compacto con: volumen inicial y final del corpus, tasa de retención (%), total de notas descartadas desglosado en duplicados vs. falsos positivos temáticos, y advertencias sobre pares semánticos sospechosos aún no eliminados.

**Uso.** Vuelve a llamar internamente a `limpiar_corpus(df, umbral_similitud=0.6)` para obtener `resultado_limpieza` — es decir, **la limpieza se ejecuta dos veces** en el notebook tal como está estructurado (una vez en 2.3 y otra vez dentro de 2.4).

> ⚠️ Ver nota de orden de ejecución al final del documento.

**Interpretación.** El desglose "duplicados vs. falsos positivos" se calcula por resta (`total_removidos - falsos_positivos_removidos`), asumiendo que toda la diferencia corresponde a duplicados de `Título`/`Link`. Esto es una aproximación: si en el futuro se agregan otros criterios de descarte al pipeline de `limpiar_corpus()`, este cálculo debería revisarse para que el desglose siga siendo exacto.

**Justificación.** Un resumen de alto nivel, con formato de tabla legible, es el tipo de salida que se puede pegar directamente en un informe metodológico o compartir con el equipo sin necesidad de interpretar tablas de pandas.

---

## Fase 3 — Análisis descriptivos simples

**Descripción.** Ocho celdas de exploración básica sobre `df_limpio`: vista general (`info()`/`head()`), frecuencia por `Diario`, frecuencia por `Dinámica Conflictual` con tabla cruzada Diario × Dinámica (top 10), evolución temporal simple por fecha, gráficos de barras (top 15 dinámicas + notas por diario), serie temporal en línea, heatmap Diario × Dinámica, nube de palabras extraída de `Título`, y resumen ejecutivo del corpus (total de notas, diarios, dinámicas distintas, departamentos, rango de fechas, dinámica y diario dominantes).

**Uso.** No requiere parámetros; opera directamente sobre `df_limpio`. Marcada como no obligatoria en la celda de título del notebook — es exploratoria.

**Interpretación.** Sirve como línea de base antes de cualquier análisis comparativo: una distribución muy desigual entre diarios indica que los análisis posteriores deben normalizarse por proporción, no por valor absoluto.

---

## Fase 4 — Análisis avanzados

**Descripción.** Cinco análisis temporales: (1) evolución de notas por día/semana/mes con media móvil de 7 días y composición mensual por dinámica conflictual (área apilada, top 8); (2) comparación de métricas entre dos períodos definidos por `FECHA_CORTE`; (3) detección de picos de conflictividad (`UMBRAL_SIGMA`, por defecto 1.5σ); (4) evolución mensual de las 8 organizaciones más mencionadas, con heatmap organización × mes; (5) clasificación y evolución de acciones directas vs. indirectas según `Formato agregado`.

**Uso.** Todas las celdas dependen de `df_temp` (generada en la primera celda de esta fase, ordenada por `Fecha`) y de `serie_diaria`/`media_movil_7`. Deben correrse en orden dentro de esta fase.

**Interpretación.** Un pico de conflictividad concentrado en una sola dinámica y un solo diario sugiere un evento sectorial cubierto en profundidad por ese medio; un pico distribuido entre múltiples dinámicas y diarios sugiere un evento de impacto amplio (paro general, medida de política económica).

---

## Fase 5 — Perfil editorial, actores y diversidad temática

**Descripción.** Cuatro análisis: (1) perfil temático por diario (`Dinámica Conflictual` normalizada por fila, top 10 + "Otras", barras apiladas al 100%); (2) red de co-ocurrencia de palabras extraídas de `Título` con NetworkX (umbral configurable, por defecto 3); (3) diversidad temática por diario mediante entropía de Shannon sobre `Dinámica Conflictual`; (4) ranking de las 15 organizaciones más mencionadas (`Organización detallada` por defecto), con conteo de en cuántos diarios distintos aparece cada una.

**Uso.** Opera sobre `df_limpio` directamente; no depende de las celdas de la Fase 4.

**Interpretación.** Un diario con entropía cercana al máximo teórico (`log₂(n_dinámicas)`) cubre todos los tipos de conflicto con frecuencias similares; entropía baja indica cobertura concentrada en pocas dinámicas.

---

## Fase 6 — Motor gráfico unificado y parametrizable

**Descripción.** Sistema de dos capas: la función genérica `graficar()` (construye tablas Período × Categoría y las visualiza como barras apiladas verticales/horizontales, líneas o barras al 100%), y siete funciones especializadas para los análisis que no se reducen a una tabla dinámica simple (`analisis_red_coocurrencia`, `analisis_diversidad_shannon`, `analisis_organizaciones`, `analisis_evolucion_organizaciones`, `analisis_picos`, `analisis_comparacion_periodos`, `analisis_directa_vs_indirecta`). Todo se integra en `menu_graficos()`, un menú interactivo de **19 opciones**.

**Mejoras respecto a versiones anteriores** (documentadas en el propio código, ver comentario inicial de la celda):

1. **`_mostrar_valores_unicos()`**: antes de pedir un filtro por texto libre (ej. "valores separados por coma"), el programa muestra los valores reales presentes en esa columna (hasta 40; si hay más, informa el total y muestra los 40 más frecuentes). Esto evita errores de tipeo por variantes de escritura ("Público" vs. "público" vs. "PUBLICO").
2. **Doble filtro en la opción 19**: el gráfico personalizado ahora admite un segundo filtro opcional además del primero, permitiendo combinaciones como las del gráfico de referencia original (ej. excluir `Formato agregado = "vacía"` **y** excluir `Iniciativa Estado = "ninguna"` en la misma consulta).
3. **Manejo de errores robusto**: `menu_graficos()` captura `ValueError`, `KeyError` y excepciones genéricas al generar un gráfico, imprimiendo un mensaje legible en vez de interrumpir la sesión con un traceback completo.
4. **Funciones auxiliares de validación de input**: `_pedir_columna_valida()` y `_pedir_opcion_valida()` validan las respuestas del usuario en el menú interactivo antes de proceder.

**Uso.** `graficar()` acepta: `col_categoria`, `titulo`, `tipo_grafico` (`apiladas_vertical` / `apiladas_horizontal` / `lineas` / `perfil_100`), `col_filtro`/`modo_filtro`/`valores_filtro`, `granularidad` (`año`/`trimestre`/`mes`), `año_inicio`, `año_fin`, `n_top`, `categorias_fijas`, `tipo_valores` (`absoluto`/`porcentaje`).

**Interpretación.** Cada gráfico generado corresponde a una configuración reproducible de filtro + columna + período — facilita documentar en un informe exactamente qué subconjunto de datos originó cada visualización.

---

### 6.1 Ejecutar el menú interactivo

**Descripción.** Llama a `menu_graficos(df_limpio)`.

**Uso.** Se ejecuta esta celda cada vez que se quiere generar un gráfico nuevo; el sistema pregunta interactivamente por consola qué análisis correr (opciones 1 a 19), la granularidad temporal, el rango de años y, según el análisis elegido, parámetros adicionales.

**Opciones disponibles del menú:**

| # | Análisis | Tipo de gráfico |
|---|---|---|
| 1 | Conflictos laborales según formato agregado | Barras apiladas |
| 2 | Acciones directas según tipo de formato de protesta | Líneas |
| 3 | Acciones directas según pertenencia sectorial | Líneas |
| 4 | Demandas — todos los sectores | Líneas |
| 5 | Demandas — sector público | Líneas |
| 6 | Demandas — sectores no públicos | Líneas |
| 7 | Participación de trabajadorxs — total | Barras horiz. apiladas |
| 8 | Participación — sector público | Barras horiz. apiladas |
| 9 | Participación — sectores no públicos | Barras horiz. apiladas |
| 10 | Top dinámicas conflictuales por período | Barras horiz. apiladas |
| 11 | Perfil temático por diario | Barras apiladas al 100% |
| 12 | Red de co-ocurrencia de palabras en títulos | Red (NetworkX) |
| 13 | Diversidad temática por diario | Entropía de Shannon |
| 14 | Organizaciones más mencionadas | Barras horizontales |
| 15 | Evolución mensual de organizaciones | Líneas + heatmap |
| 16 | Detección de picos de conflictividad | Serie temporal |
| 17 | Comparación entre períodos | Barras comparativas |
| 18 | Acciones directas vs. indirectas en el tiempo | Líneas |
| 19 | Gráfico personalizado (columna, tipo y doble filtro a elección) | Configurable |

---

## ⚠️ Advertencias de orden de ejecución

La numeración de secciones del notebook (2.1 → 2.2 → 2.3 → 2.4) **no coincide exactamente** con el orden real de dependencias entre variables:

- **2.1** (`test_calidad_corpus`) y **2.2** (`generar_reporte_incidencias`) solo *definen* funciones — no ejecutan nada por sí solas, salvo la última línea de 2.2, que **sí llama a `generar_reporte_incidencias(df, df_limpio, df_falsos, df_duplicados)` directamente**.
- Esa llamada requiere `df_limpio`, `df_falsos` y `df_duplicados`, que recién se generan en **2.3** (`limpiar_corpus(df, ...)`).
- Por lo tanto, si se corre el notebook celda por celda en el orden en que aparece numerado, la celda 2.2 fallará con `NameError: name 'df_limpio' is not defined`.

**Solución recomendada:** correr primero la celda 2.3 (ejecución de limpieza) y luego, en cualquier orden, las celdas 2.1, 2.2 y 2.4 — o bien renumerar las celdas del notebook para que 2.3 quede primera dentro de la Fase 2. Alternativamente, comentar la línea de ejecución al final de la celda 2.2 y llamarla manualmente después de correr 2.3.

Adicionalmente, **2.3** y **2.4** ejecutan `limpiar_corpus()` por separado (dos llamadas independientes con el mismo `umbral_similitud=0.6`), lo que duplica el procesamiento sin afectar el resultado final — es redundante pero no incorrecto. Si el corpus es grande, puede convenir que 2.4 reciba `resultado` como parámetro en vez de recalcularlo.

---

## Referencias metodológicas

- Breed, W. (1955). Social control in the newsroom: A functional analysis. *Social Forces*, 33(4), 326–335.
- Knuth, D. E. (1984). Literate programming. *The Computer Journal*, 27(2), 97–111.
- Manning, C. D., & Schütze, H. (1999). *Foundations of Statistical Natural Language Processing*. MIT Press.
- McCombs, M., & Shaw, D. (1972). The agenda-setting function of mass media. *Public Opinion Quarterly*, 36(2), 176–187.
- Neuendorf, K. A. (2017). *The Content Analysis Guidebook* (2nd ed.). SAGE.
- Shannon, C. E. (1948). A mathematical theory of communication. *Bell System Technical Journal*, 27(3), 379–423.
- Tarrow, S. (2011). *Power in Movement: Social Movements and Contentious Politics* (3rd ed.). Cambridge University Press.
- Tukey, J. W. (1977). *Exploratory Data Analysis*. Addison-Wesley.
