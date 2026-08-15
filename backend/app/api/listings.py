"""Anúncios do marketplace (listings) e o vínculo com produtos/kits do ERP.

Vincular permite usar a **margem real daquele item** na análise de ADS (ROAS even e
CPC máximo por anúncio) em vez da margem média da loja.
"""
from difflib import SequenceMatcher

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, model_validator
from sqlalchemy import select

from app.core.deps import CurrentUser, SessionDep
from app.models.kit import Kit
from app.models.listing import Listing
from app.models.product import Product

router = APIRouter(prefix="/listings", tags=["anuncios"])


class ListingLinkIn(BaseModel):
    product_id: int | None = None
    kit_id: int | None = None

    @model_validator(mode="after")
    def _one(self):
        if self.product_id and self.kit_id:
            raise ValueError("Informe apenas product_id OU kit_id")
        return self


def _score(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


@router.get("")
async def list_listings(user: CurrentUser, session: SessionDep):
    """Anúncios conhecidos (vindos dos relatórios de ADS) + sugestões de vínculo."""
    org_id = user.organization_id
    listings = (
        await session.execute(
            select(Listing).where(Listing.organization_id == org_id).order_by(Listing.id)
        )
    ).scalars().all()
    products = (
        (await session.execute(select(Product).where(Product.organization_id == org_id)))
        .scalars().all()
    )
    kits = (
        (await session.execute(select(Kit).where(Kit.organization_id == org_id))).scalars().all()
    )
    pnames = {p.id: p.dropdown_name for p in products}
    knames = {k.id: k.nome for k in kits}

    out = []
    for l in listings:
        sug = [
            {"tipo": "product", "id": p.id, "nome": p.dropdown_name, "score": round(_score(l.name, p.dropdown_name), 3)}
            for p in products
        ] + [
            {"tipo": "kit", "id": k.id, "nome": k.nome, "score": round(_score(l.name, k.nome), 3)}
            for k in kits
        ]
        sug.sort(key=lambda x: -x["score"])
        out.append(
            {
                "id": l.id,
                "listing_id": l.listing_id,
                "nome": l.name,
                "product_id": l.product_id,
                "kit_id": l.kit_id,
                "vinculado_a": pnames.get(l.product_id) or knames.get(l.kit_id),
                "sugestoes": sug[:5],
            }
        )
    return out


@router.patch("/{listing_id}")
async def link_listing(
    listing_id: int, data: ListingLinkIn, user: CurrentUser, session: SessionDep
):
    """Vincula (ou desvincula, enviando ambos nulos) o anúncio a um produto/kit."""
    org_id = user.organization_id
    l = await session.get(Listing, listing_id)
    if l is None or l.organization_id != org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Anúncio não encontrado")

    if data.product_id:
        p = await session.get(Product, data.product_id)
        if p is None or p.organization_id != org_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Produto inválido")
    if data.kit_id:
        k = await session.get(Kit, data.kit_id)
        if k is None or k.organization_id != org_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Kit inválido")

    l.product_id = data.product_id
    l.kit_id = data.kit_id
    await session.commit()
    return {"id": l.id, "product_id": l.product_id, "kit_id": l.kit_id}
