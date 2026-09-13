"""Dump OpenAPI JSON to a simple YAML snapshot (no PyYAML dependency)."""
from __future__ import annotations

import json
from pathlib import Path


def dump(obj, indent: int = 0) -> str:
    sp = "  " * indent
    if isinstance(obj, dict):
        lines: list[str] = []
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{sp}{key}:")
                lines.append(dump(value, indent + 1))
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
                lines.append(dump(item, indent + 1))
            else:
                lines.append(f"{sp}- {json.dumps(item, ensure_ascii=False)}")
        return "\n".join(lines)
    return f"{sp}{json.dumps(obj, ensure_ascii=False)}"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    src = root / "schemas" / "openapi.json"
    dst = root / "schemas" / "openapi.yaml"
    spec = json.loads(src.read_text(encoding="utf-8"))
    dst.write_text(dump(spec) + "\n", encoding="utf-8")
    print(f"Wrote {dst}")


if __name__ == "__main__":
    main()
