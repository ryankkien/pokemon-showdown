#!/bin/bash
# Pokemon Showdown LLM Battle Service - Build and Deploy Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="pokemon-showdown-llm"
IMAGE_TAG=${1:-latest}
ENVIRONMENT=${2:-development}

echo -e "${BLUE}🚀 Building and deploying Pokemon Showdown LLM Battle Service${NC}"
echo -e "${YELLOW}Image: ${IMAGE_NAME}:${IMAGE_TAG}${NC}"
echo -e "${YELLOW}Environment: ${ENVIRONMENT}${NC}"

# Function to print status
print_status() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if required files exist
if [ ! -f "Dockerfile" ]; then
    print_error "Dockerfile not found!"
    exit 1
fi

if [ ! -f "docker-compose.yml" ]; then
    print_error "docker-compose.yml not found!"
    exit 1
fi

# Check if .env file exists, create from example if not
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        print_warning "No .env file found, copying from .env.example"
        cp .env.example .env
        print_warning "Please edit .env file with your actual configuration!"
    else
        print_error "No .env or .env.example file found!"
        exit 1
    fi
fi

# Build Docker image
echo -e "${BLUE}📦 Building Docker image...${NC}"
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
print_status "Docker image built successfully"

# Tag as latest if not already
if [ "${IMAGE_TAG}" != "latest" ]; then
    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest
    print_status "Tagged image as latest"
fi

# Stop existing containers
echo -e "${BLUE}🛑 Stopping existing services...${NC}"
docker-compose down --remove-orphans || true
print_status "Stopped existing services"

# Clean up old containers and images
echo -e "${BLUE}🧹 Cleaning up...${NC}"
docker system prune -f || true
print_status "Cleaned up unused containers and images"

# Start services based on environment
if [ "${ENVIRONMENT}" = "production" ]; then
    echo -e "${BLUE}🚀 Starting production services...${NC}"
    docker-compose --profile monitoring up -d
elif [ "${ENVIRONMENT}" = "development" ]; then
    echo -e "${BLUE}🚀 Starting development services...${NC}"
    docker-compose up -d
else
    print_error "Unknown environment: ${ENVIRONMENT}"
    exit 1
fi

print_status "Services started successfully"

# Wait for services to be healthy
echo -e "${BLUE}⏳ Waiting for services to be healthy...${NC}"
sleep 10

# Check service health
check_service_health() {
    local service_name=$1
    local url=$2
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            print_status "$service_name is healthy"
            return 0
        fi
        
        echo -ne "\r⏳ Waiting for $service_name... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    echo "" # New line
    print_error "$service_name failed to become healthy"
    return 1
}

# Health checks
check_service_health "Leaderboard API" "http://localhost:5000/api/stats"
check_service_health "Pokemon Showdown Server" "http://localhost:8000"

if [ "${ENVIRONMENT}" = "production" ]; then
    check_service_health "Prometheus" "http://localhost:9090/-/healthy"
    check_service_health "Grafana" "http://localhost:3000/api/health"
fi

# Show running containers
echo -e "${BLUE}📋 Running containers:${NC}"
docker-compose ps

# Show logs for any failed containers
echo -e "${BLUE}📊 Checking for any failed containers...${NC}"
failed_containers=$(docker-compose ps --filter "status=exited" --format "table {{.Service}}")
if [ ! -z "$failed_containers" ] && [ "$failed_containers" != "SERVICE" ]; then
    print_warning "Some containers have exited:"
    echo "$failed_containers"
    echo -e "${YELLOW}💡 Check logs with: docker-compose logs [service-name]${NC}"
fi

# Display access information
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo ""
echo -e "${BLUE}📍 Service URLs:${NC}"
echo "  🌐 Leaderboard: http://localhost"
echo "  📊 API: http://localhost/api/"
echo "  🎮 Showdown Server: http://localhost/showdown/"

if [ "${ENVIRONMENT}" = "production" ]; then
    echo "  📈 Prometheus: http://localhost:9090"
    echo "  📊 Grafana: http://localhost:3000 (admin/admin123)"
fi

echo ""
echo -e "${YELLOW}💡 Useful commands:${NC}"
echo "  📋 View logs: docker-compose logs [service-name]"
echo "  🔄 Restart service: docker-compose restart [service-name]"
echo "  🛑 Stop all: docker-compose down"
echo "  📊 View status: docker-compose ps"

if [ "${ENVIRONMENT}" = "development" ]; then
    echo ""
    print_warning "Remember to configure your API keys in the .env file!"
fi