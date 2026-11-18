"""Evals comparativos de las técnicas: uv run python evals/run.py [-t bm25 -t agent ...]"""
import argparse
import json
import sys
from pathlib import Path

from strands_evals import Experiment
from strands_evals.evaluators import OutputEvaluator, ToolCalled

sys.path.insert(0, str(Path(__file__).parent))
from dataset import CASES  # noqa: E402

RUBRIC = (
    "Compará la respuesta con la esperada: debe ser factualmente consistente, en español y sin inventar. "
    "Para preguntas fuera de tema, rechazar o decir que no hay información cuenta como correcto. "
    "Score 1 = correcta, 0.5 = parcial, 0 = incorrecta o inventada."
)
# tool que debe aparecer en la trayectoria de cada técnica con agentes
TOOL_CHECK = {"agent": "search_docs", "multi": "classify_relevance"}


def task_for(ask):
    def task(case):
        r = ask(case.input)
        return {"output": r.answer, "trajectory": r.tools}  # tools: lista de nombres usados

    return task


def run(name, ask, evaluators):
    exp = Experiment(cases=CASES, evaluators=evaluators)
    return exp.run_evaluations(task_for(ask))


def summary(report):
    """Score medio por evaluador."""
    by: dict[str, list[float]] = {}
    for c, s in zip(report.cases, report.scores):
        by.setdefault(c["evaluator"], []).append(s)
    return {k: sum(v) / len(v) for k, v in by.items()}


def main():
    from tabi.config import judge_model
    from tabi.techniques import TECHNIQUES

    p = argparse.ArgumentParser()
    p.add_argument("-t", "--technique", action="append", choices=list(TECHNIQUES))
    names = p.parse_args().technique or list(TECHNIQUES)

    out = Path(__file__).parent / "results"
    out.mkdir(exist_ok=True)
    table = {}
    for n in names:
        evs = [OutputEvaluator(rubric=RUBRIC, model=judge_model(), name="correctness")]
        if n in TOOL_CHECK:
            evs.append(ToolCalled(TOOL_CHECK[n], name="tool_called"))
        rep = run(n, TECHNIQUES[n], evs)
        table[n] = summary(rep)
        (out / f"{n}.json").write_text(json.dumps(rep.model_dump() if hasattr(rep, "model_dump") else rep.to_dict(), ensure_ascii=False, indent=2, default=str))

    print(f"\n{'técnica':<12}{'correctness':>12}{'tool_called':>13}")
    for n, s in table.items():
        print(f"{n:<12}{s.get('correctness', float('nan')):>12.2f}{s.get('tool_called', float('nan')):>13.2f}")


if __name__ == "__main__":
    main()
