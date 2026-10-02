/* Navegador real contra scripts/ui_server.py y su base temporal, nunca produccion. */
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
const password = fs.readFileSync(path.join(root, '.local', 'ui_password'), 'utf8');
const output = path.join(root, '.local', 'screenshots');
fs.mkdirSync(output, {recursive: true});
const origin = `http://127.0.0.1:${process.env.QA_PORT || '8012'}`;

(async () => {
  const browser = await chromium.launch({headless: true, channel: process.env.PW_CHANNEL || (process.platform === 'win32' ? 'msedge' : undefined)});
  const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  async function screenshot(name) {await page.screenshot({path: path.join(output, name + '.png'), fullPage: true});}
  async function noOverflow() {
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false, 'Desbordamiento horizontal');
  }
  async function login(username) {
    await page.goto(origin + '/ingresar/');
    await page.locator('[name=username]').fill(username);
    await page.locator('[name=password]').fill(password);
    await page.locator('#auth-form [type=submit]').click();
    await page.waitForURL(url => !url.pathname.startsWith('/ingresar/'));
  }
  async function logout() {
    await page.locator('[data-logout]').click();
    await page.locator('body[data-authenticated="false"]').waitFor();
    await page.waitForURL(origin + '/');
  }
  try {
    await page.goto(origin);
    await page.locator('.event-card').first().waitFor();
    assert.equal(await page.locator('.event-card').count(), 6);
    await page.waitForFunction(() => [...document.querySelectorAll('.event-image')].every(image => image.complete && image.naturalWidth > 0));
    assert.equal(await page.locator('.event-image').evaluateAll(images => images.every(image => image.complete && image.naturalWidth > 0)), true);
    await noOverflow(); await screenshot('01-catalog-desktop');
    await page.locator('.event-title').first().click();
    await page.locator('[data-add-sector] button').first().click();
    await page.waitForURL('**/ingresar/?next=*');
    await page.locator('[name=username]').fill('QAViewer'); await page.locator('[name=password]').fill(password);
    await page.locator('#auth-form [type=submit]').click(); await page.waitForURL('**/eventos/*/');
    await screenshot('02-event-desktop');
    await page.locator('[data-add-sector] input').first().fill('2');
    await page.locator('[data-add-sector] button').first().click();
    await page.locator('#toast').waitFor({state: 'visible'});
    await page.goto(origin + '/carrito/');
    await page.locator('.cart-item').waitFor(); await screenshot('03-cart-desktop');
    await page.locator('#checkout').click(); await page.waitForURL('**/compras/*/');
    assert.equal(new URL(page.url()).pathname.startsWith('/api/'), false);
    await page.locator('[data-pay=declined]').click(); await page.locator('#page-error').waitFor({state: 'visible'});
    await page.locator('[data-pay=approved]').click(); await page.locator('.ticket-links a').first().waitFor();
    assert.equal(await page.locator('.ticket-links a').count(), 2);
    await screenshot('04-paid-order');
    const orderUrl = page.url();
    await page.locator('.ticket-links a').first().click(); await page.locator('.ticket-stub img').waitFor();
    const ticketId = await page.locator('.ticket-stub code').textContent();
    await page.waitForFunction(() => document.querySelector('.ticket-stub img').complete && document.querySelector('.ticket-stub img').naturalWidth > 0);
    assert.equal(await page.locator('.ticket-stub img').evaluate(image => image.complete && image.naturalWidth > 0), true);
    await screenshot('05-ticket');
    // Un cliente no puede abrir gestion ni Swagger por direcciones directas.
    assert.equal((await page.goto(origin + '/gestion/')).status(), 403);
    assert.equal((await page.goto(origin + '/api/docs/')).status(), 403);
    await page.goto(origin + '/');
    await logout();
    await login('QAManager'); await page.waitForURL('**/gestion/'); await screenshot('06-dashboard');
    await page.goto(origin + '/gestion/recintos/nuevo/');
    await page.locator('[name=name]').fill('Recinto QA'); await page.locator('[name=city]').fill('Temuco'); await page.locator('[name=address]').fill('Calle QA 12');
    await page.locator('#resource-form [type=submit]').click(); await page.waitForURL('**/gestion/recintos/');
    const row = page.locator('tr', {hasText: 'Recinto QA'});
    await row.locator('[title="Editar Recinto QA"]').click();
    await page.locator('[name=address]').fill('Calle QA 24'); await page.locator('#resource-form [type=submit]').click(); await page.waitForURL('**/gestion/recintos/');
    await page.locator('[title="Eliminar Recinto QA"]').click(); await page.locator('#confirm-dialog [value=confirm]').click();
    await page.locator('tr', {hasText: 'Recinto QA'}).waitFor({state: 'detached'});
    await page.goto(origin + '/gestion/eventos/'); await page.locator('tbody tr').first().waitFor(); await screenshot('07-events-management');
    await page.goto(origin + '/gestion/acceso/');
    const options = await page.locator('[name=event] option').allTextContents();
    const found = options.findIndex(name => name.includes('Cuerdas del puerto'));
    if (found > 0) await page.locator('[name=event]').selectOption({index: found});
    else throw new Error('Evento de prueba no encontrado');
    await page.locator('[name=ticket]').fill(ticketId); await page.locator('#admission-form button').click(); await page.locator('#admission-result').waitFor({state: 'visible'});
    await page.locator('[name=ticket]').fill(ticketId); await page.locator('#admission-form button').click(); await page.locator('#page-error').waitFor({state: 'visible'});
    await page.goto(orderUrl); await page.locator('[data-order-status=CANCELADO]').click();
    await page.locator('#confirm-reason').fill('Cancelacion de prueba UI'); await page.locator('#confirm-dialog [value=confirm]').click(); await page.waitForLoadState('networkidle');
    await page.locator('.badge.cancelado').waitFor();
    await page.goto(origin + '/api/docs/'); await page.locator('.swagger-ui .opblock').first().waitFor(); await screenshot('08-swagger-private');
    await logout();
    for (const width of [360, 768]) {
      await page.setViewportSize({width, height: 900}); await page.goto(origin); await page.locator('.event-card').first().waitFor();
      await noOverflow(); await screenshot('09-catalog-' + width);
      await page.locator('.event-title').first().click(); await noOverflow(); await screenshot('10-event-' + width);
      await page.goto(origin + '/registrarse/'); await noOverflow(); await screenshot('11-register-' + width);
    }
    assert.equal((await page.goto(origin + '/no-existe/')).status(), 404);
    await screenshot('12-friendly-404');
    assert.deepEqual(errors, []);
    console.log('UI OK: catalogo, acceso requerido, login, carrito, pago, entradas, permisos, CRUD de recinto, ingreso, cancelacion, Swagger y responsive.');
  } catch (error) {await screenshot('failure'); throw error;}
  finally {await browser.close();}
})().catch(error => {console.error(error); process.exitCode = 1;});
