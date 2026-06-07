from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Model, Rule, RuleResult
from app.db.session import get_db
from app.schemas import RuleCreate, RuleOut, RuleRunResponse
from app.services.rules import run_rules_for_model

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("", response_model=list[RuleOut])
def list_rules(db: Session = Depends(get_db)):
    return db.scalars(select(Rule).order_by(Rule.created_at.desc())).all()


@router.post("", response_model=RuleOut)
def create_rule(payload: RuleCreate, db: Session = Depends(get_db)):
    rule = Rule(**payload.model_dump(exclude={"active"}), active=1 if payload.active else 0)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.post("/run/{model_id}", response_model=RuleRunResponse)
def run_rules(model_id: int, db: Session = Depends(get_db)):
    model = db.get(Model, model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")
    evaluated, created = run_rules_for_model(db, model)
    return RuleRunResponse(model_id=model_id, evaluated_rules=evaluated, created_results=created)


@router.get("/results/{model_id}")
def get_results(model_id: int, db: Session = Depends(get_db)):
    rows = db.execute(
        select(RuleResult, Rule)
        .join(Rule, Rule.id == RuleResult.rule_id)
        .where(RuleResult.model_id == model_id)
        .order_by(RuleResult.created_at.desc())
    ).all()
    return [
        {
            "id": result.id,
            "rule_id": rule.id,
            "rule_name": rule.name,
            "severity": rule.severity,
            "element_id": result.element_id,
            "status": result.status,
            "message": result.message,
            "actual_value": result.actual_value,
            "created_at": result.created_at,
        }
        for result, rule in rows
    ]
