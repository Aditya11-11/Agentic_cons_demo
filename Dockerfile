FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    libasound2-dev \
    libgl1 \
    libglib2.0-0 \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN mkdir -p /opt && \
    wget -q https://alphacephei.com/vosk/models/vosk-model-en-in-0.5.zip && \
    unzip vosk-model-en-in-0.5.zip -d /opt && \
    mv /opt/vosk-model-en-in-0.5 /opt/vosk-model-en && \
    rm vosk-model-en-in-0.5.zip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Ensure the knowledge base directory exists
RUN mkdir -p /data

ENV VOSK_MODEL_PATH=/opt/vosk-model-en
ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
