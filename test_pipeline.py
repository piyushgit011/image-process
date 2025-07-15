#!/usr/bin/env python3
"""
Test script for the Image Processing Pipeline
Tests the complete pipeline functionality
"""

import asyncio
import aiohttp
import time
import json
import base64
from io import BytesIO
from PIL import Image
import numpy as np
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

console = Console()

class PipelineTester:
    """Test the image processing pipeline"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def create_test_image(self, width=100, height=100):
        """Create a simple test image"""
        # Create a simple test image with some patterns
        image_array = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Add some patterns to make it more interesting
        for i in range(height):
            for j in range(width):
                image_array[i, j] = [
                    (i * 255) // height,  # Red gradient
                    (j * 255) // width,   # Green gradient
                    128                     # Blue constant
                ]
        
        # Convert to PIL Image
        image = Image.fromarray(image_array)
        
        # Convert to bytes
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format='JPEG', quality=95)
        img_byte_arr.seek(0)
        
        return img_byte_arr.getvalue()
    
    async def test_health(self):
        """Test health endpoint"""
        console.print("[cyan]Testing health endpoint...[/cyan]")
        
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    console.print(f"[green]✅ Health check passed: {data}[/green]")
                    return True
                else:
                    console.print(f"[red]❌ Health check failed: {response.status}[/red]")
                    return False
        except Exception as e:
            console.print(f"[red]❌ Health check error: {str(e)}[/red]")
            return False
    
    async def test_upload(self, image_data):
        """Test image upload"""
        console.print("[cyan]Testing image upload...[/cyan]")
        
        try:
            # Create form data
            data = aiohttp.FormData()
            data.add_field('file', image_data, filename='test-image.jpg', content_type='image/jpeg')
            
            async with self.session.post(f"{self.base_url}/upload", data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    console.print(f"[green]✅ Upload successful: {result}[/green]")
                    return result.get('job_id')
                else:
                    error_text = await response.text()
                    console.print(f"[red]❌ Upload failed: {response.status} - {error_text}[/red]")
                    return None
        except Exception as e:
            console.print(f"[red]❌ Upload error: {str(e)}[/red]")
            return None
    
    async def test_job_status(self, job_id, max_wait=60):
        """Test job status checking"""
        console.print(f"[cyan]Testing job status for {job_id}...[/cyan]")
        
        start_time = time.time()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("Waiting for job completion..."),
            BarColumn(),
            TextColumn("{task.percentage:.0f}%")
        ) as progress:
            task = progress.add_task("Processing...", total=100)
            
            while time.time() - start_time < max_wait:
                try:
                    async with self.session.get(f"{self.base_url}/status/{job_id}") as response:
                        if response.status == 200:
                            data = await response.json()
                            status = data.get('status', 'unknown')
                            
                            # Update progress
                            elapsed = time.time() - start_time
                            progress_percent = min((elapsed / max_wait) * 100, 100)
                            progress.update(task, completed=progress_percent)
                            
                            if status == 'completed':
                                console.print(f"[green]✅ Job completed successfully![/green]")
                                console.print(f"[cyan]Results: {json.dumps(data.get('results', {}), indent=2)}[/cyan]")
                                return True
                            elif status == 'failed':
                                console.print(f"[red]❌ Job failed: {data.get('results', {}).get('error', 'Unknown error')}[/red]")
                                return False
                            elif status == 'processing':
                                console.print(f"[yellow]⏳ Job is processing...[/yellow]")
                            else:
                                console.print(f"[blue]📋 Job status: {status}[/blue]")
                        else:
                            console.print(f"[red]❌ Status check failed: {response.status}[/red]")
                            return False
                            
                except Exception as e:
                    console.print(f"[red]❌ Status check error: {str(e)}[/red]")
                    return False
                
                await asyncio.sleep(2)
            
            console.print(f"[red]❌ Job did not complete within {max_wait} seconds[/red]")
            return False
    
    async def test_stats(self):
        """Test pipeline statistics"""
        console.print("[cyan]Testing pipeline statistics...[/cyan]")
        
        try:
            async with self.session.get(f"{self.base_url}/stats") as response:
                if response.status == 200:
                    data = await response.json()
                    console.print(f"[green]✅ Stats retrieved successfully[/green]")
                    console.print(f"[cyan]Pipeline stats: {json.dumps(data.get('pipeline_stats', {}), indent=2)}[/cyan]")
                    return True
                else:
                    console.print(f"[red]❌ Stats failed: {response.status}[/red]")
                    return False
        except Exception as e:
            console.print(f"[red]❌ Stats error: {str(e)}[/red]")
            return False
    
    async def test_queue_status(self):
        """Test queue status"""
        console.print("[cyan]Testing queue status...[/cyan]")
        
        try:
            async with self.session.get(f"{self.base_url}/queue-status") as response:
                if response.status == 200:
                    data = await response.json()
                    console.print(f"[green]✅ Queue status retrieved[/green]")
                    console.print(f"[cyan]Queue depth: {data.get('queue_depth', 'unknown')}[/cyan]")
                    return True
                else:
                    console.print(f"[red]❌ Queue status failed: {response.status}[/red]")
                    return False
        except Exception as e:
            console.print(f"[red]❌ Queue status error: {str(e)}[/red]")
            return False
    
    async def test_batch_upload(self, num_images=3):
        """Test batch upload"""
        console.print(f"[cyan]Testing batch upload with {num_images} images...[/cyan]")
        
        try:
            # Create multiple test images
            data = aiohttp.FormData()
            
            for i in range(num_images):
                image_data = self.create_test_image(50, 50)  # Smaller images for batch test
                data.add_field('files', image_data, filename=f'test-image-{i}.jpg', content_type='image/jpeg')
            
            async with self.session.post(f"{self.base_url}/batch-upload", data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    console.print(f"[green]✅ Batch upload successful: {result}[/green]")
                    return result.get('job_ids', [])
                else:
                    error_text = await response.text()
                    console.print(f"[red]❌ Batch upload failed: {response.status} - {error_text}[/red]")
                    return []
        except Exception as e:
            console.print(f"[red]❌ Batch upload error: {str(e)}[/red]")
            return []
    
    async def run_comprehensive_test(self):
        """Run comprehensive pipeline test"""
        console.print(Panel.fit("[bold cyan]🧪 Image Processing Pipeline Test Suite[/bold cyan]"))
        
        test_results = {
            'health': False,
            'upload': False,
            'processing': False,
            'stats': False,
            'queue': False,
            'batch': False
        }
        
        # Test 1: Health check
        test_results['health'] = await self.test_health()
        if not test_results['health']:
            console.print("[red]❌ Pipeline is not healthy, stopping tests[/red]")
            return test_results
        
        # Test 2: Queue status
        test_results['queue'] = await self.test_queue_status()
        
        # Test 3: Stats
        test_results['stats'] = await self.test_stats()
        
        # Test 4: Single image upload and processing
        image_data = self.create_test_image()
        job_id = await self.test_upload(image_data)
        
        if job_id:
            test_results['upload'] = True
            test_results['processing'] = await self.test_job_status(job_id)
        else:
            test_results['upload'] = False
        
        # Test 5: Batch upload
        job_ids = await self.test_batch_upload()
        test_results['batch'] = len(job_ids) > 0
        
        # Final results
        console.print(Panel.fit("[bold cyan]📊 Test Results Summary[/bold cyan]"))
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            console.print(f"[{'green' if result else 'red'}]{test_name.upper()}: {status}[/{'green' if result else 'red'}]")
        
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        
        console.print(f"\n[bold]Overall: {passed_tests}/{total_tests} tests passed[/bold]")
        
        if passed_tests == total_tests:
            console.print("[green]🎉 All tests passed! Pipeline is working correctly.[/green]")
        else:
            console.print("[yellow]⚠️  Some tests failed. Check the pipeline configuration.[/yellow]")
        
        return test_results

async def main():
    """Main test function"""
    console.print("[bold cyan]🚀 Starting Image Processing Pipeline Tests[/bold cyan]")
    
    # Check if API is running
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/health") as response:
                if response.status != 200:
                    console.print("[red]❌ API server is not running. Please start the pipeline first.[/red]")
                    console.print("[yellow]Run: ./start.sh start[/yellow]")
                    return
    except Exception:
        console.print("[red]❌ Cannot connect to API server. Please start the pipeline first.[/red]")
        console.print("[yellow]Run: ./start.sh start[/yellow]")
        return
    
    # Run tests
    async with PipelineTester() as tester:
        await tester.run_comprehensive_test()

if __name__ == "__main__":
    asyncio.run(main()) 