"""Testes dos importadores Shopee com fixtures SINTÉTICOS (nenhum dado real).

Cobrem: parser de pedidos (agregação por pedido, taxas repetidas por linha, PII ignorada),
parser de ads (preâmbulo/período/tipos), resolução de SKU (auto vs pendente),
idempotência do upsert e consumo de estoque via pedidos importados.
"""
import io

import openpyxl
import pytest

from app.services.shopee_import import normalize_status, parse_ads_csv, parse_orders_xlsx

# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------
ORDER_HEADERS = [
    "ID do pedido", "Status do pedido", "Data de criação do pedido",
    "Hora do pagamento do pedido", "Nº de referência do SKU principal",
    "Nome do Produto", "Número de referência SKU", "Nome da variação",
    "Preço acordado", "Quantidade", "Subtotal do produto", "Desconto do vendedor",
    "Valor Total", "Taxa de transação", "Taxa de comissão líquida",
    "Taxa de serviço líquida", "Total global",
    # PII que deve ser ignorada
    "Nome do destinatário", "CPF do Comprador", "Endereço de entrega",
]


def build_orders_xlsx(rows: list[dict]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "orders"
    ws.append(ORDER_HEADERS)
    for r in rows:
        ws.append([r.get(h, "") for h in ORDER_HEADERS])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def order_row(sn, status, sku_var, qty=1, price=20.0, name="Produto X", var="Cor A", **over):
    sub = round(price * qty, 2)
    base = {
        "ID do pedido": sn,
        "Status do pedido": status,
        "Data de criação do pedido": "2026-08-05 10:00",
        "Hora do pagamento do pedido": "2026-08-05 10:05",
        "Nome do Produto": name,
        "Número de referência SKU": sku_var,
        "Nome da variação": var,
        "Preço acordado": str(price),
        "Quantidade": str(qty),
        "Subtotal do produto": str(sub),
        "Desconto do vendedor": "0.00",
        "Valor Total": str(sub),
        "Taxa de transação": "1.00",
        "Taxa de comissão líquida": "4.00",
        "Taxa de serviço líquida": "2.00",
        "Total global": str(round(sub - 7.0, 2)),
        "Nome do destinatário": "FULANO SIGILOSO",
        "CPF do Comprador": "123.456.789-00",
        "Endereço de entrega": "Rua Secreta, 42",
    }
    base.update(over)
    return base


ADS_CSV = """﻿Relatório de Todos os Anúncios CPC - Shopee Brasil\r
Nome de Usuário,loja_teste\r
Nome da loja,Loja Teste\r
ID da Loja,999\r
Data de Criação do Relatório,13/08/2026 23:22\r
Período,01/08/2026 - 13/08/2026\r
\r
#,Nome do Anúncio,Status,Tipos de Anúncios,ID do produto,Criativo,Método de Lance,Posicionamento,Data de Início,Data de Encerramento,Impressões,Cliques,CTR,Adicionar ao carrinho,Taxa de adição ao carrinho,Conversões,Conversões Diretas,Taxa de Conversão,Taxa de Conversão Direta,Custo por Conversão,Custo por Conversão Direta,Itens Vendidos,Itens Vendidos Diretos,GMV,Receita direta,Despesas,ROAS,ROAS Direto,ACOS,ACOS Direto,Impressões do Produto,Cliques de Produtos,CTR do Produto,Voucher Amount,Vouchered Sales\r
1,Anúncio Alpha,Em Andamento,Auto,111,-,GMV Max,Todos,02/08/2026 00:00:00,Ilimitado,1000,50,5.00%,10,20.0%,5,5,10.0%,10.0%,2.00,2.00,6,6,300.00,300.00,60.00,5.00,5.00,20.00%,20.00%,-,-,-,0.00,0.00\r
2,Anúncio Beta,Encerrado,Auto,222,-,GMV Max,Todos,02/08/2026 00:00:00,Ilimitado,500,10,2.00%,2,20.0%,1,1,10.0%,10.0%,15.00,15.00,1,1,50.00,50.00,15.00,3.33,3.33,30.00%,30.00%,-,-,-,0.00,0.00\r
"""


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------
def test_parse_orders_aggregates_and_ignores_pii():
    content = build_orders_xlsx(
        [
            # pedido multi-item: valores do pedido repetem nas 2 linhas
            order_row("PED1", "Enviado", "sku-a", qty=1, price=20.0,
                      **{"Valor Total": "50.00", "Total global": "43.00"}),
            order_row("PED1", "Enviado", "sku-b", qty=2, price=15.0,
                      **{"Valor Total": "50.00", "Total global": "43.00"}),
            order_row("PED2", "Cancelado", "sku-a", qty=1, price=20.0,
                      **{"Valor Total": "0.00", "Total global": "0.00",
                         "Taxa de comissão líquida": "0.00", "Taxa de serviço líquida": "0.00",
                         "Taxa de transação": "0.00"}),
        ]
    )
    res = parse_orders_xlsx(content, "t.xlsx")
    assert not res["errors"]
    assert len(res["orders"]) == 2
    p1 = next(o for o in res["orders"] if o["order_sn"] == "PED1")
    assert len(p1["items"]) == 2
    # valores do pedido pegos UMA vez (não somados por linha)
    assert p1["valor_bruto"] == pytest.approx(50.0)
    assert p1["taxa_comissao"] == pytest.approx(4.0)
    assert p1["valor_liquido"] == pytest.approx(43.0)
    # nenhuma PII em lugar nenhum
    import json
    dump = json.dumps(res, default=str)
    assert "FULANO" not in dump and "123.456" not in dump and "Rua Secreta" not in dump


def test_normalize_status():
    assert normalize_status("Não pago") == "nao_pago"
    assert normalize_status("A Enviar") == "a_enviar"
    assert normalize_status("Concluído") == "concluido"
    assert normalize_status("O comprador pode pedir uma devolução até 2026-08-17") == "entregue"


def test_parse_ads_csv():
    res = parse_ads_csv(ADS_CSV.encode("utf-8"), "ads.csv")
    assert not res["errors"]
    assert res["report_type"] == "geral"
    assert str(res["period_start"]) == "2026-08-01" and str(res["period_end"]) == "2026-08-13"
    assert len(res["rows"]) == 2
    a = res["rows"][0]
    assert a["listing_ref"] == "111"
    assert a["impressions"] == 1000 and a["clicks"] == 50
    assert a["gmv"] == pytest.approx(300.0) and a["spend"] == pytest.approx(60.0)
    assert a["roas"] == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# API: import + resolução + idempotência + estoque
# ---------------------------------------------------------------------------
async def _register(client, email):
    r = await client.post(
        "/api/auth/register",
        json={"name": "T", "email": email, "password": "secret1"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_import_orders_end_to_end(client):
    h = await _register(client, "imp@loja.com")
    # produto cujo SKU casa com o sku_var do export -> resolução automática
    pid = (await client.post("/api/products", json={"sku": "sku-a", "nome": "Produto A"}, headers=h)).json()["id"]
    await client.post(
        "/api/stock-lots",
        json={"product_id": pid, "data_entrada": "2026-08-01", "qty_in": 10, "unit_cost": 5},
        headers=h,
    )

    content = build_orders_xlsx(
        [
            order_row("PEDA", "Enviado", "sku-a", qty=2, price=20.0),
            order_row("PEDB", "Enviado", "sku-misterio", qty=1, price=30.0,
                      name="Produto Desconhecido", var="Cor Z"),
            order_row("PEDC", "Cancelado", "sku-a", qty=5, price=20.0,
                      **{"Valor Total": "0.00", "Total global": "0.00"}),
        ]
    )

    # dry-run não grava
    r = await client.post(
        "/api/imports/orders",
        files={"file": ("Order.all.test.xlsx", content, "application/vnd.ms-excel")},
        params={"dry_run": "true"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    s = r.json()["summary"]
    assert s["pedidos"] == 3 and s["novos"] == 3 and s["itens_pendentes_vinculo"] == 1
    assert (await client.get("/api/imports", headers=h)).json()["pedidos_importados"] == 0

    # import real
    r = await client.post(
        "/api/imports/orders",
        files={"file": ("Order.all.test.xlsx", content, "application/vnd.ms-excel")},
        headers=h,
    )
    assert r.json()["summary"]["novos"] == 3
    st = (await client.get("/api/imports", headers=h)).json()
    assert st["pedidos_importados"] == 3
    assert st["itens_pendentes_vinculo"] == 1  # sku-misterio

    # estoque: consumiu 2 do PEDA (enviado); cancelado (PEDC) NÃO consome
    p = (await client.get("/api/products", headers=h)).json()[0]
    assert p["estoque_atual"] == 8

    # receita: só PEDA conta (PEDB pendente de vínculo, PEDC cancelado)
    d = (await client.get("/api/reports/dashboard", headers=h)).json()
    assert d["receita_bruta"] == pytest.approx(40.0)
    # taxas reais: comissão+serviço (6.00) + transação (1.00) do pedido
    assert d["taxas_totais"] == pytest.approx(7.0)

    # reimport = idempotente (atualiza, não duplica)
    r = await client.post(
        "/api/imports/orders",
        files={"file": ("Order.all.test.xlsx", content, "application/vnd.ms-excel")},
        headers=h,
    )
    assert r.json()["summary"]["novos"] == 0
    assert r.json()["summary"]["atualizados"] == 3
    assert (await client.get("/api/imports", headers=h)).json()["pedidos_importados"] == 3
    p = (await client.get("/api/products", headers=h)).json()[0]
    assert p["estoque_atual"] == 8  # não consumiu de novo


async def test_mapping_flow(client):
    h = await _register(client, "map@loja.com")
    pid = (await client.post("/api/products", json={"sku": "prod-real", "nome": "Produto Real"}, headers=h)).json()["id"]
    await client.post(
        "/api/stock-lots",
        json={"product_id": pid, "data_entrada": "2026-08-01", "qty_in": 10, "unit_cost": 5},
        headers=h,
    )
    content = build_orders_xlsx(
        [order_row("PEDM", "Enviado", "sku-shopee-x", qty=3, price=25.0,
                   name="Blusa Tal", var="Azul, M")]
    )
    await client.post(
        "/api/imports/orders",
        files={"file": ("o.xlsx", content, "application/vnd.ms-excel")},
        headers=h,
    )

    # pendência aparece agrupada com sugestões
    pend = (await client.get("/api/mappings/pendentes", headers=h)).json()
    assert len(pend) == 1
    g = pend[0]
    assert g["qtd_unidades"] == 3
    assert g["sugestoes"]  # fuzzy trouxe candidatos

    # vincula ao produto -> aplica retroativo
    r = await client.post(
        "/api/mappings",
        json={"match_key": g["match_key"], "product_id": pid},
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["itens_aplicados"] == 1

    # sem mais pendências; estoque consumiu 3; receita conta o pedido
    assert (await client.get("/api/mappings/pendentes", headers=h)).json() == []
    p = (await client.get("/api/products", headers=h)).json()[0]
    assert p["estoque_atual"] == 7
    d = (await client.get("/api/reports/dashboard", headers=h)).json()
    assert d["receita_bruta"] == pytest.approx(75.0)

    # desfazer o vínculo devolve a pendência e o estoque
    mid = (await client.get("/api/mappings", headers=h)).json()[0]["id"]
    assert (await client.delete(f"/api/mappings/{mid}", headers=h)).status_code == 204
    assert len((await client.get("/api/mappings/pendentes", headers=h)).json()) == 1
    p = (await client.get("/api/products", headers=h)).json()[0]
    assert p["estoque_atual"] == 10


async def test_import_never_creates_products(client):
    """O import NÃO mexe no catálogo: itens desconhecidos ficam pendentes de vínculo,
    agregados por cor/modelo (tamanhos somam na mesma pendência)."""
    h = await _register(client, "nocreate@loja.com")
    content = build_orders_xlsx(
        [
            order_row("PA1", "Enviado", "Blusa-Branco-M", qty=1, price=25.0),
            order_row("PA2", "Enviado", "Blusa-Branco-G", qty=2, price=25.0),
            order_row("PA3", "Enviado", None, qty=1, price=45.0,
                      name="Kit 2 Blusas Feminina Premium", var="Azul Marinho e Marrom, G",
                      **{"Número de referência SKU": ""}),
        ]
    )
    r = await client.post(
        "/api/imports/orders",
        files={"file": ("o.xlsx", content, "application/vnd.ms-excel")},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["summary"]["itens_pendentes_vinculo"] == 3
    # nenhum produto criado
    assert (await client.get("/api/products", headers=h)).json() == []

    pend = (await client.get("/api/mappings/pendentes", headers=h)).json()
    # 'Blusa-Branco-M' e '-G' viram UMA pendência (tamanhos agregados) + a do kit
    assert len(pend) == 2
    blusa = next(p for p in pend if (p["sku_var"] or "").startswith("Blusa-Branco"))
    assert blusa["qtd_unidades"] == 3
    assert blusa["novo_produto_sugerido"]["sku"] == "blusa-branco"

    # sem vínculo, nada entra na receita
    d = (await client.get("/api/reports/dashboard", headers=h)).json()
    assert d["receita_bruta"] == pytest.approx(0.0)


async def test_mapping_survives_reimport(client):
    """Regressão: vínculo feito na tela (sem canal) deve ser reconhecido no reimport —
    caso contrário os itens voltam a 'pendente' e o trabalho manual se perde."""
    h = await _register(client, "reimp@loja.com")
    pid = (
        await client.post(
            "/api/products", json={"sku": "camiseta-base", "nome": "Camiseta Base"}, headers=h
        )
    ).json()["id"]
    await client.post(
        "/api/stock-lots",
        json={"product_id": pid, "data_entrada": "2026-08-01", "qty_in": 20, "unit_cost": 5},
        headers=h,
    )
    # nome/sku do marketplace que NÃO casa com nada -> vira pendência
    content = build_orders_xlsx(
        [order_row("PRE1", "Enviado", "sku-marketplace-y", qty=2, price=30.0,
                   name="Nome Diferente do Anuncio", var="Cor Z")]
    )
    up = {"file": ("o.xlsx", content, "application/vnd.ms-excel")}
    await client.post("/api/imports/orders", files=up, headers=h)

    g = (await client.get("/api/mappings/pendentes", headers=h)).json()[0]
    # vincula pela tela (o front NÃO envia channel_id -> vínculo global)
    await client.post("/api/mappings", json={"match_key": g["match_key"], "product_id": pid}, headers=h)
    assert (await client.get("/api/mappings/pendentes", headers=h)).json() == []

    # reimportar o mesmo arquivo mantém o vínculo
    r = await client.post(
        "/api/imports/orders",
        files={"file": ("o.xlsx", content, "application/vnd.ms-excel")},
        headers=h,
    )
    assert r.json()["summary"]["itens_pendentes_vinculo"] == 0
    assert (await client.get("/api/mappings/pendentes", headers=h)).json() == []
    # e o estoque continua consistente (não conta em dobro)
    p = (await client.get("/api/products", headers=h)).json()[0]
    assert p["estoque_atual"] == 18


async def test_import_ads_idempotent(client):
    h = await _register(client, "ads@loja.com")
    r = await client.post(
        "/api/imports/ads",
        files={"file": ("ads.csv", ADS_CSV.encode("utf-8"), "text/csv")},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["summary"] == {
        "linhas": 2, "anuncios_agrupados": 0, "novos": 2, "atualizados": 0,
        "spend_total": 75.0, "gmv_total": 350.0, "erros": 0,
    }
    # reimport -> atualiza em vez de duplicar
    r = await client.post(
        "/api/imports/ads",
        files={"file": ("ads.csv", ADS_CSV.encode("utf-8"), "text/csv")},
        headers=h,
    )
    assert r.json()["summary"]["novos"] == 0
    assert r.json()["summary"]["atualizados"] == 2
    st = (await client.get("/api/imports", headers=h)).json()
    assert len(st["ads_periodos"]) == 1
    assert st["ads_periodos"][0]["spend"] == pytest.approx(75.0)