# src/orchestration/checkpoint.py
import pickle
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

class CheckpointData:
    """
    Структура данных чекпоинта
    
    Args:
        last_completed_step: Имя последнего завершенного шага
        context: Контекст выполнения
        timestamp: Время создания чекпоинта
    """
    def __init__(self, last_completed_step: str, context: Dict[str, Any], timestamp: datetime | None = None):
        self.last_completed_step = last_completed_step
        self.context = context
        self.timestamp = timestamp or datetime.now()

class CheckpointManager:
    """
    Менеджер чекпоинтов для оркестратора
    
    Args:
        checkpoint_file: Путь к файлу чекпоинтов
    """
    def __init__(self, checkpoint_file: Path):
        self.checkpoint_file = checkpoint_file
        
    def save_checkpoint(self, last_completed_step: str, context: Dict[str, Any] | None = None) -> None:
        """
        Сохраняет состояние выполнения с использованием pickle
        
        Args:
            last_completed_step: Имя последнего завершенного шага
            context: Контекст выполнения
        """
        checkpoint_data = CheckpointData(
            last_completed_step=last_completed_step,
            context=context or {},
            timestamp=datetime.now()
        )
        
        # Создаем директорию если не существует
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Сохраняем с использованием pickle
        with open(self.checkpoint_file, 'wb') as f:
            pickle.dump(checkpoint_data, f)
            
    def load_checkpoint(self) -> Optional[CheckpointData]:
        """
        Загружает сохраненное состояние из pickle
        
        Returns:
            Optional[CheckpointData]: Сохраненные данные или None, если файл не существует
        """
        if not self.checkpoint_file.exists():
            return None
            
        try:
            with open(self.checkpoint_file, 'rb') as f:
                return pickle.load(f)
        except (pickle.PickleError, FileNotFoundError, EOFError):
            # Если файл поврежден, возвращаем None
            return None
            
    def should_skip_step(self, step_name: str) -> bool:
        """
        Проверяет, нужно ли пропустить шаг
        
        Args:
            step_name: Имя шага для проверки
        
        Returns:
            bool: True, если шаг нужно пропустить, False в противном случае
        """
        checkpoint = self.load_checkpoint()
        if not checkpoint:
            return False
        return checkpoint.last_completed_step == step_name
        
    def clear_checkpoint(self) -> None:
        """
        Очищает чекпоинт после успешного завершения
        
        Returns:
            None
        """
        if self.checkpoint_file.exists():
            self.checkpoint_file.unlink()
            
    def get_last_step(self) -> Optional[str]:
        """
        Возвращает имя последнего завершенного шага
        
        Returns:
            Optional[str]: Имя последнего завершенного шага или None, если чекпоинт не существует
        """
        checkpoint = self.load_checkpoint()
        return checkpoint.last_completed_step if checkpoint else None
        
    def get_saved_context(self) -> Dict[str, Any]:
        """
        Возвращает сохраненный контекст
        
        Returns:
            Dict[str, Any]: Сохраненный контекст или пустой словарь, если чекпоинт не существует
        """
        checkpoint = self.load_checkpoint()
        return checkpoint.context if checkpoint and checkpoint.context else {}