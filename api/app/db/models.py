from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Model(Base):
    __tablename__ = "models"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    schema: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="uploaded", nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    geometry_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    geometry_path: Mapped[str | None] = mapped_column(Text)
    geometry_error: Mapped[str | None] = mapped_column(Text)
    element_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    civil_entity_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    elements: Mapped[list["IfcElement"]] = relationship(back_populates="model", cascade="all, delete-orphan")


class IfcElement(Base):
    __tablename__ = "ifc_elements"
    __table_args__ = (
        UniqueConstraint("model_id", "step_id", name="uq_ifc_elements_model_step"),
        Index("ix_ifc_elements_model_class", "model_id", "ifc_class"),
        Index("ix_ifc_elements_global_id", "global_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    step_id: Mapped[int] = mapped_column(Integer, nullable=False)
    global_id: Mapped[str | None] = mapped_column(String(64))
    ifc_class: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str | None] = mapped_column(Text)
    object_type: Mapped[str | None] = mapped_column(Text)
    predefined_type: Mapped[str | None] = mapped_column(Text)
    type_name: Mapped[str | None] = mapped_column(Text)
    level_name: Mapped[str | None] = mapped_column(Text)
    parent_step_id: Mapped[int | None] = mapped_column(Integer)
    is_civil: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    raw_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    model: Mapped["Model"] = relationship(back_populates="elements")


class IfcTreeNode(Base):
    __tablename__ = "ifc_tree_nodes"
    __table_args__ = (Index("ix_ifc_tree_nodes_model_parent", "model_id", "parent_node_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    parent_node_id: Mapped[int | None] = mapped_column(ForeignKey("ifc_tree_nodes.id", ondelete="CASCADE"))
    element_id: Mapped[int | None] = mapped_column(ForeignKey("ifc_elements.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(Text, nullable=False)
    node_type: Mapped[str] = mapped_column(String(64), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class IfcProperty(Base):
    __tablename__ = "ifc_properties"
    __table_args__ = (Index("ix_ifc_properties_lookup", "model_id", "element_id", "pset_name", "property_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    element_id: Mapped[int] = mapped_column(ForeignKey("ifc_elements.id", ondelete="CASCADE"), nullable=False)
    pset_name: Mapped[str] = mapped_column(Text, nullable=False)
    property_name: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)


class IfcQuantity(Base):
    __tablename__ = "ifc_quantities"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    element_id: Mapped[int] = mapped_column(ForeignKey("ifc_elements.id", ondelete="CASCADE"), nullable=False)
    qto_name: Mapped[str] = mapped_column(Text, nullable=False)
    quantity_name: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)


class IfcMaterial(Base):
    __tablename__ = "ifc_materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    element_id: Mapped[int] = mapped_column(ForeignKey("ifc_elements.id", ondelete="CASCADE"), nullable=False)
    material_name: Mapped[str] = mapped_column(Text, nullable=False)


class IfcClassification(Base):
    __tablename__ = "ifc_classifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    element_id: Mapped[int] = mapped_column(ForeignKey("ifc_elements.id", ondelete="CASCADE"), nullable=False)
    system: Mapped[str | None] = mapped_column(Text)
    identification: Mapped[str | None] = mapped_column(Text)
    name: Mapped[str | None] = mapped_column(Text)


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    scope_ifc_class: Mapped[str | None] = mapped_column(String(128))
    target_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    pset_name: Mapped[str | None] = mapped_column(Text)
    field_name: Mapped[str] = mapped_column(Text, nullable=False)
    operator: Mapped[str] = mapped_column(String(32), nullable=False)
    expected_value: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(32), default="warning", nullable=False)
    active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class RuleResult(Base):
    __tablename__ = "rule_results"
    __table_args__ = (Index("ix_rule_results_model_rule", "model_id", "rule_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("rules.id", ondelete="CASCADE"), nullable=False)
    model_id: Mapped[int] = mapped_column(ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    element_id: Mapped[int | None] = mapped_column(ForeignKey("ifc_elements.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    actual_value: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
