# Gunakan base image Python 3.11 yang ringan
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV HF_HOME /app/.cache

# Buat dan set direktori kerja
WORKDIR /app

# Salin file requirements dan instal dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh kode proyek ke dalam container
COPY . /app/

RUN adduser --system --group appuser

RUN mkdir -p /app/app/data-csv /app/.cache

#    Berikan kepemilikan seluruh direktori aplikasi (termasuk .cache) ke user yang baru dibuat.
RUN chown -R appuser:appuser /app

USER appuser

# Perintah default untuk menjalankan aplikasi
CMD ["gunicorn", "temupaper_app.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]