from dataclasses import dataclass
from datetime import datetime, date

from app.models.enums import MembershipEnum
from app.utils.validators import is_valid_password


@dataclass
class User:
    id: int
    name: str
    surname: str
    email: str
    password: str  # Hashed
    date_of_birth: datetime.date
    membership: MembershipEnum
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def full_name(self) -> str:
        return f"{self.name} {self.surname}"

    @property
    def age(self) -> int:
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - (
                (today.month, today.day)
                < (self.date_of_birth.month, self.date_of_birth.day)
            )
        )

    @property
    def is_premium(self) -> bool:
        return self.membership in [MembershipEnum.GOLD, MembershipEnum.PLATINUM]

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "surname": self.surname,
            "email": self.email,
            "password_hash": self.password,  # TODO: Masked? Ensure hashing function?
            "date_of_birth": self.date_of_birth,
            "membership": self.membership.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_db_row(cls, row: dict) -> "User":
        return cls(**row)


@dataclass
class CreateUserDTO:
    name: str
    surname: str
    email: str
    password: str
    date_of_birth: datetime.date
    membership: MembershipEnum

    # Returns a list of possible validation errors
    # TODO: Enhance this validation
    def validate(self) -> list[str]:
        errors = []

        if not self.name or len(self.name) < 2:
            errors.append("Name must be at least 2 characters")

        if not self.surname or len(self.surname) < 2:
            errors.append("Surname must be at least 2 characters")

        if not self.email or "@" not in self.email:
            errors.append("Invalid email format")

        today = date.today()
        age = today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
        if age < 18:
            errors.append("You must be at least 18 years old")

        if age > 120:
            errors.append("Invalid date of birth")


        if (
            is_valid_password(password=self.password)
        ):  # TODO: Is hashed function bool to validate
            errors.append(
                "Password must be at least 8 characters, contain at least one digit, one symbol, "
                "one uppercase and one lowercase character"
            )

        return errors


@dataclass
class UpdateUserDTO:
    name: str | None = None
    surname: str | None = None
    email: str | None = None
    password: str | None = None
    date_of_birth: datetime.date | None = None
    membership: MembershipEnum | None = None

    def to_dict(self) -> dict:
        return {
            k: v
            for k, v in {
                "name": self.name,
                "surname": self.surname,
                "email": self.email,
                "password": self.password,
                "date_of_birth": self.date_of_birth,
                "membership": self.membership.value if self.membership else None,
            }.items()
            if v is not None
        }
