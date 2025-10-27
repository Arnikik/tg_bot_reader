import asyncio
import os
import json
from pathlib import Path
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, FSInputFile
from dotenv import load_dotenv
import httpx


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8000/")
BOOKS_DIR = Path(os.getenv("BOOKS_DIR", "./books"))

# Создаем папку для книг пользователей (для совместимости)
USER_BOOKS_DIR = BOOKS_DIR / "users"
USER_BOOKS_DIR.mkdir(parents=True, exist_ok=True)

dp = Dispatcher()


async def add_file_to_webapp(user_id: int, file_info: dict) -> bool:
    """Отправить информацию о файле в веб-приложение"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{WEBAPP_URL.rstrip('/')}/api/add-file",
                json={
                    "user_id": user_id,
                    "file_info": file_info
                },
                timeout=10.0
            )
            return response.status_code == 200
    except Exception as e:
        print(f"Ошибка при отправке файла в веб-приложение: {e}")
        return False


def get_user_books_dir(user_id: int) -> Path:
    """Получить папку с книгами конкретного пользователя"""
    user_dir = USER_BOOKS_DIR / str(user_id)
    user_dir.mkdir(exist_ok=True)
    return user_dir


def list_user_pdf_files(user_id: int) -> list[str]:
    """Получить список PDF файлов пользователя"""
    user_dir = get_user_books_dir(user_id)
    if not user_dir.exists():
        return []
    
    files = []
    for entry in user_dir.iterdir():
        if entry.is_file() and entry.suffix.lower() == ".pdf":
            files.append(entry.name)
    files.sort(key=lambda x: x.lower())
    return files


@dp.message(CommandStart())
async def on_start(message: types.Message) -> None:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📚 Мои книги"),
                KeyboardButton(text="📤 Загрузить книгу")
            ],
            [
                KeyboardButton(
                    text="🌐 Открыть ридер",
                    web_app=WebAppInfo(url=f"{WEBAPP_URL}/simple?user_id={message.from_user.id}"),
                )
            ]
        ],
        resize_keyboard=True,
    )

    await message.answer(
        f"Привет! Это книгридер.\n\n"
        f"📚 Мои книги — посмотреть ваши загруженные PDF\n"
        f"📤 Загрузить книгу — добавить новый PDF\n"
        f"🌐 Открыть ридер — веб-версия",
        reply_markup=keyboard,
    )


@dp.message(F.text == "📚 Мои книги")
async def show_user_books(message: types.Message) -> None:
    user_id = message.from_user.id
    
    # Получаем книги из локального хранилища
    pdf_files = list_user_pdf_files(user_id)
    
    # Пытаемся получить книги из веб-приложения
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{WEBAPP_URL.rstrip('/')}/api/books",
                params={"user_id": user_id},
                timeout=5.0
            )
            if response.status_code == 200:
                data = response.json()
                web_books = data.get("books", [])
                if web_books:
                    # Добавляем книги из веб-приложения к локальным
                    web_filenames = [book["name"] for book in web_books]
                    pdf_files.extend([f for f in web_filenames if f not in pdf_files])
    except Exception as e:
        print(f"Ошибка получения книг из веб-приложения: {e}")
    
    if not pdf_files:
        await message.answer("У вас пока нет загруженных книг.\n\nИспользуйте кнопку '📤 Загрузить книгу' для добавления PDF файлов.")
        return
    
    text = "📚 Ваши книги:\n\n"
    for i, filename in enumerate(pdf_files, 1):
        text += f"{i}. {filename}\n"
    
    text += f"\nВсего книг: {len(pdf_files)}"
    await message.answer(text)


@dp.message(F.text == "📤 Загрузить книгу")
async def request_file_upload(message: types.Message) -> None:
    await message.answer(
        "Отправьте PDF файл для загрузки.\n\n"
        "Просто прикрепите файл к сообщению и отправьте."
    )


@dp.message(F.document)
async def handle_document(message: types.Message) -> None:
    if not message.document:
        return
    
    # Проверяем, что это PDF
    if not message.document.file_name.lower().endswith('.pdf'):
        await message.answer("❌ Пожалуйста, отправьте PDF файл.")
        return
    
    # Проверяем размер файла (макс 20 МБ для Telegram)
    if message.document.file_size > 20 * 1024 * 1024:
        await message.answer("❌ Файл слишком большой. Максимальный размер: 20 МБ.")
        return
    
    try:
        user_id = message.from_user.id
        
        # Подготавливаем информацию о файле для отправки в веб-приложение
        file_info = {
            "file_id": message.document.file_id,
            "file_name": message.document.file_name,
            "file_size": message.document.file_size,
            "mime_type": message.document.mime_type
        }
        
        # Отправляем информацию о файле в веб-приложение
        success = await add_file_to_webapp(user_id, file_info)
        
        if success:
            await message.answer(
                f"✅ Книга '{message.document.file_name}' успешно добавлена!\n\n"
                f"Теперь вы можете:\n"
                f"• Посмотреть её в списке '📚 Мои книги'\n"
                f"• Открыть через '🌐 Открыть ридер'\n\n"
                f"📝 Файл не сохраняется локально - он передается напрямую из Telegram."
            )
        else:
            # Fallback: сохраняем локально, если веб-приложение недоступно
            user_dir = get_user_books_dir(user_id)
            file = await message.bot.get_file(message.document.file_id)
            file_path = user_dir / message.document.file_name
            
            await message.bot.download_file(file.file_path, file_path)
            
            await message.answer(
                f"✅ Книга '{message.document.file_name}' загружена локально!\n\n"
                f"Веб-приложение недоступно, файл сохранен локально.\n"
                f"Теперь вы можете:\n"
                f"• Посмотреть её в списке '📚 Мои книги'\n"
                f"• Открыть через '🌐 Открыть ридер'"
            )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при обработке файла: {str(e)}")


@dp.message()
async def handle_other_messages(message: types.Message) -> None:
    await message.answer(
        "Используйте кнопки меню:\n\n"
        "📚 Мои книги — посмотреть ваши PDF\n"
        "📤 Загрузить книгу — добавить новый PDF\n"
        "🌐 Открыть ридер — веб-версия"
    )


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set. Put it into .env or environment.")

    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
