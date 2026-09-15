"""Endpoint walidacji konfiguracji SenseiConfig z podwójną weryfikacją (Pydantic + JSON Schema)."""

from __future__ import annotations

import functools
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, ValidationError

from app.api.schemas.requests import ValidateConfigRequest
from app.domain.sensei import SenseiConfig

logger = logging.getLogger(__name__)

router = APIRouter(tags=["config"])

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "sensei-config.schema.json"


class ConfigValidationResponse(BaseModel):
    """Odpowiedź zwracająca status poprawności oraz listy wykrytych błędów."""

    valid: bool = Field(..., description="Czy konfiguracja spełnia wszystkie wymagania")
    pydantic_errors: list[str] = Field(default_factory=list, description="Błędy walidacji modelu domenowego Pydantic")
    schema_errors: list[str] = Field(default_factory=list, description="Błędy zgodności ze specyfikacją JSON Schema")
    schema_unavailable: bool = Field(
        default=False,
        description="True, gdy plik JSON Schema lub biblioteka jsonschema są niedostępne",
    )


@functools.cache
def _get_json_schema_validator() -> Any | None:
    """Wczytuje, kompiluje i keszuje walidator JSON Schema Draft 2020-12 w pamięci procesu."""
    if not SCHEMA_PATH.is_file():
        logger.warning("Plik schematu nie istnieje pod ścieżką: %s", SCHEMA_PATH)
        return None

    try:
        import jsonschema

        raw_schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator.check_schema(raw_schema)
        return jsonschema.Draft202012Validator(raw_schema)
    except ImportError:
        logger.error("Biblioteka 'jsonschema' nie jest zainstalowana w bieżącym środowisku.")
        return None
    except Exception as exc:
        logger.error("Nie udało się załadować schematu JSON z %s: %s", SCHEMA_PATH, exc)
        return None


def _config_as_dict(config_payload: Any) -> Any:
    if hasattr(config_payload, "model_dump"):
        return config_payload.model_dump(by_alias=True, mode="json")
    return config_payload


def collect_pydantic_errors(config_payload: Any) -> list[str]:
    """Sprawdza konfigurację modelem domenowym Pydantic i formatuje błędy."""
    try:
        SenseiConfig.model_validate(config_payload)
        return []
    except ValidationError as exc:
        return [
            f"{'.'.join(str(part) for part in err.get('loc', []))}: {err.get('msg')}"
            for err in exc.errors()
        ]


def collect_json_schema_errors(config_payload: Any) -> tuple[list[str], bool]:
    """Zwraca (błędy schema, schema_unavailable)."""
    validator = _get_json_schema_validator()
    if validator is None:
        return ["JSON Schema validator unavailable (missing file or jsonschema package)"], True

    payload = _config_as_dict(config_payload)
    errors: list[str] = []
    for err in sorted(validator.iter_errors(payload), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in err.path) or "$"
        errors.append(f"{path}: {err.message}")
    return errors, False


def validate_sensei_config_payload(config_payload: Any) -> ConfigValidationResponse:
    """Wspólna walidacja Pydantic + JSON Schema (używana przez /validate-config i start sesji)."""
    pydantic_errors = collect_pydantic_errors(config_payload)
    schema_errors, schema_unavailable = collect_json_schema_errors(config_payload)
    valid = not pydantic_errors and not schema_errors and not schema_unavailable
    return ConfigValidationResponse(
        valid=valid,
        pydantic_errors=pydantic_errors,
        schema_errors=schema_errors,
        schema_unavailable=schema_unavailable,
    )


def assert_sensei_config_valid(config_payload: Any) -> None:
    """Rzuca HTTP 422, gdy konfiguracja nie przechodzi Pydantic lub JSON Schema."""
    result = validate_sensei_config_payload(config_payload)
    if result.valid:
        return
    detail: dict[str, Any] = {
        "message": "Invalid SenseiConfig",
        "pydantic_errors": result.pydantic_errors,
        "schema_errors": result.schema_errors,
    }
    if result.schema_unavailable:
        detail["schema_unavailable"] = True
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


@router.post(
    "/validate-config",
    response_model=ConfigValidationResponse,
    summary="Walidacja konfiguracji Sensei",
)
async def validate_config(payload: ValidateConfigRequest) -> ConfigValidationResponse:
    """Weryfikuje poprawność SenseiConfig za pomocą Pydantic V2 oraz reguł JSON Schema."""
    return validate_sensei_config_payload(payload.config)
