from sqlalchemy import Column, Integer, String, DateTime, func
from database import Base

class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    original_file = Column(String(255), nullable=False)
    processed_file = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())
