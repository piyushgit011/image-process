#!/bin/bash

# Image Processing Pipeline Startup Script
# Handles initialization and startup of the pipeline components

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if required environment variables are set
check_environment() {
    log "Checking environment variables..."
    
    local required_vars=("AWS_ACCESS_KEY_ID" "AWS_SECRET_ACCESS_KEY")
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        error "Missing required environment variables: ${missing_vars[*]}"
        error "Please set these variables before starting the pipeline"
        exit 1
    fi
    
    success "Environment variables check passed"
}

# Check if model files exist
check_models() {
    log "Checking model files..."
    
    local models=("Car Face Blur Model.pt" "Car Face Blur Yolov8m.pt")
    local missing_models=()
    
    for model in "${models[@]}"; do
        if [ ! -f "$model" ]; then
            missing_models+=("$model")
        fi
    done
    
    if [ ${#missing_models[@]} -ne 0 ]; then
        error "Missing model files: ${missing_models[*]}"
        error "Please ensure all model files are present in the current directory"
        exit 1
    fi
    
    success "Model files check passed"
}

# Check if Redis is accessible
check_redis() {
    log "Checking Redis connectivity..."
    
    local redis_url="${REDIS_URL:-redis://localhost:6379}"
    local host=$(echo "$redis_url" | sed 's|redis://||' | cut -d: -f1)
    local port=$(echo "$redis_url" | sed 's|redis://||' | cut -d: -f2)
    
    if command -v redis-cli &> /dev/null; then
        if redis-cli -h "$host" -p "$port" ping &> /dev/null; then
            success "Redis connectivity check passed"
        else
            warning "Redis connectivity check failed - Redis may not be running"
            warning "The pipeline will attempt to connect to Redis during startup"
        fi
    else
        warning "redis-cli not found - skipping Redis connectivity check"
    fi
}

# Check Python dependencies
check_dependencies() {
    log "Checking Python dependencies..."
    
    if ! python -c "import torch, fastapi, redis, aioboto3" &> /dev/null; then
        error "Missing required Python dependencies"
        error "Please install dependencies with: pip install -r requirements.txt"
        exit 1
    fi
    
    success "Python dependencies check passed"
}

# Initialize the pipeline
initialize_pipeline() {
    log "Initializing image processing pipeline..."
    
    # Create necessary directories
    mkdir -p logs
    mkdir -p models
    
    # Copy model files to models directory if they exist in current directory
    if [ -f "Car Face Blur Model.pt" ]; then
        cp "Car Face Blur Model.pt" models/
    fi
    
    if [ -f "Car Face Blur Yolov8m.pt" ]; then
        cp "Car Face Blur Yolov8m.pt" models/
    fi
    
    success "Pipeline initialization completed"
}

# Start the API server
start_api_server() {
    log "Starting API server..."
    
    # Check if API server is already running
    if pgrep -f "api_server.py" > /dev/null; then
        warning "API server is already running"
        return
    fi
    
    # Start API server in background
    nohup python api_server.py > logs/api_server.log 2>&1 &
    local api_pid=$!
    
    # Wait for API server to start
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            success "API server started successfully (PID: $api_pid)"
            echo $api_pid > logs/api_server.pid
            return
        fi
        
        attempt=$((attempt + 1))
        sleep 2
    done
    
    error "API server failed to start within 60 seconds"
    exit 1
}

# Start processing workers
start_workers() {
    local num_workers=${NUM_WORKERS:-3}
    log "Starting $num_workers processing workers..."
    
    # Check if workers are already running
    local running_workers=$(pgrep -f "worker.py" | wc -l)
    if [ "$running_workers" -gt 0 ]; then
        warning "$running_workers workers are already running"
        return
    fi
    
    # Start workers
    for i in $(seq 1 $num_workers); do
        export WORKER_ID="worker-$i"
        nohup python worker.py > logs/worker_$i.log 2>&1 &
        local worker_pid=$!
        echo $worker_pid > logs/worker_$i.pid
        log "Started worker $i (PID: $worker_pid)"
    done
    
    success "Started $num_workers processing workers"
}

# Check pipeline health
check_pipeline_health() {
    log "Checking pipeline health..."
    
    # Check API server
    if curl -f http://localhost:8000/health &> /dev/null; then
        success "API server is healthy"
    else
        error "API server is not responding"
        return 1
    fi
    
    # Check queue status
    local queue_status=$(curl -s http://localhost:8000/queue-status | jq -r '.queue_depth // "unknown"')
    if [ "$queue_status" != "unknown" ]; then
        log "Queue depth: $queue_status"
    fi
    
    # Check pipeline stats
    local stats=$(curl -s http://localhost:8000/stats)
    if [ $? -eq 0 ]; then
        local processed=$(echo "$stats" | jq -r '.pipeline_stats.total_processed // 0')
        local failed=$(echo "$stats" | jq -r '.pipeline_stats.total_failed // 0')
        log "Pipeline stats - Processed: $processed, Failed: $failed"
    fi
    
    success "Pipeline health check completed"
}

# Stop the pipeline
stop_pipeline() {
    log "Stopping image processing pipeline..."
    
    # Stop API server
    if [ -f logs/api_server.pid ]; then
        local api_pid=$(cat logs/api_server.pid)
        if kill -0 $api_pid 2>/dev/null; then
            kill $api_pid
            log "Stopped API server (PID: $api_pid)"
        fi
        rm -f logs/api_server.pid
    fi
    
    # Stop workers
    for pid_file in logs/worker_*.pid; do
        if [ -f "$pid_file" ]; then
            local worker_pid=$(cat "$pid_file")
            if kill -0 $worker_pid 2>/dev/null; then
                kill $worker_pid
                log "Stopped worker (PID: $worker_pid)"
            fi
            rm -f "$pid_file"
        fi
    done
    
    # Kill any remaining Python processes
    pkill -f "api_server.py" 2>/dev/null || true
    pkill -f "worker.py" 2>/dev/null || true
    
    success "Pipeline stopped"
}

# Show pipeline status
show_status() {
    log "Pipeline status:"
    
    # Check API server
    if [ -f logs/api_server.pid ]; then
        local api_pid=$(cat logs/api_server.pid)
        if kill -0 $api_pid 2>/dev/null; then
            echo "  API Server: Running (PID: $api_pid)"
        else
            echo "  API Server: Not running"
        fi
    else
        echo "  API Server: Not running"
    fi
    
    # Check workers
    local running_workers=0
    for pid_file in logs/worker_*.pid; do
        if [ -f "$pid_file" ]; then
            local worker_pid=$(cat "$pid_file")
            if kill -0 $worker_pid 2>/dev/null; then
                running_workers=$((running_workers + 1))
            fi
        fi
    done
    echo "  Workers: $running_workers running"
    
    # Check pipeline health
    if curl -f http://localhost:8000/health &> /dev/null; then
        echo "  Health: Healthy"
    else
        echo "  Health: Unhealthy"
    fi
}

# Main function
main() {
    case "${1:-start}" in
        "start")
            log "Starting image processing pipeline..."
            check_environment
            check_models
            check_redis
            check_dependencies
            initialize_pipeline
            start_api_server
            start_workers
            sleep 5
            check_pipeline_health
            success "Pipeline started successfully"
            ;;
        "stop")
            stop_pipeline
            ;;
        "restart")
            log "Restarting pipeline..."
            stop_pipeline
            sleep 2
            $0 start
            ;;
        "status")
            show_status
            ;;
        "health")
            check_pipeline_health
            ;;
        *)
            echo "Usage: $0 {start|stop|restart|status|health}"
            echo ""
            echo "Commands:"
            echo "  start   - Start the pipeline"
            echo "  stop    - Stop the pipeline"
            echo "  restart - Restart the pipeline"
            echo "  status  - Show pipeline status"
            echo "  health  - Check pipeline health"
            exit 1
            ;;
    esac
}

# Handle signals
trap 'log "Received signal, stopping pipeline..."; stop_pipeline; exit 0' SIGINT SIGTERM

# Run main function
main "$@" 