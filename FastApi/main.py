import os, base64, datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import re

from database import get_db
from models import Image
from crud import save_image_record
from utils import remove_bg_bytes
from database import Base, engine
Base.metadata.create_all(bind=engine)

# Load ENV
load_dotenv()
BASE_URL = os.getenv("BASE_URL", "http://localhost:9000")

app = FastAPI(title="Background Remover API")

# ✅ Base directory of this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ✅ Image directories
IMAGE_DIR = os.path.join(BASE_DIR, "images")
ORIGINAL_DIR = os.path.join(IMAGE_DIR, "originals")
PROCESSED_DIR = os.path.join(IMAGE_DIR, "processed")

# ✅ Create folders if not exists
os.makedirs(ORIGINAL_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# ✅ Static file mount
app.mount("/images", StaticFiles(directory=IMAGE_DIR), name="images")


# ✅ Schema for Base64 input
class ImageBase64(BaseModel):
    image_base64: str


@app.post("/remove-bg")
async def remove_background(data: ImageBase64, db: Session = Depends(get_db)):
    try:
        # Remove "data:image/...;base64," prefix if exists
        image_base64_clean = re.sub('^data:image/\\w+;base64,', '', data.image_base64)

        # Convert to bytes
        image_bytes = base64.b64decode(image_base64_clean)
    except:
        raise HTTPException(status_code=400, detail="Invalid Base64 string")

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    orig_name = f"orig_{timestamp}.png"
    proc_name = f"bg_{timestamp}.png"

    orig_path = os.path.join(ORIGINAL_DIR, orig_name)
    proc_path = os.path.join(PROCESSED_DIR, proc_name)

    # Save original image
    with open(orig_path, "wb") as f:
        f.write(image_bytes)

    # Remove background
    processed_bytes = remove_bg_bytes(image_bytes)

    # Save processed image
    with open(proc_path, "wb") as f:
        f.write(processed_bytes)

    # Save DB record
    img = save_image_record(
        db,
        original_file=f"images/originals/{orig_name}",
        processed_file=f"images/processed/{proc_name}"
    )

    return {
        "id": img.id,
        "original_url": f"{BASE_URL}/images/originals/{orig_name}",
        "processed_url": f"{BASE_URL}/images/processed/{proc_name}"
    }


@app.get("/image/original/{image_id}")
async def get_original(image_id: int, db: Session = Depends(get_db)):
    img = db.query(Image).filter(Image.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    return {"file_url": f"{BASE_URL}/{img.original_file}"}


@app.get("/image/processed/{image_id}")
async def get_processed(image_id: int, db: Session = Depends(get_db)):
    img = db.query(Image).filter(Image.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    return {"file_url": f"{BASE_URL}/{img.processed_file}"}


@app.get("/")
def read_root():
    return {"message": "FastAPI + MySQL Background Remover API Running ✅"}
