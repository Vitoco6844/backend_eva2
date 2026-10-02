/* Compras del usuario autenticado; el filtrado de propietario se hace en servidor. */
(() => {
  const P = window.Pulso, host = document.querySelector('#purchases'), filter = document.querySelector('#purchase-status');
  async function load(path) {
    P.clearError();
    try {
      const data = await P.api(path); host.replaceChildren();
      if (!data.results.length) host.append(P.element('p', 'Todavia no tienes compras con este estado.', 'empty'));
      data.results.forEach(order => {
        const row = P.element('article', null, 'purchase-card'), info = P.element('div'), right = P.element('div', null, 'right');
        info.append(P.element('h2', order.lines.map(line => line.event_name).filter((v, i, a) => a.indexOf(v) === i).join(' + ')), P.element('p', `${P.date(order.created_at)} · ${order.id.slice(0, 8)}`), P.element('span', order.status, 'badge ' + order.status.toLowerCase()));
        right.append(P.element('strong', P.money(order.total)), P.link('Ver compra', `/compras/${order.id}/`, 'button secondary')); row.append(info, right); host.append(row);
      }); P.pager(data, load);
    } catch (error) {P.showError(error);}
  }
  filter.addEventListener('change', () => load('/api/compras/?status=' + filter.value)); load('/api/compras/');
})();
