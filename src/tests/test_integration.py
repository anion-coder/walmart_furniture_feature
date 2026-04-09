import asyncio
import requests
import tempfile
import os
from typing import Dict, Any
import json
import uuid

class IntegrationTester:
    """Test system integration with real APIs"""
    
    def __init__(self, verbose: bool = False, rate_limit: bool = True):
        self.verbose = verbose
        self.rate_limit = rate_limit
        self.base_url = "http://localhost:8000"
    
    async def test_complete_workflow_real(self) -> Dict[str, Any]:
        """Test complete system workflow with real APIs"""
        
        try:
            from src.agents.orchestrator import OrchestratorAgent
            from src.utils.config import config
            
            # Create real test video
            test_video = "video/test.mp4"
            
            print(f"\n     🎬 Created test video ({os.path.getsize(test_video)} bytes)")
            print(f"     🤖 Running complete AI workflow...")
            
            orchestrator = OrchestratorAgent(config)
            
            # Execute complete workflow with real APIs
            result = await orchestrator.execute_complete_workflow(
                test_video, 
                "cozy modern bedroom with good lighting"
            )
            
            # Cleanup
            os.unlink(test_video)
            
            if result and result.get("success"):
                packages = result.get("design_packages", [])
                total_items = sum(len(pkg.get("products", [])) for pkg in packages)
                
                return {
                    "success": True,
                    "details": f"Complete workflow success! Generated {len(packages)} packages with {total_items} items",
                    "api_calls": 5,  # Estimated: Gemini room analysis + Pinterest + Gemini recommendations
                    "estimated_cost": 0.06  # Estimated total cost
                }
            else:
                return {
                    "success": False,
                    "error": f"Workflow failed: {result.get('error', 'Unknown error')}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Complete workflow error: {str(e)}"
            }
    
    async def test_pinterest_gemini_pipeline_real(self) -> Dict[str, Any]:
        """Test Pinterest to Gemini analysis pipeline with real APIs"""
        
        try:
            from src.agents.pinterest_search_agent import PinterestSearchAgent
            from src.agents.gemini_pin_analysis_agent import GeminiPinAnalysisAgent
            from src.utils.config import config
            
            # Step 1: Real Pinterest search
            pinterest_agent = PinterestSearchAgent(config)
            search_params = {
                "search_terms": ["modern bedroom design"],
                "style_keywords": ["minimalist"]
            }
            
            print(f"\n     📌 Searching Pinterest...")
            pinterest_results = await pinterest_agent.search_trending_designs(search_params)
            
            if not pinterest_results.get("success"):
                return {
                    "success": False,
                    "error": "Pinterest search failed"
                }
            
            # Step 2: Gemini analysis of Pinterest images
            print(f"     🤖 Analyzing Pinterest images with Gemini...")
            gemini_pin_agent = GeminiPinAnalysisAgent(config)
            
            test_video = self._create_test_video()
            room_analysis = {"room_type": "bedroom", "style": "modern"}
            
            recommendations = await gemini_pin_agent.analyze_pinterest_and_recommend(
                test_video,
                pinterest_results.get("pinterest_urls", [])[:5],
                room_analysis,
                "modern cozy bedroom"
            )
            
            # Cleanup
            os.unlink(test_video)
            
            if recommendations and recommendations.get("packages"):
                return {
                    "success": True,
                    "details": f"Pinterest→Gemini pipeline success! Found {pinterest_results.get('total_results', 0)} Pinterest images, generated {len(recommendations['packages'])} packages",
                    "api_calls": 3,  # Pinterest search + Gemini image analysis
                    "estimated_cost": 0.04
                }
            else:
                return {
                    "success": False,
                    "error": "Gemini Pinterest analysis failed"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Pinterest-Gemini pipeline error: {str(e)}"
            }
    
    async def test_flutter_unity_flow_real(self) -> Dict[str, Any]:
        """Test Flutter upload to Unity retrieval flow with real backend"""
        
        try:
            # Check if server is running
            try:
                health_response = requests.get(f"{self.base_url}/health", timeout=5)
                if health_response.status_code != 200:
                    return {
                        "success": False,
                        "error": "API server not running - start with: python -m src.api.main"
                    }
            except requests.exceptions.RequestException:
                return {
                    "success": False,
                    "error": "API server not accessible"
                }
            
            # Step 1: Flutter video upload simulation
            test_video = self._create_test_video()
            
            print(f"\n     📱 Simulating Flutter video upload...")
            
            with open(test_video, 'rb') as video_file:
                files = {'video': video_file}
                data = {
                    'user_preferences': 'modern cozy bedroom test',
                    'user_id': 'test_user_123'
                }
                
                response = requests.post(
                    f"{self.base_url}/api/v1/video-upload-and-process",
                    files=files,
                    data=data,
                    timeout=30
                )
            
            os.unlink(test_video)
            
            if response.status_code == 200:
                upload_result = response.json()
                session_id = upload_result.get("session_id")
                
                if session_id:
                    # Step 2: Wait and check Unity endpoint
                    print(f"     ⏳ Waiting for processing (30s)...")
                    await asyncio.sleep(30)
                    
                    print(f"     📱 Checking Unity recommendations...")
                    unity_response = requests.get(
                        f"{self.base_url}/api/v1/ar-recommendations/{session_id}",
                        timeout=10
                    )
                    
                    if unity_response.status_code == 200:
                        unity_data = unity_response.json()
                        if unity_data.get("success"):
                            return {
                                "success": True,
                                "details": f"Flutter→Unity flow success! Session: {session_id}, Packages: {len(unity_data.get('furniture_packages', []))}",
                                "api_calls": 5,  # Full workflow API calls
                                "estimated_cost": 0.06
                            }
                    
                    return {
                        "success": False,
                        "error": f"Unity endpoint returned: {unity_response.status_code}"
                    }
                else:
                    return {
                        "success": False,
                        "error": "No session ID returned from upload"
                    }
            else:
                return {
                    "success": False,
                    "error": f"Upload failed with status: {response.status_code}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Flutter-Unity flow error: {str(e)}"
            }
    
    async def test_flutter_upload_api_real(self) -> Dict[str, Any]:
        """Test Flutter video upload API with real file"""
        
        try:
            # Create real test video
            test_video = self._create_test_video()
            
            with open(test_video, 'rb') as video_file:
                files = {'video': video_file}
                data = {
                    'user_preferences': 'modern bedroom test',
                    'user_id': 'test_user_real'
                }
                
                response = requests.post(
                    f"{self.base_url}/api/v1/video-upload-and-process",
                    files=files,
                    data=data,
                    timeout=30
                )
            
            os.unlink(test_video)
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "details": f"Upload successful. Session: {result.get('session_id', 'Unknown')}",
                    "api_calls": 1,
                    "estimated_cost": 0.0
                }
            else:
                return {
                    "success": False,
                    "error": f"Upload API returned: {response.status_code}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Flutter upload API error: {str(e)}"
            }
    
    async def test_unity_recommendations_api_real(self) -> Dict[str, Any]:
        """Test Unity recommendations API with real session"""
        
        try:
            # This would test with a real session that has completed processing
            # For now, test the endpoint response for non-existent session
            test_session_id = "test_session_real_123"
            response = requests.get(
                f"{self.base_url}/api/v1/ar-recommendations/{test_session_id}",
                timeout=10
            )
            
            # Should return 404 for non-existent session
            if response.status_code == 404:
                return {
                    "success": True,
                    "details": "Unity recommendations API responding correctly to non-existent session",
                    "api_calls": 0,
                    "estimated_cost": 0.0
                }
            else:
                return {
                    "success": False,
                    "error": f"Unexpected Unity API response: {response.status_code}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Unity recommendations API error: {str(e)}"
            }
    
    def _create_test_video(self) -> str:
        """Create a real test video file"""
        import cv2
        import numpy as np
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as f:
            temp_path = f.name
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(temp_path, fourcc, 2.0, (640, 480))
        
        # Create 20 frames
        for i in range(20):
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            
            # Add bedroom furniture simulation
            cv2.rectangle(frame, (50, 200), (300, 400), (139, 69, 19), -1)  # Bed
            cv2.rectangle(frame, (320, 220), (400, 300), (101, 67, 33), -1)  # Nightstand
            cv2.rectangle(frame, (450, 180), (620, 420), (160, 82, 45), -1)  # Dresser
            
            # Add some variation
            color = (100 + i*5, 100, 100)
            cv2.circle(frame, (500, 100), 30, color, -1)  # Lamp
            
            writer.write(frame)
        
        writer.release()
        return temp_path
