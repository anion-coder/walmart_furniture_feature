import google.generativeai as genai
import json
from typing import Dict, Any, List
import asyncio
from PIL import Image
import time

from ..utils.logger import setup_logger
from ..services.video_utils import VideoProcessor

logger = setup_logger(__name__)


class GeminiPinAnalysisAgent:
    def __init__(self, config: Dict[str, Any]):
        gemini_cfg = config.get("ai_models", {}).get("gemini", {}) or {}
        api_key = gemini_cfg.get("api_key")
        if not api_key:
            raise ValueError("Gemini API key not found in configuration")

        genai.configure(api_key=api_key)
        model_name = gemini_cfg.get("model", "gemini-2.5-flash")
        self.model = genai.GenerativeModel(model_name)
        self.video_processor = VideoProcessor()
    
    async def analyze_pinterest_and_recommend(self, video_path: str, pinterest_images: List[Image.Image], 
                                            room_analysis: Dict[str, Any], user_preferences: str) -> Dict[str, Any]:
        """Analyze Pinterest images and generate recommendations"""
        
        try:
            # Get room frame from video
            room_frame = self.video_processor.extract_key_frames(video_path, num_frames=1)[0]
            room_image = Image.fromarray(room_frame)
            
            # Create visual analysis prompt
            prompt = self._create_pinterest_analysis_prompt(room_analysis, user_preferences)
            
            # Prepare content parts for Gemini (proper multi-image format)
            content_parts = []
            
            # Add room image first
            content_parts.append(room_image)
            content_parts.append("This is the user's current room that needs furniture recommendations.")
            
            # Add Pinterest inspiration images
            # Limit to 3 images to reduce Gemini token and image quota usage
            content_parts.append("\nHere are trending Pinterest room designs for inspiration:")
            for i, pinterest_img in enumerate(pinterest_images[:3]):  # Limit to 3 images
                content_parts.append(pinterest_img)
                content_parts.append(f"Pinterest inspiration image {i+1}")
            
            # Add the analysis prompt
            content_parts.append(prompt)
            
            # Generate recommendations with proper content structure
            response = await asyncio.to_thread(
                self.model.generate_content,
                content_parts
            )
            
            # Parse response
            packages = self._parse_recommendation_response(response.text)
            print(f"Packages: {packages}")
            return packages
            
        except Exception as e:
            logger.error(f"Pinterest analysis failed: {str(e)}")
            return self._fallback_packages()
    
    def _create_pinterest_analysis_prompt(self, room_analysis: Dict[str, Any], user_preferences: str) -> str:
        return f"""
VISUAL PINTEREST INSPIRATION ANALYSIS:

You are analyzing the user's room (first image) alongside trending Pinterest inspirations (following images).

USER WANTS: {user_preferences}
ROOM ANALYSIS: {room_analysis}

ANALYSIS INSTRUCTIONS:
1. Study the user's room image - understand the current layout, style, and furniture
2. Examine each Pinterest inspiration image - identify what makes these rooms beautiful
3. Extract specific furniture pieces, colors, materials, and styling elements from Pinterest images
4. Create furniture packages that adapt these Pinterest trends to the user's specific room

CREATE 3 DESIGN PACKAGES that recreate Pinterest aesthetics:

PACKAGE 1 - "Pinterest Trending Modern"
PACKAGE 2 - "Pinterest Cozy Vibes" 
PACKAGE 3 - "Pinterest Statement Style"

For each package, specify exact products based on what you see in the Pinterest images:
- Furniture pieces (materials, colors, exact dimensions)
- Decor accessories that complete the Pinterest look
- Specific reasoning about how this recreates the Pinterest aesthetic

IMPORTANT: Base your recommendations on the actual visual elements you observe in the Pinterest images.

FORMAT as JSON:
{{
  "packages": [
    {{
      "name": "Pinterest Trending Modern",
      "description": "Recreates the modern aesthetic seen in trending Pinterest rooms",
      "inspiration_source": "Based on Pinterest images showing clean lines, neutral colors, and minimalist furniture",
      "products": [
        {{
          "category": "furniture",
          "item_type": "nightstand",
          "name": "Modern Black Nightstand with Wood Accents", 
          "material": "engineered wood with metal hardware",
          "color": "matte black with natural wood drawer",
          "dimensions": "40cm W x 35cm D x 50cm H",
          "style_keywords": ["modern", "minimalist", "geometric"],
          "pinterest_inspiration": "Matches the trending black and wood furniture combination seen in Pinterest bedroom designs",
          "estimated_price_range": "200-400"
        }}
      ]
    }}
  ]
}}
"""
    
    def _parse_recommendation_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini recommendation response"""
        try:
            # Look for JSON content in the response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = response_text[start_idx:end_idx]
                parsed = json.loads(json_str)
                logger.info("Successfully parsed Pinterest analysis response")
                print(f"Parsed: {parsed}")
                return parsed
            else:
                logger.warning("No JSON found in Pinterest analysis response")
                return self._fallback_packages()
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Pinterest analysis JSON: {str(e)}")
            logger.debug(f"Response text: {response_text[:500]}...")
            return self._fallback_packages()
    
    def _fallback_packages(self) -> Dict[str, Any]:
        """Fallback packages when analysis fails"""
        return {
            "packages": [
                {
                    "name": "fallback fake as real one not available Modern Minimalist",
                    "description": "Clean, simple, functional furniture package",
                    "inspiration_source": "Based on modern design principles",
                    "products": [
                        {
                            "category": "furniture",
                            "item_type": "nightstand",
                            "name": "Modern Black Nightstand",
                            "material": "engineered wood",
                            "color": "matte black",
                            "dimensions": "40cm W x 35cm D x 50cm H",
                            "style_keywords": ["modern", "minimalist"],
                            "pinterest_inspiration": "Contemporary minimalist design",
                            "estimated_price_range": "200-400"
                        }
                    ]
                }
            ]
        }
