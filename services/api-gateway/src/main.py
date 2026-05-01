import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncpg

from auth import get_current_user, refresh_access_token
from rate_limiter import rate_limit_middleware


API_GATEWAY_PORT = int(os.getenv("API_GATEWAY_PORT", "8080"))
CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:5005")
MODEL_SERVER_URL = os.getenv("MODEL_SERVER_REST_URL", "http://model-server:8501")
DRIFT_MONITOR_URL = os.getenv("DRIFT_MONITOR_URL", "http://drift-monitor:8502")
IRRIGATION_CONTROLLER_URL = os.getenv("IRRIGATION_CONTROLLER_URL", "http://irrigation-controller:8503")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8505")
WEB_DASHBOARD_URL = os.getenv("WEB_DASHBOARD_URL", "http://web-dashboard:3000")


app = FastAPI(title="API Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/auth/refresh")
async def refresh_token_endpoint(request: Request):
    try:
        data = await request.json()
        refresh_token_str = data.get("refresh_token")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request body",
        )

    if not refresh_token_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing refresh_token",
        )

    access, refresh = await refresh_access_token(refresh_token_str)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
    }


@app.middleware("http")
async def gateway_rate_limit(request: Request, call_next):
    if os.getenv("ENV") == "testing":
        return await call_next(request)
    await rate_limit_middleware(request, call_next)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "api-gateway"}


@app.get("/")
async def root():
    return {"message": "Smart Irrigation API Gateway", "version": "1.0.0"}


ROUTES = {
    "/auth": USER_SERVICE_URL,
    "/users": USER_SERVICE_URL,
    "/v1/sensors": MODEL_SERVER_URL,
    "/v1/predictions": MODEL_SERVER_URL,
    "/v1/zones": USER_SERVICE_URL,
    "/v1/drift": DRIFT_MONITOR_URL,
    "/v1/irrigation": IRRIGATION_CONTROLLER_URL,
    "/v1/notifications": NOTIFICATION_SERVICE_URL,
    "/dashboard": WEB_DASHBOARD_URL,
}


def get_upstream_url(path: str) -> Optional[tuple[str, str]]:
    for route_prefix, upstream in ROUTES.items():
        if path.startswith(route_prefix):
            return upstream, path
    return None


async def proxy_request(
    request: Request,
    upstream_url: str,
    path: str,
    require_auth: bool = False,
):
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    headers = dict(request.headers)
    headers["X-Forwarded-For"] = client_ip
    headers["X-Original-Path"] = path

    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            upstream_path = f"{upstream_url.rstrip('/')}{path}"
            
            response = await client.request(
                method=request.method,
                url=upstream_path,
                headers=headers,
                content=body,
                params=request.query_params,
            )

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type", "application/json"),
            )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream service error: {str(e)}",
        )


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def gateway_proxy(request: Request, path: str):
    if path == "health":
        return {"status": "healthy", "service": "api-gateway"}
    if path == "" or path == "/":
        return {"message": "Smart Irrigation API Gateway", "version": "1.0.0"}

    require_auth = False
    if path.startswith(("auth/", "users/", "v1/zones/", "v1/irrigation/", "v1/notifications/")):
        require_auth = True
    
    if path.startswith("v1/zones/") and request.method in ["PUT", "DELETE"]:
        zone_id = path.split("/")[-1] if len(path.split("/")) > 2 else None
        if zone_id and zone_id.isdigit():
            await validate_zone_ownership(request, zone_id)

    result = get_upstream_url(f"/{path}")
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Route not found",
        )

    upstream_url, _ = result
    return await proxy_request(request, upstream_url, f"/{path}", require_auth)


async def validate_zone_ownership(request: Request, zone_id: str):
    try:
        user_payload = await get_current_user_payload(request)
    except HTTPException:
        raise

    # Extract user_id and is_admin from payload
    user_id = user_payload.get("sub")
    is_admin = user_payload.get("is_admin", False)

    if is_admin:
        return # Admin can do anything

    db_url = os.getenv("DATABASE_URL", "postgresql://irrigation_user:changeme@timescaledb:5432/irrigation_db")
    
    try:
        # Use simpler connection logic if possible, or keep existing for robustness
        conn = await asyncpg.connect(dsn=db_url)
        row = await conn.fetchrow(
            "SELECT owner_id, source FROM zones WHERE zone_id = $1",
            zone_id,
        )
        await conn.close()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Zone not found",
            )

        if row["source"] == "yaml":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="YAML-defined zones are read-only",
            )

        if not row["owner_id"] or str(row["owner_id"]) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this zone",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate zone ownership: {str(e)}",
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=API_GATEWAY_PORT)