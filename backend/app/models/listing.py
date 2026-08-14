from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Listing(Base, TimestampMixin):
    """Anúncio/página de produto no marketplace (ex.: 'ID do produto' da Shopee).

    Os relatórios de ADS referenciam o listing. Vincular a um produto/kit do ERP é
    opcional e enriquece a análise (margem/CMV → ROAS de equilíbrio).
    """

    __tablename__ = "listings"
    __table_args__ = (
        UniqueConstraint("organization_id", "channel_id", "listing_id", name="uq_listing_org_channel"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    channel_id: Mapped[int | None] = mapped_column(
        ForeignKey("channels.id", ondelete="SET NULL"), index=True, nullable=True
    )
    listing_id: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)

    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    kit_id: Mapped[int | None] = mapped_column(
        ForeignKey("kits.id", ondelete="SET NULL"), nullable=True
    )
