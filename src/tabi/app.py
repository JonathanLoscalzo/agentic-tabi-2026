"""Cliente de chat: uv run tabi chat  (Streamlit)"""
import json
import os
import re

import streamlit as st

from tabi import config, index
from tabi.techniques import TECHNIQUES

st.set_page_config(page_title="TABI QA", page_icon="📚", layout="wide")
st.title("📚 TABI QA")

DOC = (config.ROOT / "docs" / "tecnicas.md").read_text()
SECTIONS = {m[1]: m[2] for m in re.finditer(r"^## (\S+) — [^\n]*\n\n(.*?)(?=^## |\Z)", DOC, re.S | re.M)}
SUMMARY = {k: v.split("\n", 1)[0].lstrip("> ") for k, v in SECTIONS.items()}


@st.cache_data(ttl=3600)
def models() -> list[str]:
    try:
        return config.list_models()
    except Exception:
        return [config.DEFAULT_LLM]


with st.sidebar:
    all_models = models()
    default = os.getenv("TABI_LLM", config.DEFAULT_LLM)
    slug = st.selectbox(
        "Modelo (OpenRouter)",
        all_models,
        index=all_models.index(default) if default in all_models else 0,
        help="Escribí para filtrar. Se aplica a todas las técnicas.",
    )
    config.use_llm(slug)
    chosen = st.multiselect("Técnicas", list(TECHNIQUES), default=["ensemble"])
    st.caption("Elegí varias para compararlas lado a lado.")
    for t in chosen:
        st.caption(f"**{t}**: {SUMMARY.get(t, '')}")
    if st.button("Limpiar chat"):
        st.session_state.msgs = []

    st.divider()
    st.subheader("Índice")
    n = index.collection().count()
    st.metric("Chunks en Chroma", n)
    st.caption(f"PDFs en data/: {len(list(config.DATA_DIR.glob('*.pdf')))}")
    if st.button("Reindexar" if n else "Indexar", help="Re-embebe los PDFs de data/ con Ollama"):
        with st.spinner("Indexando…"):
            index.rebuild()
        st.rerun()

EVALS_DOC = (config.ROOT / "docs" / "evals.md").read_text()


def eval_results() -> list[dict]:
    """Promedio por evaluador de cada corrida guardada en evals/results/."""
    rows = []
    for f in sorted((config.ROOT / "evals" / "results").glob("*__*.json")):
        d = json.loads(f.read_text())
        model, technique = f.stem.split("__", 1)
        row = {"modelo": model.replace("_", "/", 1), "técnica": technique}
        for ev in {c["evaluator"] for c in d["cases"]}:
            sc = [x for c, x in zip(d["cases"], d["scores"]) if c["evaluator"] == ev]
            row[ev] = round(sum(sc) / len(sc), 2)
        rows.append(row)
    return rows


chat_tab, docs_tab, evals_tab = st.tabs(["💬 Chat", "📖 Técnicas", "🧪 Evals"])

with evals_tab:
    st.markdown(EVALS_DOC)
    st.subheader("Últimos resultados")
    rows = eval_results()
    if rows:
        st.dataframe(rows, hide_index=True, width="stretch")
    else:
        st.info("Todavía no hay corridas. Ejecutá `make eval`.")

with docs_tab:
    st.markdown(DOC)

with chat_tab:
    msgs = st.session_state.setdefault("msgs", [])

    def render(m):
        for name, r in m["results"].items():
            with st.expander(f"**{name}** · {m['model']}", expanded=True):
                st.markdown(r.answer)
                if r.tools:
                    st.caption(f"tools: {', '.join(r.tools)}")
                if r.queries:
                    st.markdown("**Consultas que eligió el agente:** " + " · ".join(f"`{x}`" for x in r.queries))
                if r.contexts or r.prompt:
                    with st.expander("Contexto y prompt"):
                        for h in r.contexts:
                            st.markdown(f"**{h['source']}, p. {h['page']}**\n\n{h['text'][:400]}…")
                        st.code(r.prompt, language="text")

    for m in msgs:
        st.chat_message("user").write(m["q"])
        with st.chat_message("assistant"):
            render(m)

    if q := st.chat_input("Preguntá sobre los libros de TABI"):
        st.chat_message("user").write(q)
        with st.chat_message("assistant"):
            results = {}
            for name in chosen or ["ensemble"]:
                with st.spinner(name):
                    try:
                        results[name] = TECHNIQUES[name](q)
                    except Exception as e:  # ej. índice vacío, modelo inválido, Ollama caído
                        st.error(f"{name}: {e}")
            m = {"q": q, "model": slug, "results": results}
            render(m)
        msgs.append(m)
