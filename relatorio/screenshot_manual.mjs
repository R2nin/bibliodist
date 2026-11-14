// Gera os prints do "Guia rápido do administrador" (manual do Prof. Douglas).
// Pré-requisito: docker compose up (app em http://localhost:8000, admin/admin123).
// Uso: node screenshot_manual.mjs
import puppeteer from 'puppeteer';
import { mkdirSync } from 'fs';
import { execSync } from 'child_process';

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

// 8b. Empréstimo em atraso: cria um com data prevista no passado,
// fotografa a lista filtrada, a renovação e a cobrança, e depois devolve.
await ir('/emprestimos/novo/');
await page.select('select[name=livro]', livroVal);
await page.select('select[name=leitor]', leitorVal);
await page.$eval('input[name=data_prevista]', el => { el.value = '2026-11-09'; });
const [btn2] = await page.$$('xpath/.//button[contains(., "Registrar Empréstimo")]');
await Promise.all([btn2.click(), page.waitForNavigation({ waitUntil: 'networkidle2' })]);
// o formulário grava a data de hoje como data do empréstimo; recua para 20/10
// para o exemplo ficar coerente (empréstimo antes da data prevista)
execSync(
  'docker compose exec -T web python manage.py shell -c "' +
  "from biblioteca.models import Emprestimo; import datetime; " +
  "e = Emprestimo.objects.filter(data_prevista=datetime.date(2026, 11, 9)).latest('pk'); " +
  "e.data_emprestimo = datetime.date(2026, 10, 20); e.save()" + '"',
  { cwd: '..', stdio: 'inherit', env: { ...process.env, MSYS_NO_PATHCONV: '1' } },
);
await ir('/emprestimos/?status=atrasado');
await shot('14_emprestimo_atrasado');
const renovar = await page.$eval('a[href*="/renovar/"]', a => a.getAttribute('href'));
await ir(renovar);
await shot('15_renovar');
await ir(renovar.replace('/renovar/', '/cobrar/'));
// em produção o SMTP está configurado; o aviso "SMTP não configurado" é só do ambiente local
await page.$$eval('.alert-warning', els => els.forEach(e => e.remove()));
await shot('16_cobrar', { fullPage: true });
// limpa: devolve o empréstimo atrasado de exemplo
await ir(renovar.replace('/renovar/', '/devolver/'));
await Promise.all([
  page.click('main form button[type=submit], .card form button[type=submit]'),
  page.waitForNavigation({ waitUntil: 'networkidle2' }),
]);

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
