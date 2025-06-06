FROM python:3.10-slim

# Install dependensi OS minimal
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    rm -rf /var/lib/apt/lists/*

# Env setting
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements, install python dependency
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy semua source code Django
COPY . /app/

# (Opsional, jika menggunakan whitenoise, aktifkan baris ini)
RUN python manage.py collectstatic --noinput

EXPOSE 8080

# Gunicorn default Django WSGI (ganti jika struktur tidak biasa)
CMD python manage.py migrate && gunicorn temupaper_app.wsgi:application --workers 5 --threads 4 --bind 0.0.0.0:8080