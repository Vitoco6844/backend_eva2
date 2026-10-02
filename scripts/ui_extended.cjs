/* Casos de interfaz adicionales: registro, expiracion, filtros y CRUD completo. */
const {chromium} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const secret = fs.readFileSync(path.join(root, '.local/ui_password'), 'utf8');
const origin = `http://127.0.0.1:${process.env.QA_PORT || '8012'}`;
(async () => {
  const browser = await chromium.launch({headless: true, channel: process.env.PW_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined)});
  const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  async function logout() {
    const menu = page.locator('#menu-toggle'); if (await menu.isVisible() && !await page.locator('[data-logout]').isVisible()) await menu.click();
    await page.locator('[data-logout]').click(); await page.locator('body[data-authenticated="false"]').waitFor();
  }
  async function save(kind) {await page.locator('#resource-form [type=submit]').click(); await page.waitForURL(`**/gestion/${kind}/`); await page.locator('tbody tr').first().waitFor();}
  async function shot(name) {await page.screenshot({path: path.join(root, '.local/screenshots', name + '.png'), fullPage: true});}
  try {
    await page.goto(origin + '/registrarse/');
    const username = 'UI_' + Date.now();
    for (const [name, value] of Object.entries({username, first_name:'Nuevo', last_name:'Espectador', email:username+'@example.test', password:secret, password_confirmation:secret})) await page.locator(`[name=${name}]`).fill(value);
    await page.locator('#auth-form [type=submit]').click(); await page.waitForURL(origin + '/');
    await page.locator('.event-card').first().waitFor();
    await page.locator('[name=ciudad]').selectOption('Concepcion'); await page.locator('#filters [type=submit]').click();
    await page.waitForFunction(() => document.querySelector('#result-count').textContent === '2 eventos');
    await page.goto(origin + '/mis-compras/');
    assert.equal(await page.locator('#purchase-status option').count(), 5);
    await page.getByRole('link', {name:'Mis entradas', exact:true}).click(); await page.waitForURL('**/mis-entradas/');
    // Reemplazar solamente el access de la sesion de QA prueba el refresh HttpOnly real.
    await context.addCookies([{name:'pulso_access', value:'invalid-expired-test-token', domain:'127.0.0.1', path:'/', httpOnly:true, sameSite:'Lax'}]);
    await page.goto(origin + '/carrito/'); await page.locator('#cart-items .empty-state').waitFor();
    assert.equal(await page.locator('body').getAttribute('data-authenticated'), 'true');
    await logout();
    await page.goto(origin + '/ingresar/'); await page.locator('[name=username]').fill('QAManager'); await page.locator('[name=password]').fill(secret);
    await page.locator('#auth-form [type=submit]').click(); await page.waitForURL('**/gestion/');
    await page.goto(origin + '/gestion/eventos/nuevo/');
    await page.locator('[name=name]').fill('Evento UI'); await page.locator('[name=artist]').fill('Artista UI');
    await page.locator('[name=venue]').selectOption({index:1});
    const future = new Date(Date.now() + 86400000 * 90).toISOString().slice(0,16);
    await page.locator('[name=starts_at]').fill(future); await page.locator('textarea[name=description]').fill('Evento sintetico de prueba de interfaz.');
    await shot('13-event-form'); await save('eventos');
    const row = page.locator('tr', {hasText:'Evento UI'});
    await row.locator('[title="Agregar localidad"]').click();
    await page.locator('[name=name]').fill('Localidad UI'); await page.locator('[name=capacity]').fill('20'); await page.locator('[name=price]').fill('15000');
    await save('sectores');
    await page.locator('[title="Editar Localidad UI"]').click(); await page.locator('[name=price]').fill('17000');
    await shot('14-sector-form'); await save('sectores');
    await page.goto(origin + '/gestion/eventos/'); await page.locator('[title="Editar Evento UI"]').click();
    await page.locator('[name=status]').selectOption('PUBLICADO'); await save('eventos');
    await page.goto(origin + '/'); await page.locator('.event-title', {hasText:'Evento UI'}).waitFor();
    await page.goto(origin + '/gestion/ventas/'); assert.equal(await page.locator('[name=status] option').count(), 5);
    await page.setViewportSize({width:360,height:900});
    await page.goto(origin + '/gestion/eventos/'); await page.locator('tbody tr').first().waitFor();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth+1), false); await shot('15-management-mobile');
    await page.locator('[title="Editar Evento UI"]').click();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth+1), false); await shot('16-form-mobile');
    await page.locator('[name=status]').selectOption('ARCHIVADO'); await save('eventos');
    await page.setViewportSize({width:1440,height:1000});
    await page.goto(origin + '/'); await page.locator('.event-card').first().waitFor();
    assert.equal(await page.locator('.event-title', {hasText:'Evento UI'}).count(), 0);
    await page.goto(origin + '/gestion/eventos/'); await page.locator('[title="Eliminar Evento UI"]').click(); await page.locator('#confirm-dialog [value=confirm]').click();
    await page.locator('tr', {hasText:'Evento UI'}).waitFor({state:'detached'});
    assert.deepEqual(errors, []);
    console.log('UI adicional OK: registro, filtros, compras/entradas, refresh, CRUD evento/localidad, archivo y gestion movil.');
  } catch (error) {await shot('extended-failure'); throw error;}
  finally {await browser.close();}
})().catch(error => {console.error(error); process.exitCode = 1;});
