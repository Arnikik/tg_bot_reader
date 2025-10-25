import os
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
BOOKS_DIR = Path(os.getenv("BOOKS_DIR", BASE_DIR / "books")).resolve()
USER_BOOKS_DIR = BOOKS_DIR / "users"

app = FastAPI(title="TG Book Reader")

# Static files
static_dir = BASE_DIR / "app" / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.mount("/books", StaticFiles(directory=BOOKS_DIR), name="books")

# Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


def list_pdf_files(user_id: int = None) -> list[str]:
    """Получить список PDF файлов. сли user_id указан - из папки пользователя, иначе из общей папки"""
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


@app.get("/view/{filename}", response_class=HTMLResponse)
async def view_pdf(filename: str, request: Request, user_id: int = Query(None)) -> HTMLResponse:
    safe_name = Path(filename).name
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
