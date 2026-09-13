"""Tests for contains_revealed_code heuristics."""

from __future__ import annotations

import pytest

from app.application.response_pipeline import contains_revealed_code


@pytest.mark.parametrize(
    "pedagogical_response",
    [
        (
            "Rozważ adnotację @RestController nad klasą oraz @GetMapping na metodzie. "
            "Co zwraca ta metoda w architekturze MVC?"
        ),
        (
            "Spójrz do dokumentacji interfejsu `CrudRepository`. "
            "Powinieneś wykorzystać metodę `findById` przyjmującą identyfikator encji."
        ),
        (
            "Struktura powinna wyglądać następująco:\n"
            "- Kontroler przyjmuje DTO\n"
            "- Serwis przetwarza logikę\n"
            "- Repozytorium zapisuje stan"
        ),
        "Zastanów się, jaki kod błędu HTTP odpowiada za brak autoryzacji (podpowiedź: 401 vs 403).",
        "",
    ],
    ids=[
        "annotation_mentions",
        "inline_backtick_method_names",
        "bullet_point_architecture_outline",
        "conceptual_explanation",
        "empty_string",
    ],
)
def test_allowed_pedagogical_guidance(pedagogical_response: str) -> None:
    assert contains_revealed_code(pedagogical_response) is False


@pytest.mark.parametrize(
    "prohibited_code_leak",
    [
        # Complete class in a markdown fence
        """Oto rozwiązanie:
```java
@RestController
public class HelloController {
    @GetMapping("/hello")
    public String hello() {
        return "hi";
    }
}
```
""",
        # Multiline methods without markdown (raw code in prose)
        """
public String hello() {
    return new ResponseEntity<>(body, HttpStatus.OK);
}
private void helper() {
    if (x) {
        return;
    }
}
""",
        # Python (heuristics beyond brace syntax)
        """
```python
def calculate_tax(amount: float) -> float:
    rate = 0.23
    return amount * rate
```
""",
        # Algorithmic loop buried in prose
        """
for (int i = 0; i < list.size(); i++) {
    total += list.get(i).getValue();
}
""",
    ],
    ids=[
        "fenced_java_class",
        "raw_method_bodies_in_prose",
        "fenced_python_function",
        "raw_iteration_logic",
    ],
)
def test_blocked_code_implementations(prohibited_code_leak: str) -> None:
    assert contains_revealed_code(prohibited_code_leak) is True
