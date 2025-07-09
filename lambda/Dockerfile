FROM python:3.12.0-slim-bullseye

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    jq \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Heroku sets the PORT environment variable
ENV PORT=${PORT:-8080}

# Use the PORT environment variable set by Heroku
CMD uvicorn lambda_function:app --host 0.0.0.0 --port $PORT