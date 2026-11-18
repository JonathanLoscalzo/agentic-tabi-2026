import argparse

from . import index
from .techniques import TECHNIQUES


def main():
    p = argparse.ArgumentParser(prog="tabi")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("index", help="indexa los PDFs de data/ en Chroma")
    a = sub.add_parser("ask", help="pregunta con una o todas las técnicas")
    a.add_argument("question")
    a.add_argument("-t", "--technique", default="all", choices=["all", *TECHNIQUES])
    a.add_argument("--show-context", action="store_true", help="imprime los chunks y el prompt armado")
    args = p.parse_args()

    if args.cmd == "index":
        print(f"{index.build()} chunks en Chroma")
        return
    for name in TECHNIQUES if args.technique == "all" else [args.technique]:
        r = TECHNIQUES[name](args.question)
        print(f"\n===== {name} =====\n{r.answer}")
        if r.tools:
            print(f"tools: {r.tools}")
        if args.show_context:
            for h in r.contexts:
                print(f"  - {h['source']} p.{h['page']}: {h['text'][:100]!r}")
            print(f"--- prompt ---\n{r.prompt}")


if __name__ == "__main__":
    main()
