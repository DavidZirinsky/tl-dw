#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# Get the absolute path of the script's directory
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_ROOT=$( cd -- "$SCRIPT_DIR/.." &> /dev/null && pwd )
INFRA_DIR="$PROJECT_ROOT/infra"

# Define the directory for the layer relative to the script
LAYER_DIR="$SCRIPT_DIR/lambda_layer"
BIN_DIR="$LAYER_DIR/bin"
PYTHON_PKGS_DIR="$LAYER_DIR/python/lib/python3.9/site-packages"

# Clean up previous build
echo "Cleaning up old layer directory and zip files..."
rm -rf "$LAYER_DIR"
rm -f "$INFRA_DIR/lambda_layer.zip"
rm -f "$INFRA_DIR/lambda_function.zip"

# Create directories
echo "Creating layer directories..."
mkdir -p "$BIN_DIR"
mkdir -p "$PYTHON_PKGS_DIR"

# Install Python packages
# This will also install dependencies like urllib3, certifi, etc.
echo "Installing Python dependencies..."
pip install requests 'aws-lambda-powertools[all]' yt-dlp -t "$PYTHON_PKGS_DIR"

# Download and install binaries
echo "Downloading jq (for 64-bit Linux)..."
# This URL points to a specific version of jq. You may want to update it in the future.
curl -L "https://github.com/jqlang/jq/releases/download/jq-1.7.1/jq-linux64" -o "$BIN_DIR/jq"

# Make binaries executable
echo "Setting permissions..."
chmod +x "$BIN_DIR/jq"

echo "Lambda layer contents created successfully in '$LAYER_DIR/'"

# Create zip files for deployment
echo "Creating deployment packages..."

echo "Zipping lambda layer..."
(cd "$LAYER_DIR" && zip -qr "$INFRA_DIR/lambda_layer.zip" .)

echo "Zipping lambda function..."
(cd "$SCRIPT_DIR" && zip -q "$INFRA_DIR/lambda_function.zip" lambda_function.py)

echo "Deployment packages created: lambda_layer.zip, lambda_function.zip"