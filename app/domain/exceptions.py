class UnknownConversation(Exception):
    pass
class PrelabRequired(Exception):
    def __init__(self, language: str):
        self.language = language