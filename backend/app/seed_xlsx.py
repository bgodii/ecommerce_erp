"""Importa uma planilha (formato da `ERP - Ecommer.xlsx`) para uma loja.

A planilha NÃO é versionada no repositório (contém dados reais). Forneça o caminho:
    python -m app.seed_xlsx --xlsx /caminho/para/sua-planilha.xlsx --email voce@email.com --password suasenha

É seguro rodar várias vezes: se o e-mail já existir, aborta sem duplicar.
"""
from __future__ import annotations

import argparse
import asyncio
import os

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models.ad_spend import AdSpend
from app.models.channel import Channel
from app.models.kit import Kit, KitComponent
from app.models.organization import Organization
from app.models.product import Product
from app.models.sale import Sale
from app.models.settings import OrgSettings
from app.models.stock_lot import StockLot
from app.models.user import User
from app.xlsx_import import parse_workbook


async def seed(email: str, password: str, org_name: str, xlsx_path: str | None) -> None:
    parsed = parse_workbook(xlsx_path) if xlsx_path else parse_workbook()
    snap = parsed.snapshot

    async with SessionLocal() as session:
        existing = (
            await session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()
        if existing:
            print(f"[seed] Usuário {email} já existe — nada a fazer (evitando duplicar).")
            return

        org = Organization(name=org_name)
        session.add(org)
        await session.flush()

        session.add(
            User(
                organization_id=org.id,
                email=email,
                name="Demo",
                password_hash=hash_password(password),
                role="owner",
            )
        )
        st = parsed.settings
        session.add(
            OrgSettings(
                organization_id=org.id,
                taxa_shopee_pct=st.taxa_shopee_pct,
                taxa_fixa=st.taxa_fixa,
                taxa_afiliado_pct=st.taxa_afiliado_pct,
            )
        )
        channel = Channel(
            organization_id=org.id,
            name="Shopee",
            taxa_pct=st.taxa_shopee_pct,
            taxa_fixa=st.taxa_fixa,
            taxa_afiliado_pct=st.taxa_afiliado_pct,
            ativo=True,
        )
        session.add(channel)
        await session.flush()

        pid_map: dict[int, int] = {}
        for sp in snap.products:
            p = Product(
                organization_id=org.id,
                sku=sp.sku,
                nome=sp.nome,
                variacao=sp.variacao,
                dropdown_name=sp.dropdown_name,
                ativo=sp.ativo,
            )
            session.add(p)
            await session.flush()
            pid_map[sp.id] = p.id

        for sl in snap.lots:
            session.add(
                StockLot(
                    organization_id=org.id,
                    product_id=pid_map[sl.product_id],
                    lote_code=sl.lote_code,
                    data_entrada=sl.data_entrada,
                    qty_in=sl.qty_in,
                    unit_cost=sl.unit_cost,
                )
            )

        kid_map: dict[int, int] = {}
        for sk in snap.kits:
            k = Kit(
                organization_id=org.id,
                sku=sk.sku,
                nome=sk.nome,
                ativo=sk.ativo,
                preco_referencia=sk.preco_referencia,
                components=[
                    KitComponent(product_id=pid_map[c.product_id], qty=c.qty)
                    for c in sk.components
                    if c.product_id in pid_map
                ],
            )
            session.add(k)
            await session.flush()
            kid_map[sk.id] = k.id

        for ss in snap.sales:
            session.add(
                Sale(
                    organization_id=org.id,
                    data_venda=ss.data_venda,
                    pedido=ss.pedido,
                    item_type=ss.item_type,
                    product_id=pid_map.get(ss.product_id) if ss.product_id else None,
                    kit_id=kid_map.get(ss.kit_id) if ss.kit_id else None,
                    channel_id=channel.id,
                    qty=ss.qty,
                    preco_unitario=ss.preco_unitario,
                    taxa_shopee_pct=ss.taxa_shopee_pct,
                    taxa_fixa=ss.taxa_fixa,
                    taxa_afiliado_pct=ss.taxa_afiliado_pct,
                    outras_taxas=ss.outras_taxas,
                )
            )

        for sa in snap.ads:
            session.add(
                AdSpend(organization_id=org.id, data=sa.data, valor=sa.valor, canal=sa.canal)
            )

        await session.commit()
        print(
            f"[seed] OK org={org.id} '{org_name}' | login: {email} / {password} | "
            f"produtos={len(snap.products)} lotes={len(snap.lots)} kits={len(snap.kits)} "
            f"vendas={len(snap.sales)} ads={len(snap.ads)}"
        )


def main() -> None:
    from app.xlsx_import import DEFAULT_XLSX

    ap = argparse.ArgumentParser(description="Seed do ERP a partir de uma planilha")
    ap.add_argument("--email", default="demo@example.com")
    ap.add_argument("--password", default="demo12345")
    ap.add_argument("--org", default="Minha Loja")
    ap.add_argument("--xlsx", default=None, help="Caminho do .xlsx (obrigatório — não vem no repo)")
    args = ap.parse_args()

    path = args.xlsx or DEFAULT_XLSX
    if not os.path.exists(path):
        raise SystemExit(
            f"[seed] Planilha não encontrada em '{path}'. "
            "Passe --xlsx /caminho/da/sua-planilha.xlsx (o arquivo não é versionado)."
        )
    asyncio.run(seed(args.email, args.password, args.org, args.xlsx))


if __name__ == "__main__":
    main()
