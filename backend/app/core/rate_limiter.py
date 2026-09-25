import time
from typing import Dict, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding window in-memory rate limiter.
    Limits requests per IP address / Bearer token within a sliding 60-second window.
    Returns HTTP 429 Too Many Requests when threshold is exceeded.
    """
    _instance = None

    def __init__(self, app, requests_per_minute: int = 120, burst_limit: int = 20):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.history: Dict[str, list] = {}
        RateLimiterMiddleware._instance = self

    @classmethod
    def get_instance(cls):
        return cls._instance

    def reset(self):
        self.history.clear()

    def _get_client_key(self, request: Request) -> str:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return f"auth:{auth_header[7:25]}"
        
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        client_host = request.client.host if request.client else "127.0.0.1"
        return f"ip:{client_host}"

    async def dispatch(self, request: Request, call_next) -> Response:
        # Exempt health check and docs
        if request.url.path in ["/health", "/", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        now = time.time()
        client_key = self._get_client_key(request)

        window_start = now - 60.0
        
        timestamps = self.history.get(client_key, [])
        timestamps = [t for t in timestamps if t > window_start]
        
        if len(timestamps) >= self.requests_per_minute:
            retry_after = int(60.0 - (now - timestamps[0])) + 1
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Too many requests in this time window.",
                    "retry_after_seconds": max(retry_after, 1)
                }
            )
            response.headers["Retry-After"] = str(max(retry_after, 1))
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(int(now + retry_after))
            return response

        timestamps.append(now)
        self.history[client_key] = timestamps

        response = await call_next(request)
        
        remaining = max(0, self.requests_per_minute - len(timestamps))
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(now + 60))
        return response
