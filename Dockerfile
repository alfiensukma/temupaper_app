# Gunakan base image Python 3.11 yang ringan
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Buat dan set direktori kerja
WORKDIR /app

# Salin file requirements dan instal dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh kode proyek ke dalam container
COPY . /app/

# Buat user non-root untuk keamanan
RUN adduser --disabled-password appuser
USER appuser

# Perintah default (akan di-override oleh docker-compose)
CMD ["gunicorn", "temupaper_app.asgi:application", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]