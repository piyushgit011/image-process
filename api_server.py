"""
FastAPI Server for Image Processing Pipeline
Handles image ingestion and job submission
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import asyncio
import time
import uuid
from typing import Dict, Any, Optional, Union
import logging
from rich.console import Console
from rich.panel import Panel
import json
import base64

from pipeline_architecture import ImageProcessingPipeline, ProcessingStatus
from database_models import DatabaseManager
from config import get_config, get_pipeline_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()

# Initialize FastAPI app
app = FastAPI(
    title="Image Processing Pipeline API",
    description="API for processing images through Car Face Blur models",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global pipeline instance
pipeline: Optional[ImageProcessingPipeline] = None

class Base64ImageRequest(BaseModel):
    image_base64: str
    filename: Optional[str] = None
    content_type: Optional[str] = "image/jpeg"

@app.on_event("startup")
async def startup_event():
    """Initialize pipeline on startup"""
    global pipeline
    
    console.print(Panel.fit("[bold green]🚀 Starting Image Processing API Server[/bold green]"))
    
    # Get configuration
    app_config = get_config()
    pipeline_config = get_pipeline_config()
    
    # Initialize pipeline
    pipeline = ImageProcessingPipeline(pipeline_config)
    await pipeline.initialize()
    await pipeline.start_workers(app_config.NUM_WORKERS)
    
    console.print("[green]✅ API Server ready![/green]")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global pipeline
    
    if pipeline:
        await pipeline.stop()
    console.print("[yellow]🛑 API Server stopped[/yellow]")

@app.post("/upload")
async def upload_image(
    file: Optional[UploadFile] = File(None),
    image_base64: Optional[str] = Form(None),
    filename: Optional[str] = Form(None),
    content_type: Optional[str] = Form("image/jpeg"),
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    Upload and process an image (file or base64)
    - Accepts either a file upload or a base64-encoded image
    - Only uploads if a car is detected
    - Always applies face blur before upload
    """
    try:
        image_data = None
        orig_filename = filename
        orig_content_type = content_type
        
        # Accept file upload
        if file is not None:
            if not file.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="File must be an image")
            image_data = await file.read()
            orig_filename = file.filename
            orig_content_type = file.content_type
        # Accept base64
        elif image_base64 is not None:
            try:
                image_data = base64.b64decode(image_base64)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid base64 image data")
            if not orig_filename:
                orig_filename = f"upload_{uuid.uuid4().hex}.jpg"
        else:
            raise HTTPException(status_code=400, detail="No image file or base64 data provided")
        
        if len(image_data) == 0:
            raise HTTPException(status_code=400, detail="Empty image data")
        
        # Use centralized vehicle detection method
        model_manager = pipeline.model_manager
        car_detected = await model_manager.detect_vehicles_in_image(image_data)
        
        if not car_detected:
            return {
                "status": "skipped",
                "message": "No car detected in image. Image not uploaded.",
                "filename": orig_filename
            }
        
        # Submit job to pipeline (will always apply face blur)
        job_id = await pipeline.submit_job(
            image_data=image_data,
            filename=orig_filename,
            content_type=orig_content_type
        )
        
        return {
            "job_id": job_id,
            "filename": orig_filename,
            "file_size": len(image_data),
            "status": "submitted",
            "message": "Car detected. Image submitted for processing and face blur."
        }
        
    except Exception as e:
        logger.error(f"Error uploading image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/upload-base64")
async def upload_image_base64(request: Base64ImageRequest) -> Dict[str, Any]:
    """
    Upload and process an image via base64 JSON body (legacy, prefer /upload)
    """
    return await upload_image(
        file=None,
        image_base64=request.image_base64,
        filename=request.filename,
        content_type=request.content_type
    )

@app.get("/status/{job_id}")
async def get_job_status(job_id: str) -> Dict[str, Any]:
    """
    Get processing status of a job
    
    Args:
        job_id: Job ID to check
        
    Returns:
        Job status information
    """
    try:
        status = await pipeline.get_job_status(job_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "job_id": job_id,
            "status": status.get('status', 'unknown'),
            "updated_at": status.get('updated_at'),
            "results": status.get('results')
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@app.get("/stats")
async def get_pipeline_stats() -> Dict[str, Any]:
    """
    Get pipeline statistics
    
    Returns:
        Pipeline performance metrics
    """
    try:
        stats = await pipeline.get_pipeline_stats()
        
        return {
            "pipeline_stats": stats,
            "timestamp": time.time(),
            "uptime": time.time() - pipeline.start_time if hasattr(pipeline, 'start_time') else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting pipeline stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Stats retrieval failed: {str(e)}")

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "timestamp": str(time.time()),
        "pipeline_running": pipeline.running if pipeline else False
    }

@app.post("/batch-upload")
async def batch_upload_images(
    files: list[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None
) -> Dict[str, Any]:
    """
    Upload multiple images for batch processing
    
    Args:
        files: List of image files to process
        
    Returns:
        Batch job submission response
    """
    try:
        job_ids = []
        total_size = 0
        skipped = 0
        for file in files:
            # Validate file type
            if not file.content_type.startswith('image/'):
                continue  # Skip non-image files
            image_data = await file.read()
            if len(image_data) == 0:
                continue
            # Use centralized vehicle detection method
            model_manager = pipeline.model_manager
            car_detected = await model_manager.detect_vehicles_in_image(image_data)
            if not car_detected:
                skipped += 1
                continue
            # Submit job
            job_id = await pipeline.submit_job(
                image_data=image_data,
                filename=file.filename,
                content_type=file.content_type
            )
            job_ids.append(job_id)
            total_size += len(image_data)
        return {
            "batch_id": str(uuid.uuid4()),
            "job_ids": job_ids,
            "total_files": len(files),
            "processed_files": len(job_ids),
            "skipped_files": skipped,
            "total_size": total_size,
            "status": "batch_submitted",
            "message": f"Batch submitted with {len(job_ids)} valid car images. {skipped} skipped."
        }
    except Exception as e:
        logger.error(f"Error in batch upload: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Batch upload failed: {str(e)}")

@app.get("/queue-status")
async def get_queue_status() -> Dict[str, Any]:
    """
    Get queue status and depth
    
    Returns:
        Queue information
    """
    try:
        app_config = get_config()
        queue_depth = await pipeline.queue_manager.redis_client.llen(
            pipeline.queue_manager.queue_name
        )
        
        return {
            "queue_depth": queue_depth,
            "max_queue_size": app_config.MAX_QUEUE_SIZE,
            "queue_utilization": (queue_depth / app_config.MAX_QUEUE_SIZE) * 100,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Error getting queue status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Queue status failed: {str(e)}")

@app.get("/database/stats")
async def get_database_stats() -> Dict[str, Any]:
    """
    Get database processing statistics
    
    Returns:
        Database statistics with processing flags
    """
    try:
        stats = await pipeline.database_manager.get_processing_stats()
        return {
            "database_stats": stats,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Error getting database stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database stats failed: {str(e)}")

@app.get("/database/images")
async def get_processed_images(
    is_vehicle_detected: Optional[bool] = None,
    is_face_detected: Optional[bool] = None,
    is_face_blurred: Optional[bool] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get processed images filtered by flags
    
    Args:
        is_vehicle_detected: Filter by vehicle detection flag
        is_face_detected: Filter by face detection flag  
        is_face_blurred: Filter by face blur flag
        limit: Maximum number of results
        
    Returns:
        List of processed images matching criteria
    """
    try:
        images = await pipeline.database_manager.get_processed_images_by_flags(
            is_vehicle_detected=is_vehicle_detected,
            is_face_detected=is_face_detected,
            is_face_blurred=is_face_blurred,
            limit=limit
        )
        
        return {
            "images": [img.to_dict() for img in images],
            "count": len(images),
            "filters": {
                "is_vehicle_detected": is_vehicle_detected,
                "is_face_detected": is_face_detected,
                "is_face_blurred": is_face_blurred,
                "limit": limit
            },
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Error getting processed images: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

@app.get("/database/image/{job_id}")
async def get_processed_image_by_job_id(job_id: str) -> Dict[str, Any]:
    """
    Get processed image record by job ID
    
    Args:
        job_id: Job ID to lookup
        
    Returns:
        Processed image record with all flags and metadata
    """
    try:
        image = await pipeline.database_manager.get_processed_image_by_job_id(job_id)
        
        if not image:
            raise HTTPException(status_code=404, detail="Image record not found")
        
        return {
            "image": image.to_dict(),
            "timestamp": time.time()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processed image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database query failed: {str(e)}")

# API Documentation
@app.get("/")
async def root():
    """API root endpoint with documentation"""
    return {
        "message": "Image Processing Pipeline API",
        "version": "1.0.0",
        "endpoints": {
            "POST /upload": "Upload single image for processing (file or base64)",
            "POST /batch-upload": "Upload multiple images for batch processing (only car images processed)",
            "GET /status/{job_id}": "Get processing status of a job",
            "GET /stats": "Get pipeline performance statistics",
            "GET /health": "Health check endpoint",
            "GET /queue-status": "Get queue status and depth",
            "GET /database/stats": "Get database processing statistics with flags",
            "GET /database/images": "Get processed images filtered by detection flags",
            "GET /database/image/{job_id}": "Get specific processed image record by job ID"
        },
        "models": {
            "car_face_blur": "Car Face Blur Model.pt",
            "yolo_detection": "Car Face Blur Yolov8m.pt",
            "face_detection": "face_recognition library"
        },
        "processing_flags": {
            "is_vehicle_detected": "Whether a vehicle (car/truck/bus/motorcycle) was detected",
            "is_face_detected": "Whether faces were detected in the image",
            "is_face_blurred": "Whether face blurring was applied (only if both vehicle and face detected)"
        }
    }

if __name__ == "__main__":
    # Get configuration
    app_config = get_config()
    
    # Run the server
    uvicorn.run(
        "api_server:app",
        host=app_config.API_HOST,
        port=app_config.API_PORT,
        reload=app_config.API_RELOAD,
        log_level=app_config.API_LOG_LEVEL
    ) 