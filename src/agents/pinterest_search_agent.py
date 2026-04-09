# src/agents/duckduckgo_pinterest_agent.py
from ddgs import DDGS
import asyncio
import requests
from PIL import Image
from io import BytesIO
from typing import Dict, Any, List, Optional
import time
import random
from urllib.parse import urlparse

from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class PinterestSearchAgent:
    """Fixed DuckDuckGo Pinterest search agent"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_images_per_search = 15
        self.max_total_images = 10
        self.search_delay = config.get('duckduckgo', {}).get('search_delay', 1.0)
        self.retry_attempts = config.get('duckduckgo', {}).get('retry_attempts', 3)
        
        # Enhanced headers to avoid blocking
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    async def search_trending_designs(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Search Pinterest content through DuckDuckGo with proper error handling"""
        
        try:
            search_terms = search_params.get('search_terms', [])
            style_keywords = search_params.get('style_keywords', [])
            
            # Create Pinterest-targeted search queries
            pinterest_queries = self._create_pinterest_queries(search_terms, style_keywords)
            
            # Execute searches with proper rate limiting
            all_images = []
            for i, query in enumerate(pinterest_queries):
                try:
                    logger.info(f"Searching DuckDuckGo for: {query}")
                    
                    images = await self._search_pinterest_images_with_retry(query)
                    all_images.extend(images)
                    
                    # Rate limiting with random delay
                    if i < len(pinterest_queries) - 1:  # Don't delay after last query
                        delay = self.search_delay + random.uniform(0.5, 1.5)
                        await asyncio.sleep(delay)
                    
                    if len(all_images) >= self.max_total_images * 2:  # Get extra for filtering
                        break
                        
                except Exception as e:
                    logger.warning(f"Search failed for query '{query}': {str(e)}")
                    continue
            
            # Filter and download best images
            if all_images:
                best_images = await self._filter_and_download_images(all_images)
                print(f"Best images: {best_images}")
                
                return {
                    "success": True,
                    "images": best_images,
                    "image_urls": [img['url'] for img in all_images],
                    "pinterest_urls": [img['url'] for img in all_images],
                    "search_queries_used": pinterest_queries,
                    "total_results": len(all_images)
                }
            else:
                logger.warning("No images found from DuckDuckGo searches")
                return self._fallback_pinterest_results()
            
        except Exception as e:
            logger.error(f"DuckDuckGo Pinterest search failed: {str(e)}")
            return self._fallback_pinterest_results()
    
    def _create_pinterest_queries(self, search_terms: List[str], style_keywords: List[str]) -> List[str]:
        """Create optimized Pinterest search queries"""
        
        pinterest_queries = []
        
        # Primary searches with Pinterest targeting
        for term in search_terms[:3]:
            pinterest_queries.extend([
                f"{term} site:pinterest.com",
                f"{term} pinterest inspiration",
                f"{term} pinterest ideas"
            ])
        
        # Style-specific searches
        for style in style_keywords[:2]:
            pinterest_queries.append(f"{style} room pinterest site:pinterest.com")
        print(f"Search terms: {search_terms}")
        print(f"Pinterest queries: {pinterest_queries}")
        print(f"Style keywords: {style_keywords}")
        return pinterest_queries[:6]  # Limit to prevent rate limiting
    
    async def _search_pinterest_images_with_retry(self, query: str) -> List[Dict[str, Any]]:
        """Search with retry logic and proper error handling"""
        
        for attempt in range(self.retry_attempts):
            try:
                return await self._search_pinterest_images(query)
            except Exception as e:
                logger.warning(f"Search attempt {attempt + 1} failed for '{query}': {str(e)}")
                if attempt < self.retry_attempts - 1:
                    # Exponential backoff
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All retry attempts failed for query '{query}'")
                    return []
        return []
    
    async def _search_pinterest_images(self, query: str) -> List[Dict[str, Any]]:
        """Corrected DuckDuckGo image search implementation"""
        
        try:
            ddgs = DDGS()
            # results = ddgs.images(keywords=query,max_results=self.max_images_per_search)
            # Use proper DuckDuckGo search context
            with DDGS(headers=self.headers, timeout=20) as ddgs:
                results = list(ddgs.images(
                    keywords=query,
                    region="us-en",
                    safesearch="moderate",
                    size=None,  # Let DuckDuckGo decide
                    color=None,
                    type_image=None,
                    layout=None,
                    license_image=None,
                    max_results=self.max_images_per_search
                ))
            
            # Filter for Pinterest sources
            pinterest_results = []
            for result in results:
                if self._is_pinterest_source(result):
                    pinterest_results.append({
                        'url': result.get('image'),
                        'title': result.get('title', ''),
                        'source': result.get('source', ''),
                        'thumbnail': result.get('thumbnail'),
                        'width': result.get('width'),
                        'height': result.get('height'),
                        'query': query
                    })
            
            logger.info(f"Found {len(pinterest_results)} Pinterest images for '{query}'")
            print(f"Pinterest results: {pinterest_results}")
            return pinterest_results
            
        except Exception as e:
            logger.error(f"DuckDuckGo search error for '{query}': {str(e)}")
            raise
    
    def _is_pinterest_source(self, result: Dict[str, Any]) -> bool:
        """Enhanced Pinterest source detection"""
        
        source = result.get('source', '').lower()
        url = result.get('image', '').lower()
        title = result.get('title', '').lower()
        
        # Check multiple indicators
        pinterest_indicators = [
            'pinterest' in source,
            'pinimg.com' in url,
            'pinterest.com' in source,
            'pin.it' in source,
            'pinterest' in title
        ]
        print(f"Pinterest indicators: {pinterest_indicators}")
        return any(pinterest_indicators)
    
    async def _filter_and_download_images(self, all_images: List[Dict[str, Any]]) -> List[Image.Image]:
        """Filter best images and download with error handling"""
        
        # Remove duplicates and sort by quality indicators
        unique_images = self._deduplicate_and_rank_images(all_images)
        best_images = unique_images[:self.max_total_images]
        
        downloaded_images = []
        for img_data in best_images:
            try:
                image = await self._download_image_safe(img_data['url'])
                if image:
                    downloaded_images.append(image)
                    
                # Small delay between downloads
                await asyncio.sleep(0.3)
                
            except Exception as e:
                logger.warning(f"Failed to download image from {img_data['url']}: {str(e)}")
                continue
        
        logger.info(f"Successfully downloaded {len(downloaded_images)} Pinterest images")
        print(f"Downloaded images: {downloaded_images}")
        return downloaded_images
    
    def _deduplicate_and_rank_images(self, images: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicates and rank by quality"""
        
        seen_urls = set()
        unique_images = []
        
        # Sort by potential quality indicators
        sorted_images = sorted(images, key=lambda x: (
            x.get('width', 0) * x.get('height', 0),  # Prefer larger images
            len(x.get('title', '')),  # Prefer images with descriptions
            'pinterest.com' in x.get('source', '').lower()  # Prefer direct Pinterest links
        ), reverse=True)
        
        for img in sorted_images:
            url = img.get('url', '')
            if url and url not in seen_urls:
                # Basic quality checks
                if self._is_valid_image_url(url):
                    seen_urls.add(url)
                    unique_images.append(img)
        
        return unique_images
    
    def _is_valid_image_url(self, url: str) -> bool:
        """Validate image URL"""
        try:
            parsed = urlparse(url)
            
            # Check for valid scheme and domain
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Check for image file extensions
            path = parsed.path.lower()
            image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.gif']
            
            # Pinterest images might not have extensions in URL
            if 'pinimg.com' in parsed.netloc or 'pinterest' in parsed.netloc:
                return True
            
            return any(path.endswith(ext) for ext in image_extensions)
            
        except:
            return False
    
    async def _download_image_safe(self, url: str) -> Optional[Image.Image]:
        """Safely download image with proper error handling"""
        
        try:
            # Use asyncio for non-blocking download
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.get(
                    url, 
                    headers=self.headers, 
                    timeout=15,
                    stream=True
                )
            )
            
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"Invalid content type for {url}: {content_type}")
                return None
            
            # Check file size (max 10MB)
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > 10 * 1024 * 1024:
                logger.warning(f"Image too large: {url}")
                return None
            
            # Download and process image
            image_data = response.content
            image = Image.open(BytesIO(image_data))
            
            # Validate image
            if image.width < 200 or image.height < 200:
                return None
            
            # Resize if too large
            if image.width > 1024 or image.height > 1024:
                image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            return image
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error downloading {url}: {str(e)}")
            return None
        except Exception as e:
            logger.warning(f"Error processing image from {url}: {str(e)}")
            return None
    
    def _fallback_pinterest_results(self) -> Dict[str, Any]:
        """Fallback when DuckDuckGo fails"""
        logger.warning("Using fallback Pinterest results")
        return {
            "success": False,
            "images": [],
            "pinterest_urls": [],
            "search_queries_used": [],
            "total_results": 0,
            "fallback": True,
            "message": "DuckDuckGo search unavailable, using cached results"
        }
