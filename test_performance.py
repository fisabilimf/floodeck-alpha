#!/usr/bin/env python3
"""
Performance Testing Script for Floodeck Alpha
Tests the optimized system against the original implementation
"""

import time
import requests
import statistics
import json
from datetime import datetime
from typing import List, Dict, Tuple
import concurrent.futures
import threading

class PerformanceTester:
    """Performance testing utility for Floodeck Alpha"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.results = {}
        
    def test_endpoint(self, endpoint: str, method: str = "GET", 
                     data: Dict = None, iterations: int = 100) -> Dict:
        """Test a single endpoint performance"""
        print(f"Testing {method} {endpoint} with {iterations} iterations...")
        
        response_times = []
        success_count = 0
        error_count = 0
        
        for i in range(iterations):
            try:
                start_time = time.time()
                
                if method == "GET":
                    response = requests.get(f"{self.base_url}{endpoint}")
                elif method == "POST":
                    response = requests.post(f"{self.base_url}{endpoint}", json=data)
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                if response.status_code == 200:
                    success_count += 1
                    response_times.append(response_time)
                else:
                    error_count += 1
                    print(f"Error {response.status_code} on iteration {i+1}")
                
            except Exception as e:
                error_count += 1
                print(f"Exception on iteration {i+1}: {e}")
            
            # Small delay to avoid overwhelming the server
            time.sleep(0.01)
        
        if response_times:
            stats = {
                'endpoint': endpoint,
                'method': method,
                'iterations': iterations,
                'success_count': success_count,
                'error_count': error_count,
                'success_rate': (success_count / iterations) * 100,
                'min_response_time': min(response_times),
                'max_response_time': max(response_times),
                'mean_response_time': statistics.mean(response_times),
                'median_response_time': statistics.median(response_times),
                'std_response_time': statistics.stdev(response_times) if len(response_times) > 1 else 0,
                'p95_response_time': sorted(response_times)[int(len(response_times) * 0.95)],
                'p99_response_time': sorted(response_times)[int(len(response_times) * 0.99)]
            }
        else:
            stats = {
                'endpoint': endpoint,
                'method': method,
                'iterations': iterations,
                'success_count': 0,
                'error_count': error_count,
                'success_rate': 0,
                'error': 'No successful responses'
            }
        
        return stats
    
    def test_concurrent_requests(self, endpoint: str, concurrent_users: int = 10, 
                                requests_per_user: int = 10) -> Dict:
        """Test concurrent request performance"""
        print(f"Testing {endpoint} with {concurrent_users} concurrent users, "
              f"{requests_per_user} requests each...")
        
        def make_requests(user_id: int) -> List[float]:
            response_times = []
            for i in range(requests_per_user):
                try:
                    start_time = time.time()
                    response = requests.get(f"{self.base_url}{endpoint}")
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        response_times.append((end_time - start_time) * 1000)
                except Exception as e:
                    print(f"User {user_id}, Request {i+1} failed: {e}")
            return response_times
        
        all_response_times = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(make_requests, i) for i in range(concurrent_users)]
            
            for future in concurrent.futures.as_completed(futures):
                response_times = future.result()
                all_response_times.extend(response_times)
        
        if all_response_times:
            stats = {
                'endpoint': endpoint,
                'concurrent_users': concurrent_users,
                'requests_per_user': requests_per_user,
                'total_requests': len(all_response_times),
                'min_response_time': min(all_response_times),
                'max_response_time': max(all_response_times),
                'mean_response_time': statistics.mean(all_response_times),
                'median_response_time': statistics.median(all_response_times),
                'std_response_time': statistics.stdev(all_response_times) if len(all_response_times) > 1 else 0,
                'p95_response_time': sorted(all_response_times)[int(len(all_response_times) * 0.95)],
                'p99_response_time': sorted(all_response_times)[int(len(all_response_times) * 0.99)],
                'requests_per_second': len(all_response_times) / (max(all_response_times) / 1000)
            }
        else:
            stats = {
                'endpoint': endpoint,
                'concurrent_users': concurrent_users,
                'requests_per_user': requests_per_user,
                'error': 'No successful responses'
            }
        
        return stats
    
    def test_database_performance(self) -> Dict:
        """Test database-related endpoints performance"""
        print("Testing database performance...")
        
        db_endpoints = [
            '/api/real-time',
            '/api/water-data',
            '/water-data',
            '/sensor-a-data',
            '/sensor-b-data'
        ]
        
        db_results = {}
        
        for endpoint in db_endpoints:
            result = self.test_endpoint(endpoint, iterations=50)
            db_results[endpoint] = result
        
        return db_results
    
    def test_cache_performance(self) -> Dict:
        """Test cache performance by making repeated requests"""
        print("Testing cache performance...")
        
        # Test real-time endpoint (should be cached)
        first_request = self.test_endpoint('/api/real-time', iterations=1)
        time.sleep(1)  # Wait for cache to be populated
        cached_requests = self.test_endpoint('/api/real-time', iterations=10)
        
        cache_performance = {
            'first_request_time': first_request['mean_response_time'],
            'cached_request_time': cached_requests['mean_response_time'],
            'cache_improvement': ((first_request['mean_response_time'] - cached_requests['mean_response_time']) 
                                / first_request['mean_response_time']) * 100
        }
        
        return cache_performance
    
    def test_health_endpoint(self) -> Dict:
        """Test health check endpoint"""
        print("Testing health endpoint...")
        
        health_result = self.test_endpoint('/health', iterations=20)
        
        # Test health endpoint response content
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                health_result['health_status'] = health_data.get('status', 'unknown')
                health_result['database_status'] = health_data.get('services', {}).get('database', {}).get('status', 'unknown')
            else:
                health_result['health_status'] = 'error'
        except Exception as e:
            health_result['health_status'] = f'error: {e}'
        
        return health_result
    
    def run_comprehensive_test(self) -> Dict:
        """Run comprehensive performance test suite"""
        print("Starting comprehensive performance test...")
        print("=" * 60)
        
        test_results = {
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url,
            'tests': {}
        }
        
        # Test health endpoint
        test_results['tests']['health'] = self.test_health_endpoint()
        
        # Test database performance
        test_results['tests']['database'] = self.test_database_performance()
        
        # Test cache performance
        test_results['tests']['cache'] = self.test_cache_performance()
        
        # Test concurrent requests
        test_results['tests']['concurrent'] = self.test_concurrent_requests('/api/real-time', 5, 10)
        
        # Test individual endpoints
        individual_endpoints = [
            '/',
            '/water-data',
            '/sensor-a-data',
            '/sensor-b-data',
            '/analytics'
        ]
        
        test_results['tests']['individual'] = {}
        for endpoint in individual_endpoints:
            test_results['tests']['individual'][endpoint] = self.test_endpoint(endpoint, iterations=20)
        
        return test_results
    
    def generate_report(self, results: Dict) -> str:
        """Generate a human-readable performance report"""
        report = []
        report.append("=" * 60)
        report.append("FLOODECK ALPHA PERFORMANCE TEST REPORT")
        report.append("=" * 60)
        report.append(f"Test Date: {results['timestamp']}")
        report.append(f"Base URL: {results['base_url']}")
        report.append("")
        
        # Health Status
        health = results['tests']['health']
        report.append("HEALTH STATUS:")
        report.append(f"  Status: {health.get('health_status', 'unknown')}")
        report.append(f"  Database: {health.get('database_status', 'unknown')}")
        report.append(f"  Response Time: {health.get('mean_response_time', 0):.2f}ms")
        report.append("")
        
        # Cache Performance
        cache = results['tests']['cache']
        report.append("CACHE PERFORMANCE:")
        report.append(f"  First Request: {cache.get('first_request_time', 0):.2f}ms")
        report.append(f"  Cached Request: {cache.get('cached_request_time', 0):.2f}ms")
        report.append(f"  Improvement: {cache.get('cache_improvement', 0):.1f}%")
        report.append("")
        
        # Database Performance
        report.append("DATABASE PERFORMANCE:")
        db_results = results['tests']['database']
        for endpoint, stats in db_results.items():
            report.append(f"  {endpoint}:")
            report.append(f"    Mean: {stats.get('mean_response_time', 0):.2f}ms")
            report.append(f"    P95: {stats.get('p95_response_time', 0):.2f}ms")
            report.append(f"    Success Rate: {stats.get('success_rate', 0):.1f}%")
        report.append("")
        
        # Concurrent Performance
        concurrent = results['tests']['concurrent']
        report.append("CONCURRENT PERFORMANCE:")
        report.append(f"  Endpoint: {concurrent.get('endpoint', 'N/A')}")
        report.append(f"  Users: {concurrent.get('concurrent_users', 0)}")
        report.append(f"  Mean Response: {concurrent.get('mean_response_time', 0):.2f}ms")
        report.append(f"  Requests/Second: {concurrent.get('requests_per_second', 0):.1f}")
        report.append("")
        
        # Individual Endpoints
        report.append("INDIVIDUAL ENDPOINTS:")
        individual = results['tests']['individual']
        for endpoint, stats in individual.items():
            report.append(f"  {endpoint}: {stats.get('mean_response_time', 0):.2f}ms")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def save_results(self, results: Dict, filename: str = None):
        """Save test results to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"performance_test_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Results saved to {filename}")
        
        # Generate and save report
        report_filename = filename.replace('.json', '_report.txt')
        report = self.generate_report(results)
        
        with open(report_filename, 'w') as f:
            f.write(report)
        
        print(f"Report saved to {report_filename}")

def main():
    """Main function to run performance tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Performance Testing for Floodeck Alpha')
    parser.add_argument('--url', default='http://localhost:5000', 
                       help='Base URL of the application')
    parser.add_argument('--output', help='Output filename for results')
    parser.add_argument('--quick', action='store_true', 
                       help='Run quick test with fewer iterations')
    
    args = parser.parse_args()
    
    # Create tester
    tester = PerformanceTester(args.url)
    
    # Run tests
    if args.quick:
        print("Running quick performance test...")
        results = {
            'timestamp': datetime.now().isoformat(),
            'base_url': args.url,
            'tests': {
                'health': tester.test_health_endpoint(),
                'cache': tester.test_cache_performance(),
                'database': tester.test_endpoint('/api/real-time', iterations=20)
            }
        }
    else:
        results = tester.run_comprehensive_test()
    
    # Save results
    tester.save_results(results, args.output)
    
    # Print summary
    print("\n" + "=" * 60)
    print("PERFORMANCE TEST SUMMARY")
    print("=" * 60)
    
    if 'health' in results['tests']:
        health = results['tests']['health']
        print(f"Health Status: {health.get('health_status', 'unknown')}")
    
    if 'cache' in results['tests']:
        cache = results['tests']['cache']
        print(f"Cache Improvement: {cache.get('cache_improvement', 0):.1f}%")
    
    if 'database' in results['tests']:
        if isinstance(results['tests']['database'], dict):
            for endpoint, stats in results['tests']['database'].items():
                print(f"{endpoint}: {stats.get('mean_response_time', 0):.2f}ms")
        else:
            db_test = results['tests']['database']
            print(f"Database Test: {db_test.get('mean_response_time', 0):.2f}ms")

if __name__ == "__main__":
    main() 