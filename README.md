# BiblioDist — Sistema de Biblioteca Distribuído

Trabalho de **Computação Distribuída** — Arthur Naoto Miura (RA 2311600029), FEMA.

Aplicação distribuída no domínio de gerenciamento de biblioteca. Caminho enxuto:
**Django (HTTP) + gRPC (RPC) + RabbitMQ (mensageria/MOM)**.

## Estrutura

```
bibliodist/
├── api-web/        # Django (interface do bibliotecário, orquestrador) — FASE 0/1
├── proto/          # contrato gRPC (FASE 2)
├── grpc-service/   # servidor gRPC (FASE 2)
└── worker/         # consumidor RabbitMQ (FASE 3)
```

## Telas disponíveis (Fase 1)

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
| `/emprestimos/novo/` | Registrar empréstimo (valida disponibilidade) |
| `/emprestimos/<pk>/devolver/` | Registrar devolução |
| `/admin/` | Django Admin (todos os modelos) |

## Como rodar localmente (Fase 1)

```bash
cd api-web
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # edite o .env se necessário
python manage.py migrate
python manage.py seed                # popula dados de exemplo
python manage.py createsuperuser     # cria usuário para o /admin
python manage.py runserver
```

Acesse `http://127.0.0.1:8000`.

> Sem `DATABASE_URL` preenchido, o projeto usa **SQLite local** automaticamente — útil para
> desenvolver sem depender do Supabase. Ao preencher `DATABASE_URL` com a string do **pooler do
> Supabase (Session mode, porta 5432)**, ele passa a usar o Postgres.

### Comando seed

```bash
python manage.py seed            # adiciona dados sem apagar os existentes
python manage.py seed --limpar   # limpa tudo e repopula do zero
```

Cria: 6 autores, 6 categorias, 7 livros e 5 leitores de exemplo.

## Deploy no Railway (resumo)

1. Suba este repositório no GitHub.
2. No Railway, crie um serviço a partir do repo com **Root Directory = `api-web`**.
3. Defina as variáveis: `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS` (domínio Railway),
   `CSRF_TRUSTED_ORIGINS` (`https://<seu-domínio>`), `DATABASE_URL` (pooler do Supabase, 5432).
4. O `Procfile` já roda `migrate` no release e sobe o `gunicorn`.

## Roadmap

- [x] **Fase 0** — Setup e esqueleto Django
- [x] **Fase 1** — Domínio: models, admin, CRUD completo, empréstimos
- [ ] **Fase 2** — gRPC (RPC)
- [ ] **Fase 3** — RabbitMQ + worker
- [ ] **Fase 4** — docker-compose + documentação
- [ ] **Fase 5** — deploy distribuído
