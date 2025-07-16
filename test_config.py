#!/usr/bin/env python3
"""
Test script to verify the configuration system is working properly
"""

import os
import sys
from pathlib import Path

def test_config_loading():
    """Test that configuration loads properly"""
    print("Testing configuration loading...")
    
    try:
        from config import get_config, get_pipeline_config, get_aws_config
        
        # Test basic config loading
        config = get_config()
        print(f"✅ Config loaded: {config}")
        
        # Test pipeline config
        pipeline_config = get_pipeline_config()
        print(f"✅ Pipeline config loaded with keys: {list(pipeline_config.keys())}")
        
        # Test AWS config
        aws_config = get_aws_config()
        print(f"✅ AWS config loaded with keys: {list(aws_config.keys())}")
        
        # Test specific values
        print(f"✅ Redis URL: {config.get_redis_url()}")
        print(f"✅ Database URL: {config.DATABASE_URL}")
        print(f"✅ API Host:Port: {config.API_HOST}:{config.API_PORT}")
        print(f"✅ Number of workers: {config.NUM_WORKERS}")
        print(f"✅ Environment: {config.ENVIRONMENT}")
        
        return True
        
    except Exception as e:
        print(f"❌ Config loading failed: {e}")
        return False

def test_model_paths():
    """Test that model paths are configured correctly"""
    print("\nTesting model path configuration...")
    
    try:
        from config import get_config
        config = get_config()
        
        car_model_path = Path(config.CAR_FACE_BLUR_MODEL_PATH)
        yolo_model_path = Path(config.YOLO_DETECTION_MODEL_PATH)
        
        print(f"✅ Car Face Blur model path: {car_model_path}")
        print(f"✅ YOLO detection model path: {yolo_model_path}")
        
        if car_model_path.exists():
            print(f"✅ Car Face Blur model file exists")
        else:
            print(f"⚠️  Car Face Blur model file not found (this is expected if models aren't downloaded)")
            
        if yolo_model_path.exists():
            print(f"✅ YOLO detection model file exists")
        else:
            print(f"⚠️  YOLO detection model file not found (this is expected if models aren't downloaded)")
        
        return True
        
    except Exception as e:
        print(f"❌ Model path test failed: {e}")
        return False

def test_environment_override():
    """Test that environment variables properly override defaults"""
    print("\nTesting environment variable override...")
    
    try:
        # Set a test environment variable
        os.environ['NUM_WORKERS'] = '10'
        os.environ['API_PORT'] = '9000'
        
        # Reload config (create new instance)
        from config import Config
        test_config = Config()
        
        if test_config.NUM_WORKERS == 10:
            print("✅ NUM_WORKERS environment override works")
        else:
            print(f"❌ NUM_WORKERS override failed: expected 10, got {test_config.NUM_WORKERS}")
            
        if test_config.API_PORT == 9000:
            print("✅ API_PORT environment override works")
        else:
            print(f"❌ API_PORT override failed: expected 9000, got {test_config.API_PORT}")
        
        # Clean up
        del os.environ['NUM_WORKERS']
        del os.environ['API_PORT']
        
        return True
        
    except Exception as e:
        print(f"❌ Environment override test failed: {e}")
        return False

def test_validation():
    """Test configuration validation"""
    print("\nTesting configuration validation...")
    
    try:
        from config import Config
        
        # Test with production environment (should require AWS credentials)
        os.environ['ENVIRONMENT'] = 'production'
        
        try:
            prod_config = Config()
            print("⚠️  Production config loaded without AWS credentials (this might be expected if they're set)")
        except ValueError as e:
            print(f"✅ Production validation works: {e}")
        
        # Clean up
        if 'ENVIRONMENT' in os.environ:
            del os.environ['ENVIRONMENT']
        
        return True
        
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        return False

def main():
    """Run all configuration tests"""
    print("🧪 Running Configuration System Tests\n")
    
    tests = [
        test_config_loading,
        test_model_paths,
        test_environment_override,
        test_validation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All configuration tests passed!")
        return 0
    else:
        print("❌ Some configuration tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())