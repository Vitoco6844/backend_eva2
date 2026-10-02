/* El servidor firma el resumen; el navegador no fija precio, usuario ni total. */
(() => {
  const P = window.Pulso, host = document.querySelector('#cart-items'), checkout = document.querySelector('#checkout');
  let cart, key = crypto.randomUUID();
  function render(data) {
    cart = data; host.replaceChildren();
    document.querySelector('#cart-quantity').textContent = data.items.reduce((n, item) => n + item.quantity, 0);
    document.querySelector('#cart-total').textContent = P.money(data.total);
    checkout.disabled = !data.items.length || data.items.some(i => !i.sellable || i.quantity > i.available);
    if (!data.items.length) {
      const empty = P.element('div', null, 'empty-state'); empty.append(P.icon('shopping-bag'), P.element('h2', 'Tu proximo concierto te espera'), P.link('Explorar eventos', '/', 'button')); host.append(empty);
    }
    for (const item of data.items) {
      const row = P.element('article', null, 'cart-item');
      row.append(P.element('p', item.sector_name, 'eyebrow'), P.element('h2', item.event_name), P.element('p', `${P.date(item.starts_at)} · ${item.venue}`));
      if (!item.sellable || item.quantity > item.available) row.append(P.element('p', 'La disponibilidad cambio. Ajusta o elimina esta localidad.', 'notice error'));
      const controls = P.element('div', null, 'cart-item-controls'), tools = P.element('div', null, 'quantity-tools');
      const label = P.element('label', 'Cantidad'), input = P.element('input'); input.type = 'number'; input.min = 1; input.max = 100; input.value = item.quantity; label.append(input);
      const save = P.iconButton('check', 'Actualizar cantidad', () => {
        if (!input.reportValidity()) return;
        P.busy(save, async () => {render(await P.api(`/api/carrito/items/${item.id}/`, {method: 'PATCH', body: {quantity: Number(input.value)}})); key = crypto.randomUUID();});
      });
      const remove = P.iconButton('trash-2', 'Eliminar del carrito', () => P.busy(remove, async () => {
        render(await P.api(`/api/carrito/items/${item.id}/`, {method: 'DELETE'})); key = crypto.randomUUID();
      }));
      tools.append(label, save, remove); controls.append(tools, P.element('strong', P.money(item.subtotal))); row.append(controls); host.append(row);
    }
    P.icons();
  }
  async function load() {try {render(await P.api('/api/carrito/'));} catch (error) {P.showError(error);}}
  checkout.addEventListener('click', async () => {
    await P.busy(checkout, async () => {
    try {
      const order = await P.api('/api/checkout/', {method: 'POST', body: {checkout_key: key, version: cart.version, quote: cart.quote}});
      location.assign(`/compras/${order.id}/`);
    } catch (error) {
      if (error.status === 409) {await load(); key = crypto.randomUUID();}
      throw error;
    }
    });
    checkout.disabled = !cart?.items.length || cart.items.some(i => !i.sellable || i.quantity > i.available);
  });
  load();
})();
