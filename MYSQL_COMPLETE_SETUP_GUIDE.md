# Complete MySQL Setup Guide for Image Processing Pipeline

## 📋 **Overview**

This comprehensive guide covers MySQL setup for the Image Processing Pipeline across different deployment scenarios: local development, Docker Compose, and Kubernetes.

## 🎯 **Table of Contents**

1. [Local Development Setup](#-local-development-setup)
2. [Docker Compose Integration](#-docker-compose-integration)
3. [Kubernetes Deployment](#-kubernetes-deployment)
4. [Configuration Management](#-configuration-management)
5. [Database Schema & Migration](#-database-schema--migration)
6. [Monitoring & Maintenance](#-monitoring--maintenance)
7. [Troubleshooting](#-troubleshooting)

---

## 🖥️ **Local Development Setup**

### **1. Install MySQL Server**

#### **macOS (Homebrew)**
```bash
# Install MySQL
brew install mysql

# Start MySQL service
brew services start mysql

# Secure installation (optional but recommended)
mysql_secure_installation
```

#### **Ubuntu/Debian**
```bash
# Update package index
sudo apt update

# Install MySQL Server
sudo apt install mysql-server

# Start MySQL service
sudo systemctl start mysql
sudo systemctl enable mysql

# Secure installation
sudo mysql_secure_installation
```

#### **CentOS/RHEL**
```bash
# Install MySQL repository
sudo yum install mysql-server

# Start MySQL service
sudo systemctl start mysqld
sudo systemctl enable mysqld

# Get temporary root password
sudo grep 'temporary password' /var/log/mysqld.log

# Secure installation
mysql_secure_installation
```

### **2. Database Setup**

```bash
# Connect to MySQL as root
mysql -u root -p

# Create database and user
CREATE DATABASE image_processing CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'pipeline_user'@'localhost' IDENTIFIED BY 'secure_password_123';
GRANT ALL PRIVILEGES ON image_processing.* TO 'pipeline_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### **3. Python Environment Setup**

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database schema
python init_database.py

# Test the integration
python test_mysql_integration.py
```

### **4. Environment Configuration**

Update your `.env` file:
```env
# Database Configuration
DATABASE_URL=mysql+pymysql://pipeline_user:secure_password_123@localhost:3306/image_processing

# Redis Configuration
REDIS_URL=redis://localhost:6379

# AWS Configuration (for S3 storage)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
S3_BUCKET=your-image-processing-bucket
```

---

## 🐳 **Docker Compose Integration**

### **1. Updated Docker Compose Configuration**

The Docker Compose setup includes MySQL with proper networking and persistence:

```yaml
version: '3.8'

services:
  # MySQL Database
  mysql:
    image: mysql:8.0
    container_name: image-processing-mysql
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: root_password_123
      MYSQL_DATABASE: image_processing
      MYSQL_USER: pipeline_user
      MYSQL_PASSWORD: secure_password_123
      MYSQL_CHARACTER_SET_SERVER: utf8mb4
      MYSQL_COLLATION_SERVER: utf8mb4_unicode_ci
    volumes:
      - mysql_data:/var/lib/mysql
      - ./mysql-init:/docker-entrypoint-initdb.d
    networks:
      - pipeline-network
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "pipeline_user", "-psecure_password_123"]
      interval: 30s
      timeout: 10s
      retries: 5
    restart: unless-stopped

  # Redis for Queue Management
  redis:
    image: redis:7-alpine
    container_name: image-processing-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - pipeline-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # API Server
  api-server:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: image-processing-api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=mysql+pymysql://pipeline_user:secure_password_123@mysql:3306/image_processing
      - REDIS_URL=redis://redis:6379
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - AWS_REGION=${AWS_REGION:-us-east-1}
      - S3_BUCKET=${S3_BUCKET:-image-processing-bucket}
      - LOG_LEVEL=INFO
    volumes:
      - ./models:/app/models
      - ./logs:/app/logs
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - pipeline-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  mysql_data:
    driver: local
  redis_data:
    driver: local

networks:
  pipeline-network:
    driver: bridge
```

### **2. MySQL Initialization Scripts**

Create `mysql-init/01-init.sql`:
```sql
-- Additional database setup if needed
USE image_processing;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_processed_images_job_id ON processed_images(job_id);
CREATE INDEX IF NOT EXISTS idx_processed_images_created_at ON processed_images(created_at);
CREATE INDEX IF NOT EXISTS idx_processed_images_vehicle_detected ON processed_images(is_vehicle_detected);
CREATE INDEX IF NOT EXISTS idx_processed_images_face_detected ON processed_images(is_face_detected);
CREATE INDEX IF NOT EXISTS idx_processed_images_face_blurred ON processed_images(is_face_blurred);

-- Create a view for statistics
CREATE VIEW IF NOT EXISTS processing_statistics AS
SELECT 
    COUNT(*) as total_images,
    SUM(is_vehicle_detected) as vehicles_detected,
    SUM(is_face_detected) as faces_detected,
    SUM(is_face_blurred) as faces_blurred,
    ROUND(AVG(processing_time_seconds), 2) as avg_processing_time,
    DATE(created_at) as processing_date
FROM processed_images
GROUP BY DATE(created_at)
ORDER BY processing_date DESC;
```

### **3. Docker Compose Commands**

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f api-server
docker-compose logs -f mysql

# Initialize database (if needed)
docker-compose exec api-server python init_database.py

# Test the integration
docker-compose exec api-server python test_mysql_integration.py

# Stop all services
docker-compose down

# Stop and remove volumes (careful - this deletes data!)
docker-compose down -v
```

---

## ☸️ **Kubernetes Deployment**

### **1. MySQL StatefulSet Configuration**

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mysql
  namespace: image-processing-pipeline
spec:
  serviceName: mysql
  replicas: 1
  selector:
    matchLabels:
      app: mysql
  template:
    metadata:
      labels:
        app: mysql
    spec:
      containers:
      - name: mysql
        image: mysql:8.0
        ports:
        - containerPort: 3306
          name: mysql
        env:
        - name: MYSQL_ROOT_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: root-password
        - name: MYSQL_DATABASE
          value: image_processing
        - name: MYSQL_USER
          value: pipeline_user
        - name: MYSQL_PASSWORD
          valueFrom:
            secretKeyRef:
              name: mysql-secret
              key: user-password
        - name: MYSQL_CHARACTER_SET_SERVER
          value: utf8mb4
        - name: MYSQL_COLLATION_SERVER
          value: utf8mb4_unicode_ci
        volumeMounts:
        - name: mysql-data
          mountPath: /var/lib/mysql
        - name: mysql-config
          mountPath: /etc/mysql/conf.d
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          exec:
            command:
            - mysqladmin
            - ping
            - -h
            - localhost
            - -u
            - pipeline_user
            - -psecure_password_123
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - mysqladmin
            - ping
            - -h
            - localhost
            - -u
            - pipeline_user
            - -psecure_password_123
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: mysql-config
        configMap:
          name: mysql-config
  volumeClaimTemplates:
  - metadata:
      name: mysql-data
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi
      storageClassName: fast-ssd
```

### **2. Kubernetes Deployment Commands**

```bash
# Create namespace
kubectl create namespace image-processing-pipeline

# Apply MySQL configuration
kubectl apply -f mysql-statefulset.yaml

# Wait for MySQL to be ready
kubectl wait --for=condition=ready pod -l app=mysql -n image-processing-pipeline --timeout=300s

# Apply application deployments
kubectl apply -f kubernetes_deployment.yaml

# Check pod status
kubectl get pods -n image-processing-pipeline

# Initialize database
kubectl exec -it mysql-0 -n image-processing-pipeline -- mysql -u pipeline_user -psecure_password_123 image_processing < init.sql

# Check logs
kubectl logs -f deployment/api-server -n image-processing-pipeline
```

---

## ⚙️ **Configuration Management**

### **1. Environment Variables**

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | MySQL connection string | `mysql+pymysql://user:pass@host:3306/db` |
| `MYSQL_HOST` | MySQL server hostname | `localhost` or `mysql` |
| `MYSQL_PORT` | MySQL server port | `3306` |
| `MYSQL_USER` | Database username | `pipeline_user` |
| `MYSQL_PASSWORD` | Database password | `secure_password_123` |
| `MYSQL_DATABASE` | Database name | `image_processing` |

### **2. Connection Pool Settings**

```python
# In config.py
DATABASE_POOL_SIZE = int(os.getenv('DATABASE_POOL_SIZE', '20'))
DATABASE_MAX_OVERFLOW = int(os.getenv('DATABASE_MAX_OVERFLOW', '30'))
DATABASE_POOL_TIMEOUT = int(os.getenv('DATABASE_POOL_TIMEOUT', '30'))
DATABASE_POOL_RECYCLE = int(os.getenv('DATABASE_POOL_RECYCLE', '3600'))
```

---

## 🗄️ **Database Schema & Migration**

### **1. Current Schema**

```sql
CREATE TABLE processed_images (
    id CHAR(36) PRIMARY KEY,
    job_id VARCHAR(255) UNIQUE NOT NULL,
    original_filename VARCHAR(500) NOT NULL,
    s3_original_path VARCHAR(1000),
    s3_processed_path VARCHAR(1000),
    is_vehicle_detected BOOLEAN NOT NULL DEFAULT FALSE,
    is_face_detected BOOLEAN NOT NULL DEFAULT FALSE,
    is_face_blurred BOOLEAN NOT NULL DEFAULT FALSE,
    content_type VARCHAR(100),
    file_size_original INT,
    file_size_processed INT,
    processing_time_seconds FLOAT,
    vehicle_detection_data TEXT,
    face_detection_data TEXT,
    created_at DATETIME NOT NULL,
    processed_at DATETIME,
    INDEX idx_job_id (job_id),
    INDEX idx_created_at (created_at),
    INDEX idx_vehicle_detected (is_vehicle_detected),
    INDEX idx_face_detected (is_face_detected),
    INDEX idx_face_blurred (is_face_blurred)
);
```

### **2. Backup and Restore**

```bash
# Backup database
mysqldump -u pipeline_user -p image_processing > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore database
mysql -u pipeline_user -p image_processing < backup_20240101_120000.sql

# Docker backup
docker exec image-processing-mysql mysqldump -u pipeline_user -psecure_password_123 image_processing > backup.sql

# Kubernetes backup
kubectl exec mysql-0 -n image-processing-pipeline -- mysqldump -u pipeline_user -psecure_password_123 image_processing > backup.sql
```

---

## 📊 **Monitoring & Maintenance**

### **1. Performance Monitoring**

```sql
-- Check table sizes
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size (MB)'
FROM information_schema.tables 
WHERE table_schema = 'image_processing';

-- Check query performance
SELECT * FROM performance_schema.events_statements_summary_by_digest 
ORDER BY avg_timer_wait DESC LIMIT 10;
```

### **2. Health Checks**

```bash
# Check MySQL status
mysqladmin -u pipeline_user -p status

# Check connections
mysql -u pipeline_user -p -e "SHOW PROCESSLIST;"

# Check database size
mysql -u pipeline_user -p -e "SELECT table_schema AS 'Database', ROUND(SUM(data_length + index_length) / 1024 / 1024, 1) AS 'DB Size in MB' FROM information_schema.tables WHERE table_schema='image_processing';"
```

---

## 🔧 **Troubleshooting**

### **1. Common Issues**

#### **Connection Refused**
```bash
# Check if MySQL is running
brew services list | grep mysql  # macOS
systemctl status mysql          # Linux

# Check port availability
netstat -tlnp | grep 3306
```

#### **Authentication Issues**
```sql
-- Reset user password
ALTER USER 'pipeline_user'@'localhost' IDENTIFIED BY 'new_password';
FLUSH PRIVILEGES;
```

#### **Performance Issues**
```sql
-- Check slow queries
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 2;
```

### **2. Docker Troubleshooting**

```bash
# Check container logs
docker logs image-processing-mysql

# Connect to MySQL container
docker exec -it image-processing-mysql mysql -u pipeline_user -p

# Check container health
docker inspect image-processing-mysql | grep Health
```

### **3. Kubernetes Troubleshooting**

```bash
# Check pod status
kubectl describe pod mysql-0 -n image-processing-pipeline

# Check logs
kubectl logs mysql-0 -n image-processing-pipeline

# Connect to MySQL pod
kubectl exec -it mysql-0 -n image-processing-pipeline -- mysql -u pipeline_user -p
```

---

## 🎯 **Quick Start Commands**

### **Local Development**
```bash
# 1. Install and start MySQL
brew install mysql && brew services start mysql

# 2. Create database
mysql -u root -p -e "CREATE DATABASE image_processing; CREATE USER 'pipeline_user'@'localhost' IDENTIFIED BY 'secure_password_123'; GRANT ALL PRIVILEGES ON image_processing.* TO 'pipeline_user'@'localhost'; FLUSH PRIVILEGES;"

# 3. Initialize schema
python init_database.py

# 4. Start API server
python api_server.py
```

### **Docker Compose**
```bash
# 1. Start all services
docker-compose up -d

# 2. Wait for services to be ready
docker-compose logs -f mysql

# 3. Test the API
curl http://localhost:8000/health
```

### **Kubernetes**
```bash
# 1. Deploy MySQL
kubectl apply -f mysql-k8s.yaml

# 2. Deploy application
kubectl apply -f kubernetes_deployment.yaml

# 3. Check status
kubectl get pods -n image-processing-pipeline
```

---

## ✅ **Verification Checklist**

- [ ] MySQL server installed and running
- [ ] Database and user created
- [ ] Python dependencies installed
- [ ] Database schema initialized
- [ ] Connection test successful
- [ ] API server starts without errors
- [ ] Workers can connect to database
- [ ] Health checks passing
- [ ] Monitoring configured
- [ ] Backup strategy in place

---

## 🚀 **Status: Ready for Production**

This MySQL setup guide provides comprehensive coverage for all deployment scenarios. The database integration is production-ready with proper security, monitoring, and maintenance procedures.