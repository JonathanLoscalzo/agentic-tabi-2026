#!/usr/bin/env bash
# Chequea herramientas y estado del proyecto. `doctor.sh pre` = solo lo necesario antes de `make setup`.
cd "$(dirname "$0")/.." || exit 1
fail=0
ok()   { printf "  ✓ %s\n" "$1"; }
bad()  { printf "  ✗ %s\n      → %s\n" "$1" "$2"; fail=1; }
warn() { printf "  ! %s\n      → %s\n" "$1" "$2"; }

echo "Herramientas"
command -v uv >/dev/null \
  && ok "uv $(uv --version | cut -d' ' -f2)" \
  || bad "uv no está instalado" "brew install uv   (o: curl -LsSf https://astral.sh/uv/install.sh | sh)"

if command -v ollama >/dev/null; then
  ok "ollama instalado"
  curl -sf http://localhost:11434 >/dev/null \
    && ok "servidor de Ollama respondiendo" \
    || bad "el servidor de Ollama no responde" "abrí la app de Ollama o corré: ollama serve"
else
  bad "ollama no está instalado" "brew install ollama   (o https://ollama.com/download)"
fi

if command -v docker >/dev/null && docker info >/dev/null 2>&1; then
  ok "docker corriendo"
else
  warn "docker no disponible (solo hace falta para la técnica multi: make up)" "instalá/abrí Docker o Rancher Desktop"
fi

[ "$1" = "pre" ] && exit $fail

echo "Configuración"
if curl -sf http://localhost:11434 >/dev/null; then
  ollama list 2>/dev/null | awk 'NR>1{print $1}' | grep -q '^embeddinggemma' \
    && ok "modelo embeddinggemma descargado" \
    || bad "falta el modelo embeddinggemma" "make setup   (o: ollama pull embeddinggemma)"
fi
key=$(grep -E '^OPENROUTER_API_KEY=' .env 2>/dev/null | cut -d= -f2-)
key=${key:-$OPENROUTER_API_KEY}
if [ "${#key}" -gt 8 ] && [ "$key" != "sk-or-" ]; then ok "OPENROUTER_API_KEY configurada"
else bad "falta OPENROUTER_API_KEY" "completala en .env (make setup crea .env desde .env.example)"; fi
[ -d .venv ] && ok "dependencias instaladas (.venv)" || warn "no hay .venv" "make setup"

echo "Datos"
ls data/*.pdf >/dev/null 2>&1 && ok "PDFs en data/" || warn "no hay PDFs en data/" "make data"
[ -d chroma_db ] && ok "índice de Chroma creado" || warn "no hay índice" "make index"
curl -sf "http://localhost:8080" >/dev/null 2>&1 && ok "SearXNG respondiendo" || warn "SearXNG apagado (solo para multi)" "make up"

[ $fail -eq 0 ] && echo "Todo listo." || echo "Hay problemas por resolver (✗)."
exit $fail
