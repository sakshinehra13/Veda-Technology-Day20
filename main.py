import time
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from collections import defaultdict

app = FastAPI(title="Rate Limited API", version="1.0")

# Configuration for Rate Limiting
LIMIT = 2            
WINDOW_SIZE = 60     # Time window in seconds (1 minute)

# In-memory storage: mapping client_ip -> [list of request timestamps]
request_counts = defaultdict(list)

@app.middleware("http")
async def rate_limiter_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()
    
    window_start = current_time - WINDOW_SIZE
    
    # Filter out timestamps outside the current time window
    request_counts[client_ip] = [t for t in request_counts[client_ip] if t > window_start]
    
    # Check if limit is exceeded
    if len(request_counts[client_ip]) >= LIMIT:
        oldest_request = request_counts[client_ip][0]
        retry_after = int(WINDOW_SIZE - (current_time - oldest_request)) + 1
        
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Too Many Requests",
                "message": f"Rate limit exceeded. Maximum {LIMIT} requests allowed per {WINDOW_SIZE} seconds.",
                "retry_after_seconds": retry_after
            },
            headers={"Retry-After": str(retry_after)}
        )
    
    request_counts[client_ip].append(current_time)
    response = await call_next(request)
    return response

@app.get("/")
def read_root():
    return {"message": "Welcome to the Rate-Limited API!", "limit": LIMIT, "window_seconds": WINDOW_SIZE}

@app.get("/data")
def get_protected_data():
    return {"data": "This is secure, rate-limited data payload."}