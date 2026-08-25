# ADR-002 — Simulador de ROAS Seguro para Shopee e Mercado Livre

## Status

Proposto

## Data

2026-08-25

## Contexto

O gerador de anúncios será ampliado com um simulador de publicidade para Shopee e Mercado Livre. O recurso não deve apenas exibir o ROAS de uma campanha. Ele deve considerar a economia real do produto, o estoque disponível, o crédito destinado aos anúncios, o orçamento diário e os resultados observados após a ativação.

Uma campanha pode apresentar faturamento e ROAS aparentemente positivos e ainda gerar prejuízo quando comissão, tarifa fixa, impostos, custo do produto, embalagem, frete, descontos, devoluções e gasto publicitário não são considerados juntos.

As taxas e regras dos marketplaces mudam por categoria, tipo de anúncio, programa logístico, faixa de preço, campanha, conta e data. Portanto, o sistema não poderá embutir uma taxa universal como verdade permanente.

## Objetivo

Criar um simulador que:

- calcule margem de contribuição antes dos anúncios;
- calcule ROAS e ACOS de equilíbrio;
- acrescente uma margem de segurança configurável para proteger o lucro;
- limite o orçamento pelo crédito disponível, fluxo de caixa e estoque vendável;
- estime vendas, consumo de estoque e duração do crédito em cenários;
- acompanhe gasto, pedidos, receita e taxa de conversão após a ativação;
- sugira manter, reduzir, pausar ou aumentar gradualmente o orçamento;
- explique cada recomendação e os dados usados;
- funcione sem Ollama, com cálculos determinísticos;
- use Ollama apenas para explicar resultados em linguagem natural, nunca para fazer os cálculos financeiros.

## Fora do escopo inicial

- Garantir lucro ou desempenho futuro.
- Alterar automaticamente campanhas na Shopee ou no Mercado Livre.
- Consultar saldo bancário ou conceder crédito.
- Substituir a contabilidade fiscal do vendedor.
- Inferir taxas, custos ou estoque ausentes.
- Misturar métricas de atribuição incompatíveis entre marketplaces.

## Decisão

Será criado um módulo determinístico de simulação e monitoramento, independente do gerador de textos e imagens. O frontend e o MCP consumirão o mesmo núcleo de cálculo para evitar divergência de resultados.

O módulo trabalhará com perfis separados por marketplace e produto. Cada valor financeiro deverá indicar origem, data de vigência e estado de confirmação. Campo não confirmado permanecerá vazio e impedirá uma recomendação classificada como segura.

O sistema produzirá recomendações, mas a decisão e a alteração da campanha continuarão sob responsabilidade do usuário.

---

# 1. Princípios de segurança

## 1.1 Dados confirmados

Taxas, custos, preço, estoque e resultados devem vir de:

1. dados informados e confirmados pelo usuário;
2. exportação ou API oficial do marketplace, quando uma integração futura existir;
3. dados importados de relatório, com período e janela de atribuição identificados.

Não será permitido inventar comissão, conversão, CPC, custo, imposto ou quantidade em estoque.

## 1.2 Taxas configuráveis e datadas

Cada taxa terá, no mínimo:

```json
{
  "valor": 0.0,
  "unidade": "percentual",
  "origem": "informado_pelo_usuario",
  "vigente_desde": "2026-08-25",
  "confirmado": true
}
```

Taxas antigas exibirão aviso de revisão. A validade padrão será configurável. Atualizar uma taxa não alterará retroativamente simulações salvas.

## 1.3 Separação entre cálculo e explicação

- Python executará todas as fórmulas com aritmética decimal.
- O modo offline exibirá resultado e recomendação por regras determinísticas.
- O Ollama poderá resumir e explicar o resultado já calculado.
- A resposta do Ollama não poderá substituir números, alterar fórmulas ou preencher dados ausentes.

## 1.4 Sem promessa de resultado

Toda projeção será identificada como cenário, não como previsão garantida. A interface mostrará que ROAS histórico não assegura ROAS futuro.

---

# 2. Entradas obrigatórias por produto e marketplace

## 2.1 Identificação

- marketplace: Shopee ou Mercado Livre;
- SKU;
- nome do produto;
- moeda;
- preço de venda unitário;
- estoque físico;
- estoque reservado;
- estoque de segurança;
- prazo de reposição em dias.

O estoque vendável será:

```text
estoque_vendavel = estoque_fisico - estoque_reservado - estoque_seguranca
```

## 2.2 Custo unitário

- custo de aquisição ou fabricação;
- embalagem;
- etiqueta e preparação;
- imposto por venda, percentual ou fixo;
- comissão do marketplace;
- tarifa fixa por unidade;
- tarifa de pagamento, quando aplicável;
- custo ou subsídio de frete pago pelo vendedor;
- desconto ou cupom financiado pelo vendedor;
- participação em programa comercial;
- provisão para cancelamentos, devoluções, perdas e reembolsos;
- outros custos variáveis.

Custos fixos mensais poderão ser informados para análise gerencial, mas serão separados dos custos variáveis usados no ROAS de equilíbrio. Se o usuário desejar rateá-los, deverá fornecer o critério e o volume esperado.

## 2.3 Campanha e caixa

- crédito total disponível para anúncios;
- limite diário de crédito;
- orçamento diário desejado;
- duração ou horizonte da simulação;
- reserva mínima de caixa;
- ROAS esperado ou CPA esperado, quando houver histórico;
- margem líquida mínima desejada;
- limite máximo de aumento diário de orçamento.

## 2.4 Dados posteriores à ativação

- data e hora de início;
- gasto publicitário;
- impressões;
- cliques;
- pedidos atribuídos;
- unidades atribuídas;
- receita atribuída bruta;
- descontos e reembolsos ocorridos;
- cancelamentos e devoluções;
- vendas totais do produto;
- sessões ou visitas, quando disponíveis;
- janela de atribuição usada pelo marketplace;
- data de atualização do relatório.

Receita atribuída e receita total nunca serão misturadas silenciosamente.

---

# 3. Fórmulas financeiras

Os cálculos monetários usarão `Decimal`, arredondamento explícito e moeda do perfil.

## 3.1 Custos percentuais

```text
custos_percentuais = preco_venda × soma_das_taxas_percentuais
```

## 3.2 Margem de contribuição antes dos anúncios

```text
margem_contribuicao_unitaria =
    preco_venda
    - custo_produto
    - embalagem
    - custos_percentuais
    - tarifas_fixas
    - frete_pago_vendedor
    - desconto_pago_vendedor
    - provisao_devolucoes_perdas
    - outros_custos_variaveis
```

```text
margem_contribuicao_percentual =
    margem_contribuicao_unitaria / preco_venda
```

Se a margem de contribuição for menor ou igual a zero, a interface bloqueará a classificação “segura” e recomendará revisar preço e custos antes de anunciar.

## 3.3 ACOS e ROAS de equilíbrio

```text
ACOS_equilibrio = margem_contribuicao_unitaria / preco_venda
```

```text
ROAS_equilibrio = preco_venda / margem_contribuicao_unitaria
```

No ponto de equilíbrio, toda a margem disponível antes dos anúncios é consumida pela publicidade.

## 3.4 ROAS de segurança

O usuário informará a margem líquida mínima que deseja preservar depois dos anúncios:

```text
lucro_reservado_unitario = preco_venda × margem_liquida_minima
```

```text
CPA_maximo_seguro =
    margem_contribuicao_unitaria - lucro_reservado_unitario
```

```text
ROAS_minimo_seguro = preco_venda / CPA_maximo_seguro
```

O cálculo somente será válido quando `CPA_maximo_seguro > 0`. Quanto maior o ROAS mínimo escolhido, menor tende a ser o espaço para gasto por venda e maior a proteção da margem, embora isso possa reduzir alcance e volume.

## 3.5 Métricas realizadas

```text
ROAS_real = receita_atribuida_liquida / gasto_ads
```

```text
ACOS_real = gasto_ads / receita_atribuida_liquida
```

```text
CPA_real = gasto_ads / pedidos_atribuidos
```

```text
taxa_conversao_clique = pedidos_atribuidos / cliques
```

Quando sessões forem fornecidas:

```text
taxa_venda_sessao = pedidos_totais / sessoes
```

Taxa por clique e taxa por sessão terão nomes distintos e não serão comparadas como se fossem a mesma métrica.

## 3.6 Resultado após anúncios

```text
resultado_atribuido =
    receita_atribuida_liquida
    - custos_variaveis_das_unidades_atribuidas
    - gasto_ads
```

O painel também poderá mostrar resultado combinado, incluindo vendas orgânicas, mas sempre separado do resultado atribuído à publicidade.

---

# 4. Orçamento limitado por crédito, estoque e caixa

## 4.1 Crédito diário disponível

```text
credito_diario_disponivel =
    credito_ads_restante / dias_restantes
```

## 4.2 Ritmo máximo de estoque

```text
unidades_maximas_dia =
    estoque_vendavel / horizonte_dias
```

```text
orcamento_limitado_estoque =
    unidades_maximas_dia × CPA_maximo_seguro
```

## 4.3 Orçamento diário recomendado

```text
orcamento_diario_recomendado = minimo(
    orcamento_desejado,
    limite_diario_credito,
    credito_diario_disponivel,
    orcamento_limitado_estoque,
    limite_fluxo_caixa
)
```

O painel exibirá qual limite foi determinante. Se não houver reposição prevista e a cobertura de estoque for baixa, a recomendação será reduzir o orçamento mesmo quando o ROAS estiver bom.

## 4.4 Cobertura e alerta de ruptura

```text
cobertura_estoque_dias =
    estoque_vendavel / vendas_totais_medias_dia
```

Se a cobertura for menor que o prazo de reposição somado à margem logística configurada, o sistema alertará risco de ruptura.

## 4.5 Cenários

O simulador apresentará três cenários:

- pessimista;
- base;
- otimista.

Cada cenário informará explicitamente as hipóteses de CPA, conversão, cancelamento e devolução. Quando não houver histórico, os campos ficarão pendentes; o sistema não criará percentuais arbitrários.

---

# 5. Avaliação após a ativação

## 5.1 Estados da campanha

```text
SEM_DADOS
EM_APRENDIZADO
SAUDAVEL
ATENCAO
RISCO_DE_PREJUIZO
RISCO_DE_ESTOQUE
CREDITO_INSUFICIENTE
```

## 5.2 Maturação dos dados

Uma venda pode ser atribuída, cancelada ou devolvida depois do clique. Por isso, o sistema armazenará:

- dados provisórios;
- dados maturados;
- janela de atribuição;
- data da última atualização.

Recomendações fortes não serão emitidas com dados ainda incompletos. O período mínimo, o número mínimo de cliques e o número mínimo de pedidos serão configuráveis por marketplace. Os padrões iniciais serão conservadores e apresentados como parâmetros, não como regras universais.

## 5.3 Regras de sugestão

- Se os dados obrigatórios estiverem ausentes, solicitar complementação e não declarar segurança.
- Se a amostra ainda for insuficiente, manter observação e evitar mudanças repetidas.
- Se `CPA_real > CPA_maximo_seguro` ou o resultado atribuído maturado for negativo, sugerir redução ou pausa e indicar o custo responsável.
- Se `ROAS_real < ROAS_equilibrio`, classificar como risco de prejuízo.
- Se o ROAS estiver entre o equilíbrio e o mínimo seguro, classificar como atenção: a campanha pode não preservar a margem desejada.
- Se `ROAS_real >= ROAS_minimo_seguro`, houver caixa e cobertura de estoque, sugerir manutenção ou aumento gradual.
- Se o estoque estiver próximo da ruptura, sugerir redução mesmo com ROAS alto.
- Se o crédito restante não cobrir o horizonte, sugerir novo limite diário; nunca sugerir aporte sem mostrar o valor e a duração esperada.
- Se a conversão cair, investigar preço, anúncio, prazo, reputação, concorrência e página do produto antes de simplesmente aumentar o orçamento.

O aumento gradual respeitará um percentual máximo configurável e nunca será executado automaticamente.

## 5.4 Comparação antes e depois

O painel comparará períodos equivalentes, informando:

- taxa de venda antes e depois da ativação;
- vendas orgânicas e atribuídas;
- gasto incremental;
- resultado incremental estimado;
- mudanças de preço, estoque, promoção e sazonalidade registradas.

O sistema alertará que uma comparação simples antes/depois não prova causalidade quando outras condições mudaram.

---

# 6. Interface do usuário

O pequeno frontend ganhará uma área **Simulador de ROAS**, com quatro etapas.

## Etapa 1 — Produto e custos

Formulário para preço, custos, taxas, estoque e reposição. Shopee e Mercado Livre terão perfis independentes para o mesmo SKU.

## Etapa 2 — Caixa e campanha

Formulário para crédito total, orçamento diário, horizonte, margem mínima desejada e histórico de CPA ou ROAS.

## Etapa 3 — Simulação

Exibição de:

- margem antes dos anúncios;
- CPA máximo seguro;
- ACOS de equilíbrio;
- ROAS de equilíbrio;
- ROAS mínimo seguro;
- orçamento limitado por crédito;
- orçamento limitado por estoque;
- duração estimada do crédito;
- cobertura estimada de estoque;
- cenários pessimista, base e otimista.

## Etapa 4 — Pós-ativação

Entrada ou importação de métricas reais, comparação com a simulação e recomendação explicada.

Cada resultado exibirá:

- fórmula;
- valores usados;
- origem e data dos dados;
- pendências;
- nível de confiança operacional;
- motivo da sugestão.

Não será usada apenas uma cor como indicação. Estados terão cor, ícone e texto para acessibilidade.

---

# 7. MCP

O MCP disponibilizará inicialmente ferramentas somente de cálculo e consulta:

```text
calcular_economia_produto
calcular_roas_equilibrio
simular_orcamento_ads
avaliar_campanha_ativa
sugerir_ajuste_orcamento
```

As respostas serão JSON estruturado e incluirão:

```json
{
  "resultado": {},
  "recomendacao": {},
  "hipoteses": [],
  "pendencias": [],
  "alertas": [],
  "fontes_dos_dados": [],
  "versao_formula": "1.0.0"
}
```

Não haverá, nesta ADR, ferramenta para ativar, pausar ou alterar campanha no marketplace.

---

# 8. Modelo de dados sugerido

```json
{
  "marketplace": "shopee",
  "sku": "SKU0011",
  "moeda": "BRL",
  "preco_venda": null,
  "custos": {
    "produto": null,
    "embalagem": null,
    "imposto_percentual": null,
    "comissao_percentual": null,
    "tarifa_fixa": null,
    "frete_vendedor": null,
    "desconto_vendedor": null,
    "provisao_devolucoes": null,
    "outros": null
  },
  "estoque": {
    "fisico": null,
    "reservado": 0,
    "seguranca": 0,
    "prazo_reposicao_dias": null
  },
  "campanha": {
    "credito_total": null,
    "limite_diario_credito": null,
    "orcamento_diario_desejado": null,
    "horizonte_dias": null,
    "margem_liquida_minima_percentual": null
  },
  "vigencia": {
    "taxas_confirmadas_em": null,
    "origem": null
  }
}
```

Valores `null` são intencionais e não poderão ser substituídos por estimativas do modelo de linguagem.

---

# 9. Arquitetura

```text
src/gerador_anuncios/
├── roas/
│   ├── models.py
│   ├── calculator.py
│   ├── simulator.py
│   ├── evaluator.py
│   ├── recommender.py
│   └── validators.py
├── mcp_server.py
└── frontend/
```

Responsabilidades:

- `calculator`: fórmulas puras e determinísticas;
- `simulator`: cenários e limites de estoque, crédito e caixa;
- `evaluator`: consolidação dos dados realizados;
- `recommender`: regras explicáveis de sugestão;
- `validators`: dados ausentes, datas, divisões por zero e inconsistências;
- frontend: coleta e apresentação, sem repetir regra financeira;
- MCP: contrato estruturado sobre o mesmo núcleo.

As versões das fórmulas serão gravadas nas simulações para permitir auditoria futura.

---

# 10. Controles adicionais

- Valores monetários não usarão `float` binário.
- Percentuais serão rotulados e convertidos explicitamente; `15%` não poderá ser confundido com `15` ou `0,15`.
- Valores negativos só serão aceitos nos campos em que façam sentido.
- Nenhuma divisão por zero produzirá recomendação.
- Fuso padrão: `America/Sao_Paulo`.
- Dados desatualizados serão sinalizados.
- Alterações de preço ou taxas abrirão uma nova versão da simulação.
- Toda sugestão terá registro de entrada, fórmula, resultado, data e versão.
- Dados importados serão preservados sem reescrever o arquivo original.
- Segredos e tokens de APIs futuras não serão armazenados no repositório.

---

# 11. Critérios de aceite

Uma entrega será aceita quando:

- o mesmo conjunto de dados produzir o mesmo resultado offline e via MCP;
- Shopee e Mercado Livre mantiverem perfis de custos separados;
- nenhuma taxa desconhecida for preenchida automaticamente;
- margem, CPA máximo, ACOS e ROAS de equilíbrio forem demonstráveis por teste unitário;
- o orçamento recomendado nunca exceder crédito, caixa ou limite de estoque;
- estoque zero bloquear recomendação de investimento;
- margem anterior aos anúncios menor ou igual a zero bloquear status seguro;
- dados insuficientes gerarem `SEM_DADOS` ou `EM_APRENDIZADO`;
- métricas provisórias e maturadas aparecerem separadamente;
- receita atribuída e total não forem misturadas;
- a recomendação informar claramente seu motivo;
- nenhuma campanha for alterada sem ação explícita do usuário;
- testes cobrirem valores nulos, percentuais, arredondamento, devoluções e divisão por zero.

---

# 12. Melhores práticas adotadas da pesquisa

1. Definir a meta com base na economia real e no histórico da campanha, não em um número genérico.
2. Entender a relação inversa entre ROAS e ACOS e usar o ponto de equilíbrio como limite financeiro.
3. Separar receita atribuída de vendas totais e registrar a janela de atribuição.
4. Aguardar amostra e maturação suficientes antes de reagir a oscilações curtas.
5. Fazer mudanças graduais, documentadas e limitadas.
6. Considerar estoque, reposição, caixa e crédito antes de aumentar orçamento.
7. Revisar taxas oficiais periodicamente e manter sua data de vigência.
8. Trabalhar com cenários e provisões para devoluções, cancelamentos e descontos.
9. Explicar a recomendação e manter decisão humana.

## Fontes oficiais consultadas

- [Google Ads — Sobre os lances de ROAS desejado](https://support.google.com/google-ads/answer/6268637?hl=pt-BR): orientação sobre metas baseadas em valor de conversão e o efeito da meta de ROAS no volume.
- [Amazon Ads — Guia de ACOS](https://advertising.amazon.com/library/guides/acos-advertising-cost-of-sales): relação entre gasto publicitário, receita atribuída, ACOS e rentabilidade.
- [Mercado Livre — Quanto custa vender um produto](https://www.mercadolivre.com.br/ajuda/Quanto-custa-vender-um-produto_870): referência oficial para conferir custos vigentes de venda.
- [Mercado Livre Developers — Preços de produtos e tarifas](https://developers.mercadolivre.com.br/pt_br/precos-de-produtos-e-tarifas): referência para uma futura obtenção de tarifas por integração oficial.
- [Shopee — Central de Educação do Vendedor](https://seller.shopee.com.br/edu): referência oficial para regras, campanhas e taxas vigentes da conta.

As fontes foram consultadas em 2026-08-25. Nenhum percentual de taxa foi copiado para o código, pois tarifas e condições podem mudar e variar por conta e anúncio.

---

# Consequências

## Positivas

- Reduz o risco de decidir apenas por faturamento ou ROAS isolado.
- Torna explícito o custo máximo de aquisição por pedido.
- Evita investir em produtos sem margem ou sem estoque suficiente.
- Permite operar mesmo com Ollama indisponível.
- Oferece rastreabilidade para taxas, fórmulas e recomendações.

## Negativas

- Exige que o usuário mantenha custos e taxas atualizados.
- Resultados dependem da qualidade e maturação dos relatórios importados.
- A primeira configuração terá mais campos do que uma calculadora simples.
- Sem integração oficial, métricas posteriores à ativação dependerão de entrada manual ou importação.

## Riscos residuais

- Mudanças de algoritmo, concorrência, sazonalidade e reputação podem alterar o desempenho.
- Atribuição dos marketplaces pode não representar incrementalidade real.
- Custos esquecidos pelo usuário podem superestimar a margem.
- Uma boa campanha pode acelerar ruptura de estoque.

Esses riscos serão exibidos no frontend e não poderão ser eliminados apenas por cálculo.

