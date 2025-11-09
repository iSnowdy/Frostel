# app/exceptions/base.py

import json
from datetime import datetime, timezone
from typing import Any, Dict


class FrostelException(Exception):
    """
    Base exception class for Frostel application.

    All custom exceptions inherit from this to ensure consistent
    error handling, logging, and user-facing messages.

    Attributes:
        status_code: HTTP status code (default: 500)
        user_message: User-friendly message (safe to display)
        technical_message: Technical details (for logging only)
        extras: Additional context (original_exception, resource, etc.)
        timestamp: When the exception occurred (UTC)
    """

    default_status_code = 500
    default_user_message = "An unexpected error occurred. Please try again later."
    default_technical_message = "An unexpected error occurred"

    def __init__(
        self,
        user_message: str = None,
        technical_message: str = None,
        status_code: int = None,
        **kwargs,  # extras: original_exception, request_id, resource, identifier...
    ):
        """
        Initialise the exception.

        Args:
            user_message: Message safe to show to users
            technical_message: Technical details for logging
            status_code: HTTP status code
            **kwargs: Additional context stored in self.extras
        """
        super().__init__(user_message or self.default_user_message)

        self.status_code = status_code or self.default_status_code
        self.user_message = user_message or self.default_user_message
        self.technical_message = technical_message or self.default_technical_message
        self.extras = kwargs
        self.timestamp = datetime.now(tz=timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for API-like responses (user-safe).

        Only includes information safe to expose to users.
        Does NOT include technical details or extras.
        """
        result = {
            "error": {
                "type": self.__class__.__name__,  # Consider not exposing this?
                "message": self.user_message,
                "timestamp": self.timestamp.isoformat(),
            }
        }

        # Can be helpful for tracking requests lifecycle
        if "request_id" in self.extras:
            result["error"]["request_id"] = self.extras["request_id"]

        # Add field_name if available (for validation errors)
        if hasattr(self, "field") and self.field:
            result["error"]["field"] = self.field

        return result

    def to_log_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for logging (includes technical details).

        Includes ALL information for debugging and monitoring.
        """
        return {
            "exception_type": self.__class__.__name__,
            "status_code": self.status_code,
            "user_message": self.user_message,
            "technical_message": self.technical_message,
            "timestamp": self.timestamp.isoformat(),
            "extras": self.extras,
        }

    def __str__(self) -> str:
        """
        String representation for logging.

        Format: [ExceptionType] status=500 | user_msg='...' | tech_msg='...' | extras={...}
        """
        parts = [
            f"[{self.__class__.__name__}]",
            f"status={self.status_code}",
            f"user_msg='{self.user_message}'",
            f"tech_msg='{self.technical_message}'",
            f"timestamp={self.timestamp.isoformat()}",
        ]

        if self.extras:
            try:
                # Try JSON serialization
                extras_str = json.dumps(self.extras, default=str, ensure_ascii=False)
                parts.append(f"extras={extras_str}")
            except (TypeError, ValueError):
                # Fallback to repr for non-serializable objects
                parts.append(f"extras={self.extras!r}")

        return " | ".join(parts)
