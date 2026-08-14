"""Visão geral analítica da loja (home do eLucroCerto).

Agrega, para uma janela de datas:
- KPIs com delta vs período anterior de mesmo tamanho
- Caixa por status dos pedidos importados (recebido × a receber × perdido)
- Divisão de custos (CMV, taxas do canal, ads, descontos → o que sobra)
- Séries (diária na janela; mensal all-time para "melhor mês")
- Cards de insight determinísticos ("O que fazer agora")
- Top produtos (mais vendem / mais lucram) e vereditos de ADS por anúncio

Fonte de ads: se houver relatórios importados (ad_stats) intersectando a janela,
usa-os (report 'geral' > 'adgroup' > 'keyword' > 'gmvmax' para não somar duplicado);
senão usa os lançamentos manuais (ad_spends).
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ad_stat import AdStat
from app.models.listing import Listing
from app.models.order import Order
from app.services import engine
from app.services.loader import load_snapshot

_ADS_PRIORITY = ("geral", "adgroup", "keyword", "gmvmax")


def _pct_delta(cur: float, prev: float) -> float | None:
    if prev == 0:
        return None
    return (cur - prev) / prev


def _sum_rows(rows: list[dict]) -> dict:
    receita = sum(r["receita_bruta"] for r in rows)
    liquida = sum(r["receita_liquida"] for r in rows)
    cmv = sum(r["cmv"] for r in rows)
    taxas = sum(
        r["taxa_shopee_rs"] + r["taxa_fixa_rs"] + r["taxa_extra_rs"] + r["outras_taxas"]
        for r in rows
    )
    lucro = liquida - cmv
    return {
        "receita": receita,
        "liquida": liquida,
        "cmv": cmv,
        "taxas": taxas,
        "lucro": lucro,
        "margem": (lucro / receita) if receita else 0.0,
        "unidades": sum(r["qty"] for r in rows),
        "vendas": len(rows),
    }


async def build_overview(
    session: AsyncSession, org_id: int, dt_from: date, dt_to: date
) -> dict:
    snap = await load_snapshot(session, org_id)
    all_rows = engine.sale_rows(snap)

    in_window = [r for r in all_rows if dt_from <= r["data_venda"] <= dt_to]
    win_len = (dt_to - dt_from).days + 1
    prev_from, prev_to = dt_from - timedelta(days=win_len), dt_from - timedelta(days=1)
    in_prev = [r for r in all_rows if prev_from <= r["data_venda"] <= prev_to]

    cur = _sum_rows(in_window)
    prev = _sum_rows(in_prev)

    # ---------------- caixa (pedidos importados, por janela de criação) ----------
    orders = (
        await session.execute(select(Order).where(Order.organization_id == org_id))
    ).scalars().all()

    def _od(o) -> date | None:
        return o.created_at_channel.date() if o.created_at_channel else None

    ow = [o for o in orders if _od(o) and dt_from <= _od(o) <= dt_to]
    recebido = sum(o.valor_liquido for o in ow if o.status == "concluido")
    a_receber = sum(o.valor_liquido for o in ow if o.status in ("a_enviar", "enviado", "entregue"))
    aguardando = sum(o.valor_bruto for o in ow if o.status == "nao_pago")
    cancelados = [o for o in ow if o.status == "cancelado"]
    caixa = {
        "recebido": recebido,
        "a_receber": a_receber,
        "aguardando_pagamento": aguardando,
        "pedidos": len(ow),
        "pedidos_cancelados": len(cancelados),
        "taxa_cancelamento": (len(cancelados) / len(ow)) if ow else 0.0,
    }

    # ---------------- ads (importado > manual) -----------------------------------
    stats = (
        await session.execute(
            select(AdStat).where(
                AdStat.organization_id == org_id,
                AdStat.period_start <= dt_to,
                AdStat.period_end >= dt_from,
            )
        )
    ).scalars().all()
    ads_fonte = "manual"
    ads_spend = ads_gmv = 0.0
    chosen: list[AdStat] = []
    if stats:
        by_type = defaultdict(list)
        for s in stats:
            by_type[s.report_type].append(s)
        for t in _ADS_PRIORITY:
            if by_type.get(t):
                chosen = by_type[t]
                break
        ads_fonte = "importado"
        ads_spend = sum(s.spend for s in chosen)
        ads_gmv = sum(s.gmv for s in chosen)
    else:
        ads_spend = sum(a.valor for a in snap.ads if dt_from <= a.data <= dt_to)
    ads = {
        "spend": ads_spend,
        "gmv_anunciado": ads_gmv,
        "pct_faturamento": (ads_spend / cur["receita"]) if cur["receita"] else 0.0,
        "roas": (ads_gmv / ads_spend) if ads_spend and ads_gmv else 0.0,
        "fonte": ads_fonte,
    }

    lucro_apos_ads = cur["lucro"] - ads_spend

    # ---------------- séries -------------------------------------------------------
    by_day: dict[date, dict] = {}
    for r in in_window:
        d = by_day.setdefault(r["data_venda"], {"data": str(r["data_venda"]), "receita": 0.0, "lucro": 0.0, "unidades": 0})
        d["receita"] += r["receita_bruta"]
        d["lucro"] += r["lucro"]
        d["unidades"] += r["qty"]
    series_diaria = [by_day[k] for k in sorted(by_day)]

    by_month: dict[str, dict] = {}
    for r in all_rows:
        m = r["data_venda"].strftime("%Y-%m")
        d = by_month.setdefault(m, {"mes": m, "receita": 0.0, "lucro": 0.0})
        d["receita"] += r["receita_bruta"]
        d["lucro"] += r["lucro"]
    meses = [by_month[k] for k in sorted(by_month)]

    # ---------------- top produtos -------------------------------------------------
    by_item: dict[tuple, dict] = {}
    for r in in_window:
        key = (r["item_type"], r["sku"])
        d = by_item.setdefault(
            key, {"sku": r["sku"], "nome": r["nome"], "tipo": r["item_type"],
                  "unidades": 0, "receita": 0.0, "lucro": 0.0}
        )
        d["unidades"] += r["qty"]
        d["receita"] += r["receita_bruta"]
        d["lucro"] += r["lucro"]
    items = list(by_item.values())
    for it in items:
        it["margem"] = (it["lucro"] / it["receita"]) if it["receita"] else 0.0
    top_vendas = sorted(items, key=lambda x: -x["unidades"])[:5]
    top_lucro = sorted(items, key=lambda x: -x["lucro"])[:5]

    # ---------------- vereditos de ADS por anúncio --------------------------------
    listings = {
        l.listing_id: l
        for l in (
            await session.execute(select(Listing).where(Listing.organization_id == org_id))
        ).scalars()
    }
    margem_loja = cur["margem"]
    ads_produtos = []
    for s in chosen:
        margem_ref = margem_loja
        fonte_margem = "loja"
        l = listings.get(s.listing_ref)
        roas_eq = (1.0 / margem_ref) if margem_ref > 0 else None
        if s.spend <= 0:
            continue
        if s.items_sold == 0:
            veredito = "pausar"
        elif roas_eq is None:
            veredito = "ok" if s.roas >= 4 else ("atencao" if s.roas >= 2 else "pausar")
        elif s.roas >= 1.5 * roas_eq:
            veredito = "escalar"
        elif s.roas >= roas_eq:
            veredito = "ok"
        elif s.roas >= 0.6 * roas_eq:
            veredito = "atencao"
        else:
            veredito = "pausar"
        ads_produtos.append(
            {
                "listing": s.listing_ref,
                "nome": (l.name if l else s.ad_name) or s.ad_name,
                "spend": s.spend,
                "gmv": s.gmv,
                "itens_vendidos": s.items_sold,
                "roas": s.roas,
                "roas_equilibrio": roas_eq,
                "fonte_margem": fonte_margem,
                "veredito": veredito,
            }
        )
    ads_produtos.sort(key=lambda x: -x["spend"])

    # ---------------- insights ("O que fazer agora") ------------------------------
    insights: list[dict] = []

    if len(meses) >= 1:
        best = max(meses, key=lambda m: m["lucro"])
        if best["lucro"] > 0:
            nome_mes = date.fromisoformat(best["mes"] + "-01").strftime("%B de %Y").capitalize()
            insights.append(
                {
                    "tipo": "sucesso",
                    "icone": "🏆",
                    "titulo": f"Seu melhor mês foi {nome_mes}",
                    "texto": f"Lucro real de R$ {best['lucro']:,.2f} nesse mês.".replace(",", "@").replace(".", ",").replace("@", "."),
                }
            )

    if prev["receita"] > 0 and cur["margem"] is not None:
        diff_pts = (cur["margem"] - prev["margem"]) * 100
        if diff_pts <= -1:
            insights.append(
                {
                    "tipo": "alerta",
                    "icone": "📉",
                    "titulo": f"Sua margem caiu {abs(diff_pts):.1f} pontos",
                    "texto": f"De {prev['margem']*100:.1f}% para {cur['margem']*100:.1f}% do faturamento vs o período anterior.",
                }
            )
        elif diff_pts >= 1:
            insights.append(
                {
                    "tipo": "sucesso",
                    "icone": "📈",
                    "titulo": f"Sua margem subiu {diff_pts:.1f} pontos",
                    "texto": f"De {prev['margem']*100:.1f}% para {cur['margem']*100:.1f}% do faturamento.",
                }
            )

    if cur["receita"] > 0 and ads_spend > 0:
        pct = ads_spend / cur["receita"] * 100
        if pct <= 12:
            insights.append(
                {
                    "tipo": "info",
                    "icone": "🔔",
                    "titulo": f"Você investe {pct:.1f}% do faturamento em ADS",
                    "texto": "Patamar saudável. Acompanhe o ROAS na Análise de ADS.",
                }
            )
        elif pct <= 25:
            insights.append(
                {
                    "tipo": "alerta",
                    "icone": "⚠️",
                    "titulo": f"ADS consome {pct:.1f}% do faturamento",
                    "texto": "Atenção: acima de ~12% o lucro fica sensível ao ROAS. Revise os anúncios com veredito 'atenção'.",
                }
            )
        else:
            insights.append(
                {
                    "tipo": "alerta",
                    "icone": "🚨",
                    "titulo": f"ADS muito alto: {pct:.1f}% do faturamento",
                    "texto": "Considere pausar anúncios com ROAS abaixo do equilíbrio.",
                }
            )

    if caixa["pedidos"] >= 10 and caixa["taxa_cancelamento"] > 0.12:
        insights.append(
            {
                "tipo": "alerta",
                "icone": "❌",
                "titulo": f"Cancelamento alto: {caixa['taxa_cancelamento']*100:.0f}% dos pedidos",
                "texto": f"{caixa['pedidos_cancelados']} pedidos cancelados no período. Verifique estoque, prazo de envio e descrição dos anúncios.",
            }
        )

    # reposição: cobertura de estoque < 7 dias pelo ritmo do período
    pstates = engine.product_states(snap)
    vendas_por_produto: dict[int, int] = defaultdict(int)
    sku_to_pid = {p.sku: p.id for p in snap.products}
    for it in items:
        if it["tipo"] == "product" and it["sku"] in sku_to_pid:
            vendas_por_produto[sku_to_pid[it["sku"]]] += it["unidades"]
        elif it["tipo"] == "kit":
            kit = next((k for k in snap.kits if k.sku == it["sku"]), None)
            if kit:
                for c in kit.components:
                    vendas_por_produto[c.product_id] += c.qty * it["unidades"]
    repor = []
    for pid, sold in vendas_por_produto.items():
        ritmo = sold / max(win_len, 1)
        estoque = pstates.get(pid, {}).get("estoque_atual", 0)
        if ritmo > 0 and estoque / ritmo < 7:
            repor.append((pstates[pid]["dropdown_name"], estoque, ritmo))
    if repor:
        repor.sort(key=lambda x: x[1] / x[2])
        nomes = ", ".join(n for n, _, _ in repor[:3])
        insights.append(
            {
                "tipo": "alerta",
                "icone": "📦",
                "titulo": f"Estoque acabando: {nomes}",
                "texto": "Menos de 7 dias de cobertura no ritmo atual de vendas. Programe a reposição.",
            }
        )

    if top_lucro and top_lucro[0]["lucro"] > 0:
        t = top_lucro[0]
        insights.append(
            {
                "tipo": "sucesso",
                "icone": "⭐",
                "titulo": f"Campeão de lucro: {t['nome']}",
                "texto": f"R$ {t['lucro']:,.2f} de lucro ({t['margem']*100:.0f}% de margem) no período.".replace(",", "@").replace(".", ",").replace("@", "."),
            }
        )

    return {
        "periodo": {"de": str(dt_from), "ate": str(dt_to), "dias": win_len},
        "kpis": {
            "faturamento": cur["receita"],
            "delta_faturamento": _pct_delta(cur["receita"], prev["receita"]),
            "pedidos": caixa["pedidos"] or cur["vendas"],
            "unidades": cur["unidades"],
            "ticket_medio": (cur["receita"] / cur["vendas"]) if cur["vendas"] else 0.0,
            "lucro": cur["lucro"],
            "delta_lucro": _pct_delta(cur["lucro"], prev["lucro"]),
            "lucro_apos_ads": lucro_apos_ads,
            "margem": cur["margem"],
            "margem_anterior": prev["margem"] if prev["receita"] else None,
        },
        "caixa": caixa,
        "custos": {
            "receita": cur["receita"],
            "cmv": cur["cmv"],
            "taxas_canal": cur["taxas"],
            "ads": ads_spend,
            "lucro": lucro_apos_ads,
            "fonte_ads": ads_fonte,
        },
        "ads": ads,
        "series_diaria": series_diaria,
        "meses": meses[-12:],
        "insights": insights[:6],
        "top_vendas": top_vendas,
        "top_lucro": top_lucro,
        "ads_produtos": ads_produtos,
    }
