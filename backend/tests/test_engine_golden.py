"""Testes do motor de cálculo contra um fixture sintético (valores calculados à mão).

Não usa dados reais. O dataset é pequeno e determinístico, então os valores esperados
são verificáveis manualmente — cobrindo FIFO por lote, CMV de kit, taxas, dashboard,
balanço diário e estoque diário.

Dataset:
- Produto A: lote1 10 un @ 5 (01/01), lote2 10 un @ 8 (05/01)
- Produto B: lote  20 un @ 3 (01/01)
- Kit K = 1×A + 1×B
- Venda S1 (10/01): A, 6 un @ 20   -> CMV FIFO = 6×5 = 30
- Venda S2 (11/01): A, 6 un @ 20   -> CMV FIFO = (10×5 + 2×8) - 30 = 36
- Venda S3 (12/01): Kit K, 2 un @ 50 -> CMV = (custo_médio_A + custo_médio_B)×2 = (8+3)×2 = 22
- Ads: 20 em 12/01
Taxas: Shopee 20% + fixa R$4 por pedido.
"""
from datetime import date

import pytest

from app.services import engine
from app.services.snapshot import SAd, SKit, SKitComponent, SLot, SProduct, SSale, Snapshot

TOL = 1e-9


@pytest.fixture(scope="module")
def snap():
    return Snapshot(
        products=[
            SProduct(id=1, sku="A", nome="Produto A", dropdown_name="Produto A"),
            SProduct(id=2, sku="B", nome="Produto B", dropdown_name="Produto B"),
        ],
        lots=[
            SLot(id=1, product_id=1, data_entrada=date(2026, 1, 1), qty_in=10, unit_cost=5.0),
            SLot(id=2, product_id=1, data_entrada=date(2026, 1, 5), qty_in=10, unit_cost=8.0),
            SLot(id=3, product_id=2, data_entrada=date(2026, 1, 1), qty_in=20, unit_cost=3.0),
        ],
        kits=[
            SKit(
                id=1,
                sku="K",
                nome="Kit A+B",
                components=[SKitComponent(product_id=1, qty=1), SKitComponent(product_id=2, qty=1)],
            )
        ],
        sales=[
            SSale(id=1, data_venda=date(2026, 1, 10), item_type="product", product_id=1, qty=6,
                  preco_unitario=20.0, taxa_shopee_pct=0.2, taxa_fixa=4.0, pedido="S1"),
            SSale(id=2, data_venda=date(2026, 1, 11), item_type="product", product_id=1, qty=6,
                  preco_unitario=20.0, taxa_shopee_pct=0.2, taxa_fixa=4.0, pedido="S2"),
            SSale(id=3, data_venda=date(2026, 1, 12), item_type="kit", kit_id=1, qty=2,
                  preco_unitario=50.0, taxa_shopee_pct=0.2, taxa_fixa=4.0, pedido="S3"),
        ],
        ads=[SAd(id=1, data=date(2026, 1, 12), valor=20.0)],
    )


def _row(rows, pedido):
    return next(r for r in rows if r["pedido"] == pedido)


def test_fifo_produto(snap):
    rows = engine.sale_rows(snap)
    s1 = _row(rows, "S1")
    assert s1["cmv"] == pytest.approx(30.0, abs=TOL)  # 6×5
    assert s1["receita_liquida"] == pytest.approx(92.0, abs=TOL)  # 120 - 24 - 4
    assert s1["lucro"] == pytest.approx(62.0, abs=TOL)
    s2 = _row(rows, "S2")
    assert s2["cmv"] == pytest.approx(36.0, abs=TOL)  # atravessa lote1->lote2
    assert s2["lucro"] == pytest.approx(56.0, abs=TOL)


def test_cmv_kit(snap):
    s3 = _row(engine.sale_rows(snap), "S3")
    assert s3["cmv"] == pytest.approx(22.0, abs=TOL)  # (8+3)×2
    assert s3["receita_liquida"] == pytest.approx(76.0, abs=TOL)  # 100 - 20 - 4
    assert s3["lucro"] == pytest.approx(54.0, abs=TOL)


def test_product_states(snap):
    ps = engine.product_states(snap)
    by = {v["sku"]: v for v in ps.values()}
    assert by["A"]["estoque_atual"] == 6  # 20 - 12 diretas - 2 kits
    assert by["A"]["valor_estoque"] == pytest.approx(48.0, abs=TOL)  # 6 × 8
    assert by["A"]["custo_medio_atual"] == pytest.approx(8.0, abs=TOL)
    assert by["A"]["vendas_diretas"] == 12
    assert by["A"]["consumo_kits"] == 2
    assert by["B"]["estoque_atual"] == 18
    assert by["B"]["custo_medio_atual"] == pytest.approx(3.0, abs=TOL)


def test_dashboard(snap):
    d = engine.dashboard(snap)
    assert d["receita_bruta"] == pytest.approx(340.0, abs=TOL)
    assert d["cmv"] == pytest.approx(88.0, abs=TOL)  # 30 + 36 + 22
    assert d["taxas_totais"] == pytest.approx(80.0, abs=TOL)  # 68 shopee + 12 fixa
    assert d["receita_liquida"] == pytest.approx(260.0, abs=TOL)
    assert d["lucro_antes_ads"] == pytest.approx(172.0, abs=TOL)
    assert d["ads_total"] == pytest.approx(20.0, abs=TOL)
    assert d["lucro_apos_ads"] == pytest.approx(152.0, abs=TOL)
    assert d["estoque_total"] == 24
    assert d["valor_estoque"] == pytest.approx(102.0, abs=TOL)


def test_balanco_com_roas(snap):
    b = next(x for x in engine.balanco_diario(snap) if x["data"] == date(2026, 1, 12))
    assert b["qty"] == 2
    assert b["receita_bruta"] == pytest.approx(100.0, abs=TOL)
    assert b["cmv"] == pytest.approx(22.0, abs=TOL)
    assert b["ads"] == pytest.approx(20.0, abs=TOL)
    assert b["lucro_apos_ads"] == pytest.approx(34.0, abs=TOL)  # 76 - 22 - 20
    assert b["roas"] == pytest.approx(5.0, abs=TOL)  # 100 / 20


def test_estoque_diario(snap):
    ed = engine.estoque_diario(snap, date(2026, 1, 12))
    assert ed["pecas_que_sairam"] == 4  # kit 2× -> 2 A + 2 B
    assert ed["estoque_final"] == 24
    a = next(l for l in ed["linhas"] if l["sku"] == "A")
    assert a["estoque_inicio"] == 8  # 20 - 12 diretas antes
    assert a["venda_unitaria"] == 0
    assert a["saida_via_kits"] == 2
    assert a["estoque_fim"] == 6


def test_estoque_diario_range(snap):
    dias = engine.estoque_diario_range(snap)
    assert [r["data"] for r in dias] == [date(2026, 1, 10), date(2026, 1, 11), date(2026, 1, 12)]
    d12 = next(r for r in dias if r["data"] == date(2026, 1, 12))
    assert d12["pecas_que_sairam"] == 4
    assert d12["estoque_final"] == 24
    so12 = engine.estoque_diario_range(snap, dt_from=date(2026, 1, 12))
    assert [r["data"] for r in so12] == [date(2026, 1, 12)]
