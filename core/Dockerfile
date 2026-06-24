# INVISABLE OS core API
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml README.md ./
COPY invisable_os ./invisable_os
RUN pip install --upgrade pip && pip install ".[llm,memory]"

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx,os; httpx.get(f'http://localhost:{os.getenv(\"INVISABLE_API_PORT\",\"8080\")}/health').raise_for_status()"

CMD ["uvicorn", "invisable_os.main:app", "--host", "0.0.0.0", "--port", "8080"]
