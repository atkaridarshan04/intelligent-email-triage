FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Download roberta-base at build time so first request is fast
# RUN python -c "\
# from transformers import RobertaTokenizerFast, RobertaModel; \
# RobertaTokenizerFast.from_pretrained('roberta-base'); \
# RobertaModel.from_pretrained('roberta-base')"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.serving.main:app", "--host", "0.0.0.0", "--port", "8000"]
