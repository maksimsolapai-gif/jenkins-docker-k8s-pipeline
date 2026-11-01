import os
import sqlite3
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="DevOps Task Board")

# Путь к встроенной базе данных (папка /app/data будет монтироваться через PVC)
DB_DIR = "/app/data"
DB_PATH = os.path.join(DB_DIR, "tasks.db")

# Гарантируем наличие папки для БД
os.makedirs(DB_DIR, exist_ok=True)

def init_db():
    """Инициализация полноценной встроенной БД SQLite"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'TODO'
            )
        """)
        conn.commit()

# Инициализируем БД при запуске приложения
init_db()

# Настройка шаблонов UI
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_board(request: Request):
    """Отображение Канбан-доски с данными из БД"""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks")
        rows = cursor.fetchall()
    
    # Группируем задачи по колонкам для UI
    tasks = {"TODO": [], "IN_PROGRESS": [], "DONE": []}
    for row in rows:
        if row["status"] in tasks:
            tasks[row["status"]].append(row)
            
    return templates.TemplateResponse("index.html", {"request": request, "tasks": tasks})

@app.post("/task/create")
async def create_task(title: str = Form(...), description: str = Form(None)):
    """Создание пользовательской записи в БД"""
    if not title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
        
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tasks (title, description, status) VALUES (?, ?, 'TODO')", (title, description))
        conn.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/task/move/{task_id}")
async def move_task(task_id: int, status: str = Form(...)):
    """Обновление статуса задачи (бизнес-логика)"""
    if status not in ["TODO", "IN_PROGRESS", "DONE"]:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
        conn.commit()
    return RedirectResponse(url="/", status_code=303)
