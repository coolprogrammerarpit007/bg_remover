from rembg import remove
from PIL import Image
import io
import threading
import time

class TimeoutError(Exception):
    """Raised when image processing exceeds allowed time."""
    pass


def remove_bg_bytes(image_bytes: bytes) -> bytes:
    """
    Removes background from an image byte stream safely.
    Works cross-platform (Windows, Linux, macOS).
    Includes:
      - validation
      - corruption check
      - timeout guard (20s)
      - rembg safe handling
    """
    if not image_bytes or len(image_bytes) < 50:
        raise ValueError("Invalid or empty image data")

    # Validate image first
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.verify()
    except Exception:
        raise ValueError("Corrupted or unsupported image format")

    # Timeout wrapper
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

    if thread.is_alive():
        # Thread still running → timeout
        raise TimeoutError("Image processing exceeded time limit")

    if "error" in result:
        raise RuntimeError(f"Background removal failed: {result['error']}")

    if "data" not in result:
        raise RuntimeError("Unknown background removal failure")

    return result["data"]
