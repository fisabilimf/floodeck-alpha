from flask_caching import Cache
from functools import wraps
import hashlib
import json
from typing import Any, Callable

# Initialize cache
cache = Cache(config={
    'CACHE_TYPE': 'simple',  # Can be changed to 'redis' or 'memcached' for production
    'CACHE_DEFAULT_TIMEOUT': 300,
    'CACHE_KEY_PREFIX': 'floodeck_'
})

def cache_key_generator(*args, **kwargs) -> str:
    """Generate cache key from function arguments"""
    # Create a string representation of arguments
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
    key_string = "|".join(key_parts)
    
    # Create hash for consistent key length
    return hashlib.md5(key_string.encode()).hexdigest()

def cached_response(timeout: int = 300, key_prefix: str = None):
    """Decorator for caching function responses"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_prefix:
                cache_key = f"{key_prefix}:{cache_key_generator(*args, **kwargs)}"
            else:
                cache_key = f"{func.__name__}:{cache_key_generator(*args, **kwargs)}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout=timeout)
            return result
        
        return wrapper
    return decorator

def invalidate_cache_pattern(pattern: str):
    """Invalidate cache entries matching a pattern"""
    # Note: This is a simplified version. In production with Redis,
    # you would use SCAN and DEL commands
    pass

class CacheManager:
    """Cache management utility class"""
    
    @staticmethod
    def clear_all():
        """Clear all cache entries"""
        cache.clear()
    
    @staticmethod
    def get_cache_info() -> dict:
        """Get cache statistics"""
        # This would return actual cache stats in production
        return {
            'cache_type': cache.config.get('CACHE_TYPE', 'unknown'),
            'default_timeout': cache.config.get('CACHE_DEFAULT_TIMEOUT', 300)
        }
    
    @staticmethod
    def cache_sensor_data(sensor_type: str, post_code: str, data: dict, timeout: int = 60):
        """Cache sensor data with specific key"""
        cache_key = f"sensor_{sensor_type}_{post_code}"
        cache.set(cache_key, data, timeout=timeout)
    
    @staticmethod
    def get_cached_sensor_data(sensor_type: str, post_code: str) -> dict:
        """Get cached sensor data"""
        cache_key = f"sensor_{sensor_type}_{post_code}"
        return cache.get(cache_key)
    
    @staticmethod
    def cache_water_data(post_code: str, data: dict, timeout: int = 60):
        """Cache water data"""
        cache_key = f"water_data_{post_code}"
        cache.set(cache_key, data, timeout=timeout)
    
    @staticmethod
    def get_cached_water_data(post_code: str) -> dict:
        """Get cached water data"""
        cache_key = f"water_data_{post_code}"
        return cache.get(cache_key)
    
    @staticmethod
    def cache_forecasting_data(post_code: str, data: dict, timeout: int = 60):
        """Cache forecasting data"""
        cache_key = f"forecasting_{post_code}"
        cache.set(cache_key, data, timeout=timeout)
    
    @staticmethod
    def get_cached_forecasting_data(post_code: str) -> dict:
        """Get cached forecasting data"""
        cache_key = f"forecasting_{post_code}"
        return cache.get(cache_key)
    
    @staticmethod
    def invalidate_sensor_cache(sensor_type: str = None, post_code: str = None):
        """Invalidate sensor cache"""
        if sensor_type and post_code:
            cache_key = f"sensor_{sensor_type}_{post_code}"
            cache.delete(cache_key)
        elif sensor_type:
            # In production, you would use pattern matching
            pass
    
    @staticmethod
    def invalidate_water_cache(post_code: str = None):
        """Invalidate water data cache"""
        if post_code:
            cache_key = f"water_data_{post_code}"
            cache.delete(cache_key)
    
    @staticmethod
    def invalidate_forecasting_cache(post_code: str = None):
        """Invalidate forecasting cache"""
        if post_code:
            cache_key = f"forecasting_{post_code}"
            cache.delete(cache_key) 