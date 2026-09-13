"""Domain exceptions."""


class UnknownConversation(Exception):
    pass


class PrelabRequired(Exception):
    pass


class TokenBudgetExceeded(Exception):
    pass


class RevealNotAllowed(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)
