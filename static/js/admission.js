/* Un lector QR puede escribir el UUID; validar por segunda vez devuelve conflicto. */
(() => {
  const P = window.Pulso, form = document.querySelector('#admission-form');
  form.addEventListener('submit', event => {
    event.preventDefault(); const result = document.querySelector('#admission-result'); result.hidden = true;
    P.busy(form.querySelector('[type=submit]'), async () => {
      const ticket = await P.api('/api/entradas/validar/', {method: 'POST', body: {event: Number(form.elements.event.value), ticket: form.elements.ticket.value.trim()}});
      result.textContent = `Ingreso registrado. Entrada ${ticket.id}.`; result.hidden = false; form.elements.ticket.value = ''; form.elements.ticket.focus();
    });
  });
})();
