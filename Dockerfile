FROM python:3.12-slim

WORKDIR /app

# System deps for LightGBM
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and configs
COPY src/ src/
COPY configs/ configs/
COPY checkpoints/production/ checkpoints/production/
COPY data/assets/ data/assets/

# SQLite feedback DB persisted via volume mount in docker-compose.yml
# Create the data dir so the app can write feedback.db at runtime
RUN mkdir -p data

EXPOSE 8000

CMD ["uvicorn", "src.serving.api:app", "--host", "0.0.0.0", "--port", "8000"]
