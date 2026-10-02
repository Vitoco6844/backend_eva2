/* Transiciones explicitas, idempotentes en servidor y sin cobros reales. */
(() => {
  const P = window.Pulso, id = document.querySelector('#purchase-detail').dataset.id;
  document.querySelectorAll('[data-pay]').forEach(button => button.addEventListener('click', () => P.busy(button, async () => {
    await P.api(`/api/compras/${id}/pagar/`, {method: 'POST', body: {result: button.dataset.pay}}); location.reload();
  })));
  document.querySelectorAll('[data-order-status]').forEach(button => button.addEventListener('click', () => P.busy(button, async () => {
    let reason = '';
    if (button.dataset.orderStatus === 'CANCELADO') {
      reason = await P.confirm('Se anularan todas las entradas y se liberaran los cupos pagados, incluso si se registraron ingresos. No hay devolucion bancaria real.', true);
      if (!reason) return;
    } else if (!await P.confirm(button.dataset.orderStatus === 'ENTREGADO' ? 'Registrar el ingreso de todas las entradas de esta compra, incluidos sus distintos eventos.' : 'Confirmar el pago de demostracion y emitir las entradas.')) return;
    await P.api(`/api/compras/${id}/estado/`, {method: 'PATCH', body: {status: button.dataset.orderStatus, reason}}); location.reload();
  })));
})();
