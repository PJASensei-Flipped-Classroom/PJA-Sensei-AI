"""
Unified test entrypoint for PJA-Sensei AI Module.

Runs:
  1) Offline: pytest (tests/) — warstwy happy / struggle / cheat / edges
  2) Live HTTP suite (S1–S9) when the API is up

Usage:
    python -m tests.live.test_all
    python -m tests.live.test_all --offline-only
    python -m tests.live.test_all --require-live
    python -m tests.live.test_all --only 1,4,7
    python -m tests.live.test_all --group happy,cheat
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def project_python() -> Path | None:
    candidates = [
        ROOT / ".venv" / "Scripts" / "python.exe",
        ROOT / ".venv" / "bin" / "python",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def _ensure_project_venv() -> None:
    if os.environ.get("PJA_TEST_ALL_VENV") == "1":
        return
    venv_py = project_python()
    if venv_py is None:
        return
    if Path(sys.executable).resolve() == venv_py.resolve():
        return
    try:
        import openai  # noqa: F401
        import httpx  # noqa: F401
    except ImportError:
        env = {**os.environ, "PJA_TEST_ALL_VENV": "1"}
        print(
            f"Uwaga: uruchamiam ponownie w venv:\n  {venv_py}\n"
            f"(bieżący interpreter nie ma zależności projektu: {sys.executable})"
        )
        raise SystemExit(
            subprocess.call(
                [str(venv_py), "-m", "tests.live.test_all", *sys.argv[1:]], env=env
            )
        )


_ensure_project_venv()

import httpx

from tests.live.helpers import API_BASE
from tests.live.registry import parse_groups, parse_only, select_scenarios
from tests.live.test_scenarios import run_suite


def resolve_pytest_python() -> str:
    venv_py = project_python()
    return str(venv_py) if venv_py is not None else sys.executable


@dataclass
class BlockResult:
    name: str
    passed: bool
    details: str
    skipped: bool = False


def run_offline_block() -> list[BlockResult]:
    py = resolve_pytest_python()
    proc = subprocess.run(
        [py, "-m", "pytest", "-q", str(ROOT / "tests")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    tail = "\n".join(out.strip().splitlines()[-8:]) if out.strip() else "(no output)"
    return [
        BlockResult(
            "offline pytest (happy/struggle/cheat/edges)",
            proc.returncode == 0,
            tail,
        )
    ]


async def run_live_block(
    *,
    require_live: bool,
    only: list[int] | None,
    groups: frozenset[str] | None,
) -> BlockResult:
    nums = select_scenarios(only, groups)
    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=5.0) as client:
            health = await client.get("/health")
            if health.status_code != 200:
                raise httpx.ConnectError("health not 200")
    except Exception as exc:
        if require_live:
            return BlockResult("live", False, f"API niedostępne: {exc}")
        return BlockResult("live", True, f"SKIP — API niedostępne ({exc})", skipped=True)

    code, results = await run_suite(nums)
    failed = [r for r in results if not r.skipped and not r.passed]
    details = f"{len(results)} scenariuszy; failed={len(failed)}"
    return BlockResult("live", code == 0, details)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--offline-only", action="store_true")
    parser.add_argument("--require-live", action="store_true")
    parser.add_argument("--only", default=None)
    parser.add_argument("--group", default=None)
    args = parser.parse_args()

    blocks = run_offline_block()
    if not args.offline_only:
        live = asyncio.run(
            run_live_block(
                require_live=args.require_live,
                only=parse_only(args.only),
                groups=parse_groups(args.group),
            )
        )
        blocks.append(live)

    print("\n" + "=" * 60)
    print("PODSUMOWANIE test_all")
    print("=" * 60)
    for b in blocks:
        mark = "SKIP" if b.skipped else ("PASS" if b.passed else "FAIL")
        print(f"  [{mark}] {b.name}: {b.details}")
    print("=" * 60)

    hard_fail = [b for b in blocks if not b.passed and not b.skipped]
    raise SystemExit(1 if hard_fail else 0)


if __name__ == "__main__":
    main()
