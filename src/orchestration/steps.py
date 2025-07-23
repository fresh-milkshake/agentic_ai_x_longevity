import pickle
from pathlib import Path
from typing import Any, Dict, Generator

import pandas as pd

from src.constants.general import (
    RESULTS_FINAL_DIR,
    RESULTS_INTERMEDIATE_DIR,
    USPT_API_KEY,
)
from src.filtering import PatentsRegistry
from src.orchestration.checkpoint import CheckpointManager
from src.orchestration.flow import GeneratorStep, Step
from src.processing.pipeline import Pipeline
from src.processing.text_extraction import extract_texts
from src.processing.txt_reader import TxtDocument
from src.utils import cut_str, logger, patent_id_to_uspto_id


class CheckPatentsStep(Step):
    def __init__(self, patent_per_batch: int):
        super().__init__("check_patents")
        self.patent_per_batch = patent_per_batch

    def execute(
        self, context: Dict[str, Any], checkpoint_manager: CheckpointManager
    ) -> Dict[str, Any]:
        documents_path = Path(context["documents_path"])
        patents_amount = len(list(documents_path.glob("*.pdf")))

        if patents_amount == 0:
            logger.info("Патентов не найдено, скачивание...")
            self._download_patents(self.patent_per_batch, documents_path)
        elif patents_amount < self.patent_per_batch:
            logger.info(
                f"Патентов меньше чем {self.patent_per_batch}, скачивание дополнительных..."
            )
            self._download_patents(
                self.patent_per_batch - patents_amount, documents_path
            )
        else:
            logger.info(f"Патентов найдено: {patents_amount}, скачивание не требуется")

        return context

    def _download_patents(self, amount: int, to_dir: Path) -> None:
        assert USPT_API_KEY, "USPT_API_KEY is not set"
        patents_registry = PatentsRegistry(api_key=USPT_API_KEY)
        patents = patents_registry.get_patents_by_query(
            query="protein binding", limit=amount
        )
        for patent in patents:
            patents_registry.download_document(
                patent_id=patent.id,
                path=to_dir,
                filename=patent_id_to_uspto_id(patent.id),
            )


class ExtractTextsStep(Step):
    def __init__(self):
        super().__init__("extract_texts")

    def execute(
        self, context: Dict[str, Any], checkpoint_manager: CheckpointManager
    ) -> Dict[str, Any]:
        documents_path = Path(context["documents_path"])
        results = extract_texts(documents_path)
        logger.info(
            f"Извлечено {results.count_total} текстов за {results.time_taken:.2f} секунд"
        )

        context["extraction_results"] = results
        return context


class CollectDocumentsStep(Step):
    def __init__(self):
        super().__init__("collect_documents")

    def execute(
        self, context: Dict[str, Any], checkpoint_manager: CheckpointManager
    ) -> Dict[str, Any]:
        results = context["extraction_results"]
        all_docs = []

        for new_text in results.new_txts:
            doc = TxtDocument(new_text)
            logger.success(f"+ {cut_str(doc.name)} ({len(doc)} страниц)")
            all_docs.append(doc)
        for old_text in results.old_txts:
            doc = TxtDocument(old_text)
            logger.info(f"  {cut_str(doc.name)} ({len(doc)} страниц)")
            all_docs.append(doc)

        context["all_documents"] = [doc.name for doc in all_docs]
        context["document_objects"] = all_docs
        return context


class ProcessDocumentsStep(GeneratorStep):
    def __init__(self):
        super().__init__("process_documents")

    def execute_generator(
        self, context: Dict[str, Any], checkpoint_manager: CheckpointManager
    ) -> Generator[Dict[str, Any], None, None]:
        docs = context.get("document_objects", [])
        processed_docs = context.get("processed_documents", [])

        # Фильтруем уже обработанные документы
        docs_to_process = [doc for doc in docs if doc.name not in processed_docs]

        logger.info(f"Нужно обработать: {len(docs_to_process)} документов")

        for i, text_file in enumerate(docs_to_process):
            logger.info(
                f"Обработка документа ({i+1}/{len(docs_to_process)}): {cut_str(text_file.name)}"
            )

            pipeline = Pipeline(
                txt_document=text_file,
                output_dir=RESULTS_INTERMEDIATE_DIR,
            )
            results = pipeline.run()

            if not results:
                logger.warning(f"Не удалось обработать документ: {text_file.name}")
                continue

            context["current_pipeline_results"] = results
            context["current_filename"] = text_file.name

            # Добавляем в список обработанных
            processed_docs.append(text_file.name)
            context["processed_documents"] = processed_docs

            yield context

    def execute(
        self, context: Dict[str, Any], checkpoint_manager: CheckpointManager
    ) -> Dict[str, Any]:
        # Для обычного выполнения собираем все результаты
        for updated_context in self.execute_generator(context, checkpoint_manager):
            context = updated_context
        return context


class SaveResultsStep(Step):
    def __init__(self):
        super().__init__("save_results")

    def execute(
        self, context: Dict[str, Any], checkpoint_manager: CheckpointManager
    ) -> Dict[str, Any]:
        filename = context["current_filename"]
        results = context["current_pipeline_results"]

        # Промежуточные результаты
        if not RESULTS_INTERMEDIATE_DIR.exists():
            RESULTS_INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Сохранение промежуточных результатов для документа: {filename}")
        with open(RESULTS_INTERMEDIATE_DIR / f"{filename}.pkl", "wb") as f:
            pickle.dump(results, f)

        # Финальные результаты
        if not RESULTS_FINAL_DIR.exists():
            RESULTS_FINAL_DIR.mkdir(parents=True, exist_ok=True)

        logger.info(f"Сохранение результатов для документа: {filename}")

        data = []
        for pagedata in results.interactions:
            page = pagedata.page
            page_number = getattr(page, "number", "")
            interactions = pagedata.interactions.interactions

            if not interactions:
                data.append(
                    {
                        "page_number": page_number,
                        "ligand": "",
                        "protein": "",
                        "interaction_type": "",
                        "context": "",
                        "Ki": "",
                        "IC50": "",
                        "Kd": "",
                        "EC50": "",
                    }
                )
            else:
                for interaction in interactions:
                    params = interaction.parameters
                    data.append(
                        {
                            "page_number": page_number,
                            "ligand": interaction.ligand,
                            "protein": interaction.protein,
                            "interaction_type": interaction.interaction_type,
                            "context": interaction.context,
                            "Ki": getattr(params, "Ki", ""),
                            "IC50": getattr(params, "IC50", ""),
                            "Kd": getattr(params, "Kd", ""),
                            "EC50": getattr(params, "EC50", ""),
                        }
                    )

        df = pd.DataFrame(data)
        df.to_csv(RESULTS_FINAL_DIR / f"{filename}.csv", index=False, encoding="utf-8")

        return context
