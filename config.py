"""
Configuration Management for Image Processing Pipeline
Handles environment variables and configuration settings
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
import logging

# Try to load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, will use system environment variables only
    pass

logger = logging.getLogger(__name__)

class Config:
    """Configuration class for the image processing pipeline"""
    
    def __init__(self):
        """Initialize configuration from environment variables"""
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment variables"""
        
        # Redis Configuration
        self.REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
        self.REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
        self.REDIS_DB = int(os.getenv('REDIS_DB', '0'))
        
        # Database Configuration
        self.DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///image_processing.db')
        
        # AWS Configuration
        self.AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
        self.AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
        self.S3_BUCKET = os.getenv('S3_BUCKET', 'image-processing-bucket')
        
        # API Server Configuration
        self.API_HOST = os.getenv('API_HOST', '0.0.0.0')
        self.API_PORT = int(os.getenv('API_PORT', '8000'))
        self.API_RELOAD = os.getenv('API_RELOAD', 'false').lower() == 'true'
        self.API_LOG_LEVEL = os.getenv('API_LOG_LEVEL', 'info')
        
        # Pipeline Configuration
        self.NUM_WORKERS = int(os.getenv('NUM_WORKERS', '5'))
        self.MAX_QUEUE_SIZE = int(os.getenv('MAX_QUEUE_SIZE', '1000'))
        self.WORKER_TIMEOUT = int(os.getenv('WORKER_TIMEOUT', '300'))
        
        # Model Configuration
        self.CAR_FACE_BLUR_MODEL_PATH = os.getenv('CAR_FACE_BLUR_MODEL_PATH', 'Car Face Blur Model.pt')
        self.YOLO_DETECTION_MODEL_PATH = os.getenv('YOLO_DETECTION_MODEL_PATH', 'Car Face Blur Yolov8m.pt')
        
        # Detection Thresholds
        self.CAR_CONFIDENCE_THRESHOLD = float(os.getenv('CAR_CONFIDENCE_THRESHOLD', '0.8'))
        self.FACE_CONFIDENCE_THRESHOLD = float(os.getenv('FACE_CONFIDENCE_THRESHOLD', '0.8'))
        
        # Logging Configuration
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FORMAT = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Environment Configuration
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')
        self.DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
        
        # Security
        self.SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here-change-in-production')
        
        # Performance Tuning
        self.TORCH_NUM_THREADS = int(os.getenv('TORCH_NUM_THREADS', '4'))
        self.OMP_NUM_THREADS = int(os.getenv('OMP_NUM_THREADS', '4'))
        
        # Validate required configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate required configuration values"""
        required_vars = []
        
        # Check AWS credentials in production
        if self.ENVIRONMENT == 'production':
            if not self.AWS_ACCESS_KEY_ID:
                required_vars.append('AWS_ACCESS_KEY_ID')
            if not self.AWS_SECRET_ACCESS_KEY:
                required_vars.append('AWS_SECRET_ACCESS_KEY')
        
        # Check model files exist
        if not Path(self.CAR_FACE_BLUR_MODEL_PATH).exists():
            logger.warning(f"Car Face Blur model not found at: {self.CAR_FACE_BLUR_MODEL_PATH}")
        
        if not Path(self.YOLO_DETECTION_MODEL_PATH).exists():
            logger.warning(f"YOLO detection model not found at: {self.YOLO_DETECTION_MODEL_PATH}")
        
        if required_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(required_vars)}")
    
    @property
    def aws_config(self) -> Dict[str, str]:
        """Get AWS configuration dictionary"""
        config = {
            'region_name': self.AWS_REGION,
            'bucket_name': self.S3_BUCKET
        }
        
        if self.AWS_ACCESS_KEY_ID and self.AWS_SECRET_ACCESS_KEY:
            config.update({
                'aws_access_key_id': self.AWS_ACCESS_KEY_ID,
                'aws_secret_access_key': self.AWS_SECRET_ACCESS_KEY
            })
        
        return config
    
    @property
    def pipeline_config(self) -> Dict[str, Any]:
        """Get pipeline configuration dictionary"""
        return {
            'redis_url': self.REDIS_URL,
            'database_url': self.DATABASE_URL,
            'aws_config': self.aws_config,
            'num_workers': self.NUM_WORKERS,
            'max_queue_size': self.MAX_QUEUE_SIZE,
            'worker_timeout': self.WORKER_TIMEOUT,
            'model_paths': {
                'car_face_blur': self.CAR_FACE_BLUR_MODEL_PATH,
                'yolo_detection': self.YOLO_DETECTION_MODEL_PATH
            }
        }
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.ENVIRONMENT == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.ENVIRONMENT == 'development'
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=getattr(logging, self.LOG_LEVEL.upper()),
            format=self.LOG_FORMAT
        )
        
        # Set torch thread count for performance
        if hasattr(os, 'environ'):
            os.environ['TORCH_NUM_THREADS'] = str(self.TORCH_NUM_THREADS)
            os.environ['OMP_NUM_THREADS'] = str(self.OMP_NUM_THREADS)
    
    def get_redis_url(self) -> str:
        """Get Redis URL with fallback construction"""
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    def __repr__(self) -> str:
        """String representation of config (without sensitive data)"""
        safe_config = {
            'environment': self.ENVIRONMENT,
            'debug': self.DEBUG,
            'api_host': self.API_HOST,
            'api_port': self.API_PORT,
            'num_workers': self.NUM_WORKERS,
            'redis_host': self.REDIS_HOST,
            'redis_port': self.REDIS_PORT,
            'aws_region': self.AWS_REGION,
            's3_bucket': self.S3_BUCKET,
            'database_type': self.DATABASE_URL.split('://')[0] if '://' in self.DATABASE_URL else 'unknown'
        }
        return f"Config({safe_config})"

# Global configuration instance
config = Config()

# Convenience functions for backward compatibility
def get_config() -> Config:
    """Get the global configuration instance"""
    return config

def get_pipeline_config() -> Dict[str, Any]:
    """Get pipeline configuration dictionary"""
    return config.pipeline_config

def get_aws_config() -> Dict[str, str]:
    """Get AWS configuration dictionary"""
    return config.aws_config

def is_production() -> bool:
    """Check if running in production environment"""
    return config.is_production()

def is_development() -> bool:
    """Check if running in development environment"""
    return config.is_development()

# Setup logging when module is imported
config.setup_logging()