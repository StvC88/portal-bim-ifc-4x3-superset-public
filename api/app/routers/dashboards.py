from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import IfcElement, IfcMaterial, IfcProperty, IfcQuantity, Model, RuleResult
from app.db.session import get_db
from app.schemas import StandardDashboardModule, StandardRoadDashboard

router = APIRouter(prefix="/dashboards", tags=["dashboards"])

MODULES = [
    {"key": "spatial_alignment", "title": "Estructura espacial y alineaciones", "description": "IfcProject, IfcSite, IfcRoad, IfcRoadPart e IfcAlignment para controlar trazado horizontal y vertical.", "patterns": ("Alignment", "Road", "FacilityPart", "Facility")},
    {"key": "sections_courses", "title": "Secciones transversales y capas", "description": "Capas de pavimento, materiales, espesores y elementos auxiliares como IfcCourse e IfcKerb.", "patterns": ("Course", "Kerb", "Pavement")},
    {"key": "earthworks", "title": "Geotecnia y movimiento de tierras", "description": "Terreno, desmonte, terraplen, taludes, estratigrafia y volumenes de obra lineal.", "patterns": ("Earth", "Geomodel", "GeographicElement", "Geotechnical", "Terrain")},
    {"key": "structures_drainage", "title": "Obras de fabrica y drenaje", "description": "Puentes, estructuras, drenaje transversal/longitudinal, tuberias, alcantarillas y sumideros.", "patterns": ("Bridge", "Pipe", "DistributionChamber", "Culvert", "Drain")},
    {"key": "psets_qtos", "title": "Propiedades no geometricas y metadatos", "description": "Psets, QtoSets, codigos presupuestarios, vida util, fabricante, estado y cantidades.", "patterns": ()},
    {"key": "gis_linear_reference", "title": "Integracion GIS y ubicacion lineal", "description": "Georreferenciacion, CRS, IfcMapConversion y consulta por PK o referencia lineal cuando exista.", "patterns": ("Referent", "PositioningElement", "Linear")},
]

@router.get("/standard-road", response_model=StandardRoadDashboard)
def standard_road_dashboard_multi(model_ids: list[int] = Query(default=[]), db: Session = Depends(get_db)):
    if not model_ids:
        return _build_dashboard(db, [])
    models = db.scalars(select(Model).where(Model.id.in_(model_ids))).all()
    missing = set(model_ids) - {model.id for model in models}
    if missing:
        raise HTTPException(status_code=404, detail=f"Modelos no encontrados: {sorted(missing)}")
    return _build_dashboard(db, models)

@router.get("/standard-road/{model_id}", response_model=StandardRoadDashboard)
def standard_road_dashboard(model_id: int, db: Session = Depends(get_db)):
    model = db.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")
    return _build_dashboard(db, [model])

# ...rest of file omitted for brevity in public mirror bootstrap
