# ========================================
# Dockerfile для аналитического дашборда ЭДО
# ========================================
# Используем официальный образ Python 3.11 (slim — минимальный размер)
FROM python:3.11-slim

# Метаданные
LABEL maintainer="practice@edo-analytics.ru"
LABEL description="Аналитический дашборд для системы электронного документооборота"

# Переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Рабочая директория в контейнере
WORKDIR /app

# Устанавливаем системные зависимости (если понадобятся для psycopg2 и т.д.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Копируем весь проект в контейнер
COPY . .

# Создаём директорию для логов и статики
RUN mkdir -p /app/logs /app/staticfiles

# Собираем статические файлы (для продакшена)
RUN python manage.py collectstatic --noinput || true

# Открываем порт 8000
EXPOSE 8000

# Команда запуска
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]