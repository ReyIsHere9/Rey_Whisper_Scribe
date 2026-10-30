from __future__ import annotations

from string import Template

from app.theme.tokens import Palette


def _rgba(rgba: tuple[int, int, int, int]) -> str:
    return "rgba({}, {}, {}, {})".format(*rgba)


TEMPLATE = Template(
    """
* {
    font-family: "Segoe UI", "Tahoma", sans-serif;
    outline: none;
}
QWidget {
    color: $text;
    font-size: 13px;
}
QWidget#Root, QStackedWidget#Content {
    background: transparent;
}
QToolTip {
    background: $panel;
    color: $text;
    border: 1px solid $border;
    padding: 6px 8px;
}

QLabel { background: transparent; }
QLabel#AppTitle {
    font-family: "Georgia", "Cambria", serif;
    font-size: 25px;
    font-weight: 600;
    color: #F7F2E9;
    letter-spacing: 1px;
}
QLabel#AppSubtitle {
    font-size: 10px;
    color: rgba(247, 242, 233, 0.62);
    letter-spacing: 3px;
    text-transform: uppercase;
}
QLabel#SectionTitle {
    font-family: "Georgia", "Cambria", serif;
    font-size: 16px;
    font-weight: 600;
    color: $heading;
}
QLabel#Eyebrow {
    font-size: 10px;
    letter-spacing: 2px;
    color: $text_muted;
    text-transform: uppercase;
}
QLabel#Muted { color: $text_muted; }
QLabel#Heading {
    font-family: "Georgia", "Cambria", serif;
    font-size: 22px;
    font-weight: 600;
    color: $heading;
}
QLabel#Chip, QLabel#DemoChip, QLabel#StatusChip, QLabel#MetaChip {
    background: $chip;
    color: $chip_text;
    border: 1px solid $border;
    border-radius: 9px;
    padding: 3px 9px;
    font-size: 10px;
    letter-spacing: 0.5px;
}
QLabel#DemoChip {
    background: transparent;
    color: $accent;
    border: 1px solid $accent;
}
QLabel#StatusChip {
    background: transparent;
    border: 1px solid $border;
    color: $text_muted;
}
QLabel#SegText {
    color: $text;
    font-size: 14px;
    line-height: 150%;
}
QLabel#SegName {
    color: $heading;
    font-size: 12px;
    font-weight: 600;
}
QLabel#SegTime {
    color: $text_muted;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 10px;
}
QLabel#SpeakMeta { color: $text_muted; font-size: 11px; }
QLabel#JobTitle {
    color: #F3EDE4;
    font-size: 12px;
    font-weight: 600;
    background: transparent;
}
QLabel#JobMeta {
    color: rgba(243, 237, 228, 0.5);
    font-size: 10px;
    background: transparent;
}
QLabel#SidebarHeading {
    color: rgba(243, 237, 228, 0.42);
    font-size: 9px;
    letter-spacing: 2px;
    background: transparent;
}
QLabel#SidebarFoot {
    color: rgba(243, 237, 228, 0.3);
    font-size: 9px;
    background: transparent;
}
QLabel#EmptyTitle {
    font-family: "Georgia", "Cambria", serif;
    font-size: 26px;
    font-weight: 600;
    color: $heading;
}
QLabel#PlayerTitle { color: rgba(245, 241, 234, 0.62); font-size: 11px; }
QLabel#PlayerTime {
    color: rgba(245, 241, 234, 0.82);
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 11px;
}

QFrame#Header {
    background: $leather;
    border-bottom: 1px solid $leather_dark;
}
QFrame#Sidebar {
    background: $leather_dark;
}
QFrame#Panel {
    background: $panel;
    border: 1px solid $border;
    border-radius: 12px;
}
QFrame#PlayerBar {
    background: $leather_dark;
    border-top: 1px solid $leather;
}
QFrame#SegmentCard {
    background: $panel;
    border: 1px solid $border;
    border-radius: 10px;
}
QFrame#SegmentCard:hover {
    background: $panel_alt;
    border-color: $border_strong;
}
QFrame#SegmentCard[active="true"] {
    border-color: $accent;
    background: $panel_alt;
}
QFrame#SegmentCard[selected="true"] {
    border-color: $accent;
    background: $panel_alt;
}
QFrame#SpeakerRow {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
}
QFrame#SpeakerRow:hover {
    background: $panel_alt;
    border-color: $border;
}
QFrame#SpeakerRow[selected="true"] {
    border-color: $accent;
    background: $panel_alt;
}
QFrame#JobCard {
    background: transparent;
    border: 1px solid transparent;
    border-$side: 2px solid transparent;
    border-radius: 8px;
}
QFrame#JobCard:hover { background: rgba(255, 255, 255, 0.05); }
QFrame#JobCard[active="true"] {
    background: rgba(255, 255, 255, 0.08);
    border-$side: 2px solid $accent;
}
QFrame#Divider {
    background: $border;
    border: none;
}
QFrame#DropZone {
    background: $panel;
    border: 1px dashed $border_strong;
    border-radius: 12px;
}

QPushButton {
    background: $panel;
    color: $text;
    border: 1px solid $border;
    border-radius: 8px;
    padding: 7px 14px;
}
QPushButton:hover {
    border-color: $accent;
    color: $accent;
}
QPushButton:pressed { background: $panel_alt; }
QPushButton:disabled { color: $text_muted; border-color: $border; }

QPushButton#Primary {
    background: $accent;
    color: $accent_text;
    border: 1px solid $accent;
    font-weight: 600;
    padding: 9px 18px;
}
QPushButton#Primary:hover { background: $accent_hover; border-color: $accent_hover; }
QPushButton#Primary:disabled { background: $border_strong; border-color: $border_strong; }

QPushButton#HeaderPrimary {
    background: #F5F1EA;
    color: #4A0E0E;
    border: 1px solid rgba(255, 255, 255, 0.45);
    font-weight: 700;
    padding: 9px 17px;
    border-radius: 8px;
}
QPushButton#HeaderPrimary:hover { background: #FFFFFF; border-color: #FFFFFF; }

QPushButton#Ghost {
    background: transparent;
    border: 1px solid transparent;
    color: $text_muted;
    padding: 7px 10px;
}
QPushButton#Ghost:hover { color: $accent; background: $panel_alt; }

QPushButton[variant="header"] {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.16);
    color: #F5F0E8;
    padding: 7px 13px;
    border-radius: 8px;
}
QPushButton[variant="header"]:hover {
    background: rgba(255, 255, 255, 0.13);
    border-color: rgba(255, 255, 255, 0.3);
    color: #FFFFFF;
}
QPushButton[variant="nav"] {
    background: transparent;
    border: none;
    border-$side: 2px solid transparent;
    border-radius: 6px;
    text-align: $nav_align;
    padding: 9px 12px;
    color: rgba(245, 241, 234, 0.62);
    font-size: 13px;
}
QPushButton[variant="nav"]:hover {
    background: rgba(255, 255, 255, 0.06);
    color: #FBF8F2;
}
QPushButton[variant="nav"][active="true"] {
    background: rgba(255, 255, 255, 0.09);
    border-$side: 2px solid $accent;
    color: #FFFFFF;
}

QLineEdit, QComboBox, QSpinBox {
    background: $panel;
    color: $text;
    border: 1px solid $border;
    border-radius: 7px;
    padding: 6px 10px;
    min-height: 18px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border-color: $accent; }
QComboBox::drop-down { border: none; background: transparent; width: 22px; }
QComboBox QAbstractItemView {
    background: $panel;
    color: $text;
    border: 1px solid $border;
    selection-background-color: $accent;
    selection-color: $accent_text;
    padding: 4px;
}
QSpinBox::up-button, QSpinBox::down-button { width: 16px; border: none; }

QCheckBox { color: $text; spacing: 8px; }
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid $border_strong;
    border-radius: 4px;
    background: $panel;
}
QCheckBox::indicator:hover { border-color: $accent; }
QCheckBox::indicator:checked { background: $accent; border-color: $accent; }

QGroupBox {
    border: 1px solid $border;
    border-radius: 10px;
    margin-top: 14px;
    padding: 14px 12px 10px 12px;
    color: $text_muted;
    font-size: 11px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: $text_muted;
    letter-spacing: 1px;
}

QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: $border_strong;
    border-radius: 5px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover { background: $accent; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

QStatusBar {
    background: $bg_alt;
    border-top: 1px solid $border;
    color: $text_muted;
    font-size: 11px;
}
QStatusBar::item { border: none; }
QStatusBar QLabel, QStatusBar QWidget { background: transparent; }
QProgressBar {
    background: $border;
    border: none;
    border-radius: 3px;
}
QProgressBar::chunk {
    background: $accent;
    border-radius: 3px;
}
QPushButton#CancelButton {
    background: transparent;
    border: 1px solid $border_strong;
    color: $accent;
    padding: 1px 10px;
    border-radius: 6px;
    font-size: 11px;
}
QPushButton#CancelButton:hover { background: $panel_alt; }
QPushButton#CancelButton:disabled { color: $text_muted; }

QDialog { background: $bg; }
QDialog QLabel { color: $text; }

QSlider::groove:horizontal {
    height: 3px;
    background: $border;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 12px;
    margin: -5px 0;
    border-radius: 6px;
    background: $accent;
}
"""
)


def build_qss(p: Palette, rtl: bool = False) -> str:
    return TEMPLATE.substitute(
        nav_align="right" if rtl else "left",
        side="right" if rtl else "left",
        bg=p.bg,
        bg_alt=p.bg_alt,
        panel=p.panel,
        panel_alt=p.panel_alt,
        text=p.text,
        text_muted=p.text_muted,
        heading=p.heading,
        accent=p.accent,
        accent_hover=p.accent_hover,
        accent_text=p.accent_text,
        border=p.border,
        border_strong=p.border_strong,
        silver=p.silver,
        leather=p.leather,
        leather_dark=p.leather_dark,
        chip=p.chip,
        chip_text=p.chip_text,
        selection=p.selection,
    )
