# Use an official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory in container
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y build-essential libpq-dev curl \
    && apt-get clean

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project code
COPY . /app/

# Collect static files (optional, if using)
# RUN python manage.py collectstatic --noinput

# Port the app runs on
EXPOSE 8000

# Run gunicorn server
CMD ["gunicorn", "b2bop_project.wsgi:application", "--bind", "0.0.0.0:8000", "--timeout", "120", "--workers", "3", "--threads", "2"]
