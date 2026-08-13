# ERP Shopee

ERP para vendedor Shopee, reconstruído a partir da planilha `ERP - Ecommer.xlsx`.
Multi-loja (multi-tenant) com login. Replica fielmente as regras da planilha —
**FIFO por lote**, **kits (BOM)**, **taxas Shopee**, **precificação** e os relatórios
diários — validado por testes _golden_ contra os próprios números da planilha.

## Stack

- **Backend:** FastAPI + SQLAlchemy 2 (async) + PostgreSQL, JWT (Argon2), Alembic.
- **Frontend:** React 18 + Vite + TypeScript + React Query.
- **Infra:** Docker Compose (db + api + web/nginx).

## Funcionalidades (uma por aba da planilha)

| Página | O que faz |
|--------|-----------|
| Dashboard | KPIs: estoque, receita, taxas, CMV, lucro antes/depois de Ads |
| Produtos | Cadastro; estoque, valor e custo médio **calculados** |
| Entradas | Lotes de compra (FIFO), saldo por lote |
| Kits | Combinações vendáveis + composição (BOM); custo e estoque possível |
| Vendas | Pedido → taxas, **CMV via FIFO**, lucro e margem |
| Ads | Investimento em anúncios por data/campanha |
| Balanço Diário | DRE por dia: receita, taxas, CMV, Ads, lucro, margem, **ROAS** |
| Estoque Diário | Peças que saíram no dia (kits explodidos em componentes) |
| Precificação | Reversa (defino lucro → preço) e direta (preço → lucro) |
| Configurações | Taxas da loja + equipe (convidar membros) |

## Regras de negócio (núcleo em `backend/app/services/`)

- **FIFO por lote:** a venda de um produto consome o lote mais antigo; o CMV segue esse custo.
- **CMV de kit:** soma dos componentes ao custo médio atual × quantidade.
- **Taxas:** `receita − taxa_shopee% − taxa_fixa(por pedido) − afiliado% − outras`.
- Todo o cálculo é **puro e determinístico** (recomputado do zero), então nunca há _drift_.

## Rodar localmente (Docker)

```bash
docker compose up --build
# Front: http://localhost:8080   API: http://localhost:8010/docs
```

Registre sua loja em **Criar minha loja**. Para popular a partir de uma planilha
(no formato esperado — **não vem no repositório**, pois contém dados reais):

```bash
docker compose exec api python -m app.seed_xlsx \
  --xlsx /caminho/sua-planilha.xlsx --email voce@email.com --password suasenha
```

Para **levar dados existentes** de um ambiente para outro sem redigitar, use
`pg_dump`/`psql` (veja [deploy/README-oracle.md](deploy/README-oracle.md)).

## Desenvolvimento sem Docker

Backend:
```bash
cd backend
virtualenv .venv && .venv/bin/pip install -r requirements.txt
# suba um Postgres e ajuste DATABASE_URL (.env), então:
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8010
.venv/bin/pytest        # testes (golden + API)
```

Frontend:
```bash
cd frontend
npm install
npm run dev             # http://localhost:5173 (proxy /api -> :8010)
```

## Deploy

Guia da Oracle Cloud VM (HTTP via IP público): [deploy/README-oracle.md](deploy/README-oracle.md).

## Testes

`cd backend && pytest` roda:
- **motor de cálculo** (`tests/test_engine_golden.py`): FIFO, CMV de kit, taxas, dashboard, balanço e
  estoque — validados contra um **fixture sintético** (valores calculados à mão, sem dados reais);
- **precificação** (`tests/test_pricing.py`);
- **integração da API** (`tests/test_api_flow.py`): auth multi-tenant, CRUD, canais, cálculo e isolamento entre lojas.
