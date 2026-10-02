/* Filtros reales contra la API; texto del catalogo insertado sin interpretar HTML. */
(() => {
  const P = window.Pulso, form = document.querySelector('#filters'), grid = document.querySelector('#events-grid');
  let sequence = 0;
  async function load(path) {
    const current = ++sequence; P.clearError(); grid.setAttribute('aria-busy', 'true');
    try {
      const data = await P.api(path);
      if (current !== sequence) return;
      grid.replaceChildren(); document.querySelector('#result-count').textContent = `${data.count} eventos`;
      if (!data.results.length) grid.append(P.element('p', 'No encontramos eventos con estos filtros.', 'empty'));
      for (const event of data.results) {
        const card = document.querySelector('#event-card-template').content.cloneNode(true);
        card.querySelectorAll('a').forEach(a => {a.href = `/eventos/${event.id}/`;});
        card.querySelector('img').src = event.cover_url; card.querySelector('img').alt = `Imagen ilustrativa de ${event.name}`;
        card.querySelector('.event-city').textContent = event.city;
        card.querySelector('.event-date').textContent = P.date(event.starts_at);
        card.querySelector('.event-title').textContent = event.name;
        card.querySelector('.event-venue').textContent = event.venue_name;
        card.querySelector('.event-price').textContent = event.price_from ? `Desde ${P.money(event.price_from)}` : 'Agotado';
        grid.append(card);
      }
      P.pager(data, load); P.icons();
    } catch (error) {if (current === sequence) {grid.replaceChildren(); P.showError(error);}}
    finally {if (current === sequence) grid.removeAttribute('aria-busy');}
  }
  function search() {
    const params = new URLSearchParams();
    for (const [key, value] of new FormData(form)) if (value) params.set(key, value);
    history.replaceState(null, '', location.pathname + (params.size ? '?' + params : ''));
    load('/api/eventos/?catalogo=true&' + params);
  }
  for (const [key, value] of new URLSearchParams(location.search)) {
    const control = form.elements.namedItem(key);
    if (control) {if (control.type === 'checkbox') control.checked = value === 'true'; else control.value = value;}
  }
  form.addEventListener('submit', event => {event.preventDefault(); search();});
  form.addEventListener('reset', () => setTimeout(search, 0)); search();
})();
