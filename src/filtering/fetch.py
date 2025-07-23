from pathlib import Path
import requests
from copy import deepcopy
from src.models import Patent
from loguru import logger
from typing import Any, List, Optional


class USPTO:
    """
    Класс для работы с PatentsView API (USPTO): поиск и получение патентов по id.
    """

    API_ENDPOINT: str = "https://search.patentsview.org/api/v1/"

    def __init__(self, api_key: str) -> None:
        """
        :param api_key: Ваш API-ключ PatentsView
        """
        self.api_key = api_key
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Api-Key": self.api_key,
            }
        )
        logger.info("USPTO client инициализирован с переданным API-ключом.")

    @property
    def headers(self) -> dict:
        """Текущие заголовки с API-ключом."""
        logger.debug(f"Текущие заголовки с API-ключом: {self._session.headers}")
        return deepcopy(self._session.headers)

    def _get_patents_request(
        self,
        q: dict,
        limit: int = 10,
    ) -> List[Patent]:
        url = self.API_ENDPOINT + "patent/"
        data: dict = {
            "f": [
                "patent_id",
                "patent_title",
                "patent_abstract",
                "patent_date",
            ],
            "o": {"size": limit, "pad_patent_id": False, "exclude_withdrawn": True},
            "q": q,
            "s": [{"patent_id": "asc"}],
        }
        logger.info(f"Отправка запроса к USPTO: url={url}, limit={limit}")
        logger.debug(f"Тело запроса: {data}")
        try:
            response = self._session.post(url=url, json=data, timeout=15)
            logger.debug(f"Ответ от USPTO: status_code={response.status_code}")
            response.raise_for_status()
            resp_data: dict[str, dict[str, Any]] = response.json()
            logger.debug(f"Полученные данные: {resp_data}")
            patents: List[Patent] = []
            for p in resp_data.get("patents", []):
                patent = Patent(
                    patent_id=p.get("patent_id", ""),
                    patent_title=p.get("patent_title", ""),
                    patent_abstract=p.get("patent_abstract"),
                    patent_date=p.get("patent_date"),
                )
                patents.append(patent)
            logger.info(f"Найдено патентов: {len(patents)}")
            return patents
        except Exception as e:
            logger.debug(f"Заголовки ответа: {getattr(response, 'headers', None)}")
            logger.error(f"USPTO API error: {e}")
            return []

    def __repr__(self) -> str:
        return f"<USPTO(api_key={'***' if self.api_key else None})>"

    def get_patents_by_query(self, query: str, limit: int = 10) -> List[Patent]:
        """
        Поиск патентов по ключевым словам title/abstract (POST-запрос).

        Args:
            query: Ключевые слова для поиска
            limit: Максимальное число патентов

        Returns:
            Список объектов Patent
        """
        logger.info(f"Поиск патентов по ключевым словам: '{query}', limit={limit}")
        return self._get_patents_request({"_text_any": {"patent_title": query}}, limit)

    def get_patent_by_id(self, patent_id: str) -> Optional[Patent]:
        """
        Получить патент по его patent_id (POST-запрос).

        Args:
            patent_id: Идентификатор патента

        Returns:
            Patent или None
        """
        logger.info(f"Запрос патента по patent_id: {patent_id}")
        result = self._get_patents_request({"patent_id": patent_id}, 1)
        if result:
            logger.debug(f"Патент найден: {result[0]}")
            return result[0]
        else:
            logger.info(f"Патент с patent_id={patent_id} не найден.")
            return None

    def download_document(self, patent_id: str, path, filename: str) -> None:
        """
        Скачать PDF-документ по патенту по его patent_id и сохранить в path/filename
        """
        if not isinstance(path, Path):
            path = Path(path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

        uspto_url = f"https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/{patent_id}"

        logger.info(f"Пробую скачать PDF напрямую с USPTO: {uspto_url}")
        try:
            response = requests.get(uspto_url, timeout=30)
            if response.status_code == 200 and response.headers.get(
                "Content-Type", ""
            ).lower().startswith("application/pdf"):
                with open(path / filename, "wb") as f:
                    f.write(response.content)
                logger.info(f"PDF сохранён как {path / filename} (USPTO)")
                return
            else:
                logger.warning(
                    f"Не удалось скачать PDF (status={response.status_code}, content-type={response.headers.get('Content-Type')})"
                )
        except Exception as e:
            logger.error(f"Ошибка при скачивании PDF с USPTO: {e}")
