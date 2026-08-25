# SPEC-004 — Simulador de ROAS para Marketplaces

## Escopo

Implementar a [ADR-002](../adr/ADR-002-simulador-roas-seguro-marketplaces.md) no frontend e no MCP. O cálculo é determinístico, opera offline e mantém perfis independentes para Shopee e Mercado Livre.

## Contrato HTTP

### `POST /api/roas/simulate`

Recebe o perfil econômico, estoque e campanha. Retorna margem de contribuição, CPA máximo seguro, ROAS/ACOS de equilíbrio, ROAS mínimo seguro e limites de orçamento.

Também retorna:

- estoque mínimo para consumir o crédito planejado no ponto de equilíbrio;
- estoque mínimo para consumir o crédito preservando a margem líquida desejada;
- crédito máximo seguro suportado pelo estoque vendável;
- quantidade adicional necessária;
- compatibilidade do produto com o crédito: `SEM_CREDITO`, `COMPATIVEL`, `INCOMPATIVEL_ESTOQUE` ou `INCOMPATIVEL_MARGEM`.
- lucro protegido por unidade em reais;
- lucro projetado após Ads para as unidades mínimas do cenário seguro;
- resultado potencial caso todo o estoque vendável seja vendido após consumir o crédito planejado.

Os valores projetados devem ser identificados como cenários matemáticos, sem promessa de vendas.

O crédito planejado é o menor valor entre o crédito total e `orçamento diário × horizonte`. Quando o orçamento diário for zero, considera-se o crédito total para a análise de compatibilidade.

```text
estoque_minimo_equilibrio = teto(credito_planejado / margem_contribuicao_unitaria)
estoque_minimo_lucro = teto(credito_planejado / CPA_maximo_seguro)
credito_maximo_seguro = estoque_vendavel × CPA_maximo_seguro
```

### `POST /api/roas/evaluate`

Recebe o mesmo perfil com o objeto `actual`. Retorna métricas realizadas, estado da campanha e sugestões explicáveis.

### `POST /api/calculator/sale-profit`

Calcula quanto sobra por venda, detalhando comissão, tarifa fixa, embalagem, imposto, frete, Ads, custo total, lucro e margem.

### `POST /api/calculator/ideal-price`

Calcula o preço necessário para atingir a margem informada. Ads pode ser ignorado, informado como custo fixo por venda ou derivado de um ROAS esperado.

## Calculadora Mercado Livre

A página `/calculadora-mercado-livre` oferece os mesmos modos de lucro e preço ideal, com seleção de anúncio Clássico ou Premium, comissões configuráveis, peso informativo, custo de envio, tarifa fixa e Mercado Ads. O sistema não embute tabela de frete ou comissão como regra permanente.

## Calculadora unificada e administração

A página `/calculadora-marketplaces` calcula lucro e preço ideal para Shopee, Mercado Livre, Magalu e Amazon. O menu Administração mantém comissão, taxa de pagamento, tarifa fixa, impostos, embalagem, logística, margem e data de revisão por plataforma no `localStorage`, com exportação e importação JSON.

O resultado é recalculado automaticamente após alterações de preço, margem desejada, comissão, taxas, Ads ou custos. Alterar a margem desejada atualiza o preço ideal e o lucro correspondente; na Shopee, a faixa de comissão e a tarifa fixa são aplicadas antes de cada recálculo.

O perfil inicial Shopee segue as faixas exibidas pela referência informada pelo usuário, indicadas como vigentes desde 01/03/2026: 20% + R$ 4 até R$ 79,99; 14% + R$ 16 de R$ 80 a R$ 99,99; 14% + R$ 20 de R$ 100 a R$ 199,99; e 14% + R$ 26 a partir de R$ 200. O adicional configurável para CPF com mais de 450 pedidos em 90 dias inicia em R$ 3. Esses valores têm origem e data visíveis e podem ser alterados no menu administrativo.

Valores monetários e razões retornam como strings decimais para evitar perda de precisão. Percentuais de entrada usam a escala de 0 a 100.

## Entrada

```json
{
  "marketplace": "shopee",
  "sku": "SKU0011",
  "price": 39.90,
  "costs": {
    "product": 10.00,
    "packaging": 1.00,
    "commission_pct": 20,
    "tax_pct": 6,
    "payment_pct": 0,
    "fixed_fee": 4,
    "seller_shipping": 0,
    "seller_discount": 0,
    "returns_reserve_pct": 2,
    "other": 0
  },
  "stock": {"physical": 100, "reserved": 5, "safety": 10},
  "campaign": {
    "credit_total": 300,
    "daily_credit_limit": 30,
    "desired_daily_budget": 25,
    "cashflow_daily_limit": 25,
    "horizon_days": 30,
    "minimum_net_margin_pct": 8
  }
}
```

Todos os custos devem ser revisados pelo usuário conforme sua conta. O exemplo não representa tarifas oficiais.

## Dados pós-ativação

O objeto `actual` aceita gasto, receita atribuída, cliques, pedidos e unidades atribuídas, pedidos totais, sessões, dias observados, maturação e amostras mínimas.

Estados: `SEM_DADOS`, `EM_APRENDIZADO`, `SAUDAVEL`, `ATENCAO`, `RISCO_DE_PREJUIZO`, `RISCO_DE_ESTOQUE` e `CREDITO_INSUFICIENTE`.

## MCP

- `calcular_roas_equilibrio(perfil)`
- `simular_orcamento_ads(perfil)`
- `avaliar_campanha_ativa(perfil)`
- `sugerir_ajuste_orcamento(perfil)`

As ferramentas usam o mesmo módulo chamado pela API HTTP e não alteram campanhas externas.

## Regras de validação

- Preço e horizonte devem ser maiores que zero.
- Estoque e valores financeiros não podem ser negativos.
- Percentuais devem estar entre 0 e 100.
- Margem ou CPA seguro não positivos bloqueiam orçamento seguro.
- Divisões sem denominador retornam `null`, não infinito.
- O orçamento recomendado é o menor limite aplicável.

## Testes mínimos

- fórmulas de equilíbrio e segurança;
- limites de crédito e estoque;
- incompatibilidade do crédito por estoque e por margem;
- margem negativa e percentuais inválidos;
- estados sem dados, em aprendizado, prejuízo e saudável;
- valores nulos, arredondamento e divisão por zero.
