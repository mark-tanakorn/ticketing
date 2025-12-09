"""
Observability Middleware

Provides logging and metrics middleware for FastAPI.
"""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
import time
import logging

logger = logging.getLogger(__name__)


class LoggingMiddleware:
    """
    Middleware for logging HTTP requests and responses.
    Uses raw ASGI to avoid buffering streaming responses.
    """
    
    def __init__(self, app: ASGIApp):
        self.app = app
    
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        ASGI middleware that logs requests without buffering streams.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Get request info
        method = scope["method"]
        path = scope["path"]
        
        # Check if this is an SSE stream endpoint
        is_sse_stream = "/stream" in path and method == "GET"
        
        # Log request
        logger.info(f"{method} {path}")
        
        if is_sse_stream:
            logger.info(f"{method} {path} - SSE stream starting, passing through without modification")
            # For SSE, pass through completely unmodified
            await self.app(scope, receive, send)
            logger.info(f"{method} {path} - SSE stream ended")
        else:
            # For regular requests, track timing
            start_time = time.time()
            
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    # Log completion when response starts
                    process_time = time.time() - start_time
                    logger.info(
                        f"{method} {path} "
                        f"completed in {process_time:.3f}s with status {message['status']}"
                    )
                await send(message)
            
            await self.app(scope, receive, send_wrapper)


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting metrics.
    
    TODO: Implement actual metrics collection (Prometheus, etc.)
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Collect request metrics.
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain
        
        Returns:
            Response from next handler
        """
        # TODO: Collect metrics (request count, latency, etc.)
        
        response = await call_next(request)
        
        return response
