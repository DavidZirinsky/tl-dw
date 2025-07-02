FROM public.ecr.aws/docker/library/python:3.12.0-slim-bullseye

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      jq \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Download AWS Lambda Runtime Interface Emulator (RIE)
ADD https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie /usr/local/bin/aws-lambda-rie
RUN chmod +x /usr/local/bin/aws-lambda-rie

# Lambda Web Adapter extension
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 \
     /lambda-adapter /opt/extensions/lambda-adapter

# Environment for adapter & streaming
ENV AWS_LAMBDA_EXEC_WRAPPER=/opt/extensions/lambda-adapter
# Internal port for Uvicorn
ENV PORT=3000
# Adapter health-check port (must match Uvicorn)
ENV AWS_LWA_PORT=3000
ENV AWS_LWA_INVOKE_MODE=RESPONSE_STREAM

WORKDIR /app

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

# Use RIE as ENTRYPOINT, specifying adapter as bootstrap
ENTRYPOINT ["/usr/local/bin/aws-lambda-rie", "--bootstrap", "/opt/extensions/lambda-adapter"]
# Launch Uvicorn on the adapter-poll port
CMD ["uvicorn", "lambda_function:app", "--host", "0.0.0.0", "--port", "3000"]
