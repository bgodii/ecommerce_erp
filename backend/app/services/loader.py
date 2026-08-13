"""Carrega um Snapshot em memória a partir do banco, escopado por organização."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ad_spend import AdSpend
from app.models.channel import Channel
from app.models.kit import Kit
from app.models.product import Product
from app.models.sale import Sale
from app.models.stock_lot import StockLot
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
        ],
        ads=[SAd(id=a.id, data=a.data, valor=a.valor, canal=a.canal) for a in ads],
    )
