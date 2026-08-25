"""CLI para verificar a conexão com o Ollama remoto."""

from __future__ import annotations

import argparse
import sys

from .ollama import OllamaClient, OllamaError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ollama-check")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("health", help="verifica a API e conta os modelos")
    commands.add_parser("models", help="lista os modelos instalados")
    chat = commands.add_parser("chat", help="envia um prompt de teste")
    chat.add_argument("--prompt", required=True)
    chat.add_argument("--model")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    client = OllamaClient()
    try:
        if args.command == "health":
            models = client.list_models()
            print(f"Ollama disponível em {client.config.base_url} ({len(models)} modelo(s))")
        elif args.command == "models":
            models = client.list_models()
            print("\n".join(models) if models else "Nenhum modelo instalado")
        else:
            print(client.chat([{"role": "user", "content": args.prompt}], model=args.model))
    except OllamaError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
