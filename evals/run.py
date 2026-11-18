"""Evals comparativos de las técnicas: uv run python evals/run.py [-t bm25 -t agent ...] [-m modelo] [-w 4]"""
import argparse
import asyncio
import json
import os
import sys
import threading
import time
from pathlib import Path

from opentelemetry import trace
from strands_evals import Experiment
from strands_evals.evaluators import FaithfulnessEvaluator, OutputEvaluator, ResponseRelevanceEvaluator, ToolCalled
from strands_evals.mappers import StrandsInMemorySessionMapper
from strands_evals.telemetry import StrandsEvalsTelemetry

sys.path.insert(0, str(Path(__file__).parent))
from dataset import CASES  # noqa: E402

RUBRIC = (
    "Compará la respuesta con la esperada: debe ser factualmente consistente, en español y sin inventar. "
    "Para preguntas fuera de tema, rechazar o decir que no hay información cuenta como correcto. "
    "Score 1 = correcta, 0.5 = parcial, 0 = incorrecta o inventada."
)
# tool que debe aparecer en la trayectoria de cada técnica con agentes
TOOL_CHECK = {"agent": "search_docs", "multi": "classify_relevance"}


EXPORTER = None  # se crea en main(); sin él (ej. smoke.py) la trayectoria es solo la lista de tools


def _session(trace_id, session_id):
    """Spans OTEL del caso (filtrados por trace_id, así funciona en paralelo) -> Session para los evaluadores."""
    spans = [x for x in EXPORTER.get_finished_spans() if x.context.trace_id == trace_id]
    return StrandsInMemorySessionMapper().map_to_session(spans, session_id)


def task_for(name, ask):
    """Task por técnica: imprime una línea por caso apenas termina y no deja que un error tumbe la corrida."""
    done, lock, total = [0], threading.Lock(), len(CASES)

    def task(case):
        t0 = time.time()
        trace_id = trace.get_current_span().get_span_context().trace_id
        try:
            r = ask(case.input)
            out, tools, status = r.answer, r.tools, "ok"
        except Exception as e:  # ej. error del modelo: el caso puntúa 0 y se ve en pantalla
            out, tools, status = f"ERROR: {e}", [], f"ERROR {type(e).__name__}: {str(e)[:80]}"
        with lock:
            done[0] += 1
            print(f"  [{name}] {done[0]}/{total} {time.time() - t0:5.1f}s {status} | {case.input[:50]}", flush=True)
        # con telemetría: Session completa (mensajes, contexto recuperado, tool calls); sin ella: nombres de tools
        return {"output": out, "trajectory": _session(trace_id, case.name) if EXPORTER else tools}

    return task


def run(name, ask, evaluators, workers=1):
    exp = Experiment(cases=CASES, evaluators=evaluators)
    return asyncio.run(exp.run_evaluations_async(task_for(name, ask), max_workers=workers))


def summary(report):
    """Score medio por evaluador."""
    by: dict[str, list[float]] = {}
    for c, s in zip(report.cases, report.scores):
        by.setdefault(c["evaluator"], []).append(s)
    return {k: sum(v) / len(v) for k, v in by.items()}


def main():
    from tabi.config import judge_model, use_llm
    from tabi.techniques import TECHNIQUES

    p = argparse.ArgumentParser()
    p.add_argument("-t", "--technique", action="append", choices=list(TECHNIQUES))
    p.add_argument("-m", "--model", help="slug de OpenRouter a evaluar (el juez no cambia)")
    p.add_argument("-w", "--workers", type=int, default=4, help="casos en paralelo (bajalo si OpenRouter limita)")
    args = p.parse_args()
    names = args.technique or list(TECHNIQUES)
    global EXPORTER
    EXPORTER = StrandsEvalsTelemetry().setup_in_memory_exporter().in_memory_exporter
    if args.model:
        use_llm(args.model)

    out = Path(__file__).parent / "results"
    out.mkdir(exist_ok=True)
    print(f"{len(CASES)} casos x {len(names)} técnicas | modelo: {args.model or 'default'} | {args.workers} en paralelo")
    table = {}
    for n in names:
        print(f"\n== {n}: respondiendo y evaluando con el juez…", flush=True)
        t0 = time.time()
        evs = [
            OutputEvaluator(rubric=RUBRIC, model=judge_model(), name="correctness"),
            FaithfulnessEvaluator(model=judge_model(), name="faithfulness"),
            ResponseRelevanceEvaluator(model=judge_model(), name="relevance"),
        ]
        if n in TOOL_CHECK:
            evs.append(ToolCalled(TOOL_CHECK[n], name="tool_called"))
        rep = run(n, TECHNIQUES[n], evs, args.workers)
        table[n] = summary(rep)
        print(f"== {n} listo en {time.time() - t0:.0f}s: {table[n]}", flush=True)
        slug = (args.model or "default").replace("/", "_")
        dump = rep.model_dump()
        for c in dump["cases"]:
            c.pop("actual_trajectory", None)  # la Session completa es enorme; el detalle queda en los puntajes y razones
        (out / f"{slug}__{n}.json").write_text(json.dumps(dump, ensure_ascii=False, indent=2, default=str))

    cols = ["correctness", "faithfulness", "relevance", "tool_called"]
    if path := os.getenv("GITHUB_STEP_SUMMARY"):  # en GitHub Actions: tabla markdown en el summary de la corrida
        md = [f"## Evals TABI — modelo `{args.model or 'default'}`", "", f"{len(CASES)} casos por técnica", ""]
        md += ["| técnica | " + " | ".join(cols) + " |", "|---|" + "---:|" * len(cols)]
        md += [f"| {n} | " + " | ".join(f"{s[c]:.2f}" if c in s else "–" for c in cols) + " |" for n, s in table.items()]
        with open(path, "a") as f:
            f.write("\n".join(md) + "\n")
    print(f"\n{'técnica':<12}" + "".join(f"{c:>14}" for c in cols))
    for n, s in table.items():
        print(f"{n:<12}" + "".join(f"{s.get(c, float('nan')):>14.2f}" for c in cols))


if __name__ == "__main__":
    main()
