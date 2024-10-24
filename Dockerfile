# Установка Python из официального базового образа
FROM python:3.10

# Установка системных библиотек для сборки
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev

# Установка рабочей директории внутри будущего контейнера
WORKDIR /app

# Копирование всех файлов приложения в контейнер
COPY . /app

# Обновление pip, setuptools и wheel
RUN pip install --upgrade pip setuptools wheel

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Экспорт порта, на котором будет работать приложение
EXPOSE 8000

# Запуск тестового Python-приложения
CMD ["python3", "main.py"]