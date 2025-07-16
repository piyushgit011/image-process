"""
Standalone Image Processing Worker
Runs independently to process images from Redis queue
"""

import asyncio
import os
import sys
import time
import logging
from typing import Optional
import signal
from rich.console import Console
from rich.panel import Panel
import io
import numpy as np
from PIL import Image

from pipeline_architecture import (
    ImageProcessingPipeline, 
    ModelManager, 
    RedisQueueManager, 
    S3StorageManager
)
from database_models import DatabaseManager
from config import get_config, get_pipeline_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
console = Console()

class StandaloneWorker:
    """Standalone worker for image processing"""
    
    def __init__(self, worker_id: str, config: dict = None):
        self.worker_id = worker_id
        self.config = config or get_pipeline_config()
        self.app_config = get_config()
        self.running = False
        self.stats = {
            'processed': 0,
            'failed': 0,
            'total_time': 0,
            'start_time': time.time()
        }
        
        # Initialize components
        self.model_manager = ModelManager(self.app_config)
        self.queue_manager = RedisQueueManager(self.config.get('redis_url', self.app_config.get_redis_url()))
        self.storage_manager = S3StorageManager(self.config.get('aws_config', self.app_config.aws_config))
        self.database_manager = DatabaseManager(self.config.get('database_url', self.app_config.DATABASE_URL))
        
    async def initialize(self):
        """Initialize worker components"""
        console.print(f"[cyan]🚀 Initializing Worker {self.worker_id}...[/cyan]")
        
        try:
            # Connect to Redis
            await self.queue_manager.connect()
            console.print(f"[green]✅ Worker {self.worker_id} connected to Redis[/green]")
            
            # Connect to S3
            await self.storage_manager.connect()
            console.print(f"[green]✅ Worker {self.worker_id} connected to S3[/green]")
            
            # Initialize database
            await self.database_manager.initialize()
            console.print(f"[green]✅ Worker {self.worker_id} connected to database[/green]")
            
            # Load models
            await self.model_manager.load_models()
            console.print(f"[green]✅ Worker {self.worker_id} loaded models[/green]")
            
            return True
            
        except Exception as e:
            console.print(f"[red]❌ Worker {self.worker_id} initialization failed: {str(e)}[/red]")
            return False
    
    async def process_job(self, job_data: dict):
        """Process a single job"""
        start_time = time.time()
        job_id = job_data.get('job_id', 'unknown')
        
        try:
            console.print(f"[cyan]🔄 Worker {self.worker_id} processing job {job_id}[/cyan]")
            
            # Update job status to processing
            await self.queue_manager.update_job_status(job_id, 'processing')
            
            # Extract job data
            image_data = job_data.get('image_data', b'')
            filename = job_data.get('original_filename', 'unknown')
            content_type = job_data.get('content_type', 'image/jpeg')
            
            if not image_data:
                raise ValueError("No image data provided")
            
            # Use centralized vehicle detection method
            car_detected = await self.model_manager.detect_vehicles_in_image(image_data)
            if not car_detected:
                # Mark as skipped, do not upload
                await self.queue_manager.update_job_status(job_id, 'skipped', {
                    'message': 'No car detected in image. Image not uploaded.',
                    'filename': filename
                })
                console.print(f"[yellow]⏭️  No car detected for job {job_id}, skipping upload.[/yellow]")
                return
            # Process image through models (always apply face blur)
            processed_image, results = await self.model_manager.process_image(image_data)
            # Generate S3 keys
            timestamp = int(time.time())
            original_key = f"original/{job_id}_{timestamp}.jpg"
            processed_key = f"processed/{job_id}_{timestamp}.jpg"
            metadata_key = f"metadata/{job_id}_{timestamp}.json"
            # Upload to S3
            original_url = await self.storage_manager.upload_image(
                image_data, original_key, content_type
            )
            processed_url = await self.storage_manager.upload_image(
                processed_image, processed_key, 'image/jpeg'
            )
            # Prepare processing result
            processing_time = time.time() - start_time
            processing_result = {
                'job_id': job_id,
                'original_image_path': original_url,
                'processed_image_path': processed_url,
                'blur_metadata': results.get('face_blur', {}),
                'detection_metadata': results.get('vehicle_detection', {}),
                'processing_time': processing_time,
                'model_versions': {
                    'person_detection': '1.0',
                    'vehicle_detection': '8m'
                },
                'confidence_scores': {
                    'avg_detection_confidence': np.mean(results.get('vehicle_detection', {}).get('confidences', [0])) if results.get('vehicle_detection', {}).get('confidences') else 0
                }
            }
            
            # Upload metadata
            metadata_url = await self.storage_manager.upload_metadata(
                processing_result, metadata_key
            )
            
            # Save to database with flags
            await self.database_manager.save_processed_image(
                job_id=job_id,
                original_filename=filename,
                s3_original_path=original_url,
                s3_processed_path=processed_url,
                is_vehicle_detected=results['flags']['is_vehicle_detected'],
                is_face_detected=results['flags']['is_person_detected'],  # Person detection (for face blurring)
                is_face_blurred=results['flags']['is_face_blurred'],
                content_type=content_type,
                file_size_original=len(image_data),
                file_size_processed=len(processed_image),
                processing_time_seconds=processing_time,
                vehicle_detection_data=results.get('vehicle_detection', {}),
                face_detection_data=results.get('person_detection', {})  # Person detection data
            )
            
            # Update job status
            await self.queue_manager.update_job_status(job_id, 'completed', processing_result)
            # Update stats
            self.stats['processed'] += 1
            self.stats['total_time'] += time.time() - start_time
            console.print(f"[green]✅ Worker {self.worker_id} completed job {job_id}[/green]")
        except Exception as e:
            logger.error(f"Worker {self.worker_id} error processing job {job_id}: {str(e)}")
            # Update job status to failed
            await self.queue_manager.update_job_status(
                job_id, 'failed', {'error': str(e)}
            )
            self.stats['failed'] += 1
    
    async def run(self):
        """Main worker loop"""
        self.running = True
        console.print(f"[bold green]🚀 Worker {self.worker_id} started[/bold green]")
        
        while self.running:
            try:
                # Get job from queue
                job = await self.queue_manager.dequeue_job()
                
                if job:
                    await self.process_job(job)
                else:
                    # No jobs available, wait a bit
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Worker {self.worker_id} error: {str(e)}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def stop(self):
        """Stop the worker"""
        self.running = False
        console.print(f"[yellow]🛑 Worker {self.worker_id} stopping...[/yellow]")
        
        # Print final stats
        uptime = time.time() - self.stats['start_time']
        avg_processing_time = self.stats['total_time'] / self.stats['processed'] if self.stats['processed'] > 0 else 0
        throughput = self.stats['processed'] / (uptime / 60) if uptime > 0 else 0
        
        console.print(Panel.fit(
            f"[bold cyan]Worker {self.worker_id} Final Stats[/bold cyan]\n"
            f"Processed: [green]{self.stats['processed']}[/green]\n"
            f"Failed: [red]{self.stats['failed']}[/red]\n"
            f"Success Rate: [green]{(self.stats['processed'] / (self.stats['processed'] + self.stats['failed']) * 100):.1f}%[/green]\n"
            f"Avg Processing Time: [cyan]{avg_processing_time:.2f}s[/cyan]\n"
            f"Throughput: [cyan]{throughput:.1f} jobs/minute[/cyan]\n"
            f"Uptime: [cyan]{uptime:.1f}s[/cyan]"
        ))
    
    def get_stats(self):
        """Get current worker statistics"""
        uptime = time.time() - self.stats['start_time']
        avg_processing_time = self.stats['total_time'] / self.stats['processed'] if self.stats['processed'] > 0 else 0
        throughput = self.stats['processed'] / (uptime / 60) if uptime > 0 else 0
        
        return {
            'worker_id': self.worker_id,
            'processed': self.stats['processed'],
            'failed': self.stats['failed'],
            'success_rate': (self.stats['processed'] / (self.stats['processed'] + self.stats['failed']) * 100) if (self.stats['processed'] + self.stats['failed']) > 0 else 0,
            'avg_processing_time': avg_processing_time,
            'throughput_jobs_per_minute': throughput,
            'uptime': uptime,
            'running': self.running
        }

async def main():
    """Main worker execution"""
    # Get worker ID from environment or use default
    worker_id = os.getenv('WORKER_ID', f'worker-{int(time.time())}')
    
    console.print(Panel.fit(f"[bold cyan]Image Processing Worker {worker_id}[/bold cyan]"))
    
    # Create and initialize worker (config will be loaded automatically)
    worker = StandaloneWorker(worker_id)
    
    # Initialize worker
    if not await worker.initialize():
        console.print("[red]❌ Worker initialization failed, exiting[/red]")
        sys.exit(1)
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        console.print(f"[yellow]Received signal {signum}, shutting down...[/yellow]")
        asyncio.create_task(worker.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Run the worker
        await worker.run()
    except KeyboardInterrupt:
        console.print("[yellow]Received keyboard interrupt[/yellow]")
    finally:
        await worker.stop()

if __name__ == "__main__":
    asyncio.run(main()) 