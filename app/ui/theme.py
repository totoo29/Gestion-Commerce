# app/ui/theme.py
"""
Tema visual (tokens) de DevMont Commerce.

Versión simplificada: un único esquema oscuro tipo SaaS,
sin cambio de modo claro/oscuro.
"""

from __future__ import annotations

from app.core.config import settings

# ── Paleta fija (dark SaaS) ───────────────────────────────────────────────────

COLORS: dict[str, str] = {
    # Superficies
    "bg_main": "#0B1220",
    "bg_panel": "#0F172A",
    "bg_card": "#111C33",
    "bg_input": "#0B1326",
    "bg_elevated": "#16233F",

    # Marca / acciones
    "primary": "#4F46E5",
    "primary_hover": "#4338CA",
    "primary_soft": "#232B53",

    "success": "#16A34A",
    "success_hover": "#15803D",
    "warning": "#F59E0B",
    "error": "#DC2626",
    "info": "#38BDF8",

    # Texto
    "text_primary": "#E5E7EB",
    "text_secondary": "#A8B0C2",
    "text_disabled": "#6B7280",
    "text_on_primary": "#FFFFFF",

    # Bordes / separadores
    "border": "#1F2A44",
    "border_subtle": "#17213A",
    "border_focus": "#4F46E5",

    # Botones neutrales
    "btn_neutral": "#111C33",
    "btn_neutral_hover": "#16233F",
    "btn_danger": "#DC2626",
    "btn_danger_hover": "#B91C1C",

    # Compat (nombres legacy usados en la app)
    "accent": "#4F46E5",
    "accent_hover": "#4338CA",
    "accent_light": "#A5B4FC",
    "btn_success": "#16A34A",
    "btn_success_hover": "#15803D",
}

# ── Tipografía ────────────────────────────────────────────────────────────────
FONTS = {
    "title": ("Segoe UI", 22, "bold"),
    "subtitle": ("Segoe UI", 16, "bold"),
    "heading": ("Segoe UI", 14, "bold"),
    "body": ("Segoe UI", settings.FONT_SIZE),
    "body_bold": ("Segoe UI", settings.FONT_SIZE, "bold"),
    "small": ("Segoe UI", max(11, settings.FONT_SIZE - 2)),
    "small_bold": ("Segoe UI", max(11, settings.FONT_SIZE - 2), "bold"),
    "mono": ("Consolas", settings.FONT_SIZE),
    "price": ("Consolas", 20, "bold"),
    "badge": ("Segoe UI", 10, "bold"),
}

# ── Layout tokens ─────────────────────────────────────────────────────────────
SIZES = {
    "window_w": 1280,
    "window_h": 768,

    "sidebar_w": 264,
    "sidebar_w_collapsed": 76,

    "padding": 16,
    "padding_sm": 8,
    "padding_lg": 24,

    "radius_sm": 10,
    "radius_md": 12,
    "radius_lg": 16,

    "btn_height": 40,
    "input_height": 38,
    "row_height": 36,
    "header_h": 56,
}
