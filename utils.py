import logging
import json
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from functools import wraps
from flask import request, jsonify
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('floodeck.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

class DataProcessingError(Exception):
    """Custom exception for data processing errors"""
    pass

def handle_exceptions(func):
    """Decorator to handle exceptions and return proper error responses"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {e}")
            return jsonify({
                'error': 'Validation Error',
                'message': str(e),
                'status': 'error'
            }), 400
        except DataProcessingError as e:
            logger.error(f"Data processing error in {func.__name__}: {e}")
            return jsonify({
                'error': 'Data Processing Error',
                'message': str(e),
                'status': 'error'
            }), 500
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}")
            logger.error(traceback.format_exc())
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred',
                'status': 'error'
            }), 500
    return wrapper

def validate_phone_number(phone_number: str) -> bool:
    """Validate phone number format"""
    if not phone_number:
        return False
    
    # Remove spaces and special characters
    cleaned = re.sub(r'[\s\-\(\)]', '', phone_number)
    
    # Check if it's a valid international format
    pattern = r'^\+?1?\d{9,15}$'
    return bool(re.match(pattern, cleaned))

def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_coordinates(latitude: str, longitude: str) -> bool:
    """Validate latitude and longitude coordinates"""
    try:
        lat = float(latitude)
        lon = float(longitude)
        
        # Check latitude range (-90 to 90)
        if not -90 <= lat <= 90:
            return False
        
        # Check longitude range (-180 to 180)
        if not -180 <= lon <= 180:
            return False
        
        return True
    except (ValueError, TypeError):
        return False

def validate_sensor_data(data: Dict[str, Any]) -> bool:
    """Validate sensor data format and values"""
    required_fields = ['water_post_code', 'created_at']
    
    # Check required fields
    for field in required_fields:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}")
    
    # Validate numeric values
    numeric_fields = ['temperature', 'humidity', 'water_height', 'raindrop']
    for field in numeric_fields:
        if field in data:
            try:
                value = float(data[field])
                if value < 0:
                    raise ValidationError(f"{field} cannot be negative")
            except (ValueError, TypeError):
                raise ValidationError(f"{field} must be a valid number")
    
    # Validate status values
    valid_statuses = ['SAFE', 'WARNING', 'DANGER', 'UNKNOWN']
    if 'status' in data and data['status'] not in valid_statuses:
        raise ValidationError(f"Invalid status value. Must be one of: {valid_statuses}")
    
    return True

def sanitize_input(data: Union[str, Dict, List]) -> Union[str, Dict, List]:
    """Sanitize user input to prevent injection attacks"""
    if isinstance(data, str):
        # Remove potentially dangerous characters
        return re.sub(r'[<>"\']', '', data)
    elif isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    else:
        return data

def format_datetime(dt: datetime) -> str:
    """Format datetime object to ISO string"""
    if dt is None:
        return None
    return dt.isoformat()

def parse_datetime(dt_string: str) -> Optional[datetime]:
    """Parse datetime string to datetime object"""
    if not dt_string:
        return None
    
    try:
        return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
    except ValueError:
        try:
            return datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            logger.warning(f"Unable to parse datetime string: {dt_string}")
            return None

def calculate_statistics(data: List[float]) -> Dict[str, float]:
    """Calculate basic statistics from a list of numbers"""
    if not data:
        return {
            'count': 0,
            'mean': 0,
            'min': 0,
            'max': 0,
            'std': 0
        }
    
    import statistics
    
    return {
        'count': len(data),
        'mean': statistics.mean(data),
        'min': min(data),
        'max': max(data),
        'std': statistics.stdev(data) if len(data) > 1 else 0
    }

def chunk_list(data: List, chunk_size: int) -> List[List]:
    """Split a list into chunks of specified size"""
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero"""
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except (TypeError, ValueError):
        return default

def log_request_info():
    """Log request information for debugging"""
    logger.info(f"Request: {request.method} {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")
    if request.json:
        logger.info(f"JSON Data: {json.dumps(request.json, indent=2)}")
    if request.form:
        logger.info(f"Form Data: {dict(request.form)}")

def log_response_info(response_data: Any):
    """Log response information for debugging"""
    if isinstance(response_data, dict):
        logger.info(f"Response: {json.dumps(response_data, indent=2)}")
    else:
        logger.info(f"Response: {response_data}")

class PerformanceMonitor:
    """Monitor function performance"""
    
    def __init__(self, name: str):
        self.name = name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        logger.debug(f"Starting {self.name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            logger.debug(f"Completed {self.name} in {duration:.3f}s")
            
            if duration > 1.0:  # Log slow operations
                logger.warning(f"Slow operation detected: {self.name} took {duration:.3f}s")

def monitor_performance(name: str = None):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor_name = name or f"{func.__module__}.{func.__name__}"
            with PerformanceMonitor(monitor_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator

def retry_on_failure(max_attempts: int = 3, delay: float = 1.0):
    """Decorator to retry function on failure"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        logger.error(f"Function {func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}")
                    time.sleep(delay * (2 ** attempt))  # Exponential backoff
            
        return wrapper
    return decorator

def cache_key_generator(*args, **kwargs) -> str:
    """Generate a cache key from function arguments"""
    import hashlib
    
    # Create a string representation of arguments
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
    key_string = "|".join(key_parts)
    
    # Create hash for consistent key length
    return hashlib.md5(key_string.encode()).hexdigest()

def validate_pagination_params(page: int, per_page: int, max_per_page: int = 100) -> tuple:
    """Validate and sanitize pagination parameters"""
    try:
        page = max(1, int(page))
        per_page = max(1, min(int(per_page), max_per_page))
        return page, per_page
    except (ValueError, TypeError):
        return 1, 10

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}" 