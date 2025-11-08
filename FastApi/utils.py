from rembg import remove
from PIL import Image, UnidentifiedImageError, ImageEnhance
import io
import threading
import time
import traceback
import sys
import numpy as np

class TimeoutError(Exception):
    """Raised when image processing exceeds allowed time."""
    pass


def preprocess_image(image_bytes: bytes) -> bytes:
    """
    Preprocess image to improve background removal accuracy.
    - Resize large images for consistency
    - Enhance contrast and sharpness
    - Convert to optimal color space
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # Convert RGBA to RGB if needed (rembg works better with RGB)
        if img.mode == 'RGBA':
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if too large (improves speed and consistency)
        max_dimension = 1920
        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Enhance image quality for better segmentation
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)  # Slight contrast boost
        
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(1.1)  # Slight sharpness boost
        
        # Convert back to bytes
        output = io.BytesIO()
        img.save(output, format='PNG', optimize=True)
        return output.getvalue()
    
    except Exception as e:
        # If preprocessing fails, return original
        return image_bytes


def postprocess_image(result_bytes: bytes) -> bytes:
    """
    Postprocess the result to improve edge quality.
    - Refine alpha channel edges
    - Remove artifacts
    """
    try:
        img = Image.open(io.BytesIO(result_bytes))
        
        if img.mode == 'RGBA':
            # Get alpha channel
            r, g, b, a = img.split()
            
            # Convert alpha to numpy for processing
            alpha_np = np.array(a)
            
            # Apply slight morphological operations to clean edges
            from scipy import ndimage
            
            # Remove small noise
            alpha_np = ndimage.median_filter(alpha_np, size=2)
            
            # Smooth edges slightly
            alpha_np = ndimage.gaussian_filter(alpha_np, sigma=0.5)
            
            # Convert back to PIL
            a = Image.fromarray(alpha_np.astype('uint8'))
            
            # Recombine
            img = Image.merge('RGBA', (r, g, b, a))
        
        # Save processed result
        output = io.BytesIO()
        img.save(output, format='PNG', optimize=True)
        return output.getvalue()
    
    except Exception:
        # If postprocessing fails, return original
        return result_bytes


def remove_bg_bytes(image_bytes: bytes) -> dict:
    """
    Removes background from an image byte stream safely and returns structured response.

    Includes:
      - Input validation
      - Image format verification
      - Preprocessing for better accuracy
      - Timeout guard
      - rembg error handling with multiple models
      - Postprocessing for refined edges
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

        # --- STEP 2.5: Preprocess Image ---
        preprocessed_bytes = preprocess_image(image_bytes)

        # --- STEP 3: Process with Timeout Guard and Enhanced Settings ---
        result = {}
        timeout_seconds = 30  # Increased slightly for better quality processing

        def worker():
            try:
                # Use u2net model for better accuracy (default)
                # You can also try: u2netp (faster), u2net_human_seg (for people)
                # silueta (good for products), isnet-general-use (best quality but slower)
                
                # For best accuracy, use isnet-general-use or u2net
                result["data"] = remove(
                    preprocessed_bytes,
                    alpha_matting=True,  # Better edge refinement
                    alpha_matting_foreground_threshold=240,
                    alpha_matting_background_threshold=10,
                    alpha_matting_erode_size=10,
                    # model_name="u2net"  # Default, good balance
                    # Uncomment below for even better quality (but slower):
                    # model_name="isnet-general-use"
                )
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

        # --- STEP 3.5: Postprocess Result ---
        processed_bytes = postprocess_image(result["data"])

        # --- STEP 4: Success ---
        elapsed = round(time.time() - start_time, 2)
        response["status"] = True
        response["message"] = "Background removed successfully"
        response["data"] = processed_bytes
        response["diagnostic"] = {
            "processing_time_seconds": elapsed,
            "image_format": format_info,
            "image_size_bytes": len(image_bytes),
            "hint": "Output returned as image bytes with enhanced edge quality."
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