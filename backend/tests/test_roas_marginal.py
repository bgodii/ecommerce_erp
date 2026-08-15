"""ROAS marginal: o retorno do dinheiro EXTRA decide se vale escalar.

Regra: lucro é máximo quando o marginal encosta no ROAS even. Acima dele, subir rende;
abaixo, cada real a mais destrói lucro — mesmo com o ROAS médio parecendo ótimo.
"""
import pytest

from tests.test_shopee_import import _register, build_orders_xlsx, order_row


def ads_csv(period_de: str, period_ate: str, spend: float, gmv: float) -> bytes:
    """Relatório de ADS de um período específico (semanal), com 1 anúncio."""
    return (
        "﻿Relatório de Todos os Anúncios CPC - Shopee Brasil\r\n"
        "Nome de Usuário,loja\r\nNome da loja,Loja\r\nID da Loja,1\r\n"
        "Data de Criação do Relatório,13/08/2026 23:22\r\n"
        f"Período,{period_de} - {period_ate}\r\n\r\n"
        "#,Nome do Anúncio,Status,Tipos de Anúncios,ID do produto,Criativo,Método de Lance,"
        "Posicionamento,Data de Início,Data de Encerramento,Impressões,Cliques,CTR,"
        "Adicionar ao carrinho,Taxa de adição ao carrinho,Conversões,Conversões Diretas,"
        "Taxa de Conversão,Taxa de Conversão Direta,Custo por Conversão,Custo por Conversão Direta,"
        "Itens Vendidos,Itens Vendidos Diretos,GMV,Receita direta,Despesas,ROAS,ROAS Direto,"
        "ACOS,ACOS Direto,Impressões do Produto,Cliques de Produtos,CTR do Produto,"
        "Voucher Amount,Vouchered Sales\r\n"
        f"1,Anuncio A,Em Andamento,Auto,111,-,Auto,Todos,01/08/2026 00:00:00,Ilimitado,"
        f"1000,100,10%,10,10%,10,10,10%,10%,1,1,10,10,{gmv:.2f},{gmv:.2f},{spend:.2f},"
        f"{gmv/spend:.2f},{gmv/spend:.2f},10%,10%,-,-,-,0.00,0.00\r\n"
    ).encode("utf-8")


async def _loja_com_margem(client, email):
    """Loja com margem conhecida: preço 100, custo 60, taxa 20% -> margem 20% -> even 5x."""
    h = await _register(client, email)
    pid = (
        await client.post("/api/products", json={"sku": "sku-a", "nome": "A"}, headers=h)
    ).json()["id"]
    await client.post(
        "/api/stock-lots",
        json={"product_id": pid, "data_entrada": "2026-08-01", "qty_in": 500, "unit_cost": 60},
        headers=h,
    )
    # vendas dão a margem: 100 - 20% taxa - 60 custo = 20 -> 20%
    content = build_orders_xlsx(
        [
            order_row(f"P{i}", "Enviado", "sku-a", qty=1, price=100.0,
                      **{"Valor Total": "100.00", "Taxa de comissão líquida": "20.00",
                         "Taxa de serviço líquida": "0.00", "Taxa de transação": "0.00",
                         "Total global": "80.00", "Data de criação do pedido": "2026-08-12 10:00"})
            for i in range(10)
        ]
    )
    await client.post(
        "/api/imports/orders",
        files={"file": ("o.xlsx", content, "application/vnd.ms-excel")},
        headers=h,
    )
    return h


async def test_marginal_acima_do_even_manda_escalar(client):
    h = await _loja_com_margem(client, "mg1@loja.com")
    # semana anterior: 100 de ads -> 800 GMV | semana atual: 200 -> 2400
    # marginal = (2400-800)/(200-100) = 16x  >> even 5x
    await client.post("/api/imports/ads",
        files={"file": ("a1.csv", ads_csv("01/08/2026", "07/08/2026", 100, 800), "text/csv")},
        headers=h)
    await client.post("/api/imports/ads",
        files={"file": ("a2.csv", ads_csv("08/08/2026", "14/08/2026", 200, 2400), "text/csv")},
        headers=h)

    r = await client.get("/api/reports/roas-marginal", params={"dias": 7, "ate": "2026-08-14"}, headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["atual"]["spend"] == pytest.approx(200.0)
    assert d["anterior"]["spend"] == pytest.approx(100.0)
    assert d["roas_marginal"] == pytest.approx(16.0)
    assert d["roas_even"] == pytest.approx(5.0, abs=0.01)
    assert d["veredito"] == "escalar"
    assert d["confiavel"] is True


async def test_marginal_abaixo_do_even_manda_voltar(client):
    """O ROAS MÉDIO continua ótimo, mas o dinheiro extra rendeu pouco -> voltar."""
    h = await _loja_com_margem(client, "mg2@loja.com")
    # anterior: 100 -> 800 (8x) | atual: 200 -> 1000 (5x médio, ainda = even)
    # marginal = (1000-800)/100 = 2x  << even 5x
    await client.post("/api/imports/ads",
        files={"file": ("a1.csv", ads_csv("01/08/2026", "07/08/2026", 100, 800), "text/csv")},
        headers=h)
    await client.post("/api/imports/ads",
        files={"file": ("a2.csv", ads_csv("08/08/2026", "14/08/2026", 200, 1000), "text/csv")},
        headers=h)

    d = (await client.get("/api/reports/roas-marginal",
                          params={"dias": 7, "ate": "2026-08-14"}, headers=h)).json()
    assert d["atual"]["roas"] == pytest.approx(5.0)   # média ainda no even
    assert d["roas_marginal"] == pytest.approx(2.0)   # mas o extra rendeu 2x
    assert d["veredito"] == "voltar"


async def test_relatorio_mensal_unico_nao_permite_marginal(client):
    """Com um só relatório agregado, os dois períodos são rateios do mesmo dado."""
    h = await _loja_com_margem(client, "mg3@loja.com")
    await client.post("/api/imports/ads",
        files={"file": ("a.csv", ads_csv("01/08/2026", "31/08/2026", 300, 2000), "text/csv")},
        headers=h)
    d = (await client.get("/api/reports/roas-marginal",
                          params={"dias": 7, "ate": "2026-08-20"}, headers=h)).json()
    assert d["veredito"] == "sem_dados"
    assert d["confiavel"] is False
    assert "por semana" in d["recomendacao"]
