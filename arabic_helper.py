# -*- coding: utf-8 -*-
"""
Arabic text helper for Kivy mobile application.
Handles Arabic text reshaping and bidirectional (bidi) reordering
so Arabic labels render correctly on mobile screens.
"""
import os
import sys

_has_reshaper = False
_has_bidi = False

try:
    import arabic_reshaper
    _has_reshaper = True
except ImportError:
    pass

try:
    from bidi.algorithm import get_display
    _has_bidi = True
except ImportError:
    pass


def ar(text: str) -> str:
    """
    Reshape and reorder Arabic text for correct RTL visual rendering in Kivy.
    If text contains Arabic characters, it reshapes connecting letters and inverts display order.
    """
    if not text:
        return ""
    text_str = str(text)
    # Quick check if text contains Arabic characters (Unicode range 0x0600 - 0x06FF)
    has_arabic = any('\u0600' <= char <= '\u06FF' for char in text_str)
    if not has_arabic:
        return text_str

    try:
        reshaped = text_str
        if _has_reshaper:
            # Configure reshaper to keep numbers and punctuation intact
            configuration = {
                'delete_harakat': False,
                'support_ligatures': True,
            }
            reshaper = arabic_reshaper.ArabicReshaper(configuration=configuration)
            reshaped = reshaper.reshape(text_str)
        if _has_bidi:
            return get_display(reshaped)
        return reshaped
    except Exception:
        return text_str


def get_arabic_font() -> str:
    """
    Locates the best available TrueType font for Arabic rendering.
    Checks Android system fonts, Windows system fonts, and local assets.
    """
    candidate_paths = [
        # Local bundled asset (if packaged)
        os.path.join(os.path.dirname(__file__), "assets", "Cairo-Regular.ttf"),
        os.path.join(os.path.dirname(__file__), "assets", "arial.ttf"),
        # Android system fonts
        "/system/fonts/NotoNaskhArabic-Regular.ttf",
        "/system/fonts/NotoSansArabic-Regular.ttf",
        "/system/fonts/Roboto-Regular.ttf",
        "/system/fonts/DroidSansArabic.ttf",
        # Windows system fonts
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\tahoma.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        # Linux system fonts
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for p in candidate_paths:
        if os.path.exists(p):
            return p

    return "Roboto"  # Kivy default font fallback
