"""Testes da precificação — replica a aba Precificacao.

Cenário da própria planilha: Blusa - Azul, custo unit. 13, taxa Shopee 20%, taxa fixa 4,
afiliado 0, quantidade 1, lucro desejado 10 -> preço necessário.
"""
import pytest

from app.services import pricing

TOL = 1e-6


def test_modo_lucro_acha_preco():
    # preco = (lucro + fixa + outros + cmv) / (qty*(1-pct))
    #       = (10 + 4 + 0 + 13) / (1 * (1 - 0.2)) = 27 / 0.8 = 33.75
    res = pricing.simulate(
        custo_unitario=13.0,
        qty=1,
        modo="lucro",
        taxa_shopee_pct=0.20,
        taxa_fixa=4.0,
        taxa_afiliado_pct=0.0,
        outros_custos=0.0,
        lucro_desejado=10.0,
    )
    assert res["erro"] is False
    assert res["preco_unitario"] == pytest.approx(33.75, abs=TOL)
    assert res["lucro"] == pytest.approx(10.0, abs=TOL)  # sobra exatamente o lucro pedido
    # preço de equilíbrio (lucro zero) = (4 + 0 + 13)/0.8 = 21.25
    assert res["preco_equilibrio"] == pytest.approx(21.25, abs=TOL)
    assert res["markup"] == pytest.approx(33.75 / 13.0, abs=TOL)


def test_modo_preco_calcula_lucro():
    res = pricing.simulate(
        custo_unitario=13.0,
        qty=1,
        modo="preco",
        taxa_shopee_pct=0.20,
        taxa_fixa=4.0,
        preco_informado=33.75,
    )
    assert res["lucro"] == pytest.approx(10.0, abs=TOL)
    assert res["margem"] == pytest.approx(10.0 / 33.75, abs=TOL)


def test_taxas_acima_de_100pct_da_erro():
    res = pricing.simulate(
        custo_unitario=10.0,
        qty=1,
        modo="lucro",
        taxa_shopee_pct=0.8,
        taxa_fixa=4.0,
        taxa_afiliado_pct=0.3,
        lucro_desejado=5.0,
    )
    assert res["erro"] is True


def test_metas_de_anuncio():
    """A precificação também entrega as metas de anúncio: ROAS even e CPC máximo."""
    res = pricing.simulate(
        custo_unitario=13.0,
        qty=1,
        modo="preco",
        taxa_shopee_pct=0.20,
        taxa_fixa=4.0,
        preco_informado=33.75,
    )
    # lucro 10 sobre receita 33.75 -> margem 29.63% -> ROAS even 3.375x
    assert res["margem_por_venda"] == pytest.approx(10.0, abs=TOL)
    assert res["roas_even"] == pytest.approx(33.75 / 10.0, abs=1e-6)
    # CPC máximo = margem da venda × taxa de conversão
    m2 = next(m for m in res["metas_cpc"] if m["taxa_conversao"] == 0.02)
    assert m2["cpc_maximo"] == pytest.approx(0.20, abs=TOL)   # 10 × 2%
    assert m2["cliques_por_venda"] == 50
