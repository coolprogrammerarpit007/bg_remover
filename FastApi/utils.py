from rembg import remove

def remove_bg_bytes(image_bytes: bytes) -> bytes:
    return remove(image_bytes)
