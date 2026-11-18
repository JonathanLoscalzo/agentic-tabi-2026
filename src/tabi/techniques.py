"""Todas las técnicas comparten la firma ask(question) -> Result."""
from dataclasses import dataclass, field
from typing import Callable

import httpx

from strands import Agent, tool

from . import index
from .config import K, SEARXNG_URL, model

RAG_PROMPT = """Respondé la pregunta usando SOLO el contexto. Si el contexto no alcanza, decí que no lo sabés.
Máximo tres oraciones, en español. Citá la fuente como (archivo, p. N).

CONTEXTO
{context}

PREGUNTA: {question}"""


@dataclass
class Result:
    answer: str
    contexts: list[dict] = field(default_factory=list)  # chunks recuperados
    prompt: str = ""  # prompt final armado (el "contexto")
    tools: list[str] = field(default_factory=list)  # tools usadas por agentes


def build_context(hits: list[dict]) -> str:
    return "\n\n".join(f"[{i}] ({h['source']}, p. {h['page']})\n{h['text']}" for i, h in enumerate(hits, 1))


def _answer(llm_prompt: str) -> str:
    return str(Agent(model=model(), callback_handler=None)(llm_prompt))


def no_context(q: str) -> Result:
    return Result(_answer(q), prompt=q)


def _rag(search: Callable[[str, int], list[dict]]) -> Callable[[str], Result]:
    def run(q: str) -> Result:
        hits = search(q, K)
        prompt = RAG_PROMPT.format(context=build_context(hits), question=q)
        return Result(_answer(prompt), hits, prompt)

    return run


bm25, vector, ensemble = _rag(index.search_bm25), _rag(index.search_vector), _rag(index.search_ensemble)


# ---------- agentes ----------
def _tool_names(agent_result) -> list[str]:
    return list(agent_result.metrics.tool_metrics.keys())


@tool
def search_docs(query: str) -> str:
    """Busca en los libros locales (modelo dimensional, open source, datos, ML) y devuelve fragmentos con fuente."""
    return build_context(index.search_ensemble(query, K))


@tool
def search_web(query: str) -> str:
    """Busca en la web (SearXNG local) cuando los documentos locales no alcanzan."""
    r = httpx.get(f"{SEARXNG_URL}/search", params={"q": query, "format": "json"}, timeout=20)
    r.raise_for_status()
    return "\n".join(f"- {x['title']}: {x.get('content', '')} ({x['url']})" for x in r.json()["results"][:4])


def agent(q: str) -> Result:
    """Un solo agente que decide cuándo llamar a la tool de búsqueda."""
    a = Agent(
        model=model(),
        tools=[search_docs],
        system_prompt="Respondé en español usando search_docs antes de contestar. Citá (archivo, p. N). Si no hay info, decilo.",
        callback_handler=None,
    )
    r = a(q)
    return Result(str(r), prompt=q, tools=_tool_names(r))


def _sub(name: str, prompt: str, tools: list) -> Callable:
    @tool(name=name)
    def run(query: str) -> str:
        return str(Agent(model=model(), tools=tools, system_prompt=prompt, callback_handler=None)(query))

    run.__doc__ = prompt.splitlines()[0]
    return run


_classifier = _sub(
    "classify_relevance",
    "Clasificador. Respondé SOLO RELEVANTE o NO_RELEVANTE: ¿la pregunta trata de modelo dimensional, open source, datos o machine learning?",
    [],
)
_docs_agent = _sub("docs_agent", "Agente de documentos locales. Usá search_docs y devolvé hallazgos con fuente.", [search_docs])
_web_agent = _sub("web_agent", "Agente web. Usá search_web y devolvé hallazgos con URL.", [search_web])

ORCHESTRATOR = """Sos el orquestador de TABI. Flujo:
1. Llamá classify_relevance. Si es NO_RELEVANTE, respondé que está fuera de tema y terminá.
2. Llamá docs_agent. Si la información es insuficiente, llamá también web_agent.
3. Resumí en español en máximo 4 oraciones, citando fuentes."""


def multi(q: str) -> Result:
    """Multi-agente (agents-as-tools): clasificador -> docs -> web -> resumen."""
    a = Agent(
        model=model(),
        tools=[_classifier, _docs_agent, _web_agent],
        system_prompt=ORCHESTRATOR,
        callback_handler=None,
    )
    r = a(q)
    return Result(str(r), prompt=q, tools=_tool_names(r))


TECHNIQUES: dict[str, Callable[[str], Result]] = {
    "no_context": no_context,
    "bm25": bm25,
    "vector": vector,
    "ensemble": ensemble,
    "agent": agent,
    "multi": multi,
}
