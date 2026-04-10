"""
Room video analysis agent using Qwen2.5-VL-7B-Instruct via HuggingFace
Inference API (serverless). No model download required.

Drop-in replacement for GeminiVideoAgent — same public API, same JSON output
structure, so the orchestrator can swap between them with a single config flag.
"""

import asyncio
import base64
import io
import json
import os
from datetime import datetime
from typing import Dict, Any, List

from PIL import Image
from huggingface_hub import InferenceClient

from ..services.video_utils import VideoProcessor
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class HuggingFaceVideoAgent:
    """Analyse room video frames with Qwen2.5-VL via HF Inference API."""

    def __init__(self, config: Dict[str, Any]):
        hf_cfg = config.get("ai_models", {}).get("huggingface", {}) or {}
        self.model_id = hf_cfg.get("model", "Qwen/Qwen2.5-VL-7B-Instruct")
        self.max_new_tokens = int(hf_cfg.get("max_tokens", 2048))
        self.temperature = float(hf_cfg.get("temperature", 0.3))
        self.num_frames = int(hf_cfg.get("num_frames", 3))

        # HF access token: config yaml > HF_TOKEN env var > cached login
        self.hf_token = (
            hf_cfg.get("access_token")
            or os.environ.get("HF_TOKEN")
            or None  # falls back to ~/.cache/huggingface/token via huggingface-cli login
        )

        self.video_processor = VideoProcessor()
        self.client = None
        self._init_client()

    # ------------------------------------------------------------------
    # Client init
    # ------------------------------------------------------------------

    def _init_client(self):
        """Initialise the HuggingFace Inference API client."""
        try:
            self.client = InferenceClient(
                model=self.model_id,
                token=self.hf_token,
            )
            logger.info(f"HF Inference client ready for {self.model_id}")
        except Exception as e:
            logger.error(f"Failed to create HF Inference client: {e}")
            self.client = None

    # ------------------------------------------------------------------
    # Public API  (same signature as GeminiVideoAgent)
    # ------------------------------------------------------------------

    async def analyze_room_video(
        self, video_path: str, user_preferences: str
    ) -> Dict[str, Any]:
        """Analyse a room video and return structured JSON analysis."""

        if self.client is None:
            logger.warning("HF client not available — returning fallback analysis")
            return self._enhanced_fallback_analysis(user_preferences)

        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"Video not found: {video_path}")

            # Extract key frames from the video
            frames = self.video_processor.extract_key_frames(
                video_path, num_frames=self.num_frames
            )
            pil_images = [Image.fromarray(f) for f in frames]

            # Run inference via API in a thread so we don't block the event loop
            analysis = await asyncio.to_thread(
                self._run_inference, pil_images, user_preferences
            )
            analysis["analysis_method"] = "qwen2_5_vl_api"
            analysis["model_used"] = self.model_id
            return analysis

        except Exception as e:
            logger.error(f"Video analysis failed: {e}")
            return self._enhanced_fallback_analysis(user_preferences)

    # ------------------------------------------------------------------
    # Inference via HF Inference API
    # ------------------------------------------------------------------

    @staticmethod
    def _image_to_base64_url(image: Image.Image) -> str:
        """Convert a PIL image to a base64 data URL for the API."""
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=85)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64}"

    def _run_inference(
        self, images: List[Image.Image], user_preferences: str
    ) -> Dict[str, Any]:
        """Send frames + prompt to HF Inference API, parse JSON response."""

        prompt_text = self._create_room_analysis_prompt(user_preferences)

        # Build multi-image content list for the chat_completion API
        content: list[dict] = []
        for img in images:
            content.append({
                "type": "image_url",
                "image_url": {"url": self._image_to_base64_url(img)},
            })
        content.append({"type": "text", "text": prompt_text})

        messages = [{"role": "user", "content": content}]

        response = self.client.chat_completion(
            messages=messages,
            max_tokens=self.max_new_tokens,
            temperature=self.temperature,
        )

        response_text = response.choices[0].message.content
        logger.info(f"HF API response length: {len(response_text)} chars")
        return self._parse_analysis_response(response_text, user_preferences)

    # ------------------------------------------------------------------
    # Prompts  (identical structure to GeminiVideoAgent)
    # ------------------------------------------------------------------

    def _create_room_analysis_prompt(self, user_preferences: str) -> str:
        return f"""You are a PROFESSIONAL INTERIOR DESIGNER with 15+ years of experience.

Analyze the room images provided. These are key frames from a video walkthrough of the room.

USER PREFERENCES: {user_preferences}

TASKS:
1. SPATIAL ASSESSMENT — room type, estimated size, architectural features, lighting
2. EXISTING ELEMENTS — current furniture, color palette, style coherence
3. DESIGN DIAGNOSIS — what works, what needs improvement
4. PINTEREST SEARCH STRATEGY — search terms for finding matching design inspiration

Return ONLY valid JSON (no markdown, no extra text):
{{
  "room_type": "bedroom/living_room/dining_room/office/kitchen",
  "current_style": "modern/traditional/rustic/minimalist/eclectic",
  "color_palette": ["primary_color", "secondary_color", "accent_color"],
  "existing_furniture": ["item1", "item2", "item3"],
  "room_size": "small/medium/large",
  "lighting": "bright/natural/dim",
  "architectural_features": ["feature1", "feature2"],
  "improvement_opportunities": ["improvement1", "improvement2"],
  "style_confidence": 0.85,
  "design_problems": ["problem1", "problem2"],
  "preservation_elements": ["keep_item1", "keep_item2"],
  "pinterest_search_params": {{
    "search_terms": [
      "{user_preferences} room design inspiration",
      "trending room decor 2024",
      "room makeover before after",
      "{user_preferences} interior design",
      "modern room styling ideas"
    ],
    "style_keywords": ["primary_style", "complementary_style"],
    "color_searches": [
      "room color scheme",
      "neutral room colors",
      "interior color palettes"
    ]
  }},
  "video_analysis_notes": "Specific observations from the room images"
}}"""

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_analysis_response(
        self, response_text: str, user_preferences: str
    ) -> Dict[str, Any]:
        try:
            cleaned = response_text.strip()
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start != -1 and end > start:
                analysis = json.loads(cleaned[start:end])
                analysis = self._validate_and_enhance(analysis, user_preferences)
                logger.info("Successfully parsed Qwen2.5-VL response")
                return analysis
            raise ValueError("No JSON object found in model output")
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse model response: {e}")
            logger.debug(f"Raw response: {response_text[:500]}")
            return self._enhanced_fallback_analysis(user_preferences)

    def _validate_and_enhance(
        self, analysis: Dict[str, Any], user_preferences: str
    ) -> Dict[str, Any]:
        defaults = {
            "room_type": "bedroom",
            "current_style": "modern",
            "color_palette": ["white", "gray", "beige"],
            "existing_furniture": ["furniture"],
            "room_size": "medium",
            "lighting": "natural",
            "improvement_opportunities": ["general_improvement"],
            "style_confidence": 0.7,
        }
        for field, default in defaults.items():
            if field not in analysis or not analysis[field]:
                analysis[field] = default

        # Ensure pinterest_search_params is complete
        psp = analysis.get("pinterest_search_params")
        if not psp or not isinstance(psp, dict):
            analysis["pinterest_search_params"] = self._default_pinterest_params(
                user_preferences, analysis
            )
        else:
            if "search_terms" not in psp or len(psp.get("search_terms", [])) < 3:
                psp["search_terms"] = self._default_search_terms(
                    user_preferences, analysis
                )
            if "style_keywords" not in psp:
                psp["style_keywords"] = [analysis.get("current_style", "modern"), "cozy"]
            if "color_searches" not in psp:
                psp["color_searches"] = self._default_color_searches(analysis)

        analysis["analyzed_at"] = datetime.now().isoformat()
        analysis["api_version"] = "qwen2_5_vl_inference_api"
        return analysis

    # ------------------------------------------------------------------
    # Fallback / defaults  (identical output to GeminiVideoAgent)
    # ------------------------------------------------------------------

    def _enhanced_fallback_analysis(self, user_preferences: str) -> Dict[str, Any]:
        prefs = user_preferences.lower()
        style = "modern"
        for s in ["cozy", "rustic", "minimalist", "traditional", "scandinavian"]:
            if s in prefs:
                style = s
                break
        room_type = "bedroom"
        for rt, kw in [("living_room", "living"), ("dining_room", "dining"),
                       ("office", "office"), ("kitchen", "kitchen")]:
            if kw in prefs:
                room_type = rt
                break

        return {
            "room_type": room_type,
            "current_style": "traditional",
            "color_palette": ["beige", "brown", "white"],
            "existing_furniture": ["bed", "nightstand", "dresser"],
            "room_size": "medium",
            "lighting": "natural",
            "architectural_features": ["standard_ceiling", "windows"],
            "improvement_opportunities": [
                "modern_furniture_upgrade", "better_lighting_setup",
                "color_coordination", "storage_optimization",
            ],
            "style_confidence": 0.7,
            "design_problems": ["outdated_furniture", "inconsistent_styling"],
            "preservation_elements": ["room_layout", "natural_lighting"],
            "pinterest_search_params": self._default_pinterest_params(
                user_preferences,
                {"room_type": room_type, "current_style": style},
            ),
            "analysis_method": "enhanced_fallback",
            "video_analysis_notes": f"Fallback based on preferences: {user_preferences}",
            "analyzed_at": datetime.now().isoformat(),
            "api_version": "qwen2_5_vl_inference_api",
        }

    def _default_pinterest_params(
        self, user_preferences: str, analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {
            "search_terms": self._default_search_terms(user_preferences, analysis),
            "style_keywords": [analysis.get("current_style", "modern"), "cozy"],
            "color_searches": self._default_color_searches(analysis),
        }

    @staticmethod
    def _default_search_terms(
        user_preferences: str, analysis: Dict[str, Any]
    ) -> List[str]:
        rt = analysis.get("room_type", "bedroom")
        st = analysis.get("current_style", "modern")
        return [
            f"{user_preferences} {rt} design",
            f"{st} {rt} inspiration",
            f"{rt} makeover ideas",
            f"trending {rt} decor",
            f"{user_preferences} interior design",
        ]

    @staticmethod
    def _default_color_searches(analysis: Dict[str, Any]) -> List[str]:
        st = analysis.get("current_style", "modern")
        rt = analysis.get("room_type", "bedroom")
        return [f"{st} color palette", f"{rt} color schemes", "neutral interior colors"]
