from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SkuMapping(Base, TimestampMixin):
    """De-para: SKU/variação do marketplace → produto ou kit do ERP.

    match_key é a chave normalizada (minúscula, sem espaços duplicados):
      - sku_var quando o export traz 'Número de referência SKU'
      - senão 'product_name||variation_name'
    Vários tamanhos podem apontar pro mesmo produto (decisão do usuário: agregar por cor/modelo).
    """

    __tablename__ = "sku_mappings"
    __table_args__ = (
        UniqueConstraint("organization_id", "channel_id", "match_key", name="uq_mapping_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    channel_id: Mapped[int | None] = mapped_column(
        ForeignKey("channels.id", ondelete="SET NULL"), index=True, nullable=True
    )
    match_key: Mapped[str] = mapped_column(String(400), nullable=False)

    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=True
    )
    kit_id: Mapped[int | None] = mapped_column(
        ForeignKey("kits.id", ondelete="CASCADE"), nullable=True
    )
    # multiplicador de quantidade (ex.: 1 linha do marketplace = 2 unidades do produto)
    qty: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
