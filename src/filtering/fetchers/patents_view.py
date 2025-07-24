from datetime import datetime
import requests

from src.models import Patent
from src.filtering.fetchers.base import BaseFetcher
from src.constants.processing import DEFAULT_YEAR_RANGE
from loguru import logger


class PatentsViewFetcher(BaseFetcher):
    API_ENDPOINT: str = "https://search.patentsview.org/api/v1/"

    def __init__(self, api_key: str) -> None:
        """
        Инициализация клиента USPTO (PatentsView)
        
        Args:
            api_key: API-ключ PatentsView
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

    def _get_patents_request(
        self,
        q: dict,
        limit: int = 10,
    ) -> list[Patent]:
        """
        Запрос патентов по заданным критериям
        
        Args:
            q: Критерии поиска
            limit: Максимальное количество патентов
            
        Returns:
            Список объектов Patent
        """
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
        response = None
        try:
            response = self._session.post(url=url, json=data, timeout=15)
            logger.debug(f"Ответ от USPTO: status_code={response.status_code}")
            if response.status_code != 200:
                logger.error(f"Ошибка при получении патентов: {response.status_code}\n{response.text}\n{response.headers}")
                return []
            resp_data: dict[str, list[dict[str, str]]] = response.json()
            logger.debug(f"Полученные данные: {resp_data}")
            patents: list[Patent] = []
            for p in resp_data["patents"]:
                p: dict[str, str]
                patent = Patent(
                    id=p["patent_id"],
                    title=p["patent_title"],
                    abstract=p["patent_abstract"],
                    date=p["patent_date"],  # type: ignore
                )
                patents.append(patent)
            logger.info(f"Найдено патентов: {len(patents)}")
            return patents
        except Exception as e:
            if response:
                logger.debug(f"Заголовки ответа: {getattr(response, 'headers', None)}")
            logger.error(f"USPTO API error: {e}")
            logger.exception(e)
            return []

    def __repr__(self) -> str:
        return f"<PatentsViewFetcher(api_key={'***' if self.api_key else None})>"

    def get_patents_by_query(
        self, query: str, limit: int = 10, year: str = DEFAULT_YEAR_RANGE
    ) -> list[Patent]:
        """
        Поиск патентов по ключевым словам title/abstract (POST-запрос).

        Args:
            query: Ключевые слова для поиска
            limit: Максимальное число патентов

        Returns:
            Список объектов Patent
        """
        logger.info(f"Поиск патентов по ключевым словам: '{query}', limit={limit}")
        current_year = datetime.now().year
        criterion = {
            "_and": [
                {"_text_phrase": {"patent_title": query, "patent_abstract": query}},
                {
                    "_gte": {"patent_date": f"{year}-01-01"},
                    "_lte": {"patent_date": f"{current_year}-12-31"},
                },
            ]
        }
        return self._get_patents_request(criterion, limit)

    def get_patent_by_id(self, patent_id: str) -> Patent | None:
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
