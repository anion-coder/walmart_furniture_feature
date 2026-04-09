from src.models.walmart_inventory import DatabaseManager
from src.utils.config import config

try:
    db = DatabaseManager(config['database']['url'])
    products = db.get_products_by_criteria(limit=10)
    
    print(f"Database has {len(products)} products")
    
    if products:
        sample = products[0]
        print(f"Sample: {sample['name']} - ${sample['price']}")
        
        # Show more details
        print("\nFirst 3 products:")
        for i, product in enumerate(products[:3]):
            print(f"  {i+1}. {product['name']} - ${product['price']} ({product['category']})")
    else:
        print("No products found - run setup_sample_data.py first")
        
except Exception as e:
    print(f"Database error: {e}")
