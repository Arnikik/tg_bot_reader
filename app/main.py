import os
import json
import asyncio
from pathlib import Path
from urllib.parse import quote
from typing import Dict, List, Optional

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import httpx


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
BOOKS_DIR = Path(os.getenv("BOOKS_DIR", BASE_DIR / "books")).resolve()
USER_BOOKS_DIR = BOOKS_DIR / "users"

# Telegram Bot API settings
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# In-memory storage for user files (file_id -> file_info mapping)
user_files_storage: Dict[int, List[Dict]] = {}

app = FastAPI(title="TG Book Reader")

# Static files
static_dir = BASE_DIR / "app" / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/books", StaticFiles(directory=BOOKS_DIR), name="books")

# Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


async def get_user_files_from_telegram(user_id: int) -> List[Dict]:
    """Получить список файлов пользователя из Telegram Bot API"""
    if user_id not in user_files_storage:
        return []
    return user_files_storage[user_id]

def add_user_file(user_id: int, file_info: Dict) -> None:
    """Добавить файл пользователя в хранилище"""
    if user_id not in user_files_storage:
        user_files_storage[user_id] = []
    
    # Проверяем, что файл еще не добавлен
    file_id = file_info.get('file_id')
    if not any(f.get('file_id') == file_id for f in user_files_storage[user_id]):
        user_files_storage[user_id].append(file_info)

def list_pdf_files(user_id: int = None) -> list[str]:
    """Получить список PDF файлов. Если user_id указан - из папки пользователя, иначе из общей папки"""
    if user_id:
        user_dir = USER_BOOKS_DIR / str(user_id)
        if not user_dir.exists():
            return []
        search_dir = user_dir
    else:
        search_dir = BOOKS_DIR
    
    if not search_dir.exists():
        return []
    
    files: list[str] = []
    for entry in search_dir.iterdir():
        if entry.is_file() and entry.suffix.lower() == ".pdf":
            files.append(entry.name)
    files.sort(key=lambda x: x.lower())
    return files

async def list_user_pdf_files_from_storage(user_id: int) -> List[Dict]:
    """Получить список PDF файлов пользователя из хранилища"""
    files = await get_user_files_from_telegram(user_id)
    pdf_files = [f for f in files if f.get('file_name', '').lower().endswith('.pdf')]
    return pdf_files

async def stream_file_from_telegram(file_id: str, filename: str):
    """Потоковая передача файла из Telegram Bot API"""
    if not BOT_TOKEN:
        raise HTTPException(status_code=500, detail="Bot token not configured")
    
    try:
        # Получаем информацию о файле
        async with httpx.AsyncClient() as client:
            file_info_response = await client.get(f"{TELEGRAM_API_URL}/getFile", params={"file_id": file_id})
            file_info_response.raise_for_status()
            file_info = file_info_response.json()
            
            if not file_info.get("ok"):
                raise HTTPException(status_code=404, detail="File not found in Telegram")
            
            file_path = file_info["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            
            # Стримим файл
            async with client.stream("GET", file_url) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes():
                    yield chunk
                    
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Error fetching file from Telegram: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


def get_file_path(filename: str, user_id: int = None) -> Path:
    """Получить путь к файлу. Сначала ищем в папке пользователя, потом в общей"""
    safe_name = Path(filename).name
    
    if user_id:
        user_dir = USER_BOOKS_DIR / str(user_id)
        user_file = user_dir / safe_name
        if user_file.exists():
            return user_file
    
    # Fallback to general books directory
    return BOOKS_DIR / safe_name


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, user_id: int = Query(None)) -> HTMLResponse:
    pdf_files = list_pdf_files(user_id)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "pdf_files": pdf_files,
            "user_id": user_id,
        },
    )


@app.get("/api/books")
async def api_books(user_id: int = Query(None)) -> JSONResponse:
    """API endpoint для получения списка книг"""
    if user_id:
        # Получаем книги из хранилища Telegram
        pdf_files_info = await list_user_pdf_files_from_storage(user_id)
        books = [{"name": f["file_name"], "file_id": f["file_id"]} for f in pdf_files_info]
    else:
        # Получаем книги из локальной папки
        pdf_files = list_pdf_files(user_id)
        books = [{"name": f, "file_id": None} for f in pdf_files]
    
    return JSONResponse(content={"books": books})


@app.get("/simple", response_class=HTMLResponse)
async def simple_view(request: Request, user_id: int = Query(None)) -> HTMLResponse:
    """Простая страница без ngrok предупреждений"""
    return templates.TemplateResponse("simple.html", {"request": request})


@app.get("/stream/{file_id}")
async def stream_pdf(file_id: str, filename: str = Query(...)):
    """Потоковая передача PDF файла из Telegram"""
    return StreamingResponse(
        stream_file_from_telegram(file_id, filename),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={quote(filename)}"}
    )

@app.post("/api/add-file")
async def add_file(request: Request) -> JSONResponse:
    """API endpoint для добавления файла пользователя"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        file_info = data.get("file_info")
        
        if not user_id or not file_info:
            raise HTTPException(status_code=400, detail="Missing user_id or file_info")
        
        add_user_file(user_id, file_info)
        return JSONResponse(content={"status": "success"})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/view/{filename}", response_class=HTMLResponse)
async def view_pdf(filename: str, request: Request, user_id: int = Query(None), file_id: str = Query(None)) -> HTMLResponse:
    safe_name = Path(filename).name
    
    # Если есть file_id, используем потоковую передачу из Telegram
    if file_id and user_id:
        file_url = f"/stream/{file_id}?filename={quote(safe_name)}"
    else:
        # Fallback к локальным файлам
        file_path = get_file_path(safe_name, user_id)
        
        if not file_path.exists() or file_path.suffix.lower() != ".pdf":
            raise HTTPException(status_code=404, detail="PDF not found")

        # Build absolute file URL for the client
        encoded = quote(safe_name)
        file_url = f"/books/{encoded}"

    return templates.TemplateResponse(
        "viewer.html",
        {
            "request": request,
            "filename": safe_name,
            "file_url": file_url,
        },
    )
