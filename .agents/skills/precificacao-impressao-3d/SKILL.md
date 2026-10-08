---
name: precificacao-impressao-3d
description: Implementar, operar ou diagnosticar a precificação de impressão 3D da ADR-002 neste repositório, incluindo fabricação, kits, tarifas, comparação e histórico. Use para custos e preços de peças FDM; não para edição de imagens ou gestão de campanhas ROAS.
---

# Precificação de impressão 3D

Leia a [ADR-002](../../../docs/adr/ADR-002-motor-precificacao-impressao-3d.md) e a [SPEC-006](../../../docs/specs/SPEC-006-motor-precificacao-impressao-3d.md) antes de alterar cálculos. Para interface, armazenamento no navegador ou publicação, consulte a [SPEC-007](../../../docs/specs/SPEC-007-interface-precificacao-impressao-3d.md).

## Invariantes do domínio

- Use `pricing.calculate_pricing` / `/api/pricing/calculate`; no Pages, `Pricing3D.calculate`. Não delegue matemática financeira ao modelo de linguagem.
- Peso inclui suportes. Quantidade do componente é por unidade/kit; `order_units` multiplica os componentes. Embalagem e montagem são totais do pedido.
- Preços e lucro são do pedido; tarifa `unit` multiplica unidades vendidas, nunca componentes internos do kit. Tarifa `order` entra uma vez.
- Margem é sobre receita, não markup. Some comissão, pagamento, imposto e margem antes de validar o denominador. O desconto configurado é custo do vendedor, com percentuais sobre preço bruto.
- Preserve `Decimal` no Python e operações racionais `BigInt` no navegador. Não arredonde intermediários. Arredonde preço para cima; use meia unidade para cima na apresentação monetária.
- Taxas são configurações do operador. Os valores da ADR são exemplos, não tarifas oficiais. Regras selecionadas devem respeitar canal, versão, vigência e faixa por unidade; não extrapole faixa quando o preço calculado a atravessar.
- Comparações usam pedidos equivalentes, fonte e data. Não transforme vendas acumuladas em vendas por período. Dados ausentes resultam em classificação Indeterminada.
- Preserve snapshots e revisões: alteração de material ou regra não muda histórico. No Pages, informe que os dados são locais e ofereça exportação; não apague dados para contornar quota.

## Alterações e validação

Fontes: `src/gerador_anuncios/pricing.py`, `pricing_repository.py` e `static/pricing*`. Atualize ambos os motores ao alterar fórmulas. Gere o Pages com `python scripts/build_pricing_site.py`; não edite isoladamente a cópia gerada.

Execute testes de precificação/API e paridade Python/Node. Preserve o exemplo da ADR (18,685 de custo e 46,37 de preço) e cubra qualquer novo limite financeiro introduzido. Depois execute a suíte do CI. Use o fluxo CI/CD do repositório para publicação; não considere push de branch como deploy concluído.
