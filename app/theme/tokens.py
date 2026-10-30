from __future__ import annotations

from dataclasses import dataclass

RGBA = tuple[int, int, int, int]


@dataclass(frozen=True)
class Palette:
    name: str
    is_dark: bool
    bg: str
    bg_alt: str
    panel: str
    panel_alt: str
    text: str
    text_muted: str
    heading: str
    accent: str
    accent_hover: str
    accent_text: str
    border: str
    border_strong: str
    silver: str
    leather: str
    leather_dark: str
    chip: str
    chip_text: str
    selection: str
    paper_tex: str
    bg_tex: str
    overlay: RGBA
    ornament_opacity: float


PARCHMENT = Palette(
    name="Parchment",
    is_dark=False,
    bg="#F5F1EA",
    bg_alt="#EDE6DA",
    panel="#FBF8F2",
    panel_alt="#F3ECE1",
    text="#241C1A",
    text_muted="#6E5F58",
    heading="#4A0E0E",
    accent="#7E1B1B",
    accent_hover="#9B2226",
    accent_text="#FBF8F2",
    border="#D9CDBC",
    border_strong="#C3B49F",
    silver="#B9B0A2",
    leather="#5C1414",
    leather_dark="#3A0D0D",
    chip="#EFE7DA",
    chip_text="#5C4A3F",
    selection="#7E1B1B",
    paper_tex="paper.webp",
    bg_tex="paper.webp",
    overlay=(245, 241, 234, 96),
    ornament_opacity=1.0,
)

MIDNIGHT = Palette(
    name="Midnight Ink",
    is_dark=True,
    bg="#141112",
    bg_alt="#0F0D0D",
    panel="#1E191A",
    panel_alt="#241D1E",
    text="#EFE9E2",
    text_muted="#A79C96",
    heading="#F0E6D8",
    accent="#A32626",
    accent_hover="#C0392B",
    accent_text="#FFF6EE",
    border="#3A2E2E",
    border_strong="#544343",
    silver="#C9C9C9",
    leather="#3A1010",
    leather_dark="#1A0707",
    chip="#2A2223",
    chip_text="#D8CFC7",
    selection="#A32626",
    paper_tex="marble.webp",
    bg_tex="marble.webp",
    overlay=(20, 17, 18, 150),
    ornament_opacity=0.92,
)

THEMES = {"light": PARCHMENT, "dark": MIDNIGHT}


def palette_for(theme: str) -> Palette:
    return THEMES.get(theme, PARCHMENT)


SPEAKER_COLORS = [
    "#9B2226",
    "#2E4A6B",
    "#4C3A78",
    "#2F5D5A",
    "#8A6A3B",
    "#8C4A55",
    "#5B5F3A",
    "#4A5568",
    "#6B3A5E",
    "#A08A6A",
    "#3B4A8C",
    "#A14A2A",
]


def speaker_color(index: int) -> str:
    return SPEAKER_COLORS[index % len(SPEAKER_COLORS)]
