---
name: simulador-roas-marketplaces
description: Implementar, operar ou diagnosticar o simulador de ROAS seguro deste repositório para Shopee e Mercado Livre, incluindo margem, custos, estoque, crédito, orçamento e avaliação pós-ativação. Não use para definir tarifas oficiais sem dados atuais confirmados.
---

# Simulador de ROAS para marketplaces

Antes de alterar fórmulas ou recomendações, leia [`docs/adr/ADR-002-simulador-roas-seguro-marketplaces.md`](../../../docs/adr/ADR-002-simulador-roas-seguro-marketplaces.md) e [`docs/specs/SPEC-004-simulador-roas-marketplaces.md`](../../../docs/specs/SPEC-004-simulador-roas-marketplaces.md).

## Regras essenciais

- Execute cálculos com o núcleo determinístico; Ollama pode explicar, mas não calcular ou completar valores.
- Trate taxas como dados confirmados, datados e específicos da conta. Nunca grave percentuais de marketplace como universais.
- Preserve a separação entre receita atribuída e total, conversão por clique e por sessão, dados provisórios e maturados.
- Não classifique como seguro quando preço, margem ou CPA seguro forem inválidos.
- Limite orçamento por crédito, caixa e estoque, indicando qual limite determinou o resultado.
- Calcule estoque mínimo e crédito máximo suportado; sinalize explicitamente incompatibilidade por margem ou estoque.
- Recomende mudanças somente depois da amostra mínima configurada e nunca altere campanhas externas sem autorização explícita.
- Use `Decimal` para dinheiro e teste limites, valores nulos e divisão por zero.

## Fluxo

1. Valide preço, custos, percentuais, estoque e campanha.
2. Calcule margem antes dos anúncios, ACOS/ROAS de equilíbrio e CPA/ROAS seguro.
3. Calcule os limites de crédito, caixa e estoque.
4. Na avaliação, confirme maturação e amostra antes de sugerir ajuste.
5. Retorne fórmulas, hipóteses, alertas e motivos em estrutura auditável.

Use `/api/roas/simulate`, `/api/roas/evaluate` ou as ferramentas MCP correspondentes.
