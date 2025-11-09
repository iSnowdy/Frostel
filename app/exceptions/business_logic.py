from app.exceptions.base import FrostelException


class BusinessLogicException(FrostelException):
    """
    Base for business rule violations.

    Use when domain/business logic rules are violated,
    but the request format is valid.
    """

    default_status_code = 400
    default_user_message = "This operation cannot be completed"
    default_technical_message = "Business rule violation"


# General


class ResourceAlreadyExistsException(BusinessLogicException):
    """
    Generic exception for duplicate resources.

    Examples:
        - User with email already exists
        - Hotel with name already exists
        - Booking already confirmed

    Usage:
        raise ResourceAlreadyExistsException(
            resource="user",
            identifier="email=john@example.com"
        )
    """

    def __init__(
        self,
        resource: str,
        identifier: str,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.resource = resource
        self.identifier = identifier

        self.status_code = 409
        self.user_message = f"{resource.capitalize()} already exists"
        self.technical_message = f"Duplicate: {resource}: {identifier}"

        self.extras["resource"] = resource
        self.extras["identifier"] = identifier


class ResourceNotFoundException(BusinessLogicException):
    """
    Generic exception for missing resources.

    IMPORTANT: This is a BUSINESS LOGIC error, not a database error.
    Use this when:
      - User tries to book a non-existent hotel
      - User tries to view a booking that doesn't exist
      - User references a room_id that's not in the system

    Do NOT use this for:
      - Database connection failures (use DatabaseException)
      - Query syntax errors (use QueryException)

    Usage:
        raise ResourceNotFoundException(
            resource="booking",
            identifier="booking_id=999"
        )
    """

    def __init__(
        self,
        resource: str,
        identifier: str,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.resource = resource
        self.identifier = identifier

        self.status_code = 404
        self.user_message = f"{resource.capitalize()} not found"
        self.technical_message = f"{resource.capitalize()} not found: {identifier}"

        self.extras["resource"] = resource
        self.extras["identifier"] = identifier


# User-related exceptions


class UnauthorizedException(BusinessLogicException):
    default_status_code = 401
    default_user_message = "Please log in to continue"
    default_technical_message = "Authentication required"


class ForbiddenException(BusinessLogicException):
    default_status_code = 403
    default_user_message = "You do not have permissions to perform this action"
    default_technical_message = "Access forbidden"


class InvalidCredentialsException(BusinessLogicException):
    default_status_code = 401
    default_user_message = "Invalid email or password."
    default_technical_message = "Authentication failed - invalid credentials"


# Booking-related exceptions


class RoomAlreadyBookedException(BusinessLogicException):
    """
    Raised when room is already booked for requested dates.

    Includes context about the conflicting booking for debugging.
    """

    def __init__(
        self,
        room_id: int,
        conflicting_booking_id: int,
        check_in: str = None,
        check_out: str = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.room_id = room_id
        self.conflicting_booking_id = conflicting_booking_id

        self.status_code = 409
        self.user_message = "This room is no longer available for your selected dates"
        self.technical_message = f"Room {room_id} already booked (conflict with booking {conflicting_booking_id})"

        self.extras["room_id"] = room_id
        self.extras["conflicting_booking_id"] = conflicting_booking_id
        if check_in:
            self.extras["check_in"] = check_in
        if check_out:
            self.extras["check_out"] = check_out


# Reuse for both flights and hotels?
class InsufficientCapacityException(BusinessLogicException):
    """
    Raised when insufficient rooms/seats available.

    Can be reused for:
      - Hotels: Not enough rooms available
      - Flights: Not enough seats available
    """

    default_status_code = 409
    default_user_message = "Not enough capacity available for your request"
    default_technical_message = "Insufficient capacity"

    def __init__(
        self,
        resource_type: str,  # "rooms" or "seats" TODO: ENUM?
        requested: int,
        available: int,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.resource_type = resource_type
        self.requested = requested
        self.available = available

        self.technical_message = f"Insufficient {resource_type}: requested={requested}, available={available}"

        self.extras["resource_type"] = resource_type
        self.extras["requested"] = requested
        self.extras["available"] = available


class InvalidDateRangeException(BusinessLogicException):
    """
    Raised when date range is invalid.

    Examples:
      - Check-out before check-in
      - Return before departure (flights)
      - Dates more than 1 year in future
    """

    default_status_code = 400
    default_user_message = "Invalid date range. Please check your dates"
    default_technical_message = "Date range validation failed"

    def __init__(
        self,
        start_date: str = None,
        end_date: str = None,
        reason: str = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        if reason:
            self.user_message = f"Invalid date range: {reason}"
            self.technical_message = f"Invalid date range: {reason}"
            self.extras["reason"] = reason

        if start_date:
            self.extras["start_date"] = start_date
        if end_date:
            self.extras["end_date"] = end_date


# Payment-related exceptions


class PaymentRequiredException(BusinessLogicException):
    """
    Raised when payment is required but missing.

    Use when:
      - User tries to confirm booking without payment
      - Deposit required but not received
    """

    default_status_code = 402  # Payment Required
    default_user_message = "Payment is required to complete this booking"
    default_technical_message = "Payment required"


class InvalidPaymentException(BusinessLogicException):
    """
    Raised when payment information is invalid.

    Use when:
      - Credit card declined
      - Invalid card number format
      - Insufficient funds
      - Payment gateway error
    """

    default_status_code = 400
    default_user_message = "Invalid payment information. Please check and try again"
    default_technical_message = "Payment validation failed"

    def __init__(self, reason: str = None, **kwargs):
        super().__init__(**kwargs)
        if reason:
            self.technical_message = f"Payment validation failed: {reason}"
            self.extras["reason"] = reason
