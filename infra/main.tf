provider "aws" {
  region = "us-east-1"
}

# IAM Role for Lambda Execution
resource "aws_iam_role" "lambda_role" {
  name = "tldw_lambda_role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow"
    }
  ]
}
EOF
}

resource "aws_iam_policy_attachment" "lambda_basic_execution" {
  name       = "lambda_basic_execution"
  roles      = [aws_iam_role.lambda_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda Layer
resource "aws_lambda_layer_version" "tldw_layer" {
  filename            = "lambda_layer.zip"
  layer_name          = "tldw_layer"
  compatible_runtimes = ["python3.9"]
  source_code_hash    = filebase64sha256("lambda_layer.zip")
}

# Lambda Function
resource "aws_lambda_function" "tldw" {
  filename         = "lambda_function.zip"
  function_name    = "tldw_lambda"
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.lambda_handler"
  runtime         = "python3.9"
  timeout         = 300  # Increased to 5 minutes for processing
  memory_size     = 512  # Increase if needed
  source_code_hash = filebase64sha256("lambda_function.zip")
  layers          = [aws_lambda_layer_version.tldw_layer.arn]

  # Reserved concurrency to limit concurrent executions (cost protection)
  reserved_concurrent_executions = 5

  environment {
    variables = {
      OPENAI_API_KEY = var.OPENAI_API_KEY
    }
  }
}

# CloudWatch Log Group with retention
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.tldw.function_name}"
  retention_in_days = 7  # Reduce log retention to save costs
}

# Lambda Function URL (for streaming)
resource "aws_lambda_function_url" "tldw_url" {
  function_name      = aws_lambda_function.tldw.function_name
  authorization_type = "AWS_IAM"  # Changed to require IAM auth
  invoke_mode       = "RESPONSE_STREAM"
}

# API Gateway REST API
resource "aws_api_gateway_rest_api" "tldw_api" {
  name        = "tldw-api"
  description = "API for YouTube summarizer with rate limiting"
  
  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# API Gateway Resource
resource "aws_api_gateway_resource" "summarize" {
  rest_api_id = aws_api_gateway_rest_api.tldw_api.id
  parent_id   = aws_api_gateway_rest_api.tldw_api.root_resource_id
  path_part   = "summarize"
}

# API Gateway Method
resource "aws_api_gateway_method" "summarize_get" {
  rest_api_id   = aws_api_gateway_rest_api.tldw_api.id
  resource_id   = aws_api_gateway_resource.summarize.id
  http_method   = "GET"
  authorization = "NONE"
  
  request_parameters = {
    "method.request.querystring.url" = true
  }
}

# API Gateway Integration
resource "aws_api_gateway_integration" "lambda_integration" {
  rest_api_id = aws_api_gateway_rest_api.tldw_api.id
  resource_id = aws_api_gateway_resource.summarize.id
  http_method = aws_api_gateway_method.summarize_get.http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.tldw.invoke_arn
}

# Lambda Permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.tldw.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.tldw_api.execution_arn}/*/*"
}

# Usage Plan for Rate Limiting
resource "aws_api_gateway_usage_plan" "tldw_usage_plan" {
  name         = "tldw-usage-plan"
  description  = "Usage plan for TLDW API"

  api_stages {
    api_id = aws_api_gateway_rest_api.tldw_api.id
    stage  = aws_api_gateway_deployment.tldw_deployment.stage_name
  }

  throttle_settings {
    rate_limit  = 2    # 2 requests per second
    burst_limit = 5    # Allow bursts up to 5 requests
  }

  quota_settings {
    limit  = 100       # 100 requests per day
    period = "DAY"
  }
}

# API Key
resource "aws_api_gateway_api_key" "tldw_key" {
  name = "tldw-api-key"
}

# Usage Plan Key
resource "aws_api_gateway_usage_plan_key" "tldw_usage_plan_key" {
  key_id        = aws_api_gateway_api_key.tldw_key.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.tldw_usage_plan.id
}

# API Gateway Deployment
resource "aws_api_gateway_deployment" "tldw_deployment" {
  depends_on = [
    aws_api_gateway_method.summarize_get,
    aws_api_gateway_integration.lambda_integration,
  ]

  rest_api_id = aws_api_gateway_rest_api.tldw_api.id
  stage_name  = "prod"
}

# CloudWatch Billing Alarm (Optional but recommended)
resource "aws_cloudwatch_metric_alarm" "billing_alarm" {
  alarm_name          = "billing-alarm-tldw"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400"  # 24 hours
  statistic           = "Maximum"
  threshold           = "10"     # Alert if estimated charges exceed $10
  alarm_description   = "This metric monitors AWS estimated charges"
  alarm_actions       = []       # Add SNS topic ARN if you want notifications

  dimensions = {
    Currency = "USD"
  }
}

variable "OPENAI_API_KEY" {
  description = "API key for OpenAI service"
  type        = string
  sensitive   = true
}

# Outputs
output "api_gateway_url" {
  description = "API Gateway URL (rate limited, recommended for production)"
  value       = "${aws_api_gateway_rest_api.tldw_api.execution_arn}/prod/summarize"
}

output "api_key" {
  description = "API Gateway Key (keep this secret!)"
  value       = aws_api_gateway_api_key.tldw_key.value
  sensitive   = true
}

output "lambda_function_url" {
  description = "Direct Lambda URL (for streaming, use carefully)"
  value       = aws_lambda_function_url.tldw_url.function_url
}
