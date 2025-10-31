import os
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import aiofiles
import uuid
from database import get_db, Base, engine
from crud import create_image_record, update_processing_started, update_processing_done, update_processing_failed, get_image
from utils import remove_background_local
import sys


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Background Remover API")


app.mount("/images", StaticFiles(directory="images"), name="images")

UPLOAD_DIR = "images"
ORIGINALS_DIR = os.path.join(UPLOAD_DIR, "originals")
PROCESSED_DIR = os.path.join(UPLOAD_DIR, "processed")

os.makedirs(ORIGINALS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

ALLOWED_CONTENT = {"image/png", "image/jpeg", "image/webp", "image/jpg"}


@app.post("/upload", status_code=201)
async def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type not in ALLOWED_CONTENT:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    ext = file.filename.split(".")[-1]
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    orig_path = os.path.join(ORIGINALS_DIR, unique_name)

    async with aiofiles.open(orig_path, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)

    
    orig_url = f"/images/originals/{unique_name}"
    img_record = create_image_record(db, file.filename, orig_url)

    try:
        update_processing_started(db, img_record)

        processed_name = f"{uuid.uuid4().hex}.png"
        processed_path = os.path.join(PROCESSED_DIR, processed_name)

        
        remove_background_local(orig_path, processed_path)

        processed_url = f"/images/processed/{processed_name}"
        update_processing_done(db, img_record, processed_name, processed_url)

    except Exception as e:
        update_processing_failed(db, img_record, str(e))
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")

    return {
        "id": img_record.id,
        "original_url": orig_url,
        "processed_url": processed_url,
        "status": img_record.status
    }


@app.get("/images/{image_id}")
def get_image_info(image_id: int, db: Session = Depends(get_db)):
    img = get_image(db, image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    return {
        "id": img.id,
        "original_url": img.original_path,
        "processed_url": img.processed_path,
        "status": img.status,
        "created_at": img.created_at,
        "processed_at": img.processed_at,
    }


@app.get("/download/original/{image_id}")
def download_original(image_id: int, db: Session = Depends(get_db)):
    img = get_image(db, image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Not found")

    local_path = img.original_path.replace("/images", "images")
    if not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="File missing")

    return FileResponse(local_path, filename=img.original_filename)


@app.get("/download/processed/{image_id}")
def download_processed(image_id: int, db: Session = Depends(get_db)):
    img = get_image(db, image_id)
    if not img or img.status != "done":
        raise HTTPException(status_code=404, detail="Processed image not available")

    local_path = img.processed_path.replace("/images", "images")
    if not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail="File missing")

    suggested_name = f"processed_{img.original_filename.rsplit('.',1)[0]}.png"
    return FileResponse(local_path, filename=suggested_name)


@app.get("/")
def read_root():
    return {"message": "FastAPI + MySQL Background Remover API Running"}
