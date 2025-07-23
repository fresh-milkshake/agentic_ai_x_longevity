# src/orchestration/flow.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Generator
from src.orchestration.checkpoint import CheckpointManager

class Step(ABC):
    """Базовый класс для шага обработки"""
    
    def __init__(self, name: str):
        self.name = name
        
    @abstractmethod
    def execute(self, context: Dict[str, Any], checkpoint_manager: CheckpointManager) -> Dict[str, Any]:
        """Выполняет шаг и возвращает обновленный контекст"""
        pass
    
    def should_skip(self, checkpoint_manager: CheckpointManager) -> bool:
        """Проверяет, нужно ли пропустить этот шаг"""
        return checkpoint_manager.should_skip_step(self.name)
    
    def mark_completed(self, checkpoint_manager: CheckpointManager, context: Dict[str, Any] | None = None) -> None:
        """Помечает шаг как завершенный"""
        checkpoint_manager.save_checkpoint(self.name, context)

class GeneratorStep(Step):
    """Шаг, который может генерировать промежуточные результаты"""
    
    @abstractmethod
    def execute_generator(self, context: Dict[str, Any], checkpoint_manager: CheckpointManager) -> Generator[Dict[str, Any], None, None]:
        """Выполняет шаг и генерирует промежуточные результаты"""
        pass