"""Scenario registry with tags for --only / --group filtering."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx

from tests.live.helpers import ScenarioResult
from tests.live.scenarios import contract, pedagogy, roi

ScenarioFn = Callable[[httpx.AsyncClient], Awaitable[ScenarioResult]]

ALLOWED_TAGS = frozenset({"pedagogy", "contract", "gates", "roi", "edge", "student"})


@dataclass(frozen=True)
class ScenarioSpec:
    """Metadane zarejestrowanego scenariusza live (numer, tagi, coroutine)."""

    number: int
    name: str
    tags: frozenset[str]
    fn: ScenarioFn


def _spec(
    number: int, name: str, tags: set[str], fn: ScenarioFn
) -> ScenarioSpec:
    unknown = tags - ALLOWED_TAGS
    if unknown:
        raise ValueError(f"S{number}: unknown tags {unknown}")
    return ScenarioSpec(number, name, frozenset(tags), fn)


SPECS: dict[int, ScenarioSpec] = {
    s.number: s
    for s in [
        # --- Student / pedagogy narratives ---
        _spec(1, "Student pyta o teorię bez kodu", {"pedagogy", "student"}, pedagogy.scenario_1_theory),
        _spec(2, "Student korzysta z materiałów RAG (Spring)", {"pedagogy", "student"}, pedagogy.scenario_2_rag),
        _spec(3, "Student próbuje jailbreak / injection", {"pedagogy", "gates", "student"}, pedagogy.scenario_3_injection),
        _spec(4, "Student żąda gotowca (pełny kod)", {"pedagogy", "gates", "student"}, pedagogy.scenario_4_anti_code),
        _spec(
            5,
            "Student frustruje się (niskie score → sokratyzm)",
            {"pedagogy", "edge", "student"},
            pedagogy.scenario_5_frustration,
        ),
        _spec(6, "Student zmienia kod by ominąć cache", {"pedagogy", "student"}, pedagogy.scenario_6_cache),
        _spec(7, "Student streamuje odpowiedź (JSON escape)", {"pedagogy", "student"}, pedagogy.scenario_7_json_stream),
        _spec(8, "Student wraca do nazw po kompresji historii", {"pedagogy", "student"}, pedagogy.scenario_8_memory),
        _spec(9, "Awaria RAG nie wywala sesji studenta", {"pedagogy", "edge", "student"}, pedagogy.scenario_9_rag_timeout),
        # --- Contract / ops (not student narratives) ---
        _spec(
            10,
            "Health i metrics",
            {"contract"},
            contract.scenario_10_health_metrics,
        ),
        _spec(
            11,
            "GET/DELETE/events/restrictions",
            {"contract"},
            contract.scenario_11_session_contract,
        ),
        _spec(
            12,
            "Student bez zaliczonego pre-lab (chat zablokowany)",
            {"contract", "gates", "student"},
            contract.scenario_12_prelab_gate,
        ),
        _spec(
            13,
            "Validate config",
            {"contract"},
            contract.scenario_13_validate_config,
        ),
        _spec(
            14,
            "Prometheus + request_id",
            {"contract"},
            contract.scenario_14_prometheus_request_id,
        ),
        _spec(
            15,
            "Export + soft DELETE",
            {"contract"},
            contract.scenario_15_export_soft_delete,
        ),
        _spec(
            16,
            "Live stream tokens",
            {"contract"},
            contract.scenario_16_live_stream_tokens,
        ),
        _spec(
            17,
            "Student ponawia to samo client_message_id (idempotency)",
            {"contract", "student"},
            contract.scenario_17_idempotency,
        ),
        _spec(
            18,
            "Student wysyła bogaty CodeContext z IDE",
            {"contract", "student"},
            contract.scenario_18_rich_code_context,
        ),
        _spec(
            19,
            "Student odblokowuje checkpointy / cele",
            {"contract", "roi", "student"},
            contract.scenario_19_checkpoints,
        ),
        _spec(
            20,
            "Restrictions endpoint",
            {"contract"},
            contract.scenario_20_restrictions,
        ),
        _spec(
            21,
            "Student bierze reveal, ocenia, kończy summary",
            {"roi", "gates", "student"},
            roi.scenario_21_reveal_feedback_summary,
        ),
        _spec(
            22,
            "Student wyczerpuje budżet tokenów sesji",
            {"roi", "gates", "contract", "student"},
            roi.scenario_22_token_budget,
        ),
        _spec(
            23,
            "Student czatuje bez pliku przy requireFileContext",
            {"roi", "gates", "student"},
            roi.scenario_23_require_file_context,
        ),
        _spec(
            24,
            "Unknown conversation 404",
            {"contract"},
            contract.scenario_24_unknown_conversation,
        ),
        _spec(
            25,
            "Student farmi reveal niskimi score’ami",
            {"roi", "edge", "student"},
            roi.scenario_25_reveal_after_low_streak,
        ),
        _spec(
            26,
            "Student wyczerpuje limit reveal w sesji",
            {"roi", "gates", "edge", "student"},
            roi.scenario_26_reveal_quota_exhausted,
        ),
        _spec(
            27,
            "Student dostaje coaching next_checkpoint",
            {"roi", "student"},
            roi.scenario_27_next_checkpoint_coaching,
        ),
        _spec(
            28,
            "Rich summary shape",
            {"roi"},
            roi.scenario_28_rich_summary_shape,
        ),
        _spec(
            29,
            "Student failuje prelab, potem zalicza",
            {"roi", "gates", "student"},
            roi.scenario_29_prelab_fail_then_pass,
        ),
        _spec(30, "Sesja w trybie theory", {"roi", "student"}, roi.scenario_30_mode_theory),
        _spec(31, "PDF RAG material", {"roi", "edge"}, roi.scenario_31_pdf_rag_material),
        _spec(
            32,
            "Student generuje eventy IDE → summary",
            {"roi", "student"},
            roi.scenario_32_ide_events_in_summary,
        ),
        _spec(
            33,
            "Sync vs stream parity",
            {"roi", "contract"},
            roi.scenario_33_sync_stream_parity,
        ),
    ]
}

# number -> coroutine
SCENARIOS: dict[int, ScenarioFn] = {n: s.fn for n, s in SPECS.items()}


def parse_only(raw: str | None) -> list[int] | None:
    """Parsuje ``--only 1,3,5`` do listy numerów scenariuszy."""
    if not raw:
        return None
    nums: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        n = int(part)
        if n not in SPECS:
            raise SystemExit(
                f"Nieznany numer scenariusza: {n} (dozwolone 1-{max(SPECS)})"
            )
        nums.append(n)
    return nums


def parse_groups(raw: str | None) -> set[str] | None:
    """Parsuje ``--group pedagogy,roi`` do zbioru tagów ALLOWED_TAGS."""
    if not raw:
        return None
    tags = {p.strip() for p in raw.split(",") if p.strip()}
    bad = tags - ALLOWED_TAGS
    if bad:
        raise SystemExit(
            f"Nieznane tagi: {sorted(bad)} (dozwolone: {sorted(ALLOWED_TAGS)})"
        )
    return tags


def select_scenarios(
    only: list[int] | None = None,
    groups: set[str] | None = None,
) -> list[int]:
    """Return scenario numbers. Both filters → intersection; preserve --only order."""
    if only is not None:
        nums = list(only)
    else:
        nums = sorted(SPECS.keys())
    if groups:
        nums = [n for n in nums if SPECS[n].tags & groups]
    return nums
