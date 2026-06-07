from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import Rule
from app.db.session import Base, engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE models ADD COLUMN IF NOT EXISTS geometry_status VARCHAR(32) NOT NULL DEFAULT 'pending'"))
        conn.execute(text("ALTER TABLE models ADD COLUMN IF NOT EXISTS geometry_path TEXT"))
        conn.execute(text("ALTER TABLE models ADD COLUMN IF NOT EXISTS geometry_error TEXT"))
        conn.execute(
            text(
                """
                CREATE OR REPLACE VIEW v_ifc_class_summary AS
                SELECT
                    m.id AS model_id,
                    m.name AS model_name,
                    e.ifc_class,
                    e.level_name,
                    COUNT(*) AS element_count,
                    SUM(e.is_civil) AS civil_entity_count
                FROM models m
                JOIN ifc_elements e ON e.model_id = m.id
                GROUP BY m.id, m.name, e.ifc_class, e.level_name
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE OR REPLACE VIEW v_rule_result_summary AS
                SELECT
                    m.id AS model_id,
                    m.name AS model_name,
                    r.name AS rule_name,
                    r.severity,
                    rr.status,
                    e.ifc_class,
                    e.level_name,
                    COUNT(*) AS result_count
                FROM rule_results rr
                JOIN rules r ON r.id = rr.rule_id
                JOIN models m ON m.id = rr.model_id
                LEFT JOIN ifc_elements e ON e.id = rr.element_id
                GROUP BY m.id, m.name, r.name, r.severity, rr.status, e.ifc_class, e.level_name
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE OR REPLACE VIEW v_road_ifc4x3_standard_dashboard AS
                SELECT
                    m.id AS model_id,
                    m.name AS model_name,
                    CASE
                        WHEN e.ifc_class ILIKE '%Alignment%' THEN '01 Alineaciones'
                        WHEN e.ifc_class ILIKE '%Road%' OR e.ifc_class ILIKE '%FacilityPart%' THEN '02 Estructura espacial vial'
                        WHEN e.ifc_class ILIKE '%Course%' OR e.ifc_class ILIKE '%Kerb%' THEN '03 Secciones y capas'
                        WHEN e.ifc_class ILIKE '%Earth%' OR e.ifc_class ILIKE '%Geomodel%' OR e.ifc_class ILIKE '%GeographicElement%' THEN '04 Geotecnia y tierras'
                        WHEN e.ifc_class ILIKE '%Bridge%' OR e.ifc_class ILIKE '%Pipe%' OR e.ifc_class ILIKE '%DistributionChamber%' THEN '05 Obras de fabrica y drenaje'
                        ELSE '06 Otros elementos IFC'
                    END AS dashboard_module,
                    e.ifc_class,
                    e.level_name,
                    COUNT(*) AS element_count,
                    COUNT(DISTINCT p.property_name) AS property_count,
                    COUNT(DISTINCT q.quantity_name) AS quantity_count,
                    COUNT(DISTINCT mat.material_name) AS material_count,
                    SUM(e.is_civil) AS civil_entity_count
                FROM models m
                JOIN ifc_elements e ON e.model_id = m.id
                LEFT JOIN ifc_properties p ON p.element_id = e.id
                LEFT JOIN ifc_quantities q ON q.element_id = e.id
                LEFT JOIN ifc_materials mat ON mat.element_id = e.id
                GROUP BY m.id, m.name, dashboard_module, e.ifc_class, e.level_name
                """
            )
        )


def seed_rules(db: Session) -> None:
    existing = db.scalar(select(Rule).where(Rule.name == "RCEclass requerido"))
    if existing:
        return
    db.add(
        Rule(
            name="RCEclass requerido",
            scope_ifc_class=None,
            target_kind="property",
            pset_name=None,
            field_name="RCEclass",
            operator="exists",
            expected_value=None,
            severity="warning",
            active=1,
        )
    )
    db.commit()
