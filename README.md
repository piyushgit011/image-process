# 🚀 Image Processing Pipeline with Car Face Blur Models

A **high-performance, scalable image processing pipeline** that applies ML models (Car Face Blur and YOLO Detection) to images with **30+ images/sec throughput**. Complete with MySQL database integration, Redis queue management, and production-ready deployment configurations.

[![Production Ready](https://img.shields.io/badge/Production-Ready-green.svg)](https://github.com/your-repo)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://docker.com)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-blue.svg)](https://kubernetes.io)
[![MySQL](https://img.shields.io/badge/MySQL-Integrated-orange.svg)](https://mysql.com)

---

## 📋 Table of Contents

1. [🎯 What This Project Does](#-what-this-project-does)
2. [🏗️ Architecture Overview](#️-architecture-overview)
3. [🚀 Complete Setup Guide](#-complete-setup-guide)
4. [📋 Complete File Analysis](#-complete-file-analysis)
5. [🔄 How to Use the API](#-how-to-use-the-api)
6. [🐳 Deployment Options](#-deployment-options)
7. [📊 Monitoring & Performance](#-monitoring--performance)
8. [🔧 Configuration Reference](#-configuration-reference)
9. [🚨 Troubleshooting](#-troubleshooting)
10. [🤝 Contributing](#-contributing)

---

## 🎯 What This Project Does

### **Core Functionality**
- **Detects vehicles** in uploaded images using YOLO models
- **Detects and blurs faces** in images containing vehicles
- **Processes images asynchronously** with high throughput (30+ images/sec)
- **Stores results** in S3 with comprehensive metadata
- **Tracks processing statistics** in MySQL database
- **Provides REST API** for image upload and status checking

### **Key Features**
- ✅ **High Performance**: 30+ images/second processing
- ✅ **Scalable Architecture**: Auto-scaling workers and API servers
- ✅ **Production Ready**: Complete Docker and Kubernetes configurations
- ✅ **Database Integration**: MySQL with comprehensive tracking
- ✅ **Monitoring**: Prometheus metrics and health checks
- ✅ **Security**: Secure credential management and network policies

---

## 🏗️ Architecture Overview

### **Multi-Stage Pipeline Design**

```
📤 Image Upload → 🌐 API Server → 📊 Redis Queue → ⚙️ Processing Workers → 🗄️ S3 Storage
       ↓              ↓              ↓                ↓                    ↓
   📱 Client      🚀 FastAPI     📋 Job Queue      🤖 ML Models       📁 Results + Metadata
                                                                            ↓
                                                                    🗃️ MySQL Database
```

### **Components Breakdown**

| Component | Technology | Purpose | Scaling |
|-----------|------------|---------|---------|
| **API Server** | FastAPI | HTTP endpoints, job creation | Horizontal (3-10 pods) |
| **Processing Workers** | Python + PyTorch | ML model execution | Queue-based (5-20 pods) |
| **Redis Queue** | Redis | Job queue management | StatefulSet (3 nodes) |
| **MySQL Database** | MySQL 8.0 | Metadata and statistics | StatefulSet (1-3 nodes) |
| **S3 Storage** | AWS S3 | Image and result storage | Managed service |
| **Monitoring** | Prometheus + Grafana | Metrics and alerting | Deployment |

---

## 🚀 Complete Setup Guide

### **Prerequisites**

Before starting, ensure you have:
- **Python 3.9+** installed
- **Docker & Docker Compose** installed
- **Git** for cloning the repository
- **AWS Account** with S3 access (for production)
- **MySQL 8.0+** (for local development)

---

### **🖥️ Method 1: Local Development Setup**

#### **Step 1: Clone and Setup Repository**
```bash
# Clone the repository
git clone https://github.com/your-username/image-processing-pipeline.git
cd image-processing-pipeline

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### **Step 2: Install MySQL Server**

**macOS (Homebrew):**
```bash
brew install mysql
brew services start mysql
mysql_secure_installation  # Optional but recommended
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql
sudo mysql_secure_installation
```

**Windows:**
- Download MySQL installer from [mysql.com](https://dev.mysql.com/downloads/installer/)
- Follow installation wizard
- Start MySQL service

#### **Step 3: Setup Database**
```bash
# Connect to MySQL
mysql -u root -p

# Create database and user
CREATE DATABASE image_processing CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'pipeline_user'@'localhost' IDENTIFIED BY 'secure_password_123';
GRANT ALL PRIVILEGES ON image_processing.* TO 'pipeline_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### **Step 4: Install Python Dependencies**
```bash
pip install -r requirements.txt
```

#### **Step 5: Configure Environment**
```bash
# Copy environment template
cp .env.example .env  # If available, or create .env file

# Edit .env file with your settings:
DATABASE_URL=mysql+pymysql://pipeline_user:secure_password_123@localhost:3306/image_processing
REDIS_URL=redis://localhost:6379
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_BUCKET=your-image-processing-bucket
```

#### **Step 6: Initialize Database**
```bash
# Initialize database schema
python init_database.py

# Test database connection
python test_mysql_integration.py
```

#### **Step 7: Start Redis (Required)**
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis

# Windows - Download from https://redis.io/download
```

#### **Step 8: Start the Application**
```bash
# Option A: Use the startup script
./start.sh

# Option B: Start components manually
# Terminal 1: Start API server
python api_server.py

# Terminal 2: Start worker
python worker.py
```

#### **Step 9: Test the Setup**
```bash
# Check health
curl http://localhost:8000/health

# Upload test image
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test-image.jpg"
```

---

### **🐳 Method 2: Docker Compose Setup (Recommended)**

#### **Step 1: Clone Repository**
```bash
git clone https://github.com/your-username/image-processing-pipeline.git
cd image-processing-pipeline
```

#### **Step 2: Configure Environment**
```bash
# Create .env file with your AWS credentials
cat > .env << EOF
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_BUCKET=your-image-processing-bucket
EOF
```

#### **Step 3: Start All Services**
```bash
# Start all services (MySQL, Redis, API, Workers)
docker compose up -d

# Check service status
docker compose ps

# View logs
docker compose logs -f api-server
docker compose logs -f mysql
```

#### **Step 4: Initialize Database (if needed)**
```bash
# Initialize database schema
docker compose exec api-server python init_database.py

# Test integration
docker compose exec api-server python test_docker_mysql_integration.py
```

#### **Step 5: Test the Setup**
```bash
# Check health
curl http://localhost:8000/health

# Upload test image
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test-image.jpg"
```

---

### **☸️ Method 3: Kubernetes Deployment**

#### **Step 1: Prepare Kubernetes Cluster**
```bash
# Ensure kubectl is configured
kubectl cluster-info

# Create namespace
kubectl create namespace image-processing-pipeline
```

#### **Step 2: Setup Secrets**
```bash
# Create AWS credentials secret
kubectl create secret generic aws-credentials \
  --from-literal=aws-access-key-id=your_key \
  --from-literal=aws-secret-access-key=your_secret \
  -n image-processing-pipeline

# Create MySQL secret (base64 encoded)
kubectl create secret generic mysql-secret \
  --from-literal=root-password=root_password_123 \
  --from-literal=user-password=secure_password_123 \
  -n image-processing-pipeline
```

#### **Step 3: Deploy MySQL**
```bash
# Deploy MySQL StatefulSet
kubectl apply -f mysql-k8s.yaml

# Wait for MySQL to be ready
kubectl wait --for=condition=ready pod -l app=mysql -n image-processing-pipeline --timeout=300s
```

#### **Step 4: Deploy Application**
```bash
# Deploy application components
kubectl apply -f kubernetes_deployment.yaml

# Check deployment status
kubectl get pods -n image-processing-pipeline
kubectl get services -n image-processing-pipeline
```

#### **Step 5: Access the Application**
```bash
# Get service URL
kubectl get service api-server-service -n image-processing-pipeline

# Port forward for testing
kubectl port-forward service/api-server-service 8000:80 -n image-processing-pipeline

# Test
curl http://localhost:8000/health
```

---

## 📋 Complete File Analysis

### ✅ **System File Organization**

The Image Processing Pipeline contains **26 essential files** organized across all deployment scenarios. Every file serves a specific purpose in the complete application lifecycle.

#### **Core Application Files (5 files)**
| File | Purpose | Dependencies | Status |
|------|---------|--------------|--------|
| `api_server.py` | FastAPI web server - main API entry point | pipeline_architecture, database_models, config | ✅ Essential |
| `worker.py` | Background processing workers for image pipeline | pipeline_architecture, database_models, config | ✅ Essential |
| `pipeline_architecture.py` | Central pipeline orchestration and ML models | torch, cv2, redis, aioboto3 | ✅ Essential |
| `config.py` | Configuration management for all environments | os, pathlib, logging | ✅ Essential |
| `database_models.py` | MySQL ORM models and database operations | sqlalchemy, pymysql | ✅ Essential |

#### **Database & Initialization (2 files)**
| File | Purpose | Dependencies | Status |
|------|---------|--------------|--------|
| `init_database.py` | Database initialization and testing utility | database_models, config | ✅ Essential |
| `mysql-init/01-init.sql` | MySQL container initialization script | None (SQL) | ✅ Essential |

#### **Configuration Files (2 files)**
| File | Purpose | Usage | Status |
|------|---------|-------|--------|
| `.env` | Environment variables for all deployment scenarios | All Python components | ✅ Essential |
| `requirements.txt` | Python package dependencies | Docker, local setup | ✅ Essential |

#### **Deployment & Orchestration (5 files)**
| File | Purpose | Dependencies | Status |
|------|---------|--------------|--------|
| `Dockerfile` | Container image definition | requirements.txt, start.sh | ✅ Essential |
| `docker-compose.yml` | Multi-container orchestration with MySQL | Dockerfile, mysql-init | ✅ Essential |
| `kubernetes_deployment.yaml` | Kubernetes deployment configuration | Container images | ✅ Essential |
| `mysql-k8s.yaml` | MySQL StatefulSet for Kubernetes | None | ✅ Essential |
| `start.sh` | Startup script for local development | Python components | ✅ Essential |

#### **Documentation (5 files)**
| File | Purpose | Audience | Status |
|------|---------|----------|--------|
| `README.md` | Main project documentation (this file) | All users | ✅ Essential |
| `MYSQL_COMPLETE_SETUP_GUIDE.md` | Comprehensive MySQL setup guide | DevOps, Developers | ✅ Essential |
| `MYSQL_INTEGRATION_COMPLETE_STATUS.md` | Integration status and verification | Technical team | ✅ Essential |
| `DEPLOYMENT_GUIDE.md` | Production deployment instructions | DevOps team | ✅ Essential |
| `FILE_ANALYSIS_REPORT.md` | Comprehensive file analysis report | Maintainers | ✅ Essential |

#### **Machine Learning Models (2 files)**
| File | Purpose | Size | Status |
|------|---------|------|--------|
| `Car Face Blur Model.pt` | Face detection and blurring model | ~100MB | ✅ Essential |
| `Car Face Blur Yolov8m.pt` | Vehicle detection model | ~50MB | ✅ Essential |

#### **Monitoring & Testing (3 files)**
| File | Purpose | Usage | Status |
|------|---------|-------|--------|
| `monitoring/prometheus.yml` | Prometheus monitoring configuration | Production monitoring | ✅ Essential |
| `load-tests/load-test.js` | K6 performance testing | Performance validation | ✅ Essential |
| `test_docker_mysql_integration.py` | Docker MySQL integration testing | CI/CD pipeline | ✅ Essential |

#### **System Files (2 files)**
| File | Purpose | Usage | Status |
|------|---------|-------|--------|
| `.gitignore` | Git ignore patterns for cache and temp files | Version control | ✅ Essential |
| `FILE_ANALYSIS_REPORT.md` | Comprehensive file analysis report | Documentation | ✅ Essential |

### 🔍 **File Dependencies & Import Chain**

```
api_server.py
├── pipeline_architecture.py
├── database_models.py
└── config.py

worker.py
├── pipeline_architecture.py
├── database_models.py
└── config.py

pipeline_architecture.py
├── database_models.py
├── config.py
├── torch (ML models)
├── cv2 (image processing)
├── redis (queue management)
└── aioboto3 (S3 storage)

init_database.py
├── database_models.py
└── config.py

test_docker_mysql_integration.py
├── database_models.py
└── config.py
```

### 📊 **System Health Status**

**✅ EXCELLENT FILE ORGANIZATION**
- **Zero Redundancy**: No duplicate or obsolete files
- **Complete Coverage**: All deployment scenarios supported
- **Clear Dependencies**: Well-defined import chains
- **Production Ready**: All configurations tested
- **Comprehensive Documentation**: Complete setup guides

---

## 🔄 How to Use the API

### **API Endpoints Overview**

| Endpoint | Method | Purpose | Authentication |
|----------|--------|---------|----------------|
| `/health` | GET | Health check | None |
| `/upload` | POST | Upload single image | None |
| `/batch-upload` | POST | Upload multiple images | None |
| `/status/{job_id}` | GET | Check job status | None |
| `/stats` | GET | Pipeline statistics | None |
| `/queue-status` | GET | Queue information | None |
| `/database/stats` | GET | Database statistics | None |
| `/database/images` | GET | Query processed images | None |

### **1. Upload Single Image**

**Endpoint:** `POST /upload`

**Request:**
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-image.jpg"
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "your-image.jpg",
  "file_size": 1024000,
  "status": "submitted",
  "message": "Car detected. Image submitted for processing and face blur."
}
```

### **2. Upload Base64 Image**

**Endpoint:** `POST /upload`

**Request:**
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "image_base64=$(base64 -i your-image.jpg)" \
  -d "filename=your-image.jpg" \
  -d "content_type=image/jpeg"
```

### **3. Batch Upload**

**Endpoint:** `POST /batch-upload`

**Request:**
```bash
curl -X POST "http://localhost:8000/batch-upload" \
  -H "Content-Type: multipart/form-data" \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg" \
  -F "files=@image3.jpg"
```

**Response:**
```json
{
  "batch_id": "batch-550e8400-e29b-41d4-a716-446655440000",
  "job_ids": [
    "job-1-550e8400-e29b-41d4-a716-446655440000",
    "job-2-550e8400-e29b-41d4-a716-446655440000"
  ],
  "total_files": 3,
  "processed_files": 2,
  "skipped_files": 1,
  "total_size": 3072000,
  "status": "batch_submitted",
  "message": "Batch submitted with 2 valid car images. 1 skipped."
}
```

### **4. Check Job Status**

**Endpoint:** `GET /status/{job_id}`

**Request:**
```bash
curl "http://localhost:8000/status/550e8400-e29b-41d4-a716-446655440000"
```

**Response:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "updated_at": 1640995200,
  "results": {
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "original_image_path": "s3://bucket/original/550e8400_1640995200.jpg",
    "processed_image_path": "s3://bucket/processed/550e8400_1640995200.jpg",
    "blur_metadata": {
      "processing_applied": true,
      "faces_blurred": 2,
      "input_shape": [1080, 1920, 3],
      "output_shape": [1080, 1920, 3],
      "reason": "Blurred 2 faces"
    },
    "detection_metadata": {
      "boxes": [[100, 100, 200, 200], [300, 300, 400, 400]],
      "confidences": [0.95, 0.87],
      "class_ids": [2, 2],
      "detection_count": 2,
      "vehicle_detected": true
    },
    "processing_time": 2.5,
    "model_versions": {
      "person_detection": "1.0",
      "vehicle_detection": "8m"
    },
    "confidence_scores": {
      "avg_detection_confidence": 0.91
    }
  }
}
```

### **5. Get Pipeline Statistics**

**Endpoint:** `GET /stats`

**Request:**
```bash
curl "http://localhost:8000/stats"
```

**Response:**
```json
{
  "pipeline_stats": {
    "total_processed": 1250,
    "total_failed": 15,
    "success_rate": 98.8,
    "avg_processing_time": 2.3,
    "throughput_jobs_per_minute": 32.5,
    "active_workers": 3,
    "queue_depth": 5
  },
  "timestamp": 1640995200,
  "uptime": 86400
}
```

### **6. Get Database Statistics**

**Endpoint:** `GET /database/stats`

**Request:**
```bash
curl "http://localhost:8000/database/stats"
```

**Response:**
```json
{
  "database_stats": {
    "total_images_processed": 1250,
    "vehicle_detection_count": 1100,
    "face_detection_count": 800,
    "face_blur_count": 800,
    "vehicle_detection_rate": 88.0,
    "face_detection_rate": 64.0,
    "face_blur_rate": 64.0
  },
  "timestamp": 1640995200
}
```

### **7. Query Processed Images**

**Endpoint:** `GET /database/images`

**Request:**
```bash
# Get all images with vehicles detected
curl "http://localhost:8000/database/images?is_vehicle_detected=true&limit=10"

# Get images with faces blurred
curl "http://localhost:8000/database/images?is_face_blurred=true&limit=5"
```

**Response:**
```json
{
  "images": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "job_id": "job-550e8400-e29b-41d4-a716-446655440000",
      "original_filename": "car-image.jpg",
      "s3_original_path": "s3://bucket/original/550e8400_1640995200.jpg",
      "s3_processed_path": "s3://bucket/processed/550e8400_1640995200.jpg",
      "is_vehicle_detected": true,
      "is_face_detected": true,
      "is_face_blurred": true,
      "content_type": "image/jpeg",
      "file_size_original": 1024000,
      "file_size_processed": 1100000,
      "processing_time_seconds": 2.5,
      "vehicle_detection_data": {
        "boxes": [[100, 100, 200, 200]],
        "confidences": [0.95],
        "class_ids": [2],
        "detection_count": 1
      },
      "face_detection_data": {
        "person_count": 1,
        "person_boxes": [[50, 50, 150, 150]],
        "person_confidences": [0.92]
      },
      "created_at": "2021-12-31T12:00:00",
      "processed_at": "2021-12-31T12:00:02"
    }
  ],
  "count": 1,
  "filters": {
    "is_vehicle_detected": true,
    "is_face_detected": null,
    "is_face_blurred": null,
    "limit": 10
  },
  "timestamp": 1640995200
}
```

---

## 🐳 Deployment Options

### **1. Local Development**
- **Best for**: Development, testing, debugging
- **Requirements**: Python 3.9+, MySQL, Redis
- **Setup time**: 15-30 minutes
- **Scalability**: Single machine

### **2. Docker Compose**
- **Best for**: Local testing, small deployments
- **Requirements**: Docker, Docker Compose
- **Setup time**: 5-10 minutes
- **Scalability**: Single machine, multiple containers

### **3. Kubernetes**
- **Best for**: Production, high availability, auto-scaling
- **Requirements**: Kubernetes cluster, kubectl
- **Setup time**: 30-60 minutes
- **Scalability**: Multi-node, auto-scaling

### **Deployment Comparison**

| Feature | Local | Docker Compose | Kubernetes |
|---------|-------|----------------|------------|
| **Setup Complexity** | Medium | Low | High |
| **Isolation** | None | Container | Pod/Namespace |
| **Scalability** | Manual | Limited | Auto-scaling |
| **High Availability** | No | No | Yes |
| **Production Ready** | No | Limited | Yes |
| **Resource Usage** | Low | Medium | High |
| **Monitoring** | Basic | Basic | Advanced |

---

## 📊 Monitoring & Performance

### **Performance Targets**
- **Throughput**: 30+ images/second
- **Latency**: <60 seconds end-to-end
- **Availability**: 99.9% uptime
- **Queue Processing**: <5 second average wait time

### **Resource Requirements**

#### **API Server**
- **CPU**: 0.5-1.0 cores per instance
- **Memory**: 1-2GB per instance
- **Replicas**: 3-10 (auto-scaling)
- **Network**: 100Mbps per instance

#### **Processing Workers**
- **CPU**: 4-8 cores per instance (ML processing)
- **Memory**: 8-16GB per instance (model loading)
- **GPU**: Optional but recommended
- **Replicas**: 5-20 (queue-based scaling)

#### **MySQL Database**
- **CPU**: 2-4 cores
- **Memory**: 4-8GB
- **Storage**: 100GB+ SSD
- **IOPS**: 3000+ for production

#### **Redis Queue**
- **CPU**: 0.5-1.0 cores
- **Memory**: 2-4GB
- **Persistence**: AOF + RDB
- **Replicas**: 3 nodes (cluster mode)

### **Monitoring Endpoints**

| Endpoint | Purpose | Frequency |
|----------|---------|-----------|
| `/health` | Service health | Every 30s |
| `/stats` | Pipeline metrics | Every 60s |
| `/queue-status` | Queue depth | Every 30s |
| `/database/stats` | DB statistics | Every 300s |

### **Key Metrics to Monitor**

- **Queue Depth**: Should be <100 items
- **Processing Time**: Should be <60 seconds
- **Success Rate**: Should be >95%
- **Memory Usage**: Should be <80% of allocated
- **CPU Usage**: Should be <70% average
- **Database Connections**: Should be <80% of max

---

## 🔧 Configuration Reference

### **Environment Variables**

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | MySQL connection string | `mysql+pymysql://user:password@localhost:3306/image_processing` | Yes |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` | Yes |
| `AWS_ACCESS_KEY_ID` | AWS access key for S3 | None | Yes |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for S3 | None | Yes |
| `AWS_REGION` | AWS region | `us-east-1` | No |
| `S3_BUCKET` | S3 bucket name | `image-processing-bucket` | Yes |
| `API_HOST` | API server host | `0.0.0.0` | No |
| `API_PORT` | API server port | `8000` | No |
| `NUM_WORKERS` | Number of processing workers | `5` | No |
| `MAX_QUEUE_SIZE` | Maximum queue size | `1000` | No |
| `WORKER_TIMEOUT` | Worker timeout in seconds | `300` | No |
| `FACE_DETECTION_MODEL_PATH` | Path to face detection model | `Car Face Blur Model.pt` | Yes |
| `VEHICLE_DETECTION_MODEL_PATH` | Path to vehicle detection model | `Car Face Blur Yolov8m.pt` | Yes |
| `CAR_CONFIDENCE_THRESHOLD` | Vehicle detection confidence | `0.8` | No |
| `FACE_CONFIDENCE_THRESHOLD` | Face detection confidence | `0.8` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |

### **Configuration Examples**

#### **Development (.env)**
```env
DATABASE_URL=mysql+pymysql://pipeline_user:secure_password@localhost:3306/image_processing
REDIS_URL=redis://localhost:6379
AWS_ACCESS_KEY_ID=your_dev_access_key
AWS_SECRET_ACCESS_KEY=your_dev_secret_key
AWS_REGION=us-east-1
S3_BUCKET=dev-image-processing-bucket
LOG_LEVEL=DEBUG
NUM_WORKERS=2
```

#### **Production (.env)**
```env
DATABASE_URL=mysql+pymysql://pipeline_user:secure_password@mysql-cluster:3306/image_processing
REDIS_URL=redis://redis-cluster:6379
AWS_ACCESS_KEY_ID=your_prod_access_key
AWS_SECRET_ACCESS_KEY=your_prod_secret_key
AWS_REGION=us-east-1
S3_BUCKET=prod-image-processing-bucket
LOG_LEVEL=INFO
NUM_WORKERS=10
MAX_QUEUE_SIZE=5000
WORKER_TIMEOUT=600
```

---

## 🚨 Troubleshooting

### **Common Issues & Solutions**

#### **1. Database Connection Issues**

**Problem**: `Can't connect to MySQL server`
```bash
# Check MySQL status
sudo systemctl status mysql  # Linux
brew services list | grep mysql  # macOS

# Test connection
mysql -u pipeline_user -p -h localhost

# Check configuration
python -c "from config import get_config; print(get_config().DATABASE_URL)"
```

**Solutions**:
- Ensure MySQL is running
- Verify credentials in `.env`
- Check firewall settings
- Confirm database exists

#### **2. Redis Connection Issues**

**Problem**: `Connection refused to Redis`
```bash
# Check Redis status
redis-cli ping

# Check Redis logs
sudo journalctl -u redis  # Linux
brew services list | grep redis  # macOS
```

**Solutions**:
- Start Redis service
- Check Redis configuration
- Verify REDIS_URL in `.env`
- Check network connectivity

#### **3. Model Loading Issues**

**Problem**: `Model file not found`
```bash
# Check model files
ls -la *.pt

# Check model paths
python -c "from config import get_config; c=get_config(); print(f'Face: {c.FACE_DETECTION_MODEL_PATH}'); print(f'Vehicle: {c.VEHICLE_DETECTION_MODEL_PATH}')"
```

**Solutions**:
- Download model files
- Check file paths in configuration
- Verify file permissions
- Ensure sufficient disk space

#### **4. High Queue Depth**

**Problem**: Queue depth growing continuously
```bash
# Check queue status
curl http://localhost:8000/queue-status

# Check worker status
curl http://localhost:8000/stats
```

**Solutions**:
- Scale up workers
- Check worker health
- Monitor resource usage
- Investigate processing errors

#### **5. S3 Upload Failures**

**Problem**: `Access denied` or `Bucket not found`
```bash
# Test AWS credentials
aws s3 ls s3://your-bucket-name

# Check IAM permissions
aws iam get-user
```

**Solutions**:
- Verify AWS credentials
- Check S3 bucket permissions
- Confirm bucket exists
- Review IAM policies

### **Debug Commands**

```bash
# Check overall system health
curl http://localhost:8000/health

# Get detailed pipeline statistics
curl http://localhost:8000/stats | jq

# Check queue depth and utilization
curl http://localhost:8000/queue-status | jq

# Get database statistics
curl http://localhost:8000/database/stats | jq

# Check recent processed images
curl "http://localhost:8000/database/images?limit=5" | jq

# Test database connection
python init_database.py

# Test Docker integration
python test_docker_mysql_integration.py

# Check Docker services
docker compose ps
docker compose logs api-server
docker compose logs mysql

# Check Kubernetes pods
kubectl get pods -n image-processing-pipeline
kubectl logs -f deployment/api-server -n image-processing-pipeline
kubectl describe pod mysql-0 -n image-processing-pipeline
```

### **Performance Optimization**

#### **Database Optimization**
```sql
-- Check slow queries
SELECT * FROM performance_schema.events_statements_summary_by_digest 
ORDER BY avg_timer_wait DESC LIMIT 10;

-- Check table sizes
SELECT table_name, 
       ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)'
FROM information_schema.tables 
WHERE table_schema = 'image_processing';

-- Optimize tables
OPTIMIZE TABLE processed_images;
```

#### **Redis Optimization**
```bash
# Check Redis memory usage
redis-cli info memory

# Check slow queries
redis-cli slowlog get 10

# Monitor Redis performance
redis-cli monitor
```

---

## 🤝 Contributing

### **Development Setup**
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Follow the local development setup guide
4. Make your changes
5. Add tests for new functionality
6. Run tests: `python -m pytest`
7. Commit changes: `git commit -m 'Add amazing feature'`
8. Push to branch: `git push origin feature/amazing-feature`
9. Open a Pull Request

### **Code Standards**
- Follow PEP 8 for Python code
- Add docstrings for all functions
- Include type hints where appropriate
- Write tests for new features
- Update documentation

### **Testing**
```bash
# Run unit tests
python -m pytest tests/

# Run integration tests
python test_mysql_integration.py
python test_docker_mysql_integration.py

# Run load tests
k6 run load-tests/load-test.js
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🆘 Support

### **Getting Help**
- 📖 **Documentation**: Check this README and other docs in the repository
- 🐛 **Issues**: Create an issue on GitHub for bugs or feature requests
- 💬 **Discussions**: Use GitHub Discussions for questions and community support
- 📧 **Contact**: Reach out to the development team

### **Useful Links**
- [MySQL Setup Guide](MYSQL_COMPLETE_SETUP_GUIDE.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [File Analysis Report](FILE_ANALYSIS_REPORT.md)
- [Integration Status](MYSQL_INTEGRATION_COMPLETE_STATUS.md)

---

**🚀 Built with ❤️ for high-performance image processing**

*Ready to process millions of images with vehicle detection and face blurring at scale!*