import asyncio
import json
import redis
from datetime import datetime
from typing import Dict, Any
import uuid

from ..agents.orchestrator import OrchestratorAgent
from ..models.walmart_inventory import DatabaseManager
from ..models.walmart_inventory import ProcessingSession
from ..utils.config import config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class BackgroundProcessor:
    """Handle background video processing tasks"""
    
    def __init__(self):
        # Try to connect to Redis, but don't crash the app if unreachable.
        try:
            self.redis_client = redis.from_url(config["redis"]["url"])
            # Test the connection quickly
            self.redis_client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.warning(f"Redis unavailable, proceeding without Redis: {e}")
            self.redis_client = None

        self.db_manager = DatabaseManager(config["database"]["url"])
        self.orchestrator = OrchestratorAgent(config)
    
    async def start_processing_task(self, video_path: str, user_preferences: str, 
                                  session_id: str, user_id: str = None) -> str:
        """Start background processing task"""
        
        task_id = str(uuid.uuid4())
        
        # Save session to database
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "video_path": video_path,
            "user_preferences": user_preferences,
            "status": "processing",
            "progress": 0
        }
        
        self.db_manager.save_processing_session(session_data)
        
        # Set initial Redis status
        self._update_redis_status(session_id, {
            "status": "processing",
            "progress": 0,
            "task_id": task_id,
            "started_at": datetime.now().isoformat(),
            "message": "Starting video analysis..."
        })
        
        # Start background task
        asyncio.create_task(self._process_video_async(video_path, user_preferences, session_id, task_id))
        
        return task_id
    
    async def _process_video_async(self, video_path: str, user_preferences: str, 
                                 session_id: str, task_id: str):
        """Background video processing with progress updates"""
        
        try:
            # Stage 1: Room analysis (20%)
            self._update_progress(session_id, 20, "Analyzing room video with AI...")
            
            # Stage 2: Pinterest search (40%)
            self._update_progress(session_id, 40, "Finding Pinterest inspiration...")
            
            # Stage 3: AI recommendations (60%)
            self._update_progress(session_id, 60, "Generating furniture recommendations...")
            
            # Execute complete workflow
            result = await self.orchestrator.execute_complete_workflow(video_path, user_preferences)
            
            # Stage 4: Product matching (80%)
            self._update_progress(session_id, 80, "Matching products from database...")
            
            # Stage 5: AR asset preparation (90%)
            self._update_progress(session_id, 90, "Preparing AR visualization data...")
            
            # Enhance with placement instructions
            enhanced_result = await self._enhance_with_placement_data(result)
            
            # Save results to database
            self.db_manager.update_session_status(
                session_id, "completed", 100, enhanced_result
            )
            
            # Update Redis with completion
            self._update_redis_status(session_id, {
                "status": "completed",
                "progress": 100,
                "task_id": task_id,
                "completed_at": datetime.now().isoformat(),
                "message": "Processing complete"
            })
            
            logger.info(f"Successfully completed processing for session {session_id}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Processing failed for session {session_id}: {error_msg}")
            
            # Update database with error
            self.db_manager.update_session_status(session_id, "failed", error=error_msg)
            
            # Update Redis with error
            self._update_redis_status(session_id, {
                "status": "failed",
                "error": error_msg,
                "task_id": task_id,
                "failed_at": datetime.now().isoformat()
            })
    
    def _update_progress(self, session_id: str, progress: int, message: str):
        """Update processing progress"""
        
        # Update database
        self.db_manager.update_session_status(session_id, "processing", progress)
        
        # Update Redis
        self._update_redis_status(session_id, {
            "status": "processing",
            "progress": progress,
            "message": message,
            "updated_at": datetime.now().isoformat()
        })
    
    def _update_redis_status(self, session_id: str, status_data: Dict[str, Any]):
        """Update Redis with status data"""
        if not self.redis_client:
            # Redis is optional; skip if not available
            return

        self.redis_client.setex(
            f"task:{session_id}",
            config["redis"]["task_ttl"],
            json.dumps(status_data),
        )
    
    async def get_processing_status(self, session_id: str) -> Dict[str, Any]:
        """Get current processing status"""
        # Try Redis first (faster) if available
        if self.redis_client:
            try:
                redis_status = self.redis_client.get(f"task:{session_id}")
            except Exception as e:
                logger.warning(f"Redis status lookup failed, falling back to DB: {e}")
                redis_status = None

            if redis_status:
                return json.loads(redis_status)
        
        # Fallback to database
        session = self.db_manager.get_session()
        processing_session = session.query(ProcessingSession).filter_by(session_id=session_id).first()
        session.close()
        
        if processing_session:
            return {
                "status": processing_session.status,
                "progress": processing_session.progress,
                "error": processing_session.error_message
            }
        
        return {"status": "not_found"}
    
    async def _enhance_with_placement_data(self, ai_result: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance AI result with placement instructions"""
        
        from ..services.placement_generator import PlacementInstructionsGenerator
        
        placement_generator = PlacementInstructionsGenerator()
        enhanced_packages = []
        
        for package in ai_result.get('design_packages', []):
            enhanced_items = []
            
            for product in package.get('products', []):
                # Generate placement instructions
                placement_instructions = placement_generator.generate_placement_instructions(
                    product, ai_result['room_analysis']
                )
                
                enhanced_item = {
                    "item_id": product['walmart_id'],
                    "name": product['name'],
                    "category": product['category'],
                    "price": product['price'],
                    "glb_download_url": f"temp in background processor",
                    "thumbnail_url": product['image_urls'],
                    "placement_instructions": placement_instructions,
                    "style_reasoning": product.get('pinterest_match_reason', '')
                }
                
                enhanced_items.append(enhanced_item)
            
            enhanced_package = {
                "package_id": package['package_name'].replace(" ", "_").lower(),
                "package_name": package['package_name'],
                "style_description": package['style_description'],
                "total_cost": sum(item['price'] for item in enhanced_items),
                "items": enhanced_items
            }
            
            enhanced_packages.append(enhanced_package)
        
        return {
            "success": True,
            "room_analysis": ai_result['room_analysis'],
            "furniture_packages": enhanced_packages,
            "total_items": sum(len(pkg['items']) for pkg in enhanced_packages)
        }
