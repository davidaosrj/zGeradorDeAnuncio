from __future__ import annotations

import argparse
import sys

from .offline import OfflineGenerationError
from .pipeline import generate_advertisement


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gerar-anuncio")
    parser.add_argument("input", help="diretório do produto ou produto.json")
    parser.add_argument("--output")
    parser.add_argument("--mode", choices=("auto", "offline", "online"), default="auto")
    args = parser.parse_args(argv)
    try:
        output = generate_advertisement(args.input, mode=args.mode, output_path=args.output)
    except (OfflineGenerationError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr); return 1
    print(f"Anúncio concluído em {output}"); return 0


if __name__ == "__main__": raise SystemExit(main())
