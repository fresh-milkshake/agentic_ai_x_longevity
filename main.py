from pathlib import Path
from src.orchestration import create_patent_orchestrator
from src.constants import PATENTS_PER_BATCH


if __name__ == "__main__":
    orchestrator = create_patent_orchestrator(patent_per_batch=PATENTS_PER_BATCH)
    orchestrator.run(initial_context={"documents_path": Path("patents")})