# Backlog — ERP Shopee

Itens de melhoria e novas funcionalidades, priorizados. Prioridade: **P0** urgente,
**P1** alto valor, **P2** desejável, **P3** oportunista. Cada item traz critérios de aceite.

> Fonte da verdade deste backlog. Ao concluir um item, marque `[x]` e mova a nota relevante
> para o histórico de commits.

---

## 0. Correção / Confiabilidade

- [x] **ERP-001 · Estoque explicado (P1)** ✅ — a tela de Produtos mostra as colunas
  `Entradas − Vend. diretas − Em kits = Estoque` (backend expõe a decomposição em `product_states`).

- [x] **ERP-002 · Guardrail de estoque (P1)** ✅ — venda com `qty > disponível` (produto: estoque;
  kit: estoque possível) retorna 409; a UI confirma e reenvia com `permitir_sem_estoque`.

- [ ] **ERP-003 · Validar/consertar composição de kits (P2)** — a planilha tem inconsistências
  (ex.: "Kit Blusa Branca + Marrom" composto de polos). 
  **Aceite:** validação no cadastro de kit (componentes coerentes/ativos) + relatório que aponta
  kits com composição suspeita.

- [ ] **ERP-004 · Resposta degradada no PATCH de lote (P3)** — `update_lot` retorna nome do produto
  vazio e sem saldo (`app/api/stock_lots.py`). 
  **Aceite:** o PATCH recomputa e devolve a linha completa, como já é feito em vendas.

- [ ] **ERP-005 · Precisão monetária (P2)** — valores são `float` (para espelhar a planilha), o que
  pode gerar centavos "fantasma". 
  **Aceite:** armazenar em `Decimal`/centavos com arredondamento em pontos definidos; golden tests
  mantidos com tolerância. Decisão consciente x paridade da planilha documentada.

## 1. Segurança

- [ ] **ERP-010 · Papéis e permissões (P1)** — hoje `member` pode excluir produtos/kits/vendas;
  só Configurações e convites exigem `owner`. 
  **Aceite:** operações destrutivas exigem `owner`; papel "somente leitura" disponível; testes cobrindo.

- [ ] **ERP-011 · Rate-limit no login (P1)** — sem proteção a brute force. 
  **Aceite:** limite por IP+e-mail com bloqueio temporário; testado.

- [ ] **ERP-012 · Refresh token revogável + rotação (P1)** — "Sair" é só client-side; token roubado
  vale até expirar. 
  **Aceite:** `token_version`/jti por usuário; logout e troca de senha invalidam refresh tokens.

- [ ] **ERP-013 · Endurecer armazenamento de token (P2)** — token em `localStorage` (risco XSS). 
  **Aceite:** migrar para cookie `httpOnly`+`SameSite` (ou reduzir TTL do access e isolar).

- [ ] **ERP-014 · HTTPS (P2)** — deploy atual é HTTP por IP. 
  **Aceite:** Caddy/Let's Encrypt com domínio; redirect 80→443. (já esboçado em `deploy/README-oracle.md`)

## 2. Escala / Performance

- [ ] **ERP-020 · Paginação + filtros server-side (P1)** — nenhum endpoint pagina; Vendas/Balanço
  trazem tudo. 
  **Aceite:** paginação e filtros (período, SKU, item) em Vendas e Entradas; UI com paginador.

- [ ] **ERP-021 · Recalcular sob demanda é caro (P2)** — todo request recarrega o snapshot inteiro e
  recomputa o FIFO de tudo; `estoque-diario-range` é O(dias×produtos×vendas). 
  **Aceite:** cache do estado derivado por produto (ou materialização incremental) com invalidação em
  escrita; benchmark antes/depois.

## 3. Funcionalidades novas

- [x] **ERP-030 · Import de pedidos via CSV (P1)** ✅ — `POST /sales/import` com dry-run (preview:
  novos/duplicados/erros) e importação idempotente por (pedido+item); parser tolerante a cabeçalhos
  PT-BR/Shopee, `,`/`;` e vírgula decimal; UI com modal + "baixar modelo".

- [ ] **ERP-031 · Exportar relatórios (CSV/Excel) (P1)** — Balanço, Vendas e Estoque. 
  **Aceite:** botão "Exportar" gerando CSV/XLSX do relatório filtrado.

- [ ] **ERP-032 · Conciliação de repasse Shopee (P1)** — comparar o valor que a Shopee realmente
  pagou com o líquido calculado (foi exatamente a origem do override manual `N9` da planilha). 
  **Aceite:** por pedido/repasse, registrar valor recebido; diferença vira ajuste ("Outras Taxas")
  e um relatório de divergências.

- [ ] **ERP-033 · Devoluções / cancelamentos (P1)** — reverter estoque e ajustar lucro. 
  **Aceite:** lançar devolução vinculada à venda; estoque retorna; DRE e dashboard refletem.

- [ ] **ERP-034 · Ponto de reposição + sugestão de recompra (P2)** — alerta de estoque mínimo e
  sugestão baseada no giro (velocidade de venda × lead time). 
  **Aceite:** campo de estoque mínimo por produto; painel de "comprar agora".

- [ ] **ERP-035 · Custos fixos/operacionais rateados (P2)** — embalagem, frete pago pelo vendedor,
  impostos e custos mensais → lucro líquido "de verdade". 
  **Aceite:** cadastro de custos (por pedido/por mês); dashboard mostra lucro após custos operacionais.

- [ ] **ERP-036 · Dashboard com gráficos (P2)** — hoje só KPIs+tabelas. 
  **Aceite:** séries no tempo (receita/lucro/ROAS), top produtos e margem por produto.

- [ ] **ERP-037 · Fechamento mensal + comparativo (P2)** — DRE consolidado por mês e mês-a-mês. 
  **Aceite:** relatório mensal com variação vs. mês anterior; export.

- [ ] **ERP-038 · Fornecedores + ordens de compra (P2)** — vincular lote a fornecedor, prazo e status. 
  **Aceite:** cadastro de fornecedor; OC com itens; ao receber, gera entradas (lotes).

- [x] **ERP-039 · Multicanal / e-commerces (P1)** ✅ — modelo `channels` (nome + taxa %, taxa fixa,
  afiliado %, ativo), CRUD (tela **E-commerces**), venda com dropdown de canal aplicando as taxas certas
  (snapshot). Migração 0002 faz backfill de um canal "Shopee" e vincula as vendas existentes.
  **Depois:** relatórios por canal (ERP-061).

- [ ] **ERP-061 · Relatórios por canal (P2)** — comparar desempenho entre marketplaces. 
  **Aceite:** dashboard/balanço filtráveis por canal; comparativo (qual dá mais lucro/margem/ROAS).

- [x] **ERP-064 · Calculadora de ROAS + Ads/venda (P2)** ✅ — tela "Calculadora ROAS": mostra o
  **ROAS de equilíbrio** (= 1 ÷ margem) por produto/kit e avalia o ROAS do período (ads + faturamento
  → veredito bom/ruim + lucro após ads + custo de ads por venda). Balanço Diário ganhou coluna **Ads/venda**.

- [ ] **ERP-062 · Impostos (Simples Nacional) (P3)** — alíquota de imposto no cálculo do lucro. 
  **Aceite:** % de imposto por loja/canal aplicado no lucro líquido e na precificação.

- [ ] **ERP-040 · Curva ABC + estoque parado (P3)** — priorização e dead stock. 
  **Aceite:** relatório ABC por faturamento/lucro e lista de produtos sem giro há N dias.

- [ ] **ERP-041 · Precificação em lote + histórico de preços (P3)** — aplicar regra de margem a vários
  produtos e ver evolução. 
  **Aceite:** ação em massa na Precificação; histórico por produto.

- [ ] **ERP-042 · Metas e alertas (P3)** — meta de faturamento/margem; alerta de margem negativa/ROAS baixo. 
  **Aceite:** metas por período; notificações no painel.

- [ ] **ERP-043 · PWA / mobile (P3)** — lançar venda rápido pelo celular. 
  **Aceite:** app instalável, tela de venda otimizada para toque, funciona offline básico.

- [x] **ERP-044 · Gestão de usuários pelo admin (P2)** ✅ (parcial) — tela **Usuários**: owner lista
  contas, **troca a senha** de qualquer usuário (`PATCH /auth/users/{id}/password`) e **exclui contas**
  (`DELETE /auth/users/{id}`, com guarda contra excluir a si mesmo / o único dono).
  **Pendente (adiado a pedido):** recuperação de senha por e-mail.

## 4. IA / Assistente (LLM)

- [ ] **ERP-060 · Assistente de análise (LLM) (P2)** — camada de linguagem sobre os números que o
  `engine` já calcula. **Princípio:** o LLM NÃO faz conta — recebe um "briefing" pronto (KPIs, balanço
  recente, estoque baixo, margem por produto, parados) e só explica/recomenda em PT-BR.
  **Arquitetura (trocável por env):** `app/services/llm/` com `client.py` (impl OpenAI-compatível via
  httpx — atende **Ollama local** e **APIs hospedadas** com o mesmo protocolo), `briefing.py`
  (reusa o engine) e `assistant.py`; router `POST /assistant/insights` e `POST /assistant/chat` (SSE).
  Config: `LLM_PROVIDER=off|ollama|hosted`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`.
  **Guardrails:** escopo por `org_id`; fallback pros números se o LLM cair; streaming; rate-limit por
  loja; cache do insight diário; flag `off` esconde a tela.
  **Pré-requisito:** métricas de reposição (ERP-034) e margem por produto (parte do ERP-036).
  **Aceite (MVP):** botão "Analisar minha loja" → resumo em markdown a partir do briefing real.

- [ ] **ERP-063 · Alertas proativos (P3)** — notificar estoque baixo / margem negativa / ROAS ruim
  (painel e, depois, WhatsApp/e-mail). Casa com o Assistente (ERP-060) e as metas (ERP-042).

## 5. Qualidade / Operação

- [x] **ERP-050 · CI/CD (GitHub Actions) (P1)** ✅ — `.github/workflows/deploy.yml` roda `pytest` + build
  do front a cada push/PR e, na `main`, faz **deploy por SSH** na Oracle VM (`deploy/deploy.sh`). O deploy
  nunca reseta dados; restore é único e protegido (`deploy/restore-once.sh`). Secrets: `SSH_HOST/USER/KEY/PORT`.

- [ ] **ERP-051 · Ampliar testes (P2)** — auth negativo, permissões, CRUD de kits, endpoints de report;
  testes de frontend (Vitest/RTL). 
  **Aceite:** cobertura dos caminhos críticos; front com testes de fluxo.

- [ ] **ERP-052 · Observabilidade + healthchecks (P2)** — logs estruturados, captura de erros (Sentry),
  healthcheck dos containers `api`/`web` (hoje só `db`). 
  **Aceite:** logs JSON; erros capturados; compose com healthcheck/restart em todos os serviços.

- [ ] **ERP-053 · Auditoria / soft-delete (P2)** — log de quem criou/alterou/excluiu; exclusão hoje é
  destrutiva e sem histórico. 
  **Aceite:** trilha de auditoria por entidade; soft-delete onde fizer sentido.

- [ ] **ERP-054 · Contrato da API + limpeza (P3)** — muitos endpoints retornam `dict` (piora `/docs`);
  helper `_product_names` duplicado. 
  **Aceite:** `response_model` tipado nos endpoints; helpers consolidados.

- [ ] **ERP-055 · Backups automáticos (P2)** — hoje `pg_dump` é manual. 
  **Aceite:** rotina agendada de backup + restauração documentada e testada.

- [ ] **ERP-056 · Polimento de UX (P3)** — toasts no lugar de `alert()/confirm()`, skeletons,
  ordenação em todas as colunas, estados vazios com CTA. 
  **Aceite:** feedback consistente; sem `alert()` bloqueante.

- [x] **ERP-057 · Responsivo / mobile-first (P1)** ✅ — conteúdo usa a largura toda (sem cap que jogava
  tudo pra esquerda); menu vira drawer com hambúrguer no celular; grades de 2 colunas empilham; tabelas
  largas rolam dentro do card. **Regra do projeto:** manter tudo mobile-first daqui pra frente.
