# Simple Python runtime for bots
FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir poetry==1.8.3
COPY pyproject.toml README.md ./
RUN poetry config virtualenvs.create false && poetry install --no-root --no-interaction --no-ansi
COPY . .
CMD ["python", "-m", "orchestrator.main", "--env", "testnet"]
