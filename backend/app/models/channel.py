from sqlalchemy import Boolean, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Channel(Base, TimestampMixin):
    """Canal / e-commerce (Shopee, TikTok, Mercado Livre, Shein...) com taxas próprias."""

    __tablename__ = "channels"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_channel_org_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    # comissão percentual do marketplace (fração; 0.2 = 20%)
    taxa_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    taxa_fixa: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    taxa_afiliado_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
