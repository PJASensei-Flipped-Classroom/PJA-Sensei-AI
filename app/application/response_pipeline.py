import json
import re
from typing import Dict, Any, List, Optional, Tuple
from app.domain.conversation import Conversation, GoalStatus
from app.application.dto import GoalProgressEntryDTO, NextCheckpointDTO

STATUS_RANK: Dict[GoalStatus, int] = {
    "not_started": 0,
    "in_progress": 1,
    "done": 2,
}

PL_DIACRITICS_RE = re.compile(r"[ąćęłńóśźżĄĆĘŁŃÓŚŹŻ]")

PL_WORDS_RE = re.compile(
    r"\b(jest|nie|się|oraz|czy|jak|kod|że|aby|przez|tylko|funkcj\w*|klas\w*)\b",
    re.IGNORECASE,
)

# Wzbogacony słownik popularnych słów i spójników angielskich
EN_WORDS_RE = re.compile(
    r"\b(the|and|you|should|this|that|your|with|from|have|what|where|because|please|check|code|is|are|a|an|for|on|in|to|it|of|based|can|will|as|by)\b",
    re.IGNORECASE,
)

GIVEAWAY_REQUEST_RE = re.compile(
    r"(napisz\s+za\s+mnie|daj\s+gotow|cały\s+kod|gotowe\s+rozwiązanie|write\s+the\s+full\s+code|give\s+me\s+the\s+full\s+code)",
    re.IGNORECASE,
)
CODE_BLOCK_RE = re.compile(r"```(?:[a-zA-Z0-9_+-]+)?\s*\n(.*?)```", re.DOTALL)


class ResponsePipeline:

    def extract_json(self, raw_text: str) -> Tuple[Optional[Dict[str, Any]], bool]:
        if not raw_text or not raw_text.strip():
            return None, True

        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = cleaned[start : end + 1]
            try:
                data = json.loads(candidate)
                if isinstance(data, dict):
                    return data, False
            except json.JSONDecodeError:
                pass

        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return data, False
        except json.JSONDecodeError:
            pass

        return None, True

    def build_fallback_payload(self, raw_text: str, conv: Conversation) -> Dict[str, Any]:
        clean_msg = (raw_text or "").strip()
        if not clean_msg or clean_msg.startswith("{"):
            clean_msg = (
                "Przeanalizujmy ten problem krok po kroku. Co do tej pory sprawdziłeś?"
                if conv.config.language == "pl"
                else "Let's analyze this step by step. What have you checked so far?"
            )

        feedback = (
            "Odpowiedź zastępcza (fallback po błędzie formatu JSON)."
            if conv.config.language == "pl"
            else "Fallback response (malformed JSON recovery)."
        )
        next_step = (
            "Doprecyzuj pytanie lub sprawdź logi błędów."
            if conv.config.language == "pl"
            else "Clarify your question or inspect the error logs."
        )

        return {
            "answer": clean_msg,
            "prompt_score": 5,
            "prompt_feedback": feedback,
            "penalty_applied": False,
            "suggested_next_step": next_step,
            "goal_progress": [
                {"goal": g.id, "status": conv.goal_progress.get(g.id, "not_started")}
                for g in conv.config.learning_context.goals
            ],
            "_fallback_used": True,
        }

    def has_language_drift(self, answer: str, expected_language: str) -> bool:
        if not answer or len(answer.strip()) < 12:
            return False

        pl_diacritics = len(PL_DIACRITICS_RE.findall(answer))
        pl_words = len(PL_WORDS_RE.findall(answer))
        en_words = len(EN_WORDS_RE.findall(answer))

        pl_score = pl_diacritics * 2 + pl_words
        en_score = en_words

        print(f"\n[DEBUG DRIFT] Oczekiwany język sesji: '{expected_language}'")
        print(f"[DEBUG DRIFT] Punkty PL: {pl_score} | Punkty EN: {en_score}")

        if expected_language == "pl":
            is_drift = en_score >= 2 and pl_score <= 1
            print(f"[DEBUG DRIFT] Wykryto drift: {is_drift}")
            return is_drift

        if expected_language == "en":
            is_drift = pl_score >= 2 and en_score <= 1
            print(f"[DEBUG DRIFT] Wykryto drift: {is_drift}")
            return is_drift

        return False

    def apply_code_penalty(
        self,
        answer: str,
        question: str,
        prompt_score: int,
        penalty_applied: bool,
    ) -> Tuple[int, bool]:
        has_large_code_block = False
        for match in CODE_BLOCK_RE.findall(answer or ""):
            non_empty_lines = [line for line in match.strip().splitlines() if line.strip()]
            if len(non_empty_lines) >= 4 or len(match.strip()) >= 140:
                has_large_code_block = True
                break

        asked_for_giveaway = bool(GIVEAWAY_REQUEST_RE.search(question or ""))

        if has_large_code_block or asked_for_giveaway:
            penalty_applied = True

        if penalty_applied:
            prompt_score = min(prompt_score, 4)

        return max(1, min(10, prompt_score)), penalty_applied

    def normalize_goals(
        self, conv: Conversation, raw_goals: Any
    ) -> List[GoalProgressEntryDTO]:
        valid_statuses = {"not_started", "in_progress", "done"}
        desc_to_id = {
            goal.description.lower(): goal.id for goal in conv.config.learning_context.goals
        }
        valid_ids = {g.id for g in conv.config.learning_context.goals}

        if isinstance(raw_goals, list):
            for item in raw_goals:
                if not isinstance(item, dict):
                    continue
                raw_goal = str(item.get("goal", "")).strip()
                new_status = str(item.get("status", "not_started")).strip()

                if new_status not in valid_statuses:
                    continue

                target_id = None
                if raw_goal in valid_ids:
                    target_id = raw_goal
                elif raw_goal.lower() in desc_to_id:
                    target_id = desc_to_id[raw_goal.lower()]

                if target_id:
                    old_status: GoalStatus = conv.goal_progress.get(target_id, "not_started")
                    if STATUS_RANK[new_status] > STATUS_RANK[old_status]:  # type: ignore
                        conv.goal_progress[target_id] = new_status  # type: ignore

        return [
            GoalProgressEntryDTO(
                goal=g.id,
                status=conv.goal_progress.get(g.id, "not_started"),
            )
            for g in conv.config.learning_context.goals
        ]

    def evaluate_checkpoints(self, conv: Conversation) -> Optional[NextCheckpointDTO]:
        newly_unlocked = None
        for checkpoint in conv.config.checkpoints:
            if conv.goal_progress.get(checkpoint.after_goal) == "done":
                if checkpoint.id not in conv.unlocked_checkpoints:
                    conv.unlocked_checkpoints.append(checkpoint.id)
                    newly_unlocked = checkpoint

        if newly_unlocked is not None:
            return NextCheckpointDTO(
                id=newly_unlocked.id,
                after_goal=newly_unlocked.after_goal,
                hint=newly_unlocked.hint,
                unlocked=True,
            )

        for checkpoint in conv.config.checkpoints:
            if checkpoint.id not in conv.unlocked_checkpoints:
                return NextCheckpointDTO(
                    id=checkpoint.id, after_goal=checkpoint.after_goal, hint=None, unlocked=False
                )

        if conv.config.checkpoints:
            last_cp = conv.config.checkpoints[-1]
            return NextCheckpointDTO(
                id=last_cp.id,
                after_goal=last_cp.after_goal,
                hint=last_cp.hint,
                unlocked=True,
            )
        return None