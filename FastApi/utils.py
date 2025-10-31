import os
import io
from rembg import remove
from PIL import Image

def remove_background_local(input_path: str, output_path: str) -> None:
    """
    Remove background of image at input_path, write RGBA PNG to output_path.
    Raises exceptions on error.
    """
   
    with open(input_path, "rb") as f:
        input_bytes = f.read()

    
    result_bytes = remove(input_bytes)

    img = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, format="PNG")
