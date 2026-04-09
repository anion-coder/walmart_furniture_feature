import asyncio
import os
import tempfile
from typing import Dict, Any
import uuid
import cv2
import numpy as np

from src.agents.gemini_video_agent import GeminiVideoAgent
from src.agents.pinterest_search_agent import PinterestSearchAgent
from src.agents.product_match_agent import ProductMatchAgent
from src.services.prototype_ar_service import PrototypeARService
from src.services.background_processor import BackgroundProcessor
from src.models.walmart_inventory import DatabaseManager
from src.utils.config import config

class ComponentTester:
    """Test individual system components with real APIs"""
    
    def __init__(self, verbose: bool = False, rate_limit: bool = True):
        self.verbose = verbose
        self.rate_limit = rate_limit
    
    async def test_gemini_video_analyzer_real(self) -> Dict[str, Any]:
        """Test Gemini video analysis with real API"""
        
        try:
            analyzer = GeminiVideoAgent(config)
            
            # Create a real test video
            test_video = "video/test.mp4"
            
            print(f"\n     📹 Created test video: {os.path.getsize(test_video)} bytes")
            print(f"     🤖 Calling Gemini API...")
            
            result = await analyzer.analyze_room_video(test_video, "modern cozy bedroom")
            
            # Cleanup
            os.unlink(test_video)
            
            if result and "room_type" in result:
                return {
                    "success": True,
                    "details": f"Analyzed room type: {result['room_type']}, Style: {result.get('current_style', 'Unknown')}",
                    "api_calls": 1,
                    "estimated_cost": 0.02  # Approximate Gemini cost
                }
            else:
                return {
                    "success": False,
                    "error": "Invalid analysis result from Gemini"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Gemini API error: {str(e)}"
            }
    
    async def test_pinterest_search_real(self) -> Dict[str, Any]:
        """Test Pinterest search via DuckDuckGo with real API"""
        
        try:
            pinterest_agent = PinterestSearchAgent(config)
            
            search_params = {
                "search_terms": ["modern bedroom design", "cozy bedroom ideas"],
                "style_keywords": ["minimalist", "scandinavian"]
            }
            
            print(f"\n     🔍 Searching Pinterest via DuckDuckGo...")
            result = await pinterest_agent.search_trending_designs(search_params)
            
            if result and result.get("success"):
                return {
                    "success": True,
                    "details": f"Found {result.get('total_results', 0)} Pinterest results, Downloaded {len(result.get('images', []))} images",
                    "api_calls": len(search_params.get('search_terms', [])),
                    "estimated_cost": 0.0  # DuckDuckGo is free
                }
            else:
                return {
                    "success": False,
                    "error": "Pinterest search failed - check internet connection"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Pinterest search error: {str(e)}"
            }
    
    async def test_product_matching_real(self) -> Dict[str, Any]:
        """Test product matching against real database"""
        
        try:
            product_agent = ProductMatchAgent(config)
            
            # Test with real product specification
            test_spec = {
                "category": "furniture",
                "item_type": "nightstand",
                "material": "wood",
                "color": "black",
                "style": "modern",
                "name": "Modern Black Nightstand",
                "pinterest_inspiration": "Trending minimalist furniture"
            }
            
            print(f"\n     🔍 Searching product database...")
            matches = await product_agent._find_matching_products(test_spec)
            
            if matches and len(matches) > 0:
                return {
                    "success": True,
                    "details": f"Found {len(matches)} matching products. Top match: {matches[0].get('name', 'Unknown')}",
                    "api_calls": 0,  # Database query, not external API
                    "estimated_cost": 0.0
                }
            else:
                return {
                    "success": False,
                    "error": "No product matches found - check database setup"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Product matching error: {str(e)}"
            }
    
    async def test_ar_asset_service(self) -> Dict[str, Any]:
        """Test AR asset management"""
        
        try:
            ar_service = PrototypeARService()
            
            # Test asset retrieval
            available_assets = ar_service.list_available_assets()
            
            if len(available_assets) > 0:
                # Test getting asset info for first available asset
                asset_info = ar_service.get_ar_asset(available_assets[0])
                
                if asset_info and asset_info.get("available"):
                    file_size_mb = asset_info.get('file_size', 0) / (1024 * 1024)
                    return {
                        "success": True,
                        "details": f"Found {len(available_assets)} AR assets. Sample: {available_assets[0]} ({file_size_mb:.2f} MB)",
                        "api_calls": 0,
                        "estimated_cost": 0.0
                    }
                else:
                    return {
                        "success": False,
                        "error": "Asset info retrieval failed"
                    }
            else:
                return {
                    "success": False,
                    "error": "No AR assets found - run setup_prototype_assets.py first"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"AR service error: {str(e)}"
            }
    
    async def test_database_manager(self) -> Dict[str, Any]:
        """Test database connectivity and operations"""
        
        try:
            db_manager = DatabaseManager(config['database']['url'])
            
            # Test product retrieval
            products = db_manager.get_products_by_criteria(limit=5)
            
            if products and len(products) > 0:
                return {
                    "success": True,
                    "details": f"Retrieved {len(products)} products. Sample: {products[0]['name']} (${products[0]['price']})",
                    "api_calls": 0,
                    "estimated_cost": 0.0
                }
            else:
                return {
                    "success": False,
                    "error": "No products found - run setup_sample_data.py first"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Database error: {str(e)}"
            }
    
    async def test_background_processor_real(self) -> Dict[str, Any]:
        """Test background processing system"""
        
        try:
            processor = BackgroundProcessor()
            
            # Test with a real session creation
            test_session_id = str(uuid.uuid4())
            test_video = self._create_real_test_video()
            
            print(f"\n     🚀 Starting background processing task...")
            
            task_id = await processor.start_processing_task(
                test_video, 
                "modern cozy bedroom test", 
                test_session_id,
                "test_user"
            )
            
            # Wait a moment and check status
            await asyncio.sleep(2)
            status = await processor.get_processing_status(test_session_id)
            
            # Cleanup
            os.unlink(test_video)
            
            if task_id and status.get("status") == "processing":
                return {
                    "success": True,
                    "details": f"Background task started successfully. Status: {status.get('status')}",
                    "api_calls": 0,
                    "estimated_cost": 0.0
                }
            else:
                return {
                    "success": False,
                    "error": f"Background processor failed. Status: {status}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Background processor error: {str(e)}"
            }
    
    def _create_real_test_video(self) -> str:
        """Create a real test video file with actual content"""
        
        # Create a simple test video using OpenCV
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as f:
            temp_path = f.name
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(temp_path, fourcc, 2.0, (640, 480))
        
        # Create 30 frames (15 seconds at 2 fps)
        for i in range(30):
            # Create a frame with some content
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # Add some colored rectangles to simulate room furniture
            cv2.rectangle(frame, (50, 50), (200, 150), (100, 50, 50), -1)  # Bed
            cv2.rectangle(frame, (250, 80), (320, 140), (50, 100, 50), -1)  # Nightstand
            cv2.rectangle(frame, (400, 300), (580, 450), (80, 80, 80), -1)  # Dresser
            
            # Add frame number
            cv2.putText(frame, f"Frame {i+1}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            writer.write(frame)
        
        writer.release()
        return temp_path
