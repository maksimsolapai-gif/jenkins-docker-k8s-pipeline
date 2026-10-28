# Фиксируем версию базового образа
FROM alpine:3.18.5

## Описание метаданных
LABEL maintainer="maksimsolapai-gif"

# Установка системных зависимостей с гибкой фиксацией версий
RUN apk add --no-cache python3~=3.11 py3-pip curl && \
    pip install --no-cache-dir --break-system-packages fastapi==0.111.0 jinja2==3.1.4 python-multipart==0.0.9 uvicorn==0.30.1
# Создаем рабочую директорию и папку для встроенной базы данных SQLite
WORKDIR /app
RUN mkdir -p /app/data && \
    # СОЗДАЕМ БЕЗОПАСНОГО ПОЛЬЗОВАТЕЛЯ И ВЫДАЕМ ПРАВА На ПАПКУ БД
    adduser -D -u 10001 devopsuser && \
    chown -R devopsuser:devopsuser /app

# Копируем исходный код приложения и шаблоны UI
COPY --chown=devopsuser:devopsuser main.py /app/
COPY --chown=devopsuser:devopsuser templates /app/templates

# Объявляем VOLUME для персистентного хранения данных пользователей
VOLUME /app/data

# Открываем порт веб-интерфейса
EXPOSE 8080

# ПЕРЕКЛЮЧАЕМ КОНТЕНТ НА NON-ROOT ПОЛЬЗОВАТЕЛЯ
USER 10001

# ИСПРАВЛЕНО: Запуск через стандартный production-сервер uvicorn
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
