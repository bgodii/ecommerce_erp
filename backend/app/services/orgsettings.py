"""Helper para obter (criando se necessário) as configurações de taxas da loja."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.settings import OrgSettings


async def get_or_create_settings(session: AsyncSession, org_id: int) -> OrgSettings:
    settings = await session.get(OrgSettings, org_id)
    if settings is None:
        settings = OrgSettings(organization_id=org_id)
        session.add(settings)
        await session.flush()
    return settings
