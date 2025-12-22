FROM python:3.12-slim

WORKDIR /app

COPY backend/pyproject.toml backend/README.md /app/backend/
COPY backend/app /app/backend/app
COPY backend/db /app/backend/db

RUN pip install --no-cache-dir -e /app/backend

ENV PYTHONUNBUFFERED=1
EXPOSE 8200

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8200"]

