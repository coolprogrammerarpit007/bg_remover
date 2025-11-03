from sqlalchemy.orm import Session
from models import Image


def save_image_record(db, original_file, processed_file):
    db_img = Image(
        original_file=original_file,
        processed_file=processed_file
    )
    db.add(db_img)
    db.commit()
    db.refresh(db_img)
    return db_img
