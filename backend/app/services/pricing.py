"""Precificação inteligente (aba Precificacao) — função pura.

Modo 'lucro'  -> dado o lucro desejado, acha o preço necessário.
Modo 'preco'  -> dado o preço, calcula o lucro resultante.

Fórmula (modo lucro), idêntica à planilha:
    preco = (lucro + taxa_fixa + outros + cmv) / (qty * (1 - pct_total))
onde pct_total = taxa_shopee_pct + taxa_afiliado_pct  e  cmv = custo_unit * qty.
"""
from __future__ import annotations


def simulate(
    *,
    custo_unitario: float,
    qty: int,
    modo: str,  # 'lucro' | 'preco'
    taxa_shopee_pct: float,
    taxa_fixa: float,
    taxa_afiliado_pct: float = 0.0,
    outros_custos: float = 0.0,
    lucro_desejado: float | None = None,
    preco_informado: float | None = None,
) -> dict:
    pct_total = taxa_shopee_pct + taxa_afiliado_pct
    cmv = custo_unitario * qty

    erro = None
    if qty <= 0:
        erro = "Quantidade deve ser maior que zero"
    elif pct_total >= 1:
        erro = "ERRO: taxas percentuais somam 100% ou mais"

    if erro:
        return {"status": erro, "preco_unitario": 0.0, "erro": True}

    if modo == "lucro":
        alvo = lucro_desejado or 0.0
        preco = (alvo + taxa_fixa + outros_custos + cmv) / (qty * (1 - pct_total))
        status = "Preço necessário calculado"
    else:  # preco
        preco = preco_informado or 0.0
        status = "Lucro calculado"

    receita = preco * qty
    taxa_shopee_rs = receita * taxa_shopee_pct
    taxa_afiliado_rs = receita * taxa_afiliado_pct
    taxa_fixa_rs = taxa_fixa
    lucro = receita - taxa_shopee_rs - taxa_afiliado_rs - taxa_fixa_rs - outros_custos - cmv
    preco_equilibrio = (taxa_fixa + outros_custos + cmv) / (qty * (1 - pct_total))

    return {
        "status": status,
        "erro": False,
        "preco_unitario": preco,
        "receita_bruta": receita,
        "taxa_shopee_rs": taxa_shopee_rs,
        "taxa_afiliado_rs": taxa_afiliado_rs,
        "taxa_fixa_rs": taxa_fixa_rs,
        "outros_custos": outros_custos,
        "cmv": cmv,
        "lucro": lucro,
        "lucro_unitario": (lucro / qty) if qty else 0.0,
        "margem": (lucro / receita) if receita else 0.0,
        "preco_equilibrio": preco_equilibrio,
        "markup": (preco / custo_unitario) if custo_unitario else 0.0,
    }
