# SPEC-003 — MCP, frontend e CI/CD

## Componentes

- Frontend/API FastAPI em `:8000`, com cadastro, upload e geração.
- MCP Streamable HTTP em `:8001/mcp`, com ferramentas de cadastro, validação, geração e status.
- Persistência local configurada por `PRODUCTS_ROOT`.
- Docker Compose com serviços `web` e `mcp` compartilhando o mesmo volume.
- CI executa testes e build; CD publica imagem no GitHub Container Registry em `main` e tags `v*`.

## Execução

```bash
docker compose up --build
```

Frontend: `http://localhost:8000`. MCP: `http://localhost:8001/mcp`.

O modo `auto` usa Ollama quando `OLLAMA_MODEL` está configurado e mantém fallback offline. O modo `offline` nunca acessa o Ollama; `online` falha se o serviço estiver indisponível.
