# SPEC-007 — Interface e entrega da precificação 3D

Status: implementada. Complementa [SPEC-006](SPEC-006-motor-precificacao-impressao-3d.md) e [ADR-002](../adr/ADR-002-motor-precificacao-impressao-3d.md).

## Acesso e modos

O botão “Precificação de impressão 3D” abre `/impressao-3d` na aplicação e `impressao-3d/` no GitHub Pages. A página deixa de ser uma cópia estática da proposta e passa a oferecer a calculadora. O documento permanece em `docs/adr/`.

- Aplicação local: API Python executa e persiste cálculo em SQLite.
- GitHub Pages: `pricing-engine.js` executa operações racionais com `BigInt`, sem `Number` para dinheiro. Não depende de CDN, servidor externo nem taxas consultadas automaticamente. Cadastros e histórico ficam no `localStorage` desta origem/navegador. O modo aparece na página. Não há sincronização automática entre dispositivos ou entre os modos.

Essa adaptação da diretriz de backend permite utilizar o site estático solicitado. Os dois motores implementam o mesmo contrato e são comparados por testes; a fonte Python continua disponível como API independente.

## Fluxo

1. Identificar produto ou kit e quantidade no pedido.
2. Adicionar/remover componentes; informar consumo, tempo, quantidade, filamento, máquina, energia e custos adicionais. Aplicar revisões salvas de material/impressora quando disponíveis.
3. Informar falhas, embalagens, montagem e despesas do pedido.
4. Escolher canal e preencher/aplicar regra comercial versionada. Trocar canal zera tarifas para evitar carregar inadvertidamente taxas de outro marketplace.
5. Informar margem, passo comercial e preço opcional de avaliação.
6. Opcionalmente adicionar observações de concorrentes equivalentes.
7. Calcular e salvar histórico. Exibir preços do pedido/unidade, equilíbrio, lucro/margem no preço avaliado, fator, classificação e composição de custos.

Os rótulos distinguem componente, unidade/kit e pedido. A tela usa campos associados a labels, botões nativos, região de status acessível, layout responsivo e tabelas com rolagem. Conteúdo informado é renderizado com `textContent`, nunca interpolado em HTML.

## Cadastros, cenários e histórico

Salvar cria novas revisões. Materiais e impressoras podem ser aplicados a cada componente. Regras preservam canal e versão. Produto/kit salva o cenário inteiro. Cenários podem ser exportados e importados em JSON (máximo 1 MB), com validação antes de carregar. Histórico pode ser exportado com cadastros em JSON; não há restauração automática desse backup nesta versão. Simulações anteriores podem ser vistas ou reabertas como cenário, sem sobrescrever o registro. Histórico é paginado em 50 registros na interface; exportação percorre todas as páginas.

Falhas de gravação no navegador são visíveis: mostrar resultado calculado e avisar que não houve persistência. Não apagar histórico para liberar espaço. Armazenamento local é limitado pelo navegador; exportação é o mecanismo de backup.

## Construção e CI/CD

Manter fontes em `src/gerador_anuncios/static/pricing*`. Executar `python scripts/build_pricing_site.py` para gerar `site/impressao-3d/`; `--check` rejeita divergências. A geração adapta caminhos relativos e modo de persistência, mantendo motores e interface idênticos.

CI verifica testes Python, paridade com Node, sintaxe JavaScript, sincronização dos arquivos e build da aplicação. A publicação GitHub Pages depende de validação aprovada na mesma revisão. Commit/push/PR seguem o fluxo do repositório; o site é publicado após integração na `main`.

## Limites desta versão

Seleção de regras por categoria/faixa é manual e validada por preço/vigência. Comparação de mercado depende de dados inseridos pelo usuário. Integrações de marketplace, importação de slicer, coleta automática de concorrentes, dashboard e planejamento de capacidade permanecem evoluções futuras da ADR. Nenhuma taxa de exemplo constitui tarifa oficial.
