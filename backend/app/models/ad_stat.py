from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

AD_REPORT_TYPES = ("geral", "keyword", "gmvmax", "adgroup")


class AdStat(Base, TimestampMixin):
    """Métricas de ADS importadas dos relatórios do marketplace (agregadas por período).

    Uma linha por (tipo de relatório, listing, período). Reimportar o mesmo período
    substitui os valores (upsert) — não duplica.
    """

    __tablename__ = "ad_stats"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "channel_id",
            "report_type",
            "listing_ref",
            "detail_key",
            "period_start",
            "period_end",
            name="uq_adstat_scope",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    channel_id: Mapped[int | None] = mapped_column(
        ForeignKey("channels.id", ondelete="SET NULL"), index=True, nullable=True
    )
    report_type: Mapped[str] = mapped_column(String(12), nullable=False)
    # listing_id do canal ('-' quando não se aplica, ex.: GMV MAX da loja)
    listing_ref: Mapped[str] = mapped_column(String(40), default="-", nullable=False)
    # granularidade extra (palavra-chave/locação no relatório keyword; '-' nos demais)
    detail_key: Mapped[str] = mapped_column(String(200), default="-", nullable=False)
    ad_name: Mapped[str | None] = mapped_column(String(300), nullable=True)

    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    impressions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    clicks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    items_sold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gmv: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    spend: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    roas: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    acos: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
