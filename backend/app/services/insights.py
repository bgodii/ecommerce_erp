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


def _ads_na_janela(stats: list[AdStat], dt_from: date, dt_to: date) -> dict:
    """Soma spend/GMV dos relatórios que cobrem a janela, rateando por dias em comum.

    `exato` indica se a janela casa com o período dos relatórios (sem rateio) — só nesse
    caso o número é confiável para comparar períodos.
    """
    by_type: dict[str, list[AdStat]] = defaultdict(list)
    for s in stats:
        if s.period_start <= dt_to and s.period_end >= dt_from:
            by_type[s.report_type].append(s)
    chosen: list[AdStat] = []
    for t in _ADS_PRIORITY:
        if by_type.get(t):
            chosen = by_type[t]
            break

    spend = gmv = 0.0
    exato = bool(chosen)
    relatorios = set()
    for s in chosen:
        dias_rel = (s.period_end - s.period_start).days + 1
        ini, fim = max(s.period_start, dt_from), min(s.period_end, dt_to)
        dias_comuns = max((fim - ini).days + 1, 0)
        fator = (dias_comuns / dias_rel) if dias_rel else 0.0
        if fator < 1:
            exato = False
        spend += s.spend * fator
        gmv += s.gmv * fator
        relatorios.add((s.period_start, s.period_end))
    return {"spend": spend, "gmv": gmv, "exato": exato, "relatorios": relatorios}


async def roas_marginal(
    session: AsyncSession, org_id: int, dias: int = 7, ref: date | None = None
) -> dict:
    """Compara os últimos `dias` com os `dias` anteriores e calcula o ROAS MARGINAL.

    ROAS marginal = (GMV novo − GMV velho) ÷ (investimento novo − investimento velho).
    É ele — e não o ROAS médio — que diz se vale a pena continuar escalando: o lucro
    total é máximo quando o marginal encosta no ROAS even.
    """
    ref = ref or date.today()
    atual_de, atual_ate = ref - timedelta(days=dias - 1), ref
    ant_de, ant_ate = atual_de - timedelta(days=dias), atual_de - timedelta(days=1)

    stats = (
        await session.execute(select(AdStat).where(AdStat.organization_id == org_id))
    ).scalars().all()
    atual = _ads_na_janela(stats, atual_de, atual_ate)
    anterior = _ads_na_janela(stats, ant_de, ant_ate)

    # margem/ROAS even do período atual (mesma base da visão geral)
    vg = await build_overview(session, org_id, atual_de, atual_ate)
    margem = vg["ads"]["margem_base"]
    even = (1 / margem) if margem > 0 else None

    d_spend = atual["spend"] - anterior["spend"]
    d_gmv = atual["gmv"] - anterior["gmv"]
    marginal = (d_gmv / d_spend) if d_spend > 0 else None

    # os dois períodos vieram do MESMO relatório? então tudo foi rateado e a comparação
    # é artificial (proporcional aos dias) — não dá para concluir nada.
    mesmo_relatorio = bool(
        atual["relatorios"] and atual["relatorios"] == anterior["relatorios"]
    )
    confiavel = bool(marginal and not mesmo_relatorio and atual["exato"] and anterior["exato"])

    if mesmo_relatorio:
        veredito, recomendacao = "sem_dados", (
            "Os dois períodos vêm do mesmo relatório agregado, então a comparação não é real. "
            "Exporte os relatórios de ADS por semana na Shopee para medir o ROAS marginal."
        )
    elif d_spend <= 0:
        veredito, recomendacao = "sem_aumento", (
            "Você não aumentou o investimento no período — não há marginal para avaliar. "
            "Suba 20–30% do orçamento e compare de novo daqui a 7 dias."
        )
    elif even is None:
        veredito, recomendacao = "sem_margem", "Cadastre os custos dos produtos para calcular a margem."
    elif marginal >= even * 1.3:
        veredito, recomendacao = "escalar", (
            f"O dinheiro extra rendeu {marginal:.2f}× — bem acima do even ({even:.2f}×). "
            "Pode subir mais 20–30% e medir de novo."
        )
    elif marginal >= even:
        veredito, recomendacao = "no_limite", (
            f"O extra rendeu {marginal:.2f}×, pouco acima do even ({even:.2f}×). "
            "Você está perto do ponto de lucro máximo — suba pouco (10%) ou segure."
        )
    else:
        veredito, recomendacao = "voltar", (
            f"O dinheiro extra rendeu só {marginal:.2f}×, abaixo do even ({even:.2f}×). "
            "Esse aumento destruiu lucro — volte ao orçamento anterior."
        )

    def _bloco(p: dict, de: date, ate: date) -> dict:
        return {
            "de": str(de),
            "ate": str(ate),
            "spend": p["spend"],
            "gmv": p["gmv"],
            "roas": (p["gmv"] / p["spend"]) if p["spend"] else 0.0,
            "lucro_estimado": p["gmv"] * margem - p["spend"] if margem > 0 else None,
        }

    return {
        "dias": dias,
        "atual": _bloco(atual, atual_de, atual_ate),
        "anterior": _bloco(anterior, ant_de, ant_ate),
        "delta_spend": d_spend,
        "delta_gmv": d_gmv,
        "roas_marginal": marginal,
        "roas_even": even,
        "margem": margem,
        "confiavel": confiavel,
        "veredito": veredito,
        "recomendacao": recomendacao,
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
    ads_exato = True
    ads_cobertura: list[dict] = []
    if stats:
        by_type = defaultdict(list)
        for s in stats:
            by_type[s.report_type].append(s)
        for t in _ADS_PRIORITY:
            if by_type.get(t):
                chosen = by_type[t]
                break
        ads_fonte = "importado"

        # Os relatórios de ADS vêm AGREGADOS por período (a Shopee não exporta por dia).
        # Quando a janela pedida não cobre o relatório inteiro, rateamos proporcional aos
        # dias em comum — é uma ESTIMATIVA, sinalizada com `exato: false`.
        for s in chosen:
            dias_rel = (s.period_end - s.period_start).days + 1
            ini = max(s.period_start, dt_from)
            fim = min(s.period_end, dt_to)
            dias_comuns = max((fim - ini).days + 1, 0)
            fator = (dias_comuns / dias_rel) if dias_rel else 0.0
            s._fator = fator  # usado adiante nas métricas por anúncio
            if fator < 1:
                ads_exato = False
            ads_spend += s.spend * fator
            ads_gmv += s.gmv * fator
        ads_cobertura = [
            {"de": str(p[0]), "ate": str(p[1])}
            for p in sorted({(s.period_start, s.period_end) for s in chosen})
        ]
    else:
        ads_spend = sum(a.valor for a in snap.ads if dt_from <= a.data <= dt_to)
    ads = {
        "spend": ads_spend,
        "gmv_anunciado": ads_gmv,
        "pct_faturamento": (ads_spend / cur["receita"]) if cur["receita"] else 0.0,
        "roas": (ads_gmv / ads_spend) if ads_spend and ads_gmv else 0.0,
        # ROAS even (break-even): abaixo disso o anúncio consome mais que a margem gera
        "roas_even": (1.0 / cur["margem"]) if cur["margem"] > 0 else None,
        "margem_base": cur["margem"],
        "fonte": ads_fonte,
        # exato=False -> houve rateio por dias (relatório cobre período maior que o filtro)
        "exato": ads_exato,
        "cobertura": ads_cobertura,
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

    # Margem REALIZADA por produto/kit no período — usada quando o anúncio está
    # vinculado a um item (mais preciso que a margem média da loja).
    sku_to_pid = {p.sku: p.id for p in snap.products}
    sku_to_kid = {k.sku: k.id for k in snap.kits}
    margem_produto: dict[int, float] = {}
    margem_kit: dict[int, float] = {}
    for it in items:
        if it["receita"] <= 0:
            continue
        m = it["lucro"] / it["receita"]
        if it["tipo"] == "product" and it["sku"] in sku_to_pid:
            margem_produto[sku_to_pid[it["sku"]]] = m
        elif it["tipo"] == "kit" and it["sku"] in sku_to_kid:
            margem_kit[sku_to_kid[it["sku"]]] = m

    ads_produtos = []
    for s in chosen:
        # rateio por dias em comum (ver bloco de ADS acima)
        fator = getattr(s, "_fator", 1.0)
        if fator <= 0:
            continue
        spend = s.spend * fator
        gmv = s.gmv * fator
        impressions = round(s.impressions * fator)
        clicks = round(s.clicks * fator)
        conversions = s.conversions * fator
        items_sold = s.items_sold * fator

        margem_ref = margem_loja
        fonte_margem = "loja"
        l = listings.get(s.listing_ref)
        if l is not None:
            if l.product_id and l.product_id in margem_produto:
                margem_ref, fonte_margem = margem_produto[l.product_id], "produto"
            elif l.kit_id and l.kit_id in margem_kit:
                margem_ref, fonte_margem = margem_kit[l.kit_id], "kit"
        roas_eq = (1.0 / margem_ref) if margem_ref > 0 else None
        if spend <= 0:
            continue
        if items_sold == 0:
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
        # --- funil de cliques -------------------------------------------------
        # CPC       = quanto custa cada clique
        # cliq/venda= quantos cliques você paga até sair uma venda
        # CPC máx   = teto que o clique pode custar sem dar prejuízo:
        #             (ticket × margem) ÷ cliques_por_venda
        cpc = (spend / clicks) if clicks else 0.0
        ctr = (clicks / impressions) if impressions else 0.0
        conv = (conversions / clicks) if clicks else 0.0
        cliques_por_venda = (clicks / conversions) if conversions else None
        custo_por_venda = (spend / conversions) if conversions else None
        ticket = (gmv / conversions) if conversions else None
        margem_por_venda = (ticket * margem_ref) if (ticket and margem_ref > 0) else None
        cpc_maximo = (
            margem_por_venda / cliques_por_venda
            if (margem_por_venda and cliques_por_venda)
            else None
        )
        cliques_maximos = (margem_por_venda / cpc) if (margem_por_venda and cpc) else None
        conversao_minima = (
            (cpc / margem_por_venda) if (margem_por_venda and cpc) else None
        )

        # faixa da taxa de conversão (referência de marketplace)
        if not clicks:
            faixa_conv = "sem_dados"
        elif conv >= 0.02:
            faixa_conv = "otima"
        elif conv >= 0.01:
            faixa_conv = "boa"
        elif conv >= 0.005:
            faixa_conv = "atencao"
        else:
            faixa_conv = "ruim"

        ads_produtos.append(
            {
                "listing": s.listing_ref,
                "nome": (l.name if l else s.ad_name) or s.ad_name,
                "spend": spend,
                "gmv": gmv,
                "itens_vendidos": round(items_sold),
                "roas": s.roas,
                "roas_even": roas_eq,
                "roas_equilibrio": roas_eq,  # alias (compat)
                "lucro_estimado": gmv * margem_ref - spend if margem_ref > 0 else None,
                "fonte_margem": fonte_margem,
                "margem_usada": margem_ref,
                "vinculado_a": (
                    (l.product_id and "produto") or (l.kit_id and "kit") or None
                ) if l else None,
                "veredito": veredito,
                # funil
                "impressoes": impressions,
                "cliques": clicks,
                "conversoes": round(conversions),
                "ctr": ctr,
                "cpc": cpc,
                "taxa_conversao": conv,
                "faixa_conversao": faixa_conv,
                "cliques_por_venda": cliques_por_venda,
                "custo_por_venda": custo_por_venda,
                "ticket_medio": ticket,
                "margem_por_venda": margem_por_venda,
                "cpc_maximo": cpc_maximo,
                "cliques_maximos_por_venda": cliques_maximos,
                "conversao_minima": conversao_minima,
                "cpc_saudavel": (cpc <= cpc_maximo) if cpc_maximo else None,
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

    # anúncio pagando caro demais pelo clique (gasta acima do teto de equilíbrio)
    caros = [
        p for p in ads_produtos
        if p["cpc_maximo"] and p["cpc"] > p["cpc_maximo"] and p["spend"] >= 5
    ]
    if caros:
        pior = max(caros, key=lambda p: p["spend"])
        insights.append(
            {
                "tipo": "alerta",
                "icone": "🖱️",
                "titulo": f"Clique caro demais: {pior['nome'][:40]}",
                "texto": (
                    f"Você paga R$ {pior['cpc']:.2f} por clique, mas o teto pra não ter prejuízo é "
                    f"R$ {pior['cpc_maximo']:.2f}. São {pior['cliques_por_venda']:.0f} cliques por venda "
                    f"quando o máximo seria {pior['cliques_maximos_por_venda']:.0f}."
                ),
            }
        )

    # anúncio queimando cliques sem converter
    sem_conversao = [
        p for p in ads_produtos if p["cliques"] >= 50 and p["conversoes"] == 0 and p["spend"] > 0
    ]
    if sem_conversao:
        pior = max(sem_conversao, key=lambda p: p["cliques"])
        insights.append(
            {
                "tipo": "alerta",
                "icone": "🕳️",
                "titulo": f"{pior['cliques']} cliques e nenhuma venda: {pior['nome'][:36]}",
                "texto": "O anúncio atrai clique mas não converte. Revise preço, fotos, título e avaliações — ou pause.",
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
