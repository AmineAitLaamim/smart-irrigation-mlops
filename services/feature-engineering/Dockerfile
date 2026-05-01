FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/bin/uv

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN uv venv && uv pip install --no-cache -r requirements.txt

COPY src/ ./src/

EXPOSE 8004

ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "--no-project", "python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8004"]
