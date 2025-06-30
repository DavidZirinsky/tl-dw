provider "aws" {
  region = "us-east-1"
}

# IAM Role for Lambda Execution
resource "aws_iam_role" "lambda_role" {
  name               = "tldw_lambda_role"
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
  role             = aws_iam_role.lambda_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.9"
  timeout          = 120 # Increased timeout
  source_code_hash = filebase64sha256("lambda_function.zip")
  layers           = [aws_lambda_layer_version.tldw_layer.arn]
  # ENV Variable
  environment {
    variables = {
      OPENAI_API_KEY = var.OPENAI_API_KEY
    }
  }
}

# Lambda Function URL
resource "aws_lambda_function_url" "tldw_url" {
  function_name      = aws_lambda_function.tldw.function_name
  authorization_type = "NONE"
  invoke_mode        = "RESPONSE_STREAM"
}

variable "OPENAI_API_KEY" {
  description = "API key for the service"
  type        = string
  sensitive   = true # Marks as sensitive to hide in logs
}

# Output the API URLs
output "lambda_function_url" {
  value = aws_lambda_function_url.tldw_url.function_url
}

