# TG Book Reader (Minimal: PDF + Web App)

Телеграм бот с мини‑приложением (Web App) для просмотра списка PDF книг и чтения внутри веб‑вью в Telegram при помощи PDF.js.

## Возможности (MVP)
- Список PDF файлов из директории `books/`
- Открытие PDF в минимальном ридере (PDF.js)
- Кнопка в боте «Открыть ридер» запускает Web App

## Стек
- Bot: Python, aiogram v3 (long polling)
- Web: FastAPI + Jinja2, PDF.js (CDN)

## Требования
- Python 3.10+
- Токен телеграм бота
- Публичный HTTPS URL для теста Web App на реальном устройстве (например, ngrok)

## Установка
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Скопируйте `env.example` в `.env` и заполните токен бота:
```env
BOT_TOKEN=123456789:ABC...
WEBAPP_URL=https://your-public-host/   # например, адрес ngrok, оканчивающийся на /
BOOKS_DIR=./books
```

## Запуск
В двух терминалах:

1) Запустить веб‑приложение (FastAPI):
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

2) Запустить бота:
```bash
python bot/main.py
```

Локально веб‑приложение будет доступно на `http://localhost:8000/`.
Чтобы открыть его внутри Telegram Web App, используйте публичный HTTPS URL (например, через ngrok):
```bash
ngrok http 8000
```
Поставьте значение `WEBAPP_URL` из ngrok (например, `https://abc123.ngrok-free.app/`).

## Добавление книг
- Положите ваши PDF файлы в директорию `books/` (создана в проекте)
- Обновите страницу ридера: книги появятся автоматически

## Замечания
- Это MVP для PDF. Для EPUB/MOBI потребуется дополнительная логика конвертации/рендеринга
- Для продакшена стоит реализовать проверку подписи `initData` Telegram Web App

## Структура проекта
```
tg_bot_reader/
  app/
    main.py
    templates/
      index.html
      viewer.html
    static/
      styles.css
  bot/
    main.py
  books/
    .gitkeep
  requirements.txt
  README.md
  .env.example
``` 