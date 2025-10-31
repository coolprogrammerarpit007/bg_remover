from sqlalchemy.orm import Session
from models import ImageFile
from datetime import datetime

def create_image_record(db: Session, original_filename: str, original_path: str):
    img = ImageFile(
        original_filename=original_filename,
        original_path=original_path,
        status="uploaded"
    )
    db.add(img)
    db.commit()
    db.refresh(img)
    return img

def update_processing_started(db: Session, img: ImageFile):
    img.status = "processing"
    db.commit()
    db.refresh(img)
    return img

def update_processing_done(db: Session, img: ImageFile, processed_filename: str, processed_path: str):
    img.processed_filename = processed_filename
    img.processed_path = processed_path
    img.status = "done"
    img.processed_at = datetime.utcnow()
    db.commit()
    db.refresh(img)
    return img

def update_processing_failed(db: Session, img: ImageFile, error_msg: str = None):
    img.status = "failed"
    db.commit()
    db.refresh(img)
    return img

def get_image(db: Session, image_id: int):
    return db.query(ImageFile).filter(ImageFile.id == image_id).first()