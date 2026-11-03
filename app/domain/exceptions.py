class UnknownConversation(Exception):
    pass
class UnknownMessage(Exception):
    pass
class PrelabRequired(Exception):
    def __init__(self, language: str):
        self.language = language
class TokenBudgetExceeded(Exception):
    def __init__(self, language: str = "pl", limit: int = 0, used: int = 0):
        self.language = language
        self.limit = limit
        self.used = used

class HintRevealForbidden(Exception):
    def __init__(
        self,
        reason: str,
        language: str = "pl",
        streak: int = 0,
        required_streak: int = 2,
        hints_used: int = 0,
        max_hints: int = 3,
    ):
        self.reason = reason  # "insufficient_streak" | "quota_exceeded"
        self.language = language
        self.streak = streak
        self.required_streak = required_streak
        self.hints_used = hints_used
        self.max_hints = max_hints

class SsrfBlockedError(Exception):
    def __init__(self, url: str, reason: str = "Blocked unsafe URL (SSRF protection)"):
        self.url = url
        self.reason = reason
        super().__init__(f"{reason}: {url}")