# agentic-tabi-2026

Preguntas sobre los libros de TABI con distintas técnicas, usando **Strands Agents** y modelos de **OpenRouter**.
Embeddings con Ollama (`embeddinggemma`) y Chroma, igual que en los repos anteriores.

| Técnica | Qué hace |
|---|---|
| `no_context` | El LLM solo, sin documentos (línea base) |
| `bm25` | RAG con búsqueda léxica |
| `vector` | RAG con Chroma (embeddings) |
| `ensemble` | BM25 + vectorial 50/50 fusionados con RRF |
| `agent` | Un agente Strands que decide cuándo llamar a `search_docs` |
| `multi` | Orquestador: clasificador → agente de docs → agente web (SearXNG) → resumen |

## Setup

```bash
cp .env.example .env          # completar OPENROUTER_API_KEY
ollama pull embeddinggemma
docker compose up -d          # solo para la técnica `multi` (búsqueda web con SearXNG)
uv sync                       # Python 3.14
uv run tabi index             # arma Chroma desde data/*.pdf
```

## Uso

```bash
uv run tabi ask "¿Quién es Ralph Kimball?"                              # todas las técnicas
uv run tabi ask "¿Qué es una dimensión?" -t ensemble --show-context    # muestra chunks y prompt armado
```

## Evals (Strands Evals)

```bash
uv run python evals/run.py            # compara todas las técnicas
uv run python evals/run.py -t bm25 -t vector
```

## Slides

Abrir `slides/index.html` en el navegador.

## Estructura

- `src/tabi/` — config, indexado, técnicas y CLI
- `evals/` — dataset y corrida de evaluación
- `slides/` — presentación
- `data/` — PDFs (Kimball, Díaz)
