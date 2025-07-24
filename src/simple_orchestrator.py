from pathlib import Path
import pickle
from src.processing.txt_reader import TxtDocument
from src.processing.pipeline import Pipeline, PipelineResult
from src.constants.general import (
    PATENTS_DIR,
    RESULTS_INTERMEDIATE_DIR,
    RESULTS_FINAL_DIR,
    USPT_API_KEY,
)
from src.processing.text_extraction import ExtractionResults, extract_texts
from src.utils import cut_str, logger, patent_id_to_uspto_id
from src.filtering import PatentsRegistry
import pandas as pd


class Orchestrator:
    def __init__(self, patent_per_batch: int):
        self.patent_per_batch = patent_per_batch

    def run(self) -> None:
        logger.info("Запуск оркестратора")

        self._check_patents(PATENTS_DIR)
        results = self._extract_texts(PATENTS_DIR)
        all_docs = self._collect_documents(results)
        self._process_documents(all_docs)

    def _check_patents(self, documents_path: Path) -> None:
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

    def _extract_texts(self, documents_path: Path) -> ExtractionResults:
        results = extract_texts(documents_path)
        logger.info(
            f"Извлечено {results.count_total} текстов за {results.time_taken:.2f} секунд:"
        )
        return results

    def _collect_documents(self, results: ExtractionResults) -> list[TxtDocument]:
        all_docs: list[TxtDocument] = []
        for new_text in results.new_txts:
            doc = TxtDocument(new_text)
            logger.success(f"+ {cut_str(doc.name)} ({len(doc)} страниц)")
            all_docs.append(doc)
        for old_text in results.old_txts:
            doc = TxtDocument(old_text)
            logger.info(f"  {cut_str(doc.name)} ({len(doc)} страниц)")
            all_docs.append(doc)
        return all_docs

    def _process_documents(self, docs: list[TxtDocument]):
        for text_file in docs:
            logger.info(f"Обработка документа: {text_file.name}")
            pipeline = Pipeline(
                txt_document=text_file,
                output_dir=RESULTS_INTERMEDIATE_DIR,
            )
            results = pipeline.run()

            if not results:
                logger.warning(f"Не удалось обработать документ: {text_file.name}")
                continue

            self._save_results(text_file.name, results)
        logger.success("Обработка завершена")

    def _save_results(self, filename: str, results: PipelineResult):
        if not RESULTS_INTERMEDIATE_DIR.exists():
            RESULTS_INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Сохранение промежуточных результатов для документа: {filename}")
        with open(f"{RESULTS_INTERMEDIATE_DIR}/{filename}.pkl", "wb") as f:
            pickle.dump(results, f)

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

        df = pd.DataFrame(
            data,
            columns=[
                "page_number",
                "ligand",
                "protein",
                "interaction_type",
                "context",
                "Ki",
                "IC50",
                "Kd",
                "EC50",
            ],
        )
        df.to_csv(RESULTS_FINAL_DIR / f"{filename}.csv", index=False, encoding="utf-8")
