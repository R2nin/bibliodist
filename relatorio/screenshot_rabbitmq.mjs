import puppeteer from 'puppeteer';

const browser = await puppeteer.launch({
  headless: true,
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
});

const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 900 });

// Acessa direto com autenticação Basic
await page.goto('http://guest:guest@localhost:15672/#/queues', { waitUntil: 'networkidle2', timeout: 15000 });
await new Promise(r => setTimeout(r, 3000));
await page.screenshot({ path: './screenshots/11_rabbitmq.png', fullPage: false });
console.log('OK  11_rabbitmq');

await browser.close();
