import puppeteer from 'puppeteer';
import { readFileSync } from 'fs';

function imgBase64(file) {
  const data = readFileSync(`./screenshots/${file}`);
  return `data:image/png;base64,${data.toString('base64')}`;
}

const imgs = {
  livros:       imgBase64('02_livros.png'),
  empNovo:      imgBase64('08_emprestimo_novo.png'),
  emprestimos:  imgBase64('07_emprestimos.png'),
  notificacoes: imgBase64('10_admin_notificacoes.png'),
  rabbitmq:     imgBase64('11_rabbitmq_queues.png'),
};

const html = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 12.5px;
    line-height: 1.65;
    color: #222;
    padding: 28px 44px;
  }

  /* Cabeçalho */
  .header {
    border-bottom: 3px solid #e67e22;
    padding-bottom: 10px;
    margin-bottom: 20px;
  }
  .header h1 { font-size: 20px; color: #1a1a2e; }
  .header .meta { font-size: 11px; color: #555; margin-top: 4px; }

  /* Seções */
  h2 {
    font-size: 13.5px;
    color: #fff;
    background: #1a1a2e;
    padding: 5px 10px;
    margin: 20px 0 10px;
    border-radius: 3px;
  }
  p { margin-bottom: 8px; }

  /* Diagrama */
  pre.diagrama {
    background: #f4f4f4;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 10px 14px;
    font-family: 'Consolas', monospace;
    font-size: 10.5px;
    line-height: 1.5;
    margin-bottom: 10px;
  }

  /* Passos */
  .passos { margin: 0 0 10px 0; padding: 0; }
  .passo {
    display: flex;
    gap: 10px;
    margin-bottom: 6px;
    align-items: flex-start;
  }
  .num {
    background: #e67e22;
    color: white;
    font-weight: bold;
    font-size: 11px;
    min-width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: 2px;
  }
  code {
    background: #1e1e2e;
    color: #cdd6f4;
    padding: 2px 7px;
    border-radius: 3px;
    font-family: 'Consolas', monospace;
    font-size: 11px;
  }
  .desc { color: #444; font-size: 11.5px; }

  /* Links */
  .link-box {
    background: #f0f7ff;
    border: 1px solid #b3d4f5;
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 11.5px;
    margin-bottom: 12px;
  }

  /* Screenshots */
  .screenshots {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-top: 10px;
  }
  .screenshot-item { }
  .screenshot-item p {
    font-size: 10px;
    color: #555;
    text-align: center;
    margin-top: 4px;
    margin-bottom: 0;
  }
  .screenshot-item img {
    width: 100%;
    border: 1px solid #ddd;
    border-radius: 4px;
  }
  .screenshot-full img {
    width: 100%;
    border: 1px solid #ddd;
    border-radius: 4px;
    margin-top: 10px;
  }
  .screenshot-full p {
    font-size: 10px;
    color: #555;
    text-align: center;
    margin-top: 4px;
  }
</style>
</head>
<body>

<div class="header">
  <h1>BiblioDist — Sistema de Gerenciamento de Biblioteca Distribuída</h1>
  <div class="meta">
    Disciplina: Sistemas Distribuídos &nbsp;|&nbsp; Professor: Almir &nbsp;|&nbsp; FEMA &nbsp;|&nbsp;
    Aluno: Arthur Naoto Miura &nbsp;|&nbsp; RA: 2311600029 &nbsp;|&nbsp; Junho/2026
  </div>
</div>

<!-- OBJETIVO -->
<h2>1. Objetivo do Trabalho</h2>
<p>
  O BiblioDist é um sistema web de gerenciamento de biblioteca que desenvolvi para demonstrar
  na prática os três principais paradigmas de comunicação em sistemas distribuídos: comunicação
  HTTP com Django, chamada remota de procedimento via gRPC e mensageria assíncrona com RabbitMQ.
  O sistema permite cadastrar livros, autores, leitores e gerenciar empréstimos, integrando
  essas três tecnologias em um fluxo real de uso.
</p>

<!-- ARQUITETURA -->
<h2>2. Arquitetura Adotada</h2>
<p>
  O sistema é composto por três serviços independentes que se comunicam entre si, mais um banco
  de dados PostgreSQL e um broker de mensagens RabbitMQ — todos orquestrados via Docker Compose:
</p>

<pre class="diagrama">  Usuário (Browser)
       |
       | HTTP — porta 8000
       v
  [api-web] Django + Gunicorn          &lt;-- interface web, CRUD, regras de negócio
       |                    |
       | gRPC               | AMQP (fila)
       | porta 50051        | porta 5672
       v                    v
  [grpc-service]       [RabbitMQ]
  BibliotecaService         |
  VerificarDisp.            | consome
  RegistrarEmprestimo       v
       |               [worker]  &lt;-- persiste Notificacao no banco
       |                    |
       +--------------------+
                |
                v
          [PostgreSQL]  &lt;-- banco compartilhado entre todos os serviços</pre>

<p>
  Quando o usuário cria um empréstimo, o Django chama o gRPC para verificar disponibilidade e
  registrar. O servidor gRPC então publica uma mensagem na fila do RabbitMQ, e o worker consome
  essa mensagem e persiste a notificação no banco. Se qualquer componente estiver offline, o
  sistema possui fallback automático para continuar funcionando.
</p>

<!-- EXECUÇÃO -->
<h2>3. Guia de Execução</h2>

<div class="link-box">
  <strong>Repositório:</strong> https://github.com/R2nin/bibliodist &nbsp;&nbsp;
  <strong>Pré-requisito:</strong> Docker Desktop instalado e rodando
</div>

<div class="passos">
  <div class="passo">
    <div class="num">1</div>
    <div>
      <code>git clone https://github.com/R2nin/bibliodist.git &amp;&amp; cd bibliodist</code>
      <div class="desc">Clonar o repositório</div>
    </div>
  </div>
  <div class="passo">
    <div class="num">2</div>
    <div>
      <code>docker compose up --build</code>
      <div class="desc">Construir e subir todos os containers (db, rabbitmq, grpc, web, worker). Aguardar a mensagem <em>"Worker conectado. Aguardando mensagens"</em></div>
    </div>
  </div>
  <div class="passo">
    <div class="num">3</div>
    <div>
      <code>docker compose exec web python manage.py seed</code>
      <div class="desc">Popular o banco com dados de teste (somente no primeiro uso)</div>
    </div>
  </div>
  <div class="passo">
    <div class="num">4</div>
    <div>
      <code>http://localhost:8000</code>
      <div class="desc">Acessar a aplicação no browser &nbsp;|&nbsp; RabbitMQ UI: <code>http://localhost:15672</code> (guest/guest)</div>
    </div>
  </div>
  <div class="passo">
    <div class="num">5</div>
    <div>
      <code>docker compose down</code>
      <div class="desc">Encerrar todos os serviços</div>
    </div>
  </div>
</div>

<!-- EVIDÊNCIAS -->
<h2>4. Evidências do Sistema em Funcionamento</h2>

<div class="screenshots">
  <div class="screenshot-item">
    <img src="${imgs.livros}">
    <p>Lista de livros com disponibilidade em tempo real</p>
  </div>
  <div class="screenshot-item">
    <img src="${imgs.empNovo}">
    <p>Formulário de empréstimo — chama gRPC ao submeter</p>
  </div>
  <div class="screenshot-item">
    <img src="${imgs.emprestimos}">
    <p>Lista de empréstimos com status e devolução</p>
  </div>
  <div class="screenshot-item">
    <img src="${imgs.notificacoes}">
    <p>Admin Django — lista de notificações geradas pelos empréstimos/devoluções</p>
  </div>
</div>

<div class="screenshot-full">
  <img src="${imgs.rabbitmq}">
  <p>Painel RabbitMQ (http://localhost:15672) — fila "notificacoes" ativa com mensagens publicadas e consumidas</p>
</div>

</body>
</html>`;

const browser = await puppeteer.launch({
  headless: true,
  args: ['--no-sandbox', '--disable-setuid-sandbox', '--allow-file-access-from-files'],
});

const page = await browser.newPage();
await page.setContent(html, { waitUntil: 'networkidle0' });

await page.pdf({
  path: './relatorio_curto.pdf',
  format: 'A4',
  margin: { top: '15mm', bottom: '15mm', left: '12mm', right: '12mm' },
  printBackground: true,
});

await browser.close();
console.log('PDF gerado: relatorio_curto.pdf');
