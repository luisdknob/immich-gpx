FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY immich_gpx/ ./immich_gpx/

# Entry point
ENTRYPOINT ["python", "-m", "immich_gpx.cli"]
