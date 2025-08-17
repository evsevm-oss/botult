class DomainError(Exception):
    code = "E_DOMAIN"

    def __init__(self, message: str = "") -> None:
        super().__init__(message)


class InvalidInputError(DomainError):
    code = "E_INVALID_INPUT"


class AIUnavailableError(DomainError):
    code = "E_AI_UNAVAILABLE"


class StorageUnavailableError(DomainError):
    code = "E_STORAGE_UNAVAILABLE"


