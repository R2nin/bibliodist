import puppeteer from 'puppeteer';

const browser = await puppeteer.launch({
  headless: true,
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
});

// ── Admin Django (logado) ────────────────────────────────────
{
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  // login
  await page.goto('http://localhost:8000/admin/login/', { waitUntil: 'networkidle2' });
  await page.type('#id_username', 'admin');
  await page.type('#id_password', 'admin123');
  await Promise.all([
    page.click('input[type=submit]'),
    page.waitForNavigation({ waitUntil: 'networkidle2' }),
  ]);

  // vai para lista de notificações
  await page.goto('http://localhost:8000/admin/biblioteca/notificacao/', { waitUntil: 'networkidle2' });
  await page.screenshot({ path: './screenshots/10_admin_notificacoes.png', fullPage: false });
  console.log('OK  admin_notificacoes');
  await page.close();
}

// ── RabbitMQ (logado) ────────────────────────────────────────
{
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });

  await page.goto('http://localhost:15672/', { waitUntil: 'networkidle2', timeout: 15000 });
  await page.waitForSelector('input[name=username]', { timeout: 10000 });
  await page.type('input[name=username]', 'guest');
  await page.type('input[name=password]', 'guest');
  await Promise.all([
    page.click('input[type=submit]'),
    page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 10000 }),
  ]);
  // vai direto para a aba de filas
  await page.goto('http://localhost:15672/#/queues', { waitUntil: 'networkidle2' });
  await new Promise(r => setTimeout(r, 2000));
  await page.screenshot({ path: './screenshots/11_rabbitmq_queues.png', fullPage: false });
  console.log('OK  rabbitmq_queues');
  await page.close();
}

await browser.close();
