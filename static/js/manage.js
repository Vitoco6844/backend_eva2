/* CRUD individual del organizador, con confirmacion y errores de campo. */
(() => {
  const P = window.Pulso, list = document.querySelector('#management-list'), form = document.querySelector('#resource-form');
  if (list) {
    const kind = list.dataset.kind, host = document.querySelector('#resource-table');
    let currentPath = `/api/${kind}/`;
    const configurations = {
      recintos: {head: ['Recinto', 'Ciudad', 'Direccion', 'Estado'], cells: row => [row.name, row.city, row.address, row.active ? 'Activo' : 'Inactivo']},
      eventos: {head: ['Evento', 'Fecha', 'Recinto', 'Estado'], cells: row => [row.name, P.date(row.starts_at), row.venue_name, row.status]},
      sectores: {head: ['Localidad', 'Evento', 'Precio CLP', 'Capacidad', 'Disponibles', 'Estado'], cells: row => [row.name, row.event_name, P.money(row.current_amount), row.capacity, row.available, row.active ? 'Activo' : 'Inactivo']}
    };
    async function load(path) {
      currentPath = path; P.clearError();
      try {
        const data = await P.api(path), config = configurations[kind];
        const table = P.element('table'), head = P.element('thead'), tr = P.element('tr'), body = P.element('tbody');
        config.head.forEach(name => tr.append(P.element('th', name))); tr.append(P.element('th', 'Acciones')); head.append(tr);
        data.results.forEach(row => {
          const tr = P.element('tr'); config.cells(row).forEach(value => tr.append(P.element('td', value)));
          const td = P.element('td'), actions = P.element('div', null, 'row-actions');
          if (kind === 'eventos') actions.append(P.iconButton('armchair', 'Agregar localidad', null, `/gestion/sectores/nuevo/?evento=${row.id}`));
          actions.append(P.iconButton('pencil', 'Editar ' + row.name, null, `/gestion/${kind}/${row.id}/editar/`));
          const remove = P.iconButton('trash-2', 'Eliminar ' + row.name, async () => {
            if (!await P.confirm(`¿Eliminar ${row.name}? Los registros con compras asociadas no pueden borrarse.`)) return;
            P.busy(remove, async () => {await P.api(`/api/${kind}/${row.id}/`, {method: 'DELETE'}); await load(`/api/${kind}/`); P.toast('Registro eliminado.');});
          }); remove.classList.add('danger'); actions.append(remove); td.append(actions); tr.append(td); body.append(tr);
        });
        if (!data.results.length) {const tr = P.element('tr'), td = P.element('td', 'No hay registros para mostrar.', 'empty'); td.colSpan = config.head.length + 1; tr.append(td); body.append(tr);}
        table.append(head, body); host.replaceChildren(table); document.querySelector('#result-count').textContent = `${data.count} registros`; P.pager(data, load); P.icons();
      } catch (error) {P.showError(error);}
    }
    document.querySelector('#resource-filter')?.addEventListener('change', event => load(`/api/${kind}/?estado=${event.target.value}`));
    load(currentPath);
  }
  function formData() {
      const data = new FormData(form); data.delete('csrfmiddlewaretoken');
      form.querySelectorAll('input[type=checkbox]').forEach(input => data.set(input.name, String(input.checked)));
      const dateInput = form.querySelector('[name=starts_at]');
      // datetime-local se interpreta en Chile en el servidor, no en la zona del navegador.
      if (dateInput) data.set('starts_at', dateInput.value);
      const image = data.get('image'); if (image instanceof File && !image.size) data.delete('image');
      return data;
  }
  const initial = form ? formData() : null;
  if (form) form.addEventListener('submit', event => {
    event.preventDefault(); P.busy(form.querySelector('[type=submit]'), async () => {
      const data = formData();
      const id = form.dataset.id;
      // PATCH solo cambia campos editados, sin truncar fechas historicas a minutos.
      if (id) for (const [key, value] of Array.from(data.entries())) {
        if (!(value instanceof File) && value === initial.get(key)) data.delete(key);
      }
      if (id && !Array.from(data.keys()).length) {location.assign(`/gestion/${form.dataset.kind}/`); return;}
      await P.api(`/api/${form.dataset.kind}/${id ? id + '/' : ''}`, {method: id ? 'PATCH' : 'POST', body: data});
      location.assign(`/gestion/${form.dataset.kind}/`);
    });
  });
})();
