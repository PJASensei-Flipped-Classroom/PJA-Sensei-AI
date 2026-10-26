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