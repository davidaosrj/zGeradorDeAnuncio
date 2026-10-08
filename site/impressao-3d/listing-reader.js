/* Page-side bridge. The extension supplies structured product fields, never HTML. */
(() => {
  const pending = new Map();
  window.addEventListener('message', event => {
    if (event.source !== window || event.origin !== location.origin || event.data?.channel !== 'zone-listing-response-v1') return;
    const task = pending.get(event.data.requestId);
    if (task) { pending.delete(event.data.requestId); clearTimeout(task.timer); clearInterval(task.retry); task.resolve(event.data); }
  });
  function request(action, url = '', timeout = 32000) {
    return new Promise(resolve => {
      const requestId = crypto.randomUUID();
      let retry;
      const timer = setTimeout(() => { pending.delete(requestId); clearInterval(retry); resolve({status: 'missing', message: action === 'ping' ? 'Instale o Leitor de anúncios e recarregue esta página para preencher automaticamente.' : 'A consulta demorou mais que o esperado. Verifique a aba do anúncio e tente novamente.'}); }, timeout);
      const send = () => window.postMessage({channel: 'zone-listing-request-v1', action, requestId, url}, location.origin);
      if (action === 'ping') retry = setInterval(send, 150);
      pending.set(requestId, {resolve, timer, retry});
      send();
    });
  }
  window.ListingReader = {
    available: () => request('ping', '', 900),
    read: async url => { const state = await request('ping', '', 900); return state.status === 'ready' ? request('read', url) : state; },
    focus: url => request('focus', url, 2000),
  };
})();
