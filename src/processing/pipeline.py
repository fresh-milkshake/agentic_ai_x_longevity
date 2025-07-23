from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel
from agents import Agent, RunResult, Runner, ModelBehaviorError
from src.constants import RESULTS_INTERMEDIATE_DIR
from src.processing.llm_models import DEFAULT_MODEL
from src.processing.txt_reader import Page, TxtDocument
from src.utils import logger
from openai import OpenAI

llama_client = OpenAI(base_url="http://80.209.242.40:8000/", api_key="dummy-key")


class SearcherAgentResults(BaseModel):
    """
    does_contain_interactions : содержит ли текст взаимодействия
    accuracy                  : уверенность в ответе
    """
    
    does_contain_interactions: bool
    accuracy: float


class InteractionParameters(BaseModel):
    """
    Ki   : константа ингибирования (характеризует силу связывания лиганда с белком)
    IC50 : концентрация вещества, при которой наблюдается 50% ингибирование активности
    Kd   : константа диссоциации комплекса лиганда и белка
    EC50 : концентрация, вызывающая 50% максимального эффекта
    """

    Ki: float | None
    IC50: float | None
    Kd: float | None
    EC50: float | None


class LigandProteinInteraction(BaseModel):
    """
    ligand            : название лиганда
    protein           : название белка
    interaction_type  : тип взаимодействия
    context           : контекст взаимодействия
    parameters        : параметры взаимодействия
    """
    ligand: str
    protein: str
    interaction_type: str
    context: str
    parameters: InteractionParameters


class BioinfAgentResults(BaseModel):
    """
    interactions : список взаимодействий
    """
    interactions: list[LigandProteinInteraction]


class SupervisorAgentResults(BaseModel):
    """
    is_correct   : корректность результата
    fixable      : можно ли исправить результат
    explanation  : объяснение
    """
    is_correct: bool
    fixable: bool
    explanation: str | None


@dataclass
class Pagedata:
    """
    page         : страница
    interactions : результат обработки страницы
    """
    page: Page
    interactions: BioinfAgentResults


@dataclass
class PipelineResult:
    """
    interactions : список страниц с результатами обработки
    """
    interactions: list[Pagedata]


class Pipeline:
    def __init__(
        self, txt_document: TxtDocument, output_dir: Path = RESULTS_INTERMEDIATE_DIR
    ):
        if not isinstance(txt_document, TxtDocument):
            logger.error("txt_document must be an instance of TxtDocument")
            raise ValueError("txt_document must be an instance of TxtDocument")

        logger.info(f"Инициализация Pipeline для документа: {txt_document}")
        self.txt_document = txt_document
        self.output_dir = output_dir

        self.runner = Runner()

        self.searcher_agent = Agent(
            name="SearcherAgent",
            instructions="""
            You are an expert in the field of bioinformatics.
            You are given a text and you need to determine if it contains any ligand-protein interactions.
            One of the most important things is to determine if there are any parameters of the interactions like Ki, IC50, Kd, EC50.
            If there are, you need to return True.
            You need to return a boolean value and a confidence score.
            Confidence score is a number between 0 and 1, where 1 means 100% confidence that the text contains ligand-protein interactions.
            If you are not sure, return 0.5.
            """,
            model=DEFAULT_MODEL,
            output_type=SearcherAgentResults,
        )

        self.bioinf_agent = Agent(
            name="BioinfAgent",
            instructions="""
            You are a bioinformatics expert.
            You are given a text and you need to extract all mentions of ligand-protein interactions.
            For each interaction, you need to specify:
            - The parameters of the interaction (Ki, IC50, Kd, EC50) (some could be missing)
            - The name or identifier of the ligand
            - The name or identifier of the protein
            - A description of the type of interaction (e.g., binding, inhibition, etc.)
            - The context or a quote from the text where this interaction is described
            Note that parameters HAVE TO BE taken from the text, and not calculated or imagined!
            """,
            model=DEFAULT_MODEL,
            output_type=BioinfAgentResults,
        )

        self.supervisor_agent = Agent(
            name="SupervisorAgent",
            instructions="""
            You are a very strict supervisor of the BioinfAgent.
            You are given a text and structured output of the BioinfAgent, which is a list of ligand-protein interactions.
            You need to check the output correctness and provide an explanation for your decision.
            If output could be easily fixed, note that in the fixable field.
            Correctness means:
            - No mentions of patent numbers, dates, etc., and other non-biological information
            - All ligands and proteins are mentioned are correct.
            - No usage of don't know, unknown, etc.
            - Note that some parameters could be missing, but not all of them
            """,
            model=DEFAULT_MODEL,
            output_type=SupervisorAgentResults,
        )

        self.fix_agent = Agent(
            name="FixAgent",
            instructions="""
            You are a fixer of the BioinfAgent.
            You are given a text and structured output of the BioinfAgent and a decision of the SupervisorAgent.
            You need to fix the output based on the explanation of the SupervisorAgent.
            """,
            model=DEFAULT_MODEL,
            output_type=BioinfAgentResults,
        )
        
    def use_runner_safely(self, agent: Agent, input: str, max_attempts: int = 3) -> RunResult:
        try:
            return self.runner.run_sync(agent, input)
        except ModelBehaviorError as e:
            logger.error(f"Модель некорректно сформировала ответ: {e}")
            if max_attempts > 0:
                return self.use_runner_safely(agent, input, max_attempts - 1)
            else:
                raise e

    def review_bioinf_agent(self, page: Page, result: BioinfAgentResults):
        repeates = 2
        for i in range(repeates):
            logger.debug(f"Запуск агента-супервайзера (проход {i + 1}/{repeates})")
            supervisor_result = self.use_runner_safely(
                self.supervisor_agent, f"{page.text}\n\n{result}"
            )
            logger.debug(
                f"Агент-супервайзер завершил обработку страницы. Результат: {supervisor_result.final_output}"
            )

            supervisor_decision: SupervisorAgentResults = supervisor_result.final_output

            if not supervisor_decision.is_correct:
                logger.debug(
                    f"Результат некорректен: {supervisor_decision.explanation}\n\nInteractions: {result}"
                )

                if supervisor_decision.fixable:
                    logger.debug("Запуск агента-исправления")
                    fix_result = self.use_runner_safely(
                        self.fix_agent,
                        f"{page.text}\n\n{result}\n\n{supervisor_decision.explanation}",
                    )
                    logger.debug("Агент-исправления завершил обработку страницы")
                    return self.review_bioinf_agent(page, fix_result.final_output)
                else:
                    return None

        return result

    def search_interactions(self, page: Page) -> BioinfAgentResults:
        logger.debug("Запуск агента-биоинформатика")
        result = self.use_runner_safely(self.bioinf_agent, page.text)
        logger.debug(
            f"Агент-биоинформатик завершил обработку страницы. Найдено {len(result.final_output.interactions)} взаимодействий"
        )
        return result.final_output

    def should_search_interactions(self, page: Page) -> bool:
        logger.debug("Запуск агента-поиска")
        result = self.use_runner_safely(self.searcher_agent, page.text)
        logger.debug("Агент-поиск завершил обработку страницы")

        decision: SearcherAgentResults = result.final_output
        if not decision.does_contain_interactions or decision.accuracy < 0.5:
            decision_text = (
                "Содержит" if decision.does_contain_interactions else "Не содержит"
            )
            logger.debug(
                f"Агент-поиск не обнаружил взаимодействий на странице {page.number}. Решение агента: {decision_text}, уверенность: {decision.accuracy * 100}%"
            )
            return False

        return True

    def process_page(self, page: Page):
        if not self.should_search_interactions(page):
            return None

        interactions = self.search_interactions(page)
        result = self.review_bioinf_agent(page, interactions)
        return result

    def run(self) -> PipelineResult:
        """
        Запуск обработки документа

        Returns:
            PipelineResult: Результат обработки документа
        """
        
        interactions = []
        for idx, page in enumerate(self.txt_document.pages):
            logger.info(f"Обработка страницы {idx + 1}/{len(self.txt_document)}")
            result = self.process_page(page)
            if result is None:
                logger.warning(
                    f"Супервайзер обнаружил ошибки в результате на странице {idx + 1}. Пропуск страницы."
                )
                continue
            logger.success(
                f"Извлечено {len(result.interactions)} взаимодействий на странице {idx + 1}"
            )
            interactions.append(Pagedata(page=page, interactions=result))

        logger.info(f"Обработка завершена для документа: {self.txt_document.name}")
        return PipelineResult(interactions=interactions)
