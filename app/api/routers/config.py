import json
from jsonschema import validate, ValidationError as JsonSchemaError
from pydantic import ValidationError as PydanticError
from fastapi import APIRouter
from app.application.dto import ConfigValidationRequest
from app.domain.sensei import SenseiConfig

router = APIRouter(tags=["Config"])


@router.post("/validate-config")
def validate_config(req: ConfigValidationRequest):
    response = {
        "valid": False,
        "schema_unavailable": False,
        "schema_errors": [],
        "pydantic_errors": []
    }

    try:
        with open("schemas/sensei-config.schema.json", "r") as f:
            schema = json.load(f)
        validate(instance=req.config, schema=schema)
    except FileNotFoundError:
        response["schema_unavailable"] = True
        return response
    except JsonSchemaError as e:
        response["schema_errors"].append(e.message)

    try:
        SenseiConfig(**req.config)
    except PydanticError as e:
        response["pydantic_errors"] = e.errors()

    if not response["schema_errors"] and not response["pydantic_errors"]:
        response["valid"] = True

    return response