from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    """Aba Produtos — cadastro. Estoque/valor/custo médio são derivados dos lotes e vendas."""

    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("organization_id", "sku", name="uq_product_org_sku"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sku: Mapped[str] = mapped_column(String(80), nullable=False)
    nome: Mapped[str] = mapped_column(String(160), nullable=False)
    variacao: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Nome exibido no dropdown de vendas (aba Produtos, coluna D)
    dropdown_name: Mapped[str] = mapped_column(String(200), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
