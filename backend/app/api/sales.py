from datetime import date

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import select

from app.core.deps import CurrentUser, SessionDep
from app.models.channel import Channel
from app.models.kit import Kit
from app.models.product import Product
from app.models.sale import Sale
from app.schemas.sale import SaleIn, SaleUpdate
from app.services import engine
from app.services.csv_import import parse_sales_csv
from app.services.loader import load_snapshot
from app.services.orgsettings import get_or_create_settings

router = APIRouter(prefix="/sales", tags=["vendas"])


async def _row_for(session, org_id: int, sale_id: int) -> dict:
    snap = await load_snapshot(session, org_id)
    for row in engine.sale_rows(snap):
        if row["id"] == sale_id:
            return row
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Venda não encontrada")


async def _get_owned(session, org_id: int, sale_id: int) -> Sale:
    sale = await session.get(Sale, sale_id)
    if sale is None or sale.organization_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venda não encontrada")
    return sale


@router.get("")
async def list_sales(user: CurrentUser, session: SessionDep):
    snap = await load_snapshot(session, user.organization_id)
    rows = engine.sale_rows(snap)
    rows.sort(key=lambda r: (r["data_venda"], r["id"]), reverse=True)
    return rows


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_sale(data: SaleIn, user: CurrentUser, session: SessionDep):
    org_id = user.organization_id
    if data.item_type == "product":
        item = await session.get(Product, data.product_id)
        if item is None or item.organization_id != org_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Produto inválido")
    else:
        item = await session.get(Kit, data.kit_id)
        if item is None or item.organization_id != org_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Kit inválido")

    # Guardrail de estoque (ERP-002): bloqueia venda sem saldo, salvo override.
    if not data.permitir_sem_estoque:
        snap = await load_snapshot(session, org_id)
        if data.item_type == "product":
            disponivel = engine.product_states(snap).get(data.product_id, {}).get("estoque_atual", 0)
        else:
            disponivel = engine.kit_states(snap).get(data.kit_id, {}).get("estoque_possivel", 0)
        if data.qty > disponivel:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Estoque insuficiente: disponível {disponivel}, venda de {data.qty}. "
                "Confirme para lançar mesmo assim.",
            )

    settings = await get_or_create_settings(session, org_id)

    # Taxas default: do canal selecionado (se houver), senão das Configurações da loja.
    channel = None
    if data.channel_id is not None:
        channel = await session.get(Channel, data.channel_id)
        if channel is None or channel.organization_id != org_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Canal inválido")
    def_shopee = channel.taxa_pct if channel else settings.taxa_shopee_pct
    def_fixa = channel.taxa_fixa if channel else settings.taxa_fixa
    def_afiliado = channel.taxa_afiliado_pct if channel else settings.taxa_afiliado_pct

    sale = Sale(
        organization_id=org_id,
        data_venda=data.data_venda,
        pedido=data.pedido,
        item_type=data.item_type,
        product_id=data.product_id if data.item_type == "product" else None,
        kit_id=data.kit_id if data.item_type == "kit" else None,
        channel_id=channel.id if channel else None,
        qty=data.qty,
        preco_unitario=data.preco_unitario,
        taxa_shopee_pct=data.taxa_shopee_pct if data.taxa_shopee_pct is not None else def_shopee,
        taxa_fixa=data.taxa_fixa if data.taxa_fixa is not None else def_fixa,
        taxa_afiliado_pct=data.taxa_afiliado_pct
        if data.taxa_afiliado_pct is not None
        else def_afiliado,
        outras_taxas=data.outras_taxas or 0.0,
    )
    session.add(sale)
    await session.commit()
    await session.refresh(sale)
    return await _row_for(session, org_id, sale.id)


@router.patch("/{sale_id}")
async def update_sale(sale_id: int, data: SaleUpdate, user: CurrentUser, session: SessionDep):
    sale = await _get_owned(session, user.organization_id, sale_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(sale, field, value)
    await session.commit()
    return await _row_for(session, user.organization_id, sale_id)


@router.delete("/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sale(sale_id: int, user: CurrentUser, session: SessionDep):
    sale = await _get_owned(session, user.organization_id, sale_id)
    await session.delete(sale)
    await session.commit()


@router.post("/import")
async def import_sales(
    user: CurrentUser,
    session: SessionDep,
    file: UploadFile = File(...),
    dry_run: bool = False,
):
    """Importa vendas de um CSV (ERP-030). dry_run=true só valida e mostra o preview.

    Idempotente: pula linhas cujo (pedido + item) já exista. Taxas ausentes usam as
    Configurações da loja. O guardrail de estoque NÃO se aplica (pedidos históricos).
    """
    org_id = user.organization_id
    content = await file.read()
    parsed, errors = parse_sales_csv(content)

    products = {
        p.sku: p
        for p in (
            await session.execute(select(Product).where(Product.organization_id == org_id))
        ).scalars()
    }
    kits = {
        k.sku: k
        for k in (
            await session.execute(select(Kit).where(Kit.organization_id == org_id))
        ).scalars()
    }
    settings = await get_or_create_settings(session, org_id)

    existing = {
        (s.pedido, s.item_type, s.product_id if s.item_type == "product" else s.kit_id)
        for s in (
            await session.execute(select(Sale).where(Sale.organization_id == org_id))
        ).scalars()
        if s.pedido
    }

    seen: set = set()
    to_insert: list[Sale] = []
    preview: list[dict] = []
    novos = duplicados = 0

    for r in parsed:
        sku = r["sku"]
        p = products.get(sku)
        k = kits.get(sku)
        if not p and not k:
            errors.append({"linha": None, "erro": f"SKU não encontrado: {sku}"})
            preview.append({**r, "item": None, "status": "erro"})
            continue

        item_type = "product" if p else "kit"
        item_id = p.id if p else k.id
        item_nome = p.dropdown_name if p else k.nome
        key = (r["pedido"], item_type, item_id)

        if r["pedido"] and (key in existing or key in seen):
            duplicados += 1
            preview.append({**r, "item": item_nome, "status": "duplicado"})
            continue

        seen.add(key)
        novos += 1
        preview.append({**r, "item": item_nome, "status": "novo"})
        if not dry_run:
            to_insert.append(
                Sale(
                    organization_id=org_id,
                    data_venda=date.fromisoformat(r["data_venda"]),
                    pedido=r["pedido"],
                    item_type=item_type,
                    product_id=p.id if p else None,
                    kit_id=k.id if k else None,
                    qty=r["qty"],
                    preco_unitario=r["preco_unitario"],
                    taxa_shopee_pct=r["taxa_shopee_pct"]
                    if r["taxa_shopee_pct"] is not None
                    else settings.taxa_shopee_pct,
                    taxa_fixa=r["taxa_fixa"] if r["taxa_fixa"] is not None else settings.taxa_fixa,
                    taxa_afiliado_pct=r["taxa_afiliado_pct"]
                    if r["taxa_afiliado_pct"] is not None
                    else settings.taxa_afiliado_pct,
                    outras_taxas=r["outras_taxas"] or 0.0,
                )
            )

    if not dry_run and to_insert:
        session.add_all(to_insert)
        await session.commit()

    return {
        "dry_run": dry_run,
        "summary": {
            "total": len(parsed),
            "novos": novos,
            "duplicados": duplicados,
            "erros": len(errors),
        },
        "errors": errors[:50],
        "preview": preview[:100],
    }
