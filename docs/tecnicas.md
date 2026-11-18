# Técnicas de TABI QA

Todas responden la misma pregunta sobre los libros de `data/`. Cambia **cómo se arma el contexto** y **quién decide qué buscar**. Todas comparten la firma `ask(pregunta) -> Result(answer, contexts, prompt, tools)` en `src/tabi/techniques.py`.

## Base común: indexado y contexto

> PDF → chunks de 1000 caracteres con solapamiento de 200 → embeddings (Ollama `embeddinggemma`) en Chroma, más un índice BM25 en memoria.

- **Indexado** (`src/tabi/index.py`): cada PDF se lee página por página y cada página se corta en chunks.
- **Chunking**: hasta 1000 caracteres por chunk, avanzando de a 800, así que los últimos 200 caracteres se repiten en el chunk siguiente (solape) y una idea cortada en el borde no se pierde. Un chunk nunca cruza páginas, y cada uno guarda archivo y página para poder citar. El corte es por caracteres, no por oraciones, y el final de cada página puede dar chunks muy cortos. Con los dos PDFs locales salen 441 chunks (largo medio 768). Chunks más chicos buscan con más precisión pero dan menos contexto; más grandes, al revés.
- **Embeddings y Chroma**: `embeddinggemma` (Ollama, local) convierte cada chunk en un vector de 768 números que representa su significado. Se calculan en lotes de 50 y se guardan en Chroma (`chroma_db/`, distancia coseno) junto con el texto y archivo/página. Cada chunk se guarda con un id que es su posición en la lista de chunks. Si la colección ya tiene datos, `make index` no hace nada. Al preguntar, la pregunta se convierte en vector con el mismo modelo y Chroma devuelve los chunks más cercanos.
- **Reindexar cuando cambian los PDFs**: como `make index` salta si ya hay datos, no detecta PDFs nuevos, quitados o reemplazados. Después de cualquier cambio en `data/` corré `make reindex`. Si no, Chroma sigue con los ids y textos viejos mientras BM25, que se arma en cada arranque leyendo los PDFs actuales, usa los nuevos: el `ensemble` puede fusionar como si fueran el mismo chunk dos que no lo son.
- **BM25**: no usa Chroma ni embeddings. Se arma en memoria cada vez que arranca, leyendo los PDFs y cortando los mismos chunks. Tokeniza en minúsculas con `\w+`, sin stemming ni stopwords ("dimensión" y "dimensiones" son palabras distintas), y usa los parámetros por defecto de `rank-bm25` (`k1=1.5`, `b=0.75`). Cada palabra de la pregunta suma un peso, mayor si es rara en el corpus, si aparece varias veces en el chunk (con rendimientos decrecientes) y si el chunk es corto.
- **Armado del contexto**: los `K=4` mejores chunks se numeran y se pegan en un prompt (`RAG_PROMPT`). El prompt le pide al modelo responder **solo** con ese contexto, en máximo tres oraciones, y citar `(archivo, p. N)`.
- **Modelos**: los LLM se llaman por OpenRouter a través de Strands (`OpenAIModel` con `base_url` de OpenRouter). Se elige con `TABI_LLM`, `-m` o el selector del chat.

## no_context — Sin contexto

> El LLM responde solo con lo que recuerda: es la línea base.

- **Cómo funciona**: la pregunta va directo al modelo, sin recuperar nada.
- **Fortaleza**: rápida y barata.
- **Debilidad**: no cita fuentes y puede inventar datos del libro.
- **Para qué sirve**: medir cuánto aportan las demás técnicas.

## Ejemplo real: qué devuelve cada búsqueda

Pregunta: «¿Quién es Ralph Kimball?», con los dos PDFs indexados (441 chunks).

**Chroma** (distancia coseno: menor es más cercano):

| # | id | distancia | fuente | empieza con |
|---|---|---:|---|---|
| 1 | 123 | 0.663 | Díaz p. 45 | "45 CAPÍTULO 3 Arquitectura del Data Warehouse Ralph Kimball propone el Data Warehouse…" |
| 2 | 125 | 0.667 | Díaz p. 45 | "o- puestas en algún momento confluyen y más allá de cuales es mejor…" |
| 3 | 408 | 0.709 | Kimball p. 1 | "http://www.kimballgroup.com/1997/08/a-dimensional-modeling-manifesto/ By Ralph Kimball…" |
| 4 | 227 | 0.719 | Díaz p. 78 | "do." (un chunk de 3 caracteres: el corte por caracteres deja restos) |

**BM25** (puntaje; las columnas son cuántas veces aparece cada palabra de la pregunta en el chunk):

| # | id | puntaje | quién | es | ralph | kimball | largo | fuente |
|---|---|---:|---:|---:|---:|---:|---:|---|
| 1 | 125 | 11.09 | 0 | 3 | 1 | 1 | 511 | Díaz p. 45 |
| 2 | 123 | 10.93 | 0 | 1 | 2 | 2 | 1000 | Díaz p. 45 |
| 3 | 85 | 9.03 | 0 | 5 | 1 | 1 | 1000 | Díaz p. 32 |
| 4 | 41 | 7.13 | 1 | 2 | 0 | 0 | 712 | Díaz p. 14 |

- El #1 le gana al #2 aunque menciona menos a Kimball: es más corto (511 contra 1000 caracteres) y BM25 normaliza por largo.
- El #4 no habla de Kimball: entró por «quién» y «es», porque no se quitan stopwords.

**Fusión del ensemble** (RRF, posición 0-based, peso 0.5 por lista; ids de arriba):

| id | rango BM25 | rango Chroma | puntaje RRF |
|---|---:|---:|---:|
| 125 | 1 | 2 | 0.5/60 + 0.5/61 = 0.01653 |
| 123 | 2 | 1 | 0.5/61 + 0.5/60 = 0.01653 |
| 408 | 5 | 3 | 0.5/64 + 0.5/62 = 0.01588 |
| 315 | 8 | 6 | 0.5/67 + 0.5/65 = 0.01515 |

Los chunks 123 y 125 aparecen en ambas listas, así que suben. El 85 y el 41 (solo BM25) y el 227 (solo Chroma) quedan afuera de los 4 primeros.

## bm25 — Búsqueda léxica

> Recupera los chunks que comparten palabras con la pregunta, ponderando las palabras raras.

- **Cómo funciona**: BM25 puntúa cada chunk según qué tan seguido aparecen los términos de la pregunta y qué tan poco comunes son en el corpus. No usa embeddings.
- **Fortaleza**: excelente con nombres propios, siglas y términos exactos ("Kimball", "ETL").
- **Debilidad**: no entiende sinónimos ni paráfrasis.
- **Contexto**: los 4 chunks con mayor puntaje, armados con `RAG_PROMPT`.

## vector — Búsqueda semántica

> Recupera los chunks cuyo significado es más cercano al de la pregunta, usando embeddings en Chroma.

- **Cómo funciona**: la pregunta se convierte en un vector con `embeddinggemma` y Chroma devuelve los chunks más cercanos por distancia coseno.
- **Fortaleza**: encuentra pasajes que dicen lo mismo con otras palabras.
- **Debilidad**: puede fallar con términos raros o muy específicos.
- **Contexto**: los 4 chunks más cercanos, armados con `RAG_PROMPT`.

## ensemble — BM25 + vectorial

> Combina las dos búsquedas anteriores con pesos 50/50 y se queda con lo mejor de ambas.

- **Cómo funciona**: se piden 8 resultados a BM25 y 8 a Chroma, y se fusionan con **Reciprocal Rank Fusion** ponderado: cada chunk suma `peso / (60 + posición)` por cada lista donde aparece. Se toman los 4 mejores.
- **Fortaleza**: cubre términos exactos y significado. Es un buen default.
- **Debilidad**: dos índices para mantener y un parámetro más (el peso).
- **Origen**: es el mismo 50/50 del repo `tabi-rag-2024`.

## agent — Agente con herramienta

> Un agente de Strands decide cuándo y con qué consulta llamar a `search_docs`.

- **Cómo funciona**: el modelo recibe la pregunta y una tool `search_docs`, que ejecuta la búsqueda ensemble. Puede reformular la consulta, buscar varias veces y recién después responder.
- **Fortaleza**: maneja preguntas compuestas, porque busca por partes.
- **Debilidad**: más latencia y costo, ya que son varias llamadas al modelo.
- **Contexto**: lo arma el agente. El chat muestra las consultas que eligió hacer y los chunks que recuperó.
- **Diferencia con `ensemble`**: el ensemble es un pipeline fijo (busca **una vez con tu pregunta tal cual** y responde en una sola llamada al modelo). El agente usa ese mismo ensemble como herramienta, pero **decide él** con qué texto buscar, cuántas veces y cuándo parar. Ejemplo: ante "¿En qué se diferencian Kimball e Inmon?", el ensemble hace una sola búsqueda con esa frase; el agente puede buscar "Kimball data marts" e "Inmon data warehouse" por separado. En preguntas simples el resultado es casi igual y el agente cuesta más.

## multi — Multi-agente

> Un orquestador coordina un clasificador, un agente de documentos, un agente web y el resumen final.

- **Cómo funciona** (patrón *agents as tools* de Strands):
  1. `classify_relevance`: decide si la pregunta trata de modelo dimensional, open source, datos o machine learning. Si no, el orquestador rechaza la pregunta y termina.
  2. `docs_agent`: busca en los libros con `search_docs`.
  3. `web_agent`: si los libros no alcanzan, busca en la web con SearXNG (`make up`).
  4. El orquestador resume en máximo 4 oraciones, citando fuentes.
- **Fortaleza**: filtra preguntas fuera de tema y complementa con la web.
- **Debilidad**: más piezas que pueden fallar, y más costo.

## Cómo compararlas: Strands Evals

> Los mismos casos pasan por cada técnica y un modelo juez puntúa las respuestas.

- **Dataset** (`evals/dataset.py`): 12 preguntas con respuesta esperada, dos de ellas fuera de tema.
- **Evaluadores** (`evals/run.py`): `OutputEvaluator` (un LLM juez puntúa la correctitud, de 0 a 1) para todas las técnicas, y `ToolCalled` para `agent` (`search_docs`) y `multi` (`classify_relevance`).
- **Uso**: `make eval` o `make eval M=<modelo>`. Los resultados quedan en `evals/results/`.

## ¿Cuál uso?

| Técnica | Fortaleza | Debilidad | Cuándo |
|---|---|---|---|
| `no_context` | Rápida, barata | Inventa, sin fuente | Línea base |
| `bm25` | Términos exactos, nombres | No entiende sinónimos | Siglas, autores |
| `vector` | Significado | Falla con términos raros | Preguntas conceptuales |
| `ensemble` | Combina ambas | Dos índices | Default razonable |
| `agent` | Decide qué buscar, reformula y repite | Más latencia y costo | Preguntas compuestas |
| `multi` | Filtra y usa la web | Más piezas que fallan | Dominio abierto |
