import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const successRate = new Rate('success');

// Test configuration
export const options = {
  stages: [
    // Ramp up to 30 requests per second over 2 minutes
    { duration: '2m', target: 30 },
    // Stay at 30 requests per second for 5 minutes
    { duration: '5m', target: 30 },
    // Ramp up to 50 requests per second over 2 minutes
    { duration: '2m', target: 50 },
    // Stay at 50 requests per second for 3 minutes
    { duration: '3m', target: 50 },
    // Ramp down to 0 over 1 minute
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<5000'], // 95% of requests should be below 5s
    http_req_failed: ['rate<0.1'],     // Error rate should be below 10%
    'http_req_duration{status:200}': ['p(95)<3000'], // Successful requests should be below 3s
  },
};

// Test data - base64 encoded small test image
const testImageBase64 = '/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k=';

export default function () {
  const url = __ENV.API_URL || 'http://localhost:8000';
  
  // Test 1: Health check
  const healthResponse = http.get(`${url}/health`);
  check(healthResponse, {
    'health check status is 200': (r) => r.status === 200,
    'health check response time < 500ms': (r) => r.timings.duration < 500,
  });
  
  // Test 2: Upload image
  const payload = {
    file: http.file(testImageBase64, 'test-image.jpg', 'image/jpeg'),
  };
  
  const uploadResponse = http.post(`${url}/upload`, payload, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  const uploadCheck = check(uploadResponse, {
    'upload status is 200': (r) => r.status === 200,
    'upload response has job_id': (r) => r.json('job_id') !== undefined,
    'upload response time < 2000ms': (r) => r.timings.duration < 2000,
  });
  
  if (uploadCheck) {
    successRate.add(1);
    const jobId = uploadResponse.json('job_id');
    
    // Test 3: Check job status (with retry)
    let statusResponse;
    let attempts = 0;
    const maxAttempts = 10;
    
    while (attempts < maxAttempts) {
      statusResponse = http.get(`${url}/status/${jobId}`);
      
      const statusCheck = check(statusResponse, {
        'status check is 200': (r) => r.status === 200,
        'status response has status field': (r) => r.json('status') !== undefined,
      });
      
      if (statusCheck && statusResponse.json('status') === 'completed') {
        break;
      }
      
      attempts++;
      sleep(2); // Wait 2 seconds before retry
    }
    
    check(statusResponse, {
      'job completed within 10 attempts': (r) => attempts < maxAttempts,
      'final status is completed': (r) => r.json('status') === 'completed',
      'status check response time < 1000ms': (r) => r.timings.duration < 1000,
    });
    
  } else {
    errorRate.add(1);
  }
  
  // Test 4: Get pipeline stats
  const statsResponse = http.get(`${url}/stats`);
  check(statsResponse, {
    'stats status is 200': (r) => r.status === 200,
    'stats response time < 1000ms': (r) => r.timings.duration < 1000,
  });
  
  // Test 5: Get queue status
  const queueResponse = http.get(`${url}/queue-status`);
  check(queueResponse, {
    'queue status is 200': (r) => r.status === 200,
    'queue response time < 500ms': (r) => r.timings.duration < 500,
  });
  
  // Random sleep between requests (1-3 seconds)
  sleep(Math.random() * 2 + 1);
}

// Setup function (runs once before the test)
export function setup() {
  const url = __ENV.API_URL || 'http://localhost:8000';
  
  // Verify API is running
  const healthResponse = http.get(`${url}/health`);
  if (healthResponse.status !== 200) {
    throw new Error('API server is not responding');
  }
  
  console.log('Load test setup completed');
}

// Teardown function (runs once after the test)
export function teardown(data) {
  console.log('Load test completed');
}

// Handle summary
export function handleSummary(data) {
  console.log('Test Results:');
  console.log(`- Total requests: ${data.metrics.http_reqs.values.count}`);
  console.log(`- Success rate: ${(successRate.values.rate * 100).toFixed(2)}%`);
  console.log(`- Error rate: ${(errorRate.values.rate * 100).toFixed(2)}%`);
  console.log(`- Average response time: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms`);
  console.log(`- 95th percentile: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms`);
  
  return {
    'load-test-results.json': JSON.stringify(data, null, 2),
  };
} 