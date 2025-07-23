from pathlib import Path
from loguru import logger

from src.constants.general import LOGS_DIR, TERMINAL_LOGGING_LEVEL
from datetime import datetime

current_date = datetime.now().strftime("%Y-%m-%d")
logger.remove()
logger.add(lambda msg: print(msg, end=""), level=TERMINAL_LOGGING_LEVEL, colorize=True)
logger.add(
    LOGS_DIR / f"{current_date}.log",
    rotation="10 MB",
    retention="10 days",
    level="DEBUG",
    mode="a",
)


def cut_str(string: str | Path, max_length: int = 25, suffix: str = "...") -> str:
    """
    Обрезает строку до указанной длины
    
    Args:
        string: Строка для обрезки
        max_length: Максимальная длина строки
        suffix: Суффикс, который добавляется к строке, если она превышает max_length
        
    Returns:
        str: Обрезанная строка
    """
    try:
        if not isinstance(string, str):
            string = str(string)
    except Exception as e:
        logger.error(f"Ошибка при преобразовании строки: {e}")
        return ""

    if len(string) > max_length:
        return string[:max_length] + suffix
    return string


def patent_id_to_uspto_id(patent_id: str | int) -> str:
    """
    Преобразует ID патента в формат USPT
    
    Пример:
    `11111111 --> US11111111B2`
    
    Args:
        patent_id: ID патента
        
    Returns:
        str: ID патента в формате USPT
    """
    return f"US{patent_id}B2"
