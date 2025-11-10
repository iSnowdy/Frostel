from enum import Enum


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half-open"


class MembershipEnum(Enum):
    FREE = "free"
    BRONZE = "bronze"
    GOLD = "gold"
    PLATINUM = "platinum"
