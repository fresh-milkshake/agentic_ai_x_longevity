import gradio as gr
import pandas as pd
from gradio.themes import Soft
from pathlib import Path
import tempfile
import os
import asyncio
import threading
from datetime import datetime

from src.simple_orchestrator import Orchestrator
from src.processing.pipeline import Pipeline
from src.processing.txt_reader import TxtDocument
from src.constants.general import (
    PATENTS_DIR,
    RESULTS_INTERMEDIATE_DIR,
    RESULTS_FINAL_DIR,
    USPT_API_KEY,
)
from src.constants.processing import PATENTS_PER_BATCH
from src.utils import logger, cut_str
from src.filtering import PatentsRegistry

current_results = None
processing_status = {"status": "idle", "progress": 0, "message": ""}


def run_in_thread(func, *args, **kwargs):
    def wrapper():
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка в потоке: {e}")
            return f"Ошибка: {str(e)}"

    result = [None]
    exception = [None]

    def target():
        try:
            result[0] = wrapper() # type: ignore
        except Exception as e:
            exception[0] = e # type: ignore

    thread = threading.Thread(target=target)
    thread.start()
    thread.join()

    if exception[0]:
        raise exception[0] # type: ignore

    return result[0]


def get_project_stats():
    stats = {
        "patents_count": len(list(PATENTS_DIR.glob("*.pdf")))
        if PATENTS_DIR.exists()
        else 0,
        "processed_files": len(list(RESULTS_INTERMEDIATE_DIR.glob("*.pkl")))
        if RESULTS_INTERMEDIATE_DIR.exists()
        else 0,
        "final_results": len(list(RESULTS_FINAL_DIR.glob("*.csv")))
        if RESULTS_FINAL_DIR.exists()
        else 0,
        "api_key_configured": bool(USPT_API_KEY),
    }
    return stats


def format_stats_display(stats):
    api_status = "Настроен" if stats["api_key_configured"] else "Не настроен"

    return f"""
## Статистика проекта

- **Патенты (PDF):** {stats['patents_count']}
- **Обработанные файлы:** {stats['processed_files']}
- **Финальные результаты:** {stats['final_results']}
- **USPTO API ключ:** {api_status}
"""


def download_patents(count: int, query: str = "protein binding"):
    if not USPT_API_KEY:
        return "Ошибка: USPTO API ключ не настроен. Проверьте файл .env"

    try:
        processing_status["status"] = "downloading"
        processing_status["message"] = f"Скачивание {count} патентов..."

        patents_registry = PatentsRegistry(api_key=USPT_API_KEY)
        patents = patents_registry.get_patents_by_query(query=query, limit=count)

        if not PATENTS_DIR.exists():
            PATENTS_DIR.mkdir(parents=True, exist_ok=True)

        downloaded = 0
        for i, patent in enumerate(patents):
            try:
                processing_status["progress"] = int((i / len(patents)) * 100)
                processing_status["message"] = (
                    f"Скачивание патента {i+1}/{len(patents)}: {patent.id}"
                )

                patents_registry.download_document(
                    patent_id=patent.id, path=PATENTS_DIR, filename=f"US{patent.id}B2"
                )
                downloaded += 1
            except Exception as e:
                logger.error(f"Ошибка скачивания патента {patent.id}: {e}")
                continue

        processing_status["status"] = "idle"
        processing_status["progress"] = 100
        processing_status["message"] = ""

        return f"Успешно скачано {downloaded} патентов из {len(patents)}"

    except Exception as e:
        processing_status["status"] = "idle"
        processing_status["message"] = ""
        return f"Ошибка при скачивании патентов: {str(e)}"


def create_txt_document_from_text(text: str) -> tuple[TxtDocument, Path]:
    from src.constants.processing import PAGE_DIVIDER

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        chunk_size = 2000
        chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

        for i, chunk in enumerate(chunks, 1):
            if i > 1:
                f.write(f"\n{PAGE_DIVIDER.replace('%NUM%', str(i))}\n")
            f.write(chunk)

        temp_path = Path(f.name)

    return TxtDocument(temp_path), temp_path


def _process_single_text_internal(text: str):
    temp_path = None
    try:
        processing_status["status"] = "processing"
        processing_status["message"] = "Обработка текста..."

        txt_doc, temp_path = create_txt_document_from_text(text)

        if len(txt_doc.pages) == 0:
            return "Не удалось создать документ из текста"

        if not RESULTS_INTERMEDIATE_DIR.exists():
            RESULTS_INTERMEDIATE_DIR.mkdir(parents=True, exist_ok=True)

        pipeline = Pipeline(txt_document=txt_doc, output_dir=RESULTS_INTERMEDIATE_DIR)
        results = pipeline.run()

        processing_status["status"] = "idle"
        processing_status["message"] = ""

        if not results.interactions:
            return "В тексте не найдено взаимодействий лиганд-белок"

        output = f"Найдено {len(results.interactions)} страниц с взаимодействиями:\n\n"

        for i, pagedata in enumerate(results.interactions, 1):
            interactions = pagedata.interactions.interactions
            output += f"Страница {i}: {len(interactions)} взаимодействий\n"

            for j, interaction in enumerate(interactions, 1):
                params = interaction.parameters
                param_str = []
                if params.Ki:
                    param_str.append(f"Ki: {params.Ki}")
                if params.IC50:
                    param_str.append(f"IC50: {params.IC50}")
                if params.Kd:
                    param_str.append(f"Kd: {params.Kd}")
                if params.EC50:
                    param_str.append(f"EC50: {params.EC50}")

                output += f"  {j}. {interaction.ligand} ↔ {interaction.protein}\n"
                output += f"     Тип: {interaction.interaction_type}\n"
                if param_str:
                    output += f"     Параметры: {', '.join(param_str)}\n"
                output += f"     Контекст: {cut_str(interaction.context, 100)}\n\n"

        global current_results
        current_results = results

        return output

    except Exception as e:
        processing_status["status"] = "idle"
        processing_status["message"] = ""
        logger.error(f"Ошибка при обработке текста: {e}")
        return f"Ошибка при обработке текста: {str(e)}"
    finally:
        if temp_path and temp_path.exists():
            try:
                os.unlink(temp_path)
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл {temp_path}: {e}")


def process_single_text(text: str):
    if not text.strip():
        return "Пожалуйста, введите текст для обработки"

    return run_in_thread(_process_single_text_internal, text)


def process_uploaded_file(file):
    if file is None:
        return "Пожалуйста, загрузите файл"

    try:
        if hasattr(file, "name"):
            with open(file.name, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            content = file.decode("utf-8") if isinstance(file, bytes) else str(file)

        return process_single_text(content)

    except UnicodeDecodeError:
        return "Ошибка: файл должен быть в кодировке UTF-8"
    except Exception as e:
        logger.error(f"Ошибка при чтении файла: {e}")
        return f"Ошибка при чтении файла: {str(e)}"


def _run_full_pipeline_internal():
    try:
        processing_status["status"] = "processing"
        processing_status["message"] = "Запуск полного пайплайна..."

        orchestrator = Orchestrator(patent_per_batch=PATENTS_PER_BATCH)
        orchestrator.run()

        processing_status["status"] = "idle"
        processing_status["message"] = ""

        stats = get_project_stats()
        return f"Пайплайн завершен успешно!\n\nОбработано файлов: {stats['processed_files']}\nФинальных результатов: {stats['final_results']}"

    except Exception as e:
        processing_status["status"] = "idle"
        processing_status["message"] = ""
        logger.error(f"Ошибка при выполнении пайплайна: {e}")
        return f"Ошибка при выполнении пайплайна: {str(e)}"


def run_full_pipeline():
    return run_in_thread(_run_full_pipeline_internal)


def get_results_list():
    if not RESULTS_FINAL_DIR.exists():
        return []

    results = []
    for csv_file in RESULTS_FINAL_DIR.glob("*.csv"):
        try:
            df = pd.read_csv(csv_file)
            results.append(
                {
                    "filename": csv_file.name,
                    "path": str(csv_file),
                    "rows": len(df),
                    "interactions": len(df[df["ligand"] != ""]),
                }
            )
        except Exception as e:
            logger.error(f"Ошибка чтения {csv_file}: {e}")

    return results


def load_result_file(filename):
    if not filename:
        return None, "Выберите файл для просмотра"

    try:
        file_path = RESULTS_FINAL_DIR / filename
        df = pd.read_csv(file_path)

        df_filtered = df[df["ligand"] != ""].copy()

        info = f"""
**Файл:** {filename}
**Всего строк:** {len(df)}
**Взаимодействий:** {len(df_filtered)}
**Уникальных лигандов:** {df_filtered['ligand'].nunique() if len(df_filtered) > 0 else 0}
**Уникальных белков:** {df_filtered['protein'].nunique() if len(df_filtered) > 0 else 0}
"""

        return df_filtered, info

    except Exception as e:
        return None, f"Ошибка загрузки файла: {str(e)}"


def export_combined_results():
    try:
        results = get_results_list()
        if not results:
            return None, "Нет результатов для экспорта"

        combined_df = pd.DataFrame()

        for result in results:
            df = pd.read_csv(result["path"])
            df["source_file"] = result["filename"]
            combined_df = pd.concat([combined_df, df], ignore_index=True)

        combined_df = combined_df[combined_df["ligand"] != ""]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = RESULTS_FINAL_DIR / f"combined_results_{timestamp}.csv"
        combined_df.to_csv(export_path, index=False, encoding="utf-8")

        info = f"""Экспорт завершен

Файл: {export_path.name}
Всего взаимодействий: {len(combined_df)}
Источников: {len(results)}
Уникальных лигандов: {combined_df['ligand'].nunique()}
Уникальных белков: {combined_df['protein'].nunique()}"""

        return str(export_path), info

    except Exception as e:
        logger.error(f"Ошибка экспорта: {e}")
        return None, f"Ошибка экспорта: {str(e)}"


def get_processing_status():
    if processing_status["status"] == "idle":
        return "Готов к работе"
    elif processing_status["status"] == "downloading":
        return f"Скачивание патентов... {processing_status['progress']}%"
    elif processing_status["status"] == "processing":
        return f"Обработка... {processing_status['message']}"
    else:
        return processing_status["message"]


def get_pdf_files_list():
    if not PATENTS_DIR.exists():
        return []

    pdf_files = []
    for pdf_file in PATENTS_DIR.glob("*.pdf"):
        try:
            file_size = pdf_file.stat().st_size
            size_mb = round(file_size / (1024 * 1024), 2)
            pdf_files.append(
                {"filename": pdf_file.name, "path": str(pdf_file), "size_mb": size_mb}
            )
        except Exception as e:
            logger.error(f"Ошибка чтения PDF файла {pdf_file}: {e}")

    return sorted(pdf_files, key=lambda x: x["filename"])


def download_pdf_file(filename):
    if not filename:
        return gr.File(visible=False), "Выберите PDF файл для скачивания"

    try:
        file_path = PATENTS_DIR / filename
        if not file_path.exists():
            return gr.File(visible=False), f"Файл {filename} не найден"

        return gr.File(
            value=str(file_path), visible=True
        ), f"Файл {filename} готов к скачиванию"

    except Exception as e:
        logger.error(f"Ошибка при подготовке скачивания PDF: {e}")
        return gr.File(visible=False), f"Ошибка при подготовке скачивания: {str(e)}"


def download_csv_file(filename):
    if not filename:
        return gr.File(visible=False), "Выберите CSV файл для скачивания"

    try:
        file_path = RESULTS_FINAL_DIR / filename
        if not file_path.exists():
            return gr.File(visible=False), f"Файл {filename} не найден"

        return gr.File(
            value=str(file_path), visible=True
        ), f"Файл {filename} готов к скачиванию"

    except Exception as e:
        logger.error(f"Ошибка при подготовке скачивания CSV: {e}")
        return gr.File(visible=False), f"Ошибка при подготовке скачивания: {str(e)}"


def create_combined_export():
    try:
        results = get_results_list()
        if not results:
            return gr.File(visible=False), "Нет результатов для экспорта"

        combined_df = pd.DataFrame()

        for result in results:
            df = pd.read_csv(result["path"])
            df["source_file"] = result["filename"]
            combined_df = pd.concat([combined_df, df], ignore_index=True)

        combined_df = combined_df[combined_df["ligand"] != ""]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = RESULTS_FINAL_DIR / f"combined_results_{timestamp}.csv"
        combined_df.to_csv(export_path, index=False, encoding="utf-8")

        info = f"""Экспорт завершен

Файл: {export_path.name}
Всего взаимодействий: {len(combined_df)}
Источников: {len(results)}
Уникальных лигандов: {combined_df['ligand'].nunique()}
Уникальных белков: {combined_df['protein'].nunique()}"""

        return gr.File(value=str(export_path), visible=True), info

    except Exception as e:
        logger.error(f"Ошибка экспорта: {e}")
        return gr.File(visible=False), f"Ошибка экспорта: {str(e)}"


with gr.Blocks(title="Longevity Project - AI Platform", theme=Soft()) as demo:
    gr.Markdown(""" 
    **Платформа для извлечения данных о связывании лигандов с белками из патентов**
    
    Используйте вкладки ниже для различных операций:
    - **Обработка текста** - анализ отдельных текстов
    - **Управление патентами** - скачивание и обработка патентов USPTO  
    - **Результаты** - просмотр и экспорт результатов
    """)

    status_display = gr.Textbox(
        label="Статус системы", value="Готов к работе", interactive=False
    )

    with gr.Tabs():
        with gr.TabItem("Обработка текста"):
            gr.Markdown("### Анализ текста на предмет взаимодействий лиганд-белок")

            with gr.Row():
                with gr.Column():
                    text_input = gr.Textbox(
                        label="Введите текст для анализа",
                        lines=15,
                        placeholder="Вставьте текст патента или научной статьи...",
                    )
                    text_btn = gr.Button("Анализировать текст", variant="primary")

                with gr.Column():
                    text_output = gr.Textbox(
                        label="Результаты анализа", lines=15, interactive=False
                    )

            with gr.Row():
                file_input = gr.File(
                    label="Или загрузите текстовый файл", file_types=[".txt", ".md"]
                )
                file_btn = gr.Button("Обработать файл")

            file_output = gr.Textbox(
                label="Результаты обработки файла", lines=10, interactive=False
            )

        with gr.TabItem("Управление патентами"):
            stats_display = gr.Markdown(format_stats_display(get_project_stats()))
            refresh_stats_btn = gr.Button("Обновить статистику")

            gr.Markdown("### Скачивание патентов из USPTO")

            with gr.Row():
                with gr.Column():
                    patent_count = gr.Slider(
                        minimum=1,
                        maximum=100,
                        value=PATENTS_PER_BATCH,
                        step=1,
                        label="Количество патентов для скачивания",
                    )
                    patent_query = gr.Textbox(
                        value="protein binding",
                        label="Поисковый запрос",
                        placeholder="protein binding, drug interaction, etc.",
                    )
                    download_btn = gr.Button("Скачать патенты", variant="primary")

                with gr.Column():
                    download_output = gr.Textbox(
                        label="Результат скачивания", lines=5, interactive=False
                    )

            gr.Markdown("### Скачивание PDF файлов")

            with gr.Row():
                with gr.Column():
                    pdf_files_list = gr.Dropdown(
                        label="Выберите PDF файл для скачивания",
                        choices=[f["filename"] for f in get_pdf_files_list()],
                        interactive=True,
                    )
                    refresh_pdf_btn = gr.Button("Обновить список PDF")
                    download_pdf_btn = gr.Button("Скачать PDF", variant="secondary")

                with gr.Column():
                    pdf_download_file = gr.File(
                        label="Скачанный PDF файл", visible=False
                    )
                    pdf_download_status = gr.Markdown(
                        "Выберите PDF файл для скачивания"
                    )

            gr.Markdown("### Полная обработка")
            pipeline_btn = gr.Button(
                "Запустить полный пайплайн", variant="secondary", size="lg"
            )
            pipeline_output = gr.Textbox(
                label="Результат выполнения пайплайна", lines=5, interactive=False
            )

        with gr.TabItem("Результаты"):
            gr.Markdown("### Просмотр результатов")

            with gr.Row():
                with gr.Column(scale=1):
                    results_list = gr.Dropdown(
                        label="Выберите файл результатов",
                        choices=[r["filename"] for r in get_results_list()],
                        interactive=True,
                    )
                    refresh_results_btn = gr.Button("Обновить список")

                    result_info = gr.Markdown("Выберите файл для просмотра информации")

                with gr.Column(scale=2):
                    results_table = gr.Dataframe(
                        label="Данные о взаимодействиях", interactive=False, wrap=True
                    )

            gr.Markdown("### Скачивание отдельных CSV файлов")

            with gr.Row():
                with gr.Column():
                    csv_files_list = gr.Dropdown(
                        label="Выберите CSV файл для скачивания",
                        choices=[r["filename"] for r in get_results_list()],
                        interactive=True,
                    )
                    download_csv_btn = gr.Button("Скачать CSV", variant="secondary")

                with gr.Column():
                    csv_download_file = gr.File(
                        label="Скачанный CSV файл", visible=False
                    )
                    csv_download_status = gr.Markdown(
                        "Выберите CSV файл для скачивания"
                    )

            gr.Markdown("### Экспорт объединенных результатов")

            with gr.Row():
                with gr.Column():
                    export_btn = gr.Button(
                        "Создать объединенный экспорт", variant="primary"
                    )
                    export_download_btn = gr.Button(
                        "Скачать объединенный файл", variant="secondary"
                    )

                with gr.Column():
                    export_download_file = gr.File(
                        label="Объединенный CSV файл", visible=False
                    )
                    export_output = gr.Markdown(
                        value="Нажмите кнопку экспорта для объединения всех результатов"
                    )

    text_btn.click(process_single_text, inputs=text_input, outputs=text_output)
    file_btn.click(process_uploaded_file, inputs=file_input, outputs=file_output)

    download_btn.click(
        download_patents, inputs=[patent_count, patent_query], outputs=download_output
    )

    pipeline_btn.click(run_full_pipeline, outputs=pipeline_output)

    refresh_stats_btn.click(
        lambda: format_stats_display(get_project_stats()), outputs=stats_display
    )

    refresh_pdf_btn.click(
        lambda: gr.Dropdown(choices=[f["filename"] for f in get_pdf_files_list()]),
        outputs=pdf_files_list,
    )

    download_pdf_btn.click(
        download_pdf_file,
        inputs=pdf_files_list,
        outputs=[pdf_download_file, pdf_download_status],
    )

    refresh_results_btn.click(
        lambda: [
            gr.Dropdown(choices=[r["filename"] for r in get_results_list()]),
            gr.Dropdown(choices=[r["filename"] for r in get_results_list()]),
        ],
        outputs=[results_list, csv_files_list],
    )

    results_list.change(
        load_result_file, inputs=results_list, outputs=[results_table, result_info]
    )

    download_csv_btn.click(
        download_csv_file,
        inputs=csv_files_list,
        outputs=[csv_download_file, csv_download_status],
    )

    export_btn.click(lambda: export_combined_results()[1], outputs=export_output)

    export_download_btn.click(
        create_combined_export, outputs=[export_download_file, export_output]
    )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        debug=True,
    )
