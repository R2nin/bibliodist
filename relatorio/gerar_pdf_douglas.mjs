import puppeteer from 'puppeteer';
import { marked } from 'marked';
import { readFileSync } from 'fs';

const md   = readFileSync('./manual_coolify.md', 'utf8');
const html = marked(md);

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
  h1 {
    font-size: 22px;
    color: #004784;
    border-bottom: 3px solid #F58220;
    padding-bottom: 8px;
    margin-bottom: 4px;
  }
  h2 {
    font-size: 17px;
    color: #004784;
    border-bottom: 2px solid #F58220;
    padding-bottom: 4px;
    margin-top: 32px;
  }
  h3 {
    font-size: 14px;
    color: #004784;
    margin-top: 20px;
    border-left: 4px solid #F58220;
    padding-left: 8px;
  }
  code {
    background: #f4f4f4;
    border: 1px solid #ddd;
    border-radius: 3px;
    padding: 1px 5px;
    font-family: 'Consolas', 'Courier New', monospace;
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
    border-left: 4px solid #F58220;
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
    background: #004784;
    color: white;
    padding: 8px 12px;
    text-align: left;
  }
  td {
    border: 1px solid #ddd;
    padding: 7px 12px;
  }
  tr:nth-child(even) td { background: #f0f5ff; }
  blockquote {
    border-left: 4px solid #F58220;
    margin: 12px 0;
    padding: 8px 16px;
    background: #fff8f0;
    color: #555;
    font-style: italic;
  }
  hr {
    border: none;
    border-top: 2px solid #F58220;
    margin: 28px 0;
    opacity: 0.4;
  }
  a { color: #004784; }
  p > strong { color: #004784; }
  /* Cabeçalho da capa */
  h1:first-of-type {
    font-size: 26px;
    text-align: center;
    margin-top: 20px;
  }
  /* Destaque de passos numerados */
  h3 {
    page-break-inside: avoid;
  }
</style>
</head>
<body>
${html}
</body>
</html>`;

const browser = await puppeteer.launch({
  headless: true,
  args: ['--no-sandbox', '--disable-setuid-sandbox'],
});

const page = await browser.newPage();
await page.setContent(page_html, { waitUntil: 'networkidle0' });

await page.pdf({
  path: './manual_douglas.pdf',
  format: 'A4',
  margin: { top: '20mm', bottom: '20mm', left: '15mm', right: '15mm' },
  printBackground: true,
});

await browser.close();
console.log('PDF gerado: manual_douglas.pdf');
