from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.deps import CurrentUser, SessionDep
from app.models.kit import Kit, KitComponent
from app.models.product import Product
from app.schemas.kit import KitIn, KitUpdate
from app.services import engine
from app.services.loader import load_snapshot

router = APIRouter(prefix="/kits", tags=["kits"])


def _out(kit: Kit, state: dict | None, product_names: dict[int, str]) -> dict:
    state = state or {}
    return {
        "id": kit.id,
        "sku": kit.sku,
        "nome": kit.nome,
        "ativo": kit.ativo,
        "preco_referencia": kit.preco_referencia,
        "observacao": kit.observacao,
        "components": [
            {
                "product_id": c.product_id,
                "produto": product_names.get(c.product_id, ""),
                "qty": c.qty,
            }
            for c in kit.components
        ],
        "custo_atual": state.get("custo_atual", 0.0),
        "qtd_itens": state.get("qtd_itens", sum(c.qty for c in kit.components)),
        "estoque_possivel": state.get("estoque_possivel", 0),
    }


async def _product_names(session, org_id: int) -> dict[int, str]:
    res = await session.execute(select(Product).where(Product.organization_id == org_id))
    return {p.id: p.dropdown_name for p in res.scalars().all()}


async def _validate_components(session, org_id: int, components) -> None:
    for c in components:
        p = await session.get(Product, c.product_id)
        if p is None or p.organization_id != org_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, f"Produto {c.product_id} inválido para a composição"
            )


async def _get_owned(session, org_id: int, kit_id: int) -> Kit:
    kit = await session.get(Kit, kit_id)
    if kit is None or kit.organization_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kit não encontrado")
    return kit


@router.get("")
async def list_kits(user: CurrentUser, session: SessionDep):
    snap = await load_snapshot(session, user.organization_id)
    states = engine.kit_states(snap)
    names = await _product_names(session, user.organization_id)
    res = await session.execute(
        select(Kit).where(Kit.organization_id == user.organization_id).order_by(Kit.id)
    )
    return [_out(k, states.get(k.id), names) for k in res.scalars().all()]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_kit(data: KitIn, user: CurrentUser, session: SessionDep):
    await _validate_components(session, user.organization_id, data.components)
    kit = Kit(
        organization_id=user.organization_id,
        sku=data.sku.strip(),
        nome=data.nome.strip(),
        ativo=data.ativo,
        preco_referencia=data.preco_referencia,
        observacao=data.observacao,
        components=[KitComponent(product_id=c.product_id, qty=c.qty) for c in data.components],
    )
    session.add(kit)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um kit com esse SKU")
    await session.refresh(kit)
    names = await _product_names(session, user.organization_id)
    return _out(kit, None, names)


@router.patch("/{kit_id}")
async def update_kit(kit_id: int, data: KitUpdate, user: CurrentUser, session: SessionDep):
    kit = await _get_owned(session, user.organization_id, kit_id)
    payload = data.model_dump(exclude_unset=True)
    components = payload.pop("components", None)
    for field, value in payload.items():
        setattr(kit, field, value)
    if components is not None:
        await _validate_components(session, user.organization_id, data.components)
        kit.components = [KitComponent(product_id=c["product_id"], qty=c["qty"]) for c in components]
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um kit com esse SKU")
    await session.refresh(kit)
    names = await _product_names(session, user.organization_id)
    return _out(kit, None, names)


@router.delete("/{kit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kit(kit_id: int, user: CurrentUser, session: SessionDep):
    kit = await _get_owned(session, user.organization_id, kit_id)
    try:
        await session.delete(kit)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Kit em uso por vendas — desative-o em vez de excluir"
        )
