/* Listado administrativo paginado; el detalle concentra las transiciones. */
(() => {
  const P = window.Pulso, form = document.querySelector('#sales-filters'), host = document.querySelector('#sales-table');
  async function load(path) {
    P.clearError();
    try {
      const data = await P.api(path), table = P.element('table'), head = P.element('thead'), row = P.element('tr'), body = P.element('tbody');
      ['Compra', 'Cliente', 'Fecha', 'Estado', 'Total', ''].forEach(text => row.append(P.element('th', text))); head.append(row);
      data.results.forEach(order => {
        const row = P.element('tr'); [order.id.slice(0, 8), order.buyer, P.date(order.created_at)].forEach(text => row.append(P.element('td', text)));
        const state = P.element('td'); state.append(P.element('span', order.status, 'badge ' + order.status.toLowerCase()));
        const action = P.element('td'); action.append(P.iconButton('arrow-up-right', 'Ver compra', null, `/compras/${order.id}/`));
        row.append(state, P.element('td', P.money(order.total)), action); body.append(row);
      });
      if (!data.results.length) {const row = P.element('tr'), cell = P.element('td', 'No hay ventas con estos filtros.', 'empty'); cell.colSpan = 6; row.append(cell); body.append(row);}
      table.append(head, body); host.replaceChildren(table); P.pager(data, load); P.icons();
    } catch (error) {P.showError(error);}
  }
  form.addEventListener('submit', event => {event.preventDefault(); load('/api/compras/?' + new URLSearchParams(new FormData(form)));});
  load('/api/compras/');
})();
