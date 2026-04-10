"""
End-to-end test for the complete Walmart furniture recommendation pipeline.

Takes the video from the video/ folder, runs every stage of the orchestrator,
and prints the full result — room analysis, Pinterest inspiration, design
packages with matched Walmart products, and AR-ready output.

Usage:
    python -m tests.test_full_workflow
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ── project root on sys.path so "src.*" imports resolve ──────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import config
from src.utils.logger import setup_logger
from src.agents.orchestrator import OrchestratorAgent
from src.models.walmart_inventory import DatabaseManager, WalmartProduct

logger = setup_logger("test_full_workflow")

# ── configuration ─────────────────────────────────────────────────────
VIDEO_PATH = str(PROJECT_ROOT / "video" / "test.mp4")
USER_PREFERENCES = "cozy modern bedroom with warm lighting and neutral tones"


# =====================================================================
#  Pre-flight checks
# =====================================================================

def check_video_exists():
    """Verify the test video is present."""
    if not os.path.exists(VIDEO_PATH):
        print(f"\nERROR: Video not found at {VIDEO_PATH}")
        print("Place a .mp4 file in the video/ folder and try again.")
        sys.exit(1)
    size_mb = os.path.getsize(VIDEO_PATH) / (1024 * 1024)
    print(f"Video  : {VIDEO_PATH}  ({size_mb:.1f} MB)")


def check_database():
    """Verify DB connection and that products exist."""
    try:
        db = DatabaseManager(config["database"]["url"])
        session = db.get_session()
        count = session.query(WalmartProduct).filter(
            WalmartProduct.stock_status == "in_stock",
            WalmartProduct.has_glb_file == True,
        ).count()
        session.close()
        print(f"DB     : connected  —  {count} in-stock products with GLB flag")
        if count == 0:
            print("\nWARNING: The database has 0 matching products.")
            print("Run  python -m scripts.populate_walmart_db  first.\n")
        return count
    except Exception as e:
        print(f"\nERROR: Cannot reach database — {e}")
        sys.exit(1)


# =====================================================================
#  Pretty-print helpers
# =====================================================================

def section(title: str):
    width = 64
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}")


def print_room_analysis(analysis: dict):
    section("STAGE 1 — ROOM ANALYSIS (Gemini)")
    print(f"  Room type       : {analysis.get('room_type')}")
    print(f"  Current style   : {analysis.get('current_style')}")
    print(f"  Room size       : {analysis.get('room_size')}")
    print(f"  Lighting        : {analysis.get('lighting')}")
    print(f"  Color palette   : {', '.join(analysis.get('color_palette', []))}")
    print(f"  Existing items  : {', '.join(analysis.get('existing_furniture', []))}")
    print(f"  Confidence      : {analysis.get('style_confidence')}")
    print(f"  Method          : {analysis.get('analysis_method', 'unknown')}")

    improvements = analysis.get("improvement_opportunities", [])
    if improvements:
        print("  Improvements    :")
        for imp in improvements:
            print(f"    - {imp}")

    psp = analysis.get("pinterest_search_params", {})
    if psp:
        print("  Pinterest terms :")
        for t in psp.get("search_terms", []):
            print(f"    - {t}")


def print_pinterest_info(result: dict):
    section("STAGE 2+3 — PINTEREST INSPIRATION")
    pi = result.get("pinterest_inspiration", {})
    print(f"  Total images found : {pi.get('total_images_found', 0)}")
    print(f"  Images analysed    : {pi.get('images_analyzed', 0)}")
    queries = pi.get("search_queries", [])
    if queries:
        print("  Queries used       :")
        for q in queries:
            print(f"    - {q}")


def print_design_packages(packages: list):
    section("STAGE 4+5 — DESIGN PACKAGES WITH MATCHED PRODUCTS")
    if not packages:
        print("  (no packages returned)")
        return

    for i, pkg in enumerate(packages, 1):
        print(f"\n  ── Package {i}: {pkg.get('package_name', 'N/A')} ──")
        print(f"     Style       : {pkg.get('style_description', '')[:100]}")
        print(f"     Total cost  : ${pkg.get('total_estimated_cost', 0):.2f}")
        print(f"     AR ready    : {pkg.get('ar_visualization_ready', False)}")

        products = pkg.get("products", [])
        print(f"     Products ({len(products)}):")
        for j, p in enumerate(products, 1):
            name = p.get("name", "?")
            price = p.get("price", 0)
            cat = p.get("category", "")
            score = p.get("similarity_score", "")
            score_str = f"  (score {score:.3f})" if isinstance(score, float) else ""
            print(f"       {j}. [{cat}] {name}  —  ${price:.2f}{score_str}")


def print_summary(result: dict, elapsed: float):
    section("WORKFLOW SUMMARY")
    print(f"  Success              : {result.get('success')}")
    print(f"  Task ID              : {result.get('task_id')}")
    print(f"  Pipeline time        : {result.get('processing_time')}")
    print(f"  Wall-clock time      : {elapsed:.1f}s")
    print(f"  AR-ready products    : {result.get('total_ar_ready_products', 0)}")
    print(f"  AR visualisation     : {result.get('ar_visualization_ready')}")


# =====================================================================
#  Main test runner
# =====================================================================

async def run_workflow():
    """Execute the full orchestrator workflow and display results."""

    print("\n" + "#" * 64)
    print("  WALMART FURNITURE PIPELINE — FULL WORKFLOW TEST")
    print("#" * 64)
    print(f"  Timestamp  : {datetime.now().isoformat()}")
    print(f"  Preferences: {USER_PREFERENCES}\n")

    # Pre-flight
    check_video_exists()
    product_count = check_database()

    # Initialise orchestrator (loads agents, embedding index, etc.)
    section("INITIALISING ORCHESTRATOR")
    init_start = time.time()
    orchestrator = OrchestratorAgent(config)
    print(f"  Orchestrator ready in {time.time() - init_start:.1f}s")

    # Run the full pipeline
    section("EXECUTING PIPELINE")
    print("  Running all 5 stages — this may take 1-3 minutes ...\n")

    wall_start = time.time()
    result = await orchestrator.execute_complete_workflow(VIDEO_PATH, USER_PREFERENCES)
    elapsed = time.time() - wall_start

    # ── Display results ──────────────────────────────────────────────
    if not result.get("success"):
        section("PIPELINE FAILED")
        print(f"  Error: {result.get('error', 'unknown')}")
        print("\nFull result JSON:")
        print(json.dumps(result, indent=2, default=str))
        return result

    # Stage 1: room analysis
    room = result.get("room_analysis", {})
    print_room_analysis(room)

    # Stage 2+3: pinterest
    print_pinterest_info(result)

    # Stage 4+5: design packages with matched products
    packages = result.get("design_packages", [])
    print_design_packages(packages)

    # Summary
    print_summary(result, elapsed)

    # ── Dump full JSON for inspection ────────────────────────────────
    output_path = PROJECT_ROOT / "tests" / "last_workflow_result.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\n  Full JSON saved to: {output_path}\n")

    return result


# =====================================================================
#  Entry point
# =====================================================================

def main():
    result = asyncio.run(run_workflow())
    success = result.get("success", False)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
