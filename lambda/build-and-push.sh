#!/bin/bash
set -e

# Configuration
PROJECT_ID="esoteric-quanta-122920"
REGION="us-central1"
REPOSITORY="tldw-registry"
IMAGE_NAME="tldw"
TAG="${TAG:-latest}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Building and pushing Docker image to Google Artifact Registry${NC}"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Repository: $REPOSITORY"
echo "Image: $IMAGE_NAME:$TAG"
echo ""

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}Error: No active gcloud authentication found${NC}"
    echo "Please run: gcloud auth login"
    exit 1
fi

# Configure Docker for Artifact Registry
echo -e "${YELLOW}Configuring Docker for Artifact Registry...${NC}"
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

# Build the Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t ${IMAGE_NAME}:${TAG} .

# Tag for Artifact Registry
FULL_IMAGE_NAME="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${TAG}"
echo -e "${YELLOW}Tagging image as: ${FULL_IMAGE_NAME}${NC}"
docker tag ${IMAGE_NAME}:${TAG} ${FULL_IMAGE_NAME}

# Push to Artifact Registry
echo -e "${YELLOW}Pushing image to Artifact Registry...${NC}"
docker push ${FULL_IMAGE_NAME}

echo -e "${GREEN}✅ Successfully built and pushed Docker image!${NC}"
echo ""
echo "Image URL: ${FULL_IMAGE_NAME}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. cd infra"
echo "2. terraform init"
echo "3. terraform plan"
echo "4. terraform apply"