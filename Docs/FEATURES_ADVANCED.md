# Advanced Sensei features

## Implemented in this pass (highlight)

| # | Feature | Where |
|---|---------|--------|
| **2** | Error-aware tutoring (auto `debug` mode when logs/diagnostics present) | `chat_service` + `prompts.build_system_prompt(mode_override=)` → `MessageResponse.tutoring_mode` |
| **3** | Checkpoint celebration + reflective nudge | `_finalize_response` when goals advance → `checkpoint_celebration` |
| **4** | Concept glossary card from RAG | definitional questions → `concept_card` + stronger `sources` |
| **6** | Focus mode after IDE errors | `focus_mode_seconds` on config; `focus_until` on session; softer penalties |
| **7** | Professor live dashboard | `GET /conversations/professor/dashboard?lab_id=` |
| **8** | Config dry-run | `POST /config/dry-run` |
| **9** | Hint ladder levels | `hintLadder: [{level, text}]` → `hint_level` on reveal/force |
| **11** | Intervention notes + custom force-hint | `POST .../notes`, force body `customHint` |
| **12** | Similarity signal (professor) | `POST .../similarity` vs `solutionPack` |
| **18** | Grade sync payload for Spring | `grade_payload` on summary/complete + webhook `grade_sync_prepared` |
| **19** | Professor observe | `GET .../observe` |

Config knobs (SenseiConfig): `hintLadder`, `focusModeSeconds`, `autoDebugOnErrors`, `solutionPack`.

---

## Explained only (13–16) — not implemented

### 13. Two-pass tutor
**Idea:** A small/fast model drafts or classifies; gates run; the main coding model answers only safe turns.  
**Why:** Cuts cost and catches giveaways more consistently than regex alone.  
**How it would fit:** Extend `LlmPort` with `classify` / dual adapters; wire `SECURITY_ALWAYS_CLASSIFY` per-lab; cache classifier results.  
**Risk:** Latency doubles unless classifier is tiny/local.

### 14. Rubric-aware scoring
**Idea:** Replace free-text `evaluationCriteria` with weighted rubric items (`id`, `description`, `weight`) mapped into `prompt_score` and Spring grades.  
**Why:** Professors need grades that match the lab sheet, not a 1–10 LLM vibe score.  
**How it would fit:** New `RubricItem` on `SenseiConfig`; `grade_payload` already has room for `rubric_scores`; prompt asks for per-item marks.  
**Risk:** Needs Spring agreement on schema before locking `schema_version`.

### 15. Misconception bank
**Idea:** After N similar wrong answers (e.g. forgetting `@ResponseBody`), inject a canned Socratic counter-question before the LLM.  
**Why:** Consistent pedagogy across the class for known failure modes.  
**How it would fit:** Config list `{pattern, counter_question_pl/en, after_count}`; match in `_prepare_turn`.  
**Risk:** Patterns go stale; keep professor-editable in Spring.

### 16. Timeboxed labs
**Idea:** Soft deadline in config: after T minutes allow more hints, or lock chat and emit summary/`grade_sync_prepared`.  
**Why:** Exam/lab windows and fair pacing.  
**How it would fit:** `lab_started_at` + `time_limit_seconds`; middleware/service check; reuse grade payload trigger `lab_timeout`.  
**Risk:** Clock skew and late joiners — start clock on first message, not session create.

---

## Grade payload contract (feature 18) for Spring

Webhook / stored field `grade_payload` (`schema_version: "1.0"`):

```json
{
  "schema_version": "1.0",
  "event": "grade_sync_prepared",
  "trigger": "session_summary | all_goals_done",
  "prepared_at": 0.0,
  "conversation_id": "uuid",
  "owner_sub": "student-id",
  "lab_id": "lab-id",
  "lab_score": 0,
  "completed": false,
  "goal_progress": {},
  "hints_used": 0,
  "highest_hint_level": "nudge|concept|almost|null",
  "penalties_count": 0,
  "tokens_used": 0,
  "messages_count": 0,
  "frustration_streak": 0,
  "summary": "..."
}
```

AI **prepares and stores** this; Spring should pull on webhook or poll — outbound HTTP to Spring can be enabled later via `SUMMARY_WEBHOOK_URL` / dedicated grade URL.
