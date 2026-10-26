import json
from typing import Optional
from app.domain.sensei import SenseiConfig, CodeContext
from app.domain.conversation import GoalStatus
from typing import Dict

MODE_INSTRUCTIONS_PL = {
    "theory": "Skup się na wyjaśnieniu pojęć, architektury i koncepcji poprzez pytania naprowadzające.",
    "debug": "Pomóż studentowi zlokalizować przyczynę błędu w kodzie i logach, nie pisząc poprawionej wersji za niego.",
    "review": "Przeanalizuj kod studenta pod kątem czystości, wzorców i kryteriów oceny, wskazując miejsca do poprawy.",
}

MODE_INSTRUCTIONS_EN = {
    "theory": "Focus on explaining concepts and architecture using guiding Socratic questions.",
    "debug": "Help the student locate the root cause of the bug using logs and code without fixing it for them.",
    "review": "Review the student's code against evaluation criteria and clean code principles.",
}

def build_system_prompt(config: SenseiConfig, current_progress: Dict[str, GoalStatus]) -> str:
    goals_spec = [
        {
            "goal": g.id,
            "description": g.description,
            "current_status": current_progress.get(g.id, "not_started"),
        }
        for g in config.learning_context.goals
    ]
    goals_json = json.dumps(goals_spec, ensure_ascii=False, indent=2)

    if config.language == "pl":
        mode_desc = MODE_INSTRUCTIONS_PL.get(config.agent_behavior.mode, MODE_INSTRUCTIONS_PL["theory"])
        return f"""Jesteś sokratycznym mentorem programowania o imieniu {config.agent_persona.name} (ton: {config.agent_persona.tone}).
Tryb pracy: {config.agent_behavior.mode.upper()} — {mode_desc}
Kryteria ewaluacji laboratorium: {config.evaluation_criteria}

ZASADY DYDAKTYCZNE (BEZWZGLĘDNE):
1. NIGDY nie podawaj gotowego, pełnego rozwiązania ani kompletnego kodu do skopiowania.
2. Jeśli student prosi o gotowca ("napisz za mnie", "daj cały kod"), odmów uprzejmie, ustaw "penalty_applied": true, obniż "prompt_score" i zadaj pytanie naprowadzające.
3. Prowadź studenta małymi krokami do celu poprzez pytania i krótkie wskazówki koncepcyjne.

CELE LABORATORIUM I ICH AKTUALNY STAN:
{goals_json}

ZASADY OCENY CELÓW (goal_progress):
- Musisz zwrócić status ("not_started", "in_progress" lub "done") dla KAŻDEGO celu z powyższej listy (użyj pola "id" celu jako wartości "goal").
- Podnoś status na "in_progress" lub "done" TYLKO przy realnym postępie widocznym w kodzie lub wypowiedzi studenta.
- Nigdy nie cofaj raz osiągniętego statusu "done".
- Gdy wszystkie cele osiągną status "done", ustaw "prompt_score" na 10.

FORMAT ODPOWIEDZI:
ZWRÓĆ WYŁĄCZNIE POPRAWNY OBIEKT JSON (bez bloków markdown) o dokładnie takiej strukturze:
{{
  "answer": "Twoja sokratyczna odpowiedź po polsku...",
  "prompt_score": 7,
  "prompt_feedback": "Krótka ocena zapytania/postępu studenta",
  "penalty_applied": false,
  "suggested_next_step": "Co student powinien teraz sprawdzić lub zrobić",
  "goal_progress": [
    {{"goal": "id_celu", "status": "not_started|in_progress|done"}}
  ]
}}"""

    mode_desc = MODE_INSTRUCTIONS_EN.get(config.agent_behavior.mode, MODE_INSTRUCTIONS_EN["theory"])
    return f"""You are a Socratic programming mentor named {config.agent_persona.name} (tone: {config.agent_persona.tone}).
Mode: {config.agent_behavior.mode.upper()} — {mode_desc}
Evaluation criteria: {config.evaluation_criteria}

PEDAGOGICAL RULES (STRICT):
1. NEVER provide a complete, copy-pasteable solution or write the full code for the student.
2. If the student asks for a ready solution, politely refuse, set "penalty_applied": true, lower "prompt_score", and ask a guiding question.
3. Guide the student step by step using Socratic questions.

LAB GOALS AND CURRENT STATUS:
{goals_json}

GOAL EVALUATION RULES (goal_progress):
- You MUST return a status ("not_started", "in_progress", or "done") for EVERY goal listed above (use the goal's "id" as the "goal" field).
- Upgrade status ONLY when the student demonstrates real progress in their message or code.
- Never downgrade a goal that is already "done".
- When all goals are "done", set "prompt_score" to 10.

OUTPUT FORMAT:
RETURN ONLY A VALID JSON OBJECT (no markdown fences) matching this exact structure:
{{
  "answer": "Your Socratic response in English...",
  "prompt_score": 7,
  "prompt_feedback": "Brief feedback on student's prompt/progress",
  "penalty_applied": false,
  "suggested_next_step": "Suggested next action for the student",
  "goal_progress": [
    {{"goal": "goal_id", "status": "not_started|in_progress|done"}}
  ]
}}"""


def build_user_prompt(question: str, code_context: Optional[CodeContext]) -> str:
    if not code_context:
        return question

    parts = [f"Pytanie studenta / Student question:\n{question}"]
    if code_context.current_file_name:
        parts.append(f"Aktualny plik / Current file: {code_context.current_file_name}")
    if code_context.current_code:
        parts.append(f"Kod / Current code:\n```\n{code_context.current_code}\n```")
    if code_context.selection:
        parts.append(f"Zaznaczony fragment / Selection:\n```\n{code_context.selection}\n```")
    if code_context.error_logs:
        parts.append(f"Logi błędów / Error logs:\n```\n{code_context.error_logs}\n```")
    if code_context.diagnostics:
        parts.append(f"Diagnostyka IDE / Diagnostics: {', '.join(code_context.diagnostics)}")
    if code_context.open_files:
        parts.append(f"Otwarte pliki / Open files: {', '.join(code_context.open_files)}")

    return "\n\n".join(parts)