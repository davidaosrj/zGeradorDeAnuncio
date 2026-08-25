# ADR-001 — Gerador Automatizado de Anúncios a Partir de Diretório de Imagens

## Status

Aprovado

## Objetivo

Criar um sistema genérico capaz de receber um diretório contendo fotografias reais de um determinado produto e gerar automaticamente:

* título do anúncio;
* descrição completa;
* descrição resumida;
* dados estruturados do produto;
* imagens comerciais individuais;
* pacote ZIP final.

O sistema deve funcionar para diferentes produtos sem depender de informações fixas de um anúncio específico.

---

# 1. PRINCÍPIO FUNDAMENTAL

## A fotografia real é a fonte visual de verdade

As fotografias existentes no diretório de entrada representam o produto real.

O sistema nunca deve modificar características físicas do produto.

Não alterar:

* geometria;
* formato;
* número de peças;
* quantidade de componentes;
* furos;
* encaixes;
* conectores;
* saliências;
* proporções;
* elementos funcionais;
* posição relativa entre componentes;
* cores definidas como fixas.

É permitido:

* remover fundo;
* substituir fundo por branco;
* remover objetos do ambiente;
* melhorar iluminação;
* melhorar contraste;
* melhorar nitidez;
* corrigir enquadramento;
* centralizar o produto;
* adicionar textos;
* adicionar medidas confirmadas;
* adicionar identidade visual.

---

# 2. ESTRUTURA DE ENTRADA

O sistema deverá receber um diretório contendo todas as imagens disponíveis do produto.

Exemplo:

```text
/produto
│
├── foto_01.jpg
├── foto_02.jpg
├── foto_03.jpg
├── foto_04.png
└── produto.json
```

O arquivo `produto.json` é opcional.

As imagens são obrigatórias.

---

# 3. ARQUIVO OPCIONAL produto.json

Sempre que houver informações técnicas conhecidas, elas deverão ser informadas neste arquivo.

Exemplo:

```json
{
  "sku": "SKU_0007",
  "nome": "Tampa para tubo de silicone ou PU",
  "quantidade": 1,
  "material": null,
  "medidas": [
    "3,9 cm"
  ],
  "cores_variaveis": [
    "vermelho",
    "verde",
    "azul"
  ],
  "cores_fixas": [],
  "compatibilidade": [
    "Tubos de silicone",
    "Tubos de PU"
  ],
  "itens_inclusos": [
    "1 tampa"
  ],
  "itens_nao_inclusos": [
    "Tubo de silicone",
    "Tubo de PU",
    "Produto químico",
    "Bico aplicador"
  ],
  "beneficios_confirmados": [
    "Ajuda a preservar o conteúdo do tubo por mais tempo"
  ],
  "observacoes": []
}
```

---

# 4. PRIORIDADE DAS INFORMAÇÕES

O sistema deverá utilizar a seguinte ordem de prioridade:

## Prioridade 1

Informações fornecidas explicitamente no:

```text
produto.json
```

## Prioridade 2

Informações textuais fornecidas pelo usuário.

## Prioridade 3

Informações visíveis de forma inequívoca nas fotografias.

## Proibido

Nunca estimar ou inventar:

* medidas;
* peso;
* material;
* resistência;
* temperatura suportada;
* carga máxima;
* quantidade;
* compatibilidade;
* capacidade;
* durabilidade;
* especificações técnicas.

---

# 5. ANÁLISE INICIAL

Ao iniciar o processamento, o sistema deverá analisar todas as imagens disponíveis antes de gerar qualquer arte.

Deverá identificar visualmente:

* produto principal;
* quantidade aparente;
* componentes;
* vistas disponíveis;
* formato;
* cores;
* detalhes construtivos;
* forma de utilização quando demonstrada;
* imagens adequadas para capa;
* imagens adequadas para detalhes;
* imagens adequadas para funcionamento.

Nenhuma característica técnica deve ser inferida apenas por aparência.

---

# 6. MANIFESTO INTERNO DO PRODUTO

Após analisar o diretório, o sistema deverá gerar internamente um manifesto estruturado.

Exemplo:

```json
{
  "produto": {
    "nome": null,
    "sku": null,
    "quantidade": null,
    "material": null,
    "medidas_confirmadas": [],
    "cores_confirmadas": [],
    "compatibilidade_confirmada": [],
    "itens_inclusos": [],
    "itens_nao_inclusos": [],
    "beneficios_confirmados": []
  },
  "visual": {
    "imagem_principal": "foto_01.jpg",
    "imagens_secundarias": [
      "foto_02.jpg",
      "foto_03.jpg"
    ],
    "cor_produto": null,
    "numero_componentes_visiveis": null
  },
  "pendencias": []
}
```

---

# 7. TRATAMENTO DE INFORMAÇÕES AUSENTES

Caso uma informação não esteja confirmada, utilizar:

```text
null
```

ou:

```text
[]
```

Nunca preencher utilizando suposição.

Exemplo incorreto:

```json
{
  "material": "PETG"
}
```

quando o material não tiver sido informado.

Exemplo correto:

```json
{
  "material": null
}
```

---

# 8. QUANDO PERGUNTAR AO USUÁRIO

O sistema deve fazer o mínimo possível de perguntas.

Perguntar somente quando uma informação indispensável impedir a criação correta do anúncio.

Exemplos:

* quantidade do kit não é possível determinar;
* usuário solicitou medidas, mas nenhuma medida foi fornecida;
* existem duas peças visualmente semelhantes e não está claro qual é vendida;
* cor fixa ou variável precisa ser definida.

Caso a informação não seja indispensável, simplesmente omitir.

---

# 9. DESCRIÇÃO DO PRODUTO

O sistema deverá gerar:

```text
descricao_completa.txt
descricao_resumida.txt
titulo.txt
```

Também poderá consolidar tudo em:

```text
anuncio.md
```

---

# 10. ESTRUTURA DA DESCRIÇÃO COMPLETA

A descrição deverá seguir preferencialmente:

```text
NOME DO PRODUTO

Breve apresentação e principal benefício.

O KIT CONTÉM

Quantidade e itens exatos.

MATERIAL

Somente quando confirmado.

MEDIDAS

Somente medidas confirmadas.

CORES

Somente informações confirmadas.

COMPATIBILIDADE

Somente quando confirmada.

BENEFÍCIOS

Somente benefícios razoavelmente confirmados.

IMPORTANTE

Itens não inclusos e observações relevantes.
```

---

# 11. PRODUTOS DE IMPRESSÃO 3D

Somente utilizar referência a impressão 3D quando isso estiver confirmado.

Quando aplicável:

```text
Por ser produzido através de Impressão 3D FDM, podem existir linhas de camada ou pequenas variações superficiais características do processo de fabricação.
```

Nunca presumir que um objeto foi fabricado em impressão 3D somente pela aparência.

---

# 12. IDENTIDADE VISUAL

Marca:

```text
zonegeeklab3D
```

Padrão visual:

```text
fundo branco
produto centralizado
visual limpo
e-commerce profissional
formato quadrado
```

Logo:

```text
zonegeeklab3D
```

Posição padrão:

```text
canto inferior esquerdo
```

Não adicionar:

* logo da Shopee;
* logo do Mercado Livre;
* avaliações inventadas;
* estrelas;
* descontos;
* promoções;
* selos inexistentes;
* certificações não comprovadas.

---

# 13. RESOLUÇÃO

Resolução padrão:

```text
1000 × 1000 px
```

Formato:

```text
PNG
```

Cada imagem deverá ser um arquivo independente.

---

# 14. REGRA CRÍTICA — IMAGENS INDIVIDUAIS

Nunca juntar várias artes dentro de uma mesma imagem.

É proibido gerar:

```text
02_03_04_05_06.png
```

contendo uma grade.

É proibido gerar um mosaico com as seis imagens.

Cada imagem deve existir fisicamente como arquivo próprio.

Formato obrigatório:

```text
01_CAPA.png
02_CONTEUDO.png
03_MEDIDAS.png
04_FUNCIONAMENTO.png
05_DETALHES.png
06_IMPORTANTE.png
```

---

# 15. IMAGEM 01 — CAPA

Arquivo:

```text
01_CAPA.png
```

Objetivo:

Mostrar claramente o produto vendido.

Pode conter:

* nome curto;
* quantidade;
* principal benefício;
* medida principal confirmada;
* compatibilidade confirmada.

Evitar excesso de texto.

O produto deve ser o elemento visual dominante.

---

# 16. IMAGEM 02 — CONTEÚDO

Arquivo:

```text
02_CONTEUDO.png
```

Objetivo:

Mostrar exatamente tudo o que o comprador receberá.

Exemplo:

```text
CONTEÚDO DO KIT

01 UNIDADE
TAMPA PARA TUBO
```

A imagem deverá mostrar somente os componentes vendidos.

Objetos utilizados apenas para demonstração não devem aparecer como itens inclusos.

---

# 17. IMAGEM 03 — MEDIDAS

Arquivo:

```text
03_MEDIDAS.png
```

Objetivo:

Mostrar exclusivamente dimensões confirmadas.

Nunca estimar medidas visualmente.

Caso exista somente uma medida confirmada:

```text
TAMANHO DA PEÇA

3,9 cm
```

Não adicionar outras setas ou dimensões sem informação confirmada.

Caso nenhuma medida tenha sido fornecida, a imagem poderá ser substituída por outra arte informativa ou marcada internamente como não gerável.

---

# 18. IMAGEM 04 — FUNCIONAMENTO

Arquivo:

```text
04_FUNCIONAMENTO.png
```

Objetivo:

Demonstrar:

* montagem;
* encaixe;
* instalação;
* utilização;
* sequência de uso.

Usar fotografias reais sempre que possível.

Exemplo:

```text
COMO UTILIZAR

1. Posicione a peça.
2. Encaixe corretamente.
3. Utilize normalmente.
```

As etapas deverão ser adaptadas ao produto analisado.

Nunca inventar uma forma de montagem que não esteja confirmada.

---

# 19. IMAGEM 05 — DETALHES E BENEFÍCIOS

Arquivo:

```text
05_DETALHES.png
```

Objetivo:

Destacar características reais e benefícios.

Exemplos possíveis:

```text
REUTILIZÁVEL
```

```text
FÁCIL DE UTILIZAR
```

```text
AJUDA A REDUZIR O DESPERDÍCIO
```

```text
AJUDA A PRESERVAR O PRODUTO POR MAIS TEMPO
```

Somente utilizar benefícios compatíveis com o produto e informações confirmadas.

Nunca afirmar:

```text
Indestrutível
```

```text
100% à prova de vazamentos
```

```text
Dura para sempre
```

sem comprovação.

---

# 20. IMAGEM 06 — IMPORTANTE

Arquivo:

```text
06_IMPORTANTE.png
```

Objetivo:

Evitar dúvidas do comprador.

Pode destacar:

```text
IMPORTANTE
```

```text
NÃO ACOMPANHA
```

e mostrar claramente itens utilizados apenas para demonstração.

Exemplo:

```text
NÃO ACOMPANHA:

✕ Tubo
✕ Produto químico
✕ Bico aplicador
```

A lista deverá ser criada dinamicamente para cada produto.

---

# 21. PRESERVAÇÃO DO PRODUTO REAL

Ao gerar ou editar imagens, utilizar as fotografias reais como referência obrigatória.

Não redesenhar o produto livremente.

O produto resultante deve preservar:

```text
silhueta
geometria
quantidade de partes
furos
encaixes
cores fixas
proporções
detalhes funcionais
```

A edição deve melhorar a fotografia, e não criar um produto diferente.

---

# 22. CORES

As cores poderão possuir dois estados.

## Cor fixa

Nunca pode ser modificada.

Exemplo:

```json
{
  "componente": "conector",
  "cor": "azul",
  "tipo": "fixa"
}
```

## Cor variável

Pode ser alterada para representar uma variação comercial.

Exemplo:

```json
{
  "componente": "corpo",
  "cores": [
    "vermelho",
    "verde",
    "azul"
  ],
  "tipo": "variavel"
}
```

Ao gerar uma variação, modificar somente os componentes definidos como variáveis.

---

# 23. SKU

O SKU somente deverá ser utilizado quando informado.

Nunca inventar SKU.

Quando existir:

```text
SKU_0007_01_capa.png
SKU_0007_02_conteudo.png
SKU_0007_03_medidas.png
SKU_0007_04_funcionamento.png
SKU_0007_05_detalhes.png
SKU_0007_06_importante.png
```

Quando não existir:

```text
01_capa.png
02_conteudo.png
03_medidas.png
04_funcionamento.png
05_detalhes.png
06_importante.png
```

---

# 24. DIRETÓRIO DE SAÍDA

Exemplo sem SKU:

```text
/produto
│
├── entrada/
│   ├── foto_01.jpg
│   ├── foto_02.jpg
│   └── foto_03.jpg
│
└── saida/
    ├── anuncio.md
    ├── titulo.txt
    ├── descricao_completa.txt
    ├── descricao_resumida.txt
    ├── produto_analisado.json
    │
    ├── imagens/
    │   ├── 01_capa.png
    │   ├── 02_conteudo.png
    │   ├── 03_medidas.png
    │   ├── 04_funcionamento.png
    │   ├── 05_detalhes.png
    │   └── 06_importante.png
    │
    └── Imagens_Anuncio.zip
```

---

# 25. FLUXO DE PROCESSAMENTO

Fluxo principal:

```text
1. Ler diretório de entrada
        ↓
2. Localizar imagens
        ↓
3. Ler produto.json, se existir
        ↓
4. Analisar todas as fotografias
        ↓
5. Criar manifesto do produto
        ↓
6. Validar informações confirmadas
        ↓
7. Identificar informações ausentes
        ↓
8. Perguntar somente se indispensável
        ↓
9. Gerar título
        ↓
10. Gerar descrição completa
        ↓
11. Gerar descrição resumida
        ↓
12. Preparar fotografias
        ↓
13. Gerar 01_CAPA
        ↓
14. Salvar arquivo
        ↓
15. Gerar 02_CONTEUDO
        ↓
16. Salvar arquivo
        ↓
17. Gerar 03_MEDIDAS
        ↓
18. Salvar arquivo
        ↓
19. Gerar 04_FUNCIONAMENTO
        ↓
20. Salvar arquivo
        ↓
21. Gerar 05_DETALHES
        ↓
22. Salvar arquivo
        ↓
23. Gerar 06_IMPORTANTE
        ↓
24. Salvar arquivo
        ↓
25. Validar arquivos
        ↓
26. Criar ZIP
```

---

# 26. GERAÇÃO SEQUENCIAL

As imagens deverão ser geradas sequencialmente.

Pseudoalgoritmo:

```text
para arte em [
    "01_CAPA",
    "02_CONTEUDO",
    "03_MEDIDAS",
    "04_FUNCIONAMENTO",
    "05_DETALHES",
    "06_IMPORTANTE"
]:

    gerar_apenas(arte)

    validar_resolucao()

    validar_produto()

    validar_textos()

    salvar_png()

    somente_entao:
        continuar_para_proxima()
```

Nunca solicitar ao gerador:

```text
Crie as seis imagens em uma única composição.
```

Nunca solicitar:

```text
Crie uma grade mostrando todas as artes.
```

Cada chamada deverá solicitar exatamente **uma arte**.

---

# 27. PROMPT BASE PARA CADA ARTE

Estrutura conceitual:

```text
Utilize as fotografias reais fornecidas como fonte visual de verdade.

Crie APENAS a arte:
{TIPO_ARTE}

Não crie grade.
Não crie mosaico.
Não mostre outras artes.
A saída deve representar somente uma imagem.

Resolução:
1000 × 1000.

Produto:
{DADOS_CONFIRMADOS}

Itens inclusos:
{ITENS_INCLUSOS}

Itens não inclusos:
{ITENS_NAO_INCLUSOS}

Medidas confirmadas:
{MEDIDAS}

Benefícios confirmados:
{BENEFICIOS}

Preserve exatamente a geometria e os detalhes funcionais do produto real.

Fundo branco.
Visual profissional de e-commerce.
Logo zonegeeklab3D discretamente no canto inferior esquerdo.
```

---

# 28. VALIDAÇÃO AUTOMÁTICA

Antes da entrega, verificar individualmente:

```text
[ ] Existem 6 arquivos independentes
[ ] Todos estão em PNG
[ ] Todos possuem 1000 × 1000 px
[ ] Nenhum arquivo contém mosaico de outras artes
[ ] Produto corresponde às fotografias
[ ] Quantidade está correta
[ ] Medidas são confirmadas
[ ] Nenhuma medida foi inventada
[ ] Material não foi inventado
[ ] Compatibilidade não foi inventada
[ ] Cores fixas foram preservadas
[ ] Itens não inclusos estão corretos
[ ] Logo zonegeeklab3D está presente
[ ] Não existem logos de marketplaces
[ ] Não existem promoções inventadas
[ ] Não existem avaliações inventadas
```

---

# 29. VALIDAÇÃO VISUAL DO PRODUTO

Antes de aceitar cada imagem, comparar com as fotografias originais.

Se houver mudança em:

```text
geometria
número de furos
número de encaixes
número de partes
formato
proporção
```

a imagem deverá ser descartada e gerada novamente.

---

# 30. CRIAÇÃO DO ZIP

O ZIP somente será criado depois que todas as imagens forem validadas individualmente.

Sem SKU:

```text
Imagens_Anuncio.zip
```

Com SKU:

```text
SKU_XXXX_Imagens_Anuncio.zip
```

O ZIP deverá conter arquivos individuais.

Exemplo:

```text
Imagens_Anuncio.zip
│
├── 01_capa.png
├── 02_conteudo.png
├── 03_medidas.png
├── 04_funcionamento.png
├── 05_detalhes.png
└── 06_importante.png
```

Nunca colocar somente uma imagem contendo as seis artes dentro do ZIP.

---

# 31. MÚLTIPLOS PRODUTOS

O sistema poderá processar vários diretórios.

Exemplo:

```text
/produtos
│
├── produto_001/
│   └── entrada/
│
├── produto_002/
│   └── entrada/
│
└── produto_003/
    └── entrada/
```

Processamento:

```text
para cada diretorio em /produtos:

    analisar_produto()

    gerar_descricao()

    gerar_imagens_individuais()

    validar()

    criar_zip()
```

Cada pasta representa um produto independente.

Nunca misturar imagens de produtos diferentes.

---

# 32. LOG DE PROCESSAMENTO

Criar:

```text
processamento.log
```

Exemplo:

```text
[OK] 5 imagens encontradas
[OK] produto.json encontrado
[OK] Produto analisado
[OK] Descrição gerada
[OK] 01_capa.png
[OK] 02_conteudo.png
[OK] 03_medidas.png
[OK] 04_funcionamento.png
[OK] 05_detalhes.png
[OK] 06_importante.png
[OK] Validação concluída
[OK] ZIP criado
```

Em caso de informação não confirmada:

```text
[INFO] Material não informado — campo omitido
```

Em caso de erro:

```text
[ERRO] Medida necessária mas não confirmada
```

---

# 33. CONFIGURAÇÃO GLOBAL

O projeto poderá possuir:

```text
config.json
```

Exemplo:

```json
{
  "marca": "zonegeeklab3D",
  "resolucao": {
    "largura": 1000,
    "altura": 1000
  },
  "formato": "png",
  "fundo": "branco",
  "logo_posicao": "inferior_esquerdo",
  "quantidade_imagens": 6,
  "criar_zip": true,
  "permitir_inventar_medidas": false,
  "permitir_inventar_material": false,
  "permitir_inventar_caracteristicas": false
}
```

---

# 34. ARQUITETURA SUGERIDA

Estrutura conceitual do projeto:

```text
src/
│
├── main
├── config
│
├── scanner
│   └── leitor_diretorio
│
├── analyzer
│   ├── analisador_imagens
│   ├── analisador_metadados
│   └── consolidador_produto
│
├── copy
│   ├── gerador_titulo
│   ├── gerador_descricao
│   └── gerador_descricao_curta
│
├── images
│   ├── gerador_capa
│   ├── gerador_conteudo
│   ├── gerador_medidas
│   ├── gerador_funcionamento
│   ├── gerador_detalhes
│   └── gerador_importante
│
├── validation
│   ├── validador_dados
│   ├── validador_imagens
│   └── validador_saida
│
└── export
    ├── salvador
    └── zip
```

---

# 35. RESPONSABILIDADE DOS MÓDULOS

## Scanner

Responsável por:

```text
ler o diretório
identificar imagens
identificar produto.json
organizar arquivos
```

## Analyzer

Responsável por:

```text
analisar fotografias
consolidar informações
identificar produto
identificar elementos visuais
registrar dados confirmados
```

## Copy

Responsável por:

```text
título
descrição completa
descrição resumida
textos utilizados nas artes
```

## Images

Responsável pela geração de **uma arte por vez**.

## Validation

Responsável por impedir:

```text
medidas inventadas
material inventado
quantidades erradas
mudanças no produto
imagens agrupadas
resolução incorreta
```

## Export

Responsável por:

```text
salvar arquivos
nomear arquivos
criar diretórios
criar ZIP
```

---

# 36. REGRA DE SEGURANÇA CONTRA ALUCINAÇÕES

Todo dado utilizado deverá possuir uma origem.

Modelo:

```json
{
  "valor": "3,9 cm",
  "origem": "produto.json",
  "confirmado": true
}
```

ou:

```json
{
  "valor": "vermelho",
  "origem": "imagem",
  "confirmado": true
}
```

Para informações técnicas:

```json
{
  "valor": null,
  "origem": null,
  "confirmado": false
}
```

Informações com:

```json
{
  "confirmado": false
}
```

não poderão aparecer no anúncio como fatos.

---

# 37. CRITÉRIO FINAL DE ACEITE

Uma execução será considerada concluída somente quando houver:

```text
✓ produto analisado
✓ título criado
✓ descrição completa criada
✓ descrição resumida criada
✓ dados estruturados salvos
✓ 01_CAPA gerada individualmente
✓ 02_CONTEUDO gerada individualmente
✓ 03_MEDIDAS gerada individualmente quando aplicável
✓ 04_FUNCIONAMENTO gerada individualmente
✓ 05_DETALHES gerada individualmente
✓ 06_IMPORTANTE gerada individualmente
✓ todas em 1000 × 1000
✓ nenhuma grade ou mosaico
✓ produto visualmente fiel às fotografias
✓ ZIP contendo os arquivos independentes
```

---

# DECISÃO

O sistema será desenvolvido como um pipeline genérico orientado a diretórios.

Cada diretório representa um produto.

As fotografias reais serão consideradas a principal fonte visual.

As informações técnicas somente poderão ser utilizadas quando explicitamente confirmadas.

A geração das artes será obrigatoriamente sequencial, criando **um arquivo de imagem por chamada**, evitando definitivamente a criação de mosaicos ou grades contendo várias artes.

O sistema deverá priorizar fidelidade ao produto real sobre criatividade visual.
