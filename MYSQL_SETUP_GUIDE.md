# MySQL Database Setup Guide

## Overview
The Image Processing Pipeline has been migrated from PostgreSQL to MySQL. This guide provides complete setup instructions for MySQL database integration.

## 🔧 **Database Migration Changes**

### **Configuration Updates:**

#### **config.py:**
```python
# NEW MySQL default configuration
self.DATABASE_URL = os.getenv('DATABASE_URL', 'mysql+pymysql://user:password@localhost:3306/image_processing')
```

#### **.env:**
```bash
# MySQL Database Configuration
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/image_processing

# Development example:
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/image_processing

# Production example:
DATABASE_URL=mysql+pymysql://username:password@mysql-host:3306/image_processing
```

#### **requirements.txt:**
```txt
# Database dependencies (MySQL)
sqlalchemy==2.0.23
PyMySQL==1.1.0
cryptography==41.0.8  # Required for PyMySQL with SSL
alembic==1.13.1
```

#### **database_models.py:**
```python
# MySQL-compatible UUID handling
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy import String

# UUID column definition
id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
```

## 🚀 **MySQL Installation & Setup**

### **1. Install MySQL Server**

#### **macOS (using Homebrew):**
```bash
# Install MySQL
brew install mysql

# Start MySQL service
brew services start mysql

# Secure installation (optional but recommended)
mysql_secure_installation
```

#### **Ubuntu/Debian:**
```bash
# Update package index
sudo apt update

# Install MySQL server
sudo apt install mysql-server

# Start MySQL service
sudo systemctl start mysql
sudo systemctl enable mysql

# Secure installation
sudo mysql_secure_installation
```

#### **CentOS/RHEL:**
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

### **2. Create Database and User**

```sql
-- Connect to MySQL as root
mysql -u root -p

-- Create database
CREATE DATABASE image_processing CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user for the application
CREATE USER 'pipeline_user'@'localhost' IDENTIFIED BY 'secure_password_here';

-- Grant privileges
GRANT ALL PRIVILEGES ON image_processing.* TO 'pipeline_user'@'localhost';

-- For remote access (if needed)
CREATE USER 'pipeline_user'@'%' IDENTIFIED BY 'secure_password_here';
GRANT ALL PRIVILEGES ON image_processing.* TO 'pipeline_user'@'%';

-- Flush privileges
FLUSH PRIVILEGES;

-- Exit MySQL
EXIT;
```

### **3. Update Environment Configuration**

#### **Development (.env):**
```bash
# MySQL Database Configuration
DATABASE_URL=mysql+pymysql://pipeline_user:secure_password_here@localhost:3306/image_processing

# Other configurations remain the same
REDIS_URL=redis://localhost:6379
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
# ... etc
```

#### **Production Environment Variables:**
```bash
export DATABASE_URL="mysql+pymysql://pipeline_user:secure_password_here@mysql-host:3306/image_processing"
export REDIS_URL="redis://redis-host:6379"
# ... other production variables
```

## 🐳 **Docker Setup with MySQL**

### **docker-compose.yml Example:**
```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: image_processing
      MYSQL_USER: pipeline_user
      MYSQL_PASSWORD: secure_password_here
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./mysql-init:/docker-entrypoint-initdb.d
    command: --default-authentication-plugin=mysql_native_password

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=mysql+pymysql://pipeline_user:secure_password_here@mysql:3306/image_processing
      - REDIS_URL=redis://redis:6379
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
    depends_on:
      - mysql
      - redis

volumes:
  mysql_data:
```

### **MySQL Initialization Script (mysql-init/01-init.sql):**
```sql
-- Additional database setup if needed
USE image_processing;

-- Create indexes for better performance
CREATE INDEX idx_processed_images_job_id ON processed_images(job_id);
CREATE INDEX idx_processed_images_created_at ON processed_images(created_at);
CREATE INDEX idx_processed_images_flags ON processed_images(is_vehicle_detected, is_face_detected, is_face_blurred);
```

## 🔧 **Database Migration Commands**

### **Initialize Database Schema:**
```bash
# Install dependencies
pip install -r requirements.txt

# Run the application to auto-create tables
python -c "
from database_models import DatabaseManager
import asyncio

async def init_db():
    db = DatabaseManager('mysql+pymysql://pipeline_user:secure_password_here@localhost:3306/image_processing')
    await db.initialize()
    print('Database initialized successfully!')

asyncio.run(init_db())
"
```

### **Using Alembic for Migrations (Optional):**
```bash
# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Initial migration"

# Apply migration
alembic upgrade head
```

## 🧪 **Testing MySQL Connection**

### **Test Script:**
```python
#!/usr/bin/env python3
"""Test MySQL database connection"""

import asyncio
from database_models import DatabaseManager
from config import get_config

async def test_mysql_connection():
    """Test MySQL database connection and operations"""
    config = get_config()
    print(f"Testing MySQL connection: {config.DATABASE_URL}")
    
    try:
        # Initialize database manager
        db_manager = DatabaseManager(config.DATABASE_URL)
        await db_manager.initialize()
        print("✅ Database connection successful!")
        
        # Test saving a record
        await db_manager.save_processed_image(
            job_id="test-job-123",
            original_filename="test.jpg",
            s3_original_path="s3://bucket/original/test.jpg",
            s3_processed_path="s3://bucket/processed/test.jpg",
            is_vehicle_detected=True,
            is_face_detected=True,
            is_face_blurred=True,
            content_type="image/jpeg",
            file_size_original=1024,
            file_size_processed=1024,
            processing_time_seconds=1.5,
            vehicle_detection_data={"test": "data"},
            face_detection_data={"test": "data"}
        )
        print("✅ Database write test successful!")
        
        # Test reading records
        stats = await db_manager.get_processing_stats()
        print(f"✅ Database read test successful! Stats: {stats}")
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(test_mysql_connection())
```

## 🔒 **Security Considerations**

### **MySQL Security Best Practices:**

1. **Strong Passwords:**
   ```bash
   # Use strong passwords for MySQL users
   CREATE USER 'pipeline_user'@'localhost' IDENTIFIED BY 'Very$trong!P@ssw0rd123';
   ```

2. **SSL/TLS Encryption:**
   ```bash
   # Enable SSL in MySQL configuration
   DATABASE_URL=mysql+pymysql://user:pass@host:3306/db?ssl_ca=/path/to/ca.pem&ssl_cert=/path/to/cert.pem&ssl_key=/path/to/key.pem
   ```

3. **Network Security:**
   ```bash
   # Bind MySQL to specific interface
   bind-address = 127.0.0.1  # For local only
   # Or specific IP for remote access
   ```

4. **User Privileges:**
   ```sql
   -- Grant only necessary privileges
   GRANT SELECT, INSERT, UPDATE, DELETE ON image_processing.* TO 'pipeline_user'@'localhost';
   ```

## 📊 **Performance Optimization**

### **MySQL Configuration (my.cnf):**
```ini
[mysqld]
# Performance settings
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT

# Connection settings
max_connections = 200
wait_timeout = 28800

# Character set
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
```

### **Database Indexes:**
```sql
-- Add indexes for better query performance
CREATE INDEX idx_job_id ON processed_images(job_id);
CREATE INDEX idx_created_at ON processed_images(created_at);
CREATE INDEX idx_processing_flags ON processed_images(is_vehicle_detected, is_face_detected, is_face_blurred);
CREATE INDEX idx_processing_time ON processed_images(processing_time_seconds);
```

## 🚨 **Troubleshooting**

### **Common Issues:**

1. **Connection Refused:**
   ```bash
   # Check if MySQL is running
   sudo systemctl status mysql
   
   # Start MySQL if not running
   sudo systemctl start mysql
   ```

2. **Authentication Failed:**
   ```bash
   # Reset MySQL root password
   sudo mysql
   ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'new_password';
   FLUSH PRIVILEGES;
   ```

3. **SSL Certificate Issues:**
   ```bash
   # Disable SSL for testing (not recommended for production)
   DATABASE_URL=mysql+pymysql://user:pass@host:3306/db?ssl_disabled=true
   ```

4. **Character Set Issues:**
   ```sql
   -- Ensure proper character set
   ALTER DATABASE image_processing CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

## ✅ **Migration Verification**

### **Verification Checklist:**
- [ ] MySQL server installed and running
- [ ] Database and user created
- [ ] Environment variables updated
- [ ] Dependencies installed (PyMySQL)
- [ ] Database connection test passes
- [ ] Application starts without errors
- [ ] Image processing pipeline works end-to-end
- [ ] Database records are created correctly

## 🎉 **Migration Complete!**

The Image Processing Pipeline has been successfully migrated from PostgreSQL to MySQL. The system now uses:

- **MySQL 8.0+** for data storage
- **PyMySQL** as the database driver
- **SQLAlchemy** for ORM operations
- **Alembic** for database migrations

All functionality remains the same, with improved MySQL-specific optimizations and compatibility.