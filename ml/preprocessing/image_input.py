"""Image decoding shared by training and inference."""
from io import BytesIO
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 20_000_000
FORMATS = {"PNG", "JPEG", "WEBP", "GIF", "BMP", "TIFF", "AVIF"}


def decode_image(data):
    if not data:
        raise ValueError("The image is empty")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("The image exceeds the 10 MB limit")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as original:
                if original.format not in FORMATS:
                    raise ValueError("Unsupported inference image format; use PNG, JPEG, WebP, GIF, BMP, TIFF, or AVIF")
                if original.width * original.height > MAX_IMAGE_PIXELS:
                    raise ValueError("The image exceeds the 20 megapixel decoding limit")
                original.seek(0)
                return ImageOps.exif_transpose(original).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        raise ValueError("The image is corrupt, unsupported, or unsafe to decode") from error
