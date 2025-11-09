from typing import Any

from app.exceptions.base import FrostelException


class ValidationException(FrostelException):
    """
    Base for input validation errors.

    Use when user input is invalid (wrong format, missing, out of range).
    Different from BusinessLogicException: validation is about FORMAT,
    business logic is about RULES.

    Examples:
      - Validation: Email format is invalid (not an email address)
      - Business: Email already registered (format is valid, but violates uniqueness rule)
    """

    default_status_code = 400
    default_user_message = "Invalid input provided"
    default_technical_message = "Validation failed"


class MissingFieldException(ValidationException):
    def __init__(
        self,
        field: str,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.field = field

        self.status_code = 400
        self.user_message = f"Required field '{field}' is missing"
        self.technical_message = f"Missing required field: {field}"

        self.extras["field"] = field


class InvalidFormatException(ValidationException):
    def __init__(
        self,
        field: str,
        expected_format: str = None,
        provided_value: str = None,  # TODO: PII leakage?
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.field = field
        self.expected_format = expected_format

        self.status_code = 400
        self.user_message = f"Invalid format for '{field}'"

        if expected_format:
            self.user_message += f" Expected: {expected_format}"
            self.technical_message = (
                f"Invalid format for field '{field}'. Expected: {expected_format}"
            )
        else:
            self.technical_message = f"Invalid format for field '{field}'"

        self.extras["field"] = field
        if expected_format:
            self.extras["expected_format"] = expected_format
        # Only log the provided value if it's not sensitive. This is very weak. Consider other ways?
        if provided_value and field not in ["password", "credit_card", "ssn"]:
            self.extras["provided_value"] = provided_value


class InvalidPasswordException(ValidationException):
    def __init__(
        self,
        reason: str = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.field = "password"

        self.status_code = 400
        self.user_message = "Password does not meet security requirements"

        if reason:
            self.user_message += f" {reason}"
            self.technical_message = f"Password validation failed: {reason}"
            self.extras["reason"] = reason
        else:
            self.technical_message = "Password validation failed"

        self.extras["field"] = self.field


class InvalidRangeException(ValidationException):
    def __init__(
        self,
        field: str,
        value: Any,
        min_value: Any = None,
        max_value: Any = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.field = field

        self.status_code = 400

        # Build user message
        msg_parts = [f"'{field}' value is out of range."]
        if min_value is not None and max_value is not None:
            msg_parts.append(f"Must be between {min_value} and {max_value}.")
        elif min_value is not None:
            msg_parts.append(f"Must be at least {min_value}.")
        elif max_value is not None:
            msg_parts.append(f"Must be at most {max_value}.")

        self.user_message = " ".join(msg_parts)
        self.technical_message = (
            f"Value '{value}' for field '{field}' out of range "
            f"(min={min_value}, max={max_value})"
        )

        self.extras["field"] = field
        self.extras["value"] = value
        if min_value is not None:
            self.extras["min_value"] = min_value
        if max_value is not None:
            self.extras["max_value"] = max_value
