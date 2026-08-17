"""
FastAPI main application entry point.

Combines all routers and sets up middleware.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from database import init_db
from schemas import HealthCheckResponse, ErrorResponse
from routers import analysis, anomalies, database_api, auth, auto_resolution

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="UC10 Claims & Authorization Anomaly Monitor",
    description="REST API for anomaly detection and analysis",
    version="1.0.0",
)

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],  # Allow Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    logger.info("[STARTUP] Initializing database...")
    init_db()
    logger.info("[STARTUP] UC10 API started successfully")


@app.get("/api/health", response_model=HealthCheckResponse)
def health_check():
    """Health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        message="UC10 Anomaly Monitor API is running",
    )


# Include routers
app.include_router(auth.router)
app.include_router(auto_resolution.router)
app.include_router(analysis.router)
app.include_router(anomalies.router)
app.include_router(database_api.router)


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "message": str(exc.detail),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions."""
    logger.error(f"[ERROR] Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Check server logs.",
        },
    )


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting UC10 API server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
