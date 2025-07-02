FROM public.ecr.aws/docker/library/python:3.12.0-slim-bullseye

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      jq \
      ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Lambda Web Adapter as an “extension” layer
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 \
     /lambda-adapter /opt/extensions/lambda-adapter


WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV PORT=8080
ENV AWS_LWA_PORT=8080
ENV AWS_LWA_INVOKE_MODE=RESPONSE_STREAM
ENV AWS_LAMBDA_EXEC_WRAPPER=/opt/extensions/lambda-adapter


CMD ["uvicorn", "lambda_function:app", "--host", "0.0.0.0", "--port", "8080"]