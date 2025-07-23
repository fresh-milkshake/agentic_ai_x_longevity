import os
import pickle
from src.constants import RESULTS_INTERMEDIATE_DIR
from src.processing.pipeline import PipelineResult
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header,
    Footer,
    Static,
    ListView,
    ListItem,
    Label,
    Tree,
)
from textual.binding import Binding
from typing import List, Optional, TypeVar

console = Console()

EventTreeDataType = TypeVar("EventTreeDataType")


class FileListWidget(ListView):
    def __init__(self, files: List[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.files = files
        for file in files:
            self.append(ListItem(Label(file)))


class InteractionDetailWidget(Static):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_result: Optional[PipelineResult] = None

    def update_content(self, result: PipelineResult, filename: str):
        self.current_result = result
        content = self._format_result(result, filename)
        self.update(content)

    def _format_result(self, result: PipelineResult, filename: str) -> str:
        lines = [f"[bold blue]Файл: {filename}[/bold blue]\n"]

        if not result.interactions:
            lines.append("[dim]Нет данных о взаимодействиях.[/dim]")
            return "\n".join(lines)

        total_interactions = 0
        for pagedata in result.interactions:
            interactions = getattr(pagedata, "interactions", None)
            if interactions and hasattr(interactions, "interactions"):
                total_interactions += len(interactions.interactions)

        lines.append(f"[green]Всего взаимодействий: {total_interactions}[/green]\n")

        for pagedata in result.interactions:
            page = getattr(pagedata, "page", None)
            interactions = getattr(pagedata, "interactions", None)
            page_number = getattr(page, "number", "N/A") if page else "N/A"

            lines.append(f"[yellow]═══ Страница № {page_number} ═══[/yellow]")

            if not interactions or not getattr(interactions, "interactions", []):
                lines.append("[dim]  Нет взаимодействий на этой странице.[/dim]")
            else:
                for idx, interaction in enumerate(interactions.interactions, 1):
                    lines.append(f"\n[bold green]▶ Взаимодействие {idx}[/bold green]")
                    lines.append(
                        f"  [cyan]Лиганд:[/cyan] {getattr(interaction, 'ligand', 'N/A')}"
                    )
                    lines.append(
                        f"  [cyan]Белок:[/cyan] {getattr(interaction, 'protein', 'N/A')}"
                    )
                    lines.append(
                        f"  [cyan]Тип:[/cyan] {getattr(interaction, 'interaction_type', 'N/A')}"
                    )
                    lines.append(
                        f"  [cyan]Контекст:[/cyan] {getattr(interaction, 'context', 'N/A')}"
                    )

                    params = getattr(interaction, "parameters", None)
                    if params:
                        lines.append("  [cyan]Параметры:[/cyan]")
                        lines.extend(self._format_parameters(params, indent=4))
                    else:
                        lines.append("  [dim]Параметры: отсутствуют[/dim]")
            lines.append("")

        return "\n".join(lines)

    def _format_parameters(self, params, indent=4) -> List[str]:
        lines = []
        prefix = " " * indent

        if isinstance(params, dict):
            for key, value in params.items():
                lines.append(f"{prefix}[magenta]{key}:[/magenta] {value}")
        elif isinstance(params, list):
            for item in params:
                lines.append(f"{prefix}• {item}")
        else:
            lines.append(f"{prefix}{params}")

        return lines


class InteractionTreeWidget(Tree):
    def __init__(self, *args, **kwargs):
        super().__init__("Взаимодействия", *args, **kwargs)
        self.show_root = False

    def update_tree(self, result: PipelineResult, filename: str):
        self.clear()

        if not result.interactions:
            self.root.add_leaf("[dim]Нет данных[/dim]")
            return

        file_node = self.root.add(f"📁 {filename}")

        for pagedata in result.interactions:
            page = getattr(pagedata, "page", None)
            interactions = getattr(pagedata, "interactions", None)
            page_number = getattr(page, "number", "N/A") if page else "N/A"

            page_node = file_node.add(f"📄 Страница {page_number}")

            if not interactions or not getattr(interactions, "interactions", []):
                page_node.add_leaf("[dim]Нет взаимодействий[/dim]")
            else:
                for idx, interaction in enumerate(interactions.interactions, 1):
                    ligand = getattr(interaction, "ligand", "N/A")
                    protein = getattr(interaction, "protein", "N/A")
                    interaction_type = getattr(interaction, "interaction_type", "N/A")

                    interaction_node = page_node.add(f"🔗 [{idx}] {ligand} ↔ {protein}")
                    interaction_node.add_leaf(f"Тип: {interaction_type}")

                    context = getattr(interaction, "context", "N/A")
                    if context != "N/A":
                        interaction_node.add_leaf(f"Контекст: {context}")

                    params = getattr(interaction, "parameters", None)
                    if params:
                        param_node = interaction_node.add("⚙️ Параметры")
                        self._add_parameters_to_tree(param_node, params)

        file_node.expand()

    def _add_parameters_to_tree(self, parent_node: EventTreeDataType, params):
        if isinstance(params, dict):
            for key, value in params.items():
                parent_node.add_leaf(f"{key}: {value}")
        elif isinstance(params, list):
            for item in params:
                parent_node.add_leaf(f"• {item}")
        else:
            parent_node.add_leaf(str(params))


class InteractionViewerApp(App):
    CSS = """
    Screen {
        layout: horizontal;
    }
    
    #left_panel {
        width: 30%;
        border: solid $primary;
        margin: 1;
    }
    
    #right_panel {
        width: 70%;
        border: solid $secondary;
        margin: 1;
    }
    
    #file_list_container {
        height: 45%;
        min-height: 10;
        max-height: 50%;
        border: solid $accent;
        margin: 1;
        overflow: auto;
    }
    
    #tree_view_container {
        height: 45%;
        min-height: 10;
        max-height: 50%;
        border: solid $warning;
        margin: 1;
        overflow: auto;
    }
    
    #detail_container {
        height: 100%;
        min-height: 20;
        border: solid $success;
        margin: 1;
        overflow: auto;
    }
    
    ListView {
        background: $surface;
    }
    
    ListView > ListItem {
        padding: 1;
    }
    
    ListView > ListItem:hover {
        background: $primary 20%;
    }
    
    Tree {
        background: $surface;
    }
    
    Static {
        background: $surface;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Выход"),
        Binding("r", "refresh", "Обновить"),
        Binding("t", "toggle_view", "Переключить вид"),
    ]

    def __init__(self):
        super().__init__()
        self.files: List[str] = []
        self.results_cache: dict = {}
        self.current_view = "detail"

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal():
            with Vertical(id="left_panel"):
                yield Static("📂 Файлы результатов", id="file_header")
                yield ScrollableContainer(
                    FileListWidget([], id="file_list"), id="file_list_container"
                )
                yield Static("🌳 Структура данных", id="tree_header")
                yield ScrollableContainer(
                    InteractionTreeWidget(id="tree_view"), id="tree_view_container"
                )

            with Vertical(id="right_panel"):
                yield Static("📋 Детали взаимодействий", id="detail_header")
                yield ScrollableContainer(
                    InteractionDetailWidget(id="detail_view"), id="detail_container"
                )

        yield Footer()

    def on_mount(self) -> None:
        self.load_files()

    def load_files(self):
        try:
            if not os.path.exists(RESULTS_INTERMEDIATE_DIR):
                self.notify("Директория результатов не найдена", severity="error")
                return

            self.files = [
                f for f in os.listdir(RESULTS_INTERMEDIATE_DIR) if f.endswith(".pkl")
            ]

            if not self.files:
                self.notify("Нет файлов с результатами", severity="warning")
                return

            file_list = self.query_one("#file_list", FileListWidget)
            file_list.clear()
            for file in sorted(self.files):
                file_list.append(ListItem(Label(file)))

            self.notify(f"Загружено {len(self.files)} файлов", severity="information")

        except Exception as e:
            self.notify(f"Ошибка загрузки файлов: {e}", severity="error")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id == "file_list":
            selected_item = event.item
            if selected_item and hasattr(selected_item, "children"):
                filename = str(selected_item.children[0].renderable)
                self.load_and_display_file(filename)

    def load_and_display_file(self, filename: str):
        try:
            if filename in self.results_cache:
                result = self.results_cache[filename]
            else:
                filepath = os.path.join(RESULTS_INTERMEDIATE_DIR, filename)
                with open(filepath, "rb") as f:
                    result = pickle.load(f)

                if not isinstance(result, PipelineResult):
                    self.notify(
                        f"Файл {filename} не содержит PipelineResult", severity="error"
                    )
                    return

                self.results_cache[filename] = result

            detail_widget = self.query_one("#detail_view", InteractionDetailWidget)
            detail_widget.update_content(result, filename)

            tree_widget = self.query_one("#tree_view", InteractionTreeWidget)
            tree_widget.update_tree(result, filename)

            self.notify(f"Загружен файл: {filename}", severity="information")

        except Exception as e:
            self.notify(f"Ошибка загрузки файла {filename}: {e}", severity="error")

    def action_refresh(self) -> None:
        self.results_cache.clear()
        self.load_files()
        self.notify("Список файлов обновлен", severity="information")

    def action_toggle_view(self) -> None:
        self.notify("Переключение вида (функция в разработке)", severity="information")

    def action_quit(self) -> None:
        self.exit()


def print_parameters(params, indent=10):
    if not params:
        console.print(" " * indent + "[dim]Нет параметров взаимодействия.[/dim]")
        return
    if isinstance(params, dict):
        for key, value in params.items():
            console.print(" " * indent + f"[cyan]{key}[/cyan]: {value}")
    elif isinstance(params, list):
        for item in params:
            console.print(" " * indent + f"- {item}")
    else:
        console.print(" " * indent + str(params))


def print_pipeline_result(result: PipelineResult):
    for pagedata in result.interactions:
        page = getattr(pagedata, "page", None)
        interactions = getattr(pagedata, "interactions", None)
        page_number = getattr(page, "number", "N/A") if page else "N/A"
        console.rule(
            f"[bold yellow]Страница № {page_number}[/bold yellow]", style="yellow"
        )
        if not interactions or not getattr(interactions, "interactions", []):
            console.print("[dim]  Нет взаимодействий на этой странице.[/dim]")
        else:
            for idx, interaction in enumerate(interactions.interactions, 1):
                table = Table(
                    show_header=False, box=box.SIMPLE, show_edge=False, padding=(0, 1)
                )
                table.add_row(
                    "[bold]Лиганд[/bold]", f"{getattr(interaction, 'ligand', 'N/A')}"
                )
                table.add_row(
                    "[bold]Белок[/bold]", f"{getattr(interaction, 'protein', 'N/A')}"
                )
                table.add_row(
                    "[bold]Тип взаимодействия[/bold]",
                    f"{getattr(interaction, 'interaction_type', 'N/A')}",
                )
                table.add_row(
                    "[bold]Контекст[/bold]", f"{getattr(interaction, 'context', 'N/A')}"
                )
                params = getattr(interaction, "parameters", None)
                if params:
                    param_text = Text("Параметры взаимодействия:\n")
                    with console.capture() as capture:
                        print_parameters(params, indent=4)
                    param_text.append(capture.get())
                else:
                    param_text = Text(
                        "Параметры взаимодействия: отсутствуют", style="dim"
                    )
                panel = Panel.fit(
                    table, title=f"[{idx}]", border_style="green", padding=(1, 2)
                )
                console.print(panel)
                console.print(param_text)
                console.rule("", style="dim")
        console.rule(style="yellow")


def console_mode():
    files = [f for f in os.listdir(RESULTS_INTERMEDIATE_DIR) if f.endswith(".pkl")]
    if not files:
        console.print("[bold red]Нет файлов с результатами для отображения.[/bold red]")
        return
    for filename in sorted(files):
        filepath = os.path.join(RESULTS_INTERMEDIATE_DIR, filename)
        console.rule(f"[bold blue]Файл: {filename}[/bold blue]", style="blue")
        try:
            with open(filepath, "rb") as f:
                result = pickle.load(f)
                if isinstance(result, PipelineResult):
                    print_pipeline_result(result)
                else:
                    console.print(
                        "[red]  [Ошибка] Файл не содержит объект PipelineResult.[/red]"
                    )
        except Exception as e:
            console.print(f"[red]  [Ошибка при чтении файла]: {e}[/red]")


def main():
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--console":
        console_mode()
    else:
        try:
            app = InteractionViewerApp()
            app.run()
        except KeyboardInterrupt:
            console.print("\n[yellow]Приложение прервано пользователем[/yellow]")
        except Exception as e:
            console.print(f"[red]Ошибка запуска приложения: {e}[/red]")
            console.print("[dim]Используйте --console для консольного режима[/dim]")


if __name__ == "__main__":
    main()
