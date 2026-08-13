from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Sale(Base, TimestampMixin):
    """Aba Vendas. Taxas são gravadas como snapshot; receita/CMV/lucro/margem são derivados."""

    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    data_venda: Mapped[date] = mapped_column(Date, nullable=False)
    pedido: Mapped[str | None] = mapped_column(String(60), nullable=True)

    # 'product' ou 'kit' — exatamente um dos FKs abaixo é preenchido
    item_type: Mapped[str] = mapped_column(String(10), nullable=False)
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    kit_id: Mapped[int | None] = mapped_column(
        ForeignKey("kits.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    # canal / e-commerce da venda (Shopee, TikTok, ML...). Nulo = padrão da loja.
    channel_id: Mapped[int | None] = mapped_column(
        ForeignKey("channels.id", ondelete="SET NULL"), index=True, nullable=True
    )

    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    preco_unitario: Mapped[float] = mapped_column(Float, nullable=False)

    # Snapshots das taxas no momento da venda (frações; 0.2 = 20%)
    taxa_shopee_pct: Mapped[float] = mapped_column(Float, nullable=False)
    taxa_fixa: Mapped[float] = mapped_column(Float, nullable=False)
    taxa_afiliado_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    outras_taxas: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
