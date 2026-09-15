"""
Live HTTP scenarios for PJA-Sensei AI Module (narrative layers).

Requires:
    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

Run:
    python -m tests.live.test_scenarios
    python -m tests.live.test_scenarios --only 1,4
    python -m tests.live.test_scenarios --group happy,cheat
"""

from __future__ import annotations

import argparse
import asyncio

import httpx

from tests.live.helpers import API_BASE, ScenarioResult
from tests.live.registry import SPECS, parse_groups, parse_only, select_scenarios


async def run_suite(only: list[int]) -> tuple[int, list[ScenarioResult]]:
    results: list[ScenarioResult] = []
    timeout = httpx.Timeout(90.0, connect=10.0)

    async with httpx.AsyncClient(base_url=API_BASE, timeout=timeout) as client:
        try:
            await client.get("/")
        except httpx.ConnectError:
            print(f"Brak połączenia z API pod {API_BASE}. Uruchom najpierw uvicorn.")
            return 1, results

        print(f"=== Live suite ({len(only)} scenariuszy) ===")
        for num in only:
            spec = SPECS[num]
            try:
                result = await spec.fn(client)
            except Exception as exc:
                result = ScenarioResult(num, spec.name, False, f"exception={exc!r}")
                print(f"\n!! S{num} wyjątek: {exc!r}")
            results.append(result)
            status = "SKIP" if result.skipped else ("PASS" if result.passed else "FAIL")
            tags = ",".join(sorted(spec.tags))
            print(f"\n>>> S{result.number} [{status}] {result.name} [{tags}]: {result.details}")

    executed = [r for r in results if not r.skipped]
    failed = [r for r in executed if not r.passed]
    skipped_count = sum(1 for r in results if r.skipped)
    passed_count = sum(1 for r in executed if r.passed)
    print("\n" + "=" * 60)
    print(f"Wynik live: {passed_count}/{len(executed)} PASS" + (f", {skipped_count} SKIP" if skipped_count else ""))
    print("=" * 60)
    return (0 if not failed else 1), results


def main() -> None:
    parser = argparse.ArgumentParser(description="Live narrative scenarios")
    parser.add_argument("--only", default=None, help="Numery, np. 1,4,7")
    parser.add_argument("--group", default=None, help="Tagi: happy,struggle,cheat,edges")
    args = parser.parse_args()
    only = select_scenarios(parse_only(args.only), parse_groups(args.group))
    if not only:
        raise SystemExit("Brak scenariuszy do uruchomienia")
    code, _ = asyncio.run(run_suite(only))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
