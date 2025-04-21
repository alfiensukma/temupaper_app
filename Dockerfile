# Gunakan Python base image
FROM python:3.10-slim

# Set environment vars
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set workdir
WORKDIR /app

# Salin semua project
COPY . /app/

# Install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Expose port (opsional)
EXPOSE 8000

# Jalankan server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
