"""SenseiConfig validation endpoint."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter
from pydantic import ValidationError

from app.api.schemas.requests import ValidateConfigRequest
from app.domain.sensei import SenseiConfig

router = APIRouter(tags=["config"])

SCHEMA_PATH = (
    Path(__file__).resolve().parents[3] / "schemas" / "sensei-config.schema.json"
)


@router.post("/validate-config")
async def validate_config(payload: ValidateConfigRequest):
    errors: list[str] = []
    try:
        SenseiConfig.model_validate(payload.config)
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            errors.append(f"{loc}: {err.get('msg')}")

    schema_errors: list[str] = []
    if SCHEMA_PATH.exists():
        try:
            import jsonschema

            schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
            validator = jsonschema.Draft202012Validator(schema)
            for err in sorted(validator.iter_errors(payload.config), key=str):
                path = ".".join(str(p) for p in err.path) or "$"
                schema_errors.append(f"{path}: {err.message}")
        except ImportError:
            schema_errors.append("jsonschema not installed; skipped schema check")
        except Exception as exc:
            schema_errors.append(f"schema validation error: {exc}")

    valid = not errors and not any(
        e for e in schema_errors if not e.startswith("jsonschema not installed")
    )
    return {
        "valid": valid and not errors,
        "pydantic_errors": errors,
        "schema_errors": schema_errors,
    }
