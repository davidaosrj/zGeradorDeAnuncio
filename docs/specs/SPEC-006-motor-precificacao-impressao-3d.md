# SPEC-006 — Motor de precificação de impressão 3D

Status: implementada na versão inicial. Decisão: [ADR-002](../adr/ADR-002-motor-precificacao-impressao-3d.md).

## Contrato e unidades

`pricing.calculate_pricing(dict)` não faz I/O. A API `POST /api/pricing/calculate` calcula e grava uma simulação em SQLite (`PRICING_DB`, padrão `data/pricing.sqlite3`). Erros de domínio retornam HTTP 422; cálculo inválido não gera histórico. Dinheiro é BRL e todos os preços de entrada/saída referem-se ao pedido completo. `price_per_unit` divide o preço sugerido pelas unidades vendidas. Uma unidade pode ser um kit completo.

Entradas numéricas aceitam decimais não negativos, até seis casas, sem notação exponencial, até 1 bilhão. Quantidades são inteiros de 1 a 1 milhão. Há no máximo 100 componentes e 100 concorrentes. Use strings decimais na API para preservar precisão de transporte. Cálculos Python usam `Decimal`, precisão 80, sem arredondamento intermediário. Valores apresentados usam duas casas, `ROUND_HALF_UP`. Preços mínimos e sugeridos arredondam para cima, garantindo margem. Fator multiplicador usa quatro casas.

## Dados de uma simulação

- Identificação: `name`, `sku`, `category`, `currency=BRL`, `calculation_date` (AAAA-MM-DD).
- `components[]`: `name`, `quantity` por unidade/kit, `weight_g` incluindo suportes, `hours`, `filament_price_kg`, `machine_hour`, `energy_hour`, `additional_cost`, referências opcionais `material_id`, `printer_id`.
- `order_units`: quantidade de unidades/kits no pedido.
- `failure_pct`: reserva de fabricação; `packaging_cost` e `packaging_count`: custo e número real de embalagens no pedido; `assembly_cost`: montagem total do pedido.
- `shipping`, `discount`, `order_other_cost`: frete/logística, desconto do vendedor e outras despesas totais do pedido. Estes valores entram uma vez. O desconto é um custo separado; a comissão e a margem incidem sobre o preço bruto informado, sem deduzi-lo novamente.
- `target_margin_pct`: percentual da receita bruta, não markup. `commercial_step`: múltiplo de R$ 0,01 para arredondamento comercial para cima. `selling_price`: preço bruto opcional para avaliar lucro; sem ele avalia o sugerido.
- `fee_rule`: `name`, `marketplace` (`shopee`, `mercado_livre`, `direct`), `version`, `category`, `listing_type`, `commission_pct`, `payment_pct`, `tax_pct`, `fixed_fee`, `basis` (`order` ou `unit`), `min_price`, `max_price`, `valid_from`, `valid_until`.

Os padrões de fabricação vêm da ADR (filamento 120/kg, máquina 2/h, energia 0,25/h, falhas 10%, embalagem 4, margem 30%). As fórmulas recebem esses parâmetros. Tarifas na interface começam em zero; o botão de exemplo carrega 20% e R$ 4,50 como dados do exemplo, nunca como tabela oficial.

## Cálculo e regras

1. Multiplicar custos de cada componente por sua quantidade e pelas unidades do pedido.
2. Somar material (gramas / 1000 × preço/kg), máquina, energia e outros custos de fabricação.
3. Aplicar reserva para falhas ao subtotal. Acrescentar embalagens e montagem, sem duplicação por componente.
4. Aplicar tarifa fixa uma vez (`order`) ou por unidade/kit vendido (`unit`), nunca por componente.
5. Somar ao custo de produção tarifa fixa, logística, desconto e outros custos do pedido: `F`.
6. Somar comissão, imposto e pagamento como fração da venda: `r`. Exigir `r + margem < 1`.
7. Equilíbrio = `F / (1-r)`; sugerido = `F / (1-r-margem)`.
8. Arredondar o sugerido para o próximo múltiplo de `commercial_step`. Calcular lucro = preço × `(1-r)` − `F`, margem = lucro / preço × 100, fator = preço / custo de produção.

A regra é selecionada explicitamente pelo operador para o canal, categoria, tipo de anúncio ou campanha. Não existe descoberta automática de tarifas. A vigência inclui ambas as datas; o intervalo de preço por unidade é `[min_price, max_price)`. Se o preço sugerido ou avaliado cruzar uma faixa, rejeitar e solicitar outra regra, sem extrapolar. Custos de produção e preço avaliado devem ser positivos. Percentuais individuais estão entre 0 e 100. Zero margem é permitido.

## Concorrência e rastreabilidade

`competitors[]` guarda nome, categoria, marketplace, `url`, `collected_at`, `price` do pedido equivalente, frete ao comprador, desconto exibido, vendas acumuladas, peso e dimensões. Frete e desconto do concorrente são metadados; o operador informa em `price` o preço bruto comparável. Não inferir vendas por período nem importar anúncios automaticamente.

Ao igualar o preço: lucro <= 0 → Inviável; lucro positivo e margem inferior à desejada → Moderada; margem >= desejada → Alta. Fonte HTTP(S), data e preço ausentes ou preço fora da faixa → Indeterminada. Comparações preservam a observação original.

Resposta contém decomposição dos custos, `production_cost_exact`, equilíbrio, preço calculado/comercial, preço por unidade, lucro, margem, fator, classificação, comparações, versão do motor e `snapshot` dos parâmetros. A API acrescenta ID e data UTC. Resultados anteriores não são recalculados ao alterar cadastros.

## Persistência e API

- `GET /api/pricing/history?limit=100&offset=0`: histórico, mais recente primeiro; limite 1–500.
- `GET/POST /api/pricing/catalogs/{kind}`: `materials`, `printers`, `products`, `fee-rules`. Listagem paginada; gravação cria UUID e data UTC novos, preservando revisões anteriores.
- Material: nome, tipo, fabricante, cor, preço/kg. Impressora: nome/modelo, máquina/h, energia/h, status. Produto: nome, SKU, dados de fabricação e cenário completo. Regra: nome, versão e parâmetros comerciais.

Cadastros são revisões de parâmetros; simulações enviam cópias dos valores usados, além dos IDs opcionais. Não há autenticação adicional: as rotas seguem a aplicação local existente. Não expor a API de cadastros/histórico em servidor público sem controle de acesso.

## Aceitação automatizada

Exemplo da ADR: produção exata 18,685; preço 46,37; lucro 13,91; margem 30%. Cobrir kits, múltiplas unidades, tarifa por pedido/unidade, embalagem única, impostos/pagamento, perda e montagem, arredondamento para cima, venda direta, concorrentes nas quatro classificações, tarifas vencidas, fronteiras de faixa, dados inválidos, histórico imutável, API e paridade Python/navegador.
