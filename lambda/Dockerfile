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

#Set the Lambda invoke mode
ENV AWS_LWA_INVOKE_MODE=RESPONSE_STREAM

CMD ["python", "lambda_function.py"]