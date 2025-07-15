"""
Image Processing Pipeline Architecture
Car Face Blur Processing Pipeline

This module implements a comprehensive image processing pipeline that:
1. Ingests images at 30 images/sec
2. Processes images through two ML models (Car Face Blur)
3. Stores results in S3 with metadata
4. Maintains high throughput with async processing
"""

import asyncio
import aiohttp
import aioboto3
from botocore.config import Config
import redis.asyncio as redis
import json
import time
import uuid
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import cv2
import numpy as np
from PIL import Image
import io
import base64
from pathlib import Path
import torch
import torch.nn as nn
from ultralytics import YOLO
import traceback
from concurrent.futures import ThreadPoolExecutor
import threading
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.panel import Panel
import face_recognition
from database_models import DatabaseManager, ProcessedImage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()

class ProcessingStatus(Enum):
    """Processing status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"

@dataclass
class ImageJob:
    """Image processing job data structure"""
    job_id: str
    image_data: bytes
    original_filename: str
    content_type: str
    metadata: Dict[str, Any]
    status: ProcessingStatus
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error_message: Optional[str] = None
    processing_results: Optional[Dict[str, Any]] = None

@dataclass
class ProcessingResult:
    """Processing result data structure"""
    job_id: str
    original_image_path: str
    processed_image_path: str
    blur_metadata: Dict[str, Any]
    detection_metadata: Dict[str, Any]
    processing_time: float
    model_versions: Dict[str, str]
    confidence_scores: Dict[str, float]

class ModelManager:
    """Manages loading and running of ML models"""
    
    def __init__(self):
        self.car_face_blur_model = None
        self.yolo_detection_model = None
        self.models_loaded = False
        self.load_lock = threading.Lock()
        
    async def load_models(self):
        """Load both ML models asynchronously"""
        with self.load_lock:
            if self.models_loaded:
                return
                
            console.print("[cyan]Loading ML models...[/cyan]")
            
            try:
                # Load Car Face Blur Model
                console.print("[yellow]Loading Car Face Blur Model...[/yellow]")
                self.car_face_blur_model = torch.load('Car Face Blur Model.pt', map_location='cpu')
                self.car_face_blur_model.eval()
                
                # Load YOLO Detection Model
                console.print("[yellow]Loading YOLO Detection Model...[/yellow]")
                self.yolo_detection_model = YOLO('Car Face Blur Yolov8m.pt')
                
                self.models_loaded = True
                console.print("[green]✅ Models loaded successfully![/green]")
                
            except Exception as e:
                console.print(f"[red]Error loading models: {str(e)}[/red]")
                raise
    
    async def detect_faces(self, image_array: np.ndarray) -> Dict[str, Any]:
        """Detect faces in image using face_recognition library"""
        try:
            # Convert RGB to BGR for face_recognition
            rgb_image = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
            
            # Find face locations
            face_locations = face_recognition.face_locations(rgb_image)
            
            return {
                'face_count': len(face_locations),
                'face_locations': face_locations,
                'faces_detected': len(face_locations) > 0
            }
        except Exception as e:
            logger.error(f"Error in face detection: {str(e)}")
            return {
                'face_count': 0,
                'face_locations': [],
                'faces_detected': False,
                'error': str(e)
            }

    async def process_image(self, image_data: bytes) -> Tuple[bytes, Dict[str, Any]]:
        """Process image through detection and blur models"""
        if not self.models_loaded:
            await self.load_models()
        
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_data))
        image_array = np.array(image)
        
        results = {
            'vehicle_detection': {},
            'face_detection': {},
            'car_face_blur': {},
            'processing_metadata': {},
            'flags': {
                'is_vehicle_detected': False,
                'is_face_detected': False,
                'is_face_blurred': False
            }
        }
        
        try:
            # Step 1: YOLO Vehicle Detection
            yolo_results = self.yolo_detection_model(image_array)
            detection_data = yolo_results[0] if yolo_results else None
            
            vehicle_detected = False
            if detection_data and detection_data.boxes is not None:
                # COCO class IDs for vehicles: 2=car, 5=bus, 7=truck, 3=motorcycle
                vehicle_class_ids = [2, 3, 5, 7]
                detected_classes = detection_data.boxes.cls.cpu().numpy().tolist()
                vehicle_detected = any(int(cls) in vehicle_class_ids for cls in detected_classes)
                
                results['vehicle_detection'] = {
                    'boxes': detection_data.boxes.xyxy.cpu().numpy().tolist(),
                    'confidences': detection_data.boxes.conf.cpu().numpy().tolist(),
                    'class_ids': detected_classes,
                    'detection_count': len(detection_data.boxes),
                    'vehicle_detected': vehicle_detected
                }
            
            results['flags']['is_vehicle_detected'] = vehicle_detected
            
            # Step 2: Face Detection
            face_results = await self.detect_faces(image_array)
            results['face_detection'] = face_results
            results['flags']['is_face_detected'] = face_results['faces_detected']
            
            # Step 3: Apply Face Blur (only if vehicle and face detected)
            processed_image = image_array.copy()
            face_blur_applied = False
            
            if vehicle_detected and face_results['faces_detected']:
                # Convert to tensor format for blur model
                image_tensor = torch.from_numpy(image_array).float().permute(2, 0, 1).unsqueeze(0) / 255.0
                
                with torch.no_grad():
                    blur_output = self.car_face_blur_model(image_tensor)
                    
                # Convert output back to image format
                processed_image = (blur_output.squeeze(0).permute(1, 2, 0) * 255).cpu().numpy().astype(np.uint8)
                face_blur_applied = True
            
            results['car_face_blur'] = {
                'processing_applied': face_blur_applied,
                'input_shape': image_array.shape,
                'output_shape': processed_image.shape,
                'reason': 'Vehicle and face detected' if face_blur_applied else 'No vehicle or no face detected'
            }
            
            results['flags']['is_face_blurred'] = face_blur_applied
            
            # Convert processed image back to bytes
            processed_pil = Image.fromarray(processed_image)
            img_byte_arr = io.BytesIO()
            processed_pil.save(img_byte_arr, format='JPEG', quality=95)
            processed_bytes = img_byte_arr.getvalue()
            
            results['processing_metadata'] = {
                'original_size': len(image_data),
                'processed_size': len(processed_bytes),
                'compression_ratio': len(processed_bytes) / len(image_data) if len(image_data) > 0 else 0
            }
            
            return processed_bytes, results
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise

class RedisQueueManager:
    """Manages Redis-based job queue"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
        self.queue_name = "image_processing_queue"
        self.processing_queue = "processing_queue"
        self.results_queue = "results_queue"
        
    async def connect(self):
        """Connect to Redis"""
        self.redis_client = redis.from_url(self.redis_url)
        await self.redis_client.ping()
        console.print("[green]✅ Connected to Redis[/green]")
    
    async def enqueue_job(self, job: ImageJob) -> str:
        """Add job to processing queue"""
        job_data = asdict(job)
        job_data['status'] = job.status.value
        
        await self.redis_client.lpush(self.queue_name, json.dumps(job_data))
        return job.job_id
    
    async def dequeue_job(self) -> Optional[ImageJob]:
        """Get next job from queue"""
        job_data = await self.redis_client.brpop(self.queue_name, timeout=1)
        
        if job_data:
            job_dict = json.loads(job_data[1])
            job_dict['status'] = ProcessingStatus(job_dict['status'])
            return ImageJob(**job_dict)
        
        return None
    
    async def update_job_status(self, job_id: str, status: ProcessingStatus, results: Optional[Dict] = None):
        """Update job status and results"""
        status_data = {
            'job_id': job_id,
            'status': status.value,
            'updated_at': time.time(),
            'results': results
        }
        await self.redis_client.hset(f"job_status:{job_id}", mapping=status_data)
    
    async def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get job status"""
        return await self.redis_client.hgetall(f"job_status:{job_id}")

class S3StorageManager:
    """Manages S3 storage operations"""
    
    def __init__(self, aws_config: Dict[str, str]):
        self.aws_config = aws_config
        self.bucket_name = aws_config.get('bucket_name', 'image-processing-bucket')
        self.session = None
        
    async def connect(self):
        """Initialize S3 session"""
        self.session = aioboto3.Session()
        console.print("[green]✅ S3 session initialized[/green]")
    
    async def upload_image(self, image_data: bytes, key: str, content_type: str = 'image/jpeg') -> str:
        """Upload image to S3"""
        async with self.session.client('s3', **self.aws_config) as s3_client:
            await s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=image_data,
                ContentType=content_type
            )
            return f"s3://{self.bucket_name}/{key}"
    
    async def upload_metadata(self, metadata: Dict, key: str) -> str:
        """Upload metadata JSON to S3"""
        async with self.session.client('s3', **self.aws_config) as s3_client:
            await s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json.dumps(metadata, indent=2),
                ContentType='application/json'
            )
            return f"s3://{self.bucket_name}/{key}"

class ImageProcessingWorker:
    """Worker for processing images through ML models"""
    
    def __init__(self, worker_id: str, model_manager: ModelManager, 
                 queue_manager: RedisQueueManager, storage_manager: S3StorageManager,
                 database_manager: DatabaseManager):
        self.worker_id = worker_id
        self.model_manager = model_manager
        self.queue_manager = queue_manager
        self.storage_manager = storage_manager
        self.database_manager = database_manager
        self.running = False
        self.stats = {
            'processed': 0,
            'failed': 0,
            'total_time': 0
        }
    
    async def start(self):
        """Start the worker"""
        self.running = True
        console.print(f"[cyan]🚀 Worker {self.worker_id} started[/cyan]")
        
        while self.running:
            try:
                # Get job from queue
                job = await self.queue_manager.dequeue_job()
                
                if job:
                    await self.process_job(job)
                else:
                    await asyncio.sleep(0.1)  # Small delay when no jobs
                    
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {str(e)}")
                await asyncio.sleep(1)
    
    async def process_job(self, job: ImageJob):
        """Process a single job"""
        start_time = time.time()
        
        try:
            # Update status to processing
            await self.queue_manager.update_job_status(job.job_id, ProcessingStatus.PROCESSING)
            
            # Process image through models
            processed_image, results = await self.model_manager.process_image(job.image_data)
            
            # Generate S3 keys
            timestamp = int(time.time())
            original_key = f"original/{job.job_id}_{timestamp}.jpg"
            processed_key = f"processed/{job.job_id}_{timestamp}.jpg"
            metadata_key = f"metadata/{job.job_id}_{timestamp}.json"
            
            # Upload to S3
            original_url = await self.storage_manager.upload_image(
                job.image_data, original_key, job.content_type
            )
            
            processed_url = await self.storage_manager.upload_image(
                processed_image, processed_key, 'image/jpeg'
            )
            
            # Prepare metadata
            processing_time = time.time() - start_time
            processing_result = ProcessingResult(
                job_id=job.job_id,
                original_image_path=original_url,
                processed_image_path=processed_url,
                blur_metadata=results['car_face_blur'],
                detection_metadata=results.get('vehicle_detection', {}),
                processing_time=processing_time,
                model_versions={
                    'car_face_blur': '1.0',
                    'yolo_detection': '8m'
                },
                confidence_scores={
                    'avg_detection_confidence': np.mean(results.get('vehicle_detection', {}).get('confidences', [0])) if results.get('vehicle_detection', {}).get('confidences') else 0
                }
            )
            
            # Upload metadata
            metadata_url = await self.storage_manager.upload_metadata(
                asdict(processing_result), metadata_key
            )
            
            # Save to database with flags
            await self.database_manager.save_processed_image(
                job_id=job.job_id,
                original_filename=job.original_filename,
                s3_original_path=original_url,
                s3_processed_path=processed_url,
                is_vehicle_detected=results['flags']['is_vehicle_detected'],
                is_face_detected=results['flags']['is_face_detected'],
                is_face_blurred=results['flags']['is_face_blurred'],
                content_type=job.content_type,
                file_size_original=len(job.image_data),
                file_size_processed=len(processed_image),
                processing_time_seconds=processing_time,
                vehicle_detection_data=results.get('vehicle_detection', {}),
                face_detection_data=results.get('face_detection', {})
            )
            
            # Update job status
            await self.queue_manager.update_job_status(
                job.job_id, ProcessingStatus.COMPLETED, asdict(processing_result)
            )
            
            # Update stats
            self.stats['processed'] += 1
            self.stats['total_time'] += processing_time
            
            console.print(f"[green]✅ Worker {self.worker_id} processed job {job.job_id} - Vehicle: {results['flags']['is_vehicle_detected']}, Face: {results['flags']['is_face_detected']}, Blurred: {results['flags']['is_face_blurred']}[/green]")
            
        except Exception as e:
            logger.error(f"Error processing job {job.job_id}: {str(e)}")
            await self.queue_manager.update_job_status(
                job.job_id, ProcessingStatus.FAILED, {'error': str(e)}
            )
            self.stats['failed'] += 1
    
    async def stop(self):
        """Stop the worker"""
        self.running = False
        console.print(f"[yellow]🛑 Worker {self.worker_id} stopped[/yellow]")

class ImageProcessingPipeline:
    """Main pipeline orchestrator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.model_manager = ModelManager()
        self.queue_manager = RedisQueueManager(config.get('redis_url', 'redis://localhost:6379'))
        self.storage_manager = S3StorageManager(config.get('aws_config', {}))
        self.database_manager = DatabaseManager(config.get('database_url', 'sqlite:///image_processing.db'))
        self.workers: List[ImageProcessingWorker] = []
        self.running = False
        
    async def initialize(self):
        """Initialize all components"""
        console.print("[bold cyan]🚀 Initializing Image Processing Pipeline...[/bold cyan]")
        
        # Connect to Redis
        await self.queue_manager.connect()
        
        # Connect to S3
        await self.storage_manager.connect()
        
        # Initialize database
        await self.database_manager.initialize()
        
        # Load models
        await self.model_manager.load_models()
        
        console.print("[green]✅ Pipeline initialized successfully![/green]")
    
    async def start_workers(self, num_workers: int = 5):
        """Start processing workers"""
        console.print(f"[cyan]Starting {num_workers} workers...[/cyan]")
        
        for i in range(num_workers):
            worker = ImageProcessingWorker(
                f"worker-{i+1}",
                self.model_manager,
                self.queue_manager,
                self.storage_manager,
                self.database_manager
            )
            self.workers.append(worker)
            
            # Start worker in background
            asyncio.create_task(worker.start())
        
        self.running = True
        console.print(f"[green]✅ {num_workers} workers started[/green]")
    
    async def submit_job(self, image_data: bytes, filename: str, content_type: str = 'image/jpeg') -> str:
        """Submit a new image for processing"""
        job = ImageJob(
            job_id=str(uuid.uuid4()),
            image_data=image_data,
            original_filename=filename,
            content_type=content_type,
            metadata={'submitted_at': time.time()},
            status=ProcessingStatus.PENDING,
            created_at=time.time()
        )
        
        job_id = await self.queue_manager.enqueue_job(job)
        console.print(f"[cyan]📤 Submitted job {job_id} for {filename}[/cyan]")
        return job_id
    
    async def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get status of a job"""
        return await self.queue_manager.get_job_status(job_id)
    
    async def get_pipeline_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics"""
        total_processed = sum(w.stats['processed'] for w in self.workers)
        total_failed = sum(w.stats['failed'] for w in self.workers)
        total_time = sum(w.stats['total_time'] for w in self.workers)
        
        avg_processing_time = total_time / total_processed if total_processed > 0 else 0
        throughput = total_processed / (total_time / 60) if total_time > 0 else 0  # jobs per minute
        
        return {
            'total_processed': total_processed,
            'total_failed': total_failed,
            'success_rate': (total_processed / (total_processed + total_failed)) * 100 if (total_processed + total_failed) > 0 else 0,
            'avg_processing_time': avg_processing_time,
            'throughput_jobs_per_minute': throughput,
            'active_workers': len([w for w in self.workers if w.running]),
            'queue_depth': await self.queue_manager.redis_client.llen(self.queue_manager.queue_name)
        }
    
    async def stop(self):
        """Stop the pipeline"""
        self.running = False
        
        # Stop all workers
        for worker in self.workers:
            await worker.stop()
        
        console.print("[yellow]🛑 Pipeline stopped[/yellow]")

# Configuration
DEFAULT_CONFIG = {
    'redis_url': 'redis://localhost:6379',
    'database_url': 'sqlite:///image_processing.db',  # Use PostgreSQL for production: 'postgresql://user:pass@localhost/dbname'
    'aws_config': {
        'aws_access_key_id': 'YOUR_ACCESS_KEY',
        'aws_secret_access_key': 'YOUR_SECRET_KEY',
        'region_name': 'us-east-1',
        'bucket_name': 'image-processing-bucket'
    },
    'num_workers': 5,
    'max_queue_size': 1000
}

async def main():
    """Main pipeline execution"""
    console.print(Panel.fit("[bold cyan]Car Face Blur Image Processing Pipeline[/bold cyan]"))
    
    # Initialize pipeline
    pipeline = ImageProcessingPipeline(DEFAULT_CONFIG)
    await pipeline.initialize()
    
    # Start workers
    await pipeline.start_workers(DEFAULT_CONFIG['num_workers'])
    
    # Keep pipeline running
    try:
        while True:
            await asyncio.sleep(10)
            
            # Print stats every 10 seconds
            stats = await pipeline.get_pipeline_stats()
            console.print(f"[dim]Stats: {stats}[/dim]")
            
    except KeyboardInterrupt:
        console.print("[yellow]Shutting down pipeline...[/yellow]")
        await pipeline.stop()

if __name__ == "__main__":
    asyncio.run(main()) 