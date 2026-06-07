from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
import ifcopenshell.guid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import IfcElement, Model
from app.db.session import get_db
from app.schemas import GeometrySelectionMap
from app.schemas import ModelSummary
from app.schemas import GeometryAsset
from app.services.geometry import convert_model_to_glb, geometry_url_for
from app.services.ifc_extractor import safe_upload_path

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelSummary])
def list_models(db: Session = Depends(get_db)):
    return db.scalars(select(Model).order_by(Model.created_at.desc())).all()


@router.post("/upload", response_model=list[ModelSummary])
async def upload_models(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    created: list[Model] = []
    for file in files:
        if not file.filename or not file.filename.lower().endswith(".ifc"):
            raise HTTPException(status_code=400, detail=f"{file.filename} no es un archivo .ifc")
        base_path = safe_upload_path(settings.upload_dir, file.filename)
        target_path = _unique_path(base_path)
        with target_path.open("wb") as target:
            target.write(await file.read())
        model = Model(
            name=Path(file.filename).stem,
            original_filename=file.filename,
            file_path=str(target_path),
            status="uploaded",
        )
        db.add(model)
        db.flush()
        created.append(model)
    db.commit()

    return created


@router.get("/{model_id}/geometry", response_model=GeometryAsset)
def get_geometry(model_id: int, db: Session = Depends(get_db)):
    model = db.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")
    url = geometry_url_for(model)
    return GeometryAsset(
        model_id=model.id,
        available=url is not None,
        status=model.geometry_status,
        url=url,
        error=model.geometry_error,
    )


@router.post("/{model_id}/convert", response_model=GeometryAsset)
def convert_geometry(model_id: int, db: Session = Depends(get_db)):
    model = db.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")
    convert_model_to_glb(db, model)
    url = geometry_url_for(model)
    return GeometryAsset(
        model_id=model.id,
        available=url is not None,
        status=model.geometry_status,
        url=url,
        error=model.geometry_error,
    )


@router.delete("/{model_id}", response_model=ModelSummary)
def delete_model(model_id: int, db: Session = Depends(get_db)):
    model = db.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")
    deleted = ModelSummary.model_validate(model)
    _unlink_if_exists(model.file_path)
    _unlink_if_exists(model.geometry_path)
    db.delete(model)
    db.commit()
    return deleted


@router.get("/{model_id}/selection-map", response_model=GeometrySelectionMap)
def get_selection_map(model_id: int, db: Session = Depends(get_db)):
    model = db.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")
    elements = db.scalars(select(IfcElement).where(IfcElement.model_id == model_id)).all()
    items: dict[str, int] = {}
    for element in elements:
        keys = _selection_keys(element)
        for key in keys:
            items[key] = element.id
    return GeometrySelectionMap(model_id=model_id, items=items)


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    for index in range(1, 10_000):
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise HTTPException(status_code=500, detail="No se pudo generar nombre unico de archivo")


def _unlink_if_exists(path_value: str | None) -> None:
    if not path_value:
        return
    try:
        path = Path(path_value)
        if path.exists() and path.is_file():
            path.unlink()
    except OSError:
        pass


def _selection_keys(element: IfcElement) -> set[str]:
    keys: set[str] = {str(element.step_id), f"#{element.step_id}"}
    if element.name:
        keys.add(element.name)
        keys.add(_normalize_key(element.name))
    if element.global_id:
        keys.add(element.global_id)
        keys.add(_normalize_key(element.global_id))
        try:
            hex_guid = ifcopenshell.guid.expand(element.global_id)
            uuid = str(UUID(hex=hex_guid))
            keys.update(
                {
                    hex_guid,
                    uuid,
                    f"product-{uuid}-body",
                    f"product-{uuid}",
                    f"product-{hex_guid}-body",
                    f"product-{hex_guid}",
                    _normalize_key(f"product-{uuid}-body"),
                    _normalize_key(f"product-{hex_guid}-body"),
                }
            )
        except Exception:
            pass
    return {key for key in keys if key}


def _normalize_key(value: str) -> str:
    return " ".join(value.strip().lower().split())
