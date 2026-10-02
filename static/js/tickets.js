/* Cada resultado es una unidad con UUID, incluso cuando la cantidad comprada fue mayor. */
(() => {
  const P = window.Pulso, host = document.querySelector('#ticket-list');
  async function load(path) {
    try {
      const data = await P.api(path); host.replaceChildren();
      if (!data.results.length) host.append(P.element('p', 'Tus entradas apareceran aqui despues del pago.', 'empty'));
      data.results.forEach(ticket => {
        const row = P.element('article', null, 'purchase-card'), info = P.element('div');
        info.append(P.element('h2', ticket.event_name), P.element('p', `${ticket.sector_name} · ${P.date(ticket.starts_at)}`), P.element('span', ticket.status, 'badge'));
        row.append(info, P.link('Ver entrada', `/entradas/${ticket.id}/`, 'button secondary')); host.append(row);
      }); P.pager(data, load);
    } catch (error) {P.showError(error);}
  }
  load('/api/mis-entradas/');
})();
