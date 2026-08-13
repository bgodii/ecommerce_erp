"""canais (e-commerces) com taxas próprias

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_now = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "channels",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("taxa_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("taxa_fixa", sa.Float(), nullable=False, server_default="0"),
        sa.Column("taxa_afiliado_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now, nullable=False),
        sa.UniqueConstraint("organization_id", "name", name="uq_channel_org_name"),
    )
    op.create_index("ix_channels_organization_id", "channels", ["organization_id"])

    op.add_column("sales", sa.Column("channel_id", sa.Integer(), nullable=True))
    op.create_index("ix_sales_channel_id", "sales", ["channel_id"])
    op.create_foreign_key(
        "fk_sales_channel_id", "sales", "channels", ["channel_id"], ["id"], ondelete="SET NULL"
    )

    # Backfill: cria um canal "Shopee" por loja a partir das taxas atuais e vincula as vendas.
    op.execute(
        """
        INSERT INTO channels (organization_id, name, taxa_pct, taxa_fixa, taxa_afiliado_pct, ativo, created_at)
        SELECT organization_id, 'Shopee', taxa_shopee_pct, taxa_fixa, taxa_afiliado_pct, true, now()
        FROM org_settings
        """
    )
    op.execute(
        """
        UPDATE sales SET channel_id = c.id
        FROM channels c
        WHERE c.organization_id = sales.organization_id AND c.name = 'Shopee'
        """
    )


def downgrade() -> None:
    op.drop_constraint("fk_sales_channel_id", "sales", type_="foreignkey")
    op.drop_index("ix_sales_channel_id", "sales")
    op.drop_column("sales", "channel_id")
    op.drop_table("channels")
