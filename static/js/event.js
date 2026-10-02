/* Comprar exige sesion antes de enviar una sola unidad al carrito. */
document.querySelectorAll('[data-add-sector]').forEach(form => form.addEventListener('submit', event => {
  event.preventDefault(); const P = window.Pulso;
  if (document.body.dataset.authenticated !== 'true') {P.login(); return;}
  P.busy(form.querySelector('button'), async () => {
    await P.api('/api/carrito/items/', {method: 'POST', body: {sector: Number(form.dataset.addSector), quantity: Number(form.elements.quantity.value)}});
    P.toast('Entrada agregada a tu carrito.');
  });
}));
