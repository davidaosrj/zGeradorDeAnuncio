"""CLI da pré-geração offline."""

from __future__ import annotations

import argparse
import sys

from .offline import OfflineGenerationError, generate_offline


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="anuncio-offline")
    parser.add_argument("input", help="diretório do produto ou caminho de produto.json")
    parser.add_argument("--output", help="diretório de saída opcional")
    args = parser.parse_args(argv)
    try:
        output = generate_offline(args.input, args.output)
    except (OfflineGenerationError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    print(f"Pré-anúncio criado em {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
