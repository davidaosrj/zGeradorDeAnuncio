"""Servidor MCP para agentes operarem o gerador de anúncios."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .pipeline import generate_advertisement
from .repository import ProductRepository

mcp = FastMCP("gerador-anuncios", host="0.0.0.0", port=8001)


@mcp.tool()
def cadastrar_produto(produto: dict[str, Any]) -> dict[str, Any]:
    """Cadastra ou atualiza produto.json. Imagens são enviadas pelo frontend ou copiadas para IMG_ORIGINAL."""
    target = ProductRepository().save_product(produto)
    return {"ok": True, "path": str(target), "proximo_passo": "adicione imagens em IMG_ORIGINAL"}


@mcp.tool()
def validar_produto(sku: str) -> dict[str, Any]:
    """Retorna metadados, quantidade de imagens e pendências básicas de um SKU."""
    repo = ProductRepository(); data = repo.load_product(sku); status = repo.status(sku)
    required = [name for name in ("nome", "quantidade") if not data.get(name)]
    if not status["input_images"]: required.append("imagens")
    return {**status, "pendencias": required, "valido": not required}


@mcp.tool()
def gerar_anuncio(sku: str, modo: str = "auto") -> dict[str, Any]:
    """Gera copy, seis artes por cor e ZIP. Modo: auto, offline ou online."""
    if modo not in {"auto", "offline", "online"}: raise ValueError("Modo inválido")
    repo = ProductRepository(); output = generate_advertisement(repo.product_dir(sku), mode=modo)
    return {"ok": True, "output": str(output), "status": repo.status(sku)}


@mcp.tool()
def consultar_status(sku: str) -> dict[str, Any]:
    """Consulta o estado atual dos arquivos de entrada e saída."""
    return ProductRepository().status(sku)


def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__": main()
