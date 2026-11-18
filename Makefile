.PHONY: setup up down index reindex chat ask models eval slides
Q ?= ¿Quién es Ralph Kimball?
T ?= all
M ?=
MODEL = $(if $(M),-m $(M),)

setup:        ## deps + modelo de embeddings + .env
	uv sync
	ollama pull embeddinggemma
	@test -f .env || cp .env.example .env
up:           ## SearXNG (búsqueda web para `multi`)
	docker compose up -d
down:
	docker compose down
index:        ## indexa data/*.pdf en Chroma
	uv run tabi index
reindex:
	uv run tabi index --rebuild
chat:         ## cliente de chat (Streamlit)
	uv run tabi chat
ask:          ## make ask Q="..." T=ensemble M=openai/gpt-5-mini --show-context
	uv run tabi ask "$(Q)" -t $(T) $(MODEL) --show-context
models:       ## make models F=claude
	uv run tabi models $(F)
eval:         ## make eval M=openai/gpt-5-mini
	uv run python evals/run.py $(MODEL)
slides:
	open slides/index.html
