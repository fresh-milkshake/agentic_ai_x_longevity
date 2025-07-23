from loguru import logger

from src.constants.general import LOGS_DIR, TERMINAL_LOGGING_LEVEL
from datetime import datetime

current_date = datetime.now().strftime("%Y-%m-%d")
logger.remove()
logger.add(lambda msg: print(msg, end=""), level=TERMINAL_LOGGING_LEVEL, colorize=True)
logger.add(LOGS_DIR / f"{current_date}.log", rotation="10 MB", retention="10 days", level="DEBUG", mode="a")

def cut_str(string: str, max_length: int = 25, suffix: str = "...") -> str:
    if not isinstance(string, str):
        string = str(string)

    if len(string) > max_length:
        return string[:max_length] + suffix
    return string
