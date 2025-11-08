from rembg import remove
from PIL import Image, UnidentifiedImageError
import io
import threading
import time
import traceback
import sys

class TimeoutError(Exception):
    """Raised when image processing exceeds allowed time."""
    pass


def remove_bg_bytes(image_bytes: bytes) -> dict:
    """
    Removes background from an image byte stream safely and returns structured response.

    Includes:
      - Input validation
      - Image format verification
      - Timeout guard
      - rembg error handling
      - Detailed diagnostic messages for debugging
    """

    start_time = time.time()
    response = {
        "status": False,
        "message": "",
        "data": {},
        "diagnostic": {},
    }

    try:
        # --- STEP 1: Validate Input ---
        if not image_bytes or len(image_bytes) < 50:
            response["message"] = "Invalid or empty image data"
            response["diagnostic"] = {
                "hint": "Ensure you're sending a valid image file.",
                "received_size_bytes": len(image_bytes) if image_bytes else 0,
            }
            return response

        # --- STEP 2: Validate Image ---
        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                img.verify()
                format_info = img.format
        except UnidentifiedImageError:
            response["message"] = "Unsupported or corrupted image format"
            response["diagnostic"] = {
                "hint": "Image format not recognized. Try PNG or JPG.",
                "trace": traceback.format_exc(),
            }
            return response
        except Exception as e:
            response["message"] = f"Image validation failed: {e}"
            response["diagnostic"] = {
                "hint": "Image might be partially corrupted or truncated.",
                "trace": traceback.format_exc(),
            }
            return response

        # --- STEP 3: Process with Timeout Guard ---
        result = {}
        timeout_seconds = 20

        def worker():
            try:
                result["data"] = remove(image_bytes)
            except Exception as e:
                result["error"] = e

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        thread.join(timeout_seconds)

        # --- Timeout Handling ---
        if thread.is_alive():
            response["message"] = "Image processing exceeded time limit"
            response["diagnostic"] = {
                "hint": "rembg may be stuck on complex background segmentation.",
                "suggestion": "Resize image below 1500px width before retrying.",
                "timeout_seconds": timeout_seconds,
            }
            return response

        # --- Error Handling from rembg ---
        if "error" in result:
            err = result["error"]
            response["message"] = "Background removal failed internally"
            response["diagnostic"] = {
                "exception_type": type(err).__name__,
                "error_message": str(err),
                "trace": traceback.format_exc(),
                "suggestion": "Ensure rembg is properly installed and the image is clear."
            }
            return response

        # --- Unknown failure ---
        if "data" not in result:
            response["message"] = "Unknown background removal failure"
            response["diagnostic"] = {
                "hint": "Unexpected internal state. Possibly rembg did not return output.",
                "trace": traceback.format_exc(),
            }
            return response

        # --- STEP 4: Success ---
        elapsed = round(time.time() - start_time, 2)
        response["status"] = True
        response["message"] = "Background removed successfully"
        response["data"] = result["data"]
        response["diagnostic"] = {
            "processing_time_seconds": elapsed,
            "image_format": format_info,
            "image_size_bytes": len(image_bytes),
            "hint": "Output returned as image bytes. Convert to file or Base64 if needed."
        }
        return response

    except Exception as e:
        # --- Fallback for Unexpected Errors ---
        exc_type, exc_value, exc_tb = sys.exc_info()
        response["message"] = f"Unhandled exception: {e}"
        response["diagnostic"] = {
            "exception_type": str(exc_type),
            "traceback": traceback.format_exc(),
            "suggestion": "Check server logs and ensure rembg dependencies are correctly installed.",
        }
        return response



