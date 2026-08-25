---
name: gerador-anuncios-ollama
description: Implementar, operar ou diagnosticar o pipeline deste repositório que gera anúncios em modo offline determinístico ou com um servidor Ollama remoto. Use em tarefas sobre geração offline, modelos locais, conexão Ollama, prompts, manifestos de produto ou geração de copy; não use para edição visual das fotografias.
---

# Gerador de anúncios com Ollama

Antes de alterar o pipeline, leia [`docs/adr/ADR-001-gerador-automatizado-de-anuncios.md`](../../../docs/adr/ADR-001-gerador-automatizado-de-anuncios.md). Para implantação ou diagnóstico da conexão, leia [`docs/specs/SPEC-001-integracao-ollama-raspberry-pi.md`](../../../docs/specs/SPEC-001-integracao-ollama-raspberry-pi.md).

Quando o Ollama estiver indisponível, leia [`docs/specs/SPEC-002-pre-geracao-offline.md`](../../../docs/specs/SPEC-002-pre-geracao-offline.md) e use `anuncio-offline`. O modo offline é válido apenas para dados textuais explicitamente fornecidos; ele não substitui análise visual.

## Regras essenciais

- Trate `produto.json` e informações explícitas do usuário como fontes prioritárias.
- Use fotografias somente para fatos visuais inequívocos; não converta aparência em especificação técnica.
- Preserve `null` ou listas vazias quando um dado não estiver confirmado.
- Exija saída estruturada quando a etapa alimentar automação e valide-a antes de salvar.
- Mantenha host, modelo e timeout configuráveis; nunca grave credenciais ou segredos no código.
- Antes de uma geração, consulte os modelos disponíveis e apresente erro acionável se o modelo configurado não existir.
- Não execute instalação, atualização ou comandos SSH no Raspberry Pi sem autorização explícita do usuário.
- Não exponha a API do Ollama à internet; a configuração prevista é somente para a LAN confiável.

## Fluxo de trabalho

1. Para o pipeline completo, use `gerar-anuncio <diretório> --mode auto`; ele tenta Ollama e usa fallback offline.
2. Para execução garantidamente sem rede, use `gerar-anuncio <diretório> --mode offline`.
3. Use `anuncio-offline` somente quando forem desejados os textos sem artes ou ZIP.
4. Se Ollama for obrigatório, confirme a conectividade e use `--mode online`.
5. Consolide apenas fatos confirmados e valide a saída contra o ADR-001.

Use `OLLAMA_BASE_URL`, `OLLAMA_MODEL` e `OLLAMA_TIMEOUT_SECONDS` para configuração. O endereço padrão do projeto aponta para o Raspberry Pi informado pelo usuário.
