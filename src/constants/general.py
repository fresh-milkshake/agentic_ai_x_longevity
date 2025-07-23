from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv(override=True)

# API keys
USPT_API_KEY = os.getenv("USPT_API_KEY")

# Paths
PROJECT_DIR = Path(__file__).parent.parent.parent
PATENTS_DIR = PROJECT_DIR / "patents"

RESULTS_DIR = PROJECT_DIR / "results"
RESULTS_RAW_DIR = RESULTS_DIR / "raw"
RESULTS_INTERMEDIATE_DIR = RESULTS_DIR / "intermediate"
RESULTS_FINAL_DIR = RESULTS_DIR / "final"

DATA_DIR = PROJECT_DIR / "data"

# Logging
LOGS_DIR = PROJECT_DIR / "logs"
TERMINAL_LOGGING_LEVEL = "INFO"
FILE_LOGGING_LEVEL = "DEBUG"

# LLM
LLAMA_API_ENDPOINT = os.getenv("LLAMA_API_ENDPOINT")


