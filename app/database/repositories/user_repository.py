import logging

import pymysql
from pymysql import IntegrityError

from app.database.connection import ConnectionPool, get_pool
from app.database.repositories.base_repository import BaseRepository, T
from app.exceptions.business_logic import ResourceNotFoundException
from app.exceptions.database import IntegrityConstraintException, DatabaseException
from app.models.user import User

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository[User]):
    def __init__(self):
        self.pool: ConnectionPool = get_pool()

    def find_by_id(self, entity_id: int) -> User | None:
        query = """
                SELECT *
                FROM user
                WHERE id = %s
                """
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)

                cursor.execute(query, (entity_id,))

                row = cursor.fetchone()

                return User.from_db_row(row) if row else None

        except Exception as e:
            logger.error(f"Failed to find user by id: {e}")
            raise DatabaseException(
                original_exception=e,
                resource="find by id user",
                identifier=f"id={entity_id}",
                query=query
            ) from e

    # By default, sort by created_at DESC
    def find_all(self, limit: int, offset: int, sort_by: str | None) -> list[T]:
        sort_clause = f"ORDER BY {sort_by}" if sort_by else "ORDER BY created_at DESC"
        query = f"""
                SELECT * FROM user {sort_clause} LIMIT {limit} OFFSET {offset}
                """

        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute(query, (limit, offset))

                rows = cursor.fetchall()

                return [
                    User.from_db_row(user)
                    for user in rows
                ]

        except Exception as e:
            logger.error(f"Failed to find all users: {e}")
            raise DatabaseException(
                original_exception=e,
                resource="find all users",
                query=query,
            ) from e

    def create(self, user: User) -> User:
        query = """
                INSERT INTO user (name, surname, email, password, date_of_birth, membership)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)

                cursor.execute(
                    query,
                    (
                        user.name,
                        user.surname,
                        user.email,
                        user.password,
                        user.date_of_birth,
                        user.membership.name,
                    ),
                )
                conn.commit()

                user_id = cursor.lastrowid

                logger.debug(f"Created user {user} with id={user_id}")

                return self.find_by_id(entity_id=user_id)

        except IntegrityError as e:
            logger.error(f"Integrity error creating user: {e}")
            raise IntegrityConstraintException(
                constraint="UNIQUE",  # TODO: Somehow detect it?
                field="user",
                original_exception=e,
                resource="create user",
                identifier=f"email={user.email}",
                query=query
            ) from e

        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise DatabaseException(
                original_exception=e,
                resource="user",
                identifier=f"email={user.email}",
                query=query
            ) from e

    def update(self, entity_id: int, user: User) -> User:
        query = """
                UPDATE user
                SET name          = %s,
                    surname       = %s,
                    email         = %s,
                    password      = %s,
                    date_of_birth = %s,
                    membership    = %s
                WHERE id = %s
                """

        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute(
                    query,
                    (
                        user.name,
                        user.surname,
                        user.email,
                        user.password,
                        user.date_of_birth,
                        user.membership.name,
                        entity_id,
                    ),
                )

                affected_rows = cursor.rowcount
                if affected_rows == 0:
                    raise ResourceNotFoundException(
                        resource="user",
                        identifier=f"id={entity_id}",
                        query=query,
                    )

                return self.find_by_id(entity_id=entity_id)

        except ResourceNotFoundException:
            raise

        except Exception as e:
            raise DatabaseException(
                original_exception=e,
                resource="update user",
                identifier=f"id={entity_id}",
                query=query,
            ) from e

    def delete(self, entity_id: int) -> bool:
        query = f"""
                    DELETE FROM user WHERE id = %s
                    """

        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute(query, (entity_id,))
                affected_rows = cursor.rowcount
                if affected_rows == 0:
                    raise ResourceNotFoundException(
                        resource="user",
                        identifier=f"id={entity_id}",
                        query=query
                    )
                return affected_rows > 0

        except Exception as e:
            raise DatabaseException(
                original_exception=e,
                resource="delete user",
                identifier=f"id={entity_id}",
                query=query,
            )

    def find_by(self, **kwargs) -> T | None:
        # Example: repo.find_by(hotel_name="Frostel", room_number=101)
        # keys: hotel_name, room_number
        # values: Frostel, 101
        where_clauses = [f"{key} = %s" for key in kwargs.keys()]
        where_sql = " AND ".join(where_clauses)
        values = list(kwargs.values())

        query = f"""
                    SELECT * FROM user WHERE {where_sql} LIMIT 1
                    """
        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute(query, values)
                row = cursor.fetchone()
                return User.from_db_row(row) if row else None

        except Exception as e:
            logger.error(f"Failed to find user by {kwargs}: {e}")
            raise DatabaseException(
                original_exception=e,
                resource="find by user",
                identifier=f"{kwargs}",
                find_by_args=kwargs,
                query=query
            ) from e

    def count(self, **kwargs) -> int:
        where_clauses = [f"{key} = %s" for key in kwargs.keys()]
        where_sql = " AND ".join(where_clauses)
        values = list(kwargs.values())

        query = f"""
                SELECT COUNT(*) FROM user WHERE {where_sql}
        """

        try:
            with self.pool.get_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute(query, values)

                result = cursor.fetchone()
                return result["count"] if result else 0

        except Exception as e:
            logger.error(f"Failed to count users by {kwargs}: {e}")
            raise DatabaseException(
                original_exception=e,
                resource="count users",
                identifier=f"{kwargs}",
                count_args=kwargs,
                query=query,
            ) from e

    def exists(self, **kwargs) -> bool:
        return self.count(**kwargs) > 0

    def create_many(self, users: list[T]) -> list[T]:
        return [self.create(user) for user in users]

    def delete_many(self, entity_ids: list[int]) -> int:
        return sum(self.delete(entity_id) for entity_id in entity_ids)
