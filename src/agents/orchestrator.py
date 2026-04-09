import asyncio
from typing import Dict, Any
from datetime import datetime
import uuid

from ..utils.logger import setup_logger
from .gemini_video_agent import GeminiVideoAgent
from .pinterest_search_agent import PinterestSearchAgent
from .gemini_pin_analysis_agent import GeminiPinAnalysisAgent
from .product_match_agent import ProductMatchAgent
from ..services.prototype_ar_service import PrototypeARService

logger = setup_logger(__name__)

class OrchestratorAgent:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.task_id = None
        
        # Initialize agents
        self.gemini_video_agent = GeminiVideoAgent(config)
        self.pinterest_agent = PinterestSearchAgent(config)
        self.gemini_pin_agent = GeminiPinAnalysisAgent(config)
        self.product_agent = ProductMatchAgent(config)
        self.ar_service = PrototypeARService()
    
    async def execute_complete_workflow(self, video_path: str, user_preferences: str) -> Dict[str, Any]:
        """Execute complete AI workflow"""
        self.task_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting workflow {self.task_id}")
            
            # Stage 1: Room video analysis
            logger.info("Stage 1: Analyzing room video with Gemini")
            room_analysis = await self.gemini_video_agent.analyze_room_video(
                video_path, user_preferences
            )
            
            # Stage 2: Pinterest search
            logger.info("Stage 2: Searching Pinterest via DuckDuckGo")
            pinterest_results = await self.pinterest_agent.search_trending_designs(
                room_analysis['pinterest_search_params']
            )
            
            # Stage 3: Pinterest visual analysis
            logger.info("Stage 3: Analyzing Pinterest images with Gemini")
            design_packages = await self.gemini_pin_agent.analyze_pinterest_and_recommend(
                video_path, pinterest_results['images'], room_analysis, user_preferences
            )
            
            # Stage 4: Product matching
            logger.info("Stage 4: Matching products from database")
            matched_products = await self.product_agent.match_products_to_packages(
                design_packages
            )
            
            # Stage 5: AR asset preparation
            logger.info("Stage 5: Preparing AR assets")
            final_packages = await self._prepare_ar_ready_packages(matched_products)
            
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            response = {
                "success": True,
                "task_id": self.task_id,
                "processing_time": f"{processing_time:.1f} seconds",
                "room_analysis": room_analysis,
                "pinterest_inspiration": {
                    "total_images_found": len(pinterest_results.get('pinterest_urls', [])),
                    "images_analyzed": len(pinterest_results.get('image_urls', [])),
                    "search_queries": pinterest_results.get('search_queries_used', [])
                },
                "design_packages": final_packages,
                "ar_visualization_ready": True,
                "total_ar_ready_products": self._count_ar_ready_products(final_packages)
            }
            
            logger.info(f"Workflow {self.task_id} completed in {processing_time:.1f}s")
            return response
            
        except Exception as e:
            logger.error(f"Workflow {self.task_id} failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "task_id": self.task_id
            }
    
    async def _prepare_ar_ready_packages(self, matched_products: Dict[str, Any]) -> list[Dict[str, Any]]:
        """Prepare packages with AR asset information"""
        
        ar_ready_packages = []
        
        for package in matched_products.get('matched_packages', []):
            ar_ready_products = []
            
            for product in package.get('matched_products', []):  # Limit to 6 per package
                # Get AR asset info
                print(f"product in prepare_ar_ready in orchestrator.py :{product}")
                # ar_asset = self.ar_service.get_ar_asset(product['walmart_id'])
                ar_asset = True
                
                # if ar_asset and ar_asset.get('available'):
                if ar_asset:
                    product.update({
                        "glb_file_url": "temp",
                        "thumbnail_url": "temp",
                        "ar_ready": True,
                        "placement_type": "temp"
                        # "placement_type": ar_asset.get('placement_type', 'floor')
                    })
                    ar_ready_products.append(product)
            
            if ar_ready_products:
                ar_ready_packages.append({
                    "package_name": package['name'],
                    "style_description": package['description'],
                    "total_estimated_cost": sum(p.get('price', 0) for p in ar_ready_products),
                    "products": ar_ready_products,
                    "ar_visualization_ready": True
                })
        
        print(f"ar_ready_packages: {ar_ready_packages}")
        
        return ar_ready_packages
    
    def _count_ar_ready_products(self, packages: list[Dict[str, Any]]) -> int:
        """Count total AR-ready products across all packages"""
        total = 0
        for package in packages:
            total += len(package.get('products', []))
        return total
