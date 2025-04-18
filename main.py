from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import JSONResponse
import httpx
import os
import logging
from typing import Optional

# Configure logging (basic)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

DOCLING_API_TOKEN = os.getenv("DOCLING_API_TOKEN")

DOCLING_SERVICE_NAME = os.getenv("DOCLING_SERVICE_NAME", "docling-serve-cpu")
DOCLING_SERVICE_PORT = os.getenv("DOCLING_SERVICE_PORT", "3000")

DOCLING_API_URL = os.getenv(
    "DOCLING_API_URL", 
    f"http://{DOCLING_SERVICE_NAME}.railway.internal:{DOCLING_SERVICE_PORT}"
)

EXCLUDED_PATHS = ["/health", "/docs", "/openapi.json"]

@app.middleware("http")
async def authenticate_request(request: Request, call_next):
    if request.url.path in EXCLUDED_PATHS:
        response = await call_next(request)
        return response

    if not DOCLING_API_TOKEN:
        print("CRITICAL: Proxy configuration error: DOCLING_API_TOKEN not set.") 
        return JSONResponse(
            status_code=503, 
            content={"detail": "Service unavailable: Configuration error"}
        )

    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return JSONResponse(
            status_code=401, 
            content={"detail": "Authorization header required"}
        )
    
    parts = auth_header.split(None, 1) # Split on first whitespace
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid Authorization header format. Expected 'Bearer <token>'"}
        )

    token = parts[1]
    if token != DOCLING_API_TOKEN:
        return JSONResponse(
            status_code=401, 
            content={"detail": "Invalid authorization token"}
        )
    
    response = await call_next(request)
    return response

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/convert/file")
async def proxy_convert_file(request: Request):
    content_type = request.headers.get("Content-Type", "")
    raw_body = await request.body()
    
    headers = {"Content-Type": content_type}
    
    target_url = f"{DOCLING_API_URL}/v1alpha/convert/file"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                target_url,
                content=raw_body,
                headers=headers,
                timeout=300.0
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        except Exception as e:
            # Log the specific error with traceback
            logger.error(f"Error communicating with Docling API at {target_url}:", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Error communicating with backend service"
            )
    
@app.post("/convert/source")
async def proxy_convert_source(request: Request):
    content_type = request.headers.get("Content-Type", "")
    raw_body = await request.body()
    
    headers = {"Content-Type": content_type}
    
    target_url = f"{DOCLING_API_URL}/v1alpha/convert/source"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                target_url,
                content=raw_body,
                headers=headers,
                timeout=300.0
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        except Exception as e:
            # Log the specific error with traceback
            logger.error(f"Error communicating with Docling API at {target_url}:", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Error communicating with backend service"
            )

@app.post("/convert/source/async")
async def proxy_convert_source_async(request: Request):
    """Proxies the asynchronous convert/source endpoint to Docling Serve"""
    content_type = request.headers.get("Content-Type", "")
    raw_body = await request.body()
    
    headers = {"Content-Type": content_type}
    
    target_url = f"{DOCLING_API_URL}/v1alpha/convert/source/async"
    logger.info(f"Forwarding async source conversion request to {target_url}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                target_url,
                content=raw_body,
                headers=headers,
                timeout=30.0  # Shorter timeout for async request initiation
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        except Exception as e:
            logger.error(f"Error communicating with Docling API at {target_url}:", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Error communicating with backend service"
            )

@app.get("/status/poll/{task_id}")
async def proxy_task_status(task_id: str, request: Request, wait: Optional[float] = 0.0):
    """Proxies the status polling endpoint to Docling Serve"""
    target_url = f"{DOCLING_API_URL}/v1alpha/status/poll/{task_id}"
    
    if wait > 0:
        target_url += f"?wait={wait}"
    
    logger.info(f"Polling task status from {target_url}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                target_url,
                timeout=max(wait + 5.0, 30.0)  # Add buffer to wait time
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        except Exception as e:
            logger.error(f"Error communicating with Docling API at {target_url}:", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Error communicating with backend service"
            )

@app.get("/result/{task_id}")
async def proxy_task_result(task_id: str, request: Request):
    """Proxies the task result endpoint to Docling Serve"""
    target_url = f"{DOCLING_API_URL}/v1alpha/result/{task_id}"
    logger.info(f"Fetching task result from {target_url}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                target_url,
                timeout=60.0
            )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
        except Exception as e:
            logger.error(f"Error communicating with Docling API at {target_url}:", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail="Error communicating with backend service"
            )