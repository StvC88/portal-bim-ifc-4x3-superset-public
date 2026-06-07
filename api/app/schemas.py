from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ModelSummary(BaseModel):
    id: int
    name: str
    original_filename: str
    schema_: str | None = Field(alias="schema")
    status: str
    error: str | None
    geometry_status: str
    geometry_path: str | None
    geometry_error: str | None
    element_count: int
    civil_entity_count: int
    metadata_json: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class TreeNode(BaseModel):
    id: int
    label: str
    node_type: str
    element_id: int | None = None
    children: list["TreeNode"] = []


class ElementDetail(BaseModel):
    id: int
    model_id: int
    step_id: int
    global_id: str | None
    ifc_class: str
    name: str | None
    object_type: str | None
    predefined_type: str | None
    type_name: str | None
    level_name: str | None
    is_civil: bool
    raw_json: dict[str, Any]
    properties: list[dict[str, Any]]
    quantities: list[dict[str, Any]]
    materials: list[str]
    classifications: list[dict[str, Any]]


class RuleCreate(BaseModel):
    name: str
    scope_ifc_class: str | None = None
    target_kind: Literal["property", "classification", "attribute"] = "property"
    pset_name: str | None = None
    field_name: str
    operator: Literal["exists", "equals", "contains", "in"] = "exists"
    expected_value: str | None = None
    severity: Literal["info", "warning", "error"] = "warning"
    active: bool = True


class RuleOut(RuleCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class RuleRunResponse(BaseModel):
    model_id: int
    evaluated_rules: int
    created_results: int


class SupersetEmbedConfig(BaseModel):
    superset_domain: str
    dashboard_id: str | None
    guest_token: str | None
    available: bool
    message: str


class GeometryAsset(BaseModel):
    model_id: int
    available: bool
    status: str
    url: str | None
    error: str | None


class GeometrySelectionMap(BaseModel):
    model_id: int
    items: dict[str, int]


class StandardDashboardModule(BaseModel):
    key: str
    title: str
    description: str
    element_count: int
    property_count: int
    quantity_count: int
    material_count: int
    classes: list[dict[str, Any]]


class StandardRoadDashboard(BaseModel):
    model_id: int
    model_ids: list[int] = []
    model_name: str
    schema_: str | None = Field(alias="schema")
    totals: dict[str, Any]
    georeferencing: dict[str, Any]
    units: list[dict[str, Any]]
    modules: list[StandardDashboardModule]
    rule_summary: dict[str, int]

    class Config:
        populate_by_name = True
