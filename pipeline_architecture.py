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
from config import get_config, get_pipeline_config

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
    
    def __init__(self, config=None):
        self.config = config or get_config()
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
                # Check if model files exist
                car_model_path = self.config.CAR_FACE_BLUR_MODEL_PATH
                yolo_model_path = self.config.YOLO_DETECTION_MODEL_PATH
                
                for model_path in [car_model_path, yolo_model_path]:
                    if not Path(model_path).exists():
                        raise FileNotFoundError(f"Model file not found: {model_path}")
                
                # Load Car Face Blur Model (YOLO model for face detection/blurring)
                console.print(f"[yellow]Loading Car Face Blur Model from {car_model_path}...[/yellow]")
                self.car_face_blur_model = YOLO(car_model_path)
                
                # Load YOLO Detection Model (YOLO model for vehicle detection)
                console.print(f"[yellow]Loading YOLO Detection Model from {yolo_model_path}...[/yellow]")
                self.yolo_detection_model = YOLO(yolo_model_path)
                
                # Log device info
                device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                logger.info(f"Using device: {device}")
                console.print(f"[green]Using device: {device}[/green]")
                
                self.models_loaded = True
                console.print("[green]✅ Models loaded successfully![/green]")
                
            except Exception as e:
                console.print(f"[red]Error loading models: {str(e)}[/red]")
                raise
    


    async def process_image(self, image_data: bytes) -> Tuple[bytes, Dict[str, Any]]:
        """Process image through detection and blur models"""
        if not self.models_loaded:
            await self.load_models()
        
        # Convert bytes to OpenCV image (BGR format)
        nparr = np.frombuffer(image_data, np.uint8)
        image_array = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image_array is None:
            raise ValueError("Failed to decode image data")
        
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
            # Get configuration for thresholds
            car_confidence_threshold = getattr(self.config, 'CAR_CONFIDENCE_THRESHOLD', 0.8)
            face_confidence_threshold = getattr(self.config, 'FACE_CONFIDENCE_THRESHOLD', 0.8)
            
            # Step 1: YOLO Vehicle Detection
            logger.debug("Running vehicle detection...")
            vehicle_results = self.yolo_detection_model(image_array)[0]
            
            vehicle_detected = False
            vehicle_boxes = []
            vehicle_confidences = []
            vehicle_classes = []
            
            if vehicle_results.boxes is not None:
                # COCO class IDs for vehicles: 2=car, 5=bus, 7=truck, 3=motorcycle
                vehicle_class_ids = {2, 5, 7, 3}  # car, bus, truck, motorcycle
                
                for box_idx, cls in enumerate(vehicle_results.boxes.cls):
                    cls_value = int(cls.item())
                    conf_value = vehicle_results.boxes.conf[box_idx].item()
                    
                    if cls_value in vehicle_class_ids and conf_value > car_confidence_threshold:
                        vehicle_detected = True
                        vehicle_boxes.append(vehicle_results.boxes.xyxy[box_idx].cpu().numpy().tolist())
                        vehicle_confidences.append(conf_value)
                        vehicle_classes.append(cls_value)
                        logger.debug(f"Vehicle detected: class={cls_value}, confidence={conf_value:.2f}")
                
                results['vehicle_detection'] = {
                    'boxes': vehicle_boxes,
                    'confidences': vehicle_confidences,
                    'class_ids': vehicle_classes,
                    'detection_count': len(vehicle_boxes),
                    'vehicle_detected': vehicle_detected
                }
            
            results['flags']['is_vehicle_detected'] = vehicle_detected
            
            # Step 2: Face Detection using YOLO face model
            logger.debug("Running face detection...")
            face_results = self.car_face_blur_model(image_array)[0]
            
            person_detected = False
            face_boxes = []
            face_confidences = []
            faces_blurred = 0
            
            # Create a copy of the image for processing
            processed_image = image_array.copy()
            
            if face_results.boxes is not None:
                # Class 0 is typically 'person' in YOLO models
                person_class = 0
                
                for box_idx, cls in enumerate(face_results.boxes.cls):
                    cls_value = int(cls.item())
                    conf_value = face_results.boxes.conf[box_idx].item()
                    
                    if cls_value == person_class and conf_value > face_confidence_threshold:
                        person_detected = True
                        box = face_results.boxes.xyxy[box_idx].cpu().numpy()
                        x1, y1, x2, y2 = map(int, box)
                        
                        # Ensure box coordinates are within image bounds
                        x1 = max(0, x1)
                        y1 = max(0, y1)
                        x2 = min(image_array.shape[1], x2)
                        y2 = min(image_array.shape[0], y2)
                        
                        # Check if box dimensions are valid
                        if x2 <= x1 or y2 <= y1:
                            logger.warning(f"Invalid box dimensions: ({x1},{y1},{x2},{y2})")
                            continue
                        
                        face_boxes.append([x1, y1, x2, y2])
                        face_confidences.append(conf_value)
                        
                        # Apply Gaussian blur to face region
                        face_region = processed_image[y1:y2, x1:x2]
                        blurred_face = cv2.GaussianBlur(face_region, (99, 99), 30)
                        processed_image[y1:y2, x1:x2] = blurred_face
                        faces_blurred += 1
                        
                        logger.debug(f"Face blurred at coordinates: ({x1},{y1},{x2},{y2}), confidence={conf_value:.2f}")
            
            results['face_detection'] = {
                'face_count': len(face_boxes),
                'face_boxes': face_boxes,
                'face_confidences': face_confidences,
                'faces_detected': person_detected
            }
            results['flags']['is_face_detected'] = person_detected
            
            # Step 3: Determine if face blur was applied
            face_blur_applied = person_detected and faces_blurred > 0
            results['flags']['is_face_blurred'] = face_blur_applied
            
            results['car_face_blur'] = {
                'processing_applied': face_blur_applied,
                'faces_blurred': faces_blurred,
                'input_shape': image_array.shape,
                'output_shape': processed_image.shape,
                'reason': f'Blurred {faces_blurred} faces' if face_blur_applied else 'No faces detected above threshold'
            }
            
            # Convert processed image back to bytes
            is_success, buffer = cv2.imencode('.jpg', processed_image)
            if not is_success:
                raise ValueError("Failed to encode processed image")
            
            processed_bytes = buffer.tobytes()
            
            results['processing_metadata'] = {
                'original_size': len(image_data),
                'processed_size': len(processed_bytes),
                'compression_ratio': len(processed_bytes) / len(image_data) if len(image_data) > 0 else 0,
                'car_confidence_threshold': car_confidence_threshold,
                'face_confidence_threshold': face_confidence_threshold
            }
            
            logger.info(f"Image processing complete - Vehicle: {vehicle_detected}, Faces: {person_detected}, Blurred: {face_blur_applied}")
            
            return processed_bytes, results
            
        except Exception as e:
            logger.error(f"Error processing image: {str(e)}")
            raise

class RedisQueueManager:
    """Manages Redis-based job queue"""
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or get_config().get_redis_url()
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
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or get_pipeline_config()
        self.app_config = get_config()
        self.model_manager = ModelManager(self.app_config)
        self.queue_manager = RedisQueueManager(self.config.get('redis_url', self.app_config.get_redis_url()))
        self.storage_manager = S3StorageManager(self.config.get('aws_config', self.app_config.aws_config))
        self.database_manager = DatabaseManager(self.config.get('database_url', self.app_config.DATABASE_URL))
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

async def main():
    """Main pipeline execution"""
    console.print(Panel.fit("[bold cyan]Car Face Blur Image Processing Pipeline[/bold cyan]"))
    
    # Get configuration
    app_config = get_config()
    pipeline_config = get_pipeline_config()
    
    # Initialize pipeline
    pipeline = ImageProcessingPipeline(pipeline_config)
    await pipeline.initialize()
    
    # Start workers
    await pipeline.start_workers(app_config.NUM_WORKERS)
    
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