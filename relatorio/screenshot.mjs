import puppeteer from 'puppeteer';
import { writeFileSync } from 'fs';

const BASE = 'http://localhost:8000';
const OUT  = './screenshots';

const pages = [
  { name: '01_home',            url: '/livros/' },
  { name: '02_livros',          url: '/livros/' },
  { name: '03_livro_novo',      url: '/livros/novo/' },
  { name: '04_autores',         url: '/autores/' },
  { name: '05_categorias',      url: '/categorias/' },
  { name: '06_leitores',        url: '/leitores/' },
  { name: '07_emprestimos',     url: '/emprestimos/' },
  { name: '08_emprestimo_novo', url: '/emprestimos/novo/' },
  { name: '09_notificacoes',    url: '/notificacoes/' },
  { name: '10_admin',           url: '/admin/' },
];

const browser = await puppeteer.launch({
  headless: true,
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
});

for (const { name, url } of pages) {
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });
  try {
    await page.goto(BASE + url, { waitUntil: 'networkidle2', timeout: 10000 });
    await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });
    console.log(`OK  ${name}`);
  } catch (e) {
    console.log(`ERR ${name}: ${e.message}`);
  }
  await page.close();
}

await browser.close();
