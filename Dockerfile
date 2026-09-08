FROM python:3.12-slim

# Evitar escritura de bytecode de python (.pyc) y forzar salida sin buffer
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalación de dependencias del sistema operativo C/C++ requeridas para psycopg2 y WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar e instalar requerimientos de python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el proyecto
COPY . /app/

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
