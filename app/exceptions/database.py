from app.exceptions.base import FrostelException


class DatabaseException(FrostelException):
    """
    Base for database-related errors.

    Use for ANY error from the database layer:
      - Connection failures
      - Query errors
      - Transaction failures
      - Constraint violations

    """

    default_status_code = 500
    default_user_message = "A technical error occurred. Please try again later"
    default_technical_message = "Database operation failed"


class ConnectionPoolException(DatabaseException):
    """
    Raised when connection pool operations fail.

    Examples:
      - Pool exhausted (no available connections)
      - Failed to create connection
      - Connection health check failed
    """

    default_status_code = 503  # Service Unavailable
    default_user_message = "Service temporarily unavailable. Please try again shortly."
    default_technical_message = "Connection pool error"


class CircuitBreakerException(DatabaseException):
    """
    Raised when circuit breaker is OPEN (database appears down).

    This prevents hammering a dead database and fails fast.
    User should retry after the circuit timeout period.
    """

    default_status_code = 503
    default_user_message = (
        "Service temporarily unavailable. Please try again in a few moments"
    )
    default_technical_message = "Circuit breaker is open - database appears down"

    def __init__(self, retry_after: int = None, **kwargs):
        super().__init__(**kwargs)
        if retry_after:
            self.user_message = (
                f"Service temporarily unavailable. "
                f"Please try again in {retry_after} seconds"
            )
            self.extras["retry_after"] = retry_after


class QueryException(DatabaseException):
    """
    Raised when a SQL query fails.

    Includes query context for debugging

    Usage:
        query = "SELECT * FROM user WHERE email = %s"
        try:
            cursor.execute(query, params)
        except pymysql.Error as e:
            raise QueryException(
                query=query,
                resource="user",
                identifier="email=john@example.com",
                original_exception=e
            ) from e
    """

    def __init__(
        self,
        query: str = None,
        resource: str = None,
        identifier: str = None,
        original_exception: Exception = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        tech_parts = ["Query execution failed"]
        if resource:
            tech_parts.append(f"resource={resource}")
        if identifier:
            tech_parts.append(f"identifier={identifier}")

        self.technical_message = " | ".join(tech_parts)

        if resource:
            self.extras["resource"] = resource
        if identifier:
            self.extras["identifier"] = identifier
        if original_exception:
            self.extras["original_exception"] = str(original_exception)
            self.extras["original_exception_type"] = type(original_exception).__name__


class TransactionException(DatabaseException):
    default_technical_message = "Transaction failed"

    def __init__(self, reason: str = None, **kwargs):
        super().__init__(**kwargs)
        if reason:
            self.technical_message = f"Transaction failed: {reason}"
            self.extras["reason"] = reason


class IntegrityConstraintException(DatabaseException):
    """
    Raised when database constraint is violated.

    Examples:
      - UNIQUE constraint (duplicate key)
      - FOREIGN KEY constraint (referential integrity)
      - NOT NULL constraint
      - CHECK constraint

    Usage:
        try:
            cursor.execute("INSERT INTO user ...")
        except pymysql.IntegrityError as e:
            if e.args[0] == 1062:  # Duplicate key
                raise IntegrityConstraintException(
                    constraint="UNIQUE",
                    field="email",
                    original_exception=e
                ) from e
    """

    default_status_code = 409
    default_user_message = "This operation conflicts with existing data"
    default_technical_message = "Database integrity constraint violated"

    def __init__(
        self,
        constraint: str = None,  # TODO: What constraint was violated? Maybe there's a way to auto-detect this?
        field: str = None,
        original_exception: Exception = None,
        **kwargs,
    ):
        super().__init__(**kwargs)

        if constraint and field:
            self.technical_message = (
                f"{constraint} constraint violated on field '{field}'"
            )
            self.extras["constraint"] = constraint
            self.extras["field"] = field

        if original_exception:
            self.extras["original_exception"] = str(original_exception)
            self.extras["original_exception_type"] = type(original_exception).__name__
