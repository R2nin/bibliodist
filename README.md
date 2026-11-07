# BiblioDist — Sistema de Biblioteca Distribuído

**Disciplina:** Sistemas Distribuídos  
**Professor:** Almir Camolesi (camolesi@fema.edu.br)  
**Aluno:** Arthur Naoto Miura — RA 2311600029  
**Instituição:** FEMA — Fundação Educacional do Município de Assis

---

## Aderência aos Requisitos do Trabalho

> *"Desenvolver uma aplicação que use pelo menos 3 dos conceitos abaixo"*

O BiblioDist implementa **6 dos conceitos** solicitados:

| # | Conceito | Como está implementado |
|---|---|---|
| ✅ | **Docker** | 6 containers orquestrados com Docker Compose: `db`, `rabbitmq`, `migrate`, `web`, `grpc`, `worker` |
| ✅ | **Webservice (REST)** | Django expõe interface HTTP/REST; módulo PRISMA consome a API REST pública do Acervo Digital da FEMA (`cepeinb.fema.edu.br`) |
| ✅ | **SOA — Arquitetura Orientada a Serviços** | Três serviços independentes com contratos bem definidos: HTTP (Django), RPC (gRPC/Protocol Buffers) e mensageria (RabbitMQ/AMQP) |
| ✅ | **Microserviços** | `api-web`, `grpc-service` e `worker` são processos independentes, cada um com seu próprio Dockerfile e responsabilidade única |
| ✅ | **Conceitos de DevOps** | Repositório GitHub público, pipeline de deploy via Coolify (pull → build → run automático), variáveis de ambiente, health checks |
| ✅ | **Conceitos de Computação em Nuvem** | Deploy em servidor do professor via Coolify (`computacao.fema.edu.br`), isolamento por containers, infraestrutura como código (`docker-compose.coolify.yml`) |

---

## O que o sistema faz

Sistema web de gerenciamento de biblioteca com **acervo real de 12.044 livros** importados do Portal de Transparência da FEMA, integrando três paradigmas de comunicação distribuída:

```
Navegador
    │ HTTP
    ▼
 api-web (Django :8000)
    │ gRPC (RPC)         │ AMQP (mensageria)
    ▼                    ▼
grpc-service        RabbitMQ (:5672)
  (:50051)               │
                         ▼
                      worker
```

- **Django (HTTP)** — interface web completa: CRUD de livros, autores, leitores, empréstimos
- **gRPC** — serviço interno com contrato `.proto` para verificar disponibilidade e registrar empréstimos
- **RabbitMQ + Worker** — notificações assíncronas desacopladas
- **PRISMA** — revisão sistemática de TCCs consumindo a API REST do Acervo Digital da FEMA

---

## Como executar

> Pré-requisitos: Docker Desktop instalado e rodando.

```bash
git clone https://github.com/R2nin/bibliodist.git
cd bibliodist
docker compose up --build
```

Aguarde até aparecer `Worker conectado. Aguardando mensagens na fila 'notificacoes'`.

**Importar o acervo (12.044 livros):**
```bash
docker compose exec web python manage.py importar_acervo <arquivo.json>
```

| Serviço | URL | Credenciais |
|---|---|---|
| Aplicação web | http://localhost:8000 | — |
| Django Admin | http://localhost:8000/admin | admin / admin123 |
| Revisão PRISMA | http://localhost:8000/prisma/ | — |
| RabbitMQ UI | http://localhost:15672 | guest / guest |

---

## Estrutura do repositório

```
bibliodist/
├── api-web/                    # Django — interface HTTP e orquestrador
│   └── biblioteca/
│       └── prisma/             # módulo de Revisão Sistemática PRISMA 2020
├── proto/                      # contrato gRPC compartilhado (biblioteca.proto)
├── grpc-service/               # servidor gRPC (BibliotecaService, porta 50051)
├── worker/                     # consumidor RabbitMQ (notificações assíncronas)
├── relatorio/                  # relatório acadêmico (Markdown + PDF)
├── docker-compose.yml          # orquestração local
├── docker-compose.coolify.yml  # orquestração para deploy em produção
└── INSTRUCOES.txt
```

---

## Funcionalidades

| URL | Descrição |
|---|---|
| `/` | Home com estatísticas do acervo em tempo real |
| `/livros/` | 12.044 livros do acervo FEMA — busca, ordenação, paginação |
| `/autores/` | Cadastro de autores |
| `/categorias/` | Cadastro de categorias |
| `/leitores/` | Cadastro de leitores |
| `/emprestimos/` | Empréstimos com detecção automática de atraso |
| `/emprestimos/novo/` | Registrar empréstimo (valida via gRPC) |
| `/prisma/` | Revisão sistemática PRISMA 2020 sobre os TCCs do Acervo Digital |
| `/prisma/exportar.csv` | Exportar resultados da revisão em CSV |
| `/admin/` | Django Admin |

---

## Revisão PRISMA (Acervo Digital FEMA)

Integração com a API REST pública do Acervo Digital da Biblioteca da FEMA:

**Protocolo PRISMA 2020:**
1. **Identificação** — consulta paginada à API, uma busca por termo positivo
2. **Triagem** — avalia a expressão booleana (AND/OR/NOT, parênteses, frases, prefixo*) localmente
3. **Elegibilidade** — filtra por PDF disponível e/ou resumo cadastrado
4. **Inclusão** — lista final com fluxograma, gráficos e exportação CSV

**Filtros disponíveis:** expressão booleana, curso (todos os 14 cursos da FEMA), período, orientador, modo amplo (busca também no resumo).

---

## Fases de desenvolvimento

- [x] **Fase 0** — Setup Django, configuração por env vars
- [x] **Fase 1** — Domínio: models, admin, CRUD, empréstimos
- [x] **Fase 2** — Serviço gRPC (`BibliotecaService`) com fallback local
- [x] **Fase 3** — Mensageria RabbitMQ + worker de notificações
- [x] **Fase 4** — Orquestração Docker Compose (6 serviços)
- [x] **Fase 5** — Relatório acadêmico
- [x] **Fase 6** — Importação do acervo real (12.044 livros / 36.452 exemplares) + identidade visual FEMA
- [x] **Fase 7** — Revisão Sistemática PRISMA 2020 integrada ao Acervo Digital da FEMA
- [x] **Deploy** — Servidor do professor via Coolify (`computacao.fema.edu.br`)
