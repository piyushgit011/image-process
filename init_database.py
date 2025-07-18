#!/usr/bin/env python3
"""
MySQL Database Initialization Script
Initializes the MySQL database for the Image Processing Pipeline
"""

import asyncio
import sys
import logging
from rich.console import Console
from rich.panel import Panel

from database_models import DatabaseManager
from config import get_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()

async def init_database():
    """Initialize the MySQL database"""
    console.print(Panel.fit("[bold cyan]MySQL Database Initialization[/bold cyan]"))
    
    try:
        # Get configuration
        config = get_config()
        console.print(f"[cyan]Database URL: {config.DATABASE_URL.split('@')[0]}@***[/cyan]")
        
        # Initialize database manager
        db_manager = DatabaseManager(config.DATABASE_URL)
        
        console.print("[yellow]Connecting to MySQL database...[/yellow]")
        await db_manager.initialize()
        
        console.print("[green]✅ Database initialized successfully![/green]")
        console.print("[green]✅ Tables created successfully![/green]")
        
        # Test database connection with a simple query
        session = db_manager.get_session()
        try:
            from sqlalchemy import text
            # Test the connection
            result = session.execute(text("SELECT 1 as test")).fetchone()
            console.print(f"[green]✅ Database connection test: {result[0]}[/green]")
            
            # Check if tables exist
            tables_query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = DATABASE()
            """)
            tables = session.execute(tables_query).fetchall()
            
            console.print(f"[cyan]📋 Created tables:[/cyan]")
            for table in tables:
                console.print(f"  - {table[0]}")
                
        finally:
            session.close()
        
        console.print(Panel.fit("[bold green]🎉 MySQL Database Setup Complete![/bold green]"))
        
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Database initialization failed: {str(e)}[/red]")
        logger.error(f"Database initialization error: {str(e)}")
        return False

async def test_database_operations():
    """Test basic database operations"""
    console.print(Panel.fit("[bold cyan]Testing Database Operations[/bold cyan]"))
    
    try:
        config = get_config()
        db_manager = DatabaseManager(config.DATABASE_URL)
        await db_manager.initialize()
        
        # Test saving a processed image record
        test_job_id = "test-job-12345"
        
        console.print("[yellow]Testing database write operation...[/yellow]")
        processed_image = await db_manager.save_processed_image(
            job_id=test_job_id,
            original_filename="test_image.jpg",
            s3_original_path="s3://test-bucket/original/test.jpg",
            s3_processed_path="s3://test-bucket/processed/test.jpg",
            is_vehicle_detected=True,
            is_face_detected=True,
            is_face_blurred=True,
            content_type="image/jpeg",
            file_size_original=1024,
            file_size_processed=1200,
            processing_time_seconds=2.5,
            vehicle_detection_data={"boxes": [[100, 100, 200, 200]], "confidences": [0.95]},
            face_detection_data={"person_count": 1, "person_boxes": [[50, 50, 150, 150]]}
        )
        
        console.print(f"[green]✅ Test record created with ID: {processed_image.id}[/green]")
        
        # Test reading the record back
        console.print("[yellow]Testing database read operation...[/yellow]")
        retrieved_image = await db_manager.get_processed_image_by_job_id(test_job_id)
        
        if retrieved_image:
            console.print(f"[green]✅ Test record retrieved: {retrieved_image.job_id}[/green]")
            console.print(f"  - Vehicle detected: {retrieved_image.is_vehicle_detected}")
            console.print(f"  - Face detected: {retrieved_image.is_face_detected}")
            console.print(f"  - Face blurred: {retrieved_image.is_face_blurred}")
        else:
            console.print("[red]❌ Failed to retrieve test record[/red]")
            return False
        
        # Test getting statistics
        console.print("[yellow]Testing statistics query...[/yellow]")
        stats = await db_manager.get_processing_stats()
        console.print(f"[green]✅ Statistics retrieved:[/green]")
        console.print(f"  - Total images: {stats['total_images_processed']}")
        console.print(f"  - Vehicle detection rate: {stats['vehicle_detection_rate']:.1f}%")
        console.print(f"  - Face detection rate: {stats['face_detection_rate']:.1f}%")
        console.print(f"  - Face blur rate: {stats['face_blur_rate']:.1f}%")
        
        console.print(Panel.fit("[bold green]🎉 Database Operations Test Complete![/bold green]"))
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Database operations test failed: {str(e)}[/red]")
        logger.error(f"Database operations test error: {str(e)}")
        return False

async def main():
    """Main execution function"""
    console.print(Panel.fit("[bold blue]Image Processing Pipeline - MySQL Setup[/bold blue]"))
    
    # Initialize database
    init_success = await init_database()
    if not init_success:
        console.print("[red]Database initialization failed. Exiting.[/red]")
        sys.exit(1)
    
    # Test database operations
    test_success = await test_database_operations()
    if not test_success:
        console.print("[yellow]Database operations test failed, but database is initialized.[/yellow]")
        sys.exit(1)
    
    console.print(Panel.fit("[bold green]🚀 MySQL Integration Ready![/bold green]"))
    console.print("[cyan]You can now start the API server or workers.[/cyan]")

if __name__ == "__main__":
    asyncio.run(main())