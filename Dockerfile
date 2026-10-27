# Фиксируем версию базового образа
FROM alpine:3.18.5

# Описание метаданных
LABEL maintainer="maksimsolapai-gif"

# Установка системных зависимостей с гибкой фиксацией версий
RUN apk add --no-cache python3~=3.11 py3-pip curl && \
    pip install --no-cache-dir --break-system-packages fastapi==0.109.2 jinja2==3.1.3 python-multipart==0.0.9 uvicorn==0.27.1

# Создаем рабочую директорию и папку для встроенной базы данных SQLite
WORKDIR /app
RUN mkdir -p /app/data

# Копируем исходный код приложения и шаблоны UI
COPY main.py /app/
COPY templates /app/templates

# Объявляем VOLUME для персистентного хранения данных пользователей
VOLUME /app/data

# Открываем порт веб-интерфейса
EXPOSE 8080

# ИСПРАВЛЕНО: Запуск через стандартный production-сервер uvicorn
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
