FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
COPY db_settings.json .
COPY main.py .

RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -m pinger && chown -R pinger:pinger /app
USER pinger

CMD ["python", "main.py"]