#!/usr/bin/env python3
"""
Real API Test Runner for Walmart AR Furniture Recommendation System
Usage: python run_tests.py [test_type]
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.tests.test_runner import TestRunner
from src.tests.test_components import ComponentTester
from src.tests.test_integration import IntegrationTester
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Test Walmart AR Furniture System with Real APIs")
    parser.add_argument(
        "test_type", 
        choices=["all", "components", "integration", "api", "gemini", "pinterest", "database", "ar", "quick"],
        help="Type of test to run"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--no-rate-limit", action="store_true", help="Disable rate limiting between API calls")
    parser.add_argument("--confirm", "-y", action="store_true", help="Skip confirmation prompts")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🛍️  WALMART AR FURNITURE SYSTEM - REAL API TESTS")
    print("=" * 60)
    print("⚠️  WARNING: This will make actual API calls and may incur costs!")
    print("📡 APIs that will be called:")
    print("   • Google Gemini API (paid)")
    print("   • DuckDuckGo Search (free)")
    print("   • Your local database")
    print("   • Your local file system")
    
    if not args.confirm:
        confirm = input("\nContinue with real API testing? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Testing cancelled")
            return
    
    test_runner = TestRunner(
        verbose=args.verbose, 
        rate_limit=not args.no_rate_limit
    )
    
    if args.test_type == "all":
        asyncio.run(test_runner.run_all_tests())
    elif args.test_type == "components":
        asyncio.run(test_runner.run_component_tests())
    elif args.test_type == "integration":
        asyncio.run(test_runner.run_integration_tests())
    elif args.test_type == "api":
        asyncio.run(test_runner.run_api_tests())
    elif args.test_type == "gemini":
        asyncio.run(test_runner.test_gemini_components())
    elif args.test_type == "pinterest":
        asyncio.run(test_runner.test_pinterest_components())
    elif args.test_type == "database":
        asyncio.run(test_runner.test_database_components())
    elif args.test_type == "ar":
        asyncio.run(test_runner.test_ar_components())
    elif args.test_type == "quick":
        print("\n🏃‍♂️ Running Quick Tests (no expensive API calls)")
        component_tester = ComponentTester(args.verbose, True)
        tests = [
            ("Database Manager", component_tester.test_database_manager),
            ("AR Asset Service", component_tester.test_ar_asset_service)
        ]
        async def run_quick_tests():
            for test_name, test_func in tests:
                print(f"\n🧪 {test_name}... ", end="")
                result = await test_func()
                if result and result.get("success"):
                    print("✅ PASSED")
                else:
                    print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
        asyncio.run(run_quick_tests())

if __name__ == "__main__":
    main()
