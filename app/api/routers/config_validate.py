"""SenseiConfig validation endpoint."""

from __future__ import annotations

import functools
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field, ValidationError

from app.api.schemas.requests import ValidateConfigRequest
from app.domain.sensei import SenseiConfig

logger = logging.getLogger(__name__)

router = APIRouter(tags=["config"])

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "sensei-config.schema.json"


class ConfigValidationResponse(BaseModel):
    """Sformalizowany model odpowiedzi walidacji konfiguracji."""

    valid: bool = Field(..., description="Czy konfiguracja spełnia wszystkie wymagania")
    pydantic_errors: list[str] = Field(default_factory=list, description="Błędy walidacji domenowej Pydantic")
    schema_errors: list[str] = Field(default_factory=list, description="Błędy zgodności z JSON Schema")


@functools.cache
def _get_json_schema_validator() -> Any | None:
    """Wczytuje i kompiluje walidator JSON Schema tylko raz (Singleton w pamięci)."""
    if not SCHEMA_PATH.is_file():
        logger.warning("Plik schematu nie istnieje: %s", SCHEMA_PATH)
        return None

    try:
        import jsonschema

        raw_schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        # Sprawdzenie poprawności samego schematu i prekompilacja
        jsonschema.Draft202012Validator.check_schema(raw_schema)
        return jsonschema.Draft202012Validator(raw_schema)
    except ImportError:
        logger.error("Biblioteka 'jsonschema' nie jest zainstalowana w środowisku.")
        return None
    except Exception as exc:
        logger.error("Nie udało się załadować schematu JSON z %s: %s", SCHEMA_PATH, exc)
        return None


@router.post(
    "/validate-config",
    response_model=ConfigValidationResponse,
    summary="Walidacja konfiguracji Sensei",
)
async def validate_config(payload: ValidateConfigRequest) -> ConfigValidationResponse:
    """Waliduje SenseiConfig (Pydantic) oraz opcjonalnie JSON Schema z schemas/."""
    pydantic_errors: list[str] = []

    # 1. Walidacja modelem domenowym Pydantic V2
    try:
        SenseiConfig.model_validate(payload.config)
    except ValidationError as exc:
        for err in exc.errors():
            loc = ".".join(str(step) for step in err.get("loc", []))
            pydantic_errors.append(f"{loc}: {err.get('msg')}")

    # 2. Walidacja z użyciem prekompilowanego JSON Schema
    schema_errors: list[str] = []
    validator = _get_json_schema_validator()

    if validator is not None:
        for err in sorted(validator.iter_errors(payload.config), key=lambda e: e.path):
            path = ".".join(str(p) for p in err.path) or "$"
            schema_errors.append(f"{path}: {err.message}")

    is_valid = len(pydantic_errors) == 0 and len(schema_errors) == 0

    return ConfigValidationResponse(
        valid=is_valid,
        pydantic_errors=pydantic_errors,
        schema_errors=schema_errors,
    )