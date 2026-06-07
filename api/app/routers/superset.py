from fastapi import APIRouter

from app.schemas import SupersetEmbedConfig
from app.services.superset import get_embed_config

router = APIRouter(prefix="/superset", tags=["superset"])


@router.get("/embed", response_model=SupersetEmbedConfig)
async def embed_config():
    return await get_embed_config()
