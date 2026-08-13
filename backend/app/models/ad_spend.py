from datetime import date

from sqlalchemy import Date, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AdSpend(Base, TimestampMixin):
    """Aba Ads — investimento em anúncios por data/campanha."""

    __tablename__ = "ad_spends"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    data: Mapped[date] = mapped_column(Date, nullable=False)
    canal: Mapped[str | None] = mapped_column(String(120), nullable=True)
    valor: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)
