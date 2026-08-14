"""Acerto de estoque pelo cadastro do produto (quando faltou registrar compras)."""
import pytest

from tests.test_shopee_import import _register, build_orders_xlsx, order_row


async def test_ajuste_cobre_deficit(client):
    """Cenário real: pedidos de um período maior que as entradas registradas →
    saldo real negativo. O acerto cria a entrada faltante datada ANTES da 1ª venda,
    então o FIFO das vendas antigas acha estoque e o CMV deixa de ser zero."""
    h = await _register(client, "ajuste@loja.com")
    pid = (
        await client.post("/api/products", json={"sku": "sku-a", "nome": "Produto A"}, headers=h)
    ).json()["id"]
    # comprou 10 (em 09/08), mas vendeu 17 (vendas começam em 05/08)
    await client.post(
        "/api/stock-lots",
        json={"product_id": pid, "data_entrada": "2026-08-09", "qty_in": 10, "unit_cost": 12},
        headers=h,
    )
    content = build_orders_xlsx(
        [order_row("V1", "Enviado", "sku-a", qty=17, price=30.0)]  # data 05/08
    )
    await client.post(
        "/api/imports/orders",
        files={"file": ("o.xlsx", content, "application/vnd.ms-excel")},
        headers=h,
    )

    p = (await client.get("/api/products", headers=h)).json()[0]
    assert p["estoque_atual"] == 0       # mascarado em zero
    assert p["saldo_real"] == -7         # a verdade: faltam 7
    assert p["deficit"] == 7

    # digo que tenho 3 hoje, comprados a 10.00 -> precisa criar +10 (3 - (-7))
    r = await client.post(
        f"/api/products/{pid}/ajuste-estoque",
        json={"estoque_atual": 3, "custo_unitario": 10.0},
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ajuste"] == 10
    assert body["data_entrada"] == "2026-08-04"  # dia anterior à 1ª venda (05/08)

    p = (await client.get("/api/products", headers=h)).json()[0]
    assert p["estoque_atual"] == 3
    assert p["saldo_real"] == 3
    assert p["deficit"] == 0

    # o CMV da venda agora existe: FIFO consome 10 un @10 (acerto) + 7 un @12 = 184
    d = (await client.get("/api/reports/dashboard", headers=h)).json()
    assert d["cmv"] == pytest.approx(184.0)

    # repetir o acerto com o mesmo valor não duplica nada
    r = await client.post(
        f"/api/products/{pid}/ajuste-estoque",
        json={"estoque_atual": 3, "custo_unitario": 10.0},
        headers=h,
    )
    assert r.json()["ajuste"] == 0
    assert (await client.get("/api/products", headers=h)).json()[0]["estoque_atual"] == 3


async def test_ajuste_para_menos_e_recusado(client):
    h = await _register(client, "ajuste2@loja.com")
    pid = (
        await client.post("/api/products", json={"sku": "sku-b", "nome": "Produto B"}, headers=h)
    ).json()["id"]
    await client.post(
        "/api/stock-lots",
        json={"product_id": pid, "data_entrada": "2026-08-01", "qty_in": 10, "unit_cost": 5},
        headers=h,
    )
    r = await client.post(
        f"/api/products/{pid}/ajuste-estoque",
        json={"estoque_atual": 4, "custo_unitario": 5.0},
        headers=h,
    )
    assert r.status_code == 400
    assert "menor que o calculado" in r.json()["detail"]
