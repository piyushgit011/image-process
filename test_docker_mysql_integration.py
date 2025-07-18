#!/usr/bin/env python3
"""
Test Docker Compose MySQL Integration
Verifies that MySQL integration works properly with Docker Compose
"""

import asyncio
import sys
import time
import logging
from rich.console import Console
from rich.panel import Panel
import subprocess
import json

# Import the main components
from database_models import DatabaseManager
from config import get_config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()

async def test_docker_mysql_connection():
    """Test MySQL connection in Docker environment"""
    console.print(Panel.fit("[bold cyan]Testing Docker MySQL Integration[/bold cyan]"))
    
    try:
        # Test with Docker MySQL connection string
        docker_db_url = "mysql+pymysql://pipeline_user:secure_password_123@localhost:3306/image_processing"
        console.print(f"[cyan]Testing connection to: {docker_db_url.split('@')[0]}@***[/cyan]")
        
        # Initialize database manager with Docker connection
        db_manager = DatabaseManager(docker_db_url)
        await db_manager.initialize()
        
        console.print("[green]✅ Docker MySQL connection successful[/green]")
        
        # Test database operations
        test_job_id = f"docker-test-{int(time.time())}"
        
        console.print("[yellow]Testing database operations...[/yellow]")
        processed_image = await db_manager.save_processed_image(
            job_id=test_job_id,
            original_filename="docker_test.jpg",
            s3_original_path="s3://test-bucket/original/docker_test.jpg",
            s3_processed_path="s3://test-bucket/processed/docker_test.jpg",
            is_vehicle_detected=True,
            is_face_detected=True,
            is_face_blurred=True,
            content_type="image/jpeg",
            file_size_original=2048,
            file_size_processed=2200,
            processing_time_seconds=1.8,
            vehicle_detection_data={"boxes": [[100, 100, 200, 200]], "confidences": [0.92]},
            face_detection_data={"person_count": 1, "person_boxes": [[60, 60, 160, 160]]}
        )
        
        console.print(f"[green]✅ Test record created: {processed_image.id}[/green]")
        
        # Test retrieval
        retrieved = await db_manager.get_processed_image_by_job_id(test_job_id)
        if retrieved:
            console.print(f"[green]✅ Test record retrieved: {retrieved.job_id}[/green]")
        
        # Test statistics
        stats = await db_manager.get_processing_stats()
        console.print(f"[green]✅ Statistics: {stats['total_images_processed']} total images[/green]")
        
        console.print(Panel.fit("[bold green]🎉 Docker MySQL Integration Test Passed![/bold green]"))
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Docker MySQL integration test failed: {str(e)}[/red]")
        logger.error(f"Docker MySQL test error: {str(e)}")
        return False

def check_docker_compose_status():
    """Check Docker Compose service status"""
    console.print(Panel.fit("[bold cyan]Checking Docker Compose Services[/bold cyan]"))
    
    try:
        # Check if docker compose is available
        result = subprocess.run(['docker', 'compose', 'version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            console.print("[red]❌ docker compose not found[/red]")
            return False
        
        console.print(f"[green]✅ {result.stdout.strip()}[/green]")
        
        # Check service status
        result = subprocess.run(['docker', 'compose', 'ps', '--format', 'json'], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and result.stdout.strip():
            services = []
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    try:
                        service = json.loads(line)
                        services.append(service)
                    except json.JSONDecodeError:
                        pass
            
            console.print(f"[cyan]Found {len(services)} Docker Compose services:[/cyan]")
            
            mysql_running = False
            for service in services:
                name = service.get('Name', 'Unknown')
                state = service.get('State', 'Unknown')
                status = service.get('Status', 'Unknown')
                
                if 'mysql' in name.lower():
                    mysql_running = (state.lower() == 'running')
                    status_color = "green" if mysql_running else "red"
                    console.print(f"  [{status_color}]{name}: {state} ({status})[/{status_color}]")
                else:
                    console.print(f"  [dim]{name}: {state} ({status})[/dim]")
            
            return mysql_running
        else:
            console.print("[yellow]⚠️  No Docker Compose services found or not running[/yellow]")
            return False
            
    except subprocess.TimeoutExpired:
        console.print("[red]❌ Docker Compose command timed out[/red]")
        return False
    except FileNotFoundError:
        console.print("[red]❌ docker-compose command not found[/red]")
        return False
    except Exception as e:
        console.print(f"[red]❌ Error checking Docker Compose: {str(e)}[/red]")
        return False

def provide_setup_instructions():
    """Provide setup instructions for Docker Compose"""
    console.print(Panel.fit("[bold yellow]Docker Compose Setup Instructions[/bold yellow]"))
    
    console.print("[cyan]To start the MySQL-integrated Docker Compose setup:[/cyan]")
    console.print("")
    console.print("[white]1. Start all services:[/white]")
    console.print("   [dim]docker compose up -d[/dim]")
    console.print("")
    console.print("[white]2. Check service status:[/white]")
    console.print("   [dim]docker compose ps[/dim]")
    console.print("")
    console.print("[white]3. View MySQL logs:[/white]")
    console.print("   [dim]docker compose logs -f mysql[/dim]")
    console.print("")
    console.print("[white]4. Initialize database (if needed):[/white]")
    console.print("   [dim]docker compose exec api-server python init_database.py[/dim]")
    console.print("")
    console.print("[white]5. Test the integration:[/white]")
    console.print("   [dim]python test_docker_mysql_integration.py[/dim]")
    console.print("")
    console.print("[white]6. Access API:[/white]")
    console.print("   [dim]curl http://localhost:8000/health[/dim]")

async def main():
    """Main test execution"""
    console.print(Panel.fit("[bold blue]Docker Compose MySQL Integration Test[/bold blue]"))
    
    # Check Docker Compose status
    mysql_running = check_docker_compose_status()
    
    if mysql_running:
        console.print("[green]✅ MySQL service is running in Docker Compose[/green]")
        
        # Wait a moment for MySQL to be fully ready
        console.print("[yellow]Waiting for MySQL to be fully ready...[/yellow]")
        await asyncio.sleep(5)
        
        # Test the integration
        success = await test_docker_mysql_connection()
        
        if success:
            console.print(Panel.fit("[bold green]🚀 Docker MySQL Integration: FULLY OPERATIONAL![/bold green]"))
            console.print("[cyan]The Docker Compose setup with MySQL is working perfectly![/cyan]")
        else:
            console.print("[red]Integration test failed. Check MySQL container logs.[/red]")
            console.print("[dim]docker-compose logs mysql[/dim]")
    else:
        console.print("[yellow]⚠️  MySQL service not running in Docker Compose[/yellow]")
        provide_setup_instructions()
        
        console.print(Panel.fit("[bold yellow]Setup Required[/bold yellow]"))
        console.print("[cyan]Please start the Docker Compose services first, then run this test again.[/cyan]")

if __name__ == "__main__":
    asyncio.run(main())