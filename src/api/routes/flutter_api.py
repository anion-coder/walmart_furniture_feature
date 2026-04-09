from fastapi import APIRouter, File, UploadFile, Form, HTTPException
import tempfile
import uuid
import os
from datetime import datetime
from typing import List, Dict, Any
from ...services.background_processor import BackgroundProcessor
from ...utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()

# Initialize background processor
background_processor = BackgroundProcessor()


import asyncio

@router.get("/product-packages/{session_id}")
async def get_product_packages(session_id: str):
    """
    Flutter app pulls ONLY the product-package recommendations
    (no .glb links, no placement metadata).
    This version waits until processing is complete (or fails).
    """
    try:
        # Max wait time and polling interval (adjustable)
        max_wait_seconds = 90
        poll_interval = 2
        waited = 0

        while waited < max_wait_seconds:
            data = background_processor.db_manager.get_session_recommendations(session_id)

            if data:
                flutter_response = _format_flutter_packages(data)
                flutter_response["success"] = True
                flutter_response["session_id"] = session_id
                return flutter_response

            status = await background_processor.get_processing_status(session_id)
            if status.get("status") == "failed":
                return {
                    "success": False,
                    "status": "failed",
                    "error": status.get("error", "Processing failed")
                }

            if status.get("status") == "not_found":
                raise HTTPException(status_code=404, detail="Session not found")

            await asyncio.sleep(poll_interval)
            waited += poll_interval

        # If timeout
        return {
            "success": False,
            "status": "timeout",
            "message": "Processing is taking longer than expected. Please try again later."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Flutter packages API error for {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))



def _format_flutter_packages(recommendations: Dict[str, Any]) -> Dict[str, Any]:
    """
    Keep only package-level and product-level commercial data
    (id, name, price, category, thumbnail).
    """
    output: Dict[str, Any] = {"packages": []}

    for pkg in recommendations.get("furniture_packages", []):
        clean_pkg = {
            "package_id": pkg.get("package_id", ""),
            "package_name": pkg.get("package_name", ""),
            "style_description": pkg.get("style_description", ""),
            "total_cost": pkg.get("total_cost", 0),
            "products": []
        }

        for itm in pkg.get("items", []):
            clean_pkg["products"].append({
                "item_id": itm["item_id"],
                "name": itm["name"],
                "category": itm["category"],
                "price": itm["price"],
                "thumbnail_url": itm["thumbnail_url"]
            })

        # only include packages that still have products
        if clean_pkg["products"]:
            output["packages"].append(clean_pkg)

    output["total_items"] = sum(len(p["products"]) for p in output["packages"])
    return output

@router.post("/video-upload-and-process")
async def process_room_video_flutter(
    video: UploadFile = File(...),
    user_preferences: str = Form(...),
    user_id: str = Form(...),
    session_id: str = Form(None)
):
    """
    Flutter app uploads video and receives processing confirmation
    """
    
    try:
        # Validate video file
        if not video.filename.lower().endswith(('.mp4', '.mov', '.avi')):
            raise HTTPException(status_code=400, detail="Invalid video format. Use MP4, MOV, or AVI")
        
        # Check file size (100MB limit)
        if video.size and video.size > 100 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Video file too large. Maximum size is 100MB")
        
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Save video temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            content = await video.read()
            tmp_file.write(content)
            video_path = tmp_file.name
        
        # Start background processing
        task_id = await background_processor.start_processing_task(
            video_path=video_path,
            user_preferences=user_preferences,
            session_id=session_id,
            user_id=user_id
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "task_id": task_id,
            "message": "Video uploaded successfully. AI processing started.",
            "estimated_completion": "60-90 seconds",
            "unity_endpoint": f"/api/v1/ar-recommendations/{session_id}",
            "status_endpoint": f"/api/v1/processing-status/{session_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Video upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/processing-status/{session_id}")
async def check_processing_status(session_id: str):
    """
    Check if video processing is complete
    """
    
    try:
        status = await background_processor.get_processing_status(session_id)
        
        if status.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session_id,
            "status": status.get("status", "unknown"),
            "progress": status.get("progress", 0),
            "message": status.get("message", ""),
            "error": status.get("error"),
            "estimated_remaining": status.get("estimated_remaining", "Unknown")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Status check failed for {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/cancel-processing/{session_id}")
async def cancel_processing(session_id: str):
    """
    Cancel ongoing processing (if possible)
    """
    
    try:
        # Update status to cancelled
        background_processor.db_manager.update_session_status(session_id, "cancelled")
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "Processing cancellation requested"
        }
        
    except Exception as e:
        logger.error(f"Cancellation failed for {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
