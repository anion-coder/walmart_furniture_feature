import asyncio
import time
from typing import Dict, Any, List
import json
from datetime import datetime

from .test_components import ComponentTester
from .test_integration import IntegrationTester
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class TestRunner:
    """Real API test runner for the system"""
    
    def __init__(self, verbose: bool = False, rate_limit: bool = True):
        self.verbose = verbose
        self.rate_limit = rate_limit  # Add delays between API calls
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "start_time": None,
            "end_time": None,
            "api_calls_made": 0,
            "total_cost_estimate": 0.0
        }
        
        self.component_tester = ComponentTester(verbose, rate_limit)
        self.integration_tester = IntegrationTester(verbose, rate_limit)
    
    async def run_all_tests(self):
        """Run all tests with real API calls"""
        print("\n🚀 Running All Tests with Real APIs...")
        print("⚠️  Note: This will make actual API calls and may incur costs")
        
        confirm = input("Continue with real API testing? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Testing cancelled")
            return
        
        self.results["start_time"] = datetime.now()
        
        # Component tests
        await self.run_component_tests()
        
        # Integration tests  
        await self.run_integration_tests()
        
        # API tests
        await self.run_api_tests()
        
        self.results["end_time"] = datetime.now()
        self._print_final_results()
    
    async def run_component_tests(self):
        """Run individual component tests with real APIs"""
        print("\n🔧 Testing Individual Components with Real APIs...")
        
        components = [
            ("Database Manager", self.component_tester.test_database_manager),
            ("AR Asset Service", self.component_tester.test_ar_asset_service),
            ("Pinterest Search Agent", self.component_tester.test_pinterest_search_real),
            ("Product Matching Agent", self.component_tester.test_product_matching_real),
            ("Gemini Video Analyzer", self.component_tester.test_gemini_video_analyzer_real),
            ("Background Processor", self.component_tester.test_background_processor_real)
        ]
        
        for component_name, test_func in components:
            await self._run_single_test(component_name, test_func)
            
            # Rate limiting between API calls
            if self.rate_limit and "API" in component_name or "Gemini" in component_name:
                print("   ⏳ Rate limiting (5s delay)...")
                await asyncio.sleep(5)
    
    async def run_integration_tests(self):
        """Run integration tests with real APIs"""
        print("\n🔗 Testing System Integration with Real APIs...")
        
        integration_tests = [
            ("Complete Workflow", self.integration_tester.test_complete_workflow_real),
            ("Pinterest to Gemini Pipeline", self.integration_tester.test_pinterest_gemini_pipeline_real),
            ("Flutter to Unity Flow", self.integration_tester.test_flutter_unity_flow_real),
            ("GLB File Serving", self.integration_tester.test_glb_file_serving)
        ]
        
        for test_name, test_func in integration_tests:
            await self._run_single_test(test_name, test_func)
            
            # Longer delay for integration tests
            if self.rate_limit:
                print("   ⏳ Rate limiting (10s delay)...")
                await asyncio.sleep(10)
    
    async def run_api_tests(self):
        """Run API endpoint tests"""
        print("\n🌐 Testing API Endpoints...")
        
        api_tests = [
            ("Flutter Video Upload", self.integration_tester.test_flutter_upload_api_real),
            ("Unity Recommendations API", self.integration_tester.test_unity_recommendations_api_real),
            ("GLB Download API", self.integration_tester.test_glb_download_api),
            ("Processing Status API", self.integration_tester.test_processing_status_api)
        ]
        
        for test_name, test_func in api_tests:
            await self._run_single_test(test_name, test_func)
    
    async def _run_single_test(self, test_name: str, test_func):
        """Run a single test and track results"""
        self.results["total_tests"] += 1
        
        print(f"\n  🧪 {test_name}... ", end="")
        
        try:
            start_time = time.time()
            result = await test_func()
            end_time = time.time()
            
            # Track API usage
            if result and result.get("api_calls"):
                self.results["api_calls_made"] += result["api_calls"]
            if result and result.get("estimated_cost"):
                self.results["total_cost_estimate"] += result["estimated_cost"]
            
            if result and result.get("success", False):
                print(f"✅ PASSED ({end_time - start_time:.2f}s)")
                self.results["passed"] += 1
                
                if self.verbose and result.get("details"):
                    print(f"     📝 {result['details']}")
                if result.get("api_calls"):
                    print(f"     📡 API calls: {result['api_calls']}")
            else:
                print(f"❌ FAILED ({end_time - start_time:.2f}s)")
                self.results["failed"] += 1
                error_msg = result.get("error", "Unknown error") if result else "Test returned None"
                self.results["errors"].append(f"{test_name}: {error_msg}")
                
                if self.verbose:
                    print(f"     ❗ {error_msg}")
        
        except Exception as e:
            print(f"💥 ERROR ({time.time() - start_time:.2f}s)")
            self.results["failed"] += 1
            self.results["errors"].append(f"{test_name}: {str(e)}")
            
            if self.verbose:
                print(f"     💥 Exception: {str(e)}")
    
    def _print_final_results(self):
        """Print final test results with API usage summary"""
        total_time = (self.results["end_time"] - self.results["start_time"]).total_seconds() if self.results["end_time"] else 0
        
        print("\n" + "=" * 60)
        print("📊 REAL API TEST RESULTS SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.results['total_tests']}")
        print(f"✅ Passed: {self.results['passed']}")
        print(f"❌ Failed: {self.results['failed']}")
        print(f"⏱️  Total Time: {total_time:.2f}s")
        print(f"📡 API Calls Made: {self.results['api_calls_made']}")
        print(f"💰 Estimated Cost: ${self.results['total_cost_estimate']:.4f}")
        
        if self.results["errors"]:
            print(f"\n❗ Errors ({len(self.results['errors'])}):")
            for error in self.results["errors"]:
                print(f"   • {error}")
        
        success_rate = (self.results["passed"] / self.results["total_tests"]) * 100 if self.results["total_tests"] > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("🎉 Excellent! System is working well with real APIs.")
        elif success_rate >= 70:
            print("⚠️  Good, but some issues need attention.")
        else:
            print("🚨 Multiple issues detected. Review failed tests.")
