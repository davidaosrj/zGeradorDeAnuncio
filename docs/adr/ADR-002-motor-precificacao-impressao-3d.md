# ADR-002 — Motor de Precificação para Impressão 3D

**Status:** Aceita — implementação inicial

**Data:** 08/10/2026

**Projeto:** Sistema de Gestão e Precificação de Impressão 3D

**Módulo:** Cálculo de Custos, Precificação e Rentabilidade

**Versão:** 1.0

## 1. Contexto

O projeto necessita de um motor de cálculo para determinar o preço de venda de produtos fabricados por impressão 3D, considerando custos de matéria-prima, utilização de equipamentos, energia elétrica, perdas de produção, embalagem, taxas dos marketplaces e margem de lucro desejada.

O módulo deverá atender principalmente à comercialização de produtos fabricados em impressoras FDM, incluindo PLA, PETG, ABS e outros materiais.

Atualmente, a precificação é realizada com base em uma planilha de custos que considera:

- Peso da peça em gramas.
- Preço do filamento por quilograma.
- Tempo de impressão em horas.
- Custo operacional da impressora por hora.
- Consumo e custo de energia elétrica.
- Percentual de reserva para falhas.
- Custo de embalagem.
- Comissão percentual do marketplace.
- Tarifa fixa por pedido ou unidade, conforme as regras da plataforma.
- Margem de lucro desejada.

O sistema deverá permitir comparar o preço calculado com preços praticados no mercado e identificar automaticamente produtos economicamente viáveis.

## 2. Decisão arquitetural

Será implementado um **motor de precificação independente das interfaces e dos marketplaces**, responsável pelos cálculos financeiros e pela aplicação das regras comerciais.

A arquitetura será modular, permitindo integrar diferentes plataformas de vendas sem modificar o núcleo de cálculo.

### Componentes principais

**Pricing Engine**

Responsável por calcular custos, preços de equilíbrio, preços sugeridos, margens e rentabilidade.

**Material Catalog**

Gerencia materiais, fabricantes, tipos de filamento, cores e custo por quilograma.

**Printer Profile**

Armazena características e custos operacionais das impressoras utilizadas.

**Marketplace Fee Engine**

Gerencia comissões, tarifas fixas, regras por categoria, faixas de preço e demais cobranças.

**Product Costing**

Gerencia os dados de fabricação dos produtos, incluindo peso, tempo, suportes, perdas e embalagem.

**Market Comparison**

Compara o preço sugerido com os valores encontrados em anúncios concorrentes, mantendo fonte e data de coleta.

**Pricing Simulation**

Permite simular diferentes cenários de produção, preços, margens e marketplaces.

## 3. Parâmetros iniciais

| Parâmetro | Valor padrão |
|---|---:|
| Preço do filamento | R$ 120,00/kg |
| Custo da impressora | R$ 2,00/h |
| Energia elétrica | R$ 0,25/h |
| Reserva para falhas | 10% |
| Embalagem | R$ 4,00 |
| Comissão Shopee | 20% |
| Tarifa fixa Shopee | R$ 4,50 |
| Margem de lucro desejada | 30% |

Os valores são parâmetros iniciais do projeto e não devem ser codificados diretamente nas fórmulas.

As tarifas de marketplace devem ser configuráveis, versionadas e atualizadas conforme as regras contratuais vigentes.

A tarifa de R$ 4,50 da Shopee será utilizada como configuração inicial informada pelo operador, sem presumir que se aplique a todos os pedidos ou categorias.

## 4. Fórmulas de cálculo

### 4.1. Custo do material

```text
custo_material =
    (peso_gramas / 1000) * preco_filamento_kg
```

O peso informado deverá representar o consumo total estimado de filamento, incluindo suportes e demais estruturas descartáveis.

### 4.2. Custo operacional da impressora

```text
custo_maquina =
    tempo_impressao_horas * custo_maquina_hora
```

### 4.3. Custo de energia

```text
custo_energia =
    tempo_impressao_horas * custo_energia_hora
```

### 4.4. Subtotal de fabricação

```text
subtotal =
    custo_material
    + custo_maquina
    + custo_energia
    + custos_adicionais
```

### 4.5. Reserva para falhas

```text
reserva_falhas =
    subtotal * percentual_falhas
```

### 4.6. Custo total de produção

```text
custo_producao =
    subtotal
    + reserva_falhas
    + custo_embalagem
```

O custo de embalagem será contabilizado conforme a quantidade de embalagens efetivamente necessárias para o pedido.

### 4.7. Preço de equilíbrio

Considerando comissão percentual e tarifa fixa:

```text
preco_equilibrio =
    (custo_producao + tarifa_fixa)
    / (1 - comissao_percentual)
```

Esse é o preço mínimo para que o resultado operacional calculado seja zero, antes de custos ou tributos não configurados.

### 4.8. Preço de venda com margem desejada

A margem será definida como percentual da receita bruta de venda.

```text
preco_venda =
    (custo_producao + tarifa_fixa)
    / (1 - comissao_percentual - margem_desejada)
```

**Regra obrigatória:** a soma da comissão percentual e da margem desejada deverá ser inferior a 100%.

### 4.9. Lucro operacional estimado

```text
lucro =
    preco_venda
    - (preco_venda * comissao_percentual)
    - tarifa_fixa
    - custo_producao
```

### 4.10. Margem efetiva

```text
margem_efetiva =
    (lucro / preco_venda) * 100
```

### 4.11. Fator multiplicador

```text
fator_multiplicador =
    preco_venda / custo_producao
```

O fator multiplicador efetivo poderá variar entre produtos, especialmente devido à tarifa fixa.

Não deverá ser adotado um multiplicador universal sobre o peso ou o custo do filamento.

## 5. Exemplo de cálculo

Produto: dinossauro articulado.

| Entrada | Valor |
|---|---:|
| Peso | 55 g |
| Tempo de impressão | 3 horas |
| Filamento | R$ 120/kg |
| Máquina | R$ 2/h |
| Energia | R$ 0,25/h |
| Falhas | 10% |
| Embalagem | R$ 4 |
| Comissão | 20% |
| Tarifa fixa | R$ 4,50 |
| Margem desejada | 30% |

**Cálculo:**

```text
Material = 55 / 1000 * 120
         = R$ 6,60

Máquina = 3 * 2,00
        = R$ 6,00

Energia = 3 * 0,25
        = R$ 0,75

Subtotal = R$ 13,35

Reserva para falhas = R$ 1,335

Custo total = 13,35 + 1,335 + 4,00
            = R$ 18,685

Preço calculado =
    (18,685 + 4,50) / (1 - 0,20 - 0,30)

Preço calculado = R$ 46,37
```

Preço comercial sugerido: **R$ 46,90**, respeitando a margem mínima configurada.

O arredondamento comercial deverá ocorrer para cima quando necessário para preservar a margem.

## 6. Regras específicas dos marketplaces

### Shopee

O módulo deverá suportar:

- Comissão percentual configurável.
- Tarifa fixa configurável.
- Tarifas por categoria e faixa de preço.
- Campanhas promocionais.
- Descontos subsidiados pelo vendedor.
- Custos adicionais por pedido.
- Quantidade de unidades por pedido.
- Distribuição dos custos fixos entre os itens.

### Mercado Livre

O módulo deverá suportar:

- Tipo de anúncio.
- Categoria do produto.
- Comissão percentual.
- Custos fixos aplicáveis.
- Participação do vendedor no frete.
- Custos de logística e fulfillment.
- Regras específicas por faixa de preço.

As regras financeiras de cada marketplace serão independentes.

### Venda direta

Deverá permitir:

- Ausência de comissão de marketplace.
- Tarifas de meios de pagamento.
- Custos de entrega.
- Descontos comerciais.
- Margem personalizada.

## 7. Precificação de kits

O sistema deverá permitir agrupar diferentes produtos em um único anúncio.

Exemplo:

**Kit de pistas e lançador**

- 1 lançador.
- 2 pistas.
- 6 conectores.
- 1 embalagem.

O custo de produção do kit será a soma dos custos de seus componentes, acrescida dos custos de montagem, embalagem e demais despesas aplicáveis.

A tarifa fixa deverá ser aplicada conforme a unidade de cobrança estabelecida pelo marketplace, evitando duplicidade quando uma única tarifa for cobrada por pedido.

```text
custo_kit =
    soma(custos_componentes)
    + custo_montagem
    + embalagem_kit
```

```text
preco_kit =
    (custo_kit + tarifas_fixas_aplicaveis)
    / (1 - comissao - margem_desejada)
```

## 8. Comparação de mercado

O sistema deverá armazenar:

- Nome do produto.
- Categoria.
- Marketplace.
- URL do anúncio.
- Preço anunciado.
- Frete e descontos conhecidos.
- Quantidade de vendas exibida, quando disponível.
- Data e horário da coleta.
- Peso e dimensões, quando informados.
- Preço sugerido pelo motor.
- Margem estimada ao igualar o preço concorrente.

O sistema não deverá interpretar automaticamente vendas acumuladas como vendas de um período específico.

### Classificação de viabilidade

| Classificação | Critério |
|---|---|
| Alta | Margem efetiva maior ou igual à margem desejada |
| Moderada | Margem positiva, mas inferior à desejada |
| Inviável | Lucro operacional estimado igual ou inferior a zero |
| Indeterminada | Dados essenciais ausentes |

## 9. Modelo de dados inicial

### Material

```text
id
nome
tipo
fabricante
cor
preco_kg
data_atualizacao
```

### Printer

```text
id
modelo
custo_hora
energia_hora
status
```

### Product

```text
id
sku
nome
categoria
peso_gramas
tempo_impressao_horas
material_id
printer_id
custo_embalagem
custos_adicionais
```

### MarketplaceFeeRule

```text
id
marketplace
categoria
tipo_anuncio
comissao_percentual
tarifa_fixa
base_cobranca
preco_minimo
preco_maximo
vigencia_inicio
vigencia_fim
```

### PricingResult

```text
product_id
marketplace
custo_material
custo_maquina
custo_energia
reserva_falhas
custo_producao
tarifas_marketplace
preco_equilibrio
preco_calculado
preco_comercial
lucro_estimado
margem_efetiva
fator_multiplicador
data_calculo
```

Os resultados deverão armazenar uma cópia dos parâmetros utilizados, garantindo rastreabilidade histórica mesmo após alterações de tarifas ou custos.

## 10. Arquitetura de implementação

O motor de precificação deverá funcionar independentemente do frontend.

Fluxo lógico:

```text
Cadastro de produto
        |
        v
Dados de impressão
        |
        v
Material + Perfil da impressora
        |
        v
Motor de custos
        |
        v
Regras do marketplace
        |
        v
Motor de precificação
        |
        v
Análise de margem e lucro
        |
        v
Comparação com concorrentes
        |
        v
Preço comercial sugerido
```

### Diretrizes técnicas

- Cálculos financeiros no backend.
- Utilização de aritmética decimal exata, evitando `float` para valores monetários.
- Armazenamento de moeda e unidade monetária.
- Percentuais normalizados.
- Separação entre custo por unidade e custo por pedido.
- Arredondamento financeiro explícito.
- Versionamento de regras comerciais.
- Registro dos parâmetros de cada simulação.
- API independente da interface gráfica.
- Testes unitários para fórmulas e regras.

## 11. Critérios de aceitação

A implementação será considerada funcional quando:

1. Calcular corretamente o custo de material por peso.
2. Calcular os custos operacionais pelo tempo de impressão.
3. Aplicar a reserva para falhas.
4. Considerar embalagem e despesas adicionais.
5. Aplicar comissão percentual e tarifa fixa.
6. Calcular preço de equilíbrio.
7. Calcular preço de venda para a margem desejada.
8. Calcular lucro e margem efetiva para qualquer preço informado.
9. Suportar kits e múltiplas unidades por pedido.
10. Diferenciar as tarifas da Shopee e do Mercado Livre.
11. Comparar preços próprios com preços de concorrentes.
12. Preservar o histórico dos cálculos.
13. Rejeitar configurações matematicamente inválidas.
14. Manter precisão monetária e arredondamento consistente.

## 12. Consequências da decisão

### Positivas

- Padronização da precificação.
- Redução de erros de cálculo.
- Identificação de produtos com baixa rentabilidade.
- Simulação de diferentes estratégias de venda.
- Facilidade para atualizar tarifas dos marketplaces.
- Reutilização do motor em aplicações web e mobile.
- Maior rastreabilidade financeira.

### Negativas e riscos

- Necessidade de atualização frequente das regras dos marketplaces.
- Dependência da qualidade dos dados informados pelo fatiador.
- Variação dos custos reais entre impressoras.
- Possíveis diferenças entre custos estimados e custos efetivos.
- Necessidade de tratar corretamente tarifas por pedido, unidade e faixa de preço.

## 13. Evoluções futuras

- Importação de informações do Orca Slicer e Creality Print.
- Leitura de peso e tempo estimados a partir de arquivos de projeto ou relatórios de fatiamento.
- Importação de custos de pedidos reais.
- Integração com Shopee e Mercado Livre por APIs autorizadas.
- Análise de produtos concorrentes.
- Histórico de preços de filamentos.
- Precificação automática de kits.
- Análise de lucratividade por SKU.
- Simulação de descontos promocionais.
- Dashboard de produtos mais rentáveis.
- Comparação entre diferentes impressoras.
- Cálculo de capacidade produtiva e prazo de fabricação.

## 14. Decisão final

Adotar um motor centralizado, configurável e independente para calcular os custos e os preços de produtos fabricados por impressão 3D.

A precificação deverá considerar obrigatoriamente o custo de fabricação, as tarifas percentuais e fixas dos canais de venda, os custos adicionais e a margem desejada.

O sistema deverá apresentar não apenas o preço sugerido, mas também o lucro operacional estimado, a margem efetiva e o fator multiplicador.

**Status final:** Aceita — implementação inicial conforme SPEC-006 e SPEC-007. As integrações e automações da seção 13 permanecem evoluções futuras.


## 15. Implementação inicial e adaptação ao GitHub Pages

A solicitação de implementação aprovou esta decisão. Os contratos e critérios verificáveis estão em [SPEC-006](../specs/SPEC-006-motor-precificacao-impressao-3d.md) e [SPEC-007](../specs/SPEC-007-interface-precificacao-impressao-3d.md).

A aplicação local usa motor Python com `Decimal`, API independente e SQLite. Para o site GitHub Pages já utilizado pelo projeto, existe também motor no navegador com aritmética racional exata `BigInt`, submetido a testes de paridade. Esta é uma adaptação explícita da diretriz de cálculos exclusivamente no backend: o modo estático não depende de servidor e persiste no navegador, com exportação para backup.

A primeira versão seleciona regras comerciais explicitamente e valida faixa/vigência, sem consultar taxas externas. O passo de arredondamento comercial é configurável; o exemplo de R$ 46,90 continua sendo escolha comercial, não uma terminação obrigatória. Histórico e revisões preservam parâmetros utilizados.

## 16. Preenchimento por link no navegador

A [SPEC-008](../specs/SPEC-008-preenchimento-automatico-concorrentes.md) adiciona leitura automática de dados disponíveis de anúncios Shopee/Mercado Livre por extensão do navegador, compatível com GitHub Pages. A extensão é instalada pelo operador e não requer senhas no aplicativo. Confirmações de login, bloqueios e variações permanecem explícitos; o motor calcula apenas com os dados efetivamente preenchidos. Integrações diretas com APIs externas continuam uma evolução distinta.
