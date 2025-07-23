"""
Модуль для обработки текста и патентов на разных этапах

Публичные классы:
- Pipeline: Класс для обработки текста
- TxtDocument: Класс для работы с текстовыми документами
- ExtractionResults: Класс для хранения результатов извлечения текста
- ImagePreprocessor: Класс для обработки изображений
- OCRConfigEnum: Перечисление для настроек OCR
- OCRConfig: Класс для настроек OCR
- PDFTextExtractor: Класс для извлечения текста из PDF-документов
"""

from .llm_models import DEFAULT_MODEL
from .pipeline import Pipeline
from .txt_reader import TxtDocument
from .text_extraction import (
    ExtractionResults,
    ImagePreprocessor,
    OCRConfigEnum,
    OCRConfig,
    PDFTextExtractor,
)

__all__ = [
    "DEFAULT_MODEL",
    "Pipeline",
    "TxtDocument",
    "ExtractionResults",
    "ImagePreprocessor",
    "OCRConfigEnum",
    "OCRConfig",
    "PDFTextExtractor",
]