'use strict';
const waitingTabs = new Map(), jobs = new Map();
function trustedSender(sender) {
  if (sender.frameId !== 0 || !sender.tab?.id || !sender.url) return false;
  try {
    const url = new URL(sender.url);
    return (url.origin === 'https://davidaosrj.github.io' && url.pathname.startsWith('/zGeradorDeAnuncio/')) ||
      (['http://localhost:8000', 'http://127.0.0.1:8000'].includes(url.origin) && /^\/impressao-3d\/?$/.test(url.pathname));
  } catch (_) { return false; }
}
function listing(value, productOnly = false) {
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password || url.port) return null;
    const host = url.hostname, under = domain => host === domain || host.endsWith('.' + domain);
    const shopee = under('shopee.com.br') || host === 'shope.ee';
    const ml = under('mercadolivre.com.br') || under('mercadolivre.com') || under('mercadolibre.com');
    if (!shopee && !ml) return null;
    const product = shopee ? /(?:-i\.\d+\.\d+|\/product\/\d+\/\d+)(?:\/|$)/.test(url.pathname) : /(?:MLB-?\d+|\/up\/MLBU\d+)/i.test(url.pathname);
    const short = shopee ? ['s.shopee.com.br', 'shope.ee'].includes(host) && /^\/[\w-]+\/?$/.test(url.pathname) : /^\/sec\/[\w-]+\/?$/.test(url.pathname);
    return product || (!productOnly && short) ? {url: url.href, marketplace: shopee ? 'shopee' : 'mercado_livre'} : null;
  } catch (_) { return null; }
}
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function read(url, owner) {
  const source = listing(url);
  if (!source) return {status: 'error', message: 'Use um link HTTPS de anúncio ou link curto oficial da Shopee ou Mercado Livre.'};
  const previous = jobs.get(owner);
  const job = {cancelled: false, tabId: null}; jobs.set(owner, job);
  if (previous) {
    previous.cancelled = true;
    if (previous.tabId) { try { await chrome.tabs.remove(previous.tabId); } catch (_) {} }
  }
  const key = `${owner}|${source.url}`;
  let tab, last = {status: 'unavailable', message: 'O anúncio não exibiu dados legíveis. Abra a aba do anúncio e tente novamente.'};
  try {
    if (job.cancelled) return {status: 'cancelled'};
    const existing = waitingTabs.get(key);
    if (existing) { try { tab = await chrome.tabs.get(existing); } catch (_) { waitingTabs.delete(key); } }
    const fresh = !tab;
    if (fresh) tab = await chrome.tabs.create({url: 'about:blank', active: false});
    job.tabId = tab.id;
    if (job.cancelled) { await chrome.tabs.remove(tab.id); return {status: 'cancelled'}; }
    waitingTabs.set(key, tab.id);
    if (fresh) await chrome.tabs.update(tab.id, {url: source.url});
    const deadline = Date.now() + 24000;
    let stable = '', stableCount = 0;
    while (Date.now() < deadline) {
      await pause(1000);
      if (job.cancelled) return {status: 'cancelled'};
      tab = await chrome.tabs.get(tab.id);
      if (tab.status !== 'complete') continue;
      const current = listing(tab.url || '', true);
      if (!current || current.marketplace !== source.marketplace) {
        last = {status: 'needs_action', message: 'O anúncio redirecionou para login, verificação ou outra página. Conclua o acesso na aba do anúncio e tente novamente.'};
        if (listing(tab.url || '')) continue; // Official short redirect is still settling.
        break;
      }
      try {
        await chrome.scripting.executeScript({target: {tabId: tab.id}, files: ['extractor.js']});
        const results = await chrome.scripting.executeScript({target: {tabId: tab.id}, func: () => globalThis.ZoneListingExtractor.extract()});
        last = results[0]?.result || last;
      } catch (_) { continue; }
      if (last.status === 'needs_action') break;
      if (last.status === 'ok') {
        const signature = JSON.stringify([last.data.name, last.data.price]);
        stableCount = signature === stable ? stableCount + 1 : 1; stable = signature;
        if (stableCount >= 2) {
          // Only the tab created for this lookup is closed; no user tabs are inspected.
          await chrome.tabs.remove(tab.id); waitingTabs.delete(key);
          return last;
        }
      }
    }
    return {...last, can_focus: true};
  } catch (_) {
    return {status: 'error', message: 'Não foi possível ler a aba do anúncio. Verifique a extensão e tente novamente.'};
  } finally { if (jobs.get(owner) === job) jobs.delete(owner); }
}
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if (!trustedSender(sender)) { respond({status: 'error', message: 'Origem não autorizada.'}); return; }
  if (!message || typeof message.url !== 'string' || message.url.length > 4096) return;
  if (message.action === 'read') {
    read(message.url, sender.tab.id).then(respond, () => respond({status: 'error', message: 'Falha na consulta.'})); return true;
  }
  if (message.action === 'focus') {
    const source = listing(message.url), tabId = source && waitingTabs.get(`${sender.tab.id}|${source.url}`);
    if (!tabId) { respond({status: 'error', message: 'Consulte o anúncio novamente.'}); return; }
    chrome.tabs.update(tabId, {active: true}).then(() => respond({status: 'focused'}), () => respond({status: 'error', message: 'A aba foi fechada. Consulte novamente.'})); return true;
  }
});
chrome.tabs.onRemoved.addListener(tabId => { for (const [key, value] of waitingTabs) if (value === tabId || key.startsWith(`${tabId}|`)) waitingTabs.delete(key); });
