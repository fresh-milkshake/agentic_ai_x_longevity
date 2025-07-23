from typing import List, Dict, Any
from pathlib import Path
from src.orchestration.flow import Step, GeneratorStep
from src.orchestration.checkpoint import CheckpointManager
from src.utils import logger


class FlexibleOrchestrator:
    def __init__(
        self,
        steps: List[Step],
        checkpoint_file: Path = Path("checkpoints/orchestrator.pkl"),
    ):
        """
        Инициализация оркестратора

        Args:
            steps: Список шагов в порядке выполнения.
            checkpoint_file: Путь к файлу чекпоинтов.
        """
        self.steps = steps
        self.checkpoint_manager = CheckpointManager(checkpoint_file)
        self.step_names = [step.name for step in steps]

    def _get_start_index(self) -> int:
        last_completed_step = self.checkpoint_manager.get_last_step()

        if not last_completed_step:
            return 0

        try:
            last_step_index = self.step_names.index(last_completed_step)
            return last_step_index + 1
        except ValueError:
            return 0

    def run(self, initial_context: Dict[str, Any]) -> None:
        """
        Запуск оркестратора с автоматическим восстановлением прогресса

        Args:
            initial_context: Начальный контекст для выполнения
        """
        logger.info("Запуск оркестратора")

        saved_context = self.checkpoint_manager.get_saved_context()
        context = {**initial_context, **saved_context}
        start_index = self._get_start_index()

        if start_index >= len(self.steps):
            logger.success("Все шаги уже выполнены")
            self.checkpoint_manager.clear_checkpoint()
            return

        if start_index > 0:
            logger.info(f"Возобновление обработки ({start_index}/{len(self.steps)} шагов завершено)")
        else:
            logger.info(f"Новая обработка ({len(self.steps)} шагов)")

        try:
            for i in range(start_index, len(self.steps)):
                step = self.steps[i]
                step_num = i + 1

                logger.info(f"Шаг {step_num}/{len(self.steps)}: {step.name}")

                try:
                    if isinstance(step, GeneratorStep):
                        for updated_context in step.execute_generator(
                            context, self.checkpoint_manager
                        ):
                            context = updated_context
                    else:
                        context = step.execute(context, self.checkpoint_manager)

                    step.mark_completed(self.checkpoint_manager, context)
                    logger.success("Шаг завершен")

                except Exception as step_error:
                    logger.error(f"Ошибка на шаге {step.name}: {step_error}")
                    raise

            self.checkpoint_manager.clear_checkpoint()
            logger.success("Обработка успешно завершена!")

        except KeyboardInterrupt:
            logger.warning("Обработка приостановлена пользователем")
            raise
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            raise

    def reset(self) -> None:
        """Сбрасывает весь прогресс"""
        self.checkpoint_manager.clear_checkpoint()
        logger.info("Прогресс сброшен")


def create_patent_orchestrator(
    patent_per_batch: int = 10, checkpoint_file: Path = Path("checkpoints/patents.pkl")
) -> FlexibleOrchestrator:
    """
    Создает стандартный оркестратор с полным циклом работы:
    
    Поиск и скачивание патентов ->
    Извлечение текстов ->
    Сбор документов ->
    Обработка документов <-> Сохранение результатов

    Args:
        patent_per_batch: Количество патентов для обработки за раз
        checkpoint_file: Путь к файлу чекпоинтов

    Returns:
        FlexibleOrchestrator: Стандартный оркестратор с полным циклом работы
    """
    from src.orchestration.steps import (
        CheckPatentsStep,
        ExtractTextsStep,
        CollectDocumentsStep,
        ProcessDocumentsStep,
        SaveResultsStep,
    )

    steps = [
        CheckPatentsStep(patent_per_batch),
        ExtractTextsStep(),
        CollectDocumentsStep(),
        ProcessDocumentsStep(),
        SaveResultsStep(),
    ]

    return FlexibleOrchestrator(steps, checkpoint_file)


def create_document_orchestrator(
    checkpoint_file: Path = Path("checkpoints/documents.pkl"),
) -> FlexibleOrchestrator:
    """
    Создает оркестратор для обработки документов, исключая шаг поиска и скачивания патентов

    Args:
        checkpoint_file: Путь к файлу чекпоинтов

    Returns:
        FlexibleOrchestrator: Чистый оркестратор для обработки документов
    """
    from src.orchestration.steps import (
        ExtractTextsStep,
        CollectDocumentsStep,
        ProcessDocumentsStep,
        SaveResultsStep,
    )

    steps = [
        ExtractTextsStep(),
        CollectDocumentsStep(),
        ProcessDocumentsStep(),
        SaveResultsStep(),
    ]

    return FlexibleOrchestrator(steps, checkpoint_file)
