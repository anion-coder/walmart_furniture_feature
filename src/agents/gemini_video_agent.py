import base64
import os
import json
import time
import asyncio
import tempfile
from datetime import datetime
from typing import Dict, Any, List
import numpy as np
from PIL import Image

# New Gemini imports based on docs
from google import genai
from google.genai import types

from ..utils.logger import setup_logger
from ..services.video_utils import VideoProcessor

logger = setup_logger(__name__)

class GeminiVideoAgent:
    def __init__(self, config: Dict[str, Any]):
        try:
            gemini_cfg = config.get("ai_models", {}).get("gemini", {}) or {}

            api_key = gemini_cfg.get("api_key")
            if not api_key:
                # Try environment variable as backup
                api_key = os.environ.get("GEMINI_API_KEY")
            
            if not api_key:
                raise ValueError("Gemini API key not found in configuration or environment")
            
            # Initialize new Gemini client
            self.client = genai.Client(api_key=api_key)
            # Allow overriding model from config, default to gemini-2.5-flash
            self.model_name = gemini_cfg.get("model", "gemini-2.5-flash")
            self.video_processor = VideoProcessor()
            self.api_key_valid = True
            
            logger.info("Gemini Video Agent initialized successfully with new API")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Video Agent: {str(e)}")
            self.api_key_valid = False
            self.client = None
            self.video_processor = VideoProcessor()
    
    async def analyze_room_video(self, video_path: str, user_preferences: str) -> Dict[str, Any]:
        """Analyze room video with new Gemini API"""
        
        if not self.api_key_valid or not self.client:
            logger.warning("Gemini API not available, using fallback analysis")
            return self._enhanced_fallback_analysis(user_preferences)
        
        try:
            # Validate video file
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video file not found: {video_path}")
            
            # Check video file size
            file_size = os.path.getsize(video_path)
            if file_size > 50 * 1024 * 1024:  # 50MB limit for new API
                logger.warning("Video file too large, using frame analysis")
                frames = self.video_processor.extract_key_frames(video_path, num_frames=3)
                return await self._analyze_with_frames(frames, user_preferences)
            
            # Try new Gemini video analysis
            try:
                analysis = await self._analyze_with_new_gemini_api(video_path, user_preferences)
                logger.info("Successfully analyzed video with new Gemini API")
                return analysis
            except Exception as video_error:
                logger.warning(f"New Gemini API failed: {str(video_error)}")
                
                # Fallback to frame analysis
                frames = self.video_processor.extract_key_frames(video_path, num_frames=3)
                analysis = await self._analyze_with_frames(frames, user_preferences)
                logger.info("Successfully analyzed with frame fallback")
                return analysis
                
        except Exception as e:
            logger.error(f"Complete analysis failed: {str(e)}")
            return self._enhanced_fallback_analysis(user_preferences)
    
    async def _analyze_with_new_gemini_api(self, video_path: str, user_preferences: str) -> Dict[str, Any]:
        """Analyze video using the new Gemini API structure"""
        
        try:
            # Step 1: Read and encode video file
            video_data = await self._read_and_encode_video(video_path)
            
            # Step 2: Create prompt
            prompt_text = self._create_room_analysis_prompt(user_preferences)
            
            # Step 3: Create content using new API structure
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(
                            mime_type=self._get_video_mime_type(video_path),
                            data=video_data,
                        ),
                        types.Part.from_text(text=prompt_text),
                    ],
                ),
            ]
            
            # Step 4: Configure generation
            generate_content_config = types.GenerateContentConfig(
                response_mime_type="text/plain",
                temperature=0.3,
                max_output_tokens=2000,
            )
            
            # Step 5: Generate content with streaming
            response_text = ""
            
            # Run in thread pool to avoid blocking
            def generate_content():
                nonlocal response_text
                for chunk in self.client.models.generate_content_stream(
                    model=self.model_name,
                    contents=contents,
                    config=generate_content_config,
                ):
                    if chunk.text:
                        response_text += chunk.text
                return response_text
            
            # Execute with timeout
            final_response = await asyncio.wait_for(
                asyncio.to_thread(generate_content),
                timeout=120  # 2 minute timeout
            )
            
            # Step 6: Parse and return analysis
            analysis = self._parse_analysis_response(final_response, user_preferences)
            analysis['analysis_method'] = 'new_gemini_video_api'
            analysis['model_used'] = self.model_name
            
            print(f"Gemini Video Agent analysis: {analysis}")
            return analysis
            
        except Exception as e:
            logger.error(f"New Gemini API analysis failed: {str(e)}")
            raise
    
    async def _read_and_encode_video(self, video_path: str) -> bytes:
        """Read video file and return as bytes for new API"""
        
        try:
            def read_file():
                with open(video_path, 'rb') as video_file:
                    return video_file.read()
            
            # Read file in thread to avoid blocking
            video_bytes = await asyncio.to_thread(read_file)
            
            logger.info(f"Read video file: {len(video_bytes)} bytes")
            return video_bytes
            
        except Exception as e:
            logger.error(f"Failed to read video file: {str(e)}")
            raise
    
    async def _analyze_with_frames(self, frames: List[np.ndarray], user_preferences: str) -> Dict[str, Any]:
        """Fallback analysis using individual frames with new API"""
        
        try:
            if not frames:
                raise ValueError("No frames extracted from video")
            
            # Convert best frame to PIL Image
            room_image = Image.fromarray(frames[0])
            
            # Convert image to bytes
            import io
            img_buffer = io.BytesIO()
            room_image.save(img_buffer, format='JPEG', quality=90)
            img_bytes = img_buffer.getvalue()
            
            # Create prompt for frame analysis
            prompt_text = self._create_frame_analysis_prompt(user_preferences)
            
            # Create content for image analysis
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_bytes(
                            mime_type="image/jpeg",
                            data=img_bytes,
                        ),
                        types.Part.from_text(text=prompt_text),
                    ],
                ),
            ]
            
            # Configure generation
            generate_content_config = types.GenerateContentConfig(
                response_mime_type="text/plain",
                temperature=0.3,
                max_output_tokens=1500,
            )
            
            # Generate analysis
            response_text = ""
            
            def generate_frame_analysis():
                nonlocal response_text
                for chunk in self.client.models.generate_content_stream(
                    model=self.model_name,
                    contents=contents,
                    config=generate_content_config,
                ):
                    if chunk.text:
                        response_text += chunk.text
                return response_text
            
            final_response = await asyncio.wait_for(
                asyncio.to_thread(generate_frame_analysis),
                timeout=60
            )
            
            # Parse response
            analysis = self._parse_analysis_response(final_response, user_preferences)
            analysis['analysis_method'] = 'new_gemini_frame_api'
            
            return analysis
            
        except Exception as e:
            logger.error(f"Frame analysis failed: {str(e)}")
            return self._enhanced_fallback_analysis(user_preferences)
    
    def _get_video_mime_type(self, video_path: str) -> str:
        """Determine video MIME type from file extension"""
        
        extension = os.path.splitext(video_path)[1].lower()
        mime_types = {
            '.mp4': 'video/mp4',
            '.mov': 'video/quicktime',
            '.avi': 'video/x-msvideo',
            '.mkv': 'video/x-matroska',
            '.webm': 'video/webm',
            '.3gp': 'video/3gpp',
        }
        
        return mime_types.get(extension, 'video/mp4')
    
    def _create_room_analysis_prompt(self, user_preferences: str) -> str:
        """Create comprehensive room analysis prompt for video"""
        return f"""
You are a PROFESSIONAL INTERIOR DESIGNER with 15+ years of experience analyzing spaces for high-end clients. 

Analyze this room video comprehensively, observing all angles and details shown throughout the video.

USER PREFERENCES: {user_preferences}

COMPREHENSIVE VIDEO ANALYSIS TASK:

1. SPATIAL ASSESSMENT:
   - Room type and dimensions (estimated from video walkthrough)
   - Architectural features and layout observed
   - Natural light sources and orientation
   - Traffic flow and functional zones throughout space

2. EXISTING ELEMENTS EVALUATION:
   - Current furniture inventory seen in all video angles
   - Style coherence across visible areas
   - Color palette observed throughout space
   - Lighting adequacy and opportunities

3. DESIGN DIAGNOSIS:
   - What works well and should be preserved
   - Problem areas needing improvement
   - Style inconsistencies to address
   - Functional deficiencies observed

4. PINTEREST SEARCH STRATEGY:
   Generate specific search terms for finding trending design inspiration that matches both the space and user preferences.

Return comprehensive JSON analysis:
{{
  "room_type": "bedroom/living_room/dining_room/office/kitchen",
  "current_style": "modern/traditional/rustic/minimalist/eclectic",
  "color_palette": ["primary_color", "secondary_color", "accent_color"],
  "existing_furniture": ["item1", "item2", "item3"],
  "room_size": "small/medium/large",
  "lighting": "bright/natural/dim",
  "architectural_features": ["feature1", "feature2"],
  "improvement_opportunities": ["specific_improvement1", "specific_improvement2"],
  "style_confidence": 0.85,
  "design_problems": ["problem1", "problem2"],
  "preservation_elements": ["keep_item1", "keep_item2"],
  "pinterest_search_params": {{
    "search_terms": [
      "{user_preferences} {{room_type}} design inspiration",
      "trending {{room_type}} decor 2024",
      "{{current_style}} {{room_type}} ideas",
      "{{room_type}} makeover before after",
      "{user_preferences} interior design"
    ],
    "style_keywords": ["primary_style", "complementary_style"],
    "color_searches": [
      "{{color_palette}} {{room_type}} scheme",
      "{{current_style}} color combinations",
      "neutral {{room_type}} colors"
    ]
  }},
  "video_analysis_notes": "Specific observations from complete video walkthrough"
}}

Focus on actionable insights from the complete video that will guide furniture recommendations.
IMPORTANT: Return ONLY valid JSON, no additional text or explanations.
"""
    
    def _create_frame_analysis_prompt(self, user_preferences: str) -> str:
        """Create frame analysis prompt as fallback"""
        return f"""
Analyze this room image as a professional interior designer.

USER PREFERENCES: {user_preferences}

Provide detailed room assessment in JSON format:
{{
  "room_type": "bedroom/living_room/etc",
  "current_style": "style_assessment",
  "color_palette": ["dominant_color", "secondary_color", "accent_color"],
  "existing_furniture": ["visible_item1", "visible_item2"],
  "room_size": "estimated_size",
  "lighting": "lighting_assessment",
  "improvement_opportunities": ["specific_improvement1", "specific_improvement2"],
  "style_confidence": 0.75,
  "pinterest_search_params": {{
    "search_terms": [
      "{user_preferences} room design",
      "modern room inspiration",
      "room makeover ideas",
      "trending interior design",
      "room decor inspiration"
    ],
    "style_keywords": ["modern", "cozy", "minimalist"],
    "color_searches": [
      "neutral room colors",
      "room color schemes",
      "interior color palettes"
    ]
  }}
}}

IMPORTANT: Return ONLY valid JSON, no additional text.
"""
    
    def _parse_analysis_response(self, response_text: str, user_preferences: str) -> Dict[str, Any]:
        """Parse Gemini response with enhanced error handling"""
        try:
            # Clean the response text
            cleaned_text = response_text.strip()
            
            # Find JSON in response
            start_idx = cleaned_text.find('{')
            end_idx = cleaned_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx != -1:
                json_str = cleaned_text[start_idx:end_idx]
                
                # Try to parse JSON
                analysis = json.loads(json_str)
                
                # Validate and ensure required fields exist
                analysis = self._validate_and_enhance_analysis(analysis, user_preferences)
                
                logger.info("Successfully parsed Gemini analysis response")
                return analysis
            else:
                raise ValueError("No JSON found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse Gemini response: {str(e)}")
            logger.debug(f"Response text: {response_text[:500]}...")
            return self._enhanced_fallback_analysis(user_preferences)
    
    def _validate_and_enhance_analysis(self, analysis: Dict[str, Any], user_preferences: str) -> Dict[str, Any]:
        """Validate and enhance the analysis with required fields"""
        
        # Ensure required fields exist with defaults
        required_fields = {
            'room_type': 'bedroom',
            'current_style': 'modern',
            'color_palette': ['white', 'gray', 'beige'],
            'existing_furniture': ['furniture'],
            'room_size': 'medium',
            'lighting': 'natural',
            'improvement_opportunities': ['general_improvement'],
            'style_confidence': 0.7
        }
        
        for field, default_value in required_fields.items():
            if field not in analysis or not analysis[field]:
                analysis[field] = default_value
        
        # Ensure Pinterest search params exist and are complete
        if 'pinterest_search_params' not in analysis or not analysis['pinterest_search_params']:
            analysis['pinterest_search_params'] = self._generate_default_pinterest_params(user_preferences, analysis)
        else:
            # Validate Pinterest params structure
            pinterest_params = analysis['pinterest_search_params']
            if 'search_terms' not in pinterest_params or len(pinterest_params['search_terms']) < 3:
                pinterest_params['search_terms'] = self._generate_default_search_terms(user_preferences, analysis)
            
            if 'style_keywords' not in pinterest_params:
                pinterest_params['style_keywords'] = [analysis.get('current_style', 'modern'), 'cozy']
            
            if 'color_searches' not in pinterest_params:
                pinterest_params['color_searches'] = self._generate_default_color_searches(analysis)
        
        # Add timestamp and API info
        analysis['analyzed_at'] = datetime.now().isoformat()
        analysis['api_version'] = 'new_genai_client'
        
        return analysis
    
    def _generate_default_pinterest_params(self, user_preferences: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate default Pinterest search parameters"""
        
        room_type = analysis.get('room_type', 'bedroom')
        style = analysis.get('current_style', 'modern')
        
        return {
            "search_terms": self._generate_default_search_terms(user_preferences, analysis),
            "style_keywords": [style, "modern", "cozy"],
            "color_searches": self._generate_default_color_searches(analysis)
        }
    
    def _generate_default_search_terms(self, user_preferences: str, analysis: Dict[str, Any]) -> List[str]:
        """Generate default search terms"""
        
        room_type = analysis.get('room_type', 'bedroom')
        style = analysis.get('current_style', 'modern')
        
        return [
            f"{user_preferences} {room_type} design",
            f"{style} {room_type} inspiration",
            f"{room_type} makeover ideas",
            f"trending {room_type} decor",
            f"{user_preferences} interior design"
        ]
    
    def _generate_default_color_searches(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate default color searches"""
        
        style = analysis.get('current_style', 'modern')
        room_type = analysis.get('room_type', 'bedroom')
        
        return [
            f"{style} color palette",
            f"{room_type} color schemes",
            "neutral interior colors"
        ]
    
    def _enhanced_fallback_analysis(self, user_preferences: str) -> Dict[str, Any]:
        """Enhanced fallback analysis based on user preferences"""
        
        # Extract style hints from user preferences
        style = "modern"
        room_type = "bedroom"
        
        # Style detection
        preferences_lower = user_preferences.lower()
        if "cozy" in preferences_lower:
            style = "cozy"
        elif "rustic" in preferences_lower:
            style = "rustic"
        elif "minimalist" in preferences_lower:
            style = "minimalist"
        elif "traditional" in preferences_lower:
            style = "traditional"
        elif "scandinavian" in preferences_lower:
            style = "scandinavian"
        
        # Room type detection
        if "living" in preferences_lower:
            room_type = "living_room"
        elif "dining" in preferences_lower:
            room_type = "dining_room"
        elif "office" in preferences_lower:
            room_type = "office"
        elif "kitchen" in preferences_lower:
            room_type = "kitchen"
        
        return {
            "room_type": room_type,
            "current_style": "traditional",
            "color_palette": ["beige", "brown", "white"],
            "existing_furniture": ["bed", "nightstand", "dresser"],
            "room_size": "medium",
            "lighting": "natural",
            "architectural_features": ["standard_ceiling", "windows"],
            "improvement_opportunities": [
                "modern_furniture_upgrade",
                "better_lighting_setup",
                "color_coordination",
                "storage_optimization"
            ],
            "style_confidence": 0.7,
            "design_problems": ["outdated_furniture", "inconsistent_styling"],
            "preservation_elements": ["room_layout", "natural_lighting"],
            "pinterest_search_params": {
                "search_terms": [
                    f"{user_preferences} {room_type} design",
                    f"{style} {room_type} inspiration",
                    f"{room_type} decor ideas",
                    f"{style} home decor",
                    f"trending {room_type} 2024"
                ],
                "style_keywords": [style, "modern", "cozy"],
                "color_searches": [
                    f"{style} color palette",
                    f"{room_type} colors",
                    "neutral home colors"
                ]
            },
            "analysis_method": "enhanced_fallback",
            "video_analysis_notes": f"Fallback analysis based on user preferences: {user_preferences}",
            "analyzed_at": datetime.now().isoformat(),
            "api_version": "new_genai_client"
        }
