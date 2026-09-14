"""Export OpenAPI from the running app factory to schemas/ (JSON + YAML)."""

from __future__ import annotations

import json
from pathlib import Path


def dump_yaml(obj, indent: int = 0) -> str:
    """Minimal YAML dump (no PyYAML dependency)."""
    sp = "  " * indent
    if isinstance(obj, dict):
        lines: list[str] = []
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{sp}{key}:")
                lines.append(dump_yaml(value, indent + 1))
            elif isinstance(value, str):
                lines.append(f"{sp}{key}: {json.dumps(value, ensure_ascii=False)}")
            elif value is None:
                lines.append(f"{sp}{key}: null")
            elif isinstance(value, bool):
                lines.append(f"{sp}{key}: {str(value).lower()}")
            else:
                lines.append(f"{sp}{key}: {value}")
        return "\n".join(lines)
    if isinstance(obj, list):
        lines = []
        for item in obj:
            if isinstance(item, (dict, list)):
                lines.append(f"{sp}-")
                lines.append(dump_yaml(item, indent + 1))
            else:
                lines.append(f"{sp}- {json.dumps(item, ensure_ascii=False)}")
        return "\n".join(lines)
    return f"{sp}{json.dumps(obj, ensure_ascii=False)}"


def main() -> None:
    """Buduje FastAPI app i zapisuje openapi.json oraz openapi.yaml do schemas/."""
    from app.main import create_app

    root = Path(__file__).resolve().parents[1]
    json_path = root / "schemas" / "openapi.json"
    yaml_path = root / "schemas" / "openapi.yaml"

    spec = create_app().openapi()
    json_path.write_text(
        json.dumps(spec, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    yaml_path.write_text(dump_yaml(spec) + "\n", encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {yaml_path}")
    print(f"Paths: {len(spec.get('paths') or {})}")


if __name__ == "__main__":
    main()
