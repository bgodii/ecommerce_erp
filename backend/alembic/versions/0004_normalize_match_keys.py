"""normaliza match_key dos vínculos removendo o tamanho (agrega por cor/modelo)

Antes: 'blusa-branco-m' e 'blusa-branco-g' eram vínculos diferentes.
Agora: viram 'blusa-branco' — um vínculo cobre todos os tamanhos.
Mantém o primeiro vínculo de cada chave normalizada e descarta os duplicados.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from app.services.sku_resolve import strip_size
    from app.services.shopee_import import norm_key

    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT id, organization_id, channel_id, match_key FROM sku_mappings ORDER BY id"
        )
    ).fetchall()

    seen: set[tuple] = set()
    for mid, org_id, channel_id, key in rows:
        # a chave pode ser 'sku' ou 'nome||variacao' — normaliza a última parte
        parts = (key or "").split("||")
        parts[-1] = norm_key(strip_size(parts[-1]))
        new_key = "||".join(p for p in parts if p)
        scope = (org_id, channel_id, new_key)
        if not new_key or scope in seen:
            conn.execute(sa.text("DELETE FROM sku_mappings WHERE id = :id"), {"id": mid})
            continue
        seen.add(scope)
        if new_key != key:
            conn.execute(
                sa.text("UPDATE sku_mappings SET match_key = :k WHERE id = :id"),
                {"k": new_key, "id": mid},
            )


def downgrade() -> None:
    # Normalização é irreversível (chaves antigas foram perdidas). No-op.
    pass
