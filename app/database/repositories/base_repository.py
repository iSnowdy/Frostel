from abc import ABC, abstractmethod
from typing import TypeVar, Generic

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    # Find by PK
    @abstractmethod
    def find_by_id(self, entity_id: int) -> T | None:
        raise NotImplementedError

    @abstractmethod
    def find_all(self, limit: int, offset: int, sort_by: str | None) -> list[T]:
        raise NotImplementedError

    @abstractmethod
    def create(self, entity: T) -> T:
        raise NotImplementedError

    @abstractmethod
    def update(self, entity_id: int, entity: T) -> T:
        raise NotImplementedError

    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        raise NotImplementedError

    # More flexible queries

    @abstractmethod
    def find_by(self, **kwargs) -> T | None:
        """
        Example: repo.find_by(hotel_name="Frostel")
        Example: repo.find_by(name="John", age=30)
        """
        pass

    @abstractmethod
    def count(self, **kwargs) -> int:
        pass

    @abstractmethod
    def exists(self, **kwargs) -> bool:
        pass

    # Batch operations for enhanced performance. Not sure if I'll even need this
    @abstractmethod
    def create_many(self, entities: list[T]) -> list[T]:
        return [self.create(entity) for entity in entities]

    @abstractmethod
    def delete_many(self, entity_ids: list[int]) -> int:
        return sum(self.delete(entity_id) for entity_id in entity_ids)
