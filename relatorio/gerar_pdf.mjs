import puppeteer from 'puppeteer';
import { marked } from 'marked';
import { readFileSync, existsSync } from 'fs';
import { resolve, extname } from 'path';

const md   = readFileSync('./relatorio.md', 'utf8');
const html = marked(md);

// Converte imagens locais para data URIs base64 (evita bloqueio de file:// no Puppeteer)
function imagemParaBase64(caminho) {
  const abs = resolve('./screenshots', caminho.replace(/^screenshots\//, ''));
  if (!existsSync(abs)) return caminho;
  const ext = extname(abs).slice(1).replace('jpg', 'jpeg');
  const dados = readFileSync(abs);
  return `data:image/${ext};base64,${dados.toString('base64')}`;
}

const htmlComImagens = html.replace(
  /src="screenshots\/([^"]+)"/g,
  (_, nome) => `src="${imagemParaBase64('screenshots/' + nome)}"`
);

const page_html = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  body {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
    line-height: 1.6;
    color: #222;
    max-width: 900px;
    margin: 0 auto;
    padding: 20px 40px;
  }
  h1 { font-size: 24px; color: #1a1a2e; border-bottom: 3px solid #e67e22; padding-bottom: 8px; }
  h2 { font-size: 18px; color: #16213e; border-bottom: 1px solid #ddd; padding-bottom: 4px; margin-top: 32px; }
  h3 { font-size: 15px; color: #333; margin-top: 20px; }
  code {
    background: #f4f4f4;
    border: 1px solid #ddd;
    border-radius: 3px;
    padding: 1px 5px;
    font-family: 'Consolas', monospace;
    font-size: 12px;
  }
  pre {
    background: #1e1e2e;
    color: #cdd6f4;
    border-radius: 6px;
    padding: 14px 18px;
    overflow-x: auto;
    font-size: 11.5px;
    line-height: 1.5;
  }
  pre code {
    background: none;
    border: none;
    padding: 0;
    color: inherit;
    font-size: inherit;
  }
  table {
    border-collapse: collapse;
    width: 100%;
    margin: 12px 0;
    font-size: 12px;
  }
  th {
    background: #16213e;
    color: white;
    padding: 8px 12px;
    text-align: left;
  }
  td {
    border: 1px solid #ddd;
    padding: 7px 12px;
  }
  tr:nth-child(even) td { background: #f9f9f9; }
  img {
    max-width: 100%;
    border: 1px solid #ddd;
    border-radius: 6px;
    margin: 12px 0;
    display: block;
  }
  blockquote {
    border-left: 4px solid #e67e22;
    margin: 12px 0;
    padding: 8px 16px;
    background: #fff8f0;
    color: #555;
  }
  hr { border: none; border-top: 1px solid #eee; margin: 24px 0; }
  a { color: #2980b9; }
</style>
</head>
<body>
${htmlComImagens}
</body>
</html>`;

const browser = await puppeteer.launch({
  headless: true,
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
});

const page = await browser.newPage();
await page.setContent(page_html, { waitUntil: 'networkidle0' });

await page.pdf({
  path: './relatorio.pdf',
  format: 'A4',
  margin: { top: '20mm', bottom: '20mm', left: '15mm', right: '15mm' },
  printBackground: true,
});

await browser.close();
console.log('PDF gerado: relatorio.pdf');
