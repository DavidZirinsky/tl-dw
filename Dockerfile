FROM python:3.12-slim

# Set the working directory
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY tests ./tests


RUN pip install --no-cache-dir pytest
RUN pip install .


CMD ["pytest"]