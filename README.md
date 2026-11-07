# BiblioDist — Sistema de Biblioteca Distribuído

Trabalho de **Computação Distribuída** — Arthur Naoto Miura (RA 2311600029), FEMA.

Aplicação distribuída no domínio de gerenciamento de biblioteca:
**Django (HTTP) + gRPC (RPC) + RabbitMQ (mensageria/MOM)**, orquestrada com Docker.

## Estrutura

```
bibliodist/
├── api-web/        # Django — interface do bibliotecário e orquestrador HTTP
├── proto/          # contrato gRPC compartilhado
├── grpc-service/   # servidor gRPC (BibliotecaService, porta 50051)
├── worker/         # consumidor RabbitMQ (notificações assíncronas)
├── relatorio/      # relatório acadêmico (Markdown + PDF + screenshots)
├── docker-compose.yml
└── INSTRUCOES.txt
```

## Como rodar (recomendado — Docker)

> Pré-requisitos: Docker e Docker Compose instalados.

```bash
docker compose up --build
```

Na primeira execução, popule os dados de exemplo:

```bash
docker compose exec web python manage.py seed
```

| Serviço | Endereço |
|---------|----------|
| Aplicação web (Django) | http://localhost:8000 |
| Django Admin | http://localhost:8000/admin |
| RabbitMQ Management | http://localhost:15672 (guest/guest) |

Para parar tudo:

```bash
docker compose down
```

## Telas disponíveis

| URL | Descrição |
|-----|-----------|
| `/` | Página inicial com atalhos |
| `/livros/` | Listagem com busca por título e badge de disponibilidade |
| `/livros/novo/` | Cadastrar livro |
| `/livros/<pk>/editar/` | Editar livro |
| `/livros/<pk>/excluir/` | Excluir livro |
| `/autores/` | Listagem de autores |
| `/autores/novo/` | Cadastrar autor |
| `/categorias/` | Listagem de categorias |
| `/categorias/nova/` | Cadastrar categoria |
| `/leitores/` | Listagem de leitores |
| `/leitores/novo/` | Cadastrar leitor |
| `/emprestimos/` | Listagem com filtro por status (ativo/devolvido/atrasado) |
| `/emprestimos/novo/` | Registrar empréstimo (valida disponibilidade via gRPC) |
| `/emprestimos/<pk>/devolver/` | Registrar devolução |
| `/prisma/` | Revisão sistemática PRISMA 2020 sobre os TCCs do Acervo Digital da FEMA |
| `/prisma/exportar.csv` | Exporta incluídos e excluídos (com etapa e motivo) da revisão atual |
| `/admin/` | Django Admin (todos os modelos) |

## Revisão PRISMA (Acervo Digital FEMA)

Integração do projeto [prisma-scraper](https://github.com/R2nin/prisma-scraper) ao BiblioDist,
usando como base de dados o **Acervo Digital da Biblioteca da FEMA**
(<https://cepein.fema.edu.br/aplicacoes/extra-fema/consulta-acervo-biblioteca>).

**Coleta.** A página do acervo é um app Angular. Inspecionando a aba *Network* do navegador,
descobrimos a API REST pública que ela consome, então o Django consulta essa API direto, sem Selenium:

| Endpoint | Uso |
|---|---|
| `GET cepeinb.fema.edu.br/extra-fema/consulta-acervo/buscar-lista-filtrada` | busca paginada (`page`, `size`, `tipo`, `curso`, `palavrasChave`, `titulo`, `autor`) |
| `GET .../buscar-lista-cursos` e `.../buscar-lista-tipo` | opções dos filtros |
| `GET cepeinb.fema.edu.br/download-extra-fema/download/14/{uuid_arquivo}` | PDF do trabalho |

A API busca **um termo por vez**, ignora acentos e maiúsculas e **não pesquisa no resumo**.
Por isso o BiblioDist:

1. **Identificação:** faz uma consulta por termo positivo da expressão e remove os duplicados pelo `id`.
   No *modo amplo*, baixa o acervo inteiro do curso (o BCC tem cerca de 600 TCCs) para também achar termos que só aparecem no resumo.
2. **Triagem:** avalia localmente a expressão booleana (`AND`/`OR`/`NOT`, parênteses, `"frases"`, `prefixo*`)
   sobre título, palavras-chave e resumo, e aplica o filtro de período.
3. **Elegibilidade:** exige texto completo em PDF e, se marcado, resumo cadastrado.
4. **Inclusão:** lista final, fluxograma PRISMA, gráficos por ano e por palavra-chave, e exportação em CSV.

As respostas ficam 1 h em cache para não sobrecarregar o servidor da instituição.
Código em `api-web/biblioteca/prisma/` (`acervo_fema.py`, `consulta.py`, `pipeline.py`) e testes em
`api-web/biblioteca/tests.py` (`python manage.py test biblioteca`, sem acesso à internet).

## Como rodar manualmente (sem Docker)

> Útil para desenvolvimento isolado de cada serviço.

**Terminal 1 — Django:**
```bash
cd api-web
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed
python manage.py runserver
```

**Terminal 2 — servidor gRPC:**
```bash
cd grpc-service
pip install -r requirements.txt
python server.py
```

**Terminal 3 — worker RabbitMQ:**
```bash
cd worker
pip install -r requirements.txt
python worker.py
```

> Sem `DATABASE_URL` definida, o projeto usa **SQLite local** automaticamente.
> O gRPC e o worker possuem **fallback**: se offline, o Django cria empréstimos e
> notificações diretamente, sem interromper o fluxo.

### Variáveis de ambiente (opcional)

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `DATABASE_URL` | SQLite local | URL de conexão Postgres |
| `RABBITMQ_URL` | `amqp://guest:guest@localhost:5672/` | Broker RabbitMQ |
| `GRPC_HOST` | `localhost` | Host do servidor gRPC |
| `SECRET_KEY` | valor fixo de dev | Chave secreta Django |
| `DEBUG` | `True` | Modo debug |

### Comando seed

```bash
python manage.py seed            # adiciona dados sem apagar os existentes
python manage.py seed --limpar   # limpa tudo e repopula do zero
```

Cria: 6 autores, 6 categorias, 7 livros e 5 leitores de exemplo.

## Arquitetura

```
Navegador
    │ HTTP
    ▼
 api-web (Django :8000)
    │ gRPC           │ AMQP (publish)
    ▼                ▼
grpc-service    RabbitMQ (:5672)
  (:50051)           │ AMQP (consume)
                     ▼
                  worker
                (Notificacao)
```

- **Django** recebe as requisições HTTP e coordena as operações.
- **gRPC** (`VerificarDisponibilidade` + `RegistrarEmprestimo`) separa a lógica de empréstimo em um serviço independente com contrato `.proto`.
- **RabbitMQ + worker** processam notificações de forma assíncrona e desacoplada.

## Roadmap

- [x] **Fase 0** — Setup e esqueleto Django
- [x] **Fase 1** — Domínio: models, admin, CRUD completo, empréstimos
- [x] **Fase 2** — gRPC (RPC) — `BibliotecaService` com fallback local
- [x] **Fase 3** — RabbitMQ + worker de notificações assíncronas
- [x] **Fase 4** — Docker Compose (6 serviços: db, rabbitmq, migrate, web, grpc, worker)
- [x] **Fase 5** — Relatório acadêmico completo com screenshots
