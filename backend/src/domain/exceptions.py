from __future__ import annotations


class DomainError(Exception):
    """Base error for domain and use-case failures."""


class ValidationError(DomainError):
    """Raised when input violates domain validation rules."""


class AuthenticationError(DomainError):
    """Raised when credentials or JWT tokens are invalid/expired."""


class NotFoundError(DomainError):
    """Raised when a requested resource or entity model does not exist."""


class ConflictError(DomainError):
    """Raised when an operation conflicts with existing state (e.g. duplicate email)."""


class OperationNotAllowedError(DomainError):
    """Raised when a CRUD operation is disallowed by the model's contract."""


class DatabaseError(DomainError):
    """Raised when an underlying datasource operation fails unexpectedly."""
