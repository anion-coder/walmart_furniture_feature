from typing import Dict, Any, List, Tuple
import asyncio

from ..models.embedding_index import ProductEmbeddingIndex
from ..models.walmart_inventory import DatabaseManager
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class ProductMatchAgent:
    def __init__(self, config: Dict[str, Any]):
        self.db_manager = DatabaseManager(config['database']['url'])
        self.embedding_index = ProductEmbeddingIndex()
        self._initialize_index()
    
    def _initialize_index(self):
        """Initialize product embedding index"""
        try:
            # Load existing index or build new one
            try:
                self.embedding_index.load_index("./data/embeddings")
                logger.info("Loaded existing product embedding index")
            except:
                logger.info("Building new product embedding index")
                products = self.db_manager.get_products_by_criteria(limit=1000)
                self.embedding_index.build_index(products)
                self.embedding_index.save_index("./data/embeddings")
        except Exception as e:
            logger.error(f"Failed to initialize embedding index: {str(e)}")
    
    async def match_products_to_packages(self, design_packages: Dict[str, Any]) -> Dict[str, Any]:
        """Match design packages to actual Walmart products"""
        
        try:
            matched_packages = []
            
            for package in design_packages.get('packages', []):
                matched_products = []
                
                for product_spec in package.get('products', []):
                    # Find matching products
                    matches = await self._find_matching_products(product_spec)
                    matched_products.extend(matches)
                
                matched_packages.append({
                    "name": package['name'],
                    "description": package['description'],
                    "matched_products": matched_products
                })
            
            print(f"Matched packages: {matched_packages}")
            return {"matched_packages": matched_packages}
            
        except Exception as e:
            logger.error(f"Product matching failed: {str(e)}")
            return {"matched_packages": []}
    
    async def _find_matching_products(self, product_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find Walmart products matching specification"""
        
        # Create search query from specification
        search_query = f"{product_spec.get('material', '')} {product_spec.get('color', '')} {product_spec.get('item_type', '')} {product_spec.get('name', '')}"
        
        # Search embedding index
        similar_products = self.embedding_index.search_similar(search_query, top_k=20)
        
        # Get product details from database
        matched_products = []
        for walmart_id, similarity_score in similar_products:
            products = self.db_manager.get_products_by_criteria(limit=1000)
            product = next((p for p in products if p['walmart_id'] == walmart_id), None)
            
            if product:
                product['similarity_score'] = similarity_score
                product['spec_match'] = product_spec
                matched_products.append(product)
        
        print(f"Matched products: {matched_products[:5]}")
        return matched_products[:5]  # Return top 5 matches
