from abc import ABC, abstractmethod

from pathlib import Path

class BaseDownloader(ABC):
    @abstractmethod
    def run(self, patent_id: str, output_dir: Path, filename: str) -> bool:
        pass