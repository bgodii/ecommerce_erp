from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.deps import CurrentUser, SessionDep
from app.models.product import Product
from app.models.stock_lot import StockLot
from app.schemas.product import ProductIn, ProductUpdate, StockAdjustIn
from app.services import engine
from app.services.loader import load_snapshot

router = APIRouter(prefix="/products", tags=["products"])


def _out(p: Product, state: dict | None) -> dict:
    state = state or {}
    return {
        "id": p.id,
        "sku": p.sku,
        "nome": p.nome,
        "variacao": p.variacao,
        "dropdown_name": p.dropdown_name,
        "ativo": p.ativo,
        "estoque_atual": state.get("estoque_atual", 0),
        "saldo_real": state.get("saldo_real", 0),
        "deficit": state.get("deficit", 0),
        "valor_estoque": state.get("valor_estoque", 0.0),
        "custo_medio_atual": state.get("custo_medio_atual", 0.0),
        # estoque explicado: entradas − vendas diretas − consumo em kits = estoque
        "entradas": state.get("entradas", 0),
        "vendas_diretas": state.get("vendas_diretas", 0),
        "consumo_kits": state.get("consumo_kits", 0),
    }


async def _get_owned(session, org_id: int, product_id: int) -> Product:
    p = await session.get(Product, product_id)
    if p is None or p.organization_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Produto não encontrado")
    return p


@router.get("")
async def list_products(user: CurrentUser, session: SessionDep):
    snap = await load_snapshot(session, user.organization_id)
    states = engine.product_states(snap)
    res = await session.execute(
        select(Product)
        .where(Product.organization_id == user.organization_id)
        .order_by(Product.id)
    )
    return [_out(p, states.get(p.id)) for p in res.scalars().all()]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_product(data: ProductIn, user: CurrentUser, session: SessionDep):
    p = Product(
        organization_id=user.organization_id,
        sku=data.sku.strip(),
        nome=data.nome.strip(),
        variacao=data.variacao,
        dropdown_name=(data.dropdown_name or data.nome).strip(),
        ativo=data.ativo,
    )
    session.add(p)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um produto com esse SKU")
    await session.refresh(p)
    return _out(p, None)


@router.patch("/{product_id}")
async def update_product(
    product_id: int, data: ProductUpdate, user: CurrentUser, session: SessionDep
):
    p = await _get_owned(session, user.organization_id, product_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Já existe um produto com esse SKU")
    await session.refresh(p)
    return _out(p, None)


@router.post("/{product_id}/ajuste-estoque")
async def ajustar_estoque(
    product_id: int, data: StockAdjustIn, user: CurrentUser, session: SessionDep
):
    """Acerta o estoque do produto para a quantidade informada.

    Cria uma ENTRADA de acerto com a diferença, no custo informado, datada antes da
    primeira venda (para o FIFO das vendas antigas encontrar estoque). Não altera nem
    apaga lotes existentes — o histórico é preservado.
    """
    org_id = user.organization_id
    p = await _get_owned(session, org_id, product_id)

    snap = await load_snapshot(session, org_id)
    state = engine.product_states(snap).get(product_id, {})
    saldo_real = state.get("saldo_real", 0)
    diff = data.estoque_atual - saldo_real

    if diff == 0:
        return {"ajuste": 0, "mensagem": "Estoque já está nesse valor — nada a fazer."}
    if diff < 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"O estoque informado ({data.estoque_atual}) é menor que o calculado ({saldo_real}). "
            "Para reduzir, registre a perda/devolução ou corrija as entradas existentes.",
        )

    # data do acerto: a informada, senão o dia anterior à venda mais antiga
    if data.data_entrada:
        dt = data.data_entrada
    else:
        datas = [s.data_venda for s in snap.sales]
        dt = (min(datas) - timedelta(days=1)) if datas else date.today()

    lot = StockLot(
        organization_id=org_id,
        product_id=product_id,
        lote_code="ACERTO",
        data_entrada=dt,
        qty_in=diff,
        unit_cost=data.custo_unitario,
    )
    session.add(lot)
    await session.commit()
    return {
        "ajuste": diff,
        "data_entrada": str(dt),
        "custo_unitario": data.custo_unitario,
        "mensagem": f"Entrada de acerto criada: +{diff} un a {data.custo_unitario:.2f} em {dt}.",
    }


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(product_id: int, user: CurrentUser, session: SessionDep):
    p = await _get_owned(session, user.organization_id, product_id)
    try:
        await session.delete(p)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Produto em uso por lotes, kits ou vendas — desative-o em vez de excluir",
        )
