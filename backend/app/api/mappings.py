"""Vínculo de SKUs (de-para marketplace → ERP) e aplicação retroativa."""
from difflib import SequenceMatcher

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select

from app.core.deps import CurrentUser, SessionDep
from app.models.kit import Kit
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.sku_mapping import SkuMapping
from app.services.sku_resolve import auto_product_identity, item_match_key

router = APIRouter(prefix="/mappings", tags=["vinculo-skus"])


class MappingIn(BaseModel):
    match_key: str = Field(min_length=1, max_length=400)
    channel_id: int | None = None
    product_id: int | None = None
    kit_id: int | None = None

    @model_validator(mode="after")
    def _one_target(self):
        if bool(self.product_id) == bool(self.kit_id):
            raise ValueError("Informe exatamente um: product_id OU kit_id")
        return self


def _score(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


async def _pending_items(session, org_id: int) -> list[OrderItem]:
    return list(
        (
            await session.execute(
                select(OrderItem)
                .join(Order, OrderItem.order_id == Order.id)
                .where(
                    Order.organization_id == org_id,
                    OrderItem.mapping_status == "pendente",
                )
            )
        ).scalars()
    )


@router.get("/pendentes")
async def list_pending(user: CurrentUser, session: SessionDep):
    """Itens sem vínculo, agrupados por chave, com sugestões fuzzy de produto/kit."""
    org_id = user.organization_id
    items = await _pending_items(session, org_id)

    products = (
        (await session.execute(select(Product).where(Product.organization_id == org_id)))
        .scalars().all()
    )
    kits = (
        (await session.execute(select(Kit).where(Kit.organization_id == org_id))).scalars().all()
    )

    groups: dict[str, dict] = {}
    for i in items:
        key = item_match_key(
            {
                "sku_var": i.sku_var,
                "product_name": i.product_name,
                "variation_name": i.variation_name,
            }
        )
        g = groups.setdefault(
            key,
            {
                "match_key": key,
                "sku_var": i.sku_var,
                "product_name": i.product_name,
                "variation_name": i.variation_name,
                "qtd_itens": 0,
                "qtd_unidades": 0,
            },
        )
        g["qtd_itens"] += 1
        g["qtd_unidades"] += i.qty

    out = []
    for g in groups.values():
        texto = " ".join(filter(None, [g["sku_var"], g["product_name"], g["variation_name"]]))
        sugestoes = []
        for p in products:
            s = max(_score(texto, p.dropdown_name), _score(texto, p.sku), _score(texto, p.nome))
            sugestoes.append({"tipo": "product", "id": p.id, "nome": p.dropdown_name, "score": round(s, 3)})
        for k in kits:
            s = max(_score(texto, k.nome), _score(texto, k.sku))
            sugestoes.append({"tipo": "kit", "id": k.id, "nome": k.nome, "score": round(s, 3)})
        sugestoes.sort(key=lambda x: -x["score"])
        g["sugestoes"] = sugestoes[:5]
        # sugestão de SKU/nome caso o usuário opte por CRIAR um produto novo
        sku_sug, nome_sug = auto_product_identity(
            {
                "sku_var": g["sku_var"],
                "product_name": g["product_name"],
                "variation_name": g["variation_name"],
            }
        )
        g["novo_produto_sugerido"] = {"sku": sku_sug, "nome": nome_sug}
        out.append(g)

    out.sort(key=lambda g: -g["qtd_unidades"])
    return out


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_mapping(data: MappingIn, user: CurrentUser, session: SessionDep):
    """Cria/atualiza o vínculo e aplica retroativamente aos itens pendentes."""
    org_id = user.organization_id
    if data.product_id:
        target = await session.get(Product, data.product_id)
        if target is None or target.organization_id != org_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Produto inválido")
    else:
        target = await session.get(Kit, data.kit_id)
        if target is None or target.organization_id != org_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Kit inválido")

    existing = (
        await session.execute(
            select(SkuMapping).where(
                SkuMapping.organization_id == org_id,
                SkuMapping.channel_id == data.channel_id,
                SkuMapping.match_key == data.match_key,
            )
        )
    ).scalars().first()
    if existing is None:
        existing = SkuMapping(
            organization_id=org_id, channel_id=data.channel_id, match_key=data.match_key
        )
        session.add(existing)
    existing.product_id = data.product_id
    existing.kit_id = data.kit_id

    # retroativo: aplica a TODOS os itens pendentes com a mesma chave
    aplicados = 0
    for i in await _pending_items(session, org_id):
        key = item_match_key(
            {"sku_var": i.sku_var, "product_name": i.product_name, "variation_name": i.variation_name}
        )
        if key == data.match_key:
            i.product_id = data.product_id
            i.kit_id = data.kit_id
            i.mapping_status = "manual"
            aplicados += 1

    await session.commit()
    return {"match_key": data.match_key, "itens_aplicados": aplicados}


@router.get("")
async def list_mappings(user: CurrentUser, session: SessionDep):
    org_id = user.organization_id
    rows = (
        await session.execute(
            select(SkuMapping).where(SkuMapping.organization_id == org_id).order_by(SkuMapping.id)
        )
    ).scalars().all()
    pnames = {
        p.id: p.dropdown_name
        for p in (
            await session.execute(select(Product).where(Product.organization_id == org_id))
        ).scalars()
    }
    knames = {
        k.id: k.nome
        for k in (await session.execute(select(Kit).where(Kit.organization_id == org_id))).scalars()
    }
    return [
        {
            "id": m.id,
            "match_key": m.match_key,
            "destino": pnames.get(m.product_id) or knames.get(m.kit_id) or "?",
            "tipo": "product" if m.product_id else "kit",
        }
        for m in rows
    ]


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mapping(mapping_id: int, user: CurrentUser, session: SessionDep):
    """Remove o vínculo e devolve os itens correspondentes para 'pendente'."""
    org_id = user.organization_id
    m = await session.get(SkuMapping, mapping_id)
    if m is None or m.organization_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vínculo não encontrado")

    items = (
        await session.execute(
            select(OrderItem)
            .join(Order, OrderItem.order_id == Order.id)
            .where(Order.organization_id == org_id)
        )
    ).scalars().all()
    for i in items:
        key = item_match_key(
            {"sku_var": i.sku_var, "product_name": i.product_name, "variation_name": i.variation_name}
        )
        if key == m.match_key:
            i.product_id = None
            i.kit_id = None
            i.mapping_status = "pendente"
    await session.delete(m)
    await session.commit()
