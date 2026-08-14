"""Import dos exports do marketplace (pedidos .xlsx e relatórios de ADS .csv).

Idempotente: reimportar atualiza (pedidos por order_sn — status evolui entre exports;
ads por escopo+período). Nunca duplica, nunca apaga dados de outros períodos.
"""
from collections import Counter

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import func, select

from app.core.deps import CurrentUser, SessionDep
from app.models.ad_stat import AdStat
from app.models.channel import Channel
from app.models.listing import Listing
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.services.shopee_import import parse_ads_csv, parse_orders_xlsx
from app.services.sku_resolve import Resolution, SkuResolver, auto_product_identity

router = APIRouter(prefix="/imports", tags=["imports"])


async def _default_channel(session, org_id: int) -> Channel:
    """Canal alvo do import Shopee: o canal 'Shopee' da loja (cria se não existir)."""
    ch = (
        await session.execute(
            select(Channel).where(
                Channel.organization_id == org_id, func.lower(Channel.name) == "shopee"
            )
        )
    ).scalars().first()
    if ch is None:
        ch = Channel(organization_id=org_id, name="Shopee", taxa_pct=0.20, taxa_fixa=4.0)
        session.add(ch)
        await session.flush()
    return ch


@router.post("/orders")
async def import_orders(
    user: CurrentUser,
    session: SessionDep,
    file: UploadFile = File(...),
    dry_run: bool = False,
    auto_criar: bool = True,
):
    """Importa o Order.all*.xlsx. Com auto_criar (padrão), produtos que não existem são
    criados automaticamente a partir da planilha — agregando tamanhos por cor/modelo —
    e ficam prontos para receber estoque/custo em Entradas."""
    org_id = user.organization_id
    content = await file.read()
    try:
        parsed = parse_orders_xlsx(content, file.filename or "")
    except Exception:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Arquivo inválido — envie o Order.all*.xlsx da Shopee")
    if not parsed["orders"] and parsed["errors"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, parsed["errors"][0]["erro"])

    channel = await _default_channel(session, org_id)
    resolver = await SkuResolver.load(session, org_id, channel.id)

    existing = {
        o.order_sn: o
        for o in (
            await session.execute(
                select(Order).where(
                    Order.organization_id == org_id, Order.channel_id == channel.id
                )
            )
        ).scalars()
    }

    novos = atualizados = itens_pendentes = 0
    produtos_criados: dict[str, str] = {}  # sku -> nome (para o resumo)
    preview = []
    for od in parsed["orders"]:
        items_out = []
        pend_this = 0
        for item in od["items"]:
            res = resolver.resolve(item, org_id, channel.id)
            if res.status == "pendente" and auto_criar:
                sku, nome = auto_product_identity(item)
                prod = resolver.find_product_by_sku(sku)
                if prod is None and not dry_run:
                    prod = Product(
                        organization_id=org_id, sku=sku, nome=nome, dropdown_name=nome
                    )
                    session.add(prod)
                    await session.flush()  # id para o mapping
                if prod is not None:
                    resolver.register_product(prod, item, org_id, channel.id)
                    res = Resolution(product_id=prod.id, kit_id=None, status="auto")
                elif dry_run:
                    res = Resolution(status="auto")  # simula a criação no preview
                produtos_criados.setdefault(sku, nome)
            if res.status == "pendente":
                pend_this += 1
            items_out.append((item, res))
        itens_pendentes += pend_this

        is_new = od["order_sn"] not in existing
        novos += is_new
        atualizados += not is_new
        if len(preview) < 100:
            preview.append(
                {
                    "order_sn": od["order_sn"],
                    "status": od["status"],
                    "valor_bruto": od["valor_bruto"],
                    "itens": len(od["items"]),
                    "pendencias": pend_this,
                    "acao": "novo" if is_new else "atualizar",
                }
            )

        if dry_run:
            continue

        row = existing.get(od["order_sn"])
        if row is None:
            row = Order(organization_id=org_id, channel_id=channel.id, order_sn=od["order_sn"])
            session.add(row)
            existing[od["order_sn"]] = row
        for f in (
            "status_raw",
            "status",
            "created_at_channel",
            "paid_at",
            "valor_bruto",
            "desconto_vendedor",
            "taxa_comissao",
            "taxa_servico",
            "taxa_transacao",
            "valor_liquido",
            "source_file",
        ):
            setattr(row, f, od[f])
        row.items = [
            OrderItem(
                sku_main=item["sku_main"],
                sku_var=item["sku_var"],
                product_name=item["product_name"],
                variation_name=item["variation_name"],
                qty=item["qty"],
                unit_price=item["unit_price"],
                subtotal=item["subtotal"],
                product_id=res.product_id,
                kit_id=res.kit_id,
                mapping_status=res.status,
            )
            for item, res in items_out
        ]

    if not dry_run:
        session.add_all(resolver.new_mappings)
        await session.commit()

    status_count = Counter(o["status"] for o in parsed["orders"])
    return {
        "dry_run": dry_run,
        "summary": {
            "pedidos": len(parsed["orders"]),
            "novos": novos,
            "atualizados": atualizados,
            "produtos_novos": len(produtos_criados),
            "itens_pendentes_vinculo": itens_pendentes,
            "por_status": dict(status_count),
            "erros": len(parsed["errors"]),
        },
        "produtos_criados": [
            {"sku": sku, "nome": nome} for sku, nome in list(produtos_criados.items())[:50]
        ],
        "errors": parsed["errors"][:50],
        "preview": preview,
    }


@router.post("/ads")
async def import_ads(
    user: CurrentUser,
    session: SessionDep,
    file: UploadFile = File(...),
    dry_run: bool = False,
):
    org_id = user.organization_id
    content = await file.read()
    parsed = parse_ads_csv(content, file.filename or "")
    if not parsed["rows"] and parsed["errors"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, parsed["errors"][0]["erro"])

    channel = await _default_channel(session, org_id)

    # listings conhecidos (upsert por listing_id)
    listings = {
        l.listing_id: l
        for l in (
            await session.execute(
                select(Listing).where(
                    Listing.organization_id == org_id, Listing.channel_id == channel.id
                )
            )
        ).scalars()
    }
    existing_stats = {
        (s.report_type, s.listing_ref, s.detail_key, s.period_start, s.period_end): s
        for s in (
            await session.execute(
                select(AdStat).where(
                    AdStat.organization_id == org_id, AdStat.channel_id == channel.id
                )
            )
        ).scalars()
    }

    # O mesmo listing pode ter vários anúncios no relatório (ex.: um encerrado e um em
    # andamento). Agregamos por chave somando as métricas para não perder investimento.
    agg: dict[tuple, dict] = {}
    for r in parsed["rows"]:
        k = (r["listing_ref"], r["detail_key"])
        a = agg.get(k)
        if a is None:
            agg[k] = dict(r)
        else:
            for f in ("impressions", "clicks", "conversions", "items_sold", "gmv", "spend"):
                a[f] += r[f]
            a["roas"] = (a["gmv"] / a["spend"]) if a["spend"] else 0.0
            a["acos"] = (a["spend"] / a["gmv"]) if a["gmv"] else 0.0
    rows_agg = list(agg.values())

    novos = atualizados = 0
    for r in rows_agg:
        if not dry_run and r["listing_ref"] != "-" and r["listing_ref"] not in listings:
            l = Listing(
                organization_id=org_id,
                channel_id=channel.id,
                listing_id=r["listing_ref"],
                name=r["ad_name"][:300],
            )
            session.add(l)
            listings[r["listing_ref"]] = l

        key = (
            parsed["report_type"],
            r["listing_ref"],
            r["detail_key"],
            parsed["period_start"],
            parsed["period_end"],
        )
        row = existing_stats.get(key)
        if row is None:
            novos += 1
            if dry_run:
                continue
            row = AdStat(
                organization_id=org_id,
                channel_id=channel.id,
                report_type=parsed["report_type"],
                listing_ref=r["listing_ref"],
                detail_key=r["detail_key"],
                period_start=parsed["period_start"],
                period_end=parsed["period_end"],
            )
            session.add(row)
            existing_stats[key] = row
        else:
            atualizados += 1
            if dry_run:
                continue
        row.ad_name = r["ad_name"][:300]
        for f in ("impressions", "clicks", "conversions", "items_sold", "gmv", "spend", "roas", "acos"):
            setattr(row, f, r[f])
        row.source_file = file.filename

    if not dry_run:
        await session.commit()

    # Aviso de sobreposição: períodos que se cruzam duplicariam o investimento nas somas.
    avisos = []
    overlapping = {
        (s.period_start, s.period_end)
        for s in existing_stats.values()
        if s.report_type == parsed["report_type"]
        and not (s.period_end < parsed["period_start"] or s.period_start > parsed["period_end"])
        and (s.period_start, s.period_end) != (parsed["period_start"], parsed["period_end"])
    }
    if overlapping:
        avisos.append(
            "Este período se sobrepõe a imports anteriores ("
            + ", ".join(f"{a}–{b}" for a, b in sorted(overlapping))
            + "). Para não duplicar investimento nas somas, exporte períodos contíguos (ex.: semana fechada)."
        )

    return {
        "dry_run": dry_run,
        "report_type": parsed["report_type"],
        "avisos": avisos,
        "periodo": {"de": str(parsed["period_start"]), "ate": str(parsed["period_end"])},
        "summary": {
            "linhas": len(rows_agg),
            "anuncios_agrupados": len(parsed["rows"]) - len(rows_agg),
            "novos": novos,
            "atualizados": atualizados,
            "spend_total": round(sum(r["spend"] for r in parsed["rows"]), 2),
            "gmv_total": round(sum(r["gmv"] for r in parsed["rows"]), 2),
            "erros": len(parsed["errors"]),
        },
        "errors": parsed["errors"][:50],
    }


@router.get("")
async def imports_status(user: CurrentUser, session: SessionDep):
    """Resumo do que já foi importado (para a tela de imports)."""
    org_id = user.organization_id
    orders_count = await session.scalar(
        select(func.count()).select_from(Order).where(Order.organization_id == org_id)
    )
    pend = await session.scalar(
        select(func.count())
        .select_from(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .where(Order.organization_id == org_id, OrderItem.mapping_status == "pendente")
    )
    ads_periods = (
        await session.execute(
            select(
                AdStat.report_type,
                AdStat.period_start,
                AdStat.period_end,
                func.count(),
                func.sum(AdStat.spend),
            )
            .where(AdStat.organization_id == org_id)
            .group_by(AdStat.report_type, AdStat.period_start, AdStat.period_end)
            .order_by(AdStat.period_start.desc())
        )
    ).all()
    return {
        "pedidos_importados": orders_count or 0,
        "itens_pendentes_vinculo": pend or 0,
        "ads_periodos": [
            {
                "report_type": rt,
                "de": str(ps),
                "ate": str(pe),
                "linhas": n,
                "spend": round(sp or 0, 2),
            }
            for rt, ps, pe, n, sp in ads_periods
        ],
    }
