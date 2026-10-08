const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '../..'), site = path.join(root, 'site');
const app = 'https://davidaosrj.github.io/zGeradorDeAnuncio';
const ml = 'https://produto.mercadolivre.com.br/MLB-123456-dinossauro-_JM';
const shopee = 'https://shopee.com.br/Dinossauro-i.123.456';
const fixture = (platform, price, extra = '') => `<!doctype html><html><body><main><h1>${platform} Dinossauro articulado</h1><script type="application/ld+json">${JSON.stringify({'@type':'Product', name:`${platform} Dinossauro articulado`, category:'Brinquedos', offers:{'@type':'Offer',price,priceCurrency:'BRL'},additionalProperty:[{name:'Peso',value:'55 g'},{name:'Altura',value:'10 cm'}]})}</script>${extra}</main><aside><p>Recomendado: R$ 999,90</p><p>Parcele em 3x R$ 10,00</p></aside></body></html>`;
(async () => {
  const profile = await fs.mkdtemp(path.join(os.tmpdir(), 'reader-browser-'));
  let context;
  try {
    const extension = path.join(root, 'extensions/leitor-anuncios');
    context = await chromium.launchPersistentContext(profile, {channel:'chromium', headless:true, ignoreDefaultArgs:['--disable-extensions'], args:[`--disable-extensions-except=${extension}`, `--load-extension=${extension}`]});
    if (!context.serviceWorkers().length) await context.waitForEvent('serviceworker');
    await context.route(`${app}/**`, async route => {
      const pathname = new URL(route.request().url()).pathname.slice('/zGeradorDeAnuncio'.length);
      let file = path.resolve(site, '.' + pathname);
      if (!file.startsWith(site + path.sep)) return route.abort();
      if ((await fs.stat(file)).isDirectory()) file = path.join(file, 'index.html');
      await route.fulfill({body: await fs.readFile(file), contentType: file.endsWith('.js') ? 'application/javascript' : file.endsWith('.png') ? 'image/png' : 'text/html; charset=utf-8'});
    });
    await context.route(ml, route => route.fulfill({body:fixture('ML', '50.00'),contentType:'text/html'}));
    await context.route(shopee, route => route.fulfill({body:fixture('Shopee', '39.90'),contentType:'text/html'}));
    const page = await context.newPage();
    await page.goto(`${app}/impressao-3d/`);
    await page.waitForFunction(() => document.querySelector('#reader-state').textContent.includes('conectado'));
    await page.getByRole('button',{name:'Carregar exemplo da ADR-002'}).click();
    await page.getByRole('button',{name:'Adicionar concorrente'}).click();
    await page.locator('#competitors [name=url]').fill(ml);
    // No blur or extra click: pasting/filling the link starts the lookup.
    await page.waitForFunction(() => document.querySelector('#competitors [name=price]').value === '50.00');
    assert.equal(await page.locator('#competitors [name=name]').inputValue(), 'ML Dinossauro articulado');
    assert.equal(await page.locator('#competitors [name=category]').inputValue(), 'Brinquedos');
    assert.equal(await page.locator('#competitors [name=weight_g]').inputValue(), '55');
    assert.match(await page.locator('#competitors [name=dimensions]').inputValue(), /10 cm/);
    assert.equal(await page.locator('#competitors [name=retrieval_method]').inputValue(), 'browser-extension');
    await page.getByRole('button',{name:'Calcular preço e lucro'}).click();
    await page.waitForFunction(() => document.querySelector('#comparisons').textContent.includes('R$ 50,00'));
    await page.locator('#competitors [name=url]').fill(shopee);
    await page.waitForFunction(() => document.querySelector('#competitors [name=price]').value === '39.90');
    assert.equal(await page.locator('#competitors [name=name]').inputValue(), 'Shopee Dinossauro articulado');
    assert.equal(await page.locator('#competitors [name=marketplace]').inputValue(), 'shopee');
    // Manual changes made during an update must survive the response.
    await page.getByRole('button', {name:'Preencher pelo link',exact:true}).click();
    await page.locator('#competitors [name=name]').fill('Nome conferido por mim');
    await page.waitForFunction(() => ![...document.querySelectorAll('#competitors button')].find(e=>e.textContent==='Preencher pelo link').disabled);
    assert.equal(await page.locator('#competitors [name=name]').inputValue(), 'Nome conferido por mim');
    // Superseded lookup responses cannot populate the new competitor URL.
    await page.locator('#competitors [name=url]').fill(ml);
    await page.locator('#competitors [name=url]').blur();
    await page.locator('#competitors [name=url]').fill(shopee);
    await page.locator('#competitors [name=url]').blur();
    await page.waitForFunction(() => document.querySelector('#competitors [name=price]').value === '39.90');
    assert.equal(await page.locator('#competitors [name=name]').inputValue(), 'Shopee Dinossauro articulado');
    // Test ambiguous and blocked pages without reading account data.
    const productPage = await context.newPage(); await productPage.goto(shopee);
    await productPage.addScriptTag({path:path.join(extension, 'extractor.js')});
    const extract = () => productPage.evaluate(() => ZoneListingExtractor.extract());
    assert.equal((await extract()).data.price, '39.90');
    await productPage.evaluate(() => { document.querySelector('script[type="application/ld+json"]').textContent=JSON.stringify({'@type':'Product',name:'Kit',offers:{'@type':'AggregateOffer',lowPrice:'10',highPrice:'50',priceCurrency:'BRL'}}); });
    let result = await extract(); assert.equal(result.status, 'partial'); assert.equal(result.data.price, undefined);
    await productPage.evaluate(() => { document.body.innerHTML='<h1>Login Necessário</h1><p>Faça login para continuar</p>'; });
    assert.equal((await extract()).status, 'needs_action');
    await productPage.evaluate(() => { document.body.innerHTML='<main><h1>Produto</h1><div class="ui-pdp-price__second-line"><span class="andes-money-amount"><span class="andes-money-amount__fraction">1.234</span><span class="andes-money-amount__cents">56</span></span></div></main><aside>3x R$ 5,00</aside>'; });
    result = await productPage.evaluate(() => ZoneListingExtractor.extract(document, 'https://produto.mercadolivre.com.br/MLB-123456-x-_JM'));
    assert.equal(result.data.price, '1234.56');
    await productPage.evaluate(() => { document.body.innerHTML='<h1>Produto</h1><script type="application/ld+json">{"@type":"Product","name":"Produto","offers":{"price":"1.000","priceCurrency":"BRL"}}</script>'; });
    assert.equal((await extract()).data.price, '1.00');
    // Extension refuses non-listing URLs even on an allowed marketplace host.
    result = await page.evaluate(() => ListingReader.read('https://shopee.com.br/user/account'));
    assert.equal(result.status, 'error');
    result = await page.evaluate(() => ListingReader.read('https://shopee.com.br.evil.example/Produto-i.123.456'));
    assert.equal(result.status, 'error');
    console.log('Reader OK: real extension bridge, automatic ML/Shopee fields, ranges, login, installment isolation and URL limits.');
  } finally {
    if (context) await context.close();
    await fs.rm(profile, {recursive:true,force:true});
  }
})().catch(error => {console.error(error);process.exitCode=1;});
