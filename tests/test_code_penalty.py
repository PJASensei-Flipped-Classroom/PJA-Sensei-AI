"""Tests for contains_revealed_code heuristics."""

from __future__ import annotations

import pytest

from app.application.response_pipeline import contains_revealed_code


@pytest.mark.parametrize(
    "text",
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
    ids=["annotations", "backticks", "bullets", "http_hint", "empty"],
)
def test_allowed_pedagogical_guidance(text: str) -> None:
    assert contains_revealed_code(text) is False


@pytest.mark.parametrize(
    "text",
    [
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
        """
```python
def calculate_tax(amount: float) -> float:
    rate = 0.23
    return amount * rate
```
""",
        """
for (int i = 0; i < list.size(); i++) {
    total += list.get(i).getValue();
}
""",
    ],
    ids=["fenced_java", "raw_methods", "fenced_python", "raw_loop"],
)
def test_blocked_code_implementations(text: str) -> None:
    assert contains_revealed_code(text) is True
