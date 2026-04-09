from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from datetime import datetime

from .routes.flutter_api import router as flutter_router
from .routes.unity_ar_api import router as unity_router
from ..utils.config import config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Walmart AR Furniture Recommendation API",
    description="AI-powered furniture recommendations with AR visualization",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for AR assets (optional, for direct access)
app.mount("/static", StaticFiles(directory="data/ar_assets"), name="static")

# Include API routers
app.include_router(flutter_router, prefix="/api/v1", tags=["Flutter API"])
app.include_router(unity_router, prefix="/api/v1", tags=["Unity AR API"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Walmart AR Furniture Recommendation API",
        "version": "2.0.0",
        "status": "active",
        "endpoints": {
            "flutter_upload": "/api/v1/video-upload-and-process",
            "unity_recommendations": "/api/v1/ar-recommendations/{session_id}",
            "glb_download": "/api/v1/ar/glb-file/{item_id}"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
        "service": "walmart-ar-furniture-api",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",  # Pass as import string
        host=config['api']['host'],
        port=config['api']['port'],
        reload=config['api']['debug']
    )
