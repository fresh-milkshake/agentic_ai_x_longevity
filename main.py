import os
import dotenv
from loguru import logger
from src.orchestrator import Orchestrator

dotenv.load_dotenv()

USPT_API_KEY = os.getenv("USPT_API_KEY")

if not USPT_API_KEY:
    logger.error("USPT_API_KEY is not set")
    exit(1)
        

if __name__ == "__main__":
    orchestrator = Orchestrator()
    orchestrator.run()