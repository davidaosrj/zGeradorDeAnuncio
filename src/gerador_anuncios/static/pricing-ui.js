'use strict';
(() => {
  const $ = s => document.querySelector(s), form = $('#pricing-form');
  const api = document.body.dataset.api === 'true', key = 'zonegeeklab3d-pricing-v1';
  const catalogs = {materials: [], printers: [], products: [], 'fee-rules': []};
  let history = [], historyOffset = 0, state = {catalogs, history: []};
  const clone = x => JSON.parse(JSON.stringify(x));
  const message = (text, error = false) => { $('#message').textContent = text; $('#message').className = error ? 'error' : ''; };
  const brl = v => `R$ ${String(v).replace('.', ',')}`;
  const node = (tag, text, parent) => { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (parent) parent.append(e); return e; };
  const values = element => Object.fromEntries([...element.querySelectorAll('[name]')].map(e => [e.name, e.value]));
  function fill(element, data) { for (const input of element.querySelectorAll('[name]')) if (Object.hasOwn(data, input.name)) input.value = data[input.name] ?? ''; }
  function input(parent, name, label, value = '', type = 'number') {
    const l = node('label', label, parent), e = node('input', undefined, l);
    e.name = name; e.type = type; e.value = value;
    if (type === 'number') { e.min = '0'; e.step = 'any'; }
    return e;
  }
  async function request(path, payload) {
    const response = await fetch(path, payload === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
    if (!response.ok) { let reason = `Erro HTTP ${response.status}`; try { const body = await response.json(); reason = typeof body.detail === 'string' ? body.detail : reason; } catch (_) {} throw Error(reason); }
    return response.json();
  }
  function persist(next) {
    // Commit in memory only after durable storage succeeds.
    localStorage.setItem(key, JSON.stringify(next)); state = next;
  }
  function catalogSelect(parent, kind, label, apply) {
    const l = node('label', label, parent), select = node('select', undefined, l);
    select.dataset.catalog = kind;
    select.onchange = () => { const record = catalogs[kind].find(r => r.id === select.value); if (record) apply(record.data, record.id); };
    return select;
  }
  function refreshChoices() {
    for (const select of document.querySelectorAll('[data-catalog]')) {
      const chosen = select.value; select.replaceChildren(new Option('Preencher manualmente', ''));
      for (const r of catalogs[select.dataset.catalog]) select.add(new Option(`${r.data.name} · ${r.created_at.slice(0, 19)}`, r.id));
      select.value = chosen;
    }
    const select = $('#saved-rule'), chosen = select.value;
    select.replaceChildren(new Option('Preencher manualmente', ''));
    for (const r of catalogs['fee-rules']) select.add(new Option(`${r.data.marketplace} · ${r.data.name} · v${r.data.version}`, r.id));
    select.value = chosen;
  }
  function component(data = {}) {
    const box = node('fieldset', undefined, $('#components')); box.className = 'component';
    node('legend', 'Componente do produto / kit', box);
    const grid = node('div', undefined, box); grid.className = 'grid';
    input(grid, 'name', 'Nome do componente', '', 'text');
    input(grid, 'quantity', 'Quantidade por unidade / kit', '1');
    input(grid, 'weight_g', 'Peso por componente com suportes (g)', '55');
    input(grid, 'hours', 'Horas por componente', '3');
    catalogSelect(grid, 'materials', 'Material salvo', (r, id) => { fill(box, {filament_price_kg: r.price_kg, material_id: id}); });
    input(grid, 'filament_price_kg', 'Filamento (R$/kg)', '120');
    catalogSelect(grid, 'printers', 'Impressora salva', (r, id) => { fill(box, {machine_hour: r.machine_hour, energy_hour: r.energy_hour, printer_id: id}); });
    input(grid, 'machine_hour', 'Máquina (R$/h)', '2');
    input(grid, 'energy_hour', 'Energia (R$/h)', '0.25');
    input(grid, 'additional_cost', 'Outros custos por componente (R$)', '0');
    input(grid, 'material_id', '', '', 'hidden').parentElement.hidden = true;
    input(grid, 'printer_id', '', '', 'hidden').parentElement.hidden = true;
    const remove = node('button', 'Remover componente', box); remove.type = 'button'; remove.className = 'secondary'; remove.onclick = () => box.remove();
    fill(box, data); refreshChoices();
  }
  function sourceLink(raw) {
    const value = String(raw || '').trim();
    if (!value) return null;
    try {
      const url = new URL(/^https?:\/\//i.test(value) ? value : `https://${value}`);
      if (!['https:', 'http:'].includes(url.protocol) || url.username || url.password) return null;
      const host = url.hostname.toLowerCase();
      const under = domain => host === domain || host.endsWith('.' + domain);
      const marketplace = under('shopee.com.br') || host === 'shope.ee' ? 'shopee' : under('mercadolivre.com.br') || under('mercadolivre.com') || under('mercadolibre.com') ? 'mercado_livre' : '';
      // Only add a missing scheme for a recognized marketplace.
      if (!/^https?:\/\//i.test(value) && !marketplace) return null;
      return {url: url.href, marketplace};
    } catch (_) { return null; }
  }
  const marketplaceName = value => ({shopee: 'Shopee', mercado_livre: 'Mercado Livre', direct: 'Venda direta'}[value] || value || 'Não informado');
  function competitor(data = {}) {
    const box = node('fieldset', undefined, $('#competitors')); box.className = 'component'; node('legend', 'Anúncio concorrente', box);
    const urlInput = input(box, 'url', 'Link do anúncio da Shopee ou Mercado Livre', '', 'url');
    urlInput.placeholder = 'https://shopee.com.br/... ou https://produto.mercadolivre.com.br/...';
    const linkActions = node('div', undefined, box); linkActions.className = 'actions';
    const open = node('a', 'Abrir anúncio para conferir', linkActions); open.className = 'button secondary'; open.target = '_blank'; open.rel = 'noopener noreferrer'; open.hidden = true;
    const note = node('p', 'Cole o link, confira a variação e informe o preço do mesmo produto ou kit.', box); note.setAttribute('role', 'status');
    const grid = node('div', undefined, box); grid.className = 'grid';
    for (const [name, label, value, type] of [
      ['name', 'Nome do produto', '', 'text'], ['category', 'Categoria', '', 'text'], ['marketplace', 'Marketplace identificado pelo link', '', 'text'],
      ['collected_at', 'Data em que você conferiu o preço', new Date().toISOString().slice(0, 10), 'date'],
      ['price', 'Preço observado para o mesmo pedido (R$)', '', 'number'], ['buyer_shipping', 'Frete ao comprador (R$)', '', 'number'],
      ['discount', 'Desconto exibido (R$)', '', 'number'], ['displayed_sales', 'Vendas acumuladas exibidas', '', 'number'],
      ['weight_g', 'Peso informado (g)', '', 'number'], ['dimensions', 'Dimensões informadas', '', 'text']
    ]) input(grid, name, label, value, type);
    let previousUrl = '';
    const identify = (restoring = false) => {
      const source = sourceLink(urlInput.value);
      const nextUrl = source ? source.url : urlInput.value.trim();
      if (!restoring && nextUrl !== previousUrl) fill(box, {price: '', collected_at: new Date().toISOString().slice(0, 10)});
      previousUrl = nextUrl;
      open.hidden = !source; open.removeAttribute('href');
      if (source) {
        urlInput.value = source.url; open.href = source.url;
        if (source.marketplace || !restoring) fill(box, {marketplace: source.marketplace});
        note.textContent = source.marketplace ? `${marketplaceName(source.marketplace)} identificado. Abra o anúncio, confira a variação e informe o preço observado.` : 'Link registrado. Informe o marketplace e o preço observado.';
      } else {
        if (!restoring) fill(box, {marketplace: ''});
        note.textContent = urlInput.value ? 'Informe um link HTTP ou HTTPS válido, sem usuário ou senha.' : 'Cole o link do anúncio para identificar o marketplace.';
      }
      $('#result').hidden = true;
    };
    urlInput.addEventListener('change', () => identify());
    const remove = node('button', 'Remover concorrente', box); remove.type = 'button'; remove.className = 'secondary'; remove.onclick = () => { box.remove(); $('#result').hidden = true; };
    fill(box, data); identify(true);
  }
  const ruleDefaults = {marketplace: 'shopee', version: '1', listing_type: '', commission_pct: '0', payment_pct: '0', tax_pct: '0', fixed_fee: '0', basis: 'order', min_price: '0', max_price: '', valid_from: '', valid_until: ''};
  const ruleFields = ['marketplace', 'version', 'listing_type', 'commission_pct', 'payment_pct', 'tax_pct', 'fixed_fee', 'basis', 'min_price', 'max_price', 'valid_from', 'valid_until'];
  function payload() {
    const v = Object.fromEntries([...form.querySelectorAll('[name]')].filter(e => !e.closest('fieldset')).map(e => [e.name, e.value])), rule = Object.fromEntries(ruleFields.map(k => [k, v[k]]));
    rule.name = v.rule_name; rule.category = v.category;
    const result = {currency: 'BRL', calculation_date: new Date().toISOString().slice(0, 10), fee_rule: rule};
    for (const k of ['name', 'sku', 'category', 'order_units', 'failure_pct', 'packaging_cost', 'packaging_count', 'assembly_cost', 'shipping', 'discount', 'order_other_cost', 'target_margin_pct', 'commercial_step', 'selling_price']) result[k] = v[k];
    result.components = [...$('#components').children].map(values);
    result.competitors = [...$('#competitors').children].map(values);
    return result;
  }
  function load(data) {
    Pricing3D.calculate(data);
    form.reset(); fill(form, data); fill(form, {...Object.fromEntries(ruleFields.map(k => [k, data.fee_rule[k] ?? form.elements[k].value])), rule_name: data.fee_rule.name || ''});
    $('#components').replaceChildren(); $('#competitors').replaceChildren();
    data.components.forEach(component); (data.competitors || []).forEach(competitor);
    $('#result').hidden = true; message('Cenário carregado. Confira a vigência das tarifas e calcule novamente.');
  }
  function render(result) {
    $('#result').hidden = false; $('#metrics').replaceChildren();
    for (const [label, value] of [
      ['Preço sugerido do pedido', brl(result.commercial_price)], ['Equilíbrio do pedido', brl(result.break_even_price)],
      ['Lucro no preço avaliado', brl(result.profit)], ['Margem no preço avaliado', `${result.margin_pct}%`],
      ['Preço sugerido por unidade / kit', brl(result.price_per_unit)], ['Preço avaliado do pedido', brl(result.selling_price)],
      ['Fator sobre custo de produção', `${result.multiplier}×`], ['Viabilidade', result.classification]
    ]) { const m = node('div', undefined, $('#metrics')); m.className = 'metric'; node('span', label, m); node('strong', value, m); }
    $('#breakdown').replaceChildren();
    for (const [key, label] of [['material_cost','Material'],['machine_cost','Máquina'],['energy_cost','Energia'],['additional_cost','Outros custos de fabricação'],['failure_reserve','Reserva para falhas'],['packaging','Embalagens'],['assembly','Montagem'],['production_cost','Custo total de produção'],['fixed_fee','Tarifas fixas'],['shipping','Frete / logística'],['discount','Desconto do vendedor'],['order_other_cost','Outros custos do pedido'],['variable_fees','Comissão, impostos e pagamento'],['calculated_price','Preço calculado antes do passo comercial']]) {
      const row = node('tr', undefined, $('#breakdown')); node('th', label, row).scope = 'row'; node('td', brl(result[key]), row);
    }
    $('#comparisons').replaceChildren();
    for (const c of result.comparisons) {
      const card = node('div', undefined, $('#comparisons')); card.className = 'component';
      node('h4', c.observation.name || 'Concorrente', card);
      node('p', `${marketplaceName(c.observation.marketplace)} · conferido em ${c.observation.collected_at || 'data não informada'}`, card);
      if (c.price !== undefined) node('p', `Preço do concorrente: ${brl(c.price)} · seu preço sugerido: ${brl(result.commercial_price)}`, card);
      node('p', `${c.classification}${c.profit !== undefined ? ` · seu lucro ao igualar: ${brl(c.profit)} · sua margem: ${c.margin_pct}%` : ' · informe preço e data, e confira a faixa da tarifa'}`, card);
      const source = sourceLink(c.observation.url);
      if (source) { const link = node('a', 'Ver anúncio do concorrente', card); link.href = source.url; link.target = '_blank'; link.rel = 'noopener noreferrer'; }
    }
    if (result.comparisons.length) node('p', `Projeção usando seus custos e a regra de ${marketplaceName(result.snapshot.fee_rule.marketplace)}. Para vender em outro canal, selecione as tarifas desse canal e calcule novamente.`, $('#comparisons'));
    if (!result.comparisons.length) node('p', 'Nenhum concorrente informado.', $('#comparisons'));
  }
  async function run(action) { try { await action(); } catch (e) { message(e.message, true); } }
  form.onsubmit = event => { event.preventDefault(); run(async () => {
    $('#calculate').disabled = true; $('#result').hidden = true;
    try {
      const data = payload(); let result;
      if (api) result = await request('/api/pricing/calculate', data);
      else {
        result = Pricing3D.calculate(data);
        const record = {id: crypto.randomUUID(), created_at: new Date().toISOString(), data: result};
        try { persist({...state, history: [record, ...state.history]}); }
        catch (e) { render(result); throw Error('Cálculo concluído, mas o histórico não foi salvo. Exporte o cenário e libere espaço no navegador.'); }
      }
      render(result); await refreshHistory(); message('Cálculo concluído e salvo no histórico.');
    } finally { $('#calculate').disabled = false; }
  }); };
  async function saveCatalog(kind, data) {
    if (!String(data.name || '').trim()) throw Error('Informe o nome do cadastro.');
    let record;
    if (api) record = await request(`/api/pricing/catalogs/${kind}`, data);
    else {
      record = {id: crypto.randomUUID(), created_at: new Date().toISOString(), data: clone(data)};
      persist({...state, catalogs: {...state.catalogs, [kind]: [record, ...state.catalogs[kind]]}});
    }
    await refreshCatalogs(); message('Nova revisão salva.');
  }
  function catalogList(kind, target) {
    target.replaceChildren();
    for (const record of catalogs[kind]) {
      const row = node('p', `${record.data.name} · ${record.created_at.slice(0, 19)} `, target);
      if (kind === 'products') { const button = node('button', 'Carregar', row); button.type = 'button'; button.onclick = () => run(() => load(record.data.scenario)); }
    }
  }
  async function allRecords(path) {
    const rows = []; let batch;
    do { batch = await request(`${path}?limit=500&offset=${rows.length}`); rows.push(...batch); } while (batch.length === 500);
    return rows;
  }
  async function refreshCatalogs() {
    for (const kind of Object.keys(catalogs)) catalogs[kind] = api ? await allRecords(`/api/pricing/catalogs/${kind}`) : state.catalogs[kind];
    refreshChoices(); catalogList('materials', $('#material-list')); catalogList('printers', $('#printer-list')); catalogList('products', $('#product-list'));
  }
  async function refreshHistory(more = false) {
    if (!more) { history = []; historyOffset = 0; $('#history-list').replaceChildren(); }
    const batch = api ? await request(`/api/pricing/history?limit=50&offset=${historyOffset}`) : state.history.slice(historyOffset, historyOffset + 50);
    history.push(...batch); historyOffset += batch.length;
    for (const record of batch) {
      const row = node('p', `${record.created_at.slice(0, 19)} · ${record.data.snapshot.name || 'Produto'} · ${brl(record.data.commercial_price)} `, $('#history-list'));
      const view = node('button', 'Ver resultado', row); view.onclick = () => render(record.data);
      const restore = node('button', 'Reabrir cenário', row); restore.className = 'secondary'; restore.onclick = () => run(() => load(record.data.snapshot));
    }
    $('#more-history').hidden = batch.length < 50;
    if (!history.length) node('p', 'Nenhuma simulação salva.', $('#history-list'));
  }
  function download(name, data) {
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'}));
    const a = node('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  form.addEventListener('input', () => { $('#result').hidden = true; });
  form.addEventListener('change', () => { $('#result').hidden = true; });
  $('#add-component').onclick = () => component(); $('#add-competitor').onclick = () => competitor();
  $('#saved-rule').onchange = e => { const r = catalogs['fee-rules'].find(r => r.id === e.target.value); if (r) fill(form, {...Object.fromEntries(ruleFields.map(k => [k, r.data[k] ?? ruleDefaults[k]])), rule_name: r.data.name}); };
  form.elements.marketplace.onchange = () => {
    fill(form, {commission_pct: '0', payment_pct: '0', tax_pct: '0', fixed_fee: '0', rule_name: '', version: '1', listing_type: '', min_price: '0', max_price: '', valid_from: '', valid_until: '', basis: 'order'});
    $('#saved-rule').value = ''; message('Canal alterado. Preencha ou selecione as tarifas desse canal antes de calcular.');
  };
  $('#save-rule').onclick = () => run(async () => { const data = payload(); Pricing3D.calculate(data); await saveCatalog('fee-rules', data.fee_rule); });
  for (const [selector, kind, numeric] of [['#material-form', 'materials', ['price_kg']], ['#printer-form', 'printers', ['machine_hour', 'energy_hour']]]) {
    $(selector).onsubmit = e => { e.preventDefault(); run(async () => { const data = Object.fromEntries(new FormData(e.target)); for (const k of numeric) if (!/^\d{1,10}(?:\.\d{1,6})?$/.test(data[k]) || Number(data[k]) > 1e9) throw Error('Custo inválido.'); await saveCatalog(kind, data); }); };
  }
  $('#save-product').onclick = () => run(async () => { const scenario = payload(); Pricing3D.calculate(scenario); await saveCatalog('products', {name: scenario.name, sku: scenario.sku, weight_g: scenario.components[0].weight_g, hours: scenario.components[0].hours, scenario}); });
  $('#export-scenario').onclick = () => run(() => { const data = payload(); Pricing3D.calculate(data); download('cenario-impressao-3d.json', data); });
  $('#import-scenario').onchange = e => run(async () => { const file = e.target.files[0]; if (!file) return; if (file.size > 1000000) throw Error('Arquivo maior que 1 MB.'); load(JSON.parse(await file.text())); e.target.value = ''; });
  $('#export-history').onclick = () => run(async () => download('historico-impressao-3d.json', {schema_version: 1, catalogs, history: api ? await allRecords('/api/pricing/history') : state.history}));
  $('#load-history').onclick = () => run(() => refreshHistory()); $('#more-history').onclick = () => run(() => refreshHistory(true));
  $('#load-example').onclick = () => run(() => load({name: 'Dinossauro articulado — exemplo ADR-002', currency: 'BRL', order_units: '1', components: [{name:'Dinossauro', quantity:'1', weight_g:'55', hours:'3', filament_price_kg:'120', machine_hour:'2', energy_hour:'0.25', additional_cost:'0'}], failure_pct:'10', packaging_cost:'4', packaging_count:'1', target_margin_pct:'30', commercial_step:'0.01', fee_rule:{name:'Exemplo ADR-002 — conferir na conta', marketplace:'shopee', version:'exemplo-1', commission_pct:'20', fixed_fee:'4.50', basis:'order'}, competitors:[]}));
  $('#storage-note').textContent = api ? 'Modo aplicação: cálculos e histórico salvos no servidor local.' : 'Modo GitHub Pages: cálculos e cadastros ficam neste navegador. Exporte o histórico para backup antes de limpar os dados do site.';
  run(async () => {
    if (!api) {
      const saved = localStorage.getItem(key);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (!parsed.catalogs || !Array.isArray(parsed.history) || Object.keys(catalogs).some(k => !Array.isArray(parsed.catalogs[k]))) throw Error('Histórico local inválido; os dados foram preservados.');
        state = parsed;
      }
    }
    component(); await refreshCatalogs(); await refreshHistory();
  });
})();
