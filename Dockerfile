FROM python:3.12-slim

# Set the working directory
WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY tests ./tests

RUN pip install --no-cache-dir build pytest

# This is to build a wheel package to make sure PyPI doesn't break
RUN python -m build --wheel
RUN pip install dist/*.whl

CMD ["pytest"]