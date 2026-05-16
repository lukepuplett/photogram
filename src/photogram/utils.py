"""Utility functions for image processing and validation."""

from pathlib import Path
from typing import List
from PIL import Image


def find_images(folder: Path, extensions: tuple = ('.jpg', '.jpeg', '.png')) -> List[Path]:
    """
    Find all image files in a folder.

    Args:
        folder: Path to search
        extensions: File extensions to look for (case-insensitive)

    Returns:
        List of image file paths

    Raises:
        ValueError: If no images found
    """
    folder = Path(folder)
    images = []

    for ext in extensions:
        images.extend(folder.glob(f'*{ext}'))
        images.extend(folder.glob(f'*{ext.upper()}'))

    if not images:
        raise ValueError(f"No images found in {folder}")

    return sorted(list(set(images)))  # Remove duplicates and sort


def validate_images(images: List[Path]) -> None:
    """
    Validate that all images are valid and loadable.

    Args:
        images: List of image paths to validate

    Raises:
        ValueError: If an image is corrupted or too small
    """
    min_width, min_height = 640, 480

    for img_path in images:
        try:
            with Image.open(img_path) as img:
                width, height = img.size
                if width < min_width or height < min_height:
                    raise ValueError(
                        f"Image too small: {img_path} ({width}x{height}). "
                        f"Minimum: {min_width}x{min_height}"
                    )
        except Exception as e:
            raise ValueError(f"Unable to open image {img_path}: {e}")


def estimate_required_memory(num_images: int, avg_image_size_mp: float) -> str:
    """
    Rough estimate of required RAM for processing.

    Args:
        num_images: Number of images
        avg_image_size_mp: Average image size in megapixels

    Returns:
        Human-readable memory estimate
    """
    # Very rough estimate: ~1GB per 50 images at 24MP
    gb_needed = (num_images * avg_image_size_mp) / (50 * 24)
    return f"~{int(gb_needed)}GB (rough estimate)"
