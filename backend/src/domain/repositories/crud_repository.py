from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.domain.entities.crud import DataListResponse, DataResponse


class ICRUDRepository(ABC):
    @abstractmethod
    def get_one_by_id(self, record_id: str) -> DataResponse:
        """Retrieve a single record by primary key / ObjectId."""

    @abstractmethod
    def get_list(
        self,
        page: int = 1,
        page_size: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> DataListResponse:
        """Retrieve a paginated list of records with accurate total_data & total_page."""

    @abstractmethod
    def create(self, payload: dict[str, Any]) -> DataResponse:
        """Create a new record and return it wrapped in DataResponse."""

    @abstractmethod
    def update(self, record_id: str, payload: dict[str, Any]) -> DataResponse:
        """Update an existing record by ID and return the updated DataResponse."""

    @abstractmethod
    def delete(self, record_id: str) -> None:
        """Delete an existing record by ID."""

    @abstractmethod
    def describe_data_source(self) -> dict[str, Any]:
        """Return the Avro schema dictionary describing this data source."""
