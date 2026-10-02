/* Cliente compartido: JWT en cookies HttpOnly, CSRF y errores legibles. */
window.Pulso = (() => {
  let renewal = null;
  let toastTimer;
  const money = value => new Intl.NumberFormat('es-CL', {style: 'currency', currency: 'CLP', maximumFractionDigits: 0}).format(value || 0);
  const date = value => new Intl.DateTimeFormat('es-CL', {dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Santiago'}).format(new Date(value));
  const csrf = () => document.cookie.split('; ').find(item => item.startsWith('csrftoken='))?.split('=').slice(1).join('=') || '';
  const icons = () => window.lucide?.createIcons();
  function element(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (className) node.className = className;
    return node;
  }
  function icon(name) {
    const node = element('i'); node.dataset.lucide = name; return node;
  }
  function link(text, href, className = '') {
    const node = element('a', text, className); node.href = href; return node;
  }
  function iconButton(name, label, action, href) {
    const node = element(href ? 'a' : 'button', null, 'icon-button');
    node.title = label; node.setAttribute('aria-label', label); node.append(icon(name));
    if (href) node.href = href; else {node.type = 'button'; node.addEventListener('click', action);}
    return node;
  }
  function safeNext(value, fallback = '/') {
    if (!value || !value.startsWith('/') || value.startsWith('//') || value.includes('\\')) return fallback;
    const target = new URL(value, location.origin);
    if (target.origin !== location.origin || /^\/(api|ingresar|registrarse)\//.test(target.pathname)) return fallback;
    return target.pathname + target.search;
  }
  function login() {location.assign('/ingresar/?next=' + encodeURIComponent(location.pathname + location.search));}
  async function refresh() {
    if (!renewal) renewal = fetch('/api/auth/refresh/', {method: 'POST', credentials: 'same-origin', headers: {'X-CSRFToken': csrf()}})
      .then(response => response.ok).catch(() => false).finally(() => {renewal = null;});
    return renewal;
  }
  async function api(path, options = {}, retry = true) {
    const url = new URL(path, location.origin);
    if (url.origin !== location.origin || !url.pathname.startsWith('/api/')) throw new Error('Destino no valido.');
    const headers = {'Accept': 'application/json', 'X-CSRFToken': csrf(), ...options.headers};
    let body = options.body;
    if (body !== undefined && !(body instanceof FormData)) {headers['Content-Type'] = 'application/json'; body = JSON.stringify(body);}
    let response;
    try {response = await fetch(url, {...options, body, headers, credentials: 'same-origin', cache: 'no-store'});}
    catch {throw new Error('No se pudo conectar. Revisa tu conexion y vuelve a intentar.');}
    if (response.status === 401 && retry && !url.pathname.startsWith('/api/auth/')) {
      if (await refresh()) return api(path, options, false);
      login(); throw new Error('Tu sesion termino. Ingresa nuevamente.');
    }
    if (response.status === 204) return null;
    const data = await response.json().catch(() => ({message: 'El servidor no pudo completar la solicitud.'}));
    if (!response.ok) {
      const error = new Error(data.message || data.detail || 'Revisa los datos indicados.');
      error.details = data.errors || {}; error.status = response.status; error.code = data.code;
      throw error;
    }
    return data;
  }
  function showError(error, target = document.querySelector('#page-error')) {
    if (!target) {toast(error.message); return;}
    target.replaceChildren(element('strong', error.message));
    const list = element('ul');
    const flatten = (data, prefix = '') => {
      if (Array.isArray(data)) data.forEach(value => flatten(value, prefix));
      else if (data && typeof data === 'object') Object.entries(data).forEach(([key, value]) => flatten(value, key));
      else if (data) list.append(element('li', `${prefix ? prefix + ': ' : ''}${data}`));
    };
    flatten(error.details);
    if (list.children.length) target.append(list);
    target.hidden = false;
    document.querySelectorAll('[data-error-for]').forEach(node => {
      const message = error.details?.[node.dataset.errorFor];
      node.textContent = message ? (Array.isArray(message) ? message.join(' ') : String(message)) : '';
    });
    target.scrollIntoView({block: 'nearest', behavior: 'smooth'});
  }
  function clearError() {const target = document.querySelector('#page-error'); if (target) target.hidden = true;}
  function toast(message) {
    const node = document.querySelector('#toast'); node.textContent = message; node.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => {node.hidden = true;}, 4000);
  }
  async function busy(button, task) {
    if (button.disabled) return;
    button.disabled = true; button.setAttribute('aria-busy', 'true'); clearError();
    try {return await task();} catch (error) {showError(error);} finally {button.disabled = false; button.removeAttribute('aria-busy');}
  }
  function pager(data, load) {
    const host = document.querySelector('#pagination'); if (!host) return;
    host.replaceChildren();
    if (!data.previous && !data.next) return;
    const prev = iconButton('chevron-left', 'Pagina anterior', () => load(data.previous)); prev.disabled = !data.previous;
    const next = iconButton('chevron-right', 'Pagina siguiente', () => load(data.next)); next.disabled = !data.next;
    host.append(prev, element('span', `${data.count} resultados`), next); icons();
  }
  function confirm(message, reason = false) {
    return new Promise(resolve => {
      const dialog = document.querySelector('#confirm-dialog');
      const input = document.querySelector('#confirm-reason');
      document.querySelector('#confirm-message').textContent = message;
      document.querySelector('#confirm-reason-label').hidden = !reason;
      input.required = reason; input.value = ''; dialog.returnValue = '';
      dialog.addEventListener('close', () => resolve(dialog.returnValue === 'confirm' ? (reason ? input.value.trim() : true) : false), {once: true});
      dialog.showModal();
    });
  }
  document.querySelector('#menu-toggle')?.addEventListener('click', event => {
    const open = document.querySelector('#main-nav').classList.toggle('open');
    event.currentTarget.setAttribute('aria-expanded', String(open));
  });
  document.querySelector('[data-logout]')?.addEventListener('click', event => busy(event.currentTarget, async () => {
    await api('/api/auth/logout/', {method: 'POST'}); location.assign('/');
  }));
  document.querySelectorAll('[data-show-password]').forEach(button => button.addEventListener('click', () => {
    const input = button.parentElement.querySelector('input'); const visible = input.type === 'password';
    input.type = visible ? 'text' : 'password'; button.setAttribute('aria-label', visible ? 'Ocultar contrasena' : 'Mostrar contrasena');
    button.replaceChildren(icon(visible ? 'eye-off' : 'eye')); icons();
  }));
  document.querySelector('#print-ticket')?.addEventListener('click', () => window.print());
  document.querySelectorAll('.manage-nav nav a').forEach(node => {
    if (location.pathname === new URL(node.href).pathname) {node.classList.add('active'); node.setAttribute('aria-current', 'page');}
  });
  icons();
  return {api, csrf, refresh, icons, money, date, element, icon, link, iconButton, safeNext, login, showError, clearError, toast, busy, pager, confirm};
})();
