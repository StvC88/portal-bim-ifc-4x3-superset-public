from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import ifcopenshell
import ifcopenshell.util.element
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import (
    IfcClassification,
    IfcElement,
    IfcMaterial,
    IfcProperty,
    IfcQuantity,
    IfcTreeNode,
    Model,
)
from app.services.geometry import convert_model_to_glb


CIVIL_KEYWORDS = (
    "Alignment",
    "Bridge",
    "Road",
    "Rail",
    "Track",
    "Facility",
    "FacilityPart",
    "Referent",
    "Linear",
    "Course",
    "Earthworks",
    "GeographicElement",
)


def extract_model(db: Session, model: Model) -> None:
    model.status = "extracting"
    model.error = None
    db.commit()

    try:
        ifc = ifcopenshell.open(model.file_path)
        model.schema = getattr(ifc, "schema", None)
        metadata = _metadata(ifc)
        step_to_element: dict[int, IfcElement] = {}
        class_counts: Counter[str] = Counter()
        civil_count = 0

        _delete_previous_extraction(db, model.id)

        products = list(ifc.by_type("IfcProduct"))
        for entity in products:
            step_id = entity.id()
            ifc_class = entity.is_a()
            is_civil = _is_civil_entity(ifc_class)
            civil_count += 1 if is_civil else 0
            class_counts[ifc_class] += 1
            element = IfcElement(
                model_id=model.id,
                step_id=step_id,
                global_id=_safe_attr(entity, "GlobalId"),
                ifc_class=ifc_class,
                name=_safe_attr(entity, "Name"),
                object_type=_safe_attr(entity, "ObjectType"),
                predefined_type=_safe_attr(entity, "PredefinedType"),
                type_name=_type_name(entity),
                level_name=_container_name(entity),
                parent_step_id=_container_step_id(entity),
                is_civil=1 if is_civil else 0,
                raw_json={
                    "description": _safe_attr(entity, "Description"),
                    "tag": _safe_attr(entity, "Tag"),
                    "representation": bool(_safe_attr(entity, "Representation")),
                },
            )
            db.add(element)
            db.flush()
            step_to_element[step_id] = element

            _extract_psets(db, model.id, element.id, entity)
            _extract_materials(db, model.id, element.id, entity)
            _extract_classifications(db, model.id, element.id, entity)

        db.flush()
        _build_tree(db, model.id, ifc, step_to_element)

        model.element_count = len(products)
        model.civil_entity_count = civil_count
        model.metadata_json = {
            **metadata,
            "class_counts": dict(class_counts.most_common()),
            "civil_classes": sorted([name for name in class_counts if _is_civil_entity(name)]),
        }
        model.status = "ready"
        db.commit()
        convert_model_to_glb(db, model)
    except Exception as exc:
        db.rollback()
        fresh_model = db.get(Model, model.id)
        if fresh_model:
            fresh_model.status = "error"
            fresh_model.error = str(exc)
            db.commit()
        raise


def _delete_previous_extraction(db: Session, model_id: int) -> None:
    for table in (IfcTreeNode, IfcClassification, IfcMaterial, IfcQuantity, IfcProperty, IfcElement):
        db.execute(delete(table).where(table.model_id == model_id))


def _metadata(ifc: ifcopenshell.file) -> dict[str, Any]:
    projects = ifc.by_type("IfcProject")
    units = []
    if projects:
        unit_assignment = getattr(projects[0], "UnitsInContext", None)
        if unit_assignment:
            for unit in getattr(unit_assignment, "Units", []) or []:
                units.append({"class": unit.is_a(), "name": _safe_attr(unit, "Name"), "unit_type": _safe_attr(unit, "UnitType")})

    contexts = []
    for context in ifc.by_type("IfcGeometricRepresentationContext"):
        contexts.append(
            {
                "context_type": _safe_attr(context, "ContextType"),
                "precision": _safe_attr(context, "Precision"),
                "dimension": _safe_attr(context, "CoordinateSpaceDimension"),
            }
        )

    map_conversions = []
    for conversion in ifc.by_type("IfcMapConversion"):
        map_conversions.append(
            {
                "eastings": _safe_attr(conversion, "Eastings"),
                "northings": _safe_attr(conversion, "Northings"),
                "orthogonal_height": _safe_attr(conversion, "OrthogonalHeight"),
                "x_axis_abscissa": _safe_attr(conversion, "XAxisAbscissa"),
                "x_axis_ordinate": _safe_attr(conversion, "XAxisOrdinate"),
                "scale": _safe_attr(conversion, "Scale"),
            }
        )

    return {
        "project": _safe_attr(projects[0], "Name") if projects else None,
        "units": units,
        "geometric_contexts": contexts,
        "map_conversions": map_conversions,
    }


def _build_tree(db: Session, model_id: int, ifc: ifcopenshell.file, step_to_element: dict[int, IfcElement]) -> None:
    root = IfcTreeNode(model_id=model_id, label="Modelo IFC", node_type="root", sort_order=0)
    db.add(root)
    db.flush()

    spatial_nodes: dict[int, int] = {}
    order = 0
    for spatial_type in ("IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcFacility", "IfcFacilityPart"):
        for spatial in ifc.by_type(spatial_type):
            order += 1
            parent_node_id = root.id
            parent_step = _spatial_parent_step_id(spatial)
            if parent_step and parent_step in spatial_nodes:
                parent_node_id = spatial_nodes[parent_step]
            node = IfcTreeNode(
                model_id=model_id,
                parent_node_id=parent_node_id,
                element_id=step_to_element.get(spatial.id()).id if spatial.id() in step_to_element else None,
                label=f"{spatial.is_a()} | {_safe_attr(spatial, 'Name') or spatial.id()}",
                node_type="spatial",
                sort_order=order,
            )
            db.add(node)
            db.flush()
            spatial_nodes[spatial.id()] = node.id

    class_nodes: dict[str, int] = {}
    grouped = defaultdict(list)
    for element in step_to_element.values():
        grouped[element.ifc_class].append(element)

    for class_name in sorted(grouped):
        order += 1
        node = IfcTreeNode(
            model_id=model_id,
            parent_node_id=root.id,
            label=f"{class_name} ({len(grouped[class_name])})",
            node_type="ifc_class",
            sort_order=order,
        )
        db.add(node)
        db.flush()
        class_nodes[class_name] = node.id

    for class_name, elements in grouped.items():
        parent_node_id = class_nodes[class_name]
        for element in elements:
            order += 1
            db.add(
                IfcTreeNode(
                    model_id=model_id,
                    parent_node_id=parent_node_id,
                    element_id=element.id,
                    label=element.name or element.global_id or f"#{element.step_id}",
                    node_type="element",
                    sort_order=order,
                )
            )


def _extract_psets(db: Session, model_id: int, element_id: int, entity: Any) -> None:
    psets = ifcopenshell.util.element.get_psets(entity, should_inherit=True)
    for pset_name, values in psets.items():
        if not isinstance(values, dict):
            continue
        target_cls = IfcQuantity if pset_name.lower().startswith("qto") else IfcProperty
        for prop_name, raw_value in values.items():
            if prop_name == "id":
                continue
            payload = _json_value(raw_value)
            if target_cls is IfcQuantity:
                db.add(
                    IfcQuantity(
                        model_id=model_id,
                        element_id=element_id,
                        qto_name=pset_name,
                        quantity_name=prop_name,
                        value=_string_value(raw_value),
                        value_json=payload,
                    )
                )
            else:
                db.add(
                    IfcProperty(
                        model_id=model_id,
                        element_id=element_id,
                        pset_name=pset_name,
                        property_name=prop_name,
                        value=_string_value(raw_value),
                        value_json=payload,
                    )
                )


def _extract_materials(db: Session, model_id: int, element_id: int, entity: Any) -> None:
    materials = ifcopenshell.util.element.get_materials(entity, should_inherit=True) or []
    seen = set()
    for material in materials:
        name = _safe_attr(material, "Name") or str(material)
        if name and name not in seen:
            seen.add(name)
            db.add(IfcMaterial(model_id=model_id, element_id=element_id, material_name=name))


def _extract_classifications(db: Session, model_id: int, element_id: int, entity: Any) -> None:
    for rel in getattr(entity, "HasAssociations", []) or []:
        if not rel.is_a("IfcRelAssociatesClassification"):
            continue
        classification = getattr(rel, "RelatingClassification", None)
        if not classification:
            continue
        db.add(
            IfcClassification(
                model_id=model_id,
                element_id=element_id,
                system=_safe_attr(getattr(classification, "ReferencedSource", None), "Name"),
                identification=_safe_attr(classification, "Identification") or _safe_attr(classification, "ItemReference"),
                name=_safe_attr(classification, "Name"),
            )
        )


def _safe_attr(entity: Any, name: str) -> Any:
    try:
        value = getattr(entity, name, None)
    except Exception:
        return None
    if value is None:
        return None
    if hasattr(value, "is_a"):
        return f"{value.is_a()} #{value.id()}"
    return value


def _type_name(entity: Any) -> str | None:
    try:
        type_entity = ifcopenshell.util.element.get_type(entity)
    except Exception:
        return None
    return _safe_attr(type_entity, "Name") if type_entity else None


def _container_name(entity: Any) -> str | None:
    try:
        container = ifcopenshell.util.element.get_container(entity)
    except Exception:
        return None
    return _safe_attr(container, "Name") if container else None


def _container_step_id(entity: Any) -> int | None:
    try:
        container = ifcopenshell.util.element.get_container(entity)
    except Exception:
        return None
    return container.id() if container else None


def _spatial_parent_step_id(entity: Any) -> int | None:
    for rel in getattr(entity, "Decomposes", []) or []:
        parent = getattr(rel, "RelatingObject", None)
        if parent:
            return parent.id()
    return None


def _is_civil_entity(ifc_class: str) -> bool:
    return any(keyword.lower() in ifc_class.lower() for keyword in CIVIL_KEYWORDS)


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return str(value)


def _json_value(value: Any) -> dict[str, Any]:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return {"value": value}
    if isinstance(value, (list, tuple)):
        return {"value": [_string_value(item) for item in value]}
    if isinstance(value, dict):
        return {str(key): _string_value(item) for key, item in value.items()}
    return {"value": _string_value(value)}


def safe_upload_path(upload_dir: Path, filename: str) -> Path:
    cleaned = Path(filename).name.replace(" ", "_")
    return upload_dir / cleaned
