"""Testes da visão geral (home analítica) sobre dados sintéticos importados."""
import pytest

from tests.test_shopee_import import ADS_CSV, _register, build_orders_xlsx, order_row


async def test_visao_geral(client):
    h = await _register(client, "vg@loja.com")
    pid = (await client.post("/api/products", json={"sku": "sku-a", "nome": "Produto A"}, headers=h)).json()["id"]
    await client.post(
        "/api/stock-lots",
        json={"product_id": pid, "data_entrada": "2026-08-01", "qty_in": 50, "unit_cost": 5},
        headers=h,
    )
    content = build_orders_xlsx(
        [
            # concluído: dinheiro em caixa
            order_row("VG1", "Concluído", "sku-a", qty=2, price=20.0),
            # enviado: a receber
            order_row("VG2", "Enviado", "sku-a", qty=1, price=20.0),
            # cancelado: perdido (não conta receita nem estoque)
            order_row("VG3", "Cancelado", "sku-a", qty=1, price=20.0,
                      **{"Valor Total": "0.00", "Total global": "0.00"}),
        ]
    )
    await client.post(
        "/api/imports/orders",
        files={"file": ("o.xlsx", content, "application/vnd.ms-excel")},
        headers=h,
    )
    await client.post(
        "/api/imports/ads",
        files={"file": ("ads.csv", ADS_CSV.encode("utf-8"), "text/csv")},
        headers=h,
    )

    r = await client.get(
        "/api/reports/visao-geral", params={"from": "2026-08-01", "to": "2026-08-13"}, headers=h
    )
    assert r.status_code == 200, r.text
    vg = r.json()

    # KPIs: 3 unidades vendidas (2+1), receita 60
    assert vg["kpis"]["faturamento"] == pytest.approx(60.0)
    assert vg["kpis"]["unidades"] == 3

    # caixa: recebido = Total global do concluído; a receber = do enviado
    assert vg["caixa"]["recebido"] == pytest.approx(33.0)  # 40 - 7
    assert vg["caixa"]["a_receber"] == pytest.approx(13.0)  # 20 - 7
    assert vg["caixa"]["pedidos"] == 3
    assert vg["caixa"]["pedidos_cancelados"] == 1

    # custos: cmv = 3 un × 5 = 15; ads importado (fonte geral) = 75
    assert vg["custos"]["cmv"] == pytest.approx(15.0)
    assert vg["custos"]["fonte_ads"] == "importado"
    assert vg["ads"]["spend"] == pytest.approx(75.0)
    assert vg["ads"]["roas"] == pytest.approx(350.0 / 75.0)

    # tops: produto A lidera vendas e lucro
    assert vg["top_vendas"][0]["sku"] == "sku-a"
    assert vg["top_vendas"][0]["unidades"] == 3
    assert vg["top_lucro"][0]["lucro"] > 0

    # vereditos de ads presentes (2 anúncios do CSV, ambos com spend > 0)
    assert len(vg["ads_produtos"]) == 2
    assert all(p["veredito"] in ("escalar", "ok", "atencao", "pausar") for p in vg["ads_produtos"])

    # insights existem e têm a estrutura dos cards
    assert vg["insights"]
    assert all({"tipo", "icone", "titulo", "texto"} <= set(i) for i in vg["insights"])
