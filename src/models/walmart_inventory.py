from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from typing import List, Dict, Any, Optional
import json

Base = declarative_base()

class WalmartProduct(Base):
    __tablename__ = "walmart_products"
    
    id = Column(Integer, primary_key=True)
    walmart_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100))
    subcategory = Column(String(100))
    price = Column(Float)
    description = Column(Text)
    color_primary = Column(String(50))
    color_secondary = Column(String(50))
    material = Column(String(100))
    style = Column(String(100))
    dimensions = Column(JSON)
    image_urls = Column(JSON)
    brand = Column(String(100))
    rating = Column(Float, default=4.0)
    stock_status = Column(String(20), default="in_stock")
    has_glb_file = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class ProcessingSession(Base):
    __tablename__ = "processing_sessions"
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(100), unique=True, nullable=False)
    user_id = Column(String(100))
    video_path = Column(String(500))
    user_preferences = Column(Text)
    status = Column(String(50), default="processing")
    progress = Column(Integer, default=0)
    recommendations = Column(JSON)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)

class DatabaseManager:
    def __init__(self, database_url: str):
        # More robust engine settings for cloud Postgres (e.g. Supabase)
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,          # recycle dead / timed-out connections
            pool_recycle=300,            # recycle connections every 5 minutes
            connect_args={"connect_timeout": 10},  # fail fast on connect issues
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self):
        return self.SessionLocal()
    
    def get_products_by_criteria(self, category: str = None, style: str = None, 
                                limit: int = 50) -> List[Dict[str, Any]]:
        """Get products matching criteria"""
        session = self.get_session()
        query = session.query(WalmartProduct).filter(
            WalmartProduct.stock_status == "in_stock",
            WalmartProduct.has_glb_file == True
        )
        
        if category:
            query = query.filter(WalmartProduct.category.ilike(f"%{category}%"))
        if style:
            query = query.filter(WalmartProduct.style.ilike(f"%{style}%"))
            
        products = query.limit(limit).all()
        session.close()
        
        return [self._product_to_dict(p) for p in products]
    
    def save_processing_session(self, session_data: Dict[str, Any]) -> str:
        """Save processing session to database"""
        session = self.get_session()
        
        processing_session = ProcessingSession(**session_data)
        session.add(processing_session)
        session.commit()
        
        session_id = processing_session.session_id
        session.close()
        return session_id
    
    def update_session_status(self, session_id: str, status: str, progress: int = None, 
                            recommendations: Dict[str, Any] = None, error: str = None):
        """Update processing session status"""
        session = self.get_session()
        
        processing_session = session.query(ProcessingSession).filter_by(session_id=session_id).first()
        if processing_session:
            processing_session.status = status
            if progress is not None:
                processing_session.progress = progress
            if recommendations:
                processing_session.recommendations = recommendations
            if error:
                processing_session.error_message = error
            if status == "completed":
                processing_session.completed_at = datetime.utcnow()
        
        session.commit()
        session.close()
    
    def get_session_recommendations(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get recommendations for session"""
        session = self.get_session()
        
        processing_session = session.query(ProcessingSession).filter_by(session_id=session_id).first()
        if processing_session and processing_session.recommendations:
            recommendations = processing_session.recommendations
            session.close()
            return recommendations
        
        session.close()
        return None
    
    def _product_to_dict(self, product: WalmartProduct) -> Dict[str, Any]:
        return {
            "id": product.id,
            "walmart_id": product.walmart_id,
            "name": product.name,
            "category": product.category,
            "subcategory": product.subcategory,
            "price": product.price,
            "description": product.description,
            "color_primary": product.color_primary,
            "color_secondary": product.color_secondary,
            "material": product.material,
            "style": product.style,
            "dimensions": product.dimensions,
            "image_urls": product.image_urls,
            "brand": product.brand,
            "rating": product.rating,
            "has_glb_file": product.has_glb_file
        }
