import logging
from typing import Optional
from functools import wraps
import time
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def log_execution_time(func):
    """Decorator to log function execution time"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(
                f"Function {func.__name__} executed in {execution_time:.2f} seconds"
            )
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Function {func.__name__} failed after {execution_time:.2f} seconds:  "
            )
            raise
    return wrapper

def log_mcp_request(method: str, params: Optional[dict] = None):
    """Decorator to log MCP requests"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger.info(f"MCP Request - Method: {method}")
            if params:
                logger.info(f"Parameters: {json.dumps(params, indent=2)}")
            try:
                result = await func(*args, **kwargs)
                logger.info(f"MCP Request successful - Method: {method}")
                return result
            except Exception as e:
                logger.error(f"MCP Request failed - Method: {method} - Error:  ")
                raise
        return wrapper
    return decorator