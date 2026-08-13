"""Teste de integração da API: auth multi-tenant + CRUD + cálculo + isolamento."""
import pytest


async def _register(client, email, org=None):
    r = await client.post(
        "/api/auth/register",
        json={"name": "Ree", "email": email, "password": "secret1", "org_name": org},
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_auth_crud_and_isolation(client):
    h = await _register(client, "dono@loja.com", "Minha Loja")

    # produto
    r = await client.post("/api/products", json={"sku": "p1", "nome": "Prod 1"}, headers=h)
    assert r.status_code == 201, r.text
    pid = r.json()["id"]

    # SKU duplicado -> 409
    r = await client.post("/api/products", json={"sku": "p1", "nome": "Outro"}, headers=h)
    assert r.status_code == 409

    # lote de entrada (FIFO)
    r = await client.post(
        "/api/stock-lots",
        json={"product_id": pid, "data_entrada": "2026-08-01", "qty_in": 10, "unit_cost": 5},
        headers=h,
    )
    assert r.status_code == 201, r.text

    # venda de produto: receita 40, shopee 20% = 8, fixa 4 -> liquida 28; CMV FIFO 2*5=10; lucro 18
    r = await client.post(
        "/api/sales",
        json={
            "data_venda": "2026-08-02",
            "item_type": "product",
            "product_id": pid,
            "qty": 2,
            "preco_unitario": 20,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    row = r.json()
    assert row["cmv"] == pytest.approx(10.0)
    assert row["receita_liquida"] == pytest.approx(28.0)
    assert row["lucro"] == pytest.approx(18.0)

    # estoque do produto caiu para 8
    r = await client.get("/api/products", headers=h)
    assert r.json()[0]["estoque_atual"] == 8

    # dashboard reflete a venda
    d = (await client.get("/api/reports/dashboard", headers=h)).json()
    assert d["receita_bruta"] == pytest.approx(40.0)
    assert d["cmv"] == pytest.approx(10.0)

    # precificação (custo manual, modo lucro): custo 5, shopee 20%, fixa 4, lucro desejado 10
    # preco = (lucro + fixa + cmv)/(qty*(1-pct)) = (10 + 4 + 5)/(1*(1-0.2)) = 19/0.8 = 23.75
    r = await client.post(
        "/api/pricing/simulate",
        json={"custo_unitario": 5, "qty": 1, "modo": "lucro", "lucro_desejado": 10},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["preco_unitario"] == pytest.approx(23.75)

    # ISOLAMENTO: outra loja não enxerga os produtos da primeira
    h2 = await _register(client, "outro@loja.com", "Loja 2")
    assert (await client.get("/api/products", headers=h2)).json() == []
    # e não pode vender o produto da loja 1
    r = await client.post(
        "/api/sales",
        json={
            "data_venda": "2026-08-02",
            "item_type": "product",
            "product_id": pid,
            "qty": 1,
            "preco_unitario": 20,
        },
        headers=h2,
    )
    assert r.status_code == 400


async def test_requires_auth(client):
    assert (await client.get("/api/products")).status_code == 401


async def test_user_management(client):
    h = await _register(client, "dona@loja.com", "Loja X")

    # convidar membro
    r = await client.post(
        "/api/auth/users",
        json={"name": "Membro", "email": "membro@loja.com", "password": "inicial1"},
        headers=h,
    )
    assert r.status_code == 201
    mid = r.json()["id"]
    assert len((await client.get("/api/auth/users", headers=h)).json()) == 2

    # owner troca a senha do membro
    r = await client.patch(
        f"/api/auth/users/{mid}/password", json={"password": "novaSenha1"}, headers=h
    )
    assert r.status_code == 200
    # membro entra com a nova senha
    r = await client.post(
        "/api/auth/login", json={"email": "membro@loja.com", "password": "novaSenha1"}
    )
    assert r.status_code == 200
    hm = {"Authorization": f"Bearer {r.json()['access_token']}"}

    # membro (não-owner) não pode gerenciar
    assert (
        await client.patch(f"/api/auth/users/{mid}/password", json={"password": "x123456"}, headers=hm)
    ).status_code == 403
    assert (await client.delete(f"/api/auth/users/{mid}", headers=hm)).status_code == 403

    # owner não pode excluir a si mesmo
    me = (await client.get("/api/auth/me", headers=h)).json()
    assert (await client.delete(f"/api/auth/users/{me['id']}", headers=h)).status_code == 400

    # owner exclui o membro
    assert (await client.delete(f"/api/auth/users/{mid}", headers=h)).status_code == 204
    assert len((await client.get("/api/auth/users", headers=h)).json()) == 1


async def _product_with_stock(client, h, sku, qty=10, cost=5):
    pid = (await client.post("/api/products", json={"sku": sku, "nome": sku}, headers=h)).json()["id"]
    await client.post(
        "/api/stock-lots",
        json={"product_id": pid, "data_entrada": "2026-08-01", "qty_in": qty, "unit_cost": cost},
        headers=h,
    )
    return pid


async def test_estoque_explicado_breakdown(client):
    h = await _register(client, "brk@loja.com")
    pid = await _product_with_stock(client, h, "sku-brk", qty=10)
    await client.post(
        "/api/sales",
        json={
            "data_venda": "2026-08-02",
            "item_type": "product",
            "product_id": pid,
            "qty": 3,
            "preco_unitario": 20,
        },
        headers=h,
    )
    p = (await client.get("/api/products", headers=h)).json()[0]
    assert p["entradas"] == 10
    assert p["vendas_diretas"] == 3
    assert p["consumo_kits"] == 0
    assert p["estoque_atual"] == 7  # 10 - 3 - 0


async def test_stock_guardrail(client):
    h = await _register(client, "grd@loja.com")
    pid = await _product_with_stock(client, h, "sku-grd", qty=5)
    base = {
        "data_venda": "2026-08-02",
        "item_type": "product",
        "product_id": pid,
        "preco_unitario": 20,
    }
    # vender 8 com 5 em estoque -> bloqueia
    r = await client.post("/api/sales", json={**base, "qty": 8}, headers=h)
    assert r.status_code == 409
    assert "insuficiente" in r.json()["detail"].lower()
    # com override -> permite
    r = await client.post(
        "/api/sales", json={**base, "qty": 8, "permitir_sem_estoque": True}, headers=h
    )
    assert r.status_code == 201


async def test_channels_and_fees(client):
    h = await _register(client, "canal@loja.com")
    # register cria um canal "Shopee" padrão
    chans = (await client.get("/api/channels", headers=h)).json()
    assert any(c["name"] == "Shopee" for c in chans)

    # cria canal TikTok com taxa 5% + fixa R$2
    r = await client.post("/api/channels", json={"name": "TikTok", "taxa_pct": 0.05, "taxa_fixa": 2}, headers=h)
    assert r.status_code == 201, r.text
    tid = r.json()["id"]

    pid = await _product_with_stock(client, h, "sku-ch", qty=10)
    # venda no TikTok sem informar taxas -> usa as taxas do canal
    r = await client.post(
        "/api/sales",
        json={
            "data_venda": "2026-08-02",
            "item_type": "product",
            "product_id": pid,
            "channel_id": tid,
            "qty": 1,
            "preco_unitario": 100,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    row = r.json()
    assert row["channel"] == "TikTok"
    assert row["taxa_shopee_rs"] == pytest.approx(5.0)  # 100 * 0.05
    assert row["taxa_fixa_rs"] == pytest.approx(2.0)


async def test_csv_import(client):
    h = await _register(client, "csv@loja.com")
    await _product_with_stock(client, h, "csvsku", qty=100)
    csv_bytes = (
        "data;pedido;sku;qty;preco_unitario\n"
        "2026-08-05;ORD1;csvsku;1;25,00\n"
        "2026-08-06;ORD2;csvsku;2;30,00\n"
    ).encode("utf-8")

    # dry-run: só valida
    r = await client.post(
        "/api/sales/import",
        files={"file": ("vendas.csv", csv_bytes, "text/csv")},
        params={"dry_run": "true"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["summary"] == {"total": 2, "novos": 2, "duplicados": 0, "erros": 0}
    assert (await client.get("/api/sales", headers=h)).json() == []  # nada inserido no dry-run

    # importação real
    r = await client.post(
        "/api/sales/import",
        files={"file": ("vendas.csv", csv_bytes, "text/csv")},
        headers=h,
    )
    assert r.json()["summary"]["novos"] == 2
    assert len(((await client.get("/api/sales", headers=h)).json())) == 2

    # reimportar o mesmo arquivo -> idempotente (duplicados)
    r = await client.post(
        "/api/sales/import",
        files={"file": ("vendas.csv", csv_bytes, "text/csv")},
        headers=h,
    )
    assert r.json()["summary"] == {"total": 2, "novos": 0, "duplicados": 2, "erros": 0}
