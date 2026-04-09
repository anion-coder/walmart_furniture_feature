import os
import shutil
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import json
import base64

from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class PrototypeARService:
    """Enhanced local .glb file management for prototype"""
    
    def __init__(self, base_path: str = "./data/ar_assets"):
        self.base_path = Path(base_path)
        self.glb_directory = self.base_path / "glb_files"
        self.thumbnails_directory = self.base_path / "thumbnails"
        
        # Create directories
        self.glb_directory.mkdir(parents=True, exist_ok=True)
        self.thumbnails_directory.mkdir(parents=True, exist_ok=True)
        
        # Track available assets
        self.asset_registry = self._load_asset_registry()
    
    def save_glb_file(self, walmart_id: str, glb_file_path: str, 
                      thumbnail_path: str = None) -> Dict[str, Any]:
        """Save .glb file to local storage"""
        
        destination_glb = self.glb_directory / f"{walmart_id}.glb"
        destination_thumb = self.thumbnails_directory / f"{walmart_id}.jpg"
        
        try:
            # Copy .glb file
            shutil.copy2(glb_file_path, destination_glb)
            
            # Copy or create thumbnail
            if thumbnail_path and os.path.exists(thumbnail_path):
                shutil.copy2(thumbnail_path, destination_thumb)
            else:
                self._create_default_thumbnail(destination_thumb)
            
            # Register asset
            asset_info = {
                "walmart_id": walmart_id,
                "glb_file_path": str(destination_glb),
                "thumbnail_path": str(destination_thumb),
                "file_size": os.path.getsize(destination_glb),
                "placement_type": self._determine_placement_type(walmart_id),
                "available": True,
                "created_at": str(datetime.now())
            }
            
            self.asset_registry[walmart_id] = asset_info
            self._save_asset_registry()
            
            logger.info(f"Successfully saved AR asset for {walmart_id}")
            return asset_info
            
        except Exception as e:
            logger.error(f"Failed to save AR asset for {walmart_id}: {str(e)}")
            return {
                "walmart_id": walmart_id,
                "error": str(e),
                "available": False
            }
    
    def get_ar_asset(self, walmart_id: str) -> Optional[Dict[str, Any]]:
        """Get AR asset information for API response"""
        
        if walmart_id in self.asset_registry:
            asset_info = self.asset_registry[walmart_id].copy()
            
            # Convert to API-friendly URLs
            asset_info["glb_download_url"] = f"/api/v1/ar/glb-file/{walmart_id}"
            asset_info["thumbnail_url"] = f"/api/v1/ar/thumbnail/{walmart_id}"
            
            return asset_info
        
        return None
    
    def get_glb_file_path(self, walmart_id: str) -> Optional[str]:
        """Get local file path for serving"""
        glb_path = self.glb_directory / f"{walmart_id}.glb"
        return str(glb_path) if glb_path.exists() else None
    
    def get_thumbnail_path(self, walmart_id: str) -> Optional[str]:
        """Get thumbnail file path"""
        thumb_path = self.thumbnails_directory / f"{walmart_id}.jpg"
        return str(thumb_path) if thumb_path.exists() else None
    
    def get_glb_file_base64(self, walmart_id: str) -> Optional[str]:
        """Get .glb file as base64 encoded string"""
        glb_path = self.get_glb_file_path(walmart_id)
        
        if glb_path and os.path.exists(glb_path):
            with open(glb_path, 'rb') as f:
                glb_content = f.read()
                return base64.b64encode(glb_content).decode('utf-8')
        
        return None
    
    def list_available_assets(self) -> List[str]:
        """List all available AR assets"""
        return list(self.asset_registry.keys())
    
    def bulk_add_assets(self, assets_directory: str) -> Dict[str, Any]:
        """Add multiple .glb files from directory"""
        
        results = {
            "success": [],
            "failed": [],
            "total_processed": 0
        }
        
        assets_path = Path(assets_directory)
        if not assets_path.exists():
            return {"error": "Assets directory not found"}
        
        # Process all .glb files
        for glb_file in assets_path.glob("*.glb"):
            walmart_id = glb_file.stem
            
            # Look for thumbnail
            thumbnail_file = assets_path / f"{walmart_id}.jpg"
            thumbnail_path = str(thumbnail_file) if thumbnail_file.exists() else None
            
            # Save asset
            result = self.save_glb_file(walmart_id, str(glb_file), thumbnail_path)
            
            if result.get("available"):
                results["success"].append(walmart_id)
            else:
                results["failed"].append({"walmart_id": walmart_id, "error": result.get("error")})
            
            results["total_processed"] += 1
        
        return results
    
    def _load_asset_registry(self) -> Dict[str, Any]:
        """Load asset registry from file"""
        registry_file = self.base_path / "asset_registry.json"
        
        if registry_file.exists():
            with open(registry_file, 'r') as f:
                return json.load(f)
        
        return {}
    
    def _save_asset_registry(self):
        """Save asset registry to file"""
        registry_file = self.base_path / "asset_registry.json"
        
        with open(registry_file, 'w') as f:
            json.dump(self.asset_registry, f, indent=2)
    
    def _create_default_thumbnail(self, thumbnail_path: Path):
        """Create default thumbnail"""
        # Create a simple placeholder image
        from PIL import Image, ImageDraw, ImageFont
        
        img = Image.new('RGB', (300, 300), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        
        # Add text
        try:
            font = ImageFont.load_default()
        except:
            font = None
        
        text = "AR Asset"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (300 - text_width) // 2
        y = (300 - text_height) // 2
        
        draw.text((x, y), text, fill=(100, 100, 100), font=font)
        
        img.save(thumbnail_path, 'JPEG')
    
    def _determine_placement_type(self, walmart_id: str) -> str:
        """Determine placement type"""
        # Simple heuristic for prototype
        return "floor"
