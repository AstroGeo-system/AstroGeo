FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install both backend and ML dependencies
COPY launch_model/requirements.txt ./launch_reqs.txt
COPY backend/requirements.txt ./backend_reqs.txt

RUN pip install --no-cache-dir -r launch_reqs.txt \
    && pip install --no-cache-dir -r backend_reqs.txt

# Create necessary directories
RUN mkdir -p /app/backend/data/models/launch

# Copy application files
COPY .env .env
COPY backend/ /app/backend/
COPY launch_model/models/ /app/data/models/launch/

EXPOSE 8000

# Run FastAPI using uvicorn
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
