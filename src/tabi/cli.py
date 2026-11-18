import argparse

from . import config, index
from .techniques import TECHNIQUES


def main():
    p = argparse.ArgumentParser(prog="tabi")
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("index", help="indexa los PDFs de data/ en Chroma")
    i.add_argument("--rebuild", action="store_true", help="borra y vuelve a indexar")
    sub.add_parser("chat", help="abre el cliente de chat (Streamlit)")
    m = sub.add_parser("models", help="lista modelos de OpenRouter")
    m.add_argument("filter", nargs="?", default="")
    a = sub.add_parser("ask", help="pregunta con una o todas las técnicas")
    a.add_argument("question")
    a.add_argument("-t", "--technique", default="all", choices=["all", *TECHNIQUES])
    a.add_argument("-m", "--model", help="slug de OpenRouter, ej. openai/gpt-5-mini (ver `tabi models`)")
    a.add_argument("--show-context", action="store_true", help="imprime los chunks y el prompt armado")
    args = p.parse_args()

    if args.cmd == "models":
        print("\n".join(i for i in config.list_models() if args.filter.lower() in i.lower()))
        return
    if args.cmd == "index":
        print(f"{(index.rebuild if args.rebuild else index.build)()} chunks en Chroma")
        return
    if args.cmd == "chat":
        import subprocess
        import sys
        from pathlib import Path

        sys.exit(subprocess.call([sys.executable, "-m", "streamlit", "run", str(Path(__file__).with_name("app.py"))]))
    if args.model:
        config.use_llm(args.model)
    for name in TECHNIQUES if args.technique == "all" else [args.technique]:
        r = TECHNIQUES[name](args.question)
        print(f"\n===== {name} =====\n{r.answer}")
        if r.tools:
            print(f"tools: {r.tools}")
        if args.show_context:
            if r.queries:
                print(f"consultas del agente: {r.queries}")
            for h in r.contexts:
                print(f"  - {h['source']} p.{h['page']}: {h['text'][:100]!r}")
            print(f"--- prompt ---\n{r.prompt}")


if __name__ == "__main__":
    main()
