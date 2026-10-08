(() => {
  if (window !== window.top) return;
  window.addEventListener('message', async event => {
    if (event.source !== window || event.origin !== location.origin) return;
    const data = event.data;
    if (!data || data.channel !== 'zone-listing-request-v1' || !/^[a-zA-Z0-9-]{1,80}$/.test(data.requestId || '')) return;
    const reply = result => window.postMessage({channel: 'zone-listing-response-v1', requestId: data.requestId, ...result}, location.origin);
    if (data.action === 'ping') { reply({status: 'ready', version: chrome.runtime.getManifest().version}); return; }
    if (!['read', 'focus'].includes(data.action) || typeof data.url !== 'string' || data.url.length > 4096) return;
    try { reply(await chrome.runtime.sendMessage({action: data.action, url: data.url})); }
    catch (_) { reply({status: 'error', message: 'A extensão foi atualizada ou desconectada. Recarregue a calculadora.'}); }
  });
})();
