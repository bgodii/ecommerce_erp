from sqlalchemy import Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OrgSettings(Base):
    """Aba Configuracoes — taxas por loja (1 linha por organização)."""

    __tablename__ = "org_settings"

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    # Taxa Shopee (%) — fração (0.2 = 20%)
    taxa_shopee_pct: Mapped[float] = mapped_column(Float, default=0.20, nullable=False)
    # Taxa fixa por pedido (R$)
    taxa_fixa: Mapped[float] = mapped_column(Float, default=4.0, nullable=False)
    # Taxa afiliado padrão (%) — fração
    taxa_afiliado_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
