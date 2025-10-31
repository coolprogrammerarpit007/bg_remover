from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from database import Base  

class ImageFile(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String(255), nullable=False)        
    original_path = Column(String(512), nullable=False)            
    processed_filename = Column(String(255), nullable=True)
    processed_path = Column(String(512), nullable=True)
    status = Column(String(32), default="uploaded", nullable=False) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
