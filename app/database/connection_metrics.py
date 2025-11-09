from datetime import datetime
from dataclasses import dataclass

from app.models.enums import CircuitState


@dataclass
class ConnectionMetrics:
    """Metrics for monitoring connection pool health."""

    total_connections_created: int = 0
    total_connections_closed: int = 0
    total_checkouts: int = 0
    total_checkins: int = 0
    total_errors: int = 0
    total_retries: int = 0

    active_connections: int = 0
    idle_connections: int = 0
    overflow_connections: int = 0

    avg_checkout_time_ms: float = 0.0
    max_checkout_time_ms: float = 0.0

    circuit_state: CircuitState = CircuitState.CLOSED
    circuit_failures: int = 0
    circuit_opened_at: datetime | None = None

    last_health_check: datetime | None = None
    health_check_failures: int = 0

    def to_dict(self):
        return {
            "total_connections_created": self.total_connections_created,
            "total_connections_closed": self.total_connections_closed,
            "total_checkouts": self.total_checkouts,
            "total_checkins": self.total_checkins,
            "total_errors": self.total_errors,
            "total_retries": self.total_retries,
            "active_connections": self.active_connections,
            "idle_connections": self.idle_connections,
            "overflow_connections": self.overflow_connections,
            "avg_checkout_time_ms": round(self.avg_checkout_time_ms, 2),
            "max_checkout_time_ms": round(self.max_checkout_time_ms, 2),
            "circuit_state": self.circuit_state.value,
            "circuit_failures": self.circuit_failures,
            "circuit_opened_at": self.circuit_opened_at.isoformat()
            if self.circuit_opened_at
            else None,
            "last_health_check": self.last_health_check.isoformat()
            if self.last_health_check
            else None,
            "health_check_failures": self.health_check_failures,
        }

    def reset(self):
        self.__init__()
