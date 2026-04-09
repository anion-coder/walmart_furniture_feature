from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
from typing import List, Dict, Any

from ...services.prototype_ar_service import PrototypeARService
from ...services.background_processor import BackgroundProcessor
from ...utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter()

# Initialize services
ar_service = PrototypeARService()
background_processor = BackgroundProcessor()

@router.get("/ar-recommendations/{session_id}")
async def get_ar_recommendations_unity(session_id: str):
    """
    Unity app gets complete recommendations with .glb file URLs
    """
    
    try:
        # Get processed recommendations
        recommendations = background_processor.db_manager.get_session_recommendations(session_id)
        
        if not recommendations:
            # Check if still processing
            status = await background_processor.get_processing_status(session_id)
            
            if status.get("status") == "processing":
                return {
                    "success": False,
                    "status": "processing",
                    "progress": status.get("progress", 0),
                    "message": "Recommendations not yet ready"
                }
            elif status.get("status") == "failed":
                return {
                    "success": False,
                    "status": "failed",
                    "error": status.get("error", "Processing failed")
                }
            else:
                raise HTTPException(status_code=404, detail="Session not found")
        
        # Format for Unity consumption
        unity_response = await _format_unity_response(session_id, recommendations)
        
        return unity_response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unity API error for session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ar/glb-file/{item_id}")
async def download_glb_file(item_id: str):
    """
    Unity downloads .glb file via GET request
    """
    
    try:
        glb_path = ar_service.get_glb_file_path(item_id)
        
        if not glb_path or not os.path.exists(glb_path):
            raise HTTPException(status_code=404, detail="3D model not found")
        
        return FileResponse(
            path=glb_path,
            media_type="model/gltf-binary",
            filename=f"{item_id}.glb",
            headers={
                "Content-Disposition": f"attachment; filename={item_id}.glb",
                "Cache-Control": "public, max-age=3600",
                "Content-Length": str(os.path.getsize(glb_path))
            }
        )
    except Exception as e:
        logger.error(f"GLB file download error for {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ar/thumbnail/{item_id}")
async def download_thumbnail(item_id: str):
    """
    Unity downloads thumbnail image
    """
    
    try:
        thumbnail_path = ar_service.get_thumbnail_path(item_id)
        
        if not thumbnail_path or not os.path.exists(thumbnail_path):
            raise HTTPException(status_code=404, detail="Thumbnail not found")
        
        return FileResponse(
            path=thumbnail_path,
            media_type="image/jpeg",
            filename=f"{item_id}.jpg"
        )
    except Exception as e:
        logger.error(f"Thumbnail download error for {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ar/glb-info/{item_id}")
async def get_glb_file_info(item_id: str):
    """
    Get .glb file metadata without downloading
    """
    
    try:
        asset_info = ar_service.get_ar_asset(item_id)
        
        if not asset_info:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        return {
            "item_id": item_id,
            "file_size": asset_info.get("file_size", 0),
            "download_url": f"/api/v1/ar/glb-file/{item_id}",
            "thumbnail_url": f"/api/v1/ar/thumbnail/{item_id}",
            "placement_type": asset_info.get("placement_type", ""),
            "available": True
        }
    except Exception as e:
        logger.error(f"GLB info error for {item_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ar/assets")
async def list_ar_assets():
    """
    List all available AR assets
    """
    
    try:
        assets = ar_service.list_available_assets()
        
        return {
            "available_assets": assets,
            "total_count": len(assets)
        }
    except Exception as e:
        logger.error(f"List AR assets error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def _validate_item_structure(item: Dict[str, Any]) -> bool:
    """Validate that item has required structure for Unity processing"""
    required_fields = ["item_id", "name", "category", "price"]
    
    # Check basic fields
    if not all(field in item for field in required_fields):
        missing_fields = [field for field in required_fields if field not in item]
        logger.warning(f"Missing required fields for item {item.get('item_id', 'unknown')}: {missing_fields}")
        return False
    
    return True

async def _format_unity_response(session_id: str, recommendations: Dict[str, Any]) -> Dict[str, Any]:
    """Format recommendations for Unity consumption with robust error handling"""
    
    unity_response = {
        "success": True,
        "session_id": session_id,
        "room_analysis": recommendations.get("room_analysis", {}),
        "furniture_packages": [],
        "total_items": 0,
        "processing_warnings": []
    }
    
    logger.info(f"Processing Unity response for session {session_id}")
    
    # Process each furniture package
    for package in recommendations.get("furniture_packages", []):
        package_id = package.get("package_id", "")
        logger.info(f"Processing package {package_id} with {len(package.get('items', []))} items")
        
        unity_package = {
            "package_id": package_id,
            "package_name": package.get("package_name", ""),
            "style_description": package.get("style_description", ""),
            "total_cost": package.get("total_cost", 0),
            "items": []
        }
        
        # Process each furniture item
        for item in package.get("items", []):
            item_id = item.get("item_id", "")
            logger.debug(f"Processing item {item_id}: {item.get('name', 'unnamed')}")
            
            # Validate item structure
            if not _validate_item_structure(item):
                unity_response["processing_warnings"].append(f"Skipped item {item_id} due to missing required fields")
                continue
            
            # Try to get AR asset with error handling
            ar_asset = None
            ar_available = False
            
            try:
                ar_asset = ar_service.get_ar_asset(item_id)
                ar_available = ar_asset and ar_asset.get("available", False)
                
                if not ar_available:
                    logger.warning(f"AR asset not available for item {item_id}")
                    
            except Exception as e:
                logger.error(f"Failed to get AR asset for {item_id}: {str(e)}")
                unity_response["processing_warnings"].append(f"AR asset retrieval failed for {item_id}: {str(e)}")
            
            # Get placement instructions safely
            placement_instructions = item.get("placement_instructions", {})
            
            # Create unity item with defensive data access
            unity_item = {
                "item_id": item_id,
                "name": item.get("name", ""),
                "category": item.get("category", ""),
                "price": item.get("price", 0),
                "ar_available": ar_available,
                "style_reasoning": item.get("style_reasoning", "")
            }
            
            # Add AR-specific data if available
            if ar_available and ar_asset:
                unity_item.update({
                    # .glb file access URLs
                    "glb_download_url": f"/api/v1/ar/glb-file/{item_id}",
                    "thumbnail_url": f"/api/v1/ar/thumbnail/{item_id}",
                    "file_size": ar_asset.get("file_size", 0),
                    
                    # AR placement data with safe access
                    "placement_type": placement_instructions.get("placement_type", "floor"),
                    "location": placement_instructions.get("location", ""),
                    "positioning_text": placement_instructions.get("positioning_text", ""),
                    "spatial_requirements": placement_instructions.get("spatial_requirements", {}),
                    "height_from_floor": placement_instructions.get("height_from_floor", 0),
                    "orientation": placement_instructions.get("orientation", {}),
                    
                    # Unity-specific data
                    "ar_anchor_points": placement_instructions.get("ar_anchor_points", []),
                    "dependency": placement_instructions.get("dependency"),
                    "scale_factor": placement_instructions.get("scale_factor", 1.0)
                })
            else:
                # Add placeholder data for items without AR assets
                unity_item.update({
                    "glb_download_url": None,
                    "thumbnail_url": item.get("thumbnail_url", ""),
                    "file_size": 0,
                    "placement_type": placement_instructions.get("placement_type", "floor"),
                    "location": placement_instructions.get("location", ""),
                    "positioning_text": placement_instructions.get("positioning_text", "AR model pending"),
                    "spatial_requirements": placement_instructions.get("spatial_requirements", {}),
                    "height_from_floor": placement_instructions.get("height_from_floor", 0),
                    "orientation": placement_instructions.get("orientation", {}),
                    "ar_anchor_points": placement_instructions.get("ar_anchor_points", []),
                    "dependency": placement_instructions.get("dependency"),
                    "scale_factor": placement_instructions.get("scale_factor", 1.0),
                    "status": "AR model not available"
                })
            
            unity_package["items"].append(unity_item)
        
        # Add package even if some items don't have AR assets
        if unity_package["items"]:
            unity_response["furniture_packages"].append(unity_package)
            unity_response["total_items"] += len(unity_package["items"])
        else:
            unity_response["processing_warnings"].append(f"Package {package_id} has no valid items")
    
    # Add placement sequence
    try:
        unity_response["placement_sequence"] = _generate_unity_placement_sequence(
            unity_response["furniture_packages"]
        )
    except Exception as e:
        logger.error(f"Failed to generate placement sequence: {str(e)}")
        unity_response["placement_sequence"] = []
        unity_response["processing_warnings"].append(f"Placement sequence generation failed: {str(e)}")
    
    logger.info(f"Unity response completed for session {session_id}: {unity_response['total_items']} items across {len(unity_response['furniture_packages'])} packages")
    
    return unity_response

def _generate_unity_placement_sequence(packages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate placement sequence for Unity with error handling"""
    
    try:
        all_items = []
        for package in packages:
            all_items.extend(package.get("items", []))
        
        if not all_items:
            return []
        
        # Sort by placement type priority
        priority_order = {"floor": 1, "surface": 2, "wall": 3, "ceiling": 4}
        
        # Filter items that have AR assets available
        available_items = [item for item in all_items if item.get("ar_available", False)]
        
        sorted_items = sorted(
            available_items,
            key=lambda x: priority_order.get(x.get("placement_type", "floor"), 5)
        )
        
        sequence = []
        for i, item in enumerate(sorted_items):
            sequence.append({
                "step": i + 1,
                "item_id": item.get("item_id", ""),
                "item_name": item.get("name", ""),
                "placement_type": item.get("placement_type", "floor"),
                "instruction": f"Place {item.get('name', 'item')} - {item.get('positioning_text', 'Position as appropriate')}"
            })
        
        return sequence
        
    except Exception as e:
        logger.error(f"Error generating placement sequence: {str(e)}")
        return []
