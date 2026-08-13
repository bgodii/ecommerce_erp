"""Motor de cálculo do ERP — funções puras que replicam as fórmulas da planilha.

Regras espelhadas da planilha `ERP - Ecommer.xlsx`:
- FIFO por lote: o CMV de uma venda de PRODUTO segue o custo dos lotes mais antigos,
  na posição acumulada das vendas diretas daquele SKU (colunas O/P/Q da aba Vendas).
- CMV de KIT = soma(qtd_componente * custo_medio_atual_do_componente) * qtd_vendida
  (aba Vendas usa os custos da aba Composicao Kits).
- Estoque físico do produto = entradas - vendas diretas - consumo via kits.
- Taxas: receita - taxa_shopee% - taxa_fixa(por pedido) - afiliado% - outras.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date

from app.services.snapshot import Snapshot

# ordenações canônicas (determinísticas)
def _sorted_lots(lots):
    return sorted(lots, key=lambda l: (l.data_entrada, l.id))


def _sorted_sales(sales):
    return sorted(sales, key=lambda s: (s.data_venda, s.id))


def _cost_of_first_n(sorted_lots, n: int) -> float:
    """Custo acumulado das primeiras `n` unidades consumidas em FIFO."""
    cost = 0.0
    before = 0
    for lot in sorted_lots:
        units = min(max(n - before, 0), lot.qty_in)
        cost += units * lot.unit_cost
        before += lot.qty_in
    return cost


# ---------------------------------------------------------------------------
# Estado dos produtos (estoque, valor, custo médio) e dos lotes (saldo)
# ---------------------------------------------------------------------------
def product_states(snap: Snapshot) -> dict[int, dict]:
    lots_by_p: dict[int, list] = defaultdict(list)
    for lot in snap.lots:
        lots_by_p[lot.product_id].append(lot)

    direct_out: dict[int, int] = defaultdict(int)
    kit_out: dict[int, int] = defaultdict(int)
    kit_by_id = {k.id: k for k in snap.kits}
    for s in snap.sales:
        if s.item_type == "product" and s.product_id is not None:
            direct_out[s.product_id] += s.qty
        elif s.item_type == "kit" and s.kit_id is not None:
            kit = kit_by_id.get(s.kit_id)
            if kit:
                for c in kit.components:
                    kit_out[c.product_id] += c.qty * s.qty

    states: dict[int, dict] = {}
    for p in snap.products:
        lots = _sorted_lots(lots_by_p.get(p.id, []))
        total_in = sum(l.qty_in for l in lots)
        total_out = direct_out.get(p.id, 0) + kit_out.get(p.id, 0)

        out_left = total_out
        est = 0
        valor = 0.0
        lot_saldos = []
        for lot in lots:
            consumed = min(lot.qty_in, max(out_left, 0))
            out_left -= consumed
            remaining = lot.qty_in - consumed
            est += remaining
            valor += remaining * lot.unit_cost
            lot_saldos.append(
                {
                    "lot_id": lot.id,
                    "lote_code": lot.lote_code,
                    "qty_in": lot.qty_in,
                    "unit_cost": lot.unit_cost,
                    "consumed": consumed,
                    "remaining": remaining,
                    "valor_saldo": remaining * lot.unit_cost,
                }
            )
        if est > 0:
            custo_medio = valor / est
        elif lots:
            custo_medio = lots[-1].unit_cost  # sem saldo: usa custo do lote mais recente
        else:
            custo_medio = 0.0

        states[p.id] = {
            "product_id": p.id,
            "sku": p.sku,
            "dropdown_name": p.dropdown_name,
            "estoque_atual": est,
            "valor_estoque": valor,
            "custo_medio_atual": custo_medio,
            "total_in": total_in,
            "total_out": total_out,
            # decomposição do estoque (ERP-001 "estoque explicado")
            "entradas": total_in,
            "vendas_diretas": direct_out.get(p.id, 0),
            "consumo_kits": kit_out.get(p.id, 0),
            "lots": lot_saldos,
        }
    return states


# ---------------------------------------------------------------------------
# Estado dos kits (custo atual, qtd de itens, estoque possível)
# ---------------------------------------------------------------------------
def kit_states(snap: Snapshot, pstates: dict[int, dict] | None = None) -> dict[int, dict]:
    if pstates is None:
        pstates = product_states(snap)
    result: dict[int, dict] = {}
    for k in snap.kits:
        custo = 0.0
        qtd_itens = 0
        estoque_possivel: int | None = None
        for c in k.components:
            ps = pstates.get(c.product_id)
            comp_cost = ps["custo_medio_atual"] if ps else 0.0
            custo += c.qty * comp_cost
            qtd_itens += c.qty
            if ps and c.qty > 0:
                possible = math.floor(ps["estoque_atual"] / c.qty)
                estoque_possivel = possible if estoque_possivel is None else min(estoque_possivel, possible)
        result[k.id] = {
            "kit_id": k.id,
            "sku": k.sku,
            "nome": k.nome,
            "custo_atual": custo,
            "qtd_itens": qtd_itens,
            "estoque_possivel": estoque_possivel or 0,
            "preco_referencia": k.preco_referencia,
        }
    return result


# ---------------------------------------------------------------------------
# Linhas de venda (com CMV/lucro/margem) — coração da aba Vendas
# ---------------------------------------------------------------------------
def sale_rows(snap: Snapshot) -> list[dict]:
    pstates = product_states(snap)
    kstates = kit_states(snap, pstates)
    lots_by_p: dict[int, list] = defaultdict(list)
    for lot in snap.lots:
        lots_by_p[lot.product_id].append(lot)
    lots_by_p = {pid: _sorted_lots(ls) for pid, ls in lots_by_p.items()}

    product_by_id = {p.id: p for p in snap.products}
    kit_by_id = {k.id: k for k in snap.kits}

    acc_direct: dict[int, int] = defaultdict(int)  # vendas diretas acumuladas por produto
    rows: list[dict] = []
    for s in _sorted_sales(snap.sales):
        receita = s.qty * s.preco_unitario
        taxa_shopee_rs = receita * s.taxa_shopee_pct
        taxa_fixa_rs = s.taxa_fixa  # aplicada uma vez por pedido
        taxa_extra_rs = receita * s.taxa_afiliado_pct
        receita_liquida = receita - taxa_shopee_rs - taxa_fixa_rs - taxa_extra_rs - s.outras_taxas

        if s.item_type == "product" and s.product_id is not None:
            o = acc_direct[s.product_id]
            p = o + s.qty
            lots = lots_by_p.get(s.product_id, [])
            cmv = _cost_of_first_n(lots, p) - _cost_of_first_n(lots, o)
            acc_direct[s.product_id] = p
            nome = product_by_id[s.product_id].dropdown_name if s.product_id in product_by_id else ""
            sku = product_by_id[s.product_id].sku if s.product_id in product_by_id else ""
        else:  # kit
            kit = kit_by_id.get(s.kit_id)
            unit_cost = kstates[kit.id]["custo_atual"] if kit else 0.0
            cmv = unit_cost * s.qty
            nome = kit.nome if kit else ""
            sku = kit.sku if kit else ""

        lucro = receita_liquida - cmv
        margem = (lucro / receita) if receita else 0.0
        rows.append(
            {
                "id": s.id,
                "data_venda": s.data_venda,
                "pedido": s.pedido,
                "item_type": s.item_type,
                "channel_id": s.channel_id,
                "channel": s.channel_name,
                "sku": sku,
                "nome": nome,
                "qty": s.qty,
                "preco_unitario": s.preco_unitario,
                "receita_bruta": receita,
                "taxa_shopee_pct": s.taxa_shopee_pct,
                "taxa_shopee_rs": taxa_shopee_rs,
                "taxa_fixa_rs": taxa_fixa_rs,
                "taxa_afiliado_pct": s.taxa_afiliado_pct,
                "taxa_extra_rs": taxa_extra_rs,
                "outras_taxas": s.outras_taxas,
                "receita_liquida": receita_liquida,
                "cmv": cmv,
                "lucro": lucro,
                "margem": margem,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Dashboard (aba Dashboard)
# ---------------------------------------------------------------------------
def dashboard(snap: Snapshot) -> dict:
    pstates = product_states(snap)
    kstates = kit_states(snap, pstates)
    rows = sale_rows(snap)

    receita_bruta = sum(r["receita_bruta"] for r in rows)
    taxas_totais = sum(
        r["taxa_shopee_rs"] + r["taxa_fixa_rs"] + r["taxa_extra_rs"] + r["outras_taxas"]
        for r in rows
    )
    receita_liquida = sum(r["receita_liquida"] for r in rows)
    cmv = sum(r["cmv"] for r in rows)
    lucro = sum(r["lucro"] for r in rows)
    ads_total = sum(a.valor for a in snap.ads)

    estoque_total = sum(ps["estoque_atual"] for ps in pstates.values())
    valor_estoque = sum(ps["valor_estoque"] for ps in pstates.values())

    return {
        "estoque_total": estoque_total,
        "valor_estoque": valor_estoque,
        "receita_bruta": receita_bruta,
        "taxas_totais": taxas_totais,
        "receita_liquida": receita_liquida,
        "cmv": cmv,
        "lucro_antes_ads": lucro,
        "ads_total": ads_total,
        "lucro_apos_ads": lucro - ads_total,
        "produtos": [
            {
                "dropdown_name": ps["dropdown_name"],
                "estoque": ps["estoque_atual"],
                "valor_estoque": ps["valor_estoque"],
                "custo_medio": ps["custo_medio_atual"],
            }
            for ps in pstates.values()
        ],
        "kits": [
            {"nome": ks["nome"], "estoque_possivel": ks["estoque_possivel"]}
            for ks in kstates.values()
        ],
    }


# ---------------------------------------------------------------------------
# Balanço Diário (aba Balanco Diario) — DRE por dia com ROAS
# ---------------------------------------------------------------------------
def balanco_diario(snap: Snapshot, dt_from: date | None = None, dt_to: date | None = None) -> list[dict]:
    rows = sale_rows(snap)
    ads_by_date: dict[date, float] = defaultdict(float)
    for a in snap.ads:
        ads_by_date[a.data] += a.valor

    agg: dict[date, dict] = {}
    for r in rows:
        d = r["data_venda"]
        a = agg.setdefault(
            d,
            {
                "data": d,
                "qty": 0,
                "receita_bruta": 0.0,
                "taxa_shopee": 0.0,
                "taxa_fixa": 0.0,
                "taxa_afiliado": 0.0,
                "outras_taxas": 0.0,
                "receita_liquida": 0.0,
                "cmv": 0.0,
            },
        )
        a["qty"] += r["qty"]
        a["receita_bruta"] += r["receita_bruta"]
        a["taxa_shopee"] += r["taxa_shopee_rs"]
        a["taxa_fixa"] += r["taxa_fixa_rs"]
        a["taxa_afiliado"] += r["taxa_extra_rs"]
        a["outras_taxas"] += r["outras_taxas"]
        a["receita_liquida"] += r["receita_liquida"]
        a["cmv"] += r["cmv"]

    all_dates = set(agg) | set(ads_by_date)
    out = []
    for d in sorted(all_dates):
        if dt_from and d < dt_from:
            continue
        if dt_to and d > dt_to:
            continue
        a = agg.get(
            d,
            {
                "data": d,
                "qty": 0,
                "receita_bruta": 0.0,
                "taxa_shopee": 0.0,
                "taxa_fixa": 0.0,
                "taxa_afiliado": 0.0,
                "outras_taxas": 0.0,
                "receita_liquida": 0.0,
                "cmv": 0.0,
            },
        )
        ads = ads_by_date.get(d, 0.0)
        lucro_apos = a["receita_liquida"] - a["cmv"] - ads
        receita = a["receita_bruta"]
        out.append(
            {
                **a,
                "ads": ads,
                "lucro_apos_ads": lucro_apos,
                "margem_apos_ads": (lucro_apos / receita) if receita else 0.0,
                "roas": (receita / ads) if ads else 0.0,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Estoque Diário (aba Estoque Diario) — peças que saíram no dia (kits explodidos)
# ---------------------------------------------------------------------------
def _kit_consumption(snap: Snapshot, product_id: int, predicate) -> int:
    kit_by_id = {k.id: k for k in snap.kits}
    total = 0
    for s in snap.sales:
        if s.item_type != "kit" or s.kit_id is None or not predicate(s.data_venda):
            continue
        kit = kit_by_id.get(s.kit_id)
        if not kit:
            continue
        for c in kit.components:
            if c.product_id == product_id:
                total += c.qty * s.qty
    return total


def _direct_sales(snap: Snapshot, product_id: int, predicate) -> int:
    return sum(
        s.qty
        for s in snap.sales
        if s.item_type == "product" and s.product_id == product_id and predicate(s.data_venda)
    )


def estoque_diario(snap: Snapshot, dia: date) -> dict:
    linhas = []
    total_saidas = 0
    total_fim = 0
    for p in snap.products:
        entradas_ate = sum(
            l.qty_in for l in snap.lots if l.product_id == p.id and l.data_entrada <= dia
        )
        direto_antes = _direct_sales(snap, p.id, lambda d: d < dia)
        kits_antes = _kit_consumption(snap, p.id, lambda d: d < dia)
        inicio = entradas_ate - direto_antes - kits_antes

        venda_unit = _direct_sales(snap, p.id, lambda d: d == dia)
        saida_kits = _kit_consumption(snap, p.id, lambda d: d == dia)
        saidas = venda_unit + saida_kits
        fim = inicio - saidas
        total_saidas += saidas
        total_fim += fim
        linhas.append(
            {
                "sku": p.sku,
                "dropdown_name": p.dropdown_name,
                "estoque_inicio": inicio,
                "venda_unitaria": venda_unit,
                "saida_via_kits": saida_kits,
                "total_saidas": saidas,
                "estoque_fim": fim,
                "pct_estoque_inicial": (saidas / inicio) if inicio else 0.0,
            }
        )
    return {
        "data": dia,
        "pecas_que_sairam": total_saidas,
        "estoque_final": total_fim,
        "linhas": linhas,
    }


def estoque_diario_range(
    snap: Snapshot, dt_from: date | None = None, dt_to: date | None = None
) -> list[dict]:
    """Resumo do estoque por dia (todos os dias com movimento de venda), no período."""
    dias = sorted({s.data_venda for s in snap.sales})
    out = []
    for d in dias:
        if dt_from and d < dt_from:
            continue
        if dt_to and d > dt_to:
            continue
        rep = estoque_diario(snap, d)
        out.append(
            {
                "data": d,
                "pecas_que_sairam": rep["pecas_que_sairam"],
                "estoque_final": rep["estoque_final"],
            }
        )
    return out
