"""
Planning Engine API - Main Application Entry Point

This is the main FastAPI application that orchestrates all API routers.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import warnings
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress Pydantic serialization warnings for optional date fields
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic.type_adapter")

# Create FastAPI application
app = FastAPI(title="Planning Engine API")

# Add CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Local development
        "http://localhost:8080",
        "*",  # Allow all origins for internal deployment
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers
try:
    # Try relative imports first (for production/module mode)
    from .routers import auth_api, workspace_api, geocode_api, cluster_api
    from .routers import plan_api, result_api, teams_api, progress_api
except ImportError:
    # Fall back to absolute imports (for dev)
    from routers import auth_api, workspace_api, geocode_api, cluster_api
    from routers import plan_api, result_api, teams_api, progress_api

# Include all routers
app.include_router(auth_api.router)
app.include_router(workspace_api.router)
app.include_router(geocode_api.router)
app.include_router(cluster_api.router)
app.include_router(plan_api.router)
app.include_router(result_api.router)
app.include_router(teams_api.router)
app.include_router(progress_api.router)


@app.get("/")
def root():
    """Root endpoint - API health check"""
    return {
        "status": "ok",
        "message": "Planning Engine API is running",
        "version": "2.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}
