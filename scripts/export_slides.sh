#!/usr/bin/env bash
# Exporta slides/index.html a PDF (vectorial) y PPTX (una imagen por diapositiva).
# Usa decktape (vía npx) con tu Chrome. En Linux: CHROME=/usr/bin/google-chrome make slides-export
set -euo pipefail
cd "$(dirname "$0")/.."
CHROME=${CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}
OUT=slides/export
rm -rf "$OUT/png" && mkdir -p "$OUT/png"
PUPPETEER_SKIP_DOWNLOAD=true npx --yes decktape@3.17.0 reveal \
  --chrome-path "$CHROME" --size 1100x700 --pause 800 \
  --screenshots --screenshots-directory "$OUT/png" --screenshots-format png \
  "file://$PWD/slides/index.html?export" "$OUT/agentic-tabi-2026.pdf"
uv run --with python-pptx python scripts/png_to_pptx.py "$OUT/png" "$OUT/agentic-tabi-2026.pptx"
echo "Listo: $OUT/agentic-tabi-2026.pdf y $OUT/agentic-tabi-2026.pptx"
