"""Carrega um Snapshot em memória a partir do banco, escopado por organização."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ad_spend import AdSpend
from app.models.channel import Channel
from app.models.kit import Kit
from app.models.order import Order
from app.models.product import Product
from app.models.sale import Sale
from app.models.stock_lot import StockLot

# Pedidos nestes status NÃO contam como venda (sem receita, sem consumo de estoque).
ORDER_EXCLUDED_STATUSES = ("cancelado", "nao_pago", "devolucao")

# Offset para os ids sintéticos das vendas vindas de pedidos importados,
# evitando colisão com ids de vendas manuais.
IMPORTED_SALE_ID_OFFSET = 1_000_000_000
from app.services.snapshot import (
    SAd,
    SKit,
    SKitComponent,
    SLot,
    SProduct,
    SSale,
    Snapshot,
)


async def load_snapshot(session: AsyncSession, org_id: int) -> Snapshot:
    products = (
        await session.execute(select(Product).where(Product.organization_id == org_id))
    ).scalars().all()
    lots = (
        await session.execute(select(StockLot).where(StockLot.organization_id == org_id))
    ).scalars().all()
    kits = (
        await session.execute(select(Kit).where(Kit.organization_id == org_id))
    ).scalars().all()
    sales = (
        await session.execute(select(Sale).where(Sale.organization_id == org_id))
    ).scalars().all()
    ads = (
        await session.execute(select(AdSpend).where(AdSpend.organization_id == org_id))
    ).scalars().all()
    channel_names = {
        c.id: c.name
        for c in (
            await session.execute(select(Channel).where(Channel.organization_id == org_id))
        ).scalars()
    }
    orders = (
        await session.execute(
            select(Order).where(
                Order.organization_id == org_id,
                Order.status.notin_(ORDER_EXCLUDED_STATUSES),
            )
        )
    ).scalars().all()

    # Pedidos importados viram vendas do snapshot com as TAXAS REAIS do pedido,
    # rateadas por item na proporção do subtotal. O truque: derivamos o percentual
    # (taxa/receita) para o engine reproduzir exatamente o valor absoluto.
    imported_sales: list[SSale] = []
    for o in orders:
        total_sub = sum(i.subtotal for i in o.items) or 1.0
        fees_pct_base = o.taxa_comissao + o.taxa_servico
        for i in o.items:
            if i.product_id is None and i.kit_id is None:
                continue  # pendente de vínculo — não conta até ser mapeado
            frac = i.subtotal / total_sub
            receita = i.subtotal
            imported_sales.append(
                SSale(
                    id=IMPORTED_SALE_ID_OFFSET + i.id,
                    data_venda=(o.created_at_channel.date() if o.created_at_channel else o.created_at.date()),
                    item_type="product" if i.product_id else "kit",
                    qty=i.qty,
                    preco_unitario=i.unit_price,
                    taxa_shopee_pct=(fees_pct_base * frac / receita) if receita else 0.0,
                    taxa_fixa=0.0,
                    taxa_afiliado_pct=0.0,
                    outras_taxas=o.taxa_transacao * frac,
                    product_id=i.product_id,
                    kit_id=i.kit_id,
                    pedido=o.order_sn,
                    channel_id=o.channel_id,
                    channel_name=channel_names.get(o.channel_id),
                )
            )

    return Snapshot(
        products=[
            SProduct(
                id=p.id,
                sku=p.sku,
                nome=p.nome,
                dropdown_name=p.dropdown_name,
                variacao=p.variacao,
                ativo=p.ativo,
            )
            for p in products
        ],
        lots=[
            SLot(
                id=l.id,
                product_id=l.product_id,
                data_entrada=l.data_entrada,
                qty_in=l.qty_in,
                unit_cost=l.unit_cost,
                lote_code=l.lote_code,
            )
            for l in lots
        ],
        kits=[
            SKit(
                id=k.id,
                sku=k.sku,
                nome=k.nome,
                components=[
                    SKitComponent(product_id=c.product_id, qty=c.qty) for c in k.components
                ],
                ativo=k.ativo,
                preco_referencia=k.preco_referencia,
            )
            for k in kits
        ],
        sales=[
            SSale(
                id=s.id,
                data_venda=s.data_venda,
                item_type=s.item_type,
                qty=s.qty,
                preco_unitario=s.preco_unitario,
                taxa_shopee_pct=s.taxa_shopee_pct,
                taxa_fixa=s.taxa_fixa,
                taxa_afiliado_pct=s.taxa_afiliado_pct,
                outras_taxas=s.outras_taxas,
                product_id=s.product_id,
                kit_id=s.kit_id,
                pedido=s.pedido,
                channel_id=s.channel_id,
                channel_name=channel_names.get(s.channel_id),
            )
            for s in sales
        ]
        + imported_sales,
        ads=[SAd(id=a.id, data=a.data, valor=a.valor, canal=a.canal) for a in ads],
    )
