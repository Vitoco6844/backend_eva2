/* Ingreso y registro regresan a paginas HTML, nunca a endpoints. */
(() => {
  const P = window.Pulso, form = document.querySelector('#auth-form');
  const next = new URLSearchParams(location.search).get('next');
  if (next) document.querySelector('.auth-switch a').search = '?next=' + encodeURIComponent(P.safeNext(next));
  form.addEventListener('submit', event => {
    event.preventDefault(); P.busy(form.querySelector('[type=submit]'), async () => {
      const body = Object.fromEntries(new FormData(form)); delete body.csrfmiddlewaretoken;
      const user = await P.api(`/api/auth/${form.dataset.mode}/`, {method: 'POST', body});
      location.assign(P.safeNext(next, user.role === 'ORGANIZADOR' ? '/gestion/' : '/'));
    });
  });
})();
