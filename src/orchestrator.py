from src.processing.txt_reader import TxtDocument
from src.processing.pipeline import Pipeline, PipelineResult
from src.constants.general import PATENTS_DIR, RESULTS_INTERMEDIATE_DIR
from src.processing.text_extraction import ExtractionResults, extract_texts
from src.utils import cut_str, logger
import pickle


class Orchestrator:
    def __init__(self):
        pass

    def run(self):
        results = self._extract_texts()
        all_docs = self._collect_documents(results)
        self._process_documents(all_docs[3:])

    def _extract_texts(self) -> ExtractionResults:
        results = extract_texts(PATENTS_DIR)
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
            pipeline = Pipeline(text_file)
            results = pipeline.run()

            if not results:
                logger.warning(f"Не удалось обработать документ: {text_file.name}")
                continue

            self._save_results(text_file.name, results)
        logger.success("Обработка завершена")

    def _save_results(self, filename: str, results: PipelineResult):
        if not RESULTS_INTERMEDIATE_DIR.exists():
            RESULTS_INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Сохранение результатов для документа: {filename}")
        with open(f"{RESULTS_INTERMEDIATE_DIR}/{filename}.pkl", "wb") as f:
            pickle.dump(results, f)
