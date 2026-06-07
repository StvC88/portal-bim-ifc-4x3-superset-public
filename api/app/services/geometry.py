from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import Model


def convert_model_to_glb(db: Session, model: Model) -> None:
    settings = get_settings()
    converter = shutil.which("IfcConvert")
    model.geometry_status = "converting"
    model.geometry_error = None
    db.commit()

    if not converter:
        model.geometry_status = "error"
        model.geometry_error = "IfcConvert no esta instalado en el contenedor."
        db.commit()
        return

    output_path = settings.converted_dir / f"model_{model.id}.glb"
    command = [
        converter,
        model.file_path,
        str(output_path),
    ]

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=1800, check=False)
        if result.returncode != 0 or not output_path.exists():
            model.geometry_status = "error"
            model.geometry_error = (result.stderr or result.stdout or "IfcConvert no genero archivo GLB.").strip()[:4000]
        else:
            model.geometry_status = "ready"
            model.geometry_path = str(output_path)
            model.geometry_error = None
        db.commit()
    except Exception as exc:
        model.geometry_status = "error"
        model.geometry_error = str(exc)
        db.commit()


def geometry_url_for(model: Model) -> str | None:
    if model.geometry_status != "ready" or not model.geometry_path:
        return None
    path = Path(model.geometry_path)
    if not path.exists():
        return None
    return f"/api/assets/geometry/{path.name}"
