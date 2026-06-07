from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.config import get_settings

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/geometry/{filename}")
def serve_geometry(filename: str):
    safe_name = Path(filename).name
    path = get_settings().converted_dir / safe_name
    if not path.exists() or path.suffix.lower() != ".glb":
        raise HTTPException(status_code=404, detail="Geometria no encontrada")
    return FileResponse(path, media_type="model/gltf-binary", filename=safe_name)
