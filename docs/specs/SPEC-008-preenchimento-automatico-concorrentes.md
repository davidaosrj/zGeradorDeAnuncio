# SPEC-008 — Preenchimento automático de concorrentes

Complementa ADR-002 e SPEC-007. O usuário solicitou colar o link e preencher os dados do anúncio automaticamente, em vez de exigir digitação de todos os campos.

## Solução para GitHub Pages

A página estática usa a extensão Manifest V3 `extensions/leitor-anuncios`, instalável no Chrome/Edge de computador. Não exige servidor externo, token de API nem envio de dados a serviço de leitura de terceiros. A instalação da extensão é uma ação única do usuário, e não pode ser feita pelo próprio site. Sem extensão instalada, a página explica como ativar e mantém o modo manual.

Ao colar um link reconhecido, após 700 ms sem edição (ou ao sair do campo), a calculadora consulta o leitor. A extensão abre uma aba em segundo plano no marketplace, espera carregar e extrai dados do produto. O botão “Preencher pelo link” permite repetir a leitura. Os dados chegam sem HTML, preenchem o formulário e ficam registrados no snapshot da simulação. Ao abrir cenários antigos, não se consulta automaticamente nem altera o histórico.

## Dados e extração

Preencher somente campos disponíveis e verificáveis: nome, preço único, canal, categoria, imagem de produto em CDN do marketplace, vendas acumuladas exatas quando exibidas, peso em gramas e dimensões em atributos explícitos. Registrar data UTC, horário de leitura e `retrieval_method=browser-extension`. Frete só é preenchido quando houver valor estruturado inequívoco; não interpretar cupom, banner de frete grátis ou parcela como preço/frete. Não acessar endereço ou CEP da conta.

Usar Product/Offer e BreadcrumbList em JSON-LD, metadados de preço e seletores do bloco principal. Não recorrer ao primeiro número ou `R$` arbitrário no corpo. Evitar produtos recomendados. Preço único em BRL é obrigatório para leitura completa; intervalos ou múltiplas ofertas retornam parcial e pedem conferência da variação. Nome sem preço pode ser importado como parcial; campos ausentes permanecem vazios. Os seletores dependem do HTML disponibilizado pelos marketplaces e podem exigir manutenção.

Estados: `ready` (extensão instalada), `ok`, `partial`, `needs_action` (login/verificação), `unavailable`, `error`, `missing` (extensão não encontrada) e `cancelled`. Não simular preenchimento completo quando o anúncio não foi lido. Não resolver CAPTCHA automaticamente, contornar login nem acessar páginas privadas.

## Limites de permissão e comunicação

Permissão `scripting` e hosts HTTPS da Shopee e Mercado Livre. Não solicitar cookies, histórico de navegação, senhas ou armazenamento da extensão. O script de ponte é injetado somente no site `davidaosrj.github.io/zGeradorDeAnuncio/` e na aplicação local `/impressao-3d` na porta 8000. O worker valida origem e frame antes de aceitar mensagens. O leitor só aceita URLs HTTPS de produto ou links curtos oficiais; rejeita credenciais na URL, portas personalizadas, domínios parecidos, páginas de conta e redirecionamentos fora do marketplace de origem.

Cada solicitação tem ID; a página aceita respostas de sua própria janela/origem. Consultas posteriores substituem anteriores. Não sobrescrever alterações manuais feitas enquanto a leitura estava em andamento, nem aplicar resultado antigo após troca de link ou remoção do concorrente. Trocar a origem limpa os campos importáveis anteriores.

A extensão manipula apenas abas criadas para a consulta. Consulta completa fecha sua aba; login/verificação ou resultado parcial mantém a aba para ação do usuário. “Concluir acesso no anúncio” foca essa aba. O tempo máximo de tentativa é 24 s, sem retentativas infinitas. O worker pode ser suspenso pelo Chrome após inatividade; nesse caso uma nova consulta pode criar outra aba, e a anterior pode ser fechada manualmente.

## Empacotamento, entrega e validação

`python scripts/build_pricing_site.py` gera ZIP reproduzível sem chaves ou dependências externas, nos assets da aplicação e em `site/impressao-3d/leitor-anuncios.zip`. `--check` compara arquivos gerados. A página oferece download e instruções de instalação; a atualização de extensão descompactada requer extrair a nova versão na mesma pasta e recarregar a extensão e a página.

Testes Chromium carregam a extensão real e interceptam apenas as respostas dos anúncios com fixtures controladas. Verificam colagem sem clique adicional, importação de nome/preço/categoria/atributos, comparação, preservação de edições manuais, resposta obsoleta, preço ambíguo, login, parcelas e restrições de URL. Testes de cálculo/API existentes continuam no CI. Nenhuma fixture comprova acesso a todas as páginas reais: login, verificações, geolocalização, preço por conta e mudanças no HTML continuam limites da fonte. A validação com anúncio real do operador é necessária para confirmar seu caso.
