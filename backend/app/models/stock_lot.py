from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class StockLot(Base, TimestampMixin):
    """Aba Entradas — lote de compra (FIFO). Consumo/saldo são calculados a partir das vendas."""

    __tablename__ = "stock_lots"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True, nullable=False
    )
    lote_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    data_entrada: Mapped[date] = mapped_column(Date, nullable=False)
    qty_in: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
