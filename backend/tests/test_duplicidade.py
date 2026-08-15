"""Regressão: a mesma venda não pode ser contada duas vezes.

Cenário real encontrado em produção: o pedido foi lançado à mão (ou por CSV de vendas)
E também importado do marketplace — a receita, o lucro e o estoque contavam em dobro.
"""
import pytest

from tests.test_shopee_import import _register, build_orders_xlsx, order_row


async def _produto_com_estoque(client, h, sku="sku-a", qty=50):
    pid = (
        await client.post("/api/products", json={"sku": sku, "nome": sku}, headers=h)
    ).json()["id"]
    await client.post(
        "/api/stock-lots",
        json={"product_id": pid, "data_entrada": "2026-08-01", "qty_in": qty, "unit_cost": 5},
        headers=h,
    )
    return pid


async def test_manual_e_importado_nao_somam_duas_vezes(client):
    h = await _register(client, "dup1@loja.com")
    pid = await _produto_com_estoque(client, h)

    # 1) lançamento manual do pedido PED-X
    r = await client.post(
        "/api/sales",
        json={
            "data_venda": "2026-08-05",
            "pedido": "PED-X",
            "item_type": "product",
            "product_id": pid,
            "qty": 2,
            "preco_unitario": 30.0,
        },
        headers=h,
    )
    assert r.status_code == 201
    d = (await client.get("/api/reports/dashboard", headers=h)).json()
    assert d["receita_bruta"] == pytest.approx(60.0)

    # 2) o MESMO pedido chega pelo import do marketplace
    content = build_orders_xlsx(
        [order_row("PED-X", "Enviado", "sku-a", qty=2, price=30.0)]
    )
    await client.post(
        "/api/imports/orders",
        files={"file": ("o.xlsx", content, "application/vnd.ms-excel")},
        headers=h,
    )

    # receita NÃO dobra — o importado (taxas reais) prevalece sobre o manual
    d = (await client.get("/api/reports/dashboard", headers=h)).json()
    assert d["receita_bruta"] == pytest.approx(60.0)
    # estoque consumiu 2 (não 4)
    p = (await client.get("/api/products", headers=h)).json()[0]
    assert p["estoque_atual"] == 48

    # a venda manual aparece como duplicada e pode ser removida
    dup = (await client.get("/api/sales/duplicadas", headers=h)).json()
    assert dup["total"] == 1 and dup["vendas"][0]["pedido"] == "PED-X"
    r = await client.delete("/api/sales/duplicadas", headers=h)
    assert r.json()["removidas"] == 1
    assert (await client.get("/api/sales/duplicadas", headers=h)).json()["total"] == 0
    # números seguem iguais depois da limpeza
    d = (await client.get("/api/reports/dashboard", headers=h)).json()
    assert d["receita_bruta"] == pytest.approx(60.0)


async def test_manual_recusa_pedido_repetido(client):
    h = await _register(client, "dup2@loja.com")
    pid = await _produto_com_estoque(client, h)
    venda = {
        "data_venda": "2026-08-05",
        "pedido": "PED-Y",
        "item_type": "product",
        "product_id": pid,
        "qty": 1,
        "preco_unitario": 20.0,
    }
    assert (await client.post("/api/sales", json=venda, headers=h)).status_code == 201
    # segundo lançamento do mesmo pedido é recusado
    r = await client.post("/api/sales", json=venda, headers=h)
    assert r.status_code == 409
    assert "já foi lançado" in r.json()["detail"]


async def test_manual_recusa_pedido_ja_importado(client):
    h = await _register(client, "dup3@loja.com")
    pid = await _produto_com_estoque(client, h)
    content = build_orders_xlsx([order_row("PED-Z", "Enviado", "sku-a", qty=1, price=25.0)])
    await client.post(
        "/api/imports/orders",
        files={"file": ("o.xlsx", content, "application/vnd.ms-excel")},
        headers=h,
    )
    r = await client.post(
        "/api/sales",
        json={
            "data_venda": "2026-08-05",
            "pedido": "PED-Z",
            "item_type": "product",
            "product_id": pid,
            "qty": 1,
            "preco_unitario": 25.0,
        },
        headers=h,
    )
    assert r.status_code == 409
    assert "importado do marketplace" in r.json()["detail"]


async def test_csv_sem_numero_de_pedido_nao_duplica(client):
    """Linhas sem número de pedido usam data+item+qtd+preço como chave."""
    h = await _register(client, "dup4@loja.com")
    await _produto_com_estoque(client, h, sku="csvsku")
    csv_bytes = "data;sku;qty;preco_unitario\n2026-08-05;csvsku;1;25,00\n".encode("utf-8")
    up = {"file": ("v.csv", csv_bytes, "text/csv")}
    r = await client.post("/api/sales/import", files=up, headers=h)
    assert r.json()["summary"]["novos"] == 1
    # reimportar o mesmo arquivo não duplica
    r = await client.post(
        "/api/sales/import",
        files={"file": ("v.csv", csv_bytes, "text/csv")},
        headers=h,
    )
    assert r.json()["summary"] == {"total": 1, "novos": 0, "duplicados": 1, "erros": 0}
    assert len((await client.get("/api/sales", headers=h)).json()) == 1
