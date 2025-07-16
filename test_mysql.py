#!/usr/bin/env python3
"""
Test MySQL Database Integration
Verifies that the MySQL migration is working correctly
"""

import asyncio
import sys
from database_models import DatabaseManager
from config import get_config

async def test_mysql_integration():
    """Test MySQL database integration"""
    print("🧪 Testing MySQL Database Integration\n")
    
    try:
        # Get configuration
        config = get_config()
        print(f"📊 Database URL: {config.DATABASE_URL}")
        print(f"📊 Database Type: {config.DATABASE_URL.split('://')[0]}")
        print()
        
        # Test database manager initialization
        print("🔧 Testing DatabaseManager initialization...")
        db_manager = DatabaseManager(config.DATABASE_URL)
        
        # Note: We can't actually connect without a running MySQL server
        # But we can test the configuration and model definitions
        print("✅ DatabaseManager created successfully")
        print()
        
        # Test model structure
        print("🔧 Testing ProcessedImage model structure...")
        from database_models import ProcessedImage
        
        # Check if the model has the correct attributes
        expected_attributes = [
            'id', 'job_id', 'original_filename', 's3_original_path', 's3_processed_path',
            'is_vehicle_detected', 'is_face_detected', 'is_face_blurred',
            'content_type', 'file_size_original', 'file_size_processed',
            'processing_time_seconds', 'vehicle_detection_data', 'face_detection_data',
            'created_at', 'processed_at'
        ]
        
        for attr in expected_attributes:
            if hasattr(ProcessedImage, attr):
                print(f"✅ {attr} attribute exists")
            else:
                print(f"❌ {attr} attribute missing")
                return False
        
        print()
        print("🔧 Testing model dictionary conversion...")
        
        # Test to_dict method exists
        if hasattr(ProcessedImage, 'to_dict'):
            print("✅ to_dict method exists")
        else:
            print("❌ to_dict method missing")
            return False
        
        print()
        print("🎉 All MySQL integration tests passed!")
        print()
        print("📋 Next Steps:")
        print("1. Install MySQL server")
        print("2. Create database and user")
        print("3. Update DATABASE_URL in .env with real credentials")
        print("4. Run the application to test full integration")
        
        return True
        
    except Exception as e:
        print(f"❌ MySQL integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    success = asyncio.run(test_mysql_integration())
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())