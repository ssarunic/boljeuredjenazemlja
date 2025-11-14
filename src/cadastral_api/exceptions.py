"""Custom exceptions for the Croatian Cadastral API client."""

from enum import Enum
from typing import Any


class ErrorType(str, Enum):
    """Types of cadastral API errors."""

    CONNECTION = "connection"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    INVALID_RESPONSE = "invalid_response"
    PARCEL_NOT_FOUND = "parcel_not_found"
    MUNICIPALITY_NOT_FOUND = "municipality_not_found"
    SERVER_ERROR = "server_error"


class CadastralAPIError(Exception):
    """Base exception for all cadastral API errors."""

    def __init__(
        self,
        error_type: ErrorType,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """
        Initialize cadastral API error.

        Args:
            error_type: Type of error that occurred
            details: Additional context about the error
            cause: Original exception that caused this error
        """
        self.error_type = error_type
        self.details = details or {}
        self.cause = cause
        super().__init__()

    def __str__(self) -> str:
        """Return a human-readable error message."""
        msg_parts = [f"{self.error_type.value}"]

        # Add relevant details
        if self.details:
            detail_strs = []
            for key, value in self.details.items():
                if value is not None:
                    detail_strs.append(f"{key}={value}")
            if detail_strs:
                msg_parts.append(f"({', '.join(detail_strs)})")

        # Add cause if available
        if self.cause:
            msg_parts.append(f"- caused by: {type(self.cause).__name__}: {str(self.cause)}")

        return " ".join(msg_parts)
