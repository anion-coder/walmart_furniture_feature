# src/agents/coherence_validator.py
from typing import Dict, Any, List
import asyncio
from PIL import Image

from ..utils.logger import setup_logger
from ..services.video_utils import VideoProcessor

logger = setup_logger(__name__)

def bypass_coherence_validation(validated_products: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stand-alone helper that simply passes the products through and
    attaches a default coherence score.
    """
    return {
        "final_packages": validated_products.get("validated_packages", []),
        "coherence_score": 0.8,          # assume good coherence
        "validation_method": "bypassed"
    }

class CoherenceValidator:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.video_processor = VideoProcessor()
        # ➜ Turn validation on/off via config:  coherence: { bypass: true }
        self.bypass = bool(config.get("coherence", {}).get("bypass", False))

    async def validate_package_coherence(
        self,
        video_path: str,
        validated_packages: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Either performs full coherence validation (default) or, when the
        bypass flag is True, skips all expensive checks and returns the
        packages as-is with a fixed score.
        """
        # ------------------ 1) FAST BYPASS PATH ------------------ #
        if self.bypass:
            logger.warning("⚠️  Coherence validation BYPASSED (config flag set).")
            final_packages = []
            # still attach AR-asset info for downstream steps
            for package in validated_packages.get("validated_packages", []):
                final_packages.append(
                    await self._prepare_final_package(package, coherence_score=0.8)
                )
            return final_packages

        # ------------------ 2) FULL VALIDATION PATH --------------- #
        try:
            # Extract a single representative frame
            room_frame = self.video_processor.extract_key_frames(
                video_path, num_frames=1
            )[0]
            room_image = Image.fromarray(room_frame)

            final_packages = []
            for package in validated_packages.get("validated_packages", []):
                coherence_score = await self._validate_group_coherence(
                    package["validated_products"]
                )
                if coherence_score > 0.7:
                    final_package = await self._prepare_final_package(
                        package, coherence_score
                    )
                    final_packages.append(final_package)
            return final_packages

        except Exception as e:
            logger.error(f"Coherence validation failed: {str(e)}")
            return []

    # ---------- internal helpers below remain unchanged ----------
    async def _validate_group_coherence(self, products: List[Dict[str, Any]]) -> float:
        try:
            styles = [p.get("style", "modern") for p in products]
            colors = [p.get("color_primary", "neutral") for p in products]
            categories = [p.get("category", "furniture") for p in products]

            style_coherence = self._calculate_style_coherence(styles)
            color_harmony = self._calculate_color_harmony(colors)
            category_balance = self._calculate_category_balance(categories)

            return style_coherence * 0.4 + color_harmony * 0.4 + category_balance * 0.2
        except Exception as e:
            logger.error(f"Group coherence calculation failed: {str(e)}")
            return 0.7

    def _calculate_style_coherence(self, styles: List[str]) -> float:
        if not styles:
            return 0.5
        style_counts = {}
        for style in styles:
            style_counts[style] = style_counts.get(style, 0) + 1
        return max(style_counts.values()) / len(styles)

    def _calculate_color_harmony(self, colors: List[str]) -> float:
        if not colors:
            return 0.5
        neutral_colors = {"white", "black", "grey", "gray", "beige", "cream"}
        neutral_count = sum(
            1 for c in colors if any(n in c.lower() for n in neutral_colors)
        )
        harmony_score = 0.7 + (neutral_count / len(colors)) * 0.3
        return min(harmony_score, 1.0)

    def _calculate_category_balance(self, categories: List[str]) -> float:
        if not categories:
            return 0.5
        unique_categories = len(set(categories))
        if 2 <= unique_categories <= 4:
            return 0.9
        if unique_categories == 1:
            return 0.6
        return 0.7

    async def _prepare_final_package(
        self, package: Dict[str, Any], coherence_score: float
    ) -> Dict[str, Any]:
        final_products, total_cost = [], 0
        for product in package["validated_products"][:6]:
            ar_asset = self._get_ar_asset_info(product["walmart_id"])
            final_products.append(
                {
                    "walmart_id": product["walmart_id"],
                    "name": product["name"],
                    "category": product["category"],
                    "price": product.get("price", 0),
                    "glb_file_url": ar_asset["glb_file_url"],
                    "thumbnail_url": ar_asset["thumbnail_url"],
                    "compatibility_score": product["validation"]["compatibility_score"],
                    "pinterest_match_reason": product.get("spec_match", {}).get(
                        "pinterest_inspiration", ""
                    ),
                    "placement_type": ar_asset["placement_type"],
                }
            )
            total_cost += product.get("price", 0)

        return {
            "package_name": package["name"],
            "style_description": package["description"],
            "total_estimated_cost": total_cost,
            "coherence_score": coherence_score,
            "products": final_products,
            "ar_visualization_ready": True,
        }

    def _get_ar_asset_info(self, walmart_id: str) -> Dict[str, str]:
        return {
            "glb_file_url": f"/ar-assets/{walmart_id}.glb",
            "thumbnail_url": f"/ar-assets/thumbnails/{walmart_id}.jpg",
            "placement_type": "floor",
        }
