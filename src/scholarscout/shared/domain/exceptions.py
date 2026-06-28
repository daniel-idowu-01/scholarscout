"""Shared domain exception hierarchy."""

from __future__ import annotations


class DomainError(Exception):
    """Base for all domain-layer errors."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__


class EntityNotFoundError(DomainError):
    def __init__(self, entity: str, id: object) -> None:
        super().__init__(f"{entity} with id={id} not found", code="NOT_FOUND")
        self.entity = entity
        self.entity_id = id


class DuplicateEntityError(DomainError):
    def __init__(self, entity: str, field: str, value: object) -> None:
        super().__init__(
            f"{entity} with {field}={value} already exists",
            code="DUPLICATE",
        )


class ValidationError(DomainError):
    def __init__(self, field: str, reason: str) -> None:
        super().__init__(f"Validation failed for '{field}': {reason}", code="VALIDATION_ERROR")
        self.field = field
        self.reason = reason


class BusinessRuleViolation(DomainError):
    """Raised when a domain invariant / business rule is violated."""


class InfrastructureError(Exception):
    """Base for infrastructure-layer errors that should surface as 503s."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


class ExternalServiceError(InfrastructureError):
    """Raised when a 3rd-party service call fails after retries."""


class StorageError(InfrastructureError):
    """Raised when object storage operations fail."""


class SearchIndexError(InfrastructureError):
    """Raised when OpenSearch operations fail."""
