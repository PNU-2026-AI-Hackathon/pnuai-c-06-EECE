FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY web ./web

RUN pip install --no-cache-dir .

EXPOSE 8000

# Railway·Render 는 $PORT 를 주입한다. 없으면 8000.
CMD ["sh", "-c", "uvicorn web.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
