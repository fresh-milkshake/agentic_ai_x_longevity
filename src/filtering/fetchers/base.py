from abc import ABC, abstractmethod

from src.models import Patent


class BaseFetcher(ABC):
    @abstractmethod
    def __init__(self, api_key: str):
        self.api_key = api_key

    @abstractmethod
    def get_patents_by_query(self, query: str, limit: int) -> list[Patent]:
        pass

    @abstractmethod
    def get_patent_by_id(self, patent_id: str) -> Patent | None:
        pass
