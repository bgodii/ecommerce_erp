from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Kit(Base, TimestampMixin):
    """Aba Kits — combinação vendável. Custo/estoque possível são derivados da composição."""

    __tablename__ = "kits"
    __table_args__ = (UniqueConstraint("organization_id", "sku", name="uq_kit_org_sku"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sku: Mapped[str] = mapped_column(String(80), nullable=False)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    preco_referencia: Mapped[float | None] = mapped_column(Float, nullable=True)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)

    components: Mapped[list["KitComponent"]] = relationship(
        back_populates="kit", cascade="all, delete-orphan", lazy="selectin"
    )


class KitComponent(Base):
    """Aba Composicao Kits — BOM: quais produtos e quantidades formam o kit."""

    __tablename__ = "kit_components"

    id: Mapped[int] = mapped_column(primary_key=True)
    kit_id: Mapped[int] = mapped_column(
        ForeignKey("kits.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    qty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    kit: Mapped[Kit] = relationship(back_populates="components")
