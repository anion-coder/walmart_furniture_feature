# scripts/setup_directories.py
import os
from pathlib import Path

def create_project_directories():
    """Create all required directories for the project"""
    
    directories = [
        "data/ar_assets/glb_files",
        "data/ar_assets/thumbnails", 
        "data/embeddings",
        "data/pinterest_cache",
        "data/walmart_products",
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")
    
    print("🎉 All project directories created successfully!")

if __name__ == "__main__":
    create_project_directories()
