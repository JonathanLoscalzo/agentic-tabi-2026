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

Explicación detallada de cada técnica: [`docs/tecnicas.md`](docs/tecnicas.md) (también en la pestaña **📖 Técnicas** del chat).

## Setup

```bash
make setup      # uv sync + ollama pull embeddinggemma + crea .env (completar OPENROUTER_API_KEY)
make up         # SearXNG en docker (búsqueda web para `multi`)
make index      # arma Chroma desde data/*.pdf   (make reindex para rehacerlo)
```

Python 3.14. Todos los targets están en el `Makefile`.

## Uso

```bash
make chat                                          # cliente Streamlit: modelo, técnicas, contexto e índice
make ask Q="¿Qué es una dimensión?" T=ensemble     # una técnica (T=all para todas)
make ask Q="..." T=agent M=openai/gpt-5-mini       # con otro modelo de OpenRouter
make models F=claude                               # lista/filtra los modelos disponibles
```

El modelo se elige con `M=<slug de OpenRouter>`, con `-m` en la CLI, o desde el selector del chat.
Por defecto: `TABI_LLM` en `.env`.

## Evals (Strands Evals)

```bash
make eval                      # todas las técnicas con el modelo por defecto
make eval M=openai/gpt-5-mini  # evalúa otro modelo (el juez es siempre TABI_JUDGE_LLM)
```

Resultados en `evals/results/<modelo>__<técnica>.json`.

## Slides

Abrir `slides/index.html` en el navegador.

## Estructura

- `src/tabi/` — config, indexado, técnicas y CLI
- `evals/` — dataset y corrida de evaluación
- `slides/` — presentación
- `data/` — PDFs (Kimball, Díaz)
