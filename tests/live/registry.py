"""Live scenario registry — narrative layers: happy, struggle, cheat, edges."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx

from tests.live.helpers import ScenarioResult
from tests.live.scenarios import cheat, edges, happy, struggle

ScenarioFn = Callable[[httpx.AsyncClient], Awaitable[ScenarioResult]]

ALLOWED_TAGS = frozenset({"happy", "struggle", "cheat", "edges"})


@dataclass(frozen=True)
class ScenarioSpec:
    number: int
    name: str
    tags: frozenset[str]
    fn: ScenarioFn


SPECS: dict[int, ScenarioSpec] = {
    1: ScenarioSpec(1, "Student przechodzi lab od startu do końca", frozenset({"happy"}), happy.full_lab),
    2: ScenarioSpec(2, "Student utyka i bierze reveal", frozenset({"struggle"}), struggle.reveal_after_low_scores),
    3: ScenarioSpec(3, "Student w theory bez pliku", frozenset({"struggle"}), struggle.theory_without_file),
    4: ScenarioSpec(4, "Student próbuje jailbreak", frozenset({"cheat"}), cheat.jailbreak),
    5: ScenarioSpec(5, "Student żąda gotowca", frozenset({"cheat"}), cheat.full_code_dump),
    6: ScenarioSpec(6, "Student bez prelab — chat zablokowany", frozenset({"cheat", "edges"}), cheat.prelab_blocks_chat),
    7: ScenarioSpec(7, "Health + validate-config", frozenset({"edges"}), edges.health_and_validate),
    8: ScenarioSpec(8, "Unknown conversation 404", frozenset({"edges"}), edges.unknown_404),
    9: ScenarioSpec(9, "Token budget 403", frozenset({"edges"}), edges.token_budget),
}


def parse_only(raw: str | None) -> list[int] | None:
    if not raw:
        return None
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


def parse_groups(raw: str | None) -> frozenset[str] | None:
    if not raw:
        return None
    tags = frozenset(t.strip() for t in raw.split(",") if t.strip())
    unknown = tags - ALLOWED_TAGS
    if unknown:
        raise SystemExit(f"Nieznane tagi: {sorted(unknown)}; dozwolone: {sorted(ALLOWED_TAGS)}")
    return tags


def select_scenarios(
    only: list[int] | None = None,
    groups: frozenset[str] | None = None,
) -> list[int]:
    nums = list(SPECS.keys()) if only is None else [n for n in only if n in SPECS]
    if groups:
        nums = [n for n in nums if SPECS[n].tags & groups]
    return sorted(nums)
