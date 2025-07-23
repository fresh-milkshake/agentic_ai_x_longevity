![header](assets/header.png)

Этот проект создает извлеченный набор данных о связывании лигандов с белками в формате CSV-таблицы с требуемыми полями. Датасет создается с помощью API для поиска патентов, их дальнейшей обработки и извлечения данных.

## Использование

> [!IMPORTANT]
> Для работы проекта требуется API-ключ от USPTO PatentsView. Получить его можно [здесь](https://patentsview-support.atlassian.net/servicedesk/customer/portal/1/group/1/create/18). Заявку одобряют в течение 1-2 дней.

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/fresh-milkshake/agentic_ai_x_longevity
   ```
2. Установите зависимости при помощи `uv` (или `poetry`):
   ```bash
   uv sync
   ```

> [!NOTE]
> Скачать `uv` можно при помощи `pip`:
>
> ```bash
> pip install uv
> ```

3. Создайте файл `.env` по образцу `.env.example` в корне проекта и добавьте в него API-ключ от USPTO:
   ```bash
   USPTO_API_KEY=your_api_key
   ```

4. Запустите скрипт:
   ```
   uv run main.py
   ```
   или
   ```
   python main.py
   ```

## Структура проекта




## Лицензия

Проект опубликован под лицензией MIT. Для деталей см. [LICENSE](LICENSE.txt).