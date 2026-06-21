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
| `/admin/` | Django Admin (todos os modelos) |

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
