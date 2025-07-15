# Image Processing Pipeline with Car Face Blur Models

A high-performance, scalable image processing pipeline that applies two ML models (Car Face Blur and YOLO Detection) to images with 30+ images/sec throughput.

## 🏗️ Architecture Overview

### Multi-Stage Pipeline Design

```
Image Upload → API Server → Redis Queue → Processing Workers → S3 Storage
     ↓              ↓            ↓              ↓              ↓
   FastAPI    Job Creation   Job Queue    ML Models    Results + Metadata
```

### Components

1. **API Server** (FastAPI)
   - Handles image uploads
   - Creates processing jobs
   - Provides status endpoints
   - Scales horizontally

2. **Redis Queue**
   - Decouples ingestion from processing
   - Handles traffic spikes
   - Provides retry mechanisms
   - Enables horizontal scaling

3. **Processing Workers**
   - Load and run ML models
   - Process images asynchronously
   - Upload results to S3
   - Auto-scale based on queue depth

4. **S3 Storage**
   - Stores original and processed images
   - Stores metadata and results
   - Handles large file uploads

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Docker and Docker Compose
- Redis server
- AWS S3 bucket
- Kubernetes cluster (for production)

### Local Development

1. **Clone and setup:**
```bash
git clone <repository>
cd image-processing-pipeline
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set environment variables:**
```bash
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_REGION="us-east-1"
export S3_BUCKET="your-bucket-name"
export REDIS_URL="redis://localhost:6379"
```

4. **Start with Docker Compose:**
```bash
docker-compose up -d
```

5. **Test the API:**
```bash
curl -X POST "http://localhost:8000/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test-image.jpg"
```

### Kubernetes Deployment

1. **Build and push Docker images:**
```bash
docker build -t image-processing-api:latest .
docker build -t image-processing-worker:latest .
docker push your-registry/image-processing-api:latest
docker push your-registry/image-processing-worker:latest
```

2. **Update Kubernetes config:**
```bash
# Update image names in kubernetes_deployment.yaml
# Set AWS credentials as Kubernetes secrets
kubectl create secret generic aws-credentials \
  --from-literal=aws-access-key-id=your_key \
  --from-literal=aws-secret-access-key=your_secret
```

3. **Deploy to Kubernetes:**
```bash
kubectl apply -f kubernetes_deployment.yaml
```

## 📊 Performance Characteristics

### Target Metrics
- **Throughput**: 30+ images/second
- **Latency**: <60 seconds end-to-end
- **Availability**: 99.9% uptime
- **Scalability**: Handle traffic spikes up to 100 images/sec

### Resource Requirements

#### API Server
- **CPU**: 0.5-1.0 cores per pod
- **Memory**: 1-2GB per pod
- **Replicas**: 3-10 (auto-scaling)

#### Processing Workers
- **CPU**: 4-8 cores per pod
- **Memory**: 8-16GB per pod
- **Replicas**: 5-20 (queue-based scaling)
- **GPU**: Optional but recommended for ML models

#### Redis Cluster
- **CPU**: 0.5-1.0 cores per node
- **Memory**: 2-4GB per node
- **Replicas**: 3 nodes (StatefulSet)

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `AWS_ACCESS_KEY_ID` | AWS access key | Required |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | Required |
| `AWS_REGION` | AWS region | `us-east-1` |
| `S3_BUCKET` | S3 bucket name | `image-processing-bucket` |
| `WORKER_ID` | Worker identifier | Auto-generated |
| `LOG_LEVEL` | Logging level | `INFO` |

### Pipeline Configuration

```json
{
  "redis_url": "redis://redis-cluster:6379",
  "aws_config": {
    "aws_access_key_id": "your_key",
    "aws_secret_access_key": "your_secret",
    "region_name": "us-east-1",
    "bucket_name": "image-processing-bucket"
  },
  "num_workers": 5,
  "max_queue_size": 1000
}
```

## 📈 Monitoring and Observability

### Metrics

The pipeline exposes the following metrics:

- **Throughput**: Images processed per second
- **Latency**: End-to-end processing time
- **Queue Depth**: Processing backlog
- **Resource Utilization**: CPU, memory usage
- **Success Rate**: Percentage of successful processing
- **Model Performance**: Accuracy and confidence scores

### Monitoring Stack

- **Prometheus**: Metrics collection
- **Grafana**: Dashboards and visualization
- **AlertManager**: Alerting and notifications

### Key Alerts

- High queue depth (>800 items)
- Processing failures (>10 failures/2min)
- Low throughput (<20 jobs/minute)
- Resource exhaustion

## 🔄 API Endpoints

### Upload Image
```http
POST /upload
Content-Type: multipart/form-data

file: <image_file>
```

**Response:**
```json
{
  "job_id": "uuid",
  "filename": "image.jpg",
  "file_size": 1024000,
  "status": "submitted",
  "message": "Image submitted for processing"
}
```

### Check Job Status
```http
GET /status/{job_id}
```

**Response:**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "updated_at": 1640995200,
  "results": {
    "original_image_path": "s3://bucket/original/uuid_123.jpg",
    "processed_image_path": "s3://bucket/processed/uuid_123.jpg",
    "processing_time": 2.5,
    "blur_metadata": {...},
    "detection_metadata": {...}
  }
}
```

### Batch Upload
```http
POST /batch-upload
Content-Type: multipart/form-data

files: [<image_file1>, <image_file2>, ...]
```

### Pipeline Statistics
```http
GET /stats
```

### Health Check
```http
GET /health
```

## 🧪 Testing

### Load Testing

Use the included K6 load test:

```bash
# Run load test
docker-compose run k6 k6 run /scripts/load-test.js

# Or run locally
k6 run load-tests/load-test.js
```

### Unit Testing

```bash
pytest tests/ -v
```

### Integration Testing

```bash
# Start test environment
docker-compose -f docker-compose.test.yml up -d

# Run integration tests
pytest tests/integration/ -v
```

## 🔒 Security

### Network Security
- Kubernetes Network Policies
- Service Mesh (Istio)
- TLS encryption for all communications

### Access Control
- AWS IAM roles and policies
- Kubernetes RBAC
- API authentication (JWT tokens)

### Data Protection
- Encrypted S3 storage
- Secure credential management
- Audit logging

## 🚨 Troubleshooting

### Common Issues

1. **Models not loading**
   - Check model file paths
   - Verify CUDA/GPU availability
   - Check memory allocation

2. **High queue depth**
   - Scale up processing workers
   - Check worker health
   - Monitor resource usage

3. **S3 upload failures**
   - Verify AWS credentials
   - Check network connectivity
   - Validate bucket permissions

4. **Redis connection issues**
   - Check Redis server status
   - Verify connection string
   - Monitor Redis memory usage

### Debug Commands

```bash
# Check pipeline status
curl http://localhost:8000/stats

# Check queue depth
curl http://localhost:8000/queue-status

# Check worker logs
kubectl logs -f deployment/processing-workers

# Check Redis
redis-cli -h localhost -p 6379 llen image_processing_queue
```

## 📚 Development

### Project Structure

```
image-processing-pipeline/
├── pipeline_architecture.py  # Core pipeline logic
├── api_server.py            # FastAPI server
├── worker.py                # Standalone worker
├── kubernetes_deployment.yaml # K8s deployment
├── docker-compose.yml       # Local development
├── Dockerfile              # Container image
├── requirements.txt         # Python dependencies
├── tests/                  # Test suite
├── monitoring/             # Prometheus/Grafana configs
├── load-tests/            # K6 load tests
└── docs/                  # Documentation
```

### Adding New Models

1. **Update ModelManager class:**
```python
async def load_new_model(self):
    self.new_model = torch.load('new_model.pt')
    self.new_model.eval()

async def process_with_new_model(self, image_data):
    # Add processing logic
    return processed_image, results
```

2. **Update worker processing:**
```python
# Add new model processing to worker.py
processed_image, new_results = await self.model_manager.process_with_new_model(image_data)
```

3. **Update API responses:**
```python
# Include new model results in API response
"new_model_results": new_results
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the monitoring dashboards
- Contact the development team

---

**Built with ❤️ for high-performance image processing** 