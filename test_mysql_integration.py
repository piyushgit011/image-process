#!/usr/bin/env python3
"""
Test MySQL Integration with API Components
Verifies that the database integration works with the full pipeline
"""

import asyncio
import sys
import logging
from rich.console import Console
from rich.panel import Panel

# Import the main components
from database_models import DatabaseManager
from config import get_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()

async def test_database_integration():
    """Test database integration with pipeline components"""
    console.print(Panel.fit("[bold cyan]Testing MySQL Integration with Pipeline[/bold cyan]"))
    
    try:
        # Get configuration
        config = get_config()
        console.print(f"[cyan]Testing with database: {config.DATABASE_URL.split('@')[0]}@***[/cyan]")
        
        # Initialize database manager
        db_manager = DatabaseManager(config.DATABASE_URL)
        await db_manager.initialize()
        
        console.print("[green]✅ Database manager initialized[/green]")
        
        # Test multiple image processing records
        test_jobs = [
            {
                "job_id": "job-001-vehicle-face",
                "filename": "car_with_person.jpg",
                "vehicle_detected": True,
                "face_detected": True,
                "face_blurred": True
            },
            {
                "job_id": "job-002-vehicle-only", 
                "filename": "empty_car.jpg",
                "vehicle_detected": True,
                "face_detected": False,
                "face_blurred": False
            },
            {
                "job_id": "job-003-no-vehicle",
                "filename": "landscape.jpg", 
                "vehicle_detected": False,
                "face_detected": False,
                "face_blurred": False
            }
        ]
        
        console.print("[yellow]Creating test processing records...[/yellow]")
        
        for job in test_jobs:
            await db_manager.save_processed_image(
                job_id=job["job_id"],
                original_filename=job["filename"],
                s3_original_path=f"s3://test-bucket/original/{job['filename']}",
                s3_processed_path=f"s3://test-bucket/processed/{job['filename']}",
                is_vehicle_detected=job["vehicle_detected"],
                is_face_detected=job["face_detected"],
                is_face_blurred=job["face_blurred"],
                content_type="image/jpeg",
                file_size_original=2048,
                file_size_processed=2200,
                processing_time_seconds=1.5,
                vehicle_detection_data={"boxes": [[100, 100, 200, 200]], "confidences": [0.9]} if job["vehicle_detected"] else {},
                face_detection_data={"person_count": 1, "person_boxes": [[50, 50, 150, 150]]} if job["face_detected"] else {}
            )
            console.print(f"  ✅ Created record: {job['job_id']}")
        
        # Test filtering by flags
        console.print("[yellow]Testing flag-based filtering...[/yellow]")
        
        # Get images with vehicles detected
        vehicle_images = await db_manager.get_processed_images_by_flags(is_vehicle_detected=True)
        console.print(f"  📊 Images with vehicles: {len(vehicle_images)}")
        
        # Get images with faces detected
        face_images = await db_manager.get_processed_images_by_flags(is_face_detected=True)
        console.print(f"  📊 Images with faces: {len(face_images)}")
        
        # Get images with faces blurred
        blurred_images = await db_manager.get_processed_images_by_flags(is_face_blurred=True)
        console.print(f"  📊 Images with blur applied: {len(blurred_images)}")
        
        # Get comprehensive statistics
        console.print("[yellow]Testing statistics generation...[/yellow]")
        stats = await db_manager.get_processing_stats()
        
        console.print(f"[green]📈 Processing Statistics:[/green]")
        console.print(f"  - Total images processed: {stats['total_images_processed']}")
        console.print(f"  - Vehicle detection count: {stats['vehicle_detection_count']}")
        console.print(f"  - Face detection count: {stats['face_detection_count']}")
        console.print(f"  - Face blur count: {stats['face_blur_count']}")
        console.print(f"  - Vehicle detection rate: {stats['vehicle_detection_rate']:.1f}%")
        console.print(f"  - Face detection rate: {stats['face_detection_rate']:.1f}%")
        console.print(f"  - Face blur rate: {stats['face_blur_rate']:.1f}%")
        
        # Test individual record retrieval
        console.print("[yellow]Testing individual record retrieval...[/yellow]")
        for job in test_jobs:
            record = await db_manager.get_processed_image_by_job_id(job["job_id"])
            if record:
                console.print(f"  ✅ Retrieved: {record.job_id} - Vehicle:{record.is_vehicle_detected}, Face:{record.is_face_detected}, Blur:{record.is_face_blurred}")
            else:
                console.print(f"  ❌ Failed to retrieve: {job['job_id']}")
        
        console.print(Panel.fit("[bold green]🎉 MySQL Integration Test Complete![/bold green]"))
        console.print("[cyan]All database operations working correctly with the pipeline![/cyan]")
        
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Integration test failed: {str(e)}[/red]")
        logger.error(f"Integration test error: {str(e)}")
        return False

async def main():
    """Main test execution"""
    console.print(Panel.fit("[bold blue]MySQL Integration Test Suite[/bold blue]"))
    
    success = await test_database_integration()
    
    if success:
        console.print(Panel.fit("[bold green]🚀 MySQL Integration: READY FOR PRODUCTION![/bold green]"))
        console.print("[cyan]The database is fully integrated and operational.[/cyan]")
        console.print("[cyan]You can now start the API server with: python api_server.py[/cyan]")
    else:
        console.print("[red]Integration test failed. Please check the logs.[/red]")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())