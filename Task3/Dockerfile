FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY main.py .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -m -u 1000 libraryuser
USER libraryuser

ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO

CMD ["python", "main.py"]