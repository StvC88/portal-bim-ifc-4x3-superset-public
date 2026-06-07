from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.init_db import init_db, seed_rules
from app.db.session import SessionLocal
from app.routers import assets, dashboards, elements, models, rules, superset

app = FastAPI(title="Portal BIM IFC API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_rules(db)
    finally:
        db.close()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(models.router, prefix="/api")
app.include_router(assets.router, prefix="/api")
app.include_router(elements.router, prefix="/api")
app.include_router(rules.router, prefix="/api")
app.include_router(dashboards.router, prefix="/api")
app.include_router(superset.router, prefix="/api")
