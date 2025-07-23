import io
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import fitz
import multiprocessing as mp
import numpy as np
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from loguru import logger

from src.utils import cut_str
from src.constants.processing import PAGE_DIVIDER
from src.constants.general import RESULTS_RAW_DIR


@dataclass
class ExtractionResults:
    new_txts: list[Path]
    old_txts: list[Path]
    count_new: int
    count_old: int
    count_total: int
    time_taken: float


@dataclass
class OCRConfig:
    """Конфигурация для OCR обработки"""

    language: str = "eng"
    dpi: int = 300
    psm: int = 6
    oem: int = 3
    enable_preprocessing: bool = True
    max_workers: int | None = None
    chunk_size: int = 4


class OCRConfigEnum:
    # Конфигурация для высокой точности
    HIGH_ACCURACY = OCRConfig(
        language="eng",
        dpi=300,
        psm=6,
        oem=3,
        enable_preprocessing=True,
        max_workers=3,
        chunk_size=2,
    )

    # Конфигурация для быстрой обработки
    FAST = OCRConfig(
        language="eng",
        dpi=200,
        psm=6,
        oem=1,
        enable_preprocessing=False,
        max_workers=4,
        chunk_size=6,
    )


PAGES_LIMIT = 50


class ImagePreprocessor:
    """Класс для предобработки изображений перед OCR"""

    @staticmethod
    def enhance_image(image: Image.Image) -> Image.Image:
        """Улучшает изображение для лучшего распознавания текста"""
        try:
            if image.mode != "RGB":
                image = image.convert("RGB")

            img_array = np.array(image)
            img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

            blurred = cv2.GaussianBlur(gray, (1, 1), 0)

            _, thresh = cv2.threshold(
                blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
            processed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)

            processed_pil = Image.fromarray(processed)

            return processed_pil

        except Exception as e:
            logger.warning(f"Ошибка при обработке изображения: {e}")
            return image

    @staticmethod
    def pil_enhance_image(image: Image.Image) -> Image.Image:
        """Альтернативная обработка через PIL (если OpenCV недоступен)"""
        try:
            if image.mode != "L":
                image = image.convert("L")

            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)

            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.2)

            image = image.filter(ImageFilter.MedianFilter(size=3))

            return image

        except Exception as e:
            logger.warning(f"Ошибка при PIL обработке изображения: {e}")
            return image


def _process_page_chunk(
    args: tuple[Path, list[int], OCRConfig],
) -> list[tuple[int, str]]:
    """Обрабатывает chunk страниц PDF"""
    document_path, page_nums, config = args
    results = []

    try:
        logger.debug(
            f"Открываем документ {document_path} для чанка страниц: {page_nums}"
        )
        pdf_document = fitz.open(document_path)
        matrix = fitz.Matrix(config.dpi / 72, config.dpi / 72)

        tesseract_config = f"--psm {config.psm} --oem {config.oem}"
        logger.debug(f"Tesseract config: {tesseract_config}")

        for page_num in page_nums:
            try:
                logger.debug(f"Загружаем страницу {page_num + 1}")
                page = pdf_document.load_page(page_num)
                pix = page.get_pixmap(matrix=matrix) # type: ignore
                img_data = pix.tobytes("ppm")
                image = Image.open(io.BytesIO(img_data))

                if config.enable_preprocessing:
                    logger.debug(
                        f"Выполняется предобработка изображения для страницы {page_num + 1}"
                    )
                    try:
                        image = ImagePreprocessor.enhance_image(image)
                    except Exception:
                        logger.debug(
                            f"OpenCV обработка не удалась, fallback на PIL для страницы {page_num + 1}"
                        )
                        image = ImagePreprocessor.pil_enhance_image(image)

                logger.debug(f"Запуск OCR для страницы {page_num + 1}")
                page_text = pytesseract.image_to_string(
                    image, lang=config.language, config=tesseract_config
                )

                if page_text.strip():
                    result = (
                        PAGE_DIVIDER.replace("%NUM%", str(page_num + 1)) + "\n"
                        + page_text.strip()
                        + "\n\n"
                    )
                else:
                    result = ""

                results.append((page_num, result))
                logger.debug(f"Обработана страница {page_num + 1}")

            except Exception as e:
                logger.warning(f"Ошибка при обработке страницы {page_num + 1}: {e}")
                results.append(
                    (page_num, f"=== ОШИБКА НА СТРАНИЦЕ {page_num + 1} ===\n")
                )

        pdf_document.close()
        logger.debug(
            f"Документ {document_path} закрыт после обработки чанка {page_nums}"
        )

    except Exception as e:
        logger.error(f"Критическая ошибка при обработке чанка: {e}")
        for page_num in page_nums:
            results.append(
                (page_num, f"=== КРИТИЧЕСКАЯ ОШИБКА НА СТРАНИЦЕ {page_num + 1} ===\n")
            )

    return results


def _create_chunks(page_nums: list[int], chunk_size: int) -> list[list[int]]:
    """Разбивает список страниц на чанки"""
    logger.debug(f"Разбиваем {len(page_nums)} страниц на чанки по {chunk_size}")
    return [page_nums[i : i + chunk_size] for i in range(0, len(page_nums), chunk_size)]


class PDFTextExtractor:
    """Основной класс для извлечения текста из PDF"""

    def __init__(self, config: OCRConfig | None = None):
        self.config = config or OCRConfig()
        if self.config.max_workers is None:
            self.config.max_workers = min(
                mp.cpu_count(), 4
            )
        logger.debug(f"PDFTextExtractor инициализирован с config: {self.config}")

    def extract_text(self, document_path: Path) -> str:
        """
        Извлекает текст из PDF документа

        Args:
            document_path: Путь к PDF файлу

        Returns:
            Извлеченный текст

        Raises:
            FileNotFoundError: Если файл не найден
            ValueError: Если файл не является PDF
            Exception: При других ошибках обработки
        """
        start_time = time.time()

        if not document_path.exists():
            raise FileNotFoundError(f"Файл не найден: {document_path}")

        if not document_path.suffix.lower() == ".pdf":
            raise ValueError("Файл должен быть в формате PDF")

        try:
            logger.debug(f"Открываем PDF для подсчета страниц: {document_path}")
            pdf_document = fitz.open(document_path)
            num_pages = len(pdf_document)
            pdf_document.close()

            if num_pages == 0:
                logger.warning("PDF документ пуст")
                return ""

            logger.info(
                f"Начинаем обработку PDF: {cut_str(document_path.name)} ({num_pages} страниц)"
            )

            page_nums = list(range(num_pages))
            chunks = _create_chunks(page_nums, self.config.chunk_size)
            logger.debug(f"Создано {len(chunks)} чанков для обработки")

            args = [(document_path, chunk, self.config) for chunk in chunks]

            results = []
            with ProcessPoolExecutor(max_workers=self.config.max_workers) as executor:
                future_to_chunk = {
                    executor.submit(_process_page_chunk, arg): i
                    for i, arg in enumerate(args)
                }
                logger.debug(f"Отправлено {len(future_to_chunk)} задач в пул процессов")

                for future in as_completed(future_to_chunk):
                    chunk_idx = future_to_chunk[future]
                    try:
                        chunk_results = future.result()
                        results.extend(chunk_results)
                        logger.info(f"Завершен чанк {chunk_idx + 1}/{len(chunks)}")
                    except Exception as e:
                        logger.error(f"Ошибка в чанке {chunk_idx + 1}: {e}")

            results.sort(key=lambda x: x[0])
            extracted_text = [r[1] for r in results]

            result_text = "".join(extracted_text).strip()

            processing_time = time.time() - start_time

            if not result_text:
                logger.warning("Не удалось извлечь текст из документа")
                return ""

            logger.success(
                f"Извлечение завершено за {processing_time:.2f}с. "
                f"Извлечено {len(result_text)} символов"
            )

            return result_text

        except Exception as e:
            logger.error(f"Критическая ошибка при обработке PDF: {e}")
            raise Exception(f"Ошибка при обработке PDF: {e}")

    def get_pages_count(self, document_path: Path) -> int:
        """
        Получает количество страниц в документе
        """
        logger.debug(f"Получаем количество страниц в документе: {document_path}")
        with fitz.open(document_path) as pdf:
            pages_count = len(pdf)
        logger.debug(f"В документе {document_path} {pages_count} страниц")
        return pages_count

    def extract_with_confidence(
        self, document_path: Path
    ) -> tuple[str, dict[str, Any]]:
        """
        Извлекает текст с информацией о качестве распознавания

        Returns:
            Tuple с текстом и метаданными (время обработки, статистика и т.д.)
        """
        start_time = time.time()
        logger.debug(f"Запуск extract_with_confidence для {document_path}")
        text = self.extract_text(document_path)
        processing_time = time.time() - start_time

        metadata = {
            "processing_time": processing_time,
            "text_length": len(text),
            "config_used": self.config,
            "pages_processed": text.count("=== СТРАНИЦА"),
            "errors_count": text.count("=== ОШИБКА"),
        }
        logger.debug(f"Метаданные извлечения: {metadata}")

        return text, metadata


def extract_texts(
    documents_path: Path,
    config: OCRConfig = OCRConfigEnum.HIGH_ACCURACY,
    export_path: Path = RESULTS_RAW_DIR,
) -> ExtractionResults:
    start_time = time.time()
    extractor = PDFTextExtractor(config)
    pdf_files = list(documents_path.glob("*.pdf"))

    if not pdf_files:
        logger.info(f"В директории {documents_path} нет PDF файлов")
        return ExtractionResults(
            new_txts=[],
            old_txts=[],
            count_new=0,
            count_old=0,
            count_total=0,
            time_taken=0,
        )

    if not export_path.exists():
        export_path.mkdir(parents=True, exist_ok=True)

    new_txts = []
    old_txts = []
    for pdf_file in pdf_files:
        try:
            logger.info(f"Обрабатываем: {cut_str(pdf_file.name)}")
            output_path = export_path / f"{pdf_file.stem}.txt"

            if output_path.exists():
                logger.info(f"Файл {cut_str(output_path)} уже существует, пропускаем")
                old_txts.append(output_path)
                continue

            page_count = extractor.get_pages_count(pdf_file)
            logger.debug(f"В файле {pdf_file.name} {page_count} страниц")
            if page_count > PAGES_LIMIT:
                logger.info(
                    f"Файл {cut_str(pdf_file.name)} содержит больше {PAGES_LIMIT} страниц, пропускаем"
                )
                continue

            logger.debug(f"Запуск извлечения текста с метаданными для {pdf_file.name}")
            text, metadata = extractor.extract_with_confidence(pdf_file)

            if text:
                logger.debug(f"Сохраняем результат в {output_path}")

                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(text)

                logger.success(
                    f"Файл {cut_str(pdf_file.name)} обработан успешно. "
                    f"Время: {metadata['processing_time']:.2f}с, "
                    f"Символов: {metadata['text_length']}, "
                    f"Страниц: {metadata['pages_processed']}, "
                    f"Ошибок: {metadata['errors_count']}"
                )
                new_txts.append(output_path)
            else:
                logger.warning(
                    f"Из файла {cut_str(pdf_file.name)} не удалось извлечь текст"
                )

        except Exception as e:
            logger.error(f"Ошибка при обработке {cut_str(pdf_file.name)}: {e}")
            continue

    return ExtractionResults(
        new_txts=new_txts,
        old_txts=old_txts,
        count_new=len(new_txts),
        count_old=len(old_txts),
        count_total=len(new_txts) + len(old_txts),
        time_taken=time.time() - start_time,
    )
