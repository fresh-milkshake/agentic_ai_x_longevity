from pathlib import Path
from src.models import Patent
from src.filtering.downloaders import (
    BaseDownloader,
    GooglePatentsDownloader,
    USPTODownloader,
)
from src.filtering.fetchers import (
    BaseFetcher,
    PatentsViewFetcher,
)
from loguru import logger


class PatentsRegistry(BaseFetcher):
    """
    Класс для работы с PatentsView API (USPTO): поиск и получение патентов по id.
    """

    _downloaders: list[type[BaseDownloader]] = [
        USPTODownloader,
        GooglePatentsDownloader,
    ]
    _fetchers: list[type[BaseFetcher]] = [
        PatentsViewFetcher,
    ]

    def __init__(self, api_key: str):
        self.api_key = api_key

        cls = self._fetchers.pop()
        self.fetcher = cls(api_key=api_key)

    def get_patent_by_id(self, patent_id: str) -> Patent | None:
        return self.fetcher.get_patent_by_id(patent_id)

    def get_patents_by_query(self, query: str, limit: int) -> list[Patent]:
        return self.fetcher.get_patents_by_query(query, limit)

    def download_document(self, patent_id: str, path: Path, filename: str) -> bool:
        """
        Скачать PDF-документ по патенту по его patent_id и сохранить в path/filename.
        """

        for downloader in self._downloaders:
            file_path = path / f"{filename}.pdf"
            if file_path.exists():
                logger.info(f"Файл {file_path} уже существует, пропускаем")
                return True
            
            logger.info(f"Скачиваем документ {patent_id} с {downloader.__name__}")
            if downloader().run(patent_id, path, filename):
                return True
        return False
