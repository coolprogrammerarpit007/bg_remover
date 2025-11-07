import os
import base64
import datetime
import socket
import re
import logging
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from database import get_db, Base, engine
from models import Image
from crud import save_image_record
from utils import remove_bg_bytes

# ------------------------------------------------------
# ENV & SETUP
# ------------------------------------------------------
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Background Remover API", version="2.0")

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------
# BASE URL DETECTION
# ------------------------------------------------------
def detect_base_url():
    env_url = os.getenv("BASE_URL")
    if env_url:
        return env_url.rstrip("/")

    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)

    if ip.startswith("127.") or ip.startswith("192.168"):
        return "http://localhost:9000"
    return f"http://{ip}:9000"


BASE_URL = detect_base_url()


# ------------------------------------------------------
# PATH CONFIGURATION
# ------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "images")
ORIGINAL_DIR = os.path.join(IMAGE_DIR, "originals")
PROCESSED_DIR = os.path.join(IMAGE_DIR, "processed")

for folder in [IMAGE_DIR, ORIGINAL_DIR, PROCESSED_DIR]:
    os.makedirs(folder, exist_ok=True)

# Serve images
app.mount("/images", StaticFiles(directory=IMAGE_DIR), name="images")


# ------------------------------------------------------
# RESPONSE HELPERS
# ------------------------------------------------------
def success_response(message, data=None):
    return {"status": True, "message": message, "data": data or {}}


def error_response(message):
    return {"status": False, "message": message, "data": {}}


# ------------------------------------------------------
# REQUEST MODELS
# ------------------------------------------------------
from pydantic import BaseModel

class ImageBase64(BaseModel):
    image_base64: str


# ------------------------------------------------------
# GLOBAL EXCEPTION HANDLER
# ------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled Error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content=error_response("Internal Server Error. Please try again later.")
    )


# ------------------------------------------------------
# API ROUTES
# ------------------------------------------------------
@app.post("/remove-bg")
async def remove_background(data: ImageBase64, db: Session = Depends(get_db)):
    try:
        # Clean base64
        try:
            image_base64_clean = re.sub(r'^data:image/\w+;base64,', "", data.image_base64)
            image_bytes = base64.b64decode(image_base64_clean)
        except Exception as e:
            logger.warning(f"Invalid base64 input: {e}")
            raise HTTPException(status_code=400, detail="Invalid Base64 string")

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        orig_name = f"orig_{timestamp}.png"
        proc_name = f"bg_{timestamp}.png"
        orig_path = os.path.join(ORIGINAL_DIR, orig_name)
        proc_path = os.path.join(PROCESSED_DIR, proc_name)

        # Save original image
        with open(orig_path, "wb") as f:
            f.write(image_bytes)

        # Background Removal with timeout
        try:
            processed_bytes = await run_in_threadpool(remove_bg_bytes, image_bytes)
        except TimeoutError:
            raise HTTPException(status_code=504, detail="Image processing timeout")
        except ValueError as ve:
            raise HTTPException(status_code=422, detail=f"Invalid Image Format: {ve}")
        except Exception as e:
            logger.error(f"Background removal failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to process image")

        # Save processed image
        with open(proc_path, "wb") as f:
            f.write(processed_bytes)

        # Save to DB
        img = save_image_record(
            db,
            original_file=f"images/originals/{orig_name}",
            processed_file=f"images/processed/{proc_name}"
        )

        logger.info(f"Background removed successfully: ID={img.id}")
        return success_response(
            "Background removed successfully",
            {
                "id": img.id,
                "original_url": f"{BASE_URL}/images/originals/{orig_name}",
                "processed_url": f"{BASE_URL}/images/processed/{proc_name}",
            }
        )

    except HTTPException as http_err:
        logger.warning(f"Client Error: {http_err.detail}")
        return error_response(str(http_err.detail))
    except Exception as e:
        logger.exception("Unexpected server error in /remove-bg")
        return error_response(f"Server Error: {str(e)}")


@app.get("/image/original/{image_id}")
async def get_original(image_id: int, db: Session = Depends(get_db)):
    img = db.query(Image).filter(Image.id == image_id).first()
    if not img:
        return error_response("Image not found")

    return success_response(
        "Original image URL",
        {"file_url": f"{BASE_URL}/{img.original_file}"}
    )


@app.get("/image/processed/{image_id}")
async def get_processed(image_id: int, db: Session = Depends(get_db)):
    img = db.query(Image).filter(Image.id == image_id).first()
    if not img:
        return error_response("Image not found")

    return success_response(
        "Processed image URL",
        {"file_url": f"{BASE_URL}/{img.processed_file}"}
    )


@app.get("/")
def home():
    return success_response("✅ FastAPI Background Remover API is running smoothly!")
