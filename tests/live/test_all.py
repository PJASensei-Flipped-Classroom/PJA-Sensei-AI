"""
Unified test entrypoint for PJA-Sensei AI Module.

Runs:
  1) Offline: pytest (tests/) + code-penalty unit checks
  2) Live HTTP suite (S1–S24) when the API is up

Usage:
    .venv\\Scripts\\python.exe -m tests.live.test_all
    python -m tests.live.test_all
    python -m tests.live.test_all --offline-only
    python -m tests.live.test_all --require-live
    python -m tests.live.test_all --only 14,15,23,24
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
    """Return project .venv interpreter if it exists."""
    candidates = [
        ROOT / ".venv" / "Scripts" / "python.exe",  # Windows
        ROOT / ".venv" / "bin" / "python",  # Unix
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def _ensure_project_venv() -> None:
    """Re-exec under .venv when current interpreter lacks app deps (e.g. openai)."""
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

from app.application.response_pipeline import contains_revealed_code
from tests.live.test_memory import API_BASE, SCENARIOS, parse_only, run_suite


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
    results: list[BlockResult] = []

    # --- unit: code penalty (smoke; full matrix via pytest below) ---
    try:
        assert contains_revealed_code(
            "Rozważ adnotację @RestController nad klasą."
        ) is False
        assert contains_revealed_code(
            """```java
public class HelloController {
    public String hello() { return "hi"; }
}
```"""
        ) is True
        assert contains_revealed_code(
            """
public String hello() {
    return new ResponseEntity<>(body, HttpStatus.OK);
}
private void helper() {
    if (x) {
        return;
    }
}
"""
        ) is True
        results.append(
            BlockResult("unit:code_penalty", True, "contains_revealed_code OK")
        )
        print("[PASS] offline unit:code_penalty")
    except Exception as exc:
        results.append(BlockResult("unit:code_penalty", False, str(exc)))
        print(f"[FAIL] offline unit:code_penalty — {exc}")

    # --- pytest: tests/ (prefer project venv) ---
    py = resolve_pytest_python()
    if Path(py).resolve() != Path(sys.executable).resolve():
        print(f"(pytest interpreter: {py})")
    cmd = [
        py,
        "-m",
        "pytest",
        "-q",
        str(ROOT / "tests"),
    ]
    print(f"\n>>> Offline pytest: {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    tail = "\n".join(out.strip().splitlines()[-8:]) if out.strip() else "(no output)"
    ok = proc.returncode == 0
    if not ok and "No module named" in out:
        tail = (
            "Brak zależności w interpreterze pytest. "
            "Użyj: .venv\\Scripts\\python.exe -m tests.live.test_all "
            f"| {tail}"
        )
    results.append(
        BlockResult(
            "pytest:tests/",
            ok,
            f"exit={proc.returncode}; {tail.replace(chr(10), ' | ')}",
        )
    )
    print(f"[{'PASS' if ok else 'FAIL'}] offline pytest:tests/")
    if not ok:
        print(out)
    return results


async def api_is_up() -> bool:
    try:
        async with httpx.AsyncClient(base_url=API_BASE, timeout=3.0) as client:
            r = await client.get("/health")
            return r.status_code == 200
    except Exception:
        return False


async def run_live_block(only: list[int], require_live: bool) -> list[BlockResult]:
    up = await api_is_up()
    if not up:
        msg = f"API niedostępne pod {API_BASE}"
        if require_live:
            print(f"[FAIL] live skipped — {msg} (--require-live)")
            return [BlockResult("live:suite", False, msg)]
        print(f"[SKIP] live suite — {msg} (uruchom uvicorn lub użyj --require-live)")
        return [BlockResult("live:suite", True, msg, skipped=True)]

    print("\n>>> Live HTTP suite")
    code, scenario_results = await run_suite(only)
    blocks = [
        BlockResult(
            f"live:S{r.number}:{r.name}",
            r.passed,
            r.details,
        )
        for r in scenario_results
    ]
    if not scenario_results and code != 0:
        blocks.append(BlockResult("live:suite", False, "suite failed to start"))
    return blocks


def print_summary(blocks: list[BlockResult]) -> int:
    print("\n" + "=" * 60)
    print(f"PODSUMOWANIE test_all (offline + live S1-S{max(SCENARIOS)})")
    print("=" * 60)
    offline = [b for b in blocks if b.name.startswith(("unit:", "pytest:"))]
    live = [b for b in blocks if b.name.startswith("live:")]
    executed = [b for b in blocks if not b.skipped]
    skipped = [b for b in blocks if b.skipped]
    passed = sum(1 for b in executed if b.passed)

    def _section(title: str, items: list[BlockResult]) -> None:
        if not items:
            return
        print(f"\n-- {title} --")
        for b in items:
            if b.skipped:
                mark = "SKIP"
            else:
                mark = "PASS" if b.passed else "FAIL"
            print(f"  [{mark}] {b.name} — {b.details}")

    _section("OFFLINE", offline)
    _section("LIVE", live)
    print("-" * 60)
    print(
        f"Wynik: {passed}/{len(executed)} PASS"
        + (f", {len(skipped)} SKIP" if skipped else "")
    )
    print("=" * 60)
    failed = [b for b in executed if not b.passed]
    return 0 if not failed else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pełny suite PJA-Sensei (offline + live)"
    )
    parser.add_argument(
        "--offline-only",
        action="store_true",
        help="Tylko pytest + unit (bez HTTP live)",
    )
    parser.add_argument(
        "--require-live",
        action="store_true",
        help="FAIL jeśli API nie działa (domyślnie SKIP live)",
    )
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Numery scenariuszy live, np. 14,15,16 (przekazywane do test_memory)",
    )
    args = parser.parse_args()

    print("=== PJA-Sensei test_all ===")
    blocks: list[BlockResult] = []
    blocks.extend(run_offline_block())

    if not args.offline_only:
        only = parse_only(args.only)
        blocks.extend(asyncio.run(run_live_block(only, args.require_live)))
    else:
        print("\n[SKIP] live suite — --offline-only")
        blocks.append(
            BlockResult("live:suite", True, "--offline-only", skipped=True)
        )

    raise SystemExit(print_summary(blocks))


if __name__ == "__main__":
    main()
