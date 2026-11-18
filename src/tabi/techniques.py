"""Todas las técnicas comparten la firma ask(question) -> Result."""
from dataclasses import dataclass, field
from typing import Callable

import json
import os
import time

import httpx

from strands import Agent, tool

from . import index
from .config import DEFAULT_LLM, K, ROOT, SEARXNG_URL, model

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
    queries: list[str] = field(default_factory=list)  # consultas que el agente eligió hacer a search_docs


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


CONVERSATIONS = ROOT / "tmp" / "conversations"  # ignorada por git


def _save(technique: str, q: str, answer: str, agents: dict[str, Agent]) -> None:
    """Guarda la conversación completa (mensajes, tool calls) de cada agente que participó."""
    CONVERSATIONS.mkdir(parents=True, exist_ok=True)
    f = CONVERSATIONS / f"{time.strftime('%Y%m%d-%H%M%S')}-{technique}-{time.time_ns() % 10**6:06d}.json"
    data = {
        "technique": technique,
        "model": os.getenv("TABI_LLM", DEFAULT_LLM),
        "question": q,
        "answer": answer,
        "agents": {name: ag.messages for name, ag in agents.items()},
    }
    f.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def make_search_docs(log: list[tuple[str, list[dict]]]):
    """Tool search_docs que anota (consulta, chunks) en `log` cada vez que el modelo la llama."""

    @tool
    def search_docs(query: str) -> str:
        """Busca en los libros locales (modelo dimensional, open source, datos, ML) y devuelve fragmentos con fuente."""
        hits = index.search_ensemble(query, K)
        log.append((query, hits))
        return build_context(hits)

    return search_docs


def _from_log(answer: str, q: str, r, log: list[tuple[str, list[dict]]]) -> Result:
    seen = {}
    for _, hits in log:
        for h in hits:
            seen.setdefault(h["id"], h)  # chunks únicos, en orden de aparición
    return Result(answer, list(seen.values()), q, _tool_names(r), [query for query, _ in log])


@tool
def search_web(query: str) -> str:
    """Busca en la web (SearXNG local) cuando los documentos locales no alcanzan."""
    r = httpx.get(f"{SEARXNG_URL}/search", params={"q": query, "format": "json"}, timeout=20)
    r.raise_for_status()
    return "\n".join(f"- {x['title']}: {x.get('content', '')} ({x['url']})" for x in r.json()["results"][:4])


def agent(q: str) -> Result:
    """Un solo agente que decide cuándo llamar a la tool de búsqueda."""
    log: list = []
    a = Agent(
        model=model(),
        tools=[make_search_docs(log)],
        system_prompt="Respondé en español usando search_docs antes de contestar. Citá (archivo, p. N). Si no hay info, decilo.",
        callback_handler=None,
    )
    r = a(q)
    _save("agent", q, str(r), {"agent": a})
    return _from_log(str(r), q, r, log)


def _sub(name: str, prompt: str, tools: list, sink: dict[str, Agent]) -> Callable:
    """Sub-agente expuesto como tool; registra su Agent en `sink` para guardar su conversación."""

    @tool(name=name)
    def run(query: str) -> str:
        ag = Agent(model=model(), tools=tools, system_prompt=prompt, callback_handler=None)
        sink[f"{name}#{len(sink) + 1}"] = ag
        return str(ag(query))

    run.__doc__ = prompt.splitlines()[0]
    return run


ORCHESTRATOR = """Sos el orquestador de TABI. Flujo:
1. Llamá classify_relevance. Si es NO_RELEVANTE, respondé que está fuera de tema y terminá.
2. Llamá docs_agent. Si la información es insuficiente, llamá también web_agent.
3. Resumí en español en máximo 4 oraciones, citando fuentes."""


def multi(q: str) -> Result:
    """Multi-agente (agents-as-tools): clasificador -> docs -> web -> resumen."""
    log: list = []
    sub: dict[str, Agent] = {}
    classifier = _sub(
        "classify_relevance",
        "Clasificador. Respondé SOLO RELEVANTE o NO_RELEVANTE: ¿la pregunta trata de modelo dimensional, open source, datos o machine learning?",
        [],
        sub,
    )
    docs_agent = _sub(
        "docs_agent", "Agente de documentos locales. Usá search_docs y devolvé hallazgos con fuente.", [make_search_docs(log)], sub
    )
    web_agent = _sub("web_agent", "Agente web. Usá search_web y devolvé hallazgos con URL.", [search_web], sub)
    a = Agent(model=model(), tools=[classifier, docs_agent, web_agent], system_prompt=ORCHESTRATOR, callback_handler=None)
    r = a(q)
    _save("multi", q, str(r), {"orchestrator": a, **sub})
    return _from_log(str(r), q, r, log)


TECHNIQUES: dict[str, Callable[[str], Result]] = {
    "no_context": no_context,
    "bm25": bm25,
    "vector": vector,
    "ensemble": ensemble,
    "agent": agent,
    "multi": multi,
}
