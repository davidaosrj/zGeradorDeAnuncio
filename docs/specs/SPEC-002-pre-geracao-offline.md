# SPEC-002 — Pré-geração de anúncio sem Ollama

## Status

Aprovado para implementação inicial

## Objetivo

Permitir a criação de um rascunho de anúncio quando o Ollama estiver offline, usando exclusivamente os dados confirmados em `produto.json`.

## Entradas

O comando recebe o diretório do produto ou o caminho direto de `produto.json`. O campo `nome` é obrigatório no modo offline porque não existe análise visual ou modelo para identificá-lo.

Campos suportados:

- `sku`, `nome`, `quantidade` e `material`;
- `medidas`, `cores_fixas`, `cores_variaveis` e `compatibilidade`;
- `itens_inclusos`, `itens_nao_inclusos`, `beneficios_confirmados` e `observacoes`.

Valores ausentes permanecem `null` ou `[]` e suas seções são omitidas da copy.

## Saída

Em `<produto>/saida/`:

```text
titulo.txt
descricao_completa.txt
descricao_resumida.txt
anuncio.md
produto_analisado.json
processamento.log
```

O manifesto marca cada valor recebido com origem `produto.json` e registra a pendência `analise_visual_nao_realizada`. Nenhuma imagem ou ZIP é criado no modo offline.

## Regras

- Não acessar a rede e não depender do Ollama.
- Não analisar nem descrever fotografias.
- Não acrescentar benefícios, materiais, medidas ou compatibilidades.
- Não completar texto ausente com afirmações comerciais genéricas.
- Sobrescrever somente os arquivos conhecidos da saída textual quando o comando for executado novamente.

## Execução

```bash
anuncio-offline /caminho/do/produto
```

Use `--output` para escolher outro diretório de saída.

## Saída pelo navegador

No frontend web, o servidor gera a saída em sua área temporária e disponibiliza `GET /api/products/{sku}/download`, que reúne textos, imagens, logs e pacotes em `{sku}_Anuncio_Completo.zip`. Em navegadores compatíveis com a File System Access API, o usuário escolhe diretamente a pasta local e concede permissão de gravação. Nos demais navegadores, o ZIP utiliza o download padrão. O servidor nunca recebe nem tenta listar o caminho local escolhido pelo navegador.

## Critérios de aceite

- Funciona com a rede indisponível.
- Gera todos os seis arquivos previstos.
- O texto contém somente dados presentes no JSON.
- JSON inválido, tipos incorretos e ausência de `nome` resultam em erro acionável.
