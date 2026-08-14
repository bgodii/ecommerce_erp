from fastapi import APIRouter

from app.api import (
    ad_spends,
    auth,
    channels,
    imports,
    kits,
    mappings,
    overview,
    pricing,
    products,
    reports,
    sales,
    settings,
    stock_lots,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(products.router)
api_router.include_router(stock_lots.router)
api_router.include_router(kits.router)
api_router.include_router(channels.router)
api_router.include_router(sales.router)
api_router.include_router(ad_spends.router)
api_router.include_router(settings.router)
api_router.include_router(reports.router)
api_router.include_router(pricing.router)
api_router.include_router(imports.router)
api_router.include_router(mappings.router)
api_router.include_router(overview.router)
