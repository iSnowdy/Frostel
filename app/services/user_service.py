import logging

import bcrypt

from app.database.repositories.user_repository import UserRepository
from app.exceptions.business_logic import ResourceAlreadyExistsException, ResourceNotFoundException, \
    InvalidCredentialsException
from app.exceptions.validation import ValidationException
from app.models.user import CreateUserDTO, User, UpdateUserDTO, validate_user_args, PWD_REQUIREMENTS
from app.utils.validators import is_valid_password

logger = logging.getLogger(__name__)


class UserService:

    def __init__(self, hashing_rounds: int = 12):
        self.user_repo = UserRepository()
        self.hashing_rounds = hashing_rounds

    def get_user_by_id(self, user_id: int) -> User | None:
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise ResourceNotFoundException(
                resource="user",
                identifier=f"id={user_id}",
            )
        logger.info(f"User with UD '{user_id}' found")
        return self._mask_user_password(user)

    def get_user_by_email(self, email: str) -> User | None:
        user = self.user_repo.find_by(email=email)
        if not user:
            raise ResourceNotFoundException(
                resource="user",
                identifier=f"email={email}",
            )
        user.password = "****"
        logger.info(f"User with email '{user.email}' found")
        return self._mask_user_password(user)

    def authenticate(self, email: str, password: str) -> User | None:
        user = self.user_repo.find_by(email=email)
        if not user:
            raise InvalidCredentialsException()

        if not self._verify_password(password, user.password):
            raise InvalidCredentialsException()

        logger.info(f"User '{user.email}' successfully authenticated")
        return self._mask_user_password(user)

    def register_user(self, dto: CreateUserDTO) -> User:
        errors: list[str] = validate_user_args(
            name=dto.name,
            surname=dto.surname,
            email=dto.email,
            dob=dto.date_of_birth,
            plaintext_password=dto.password,
        )

        if errors:
            logger.error(f"Validation failed: {errors}")
            raise ValidationException(
                resource="user",
                identifier=f"email={dto.email}",
                errors=f"Validation failed: {str(errors)}",
                user_message=f"Validation failed. Reason(s): {errors}",
            )

        # Check that the user doesn't already exist
        if self.user_repo.find_by(email=dto.email):
            raise ResourceAlreadyExistsException(
                resource="user",
                identifier=f"email={dto.email}",
                user_message="An account with this email already exists"
            )

        password_hash = self._hash_password(dto.password)

        if dto.password == password_hash:
            raise ValidationException(
                resource="user",
                identifier=f"email={dto.email}",
                errors="Password and hashed password are the same",
            )

        user = User(
            id=-1,
            name=dto.name,
            surname=dto.surname,
            email=dto.email,
            password=password_hash,
            date_of_birth=dto.date_of_birth,
            membership=dto.membership,
            created_at=None,
            updated_at=None,
        )
        created_user: User = self.user_repo.create(user)

        logger.info(f"User '{created_user.email}', ID {created_user.id} successfully registered")

        return self._mask_user_password(created_user)

    def _hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt(rounds=self.hashing_rounds)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def _verify_password(self, plaintext: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plaintext.encode("utf-8"), hashed_password.encode("utf-8"))

    def update_user(self, email: str, dto: UpdateUserDTO) -> User:
        user: User = self.get_user_by_email(email)

        # TODO: Needs testing
        for field, value in dto.to_dict().items():
            if field == "password":
                continue
            setattr(user, field, value)

        errors: list[str] = validate_user_args(
            name=user.name,
            surname=user.surname,
            email=user.email,
            dob=user.date_of_birth,
        )
        if errors:
            raise ValidationException(
                resource="user",
                identifier=f"email={user.email}",
                errors=f"Validation failed: {errors}",
            )

        updated_user = self.user_repo.update(user.id, user)
        logger.info(f"User '{updated_user.email}' successfully updated")
        return self._mask_user_password(updated_user)

    def change_user_password(self, email: str, new_password: str) -> User:
        user: User = self.get_user_by_email(email)

        if not is_valid_password(new_password):
            raise ValidationException(
                resource="user",
                identifier=f"email={user.email}",
                errors="Password is not valid",
                user_message=PWD_REQUIREMENTS,
            )

        user.password = self._hash_password(new_password)
        updated_user = self.user_repo.update(user.id, user)
        logger.info(f"User '{updated_user.email}' password successfully updated")
        return self._mask_user_password(updated_user)

    def _mask_user_password(self, user: User) -> User:
        user.password = "****"
        return user
