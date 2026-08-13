from fastapi import APIRouter

from app.core.deps import CurrentUser, OwnerUser, SessionDep
from app.schemas.settings import SettingsOut, SettingsUpdate
from app.services.orgsettings import get_or_create_settings

router = APIRouter(prefix="/settings", tags=["configuracoes"])


@router.get("", response_model=SettingsOut)
async def get_settings(user: CurrentUser, session: SessionDep):
    settings = await get_or_create_settings(session, user.organization_id)
    await session.commit()
    return settings


@router.put("", response_model=SettingsOut)
async def update_settings(data: SettingsUpdate, owner: OwnerUser, session: SessionDep):
    settings = await get_or_create_settings(session, owner.organization_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    await session.commit()
    await session.refresh(settings)
    return settings
