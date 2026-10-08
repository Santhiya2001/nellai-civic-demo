FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend:/app
WORKDIR /app
COPY backend/requirements.lock backend/requirements.lock
RUN pip install --no-cache-dir -r backend/requirements.lock
COPY backend backend
COPY modules modules
COPY database database
COPY ai ai
COPY scripts scripts
COPY alembic.ini pyproject.toml ./
RUN useradd --uid 10001 --create-home nellai && mkdir -p runtime/uploads && chown -R nellai:nellai /app
USER nellai
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
