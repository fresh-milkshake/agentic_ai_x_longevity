from dataclasses import dataclass
from pathlib import Path
from src.constants.processing import PAGE_DIVIDER

@dataclass
class Page:
    """
    Класс, представляющий одну страницу текста.

    Attributes:
        number (int): Номер страницы.
        text (str): Текст страницы.
        is_empty (bool): Признак пустой страницы.
        symbols_count (int): Количество символов на странице.
    """
    number: int
    text: str
    is_empty: bool
    symbols_count: int
    
    def __str__(self):
        return f"Page(number={self.number}, is_empty={self.is_empty}, symbols_count={self.symbols_count})"

class TxtDocument:
    """
    Класс для чтения и разбора текстовых файлов, разбитых на страницы.
    """

    def __init__(self, text_file: Path):
        """
        Инициализация TxtReader.

        Args:
            text_file (Path): Путь к текстовому файлу.
        """
        self._file = text_file
        self._pages = self._parse_pages()
        self._current_page_idx = 0
        self._iter_page_idx = 0  # Индекс для итератора

    def _parse_pages(self) -> list[Page]:
        with open(self._file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        pages = []
        page_lines = []
        current_page_number = None

        # Предварительно вычисляем возможные разделители страниц
        dividers = {PAGE_DIVIDER.replace("%NUM%", str(i)): i for i in range(1, 1000)}

        for line in lines:
            line_stripped = line.rstrip('\n')
            page_num = dividers.get(line_stripped)
            if page_num is not None:
                # Сохраняем предыдущую страницу, если есть
                if page_lines and current_page_number is not None:
                    page_text = "\n".join(page_lines).strip()
                    is_empty = not page_text
                    pages.append(Page(
                        number=current_page_number,
                        text=page_text,
                        is_empty=is_empty,
                        symbols_count=len(page_text)
                    ))
                    page_lines = []
                current_page_number = page_num
            else:
                page_lines.append(line_stripped)

        # Добавляем последнюю страницу, если есть
        if page_lines and current_page_number is not None:
            page_text = "\n".join(page_lines).strip()
            is_empty = not page_text
            pages.append(Page(
                number=current_page_number,
                text=page_text,
                is_empty=is_empty,
                symbols_count=len(page_text)
            ))

        return pages
    

    @property
    def pages(self) -> list[Page]:
        return self._pages
    
    
    @property
    def current_page(self) -> Page | None:
        return self._pages[self._current_page_idx]
    
    
    @property
    def name(self) -> str:
        return self._file.name
    
    @property
    def path(self) -> Path:
        return self._file


    def get_pages_count(self) -> int:
        """
        Возвращает количество страниц.

        Returns:
            int: Количество страниц.
        """
        return len(self._pages)

    def get_current_page(self) -> Page | None:
        """
        Возвращает текущую страницу.

        Returns:
            Page | None: Текущая страница или None, если индекс вне диапазона.
        """
        if 0 <= self._current_page_idx < len(self._pages):
            return self._pages[self._current_page_idx]
        return None

    def get_next_page(self) -> Page | None:
        """
        Переходит к следующей странице и возвращает её.

        Returns:
            Page | None: Следующая страница или None, если достигнут конец.
        """
        if self._current_page_idx + 1 < len(self._pages):
            self._current_page_idx += 1
            return self._pages[self._current_page_idx]
        return None

    def get_page(self, number: int) -> Page | None:
        """
        Возвращает страницу по её номеру.

        Args:
            number (int): Номер страницы (начиная с 1).

        Returns:
            Page | None: Страница с заданным номером или None, если номер некорректен.
        """
        if 1 <= number <= len(self._pages):
            return self._pages[number - 1]
        return None

    def get_all_pages(self) -> list[Page]:
        """
        Возвращает список всех страниц.

        Returns:
            list[Page]: Список всех страниц.
        """
        return self._pages

    def reset(self) -> None:
        """
        Сбрасывает текущий индекс страницы к первой странице.
        """
        self._current_page_idx = 0

    def get_prev_page(self) -> Page | None:
        """
        Переходит к предыдущей странице и возвращает её.

        Returns:
            Page | None: Предыдущая страница или None, если достигнуто начало.
        """
        if self._current_page_idx - 1 >= 0:
            self._current_page_idx -= 1
            return self._pages[self._current_page_idx]
        return None

    def get_file_path(self) -> Path:
        """
        Возвращает путь к исходному файлу.

        Returns:
            Path: Путь к файлу.
        """
        return self._file

    def get_pages_texts(self) -> list[str]:
        """
        Возвращает список текстов всех страниц.

        Returns:
            list[str]: Список текстов страниц.
        """
        return [page.text for page in self._pages]

    def is_first_page(self) -> bool:
        """
        Проверяет, находится ли текущий индекс на первой странице.

        Returns:
            bool: True, если текущая страница первая, иначе False.
        """
        return self._current_page_idx == 0

    def is_last_page(self) -> bool:
        """
        Проверяет, находится ли текущий индекс на последней странице.

        Returns:
            bool: True, если текущая страница последняя, иначе False.
        """
        return self._current_page_idx == len(self._pages) - 1

    def __iter__(self):
        self._iter_page_idx = 0
        return self

    def __next__(self):
        if self._iter_page_idx < len(self._pages):
            page = self._pages[self._iter_page_idx]
            self._iter_page_idx += 1
            return page
        raise StopIteration

    def __len__(self):
        return len(self._pages)
    
    def __str__(self):
        return f"TxtDocument(file={self._file}, pages={[str(i) for i in self._pages]})"