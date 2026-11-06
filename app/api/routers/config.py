import json
from pathlib import Path
from typing import Dict, Any

from jsonschema import validate, ValidationError as JsonSchemaError
from pydantic import ValidationError as PydanticError
from fastapi import APIRouter
from app.application.config_dry_run import run_config_dry_run
from app.application.dto import ConfigValidationRequest, ConversationStartRequest
from app.domain.sensei import SenseiConfig

router = APIRouter(tags=["config"])

_SCHEMA_PATH = Path(__file__).resolve().parents[3] / "schemas" / "sensei-config.schema.json"

@router.get("/config/schema")
def get_config_schema() -> Dict[str, Any]:
    return SenseiConfig.model_json_schema()

@router.get("/config/presets")
def get_config_presets() -> Dict[str, Any]:
    return {
        "presets": [
            {
                "id": "spring-rest-pl",
                "name": "Spring Boot REST API (PL)",
                "config": {
                    "language": "pl",
                    "evaluationCriteria": "Poprawna implementacja kontrolera REST w Spring Boot",
                    "referenceMaterials": [
                        {
                            "title": "Spring REST Guide",
                            "link": "https://spring.io/guides/gs/rest-service",
                            "content": "Adnotacja @RestController łączy @Controller oraz @ResponseBody, a @GetMapping mapuje żądania HTTP GET.",
                        }
                    ],
                    "learningContext": {
                        "goals": [
                            {"id": "g1", "description": "Utworzenie klasy z adnotacją @RestController"},
                            {"id": "g2", "description": "Dodanie metody z adnotacją @GetMapping"},
                        ]
                    },
                    "checkpoints": [
                        {"id": "cp1", "afterGoal": "g1", "hint": "Dodaj teraz metodę z @GetMapping('/hello')."},
                        {"id": "cp2", "afterGoal": "g2", "hint": "Świetnie! Wszystkie cele laboratorium ukończone."},
                    ],
                    "hints": [
                        "Pamiętaj o zaimportowaniu org.springframework.web.bind.annotation.RestController.",
                        "Metoda obsługująca GET powinna zwracać obiekt lub String i mieć adnotację @GetMapping.",
                    ],
                    "maxHints": 2,
                    "frustrationThreshold": 2,
                    # OLD: "requireFileContext": False,
                    # Removed because: gate flags belong under ideRestrictions (legacy top-level still migrates).
                    "ideRestrictions": {"requireFileContext": False},
                    "agentPersona": {"name": "PJA-Sensei", "tone": "sokratyczny i wspierający"},
                    "agentBehavior": {"mode": "theory"},
                    "preLab": {
                        "enabled": True,
                        "question": "Jaka adnotacja w Spring Boot oznacza klasę kontrolera REST?",
                        "expectedKeywords": ["RestController"],
                        "questions": [
                            {
                                "id": "q1",
                                "question": "Jaka adnotacja w Spring Boot oznacza klasę kontrolera REST?",
                                "expectedKeywords": ["RestController"],
                            }
                        ],
                    },
                },
            }
        ]
    }

# OLD:
# @router.post("/validate-config")
# @router.post("/config/validate-config")
# @router.post("/config/validate")
# Removed because: three aliases for one handler; UI/tests use /validate-config only.
@router.post("/validate-config")
def validate_config(req: ConfigValidationRequest):
    response = {
        "valid": False,
        "schema_unavailable": False,
        "schema_errors": [],
        "pydantic_errors": []
    }

    try:
        with _SCHEMA_PATH.open("r", encoding="utf-8") as f:
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


@router.post("/config/dry-run")
def config_dry_run(req: ConversationStartRequest):
    """Simulate student path (prelab/gates/security/hints) without calling the LLM."""
    return run_config_dry_run(req.config)