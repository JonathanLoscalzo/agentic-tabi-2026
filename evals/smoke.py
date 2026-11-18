"""Smoke sin red: técnica falsa + evaluadores determinísticos. uv run python evals/smoke.py"""
from types import SimpleNamespace

from strands_evals.evaluators import Contains, ToolCalled

from run import run, summary

fake = lambda q: SimpleNamespace(answer=f"Kimball y {q}", tools=["search_docs"])
rep = run("fake", fake, [Contains(value="Kimball", name="contains"), ToolCalled("search_docs", name="tool_called")])
s = summary(rep)
print(s)
assert s == {"contains": 1.0, "tool_called": 1.0}, s
print("ok")
