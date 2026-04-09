#!/usr/bin/env python3
"""
Orchestrator-Based Test Script for Walmart AR Furniture Recommendation System
Usage: python test_full.py
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List
import time
import uuid
import pprint

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.orchestrator import OrchestratorAgent
from src.services.background_processor import BackgroundProcessor
from src.services.prototype_ar_service import PrototypeARService
from src.models.walmart_inventory import DatabaseManager
from src.utils.config import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class OrchestratorTester:
    """Test using the actual orchestrator agent"""
    
    def __init__(self):
        self.orchestrator = OrchestratorAgent(config)
        self.background_processor = BackgroundProcessor()
        self.ar_service = PrototypeARService()
        self.db_manager = DatabaseManager(config['database']['url'])
        
    async def run_complete_test(self, video_path: str, user_preferences: str):
        """Run complete test using orchestrator"""
        
        print("=" * 70)
        print("🛍️  WALMART AR FURNITURE RECOMMENDATION - ORCHESTRATOR TEST")
        print("=" * 70)
        print(f"📹 Video Path: {video_path}")
        print(f"👤 User Preferences: {user_preferences}")
        print("=" * 70)
        
        # Validate inputs
        if not self._validate_inputs(video_path, user_preferences):
            return
        
        # Test Method 1: Direct Orchestrator Call
        await self._test_direct_orchestrator(video_path, user_preferences)
        
        # Test Method 2: Background Processing (Production-like)
        await self._test_background_processing(video_path, user_preferences)
        
        # Test Method 3: Full API Simulation
        await self._test_full_api_simulation(video_path, user_preferences)
        
    def _validate_inputs(self, video_path: str, user_preferences: str) -> bool:
        """Validate input parameters"""
        
        print("\n🔍 VALIDATION: Checking Inputs")
        print("-" * 40)
        
        if not os.path.exists(video_path):
            print(f"❌ Video file not found: {video_path}")
            return False
        
        file_size = os.path.getsize(video_path)
        print(f"✅ Video file: {file_size:,} bytes")
        
        if not user_preferences or len(user_preferences.strip()) < 3:
            print("❌ User preferences too short")
            return False
        
        print(f"✅ User preferences: '{user_preferences}'")
        return True
    
    async def _test_direct_orchestrator(self, video_path: str, user_preferences: str):
        """Test Method 1: Direct orchestrator call"""
        
        print("\n🎯 TEST METHOD 1: Direct Orchestrator Call")
        print("-" * 50)
        
        try:
            print("🚀 Starting orchestrator workflow...")
            start_time = time.time()
            
            # Call orchestrator directly
            result = await self.orchestrator.execute_complete_workflow(
                video_path=video_path,
                user_preferences=user_preferences
            )
            
            elapsed = time.time() - start_time
            print(f"✅ Orchestrator completed in {elapsed:.2f} seconds")
            
            # Analyze results
            self._analyze_orchestrator_results(result, "Direct Call")
            
        except Exception as e:
            print(f"❌ Direct orchestrator test failed: {e}")
    
    async def _test_background_processing(self, video_path: str, user_preferences: str):
        """Test Method 2: Background processing (production-like)"""
        
        print("\n🔄 TEST METHOD 2: Background Processing")
        print("-" * 50)
        
        try:
            session_id = str(uuid.uuid4())
            user_id = "test_user_123"
            
            print(f"📝 Session ID: {session_id}")
            print("🚀 Starting background processing...")
            
            # Start background task
            task_id = await self.background_processor.start_processing_task(
                video_path=video_path,
                user_preferences=user_preferences,
                session_id=session_id,
                user_id=user_id
            )
            
            print(f"📋 Task ID: {task_id}")
            
            # Monitor progress
            await self._monitor_background_progress(session_id)
            
            # Get final results
            final_results = self.db_manager.get_session_recommendations(session_id)
            
            if final_results:
                print("✅ Background processing completed successfully")
                self._analyze_orchestrator_results(final_results, "Background Processing")
            else:
                print("❌ Background processing failed - no results")
                
        except Exception as e:
            print(f"❌ Background processing test failed: {e}")
    
    async def _test_full_api_simulation(self, video_path: str, user_preferences: str):
        """Test Method 3: Full API simulation (Flutter -> Unity flow)"""
        
        print("\n🌐 TEST METHOD 3: Full API Simulation")
        print("-" * 50)
        
        try:
            session_id = str(uuid.uuid4())
            
            # Simulate Flutter upload
            print("📱 Simulating Flutter video upload...")
            task_id = await self.background_processor.start_processing_task(
                video_path=video_path,
                user_preferences=user_preferences,
                session_id=session_id,
                user_id="flutter_test_user"
            )
            
            # Wait for completion
            print("⏳ Waiting for processing completion...")
            await self._wait_for_completion(session_id, timeout=120)
            
            # Simulate Unity data retrieval
            print("🎮 Simulating Unity data retrieval...")
            unity_data = await self._simulate_unity_data_retrieval(session_id)
            
            if unity_data:
                print("✅ Full API simulation completed successfully")
                self._analyze_unity_results(unity_data)
            else:
                print("❌ Full API simulation failed")
                
        except Exception as e:
            print(f"❌ Full API simulation test failed: {e}")
    
    async def _monitor_background_progress(self, session_id: str):
        """Monitor background processing progress"""
        
        print("📊 Monitoring progress...")
        
        for i in range(24):  # Monitor for up to 2 minutes
            await asyncio.sleep(5)
            
            status = await self.background_processor.get_processing_status(session_id)
            
            if status.get("status") == "completed":
                print(f"   ✅ Completed (Progress: {status.get('progress', 0)}%)")
                break
            elif status.get("status") == "failed":
                print(f"   ❌ Failed: {status.get('error', 'Unknown error')}")
                break
            else:
                progress = status.get("progress", 0)
                message = status.get("message", "Processing...")
                print(f"   ⏳ Progress: {progress}% - {message}")
    
    async def _wait_for_completion(self, session_id: str, timeout: int = 120):
        """Wait for processing to complete"""
        
        for i in range(timeout // 5):  # Check every 5 seconds
            await asyncio.sleep(5)
            
            status = await self.background_processor.get_processing_status(session_id)
            
            if status.get("status") in ["completed", "failed"]:
                return status
        
        print("⚠️  Timeout waiting for completion")
        return None
    
    async def _simulate_unity_data_retrieval(self, session_id: str) -> Dict[str, Any]:
        """Simulate Unity retrieving AR data"""
        
        recommendations = self.db_manager.get_session_recommendations(session_id)
        
        if not recommendations:
            return None
        
        # Format for Unity (like the actual API would)
        unity_data = {
            "success": True,
            "session_id": session_id,
            "furniture_packages": [],
            "total_items": 0
        }
        
        for package in recommendations.get("furniture_packages", []):
            unity_package = {
                "package_id": package.get("package_id", ""),
                "package_name": package.get("package_name", ""),
                "items": []
            }
            
            for item in package.get("items", []):
                # Check AR asset availability
                ar_asset = self.ar_service.get_ar_asset(item["item_id"])
                
                if ar_asset and ar_asset.get("available"):
                    unity_item = {
                        "item_id": item["item_id"],
                        "name": item["name"],
                        "price": item["price"],
                        "glb_download_url": f"/api/v1/ar/glb-file/{item['item_id']}",
                        "ar_ready": True
                    }
                    unity_package["items"].append(unity_item)
            
            if unity_package["items"]:
                unity_data["furniture_packages"].append(unity_package)
                unity_data["total_items"] += len(unity_package["items"])
        
        return unity_data
    
    def _analyze_orchestrator_results(self, result: Dict[str, Any], test_method: str):
        """Analyze orchestrator results with robust key and type checking, including handling 'matched_packages' and 'matched_products'."""
        print(f"\n📊 {test_method.upper()} RESULTS ANALYSIS")
        print("-" * 50)

        if not result or not result.get("success"):
            print("❌ No valid results to analyze")
            pprint.pprint(result)
            return

        # Room analysis
        room_analysis = result.get("room_analysis", {})
        print(f"🏠 Room Analysis:")
        print(f"   Type: {room_analysis.get('room_type', 'Unknown')}")
        print(f"   Style: {room_analysis.get('current_style', 'Unknown')}")
        print(f"   Colors: {', '.join(room_analysis.get('color_palette', []))}")

        # Pinterest inspiration
        pinterest_data = (
            result.get("pinterest_inspiration") or
            result.get("pinterest_results") or
            {}
        )
        if pinterest_data:
            images_count = 0
            if isinstance(pinterest_data.get("images"), list):
                images_count = len(pinterest_data["images"])
            elif isinstance(pinterest_data.get("images_analyzed"), int):
                images_count = pinterest_data["images_analyzed"]
            elif isinstance(pinterest_data.get("total_images_found"), int):
                images_count = pinterest_data["total_images_found"]
            print(f"📌 Pinterest Inspiration:")
            print(f"   Results: {pinterest_data.get('total_results', images_count)}")
            print(f"   Images: {images_count}")
        else:
            print("📌 Pinterest Inspiration: No data found")

        # Design packages (handle both 'design_packages' and 'matched_packages')
        packages = result.get("design_packages") or result.get("matched_packages") or result.get("packages") or []
        print(f"📦 Design Packages: {len(packages)}")

        total_items = 0
        total_cost = 0
        ar_ready_count = 0

        for i, package in enumerate(packages, 1):
            # Try both 'products', 'items', and 'matched_products' as keys
            items = package.get("products") or package.get("items") or package.get("matched_products") or []
            package_cost = sum(item.get("price", 0) for item in items)

            print(f"   Package {i}: {package.get('package_name', package.get('name', 'Unknown'))}")
            print(f"      Items: {len(items)}")
            print(f"      Cost: ${package_cost:.2f}")

            total_items += len(items)
            total_cost += package_cost

            # Check AR availability
            for item in items:
                walmart_id = item.get("walmart_id")
                if walmart_id and hasattr(self, "ar_service") and self.ar_service.get_ar_asset(walmart_id):
                    ar_ready_count += 1

        print(f"\n📈 SUMMARY:")
        print(f"   Total Items: {total_items}")
        print(f"   Total Cost: ${total_cost:.2f}")
        print(f"   AR Ready: {ar_ready_count}/{total_items}")
        print(f"   AR Coverage: {(ar_ready_count/total_items)*100:.1f}%" if total_items > 0 else "   AR Coverage: 0%")

        # Print the full result for debugging if something seems off
        if total_items == 0 or (pinterest_data and images_count == 0):
            print("\n[DEBUG] Full orchestrator result:")
            pprint.pprint(result)
    
    def _analyze_unity_results(self, unity_data: Dict[str, Any]):
        """Analyze Unity-formatted results"""
        
        print(f"\n📊 UNITY API RESULTS ANALYSIS")
        print("-" * 50)
        
        packages = unity_data.get("furniture_packages", [])
        total_items = unity_data.get("total_items", 0)
        
        print(f"🎮 Unity Data:")
        print(f"   Session: {unity_data.get('session_id', 'Unknown')}")
        print(f"   Packages: {len(packages)}")
        print(f"   Total Items: {total_items}")
        
        ar_ready_items = 0
        for package in packages:
            for item in package.get("items", []):
                if item.get("ar_ready"):
                    ar_ready_items += 1
        
        print(f"   AR Ready Items: {ar_ready_items}")
        print(f"   AR Coverage: {(ar_ready_items/total_items)*100:.1f}%" if total_items > 0 else "   AR Coverage: 0%")
        
        if ar_ready_items > 0:
            print("✅ Unity integration ready - AR assets available")
        else:
            print("❌ Unity integration blocked - no AR assets")

async def main():
    """Main test function"""
    
    print("🚀 Walmart AR Furniture Recommendation - Orchestrator Tester")
    print("=" * 70)
    
    # Get video path
    video_path = input("📹 Enter video file path: ").strip()
    
    if not video_path:
        print("❌ No video path provided")
        return
    
    # Get user preferences
    user_preferences = input("👤 Enter preferences (e.g., 'modern cozy bedroom'): ").strip()
    
    if not user_preferences:
        print("❌ No preferences provided")
        return
    
    # Run orchestrator-based test
    tester = OrchestratorTester()
    await tester.run_complete_test(video_path, user_preferences)

if __name__ == "__main__":
    asyncio.run(main())
