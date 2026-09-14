"""
Live HTTP scenarios for PJA-Sensei AI Module.

Requires a running API:
    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

Run:
    python -m tests.live.test_scenarios
    python -m tests.live.test_scenarios --only 3,6,23
    python -m tests.live.test_scenarios --group roi,gates
    python -m tests.live.test_all
"""

from __future__ import annotations

import argparse
import asyncio

import httpx

from tests.live.helpers import API_BASE, ScenarioResult
from tests.live.registry import (
    SPECS,
    parse_groups,
    parse_only,
    select_scenarios,
)


async def run_suite(only: list[int]) -> tuple[int, list[ScenarioResult]]:
    results: list[ScenarioResult] = []
    timeout = httpx.Timeout(90.0, connect=10.0)

    async with httpx.AsyncClient(base_url=API_BASE, timeout=timeout) as client:
        try:
            await client.get("/")
        except httpx.ConnectError:
            print(f"Brak połączenia z API pod {API_BASE}. Uruchom najpierw uvicorn.")
            return 1, results

        print(f"=== Start suite PJA-Sensei ({len(only)} scenariuszy) ===")
        for num in only:
            spec = SPECS[num]
            try:
                result = await spec.fn(client)
            except Exception as exc:
                result = ScenarioResult(
                    num, spec.name, False, f"exception={exc!r}"
                )
                print(f"\n!! Scenariusz {num} wyjątek: {exc!r}")
            results.append(result)
            if result.skipped:
                status = "SKIP"
            else:
                status = "PASS" if result.passed else "FAIL"
            tags = ",".join(sorted(spec.tags))
            print(
                f"\n>>> S{result.number} [{status}] {result.name} "
                f"[{tags}]: {result.details}"
            )

    print("\n" + "=" * 60)
    print(f"PODSUMOWANIE LIVE (wybrane z S1-S{max(SPECS)})")
    print("=" * 60)
    executed = [r for r in results if not r.skipped]
    skipped_count = sum(1 for r in results if r.skipped)
    passed_count = sum(1 for r in executed if r.passed)
    failed = [r for r in executed if not r.passed]
    for r in results:
        if r.skipped:
            mark = "SKIP"
        else:
            mark = "PASS" if r.passed else "FAIL"
        print(f"  [{mark}] live:S{r.number} {r.name} — {r.details}")
    print("-" * 60)
    skip_note = f", {skipped_count} SKIP" if skipped_count else ""
    print(f"Wynik live: {passed_count}/{len(executed)} PASS{skip_note}")
    print("=" * 60)
    return (0 if not failed else 1), results


def main() -> None:
    parser = argparse.ArgumentParser(description="Suite scenariuszy PJA-Sensei")
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="Numery scenariuszy po przecinku, np. 3,6,25",
    )
    parser.add_argument(
        "--group",
        type=str,
        default=None,
        help="Tagi po przecinku: pedagogy,contract,gates,roi,edge",
    )
    args = parser.parse_args()
    only = parse_only(args.only)
    groups = parse_groups(args.group)
    selected = select_scenarios(only, groups)
    if not selected:
        raise SystemExit("Brak scenariuszy po filtrach --only/--group")
    code, _ = asyncio.run(run_suite(selected))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
