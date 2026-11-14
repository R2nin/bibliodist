// Gera os prints do "Guia rápido do administrador" (manual do Prof. Douglas).
// Pré-requisito: docker compose up (app em http://localhost:8000, admin/admin123).
// Uso: node screenshot_manual.mjs
import puppeteer from 'puppeteer';
import { mkdirSync } from 'fs';

const BASE = 'http://localhost:8000';
const OUT = './screenshots/manual';
mkdirSync(OUT, { recursive: true });

const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] });
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 800, deviceScaleFactor: 1 });

const shot = async (nome, opts = {}) => {
  await new Promise(r => setTimeout(r, 400));
  await page.screenshot({ path: `${OUT}/${nome}.png`, ...opts });
  console.log('OK ', nome);
};
const ir = (url) => page.goto(BASE + url, { waitUntil: 'networkidle2' });

// 1. Login
await ir('/login/');
await page.click('input[name=username]');
await page.type('input[name=username]', 'admin');
await page.type('input[name=password]', 'admin123');
await shot('01_login');
await Promise.all([page.click('button[type=submit]'), page.waitForNavigation({ waitUntil: 'networkidle2' })]);

// 2. Painel inicial
await shot('02_inicio');

// 3. Acervo + busca
await ir('/livros/');
await shot('03_livros');
await ir('/livros/?q=' + encodeURIComponent('sistemas operacionais'));
await shot('04_livros_busca');

// 4. Detalhe do livro (primeiro resultado da busca)
const href = await page.$eval('tbody a[href*="/livros/"]', a => a.getAttribute('href'));
await ir(href);
await shot('05_livro_detalhe');

// 5. Cadastro de livro com busca por ISBN
await ir('/livros/novo/');
await shot('06_livro_novo');

// 6. Leitores
await ir('/leitores/');
await shot('07_leitores');

// 7. Novo empréstimo (preenchido) e lista após registrar
await ir('/emprestimos/novo/');
const livroVal = await page.$eval('select[name=livro]', s =>
  [...s.options].find(o => /SISTEMAS OPERACIONAIS/i.test(o.textContent))?.value || s.options[1].value);
await page.select('select[name=livro]', livroVal);
const leitorVal = await page.$eval('select[name=leitor]', s => s.options[1].value);
await page.select('select[name=leitor]', leitorVal);
await page.$eval('input[name=data_prevista]', el => { el.value = '2026-11-28'; });
await shot('08_emprestimo_novo');
// (o menu também tem um <form> de logout; clicar no botão pelo texto)
const [btn] = await page.$$('xpath/.//button[contains(., "Registrar Empréstimo")]');
await Promise.all([btn.click(), page.waitForNavigation({ waitUntil: 'networkidle2' })]);
await shot('09_emprestimos');

// 8. Devolução (tela de confirmação do empréstimo recém-criado)
const devolver = await page.$eval('a[href*="/devolver/"]', a => a.getAttribute('href'));
await ir(devolver);
await shot('10_devolucao');

// 9. Logs de operações
await ir('/logs/');
await shot('11_logs');

// 10. Usuários
await ir('/usuarios/');
await shot('12_usuarios');

// 11. Admin Django
await ir('/admin/');
await shot('13_admin');

await browser.close();
