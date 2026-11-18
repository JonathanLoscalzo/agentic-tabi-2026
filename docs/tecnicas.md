# Técnicas de TABI QA

Todas responden la misma pregunta sobre los libros de `data/`. Cambia **cómo se arma el contexto** y **quién decide qué buscar**. Todas comparten la firma `ask(pregunta) -> Result(answer, contexts, prompt, tools)` en `src/tabi/techniques.py`.

## Base común: indexado y contexto

> PDF → chunks de 1000 caracteres con solapamiento de 200 → embeddings (Ollama `embeddinggemma`) en Chroma, más un índice BM25 en memoria.

- **Indexado** (`src/tabi/index.py`): cada página de cada PDF se parte en chunks de 1000 caracteres con 200 de solapamiento. Cada chunk guarda archivo y página. Los vectores van a Chroma con distancia coseno (`make index`).
- **Armado del contexto**: los `K=4` mejores chunks se numeran y se pegan en un prompt (`RAG_PROMPT`). El prompt le pide al modelo responder **solo** con ese contexto, en máximo tres oraciones, y citar `(archivo, p. N)`.
- **Modelos**: los LLM se llaman por OpenRouter a través de Strands (`OpenAIModel` con `base_url` de OpenRouter). Se elige con `TABI_LLM`, `-m` o el selector del chat.

## no_context — Sin contexto

> El LLM responde solo con lo que recuerda: es la línea base.

- **Cómo funciona**: la pregunta va directo al modelo, sin recuperar nada.
- **Fortaleza**: rápida y barata.
- **Debilidad**: no cita fuentes y puede inventar datos del libro.
- **Para qué sirve**: medir cuánto aportan las demás técnicas.

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
- **Contexto**: lo arma el agente. El chat muestra qué tools usó.

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
| `agent` | Reformula y repite | Más latencia y costo | Preguntas compuestas |
| `multi` | Filtra y usa la web | Más piezas que fallan | Dominio abierto |
