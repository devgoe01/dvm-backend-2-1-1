# Base image for Python 3.11 slim version.
FROM python:3.11-slim

# Set environment variables.
ENV PYTHONDONTWRITEBYTECODE 1 \
    PYTHONUNBUFFERED 1

# Set working directory.
WORKDIR /bus_service

# Install system dependencies.
RUN apt-get update && apt-get install -y netcat-openbsd gcc postgresql-client && apt-get clean

# Install Python dependencies.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy project files.
COPY . .

# Add entrypoint script and make it executable.
COPY ./entrypoint2.sh /entrypoint2.sh
RUN chmod +x /entrypoint2.sh

# Expose port 8000 for internal communication.
EXPOSE 8000

ENTRYPOINT ["/entrypoint2.sh"]
