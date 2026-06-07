from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import IfcClassification, IfcElement, IfcMaterial, IfcProperty, IfcQuantity, IfcTreeNode, Model
from app.db.session import get_db
from app.schemas import ElementDetail, TreeNode

router = APIRouter(tags=["ifc"])


@router.get("/models/{model_id}/tree", response_model=list[TreeNode])
def get_tree(model_id: int, db: Session = Depends(get_db)):
    model = db.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")
    nodes = db.scalars(
        select(IfcTreeNode).where(IfcTreeNode.model_id == model_id).order_by(IfcTreeNode.sort_order)
    ).all()
    by_parent: dict[int | None, list[IfcTreeNode]] = {}
    for node in nodes:
        by_parent.setdefault(node.parent_node_id, []).append(node)

    def build(node: IfcTreeNode) -> TreeNode:
        return TreeNode(
            id=node.id,
            label=node.label,
            node_type=node.node_type,
            element_id=node.element_id,
            children=[build(child) for child in by_parent.get(node.id, [])],
        )

    return [build(node) for node in by_parent.get(None, [])]


@router.get("/elements/{element_id}", response_model=ElementDetail)
def get_element(element_id: int, db: Session = Depends(get_db)):
    element = db.get(IfcElement, element_id)
    if not element:
        raise HTTPException(status_code=404, detail="Elemento no encontrado")

    properties = db.scalars(select(IfcProperty).where(IfcProperty.element_id == element_id)).all()
    quantities = db.scalars(select(IfcQuantity).where(IfcQuantity.element_id == element_id)).all()
    materials = db.scalars(select(IfcMaterial).where(IfcMaterial.element_id == element_id)).all()
    classifications = db.scalars(select(IfcClassification).where(IfcClassification.element_id == element_id)).all()

    return ElementDetail(
        id=element.id,
        model_id=element.model_id,
        step_id=element.step_id,
        global_id=element.global_id,
        ifc_class=element.ifc_class,
        name=element.name,
        object_type=element.object_type,
        predefined_type=element.predefined_type,
        type_name=element.type_name,
        level_name=element.level_name,
        is_civil=bool(element.is_civil),
        raw_json=element.raw_json,
        properties=[
            {"pset": prop.pset_name, "name": prop.property_name, "value": prop.value, "raw": prop.value_json}
            for prop in properties
        ],
        quantities=[
            {"qto": qto.qto_name, "name": qto.quantity_name, "value": qto.value, "raw": qto.value_json}
            for qto in quantities
        ],
        materials=[item.material_name for item in materials],
        classifications=[
            {"system": item.system, "identification": item.identification, "name": item.name}
            for item in classifications
        ],
    )
