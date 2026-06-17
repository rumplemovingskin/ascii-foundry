from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

from ascii_foundry.core.settings import AsciiSettings


def preprocess_image(image: Image.Image, settings: AsciiSettings) -> Image.Image:
    processed = image
    if settings.blur > 0:
        processed = processed.filter(ImageFilter.GaussianBlur(radius=settings.blur))
    if settings.sharpen > 0:
        processed = processed.filter(
            ImageFilter.UnsharpMask(
                radius=1.0,
                percent=min(500, round(settings.sharpen * 150)),
                threshold=2,
            )
        )
    return processed


def apply_tone_curve(values: np.ndarray, settings: AsciiSettings) -> np.ndarray:
    """Apply brightness, contrast, gamma, and inversion to normalized luminance."""
    adjusted = values.astype(np.float32, copy=False)
    adjusted = (adjusted - 0.5) * settings.contrast + 0.5
    adjusted = adjusted + settings.brightness
    adjusted = np.clip(adjusted, 0.0, 1.0)
    if settings.gamma != 1.0:
        adjusted = np.power(adjusted, 1.0 / settings.gamma)
    if settings.invert:
        adjusted = 1.0 - adjusted
    return np.clip(adjusted, 0.0, 1.0)


def apply_luminance_preprocessing(values: np.ndarray, settings: AsciiSettings) -> np.ndarray:
    adjusted = apply_tone_curve(values, settings)
    if settings.edge_mode != "none" and settings.edge_strength > 0:
        edges = detect_edges(values)
        edge_image = 1.0 - edges
        strength = min(settings.edge_strength, 3.0) / 3.0
        adjusted = adjusted * (1.0 - strength) + edge_image * strength
    if settings.posterize_levels:
        levels = max(2, settings.posterize_levels)
        adjusted = np.rint(adjusted * (levels - 1)) / (levels - 1)
    if settings.threshold is not None:
        adjusted = (adjusted >= settings.threshold).astype(np.float32)
    return np.clip(adjusted, 0.0, 1.0)


def detect_edges(values: np.ndarray) -> np.ndarray:
    gradient_y, gradient_x = np.gradient(values.astype(np.float32, copy=False))
    edges = np.hypot(gradient_x, gradient_y)
    maximum = float(np.max(edges))
    if maximum <= 0:
        return np.zeros_like(values, dtype=np.float32)
    return np.clip(edges / maximum, 0.0, 1.0).astype(np.float32)
