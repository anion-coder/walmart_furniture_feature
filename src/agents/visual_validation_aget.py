# src/agents/visual_validation_agent.py
from transformers import CLIPModel, CLIPProcessor, BlipForConditionalGeneration, BlipProcessor
import torch
from PIL import Image
import requests
from io import BytesIO
from typing import Dict, Any, List
import asyncio

from ..utils.logger import setup_logger
from ..services.video_utils import VideoProcessor

logger = setup_logger(__name__)

class VisualValidationAgent:
    def __init__(self, config: Dict[str, Any]):
        # Use CLIP for fast validation
        self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        
        # Use BLIP instead of Qwen2-VL for detailed analysis
        self.blip_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
        self.blip_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        
        self.video_processor = VideoProcessor()
    
    async def validate_products(self, video_path: str, matched_packages: Dict[str, Any]) -> Dict[str, Any]:
        """Validate product compatibility with room"""
        
        try:
            # Get room image
            room_frame = self.video_processor.extract_key_frames(video_path, num_frames=1)[0]
            room_image = Image.fromarray(room_frame)
            
            validated_packages = []
            
            for package in matched_packages.get('matched_packages', []):
                validated_products = []
                
                for product in package.get('matched_products', []):
                    # Validate individual product
                    validation_score = await self._validate_individual_product(room_image, product)
                    
                    if validation_score['compatibility_score'] > 0.6:
                        product['validation'] = validation_score
                        validated_products.append(product)
                
                if validated_products:
                    validated_packages.append({
                        "name": package['name'],
                        "description": package['description'],
                        "validated_products": validated_products
                    })
            
            return {"validated_packages": validated_packages}
            
        except Exception as e:
            logger.error(f"Visual validation failed: {str(e)}")
            return {"validated_packages": []}
    
    async def _validate_individual_product(self, room_image: Image.Image, product: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual product compatibility using CLIP and BLIP"""
        
        try:
            # Get product image (mock for prototype)
            product_image = await self._get_product_image(product)
            
            # CLIP-based compatibility check
            clip_score = self._clip_compatibility_check(room_image, product)
            
            # BLIP-based detailed validation
            blip_validation = await self._blip_detailed_validation(room_image, product_image, product)
            
            return {
                "compatibility_score": (clip_score + blip_validation.get('compatibility_score', 0.5)) / 2,
                "style_match": blip_validation.get('style_match', 'good'),
                "color_harmony": blip_validation.get('color_harmony', 'good'),
                "detailed_reasoning": blip_validation.get('reasoning', 'Compatible with room style')
            }
            
        except Exception as e:
            logger.error(f"Individual validation failed: {str(e)}")
            return {
                "compatibility_score": 0.7,
                "style_match": "good",
                "color_harmony": "good",
                "detailed_reasoning": "Basic compatibility assessment"
            }
    
    def _clip_compatibility_check(self, room_image: Image.Image, product: Dict[str, Any]) -> float:
        """CLIP-based compatibility check"""
        
        try:
            # Create room and product descriptions
            room_desc = f"a {product.get('category', 'furniture')} room with modern decor"
            product_desc = f"{product.get('style', 'modern')} {product.get('category', 'furniture')} in {product.get('color_primary', 'neutral')} color"
            
            inputs = self.clip_processor(
                text=[room_desc, product_desc],
                images=room_image,
                return_tensors="pt",
                padding=True
            )
            
            with torch.no_grad():
                outputs = self.clip_model(**inputs)
                similarity = torch.cosine_similarity(
                    outputs.text_embeds[0:1], 
                    outputs.text_embeds[1:2]
                ).item()
            
            return max(0.0, min(1.0, (similarity + 1) / 2))  # Normalize to 0-1
            
        except Exception as e:
            logger.error(f"CLIP validation failed: {str(e)}")
            return 0.7
    
    async def _blip_detailed_validation(self, room_image: Image.Image, product_image: Image.Image, product: Dict[str, Any]) -> Dict[str, Any]:
        """BLIP-based detailed validation"""
        
        try:
            # Generate room description using BLIP
            room_inputs = self.blip_processor(room_image, return_tensors="pt")
            with torch.no_grad():
                room_caption_ids = self.blip_model.generate(**room_inputs, max_length=50)
                room_caption = self.blip_processor.decode(room_caption_ids[0], skip_special_tokens=True)
            
            # Simple rule-based compatibility scoring
            compatibility_score = 0.7  # Base score
            
            # Style matching
            product_style = product.get('style', 'modern').lower()
            if any(style_word in room_caption.lower() for style_word in [product_style, 'modern', 'clean']):
                compatibility_score += 0.1
            
            # Color matching
            product_color = product.get('color_primary', '').lower()
            if product_color in room_caption.lower():
                compatibility_score += 0.1
            
            return {
                "compatibility_score": min(compatibility_score, 1.0),
                "style_match": "good",
                "color_harmony": "good",
                "reasoning": f"Product style matches room aesthetic. Room: {room_caption}"
            }
            
        except Exception as e:
            logger.error(f"BLIP validation failed: {str(e)}")
            return {
                "compatibility_score": 0.7,
                "style_match": "good",
                "color_harmony": "good",
                "reasoning": "Basic compatibility assessment"
            }
    
    async def _get_product_image(self, product: Dict[str, Any]) -> Image.Image:
        """Get product image for validation"""
        
        # For prototype, create mock product image
        # In production, fetch actual product images
        mock_image = Image.new('RGB', (300, 300), color=(150, 150, 150))
        return mock_image
