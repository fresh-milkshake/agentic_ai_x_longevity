from pathlib import Path

import requests

from src.filtering.downloaders.base import BaseDownloader
from src.utils import logger


class USPTODownloader(BaseDownloader):
    def run(self, patent_id: str, output_dir: Path, filename: str) -> bool:
        uspto_url = f"https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/{patent_id}"

        logger.info(f"Пробую скачать PDF напрямую с USPTO: {uspto_url}")
        try:
            response = requests.get(uspto_url, timeout=30)
            if response.status_code == 200 and response.headers.get(
                "Content-Type", ""
            ).lower().startswith("application/pdf"):
                with open(output_dir / f"{filename}.pdf", "wb") as f:
                    f.write(response.content)
                logger.info(f"PDF сохранён как {output_dir / filename} (USPTO)")
                return True
            else:
                logger.warning(
                    f"Не удалось скачать PDF (status={response.status_code}, content-type={response.headers.get('Content-Type')})"
                )
        except Exception as e:
            logger.error(f"Ошибка при скачивании PDF с USPTO: {e}")
        return False
