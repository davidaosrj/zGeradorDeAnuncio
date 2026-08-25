# SPEC-001 — Integração com Ollama no Raspberry Pi

## Status

Proposta inicial

## Objetivo

Conectar o gerador de anúncios a uma instância Ollama instalada no Raspberry Pi acessível na rede local como `zizao@192.168.1.231`. O Ollama será usado para análise textual/visual compatível com o modelo escolhido e para geração de conteúdo; as regras de negócio continuam definidas pelo ADR-001.

## Escopo

Esta especificação cobre cliente HTTP, configuração, verificação de disponibilidade, listagem de modelos e chamadas de chat. Instalação do sistema operacional, edição de imagens e exposição do serviço à internet ficam fora do escopo.

## Configuração do cliente

| Variável | Padrão | Finalidade |
| --- | --- | --- |
| `OLLAMA_BASE_URL` | `http://192.168.1.231:11434` | URL da API na LAN |
| `OLLAMA_MODEL` | vazio | Modelo escolhido após ser instalado |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | Timeout total da requisição |

O usuário SSH `zizao` é relevante para a administração do Raspberry Pi, mas não faz parte da URL HTTP e não deve ser usado como credencial da API.

## Preparação do Raspberry Pi

Depois de instalar o Ollama, o serviço precisa escutar na interface da rede local, por exemplo com `OLLAMA_HOST=0.0.0.0:11434`. A forma de persistir essa variável depende de como o serviço foi instalado. Reinicie o serviço após a alteração e libere a porta TCP `11434` somente na LAN, se houver firewall.

Não encaminhar a porta no roteador e não expor essa API diretamente à internet. Se a rede não for confiável, preferir VPN ou túnel SSH com autorização explícita.

## Contrato HTTP

- `GET /api/tags`: prova de saúde e relação de modelos instalados.
- `POST /api/chat`: geração com mensagens no formato `role`/`content`.
- O cliente envia `stream: false`, pois o pipeline precisa validar a resposta completa antes de persistir arquivos.
- Respostas fora da faixa 2xx, JSON inválido e ausência de `message.content` são erros.

## Critérios de aceite

- `ollama-check health` confirma a conexão e informa a quantidade de modelos.
- `ollama-check models` lista os nomes retornados pelo Raspberry Pi.
- `ollama-check chat --prompt "..."` funciona quando `OLLAMA_MODEL` ou `--model` aponta para um modelo instalado.
- Falhas de rede, timeout, modelo ausente e respostas inválidas produzem mensagens acionáveis.
- Nenhum segredo ou senha SSH é armazenado no repositório.

## Comandos de validação

```bash
export OLLAMA_BASE_URL=http://192.168.1.231:11434
ollama-check health
ollama-check models
OLLAMA_MODEL=<modelo-instalado> ollama-check chat --prompt "Responda apenas OK"
```

## Dependência do pipeline

A conexão disponível não autoriza o modelo a inventar dados. Toda saída deve manter rastreabilidade da origem dos fatos e passar pelas validações do ADR-001.
