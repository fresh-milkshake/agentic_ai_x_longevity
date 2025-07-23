from pathlib import Path
from bs4 import BeautifulSoup
import requests

from src.filtering.downloaders.base import BaseDownloader
from src.utils import logger, patent_id_to_uspto_id


class GooglePatentsDownloader(BaseDownloader):
    def run(self, patent_id: str, output_dir: Path, filename: str) -> bool:
        patent_id = patent_id_to_uspto_id(patent_id)
        base_url = f"https://patents.google.com/patent/{patent_id}/en"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        logger.info(f"Попытка получить страницу патента: {base_url}")
        try:
            response = requests.get(base_url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при получении страницы патента: {e}")
            return False

        soup = BeautifulSoup(response.text, "html.parser")

        pdf_link = None
        download_button = soup.find("a", string="Download PDF")
        if download_button:
            pdf_link = download_button.get("href")  # type: ignore
        else:
            for link in soup.find_all("a", href=True):
                href = link.get("href")  # type: ignore
                if (
                    href
                    and ".pdf" in href
                    and "patentimages.storage.googleapis.com" in href
                ):
                    pdf_link = href
                    break

        if not pdf_link:
            logger.warning("Не удалось найти ссылку на PDF-файл на странице патента.")
            return False

        if not pdf_link.startswith("http"):  # type: ignore
            logger.info(
                f"Обнаружена относительная ссылка: {pdf_link}. Попытка преобразовать в абсолютную."
            )
            pdf_link = f"https://patents.google.com{pdf_link}"

        logger.info(f"Найдена ссылка на PDF: {pdf_link}")

        output_filename = output_dir / f"{filename}.pdf"
        logger.info(f"Попытка скачать PDF в: {output_filename}")
        try:
            pdf_response = requests.get(
                pdf_link,  # type: ignore
                headers=headers,
                stream=True,
                timeout=30,
            )
            pdf_response.raise_for_status()

            with open(output_filename, "wb") as f:
                for chunk in pdf_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"PDF-файл успешно скачан: {output_filename}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при скачивании PDF-файла: {e}")
            return False
