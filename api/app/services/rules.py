from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import IfcClassification, IfcElement, IfcProperty, Model, Rule, RuleResult


def run_rules_for_model(db: Session, model: Model) -> tuple[int, int]:
    db.execute(delete(RuleResult).where(RuleResult.model_id == model.id))
    rules = list(db.scalars(select(Rule).where(Rule.active == 1)).all())
    elements = list(db.scalars(select(IfcElement).where(IfcElement.model_id == model.id)).all())
    created = 0

    for rule in rules:
        candidates = [item for item in elements if not rule.scope_ifc_class or item.ifc_class == rule.scope_ifc_class]
        for element in candidates:
            status, actual, message = evaluate_rule(db, rule, element)
            db.add(
                RuleResult(
                    rule_id=rule.id,
                    model_id=model.id,
                    element_id=element.id,
                    status=status,
                    actual_value=actual,
                    message=message,
                )
            )
            created += 1
    db.commit()
    return len(rules), created


def evaluate_rule(db: Session, rule: Rule, element: IfcElement) -> tuple[str, str | None, str]:
    actual = _actual_value(db, rule, element)
    passed = _compare(rule.operator, actual, rule.expected_value)
    status = "pass" if passed else "fail"
    expected = f" expected '{rule.expected_value}'" if rule.expected_value is not None else ""
    message = f"{rule.name}: {rule.field_name}{expected}; actual '{actual}'"
    return status, actual, message


def _actual_value(db: Session, rule: Rule, element: IfcElement) -> str | None:
    if rule.target_kind == "attribute":
        return str(getattr(element, rule.field_name, None) or "") or None

    if rule.target_kind == "classification":
        rows = db.scalars(
            select(IfcClassification).where(
                IfcClassification.element_id == element.id,
            )
        ).all()
        for row in rows:
            values = [row.system, row.identification, row.name]
            for value in values:
                if value and rule.field_name.lower() in value.lower():
                    return value
        return None

    query = select(IfcProperty).where(
        IfcProperty.element_id == element.id,
        IfcProperty.property_name == rule.field_name,
    )
    if rule.pset_name:
        query = query.where(IfcProperty.pset_name == rule.pset_name)
    prop = db.scalar(query.limit(1))
    return prop.value if prop else None


def _compare(operator: str, actual: str | None, expected: str | None) -> bool:
    if operator == "exists":
        return actual not in (None, "")
    if actual is None:
        return False
    if operator == "equals":
        return actual == (expected or "")
    if operator == "contains":
        return (expected or "").lower() in actual.lower()
    if operator == "in":
        expected_values = [item.strip() for item in (expected or "").split(",")]
        return actual in expected_values
    return False
