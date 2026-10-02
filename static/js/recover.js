/* Una sola renovacion evita bucles si la sesion termino o la cuenta se desactivo. */
(async () => {
  if (await window.Pulso.refresh()) location.reload();
  else location.replace('/ingresar/?next=' + encodeURIComponent(location.pathname + location.search));
})();
