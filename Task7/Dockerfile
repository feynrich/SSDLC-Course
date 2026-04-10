FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates/ templates/
COPY static/ static/

RUN useradd -m -u 1000 libraryuser
USER libraryuser

ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO
ENV FLASK_PORT=5000
ENV SECRET_KEY=change-me-in-production

EXPOSE 5000

CMD ["python", "app.py"]
