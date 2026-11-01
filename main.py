import os
import sqlite3
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI(title="DevOps Task Board")

DB_DIR = "/app/data"
DB_PATH = os.path.join(DB_DIR, "tasks.db")

# ИСПРАВЛЕНО: Безопасный вызов создания папки. Если файловая система Read-Only, 
# но папка уже примонтирована через PVC, мы игнорируем ошибку ОС.
try:
    os.makedirs(DB_DIR, exist_ok=True)
except OSError:
    pass

# ИСПРАВЛЕНО: Выносим подключение в единую функцию с таймаутом и PRAGMA-настройками
def get_db_connection():
    # timeout=20 заставляет поды HPA ждать своей очереди на запись до 20 секунд вместо падения в 500 ошибку
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    # Переводим журнал транзакций в оперативную память (RAM), чтобы не писать блокировки на NFS
    conn.execute("PRAGMA journal_mode=MEMORY;")
    conn.execute("PRAGMA synchronous=OFF;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
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
    conn.close()

# Инициализация БД при старте
init_db()

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_board(request: Request):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks")
    rows = cursor.fetchall()
    conn.close()
    
    tasks = {"TODO": [], "IN PROGRESS": [], "DONE": []}
    for row in rows:
        # НОРМАЛИЗАЦИЯ ПРИ ЧТЕНИИ: убираем пробелы, дефисы и переводим в верхний регистр
        db_status = row["status"].strip().upper().replace("_", " ")
        
        # Если статус совпадает, кладем в соответствующую колонку
        if db_status in tasks:
            tasks[db_status].append(dict(row))
        else:
            # Дефолтный фоллбэк: если статус совсем кривой, принудительно выводим задачу в TODO, чтобы она не терялась
            tasks["TODO"].append(dict(row))
            
    context = {"request": request, "tasks": tasks}
    return templates.TemplateResponse("index.html", context)


@app.post("/task/create")
async def create_task(title: str = Form(...), description: str = Form(None)):
    if not title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title, description, status) VALUES (?, ?, 'TODO')", (title, description))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)

@app.post("/task/move/{task_id}")
async def move_task(task_id: int, status: str = Form(...)):
    # ИСПРАВЛЕНО: Принудительно очищаем строку от пробелов, переводим в верхний регистр и меняем дефисы/подчеркивания на пробелы
    normalized_status = status.strip().upper().replace("_", " ")
    
    if normalized_status not in ["TODO", "IN PROGRESS", "DONE"]:
        raise HTTPException(status_code=400, detail=f"Invalid status received: '{status}'")
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (normalized_status, task_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/", status_code=303)
