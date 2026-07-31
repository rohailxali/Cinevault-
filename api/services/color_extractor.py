"""
api/services/color_extractor.py — Server-Side Dominant Color Extraction
=========================================================================
Extracts the dominant accent color from a title's backdrop/poster image
using ColorThief (Pillow-based k-means). Result is cached in the
CineVaultCache singleton, computed once per title on first access.

Design decisions:
- Lazy extraction: computed on first /api/titles/:id request, not at startup.
  This avoids blocking the server boot with 8k+ HTTP requests.
- Clamped luminance: raw dominant colors are often too dark or too light.
  We boost saturation and clamp L to a usable display range (30-70%).
- Fallback: any failure silently returns None; the frontend falls back to
  the global brand gold (#C9A24B).
- Thread-safe: pure function, no shared state. The cache update is atomic
  (dict assignment in CPython is GIL-protected).
"""

from __future__ import annotations

import io
import colorsys
from typing import Optional

import httpx
from colorthief import ColorThief


def _rgb_to_hsl(r: int, g: int, b: int) -> tuple[float, float, float]:
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return h, s, l


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "#{:02X}{:02X}{:02X}".format(int(r * 255), int(g * 255), int(b * 255))


def _is_too_neutral(r: int, g: int, b: int, threshold: float = 0.08) -> bool:
    """Returns True if the color is near-grey (low saturation)."""
    _, s, _ = _rgb_to_hsl(r, g, b)
    return s < threshold


def extract_accent_color(image_url: str, timeout: float = 5.0) -> Optional[str]:
    """
    Download an image from `image_url` and extract a visually distinct
    accent color suitable for use in UI gradients and glows.

    Returns a hex color string (e.g. "#4A7BC8") or None on failure.
    """
    try:
        response = httpx.get(image_url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()

        img_bytes = io.BytesIO(response.content)
        ct = ColorThief(img_bytes)

        # Get top 6 colors; skip near-neutral ones to find an interesting accent
        palette = ct.get_palette(color_count=6, quality=3)

        chosen: Optional[tuple[int, int, int]] = None
        for rgb in palette:
            if not _is_too_neutral(*rgb):
                chosen = rgb
                break

        # Fall back to most dominant if all are neutral
        if chosen is None:
            chosen = palette[0]

        r, g, b = chosen
        h, s, l = _rgb_to_hsl(r, g, b)

        # Clamp: boost saturation slightly, enforce readable luminance range
        s = min(1.0, s * 1.3)           # boost saturation 30%
        l = max(0.30, min(0.65, l))     # clamp L to 30%-65%

        return _hsl_to_hex(h, s, l)

    except Exception:
        # Any network error, decode error, etc. → silently return None
        return None
