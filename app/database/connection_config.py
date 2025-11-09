import os
from dataclasses import dataclass


@dataclass
class ConnectionPoolConfig:
    """Configuration for connection pool."""

    # Required parameters
    host: str
    port: int
    user: str
    password: str
    database: str

    # Optional parameters with their defaults
    pool_size: int = 10
    max_overflow: int = 5
    pool_recycle: int = 3600
    connection_timeout: int = 10
    max_retry_attempts: int = 3
    circuit_failure_threshold: int = 5
    circuit_timeout: int = 60
    health_check_interval: int = 60

    @classmethod
    def from_env(cls, prefix: str = "FROSTEL_MYSQL") -> "ConnectionPoolConfig":
        """
        Create configuration from environment variables.

        More variables can be added if needed to .env file and then passed on here.

        Args:
            prefix: Environment variable prefix (default: FROSTEL_MYSQL)
        """

        return cls(
            host=os.getenv(f"{prefix}_HOST"),
            port=int(os.getenv(f"{prefix}_PORT")),
            user=os.getenv(f"{prefix}_USER"),
            password=os.getenv(f"{prefix}_PASSWORD"),
            database=os.getenv(f"{prefix}_DATABASE"),
        )

    @classmethod
    def for_testing(
        cls,
        host: str = "localhost",
        port: int = 3333,
        **overrides,
    ) -> "ConnectionPoolConfig":
        """
        Create configuration optimised for testing.

        Example:
            config = ConnectionPoolConfig.for_testing(
                pool_size=3,
                circuit_timeout=10  # Faster for tests
            )
        """

        defaults = {
            "host": host,
            "port": port,
            "user": "frostel",
            "password": os.getenv("FROSTEL_MYSQL_PASSWORD", ""),
            "database": "frostel_db",
            "pool_size": 5,
            "max_overflow": 3,
            "max_retry_attempts": 3,
            "circuit_failure_threshold": 3,
            "circuit_timeout": 10,  # Shorter for testing
        }
        defaults.update(overrides)
        return cls(**defaults)

    @staticmethod
    def _is_running_in_docker() -> bool:
        """
        Detect if application is running inside a Docker container.

        Methods:
        1. Check for DOCKER_CONTAINER environment variable
        2. Check for .dockerenv file (created by Docker)
        3. Check if 'mysql' hostname resolves (Docker network)

        Returns:
            True if running in Docker, False otherwise
        """

    def to_dict(self) -> dict:
        """Convert config to dictionary for ConnectionPool."""
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_recycle": self.pool_recycle,
            "connection_timeout": self.connection_timeout,
            "max_retry_attempts": self.max_retry_attempts,
            "circuit_failure_threshold": self.circuit_failure_threshold,
            "circuit_timeout": self.circuit_timeout,
            "health_check_interval": self.health_check_interval,
        }
