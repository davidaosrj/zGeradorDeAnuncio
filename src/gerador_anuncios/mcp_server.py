"""Servidor MCP para agentes operarem o gerador de anúncios."""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .pipeline import generate_advertisement
from .repository import ProductRepository
from .roas import calculate_simulation, evaluate_campaign
from .sale_calculator import calculate_ideal_price, calculate_sale_profit

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


@mcp.tool()
def calcular_roas_equilibrio(perfil: dict[str, Any]) -> dict[str, Any]:
    """Calcula margem, ACOS/ROAS de equilíbrio e ROAS mínimo seguro."""
    return calculate_simulation(perfil)


@mcp.tool()
def simular_orcamento_ads(perfil: dict[str, Any]) -> dict[str, Any]:
    """Limita o orçamento diário por crédito, caixa, margem e estoque."""
    return calculate_simulation(perfil)


@mcp.tool()
def avaliar_campanha_ativa(perfil: dict[str, Any]) -> dict[str, Any]:
    """Avalia métricas pós-ativação, maturação e amostra mínima."""
    return evaluate_campaign(perfil)


@mcp.tool()
def sugerir_ajuste_orcamento(perfil: dict[str, Any]) -> dict[str, Any]:
    """Sugere ajuste, mas nunca executa alteração externa."""
    result = evaluate_campaign(perfil)
    return {"budget": result["budget"], "evaluation": result["evaluation"], "alerts": result["alerts"]}


@mcp.tool()
def calcular_lucro_por_venda(dados: dict[str, Any]) -> dict[str, Any]:
    """Detalha quanto sobra por venda depois de custos, tarifas, impostos e Ads."""
    return calculate_sale_profit(dados)


@mcp.tool()
def calcular_preco_ideal(dados: dict[str, Any]) -> dict[str, Any]:
    """Calcula o preço necessário para atingir a margem líquida informada."""
    return calculate_ideal_price(dados)



def main() -> None:
    mcp.run(transport="streamable-http")


if __name__ == "__main__": main()
