FROM python:3.12-slim

WORKDIR /app

# Install dependencies first — layer cache optimization
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
# Note: .env is excluded — secrets come from Compose environment at runtime
COPY . .

EXPOSE 8000

# compose.yaml overrides this CMD with: alembic upgrade head && uvicorn ...
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
