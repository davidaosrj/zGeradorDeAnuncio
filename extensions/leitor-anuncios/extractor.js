/* Runs in an isolated content-script world. Returns product data only. */
(() => {
  'use strict';
  const clean = value => String(value ?? '').replace(/\s+/g, ' ').trim();
  function money(value, localized = false) {
    let text = clean(value).replace(/^R\$\s*/, '');
    if (!/^\d[\d.,]*$/.test(text)) return '';
    if (text.includes(',')) text = text.replace(/\./g, '').replace(',', '.');
    else if (localized && /^\d{1,3}(?:\.\d{3})+$/.test(text)) text = text.replace(/\./g, '');
    text = text.replace(/(\.\d{2})0+$/, '$1');
    if (!/^\d{1,9}(?:\.\d{1,2})?$/.test(text) || !/[1-9]/.test(text)) return '';
    const [whole, fraction = ''] = text.split('.');
    return `${BigInt(whole)}.${fraction.padEnd(2, '0')}`;
  }
  function extract(doc = document, href = location.href) {
    const url = new URL(href), host = url.hostname;
    const shopee = host === 'shopee.com.br' || host.endsWith('.shopee.com.br');
    const marketplace = shopee ? 'shopee' : 'mercado_livre';
    const visible = element => element && !element.closest('[hidden],[aria-hidden="true"]') && getComputedStyle(element).display !== 'none';
    const text = selectors => {
      for (const selector of selectors) for (const e of doc.querySelectorAll(selector)) if (visible(e) && clean(e.textContent)) return clean(e.textContent);
      return '';
    };
    const meta = names => {
      for (const name of names) {
        const e = doc.querySelector(`meta[property="${name}"],meta[name="${name}"]`);
        if (e?.content) return clean(e.content);
      }
      return '';
    };
    const body = clean(doc.body?.innerText || doc.body?.textContent || '').slice(0, 100000);
    if (/Login Necessário|faça login para continuar|verifique (?:que|se) voc[eê] [eé] humano|confirme que voc[eê]|complete o captcha/i.test(body)) return {status: 'needs_action', message: 'O anúncio exige login ou verificação no navegador. Conclua na aba do anúncio e tente novamente.'};
    const objects = [];
    function walk(value, depth = 0) {
      if (!value || typeof value !== 'object' || depth > 12 || objects.length > 500) return;
      if (Array.isArray(value)) { value.forEach(v => walk(v, depth + 1)); return; }
      if (value['@type']) objects.push(value);
      if (value['@graph']) walk(value['@graph'], depth + 1);
      if (value.mainEntity) walk(value.mainEntity, depth + 1);
    }
    for (const script of doc.querySelectorAll('script[type="application/ld+json"]')) {
      if (script.textContent.length > 1000000) continue;
      try { walk(JSON.parse(script.textContent)); } catch (_) { /* Other page data are not product data. */ }
    }
    const typeIs = (obj, type) => (Array.isArray(obj['@type']) ? obj['@type'] : [obj['@type']]).some(t => String(t).split('/').pop() === type);
    const products = objects.filter(o => typeIs(o, 'Product'));
    // Multiple product nodes can be recommendations: select only a matching URL or a unique product.
    const product = products.find(p => p.url && String(p.url).split(/[?#]/)[0] === href.split(/[?#]/)[0]) || (products.length === 1 ? products[0] : {});
    const result = {url: href, resolved_url: href, marketplace, collected_at: new Date().toISOString().slice(0, 10), retrieved_at: new Date().toISOString(), retrieval_method: 'browser-extension', warnings: []};
    const title = text(['h1.ui-pdp-title', '[data-testid="product-name"]', 'main h1', 'h1']) || clean(product.name) || meta(['og:title']);
    const generic = /^(Shopee Brasil|Shopee|Mercado Livre|Mercado Libre)(\s*\|.*)?$/i.test(title) || /^(login|entrar|acesse sua conta|entre na sua conta|verificação de segurança)$/i.test(title);
    result.name = generic ? '' : title.slice(0, 500);
    let offers = product.offers ? (Array.isArray(product.offers) ? product.offers : [product.offers]) : [];
    if (offers.length === 1 && offers[0].offers) offers = Array.isArray(offers[0].offers) ? offers[0].offers : [offers[0].offers];
    const currencies = offers.map(o => o.priceCurrency).filter(Boolean);
    const currency = clean(currencies[0] || meta(['product:price:currency', 'og:price:currency']) || 'BRL');
    if (currency !== 'BRL' || currencies.some(c => c !== 'BRL')) result.warnings.push('Moeda diferente de BRL: preço não importado.');
    const priceCandidates = [...new Set(offers.map(o => money(o.price)).filter(Boolean))];
    const aggregate = offers.find(o => o.lowPrice !== undefined || o.highPrice !== undefined);
    if (aggregate) {
      result.price_min = money(aggregate.lowPrice); result.price_max = money(aggregate.highPrice);
      if (result.price_min && result.price_min === result.price_max) priceCandidates.push(result.price_min);
    }
    const range = aggregate && result.price_min !== result.price_max;
    if (currency === 'BRL' && priceCandidates.length === 1 && !range) result.price = priceCandidates[0];
    if (!result.price && !range && priceCandidates.length <= 1 && currency === 'BRL') {
      result.price = money(meta(['product:price:amount', 'og:price:amount']));
      if (!result.price) {
        const e = doc.querySelector('meta[itemprop="price"],main [itemprop="offers"] [itemprop="price"]');
        if (e) result.price = money(e.getAttribute('content') || e.textContent);
      }
      if (!result.price && !shopee) {
        // Restrict to the main price block: never read installment or recommended-product prices.
        const e = doc.querySelector('.ui-pdp-price__second-line .andes-money-amount:not(.andes-money-amount--previous)');
        if (e && visible(e)) {
          const fraction = clean(e.querySelector('.andes-money-amount__fraction')?.textContent);
          const cents = clean(e.querySelector('.andes-money-amount__cents')?.textContent || '00');
          if (fraction) result.price = money(`${fraction},${cents}`);
        }
      }
      if (!result.price && shopee) result.price = money(text(['[data-testid="product-price"]', '[data-sqe="price"]']));
    }
    if (range || priceCandidates.length > 1) {
      delete result.price;
      result.warnings.push('Há preços diferentes por variação. Escolha a variação no anúncio e confira o preço antes de comparar.');
    }
    const breadcrumb = objects.find(o => typeIs(o, 'BreadcrumbList'));
    if (breadcrumb?.itemListElement) result.category = breadcrumb.itemListElement.map(i => clean(i.name || i.item?.name)).filter(n => n && n !== result.name && !/^(mercado livre|shopee|início|home)$/i.test(n)).slice(-3).join(' > ');
    if (!result.category) result.category = clean(product.category).slice(0, 300);
    const dimensions = [];
    const properties = Array.isArray(product.additionalProperty) ? product.additionalProperty : [];
    for (const row of doc.querySelectorAll('.andes-table__row, .ui-pdp-specs__table tr, [data-testid="product-attributes"] tr')) {
      const cells = row.querySelectorAll('th,td'); if (cells.length >= 2) properties.push({name: cells[0].textContent, value: cells[1].textContent});
    }
    for (const prop of properties) {
      const label = clean(prop.name), value = clean(prop.value);
      if (/^(altura|largura|comprimento|profundidade|dimensões)( do produto)?$/i.test(label) && value) dimensions.push(`${label}: ${value}`);
      if (/^peso( do produto)?$/i.test(label)) {
        const match = value.match(/^(\d+(?:[.,]\d+)?)\s*g$/i);
        if (match) result.weight_g = match[1].replace(',', '.');
      }
    }
    if (dimensions.length) result.dimensions = dimensions.join(' · ').slice(0, 500);
    const sold = text(['.ui-pdp-subtitle', '[data-testid="sold-count"]']);
    const count = sold.match(/(?:^|\s)(\d+)\s+vendidos\b/i);
    if (count && !/[+]|mil/i.test(sold)) result.displayed_sales = count[1];
    const shipping = product.offers?.shippingDetails;
    const details = Array.isArray(shipping) ? shipping : shipping ? [shipping] : [];
    if (details.length === 1 && details[0].shippingRate?.currency === 'BRL') {
      const v = String(details[0].shippingRate.value);
      result.buyer_shipping = /^0(?:\.0+)?$/.test(v) ? '0.00' : money(v);
    }
    const image = Array.isArray(product.image) ? product.image[0] : product.image?.url || product.image || meta(['og:image']);
    try {
      const imageUrl = new URL(image);
      if (imageUrl.protocol === 'https:' && ['mlstatic.com', 'susercontent.com', 'shopeemobile.com'].some(host => imageUrl.hostname === host || imageUrl.hostname.endsWith('.' + host))) result.image_url = imageUrl.href.slice(0, 2000);
    } catch (_) { /* No public product image. */ }
    if (!result.name) return {status: 'unavailable', message: 'O anúncio ainda não exibiu os dados do produto.'};
    if (!result.price) result.warnings.push('Preço único não identificado; nenhum valor de parcela ou recomendação foi usado.');
    return {status: result.price ? 'ok' : 'partial', data: result};
  }
  globalThis.ZoneListingExtractor = {extract};
})();
