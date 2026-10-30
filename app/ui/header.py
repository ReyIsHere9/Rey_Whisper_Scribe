from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.ui.i18n import I18n
from app.ui.widgets import Ornament, TextureFrame


class Header(TextureFrame):
    new_job = Signal()
    theme_toggled = Signal()
    language_toggled = Signal()

    def __init__(self, i18n: I18n, theme: str, parent=None) -> None:
        super().__init__(
            texture="leather.webp",
            base="#5C1414",
            tint=(24, 10, 10, 168),
            border="#3A0D0D",
            parent=parent,
        )
        self.i18n = i18n
        self.theme = theme
        self.setObjectName("Header")
        self.setFixedHeight(94)

        row = QHBoxLayout(self)
        row.setContentsMargins(22, 12, 22, 12)
        row.setSpacing(16)

        self.crest = Ornament("crest.png", height=58, opacity=0.96)
        self.crest.setFixedWidth(70)
        row.addWidget(self.crest)

        titles = QVBoxLayout()
        titles.setSpacing(3)
        self.title = QLabel()
        self.title.setObjectName("AppTitle")
        self.subtitle = QLabel()
        self.subtitle.setObjectName("AppSubtitle")
        titles.addWidget(self.title)
        titles.addWidget(self.subtitle)
        row.addLayout(titles)
        row.addStretch(1)

        self.btn_language = QPushButton()
        self.btn_language.setProperty("variant", "header")
        self.btn_language.setToolTip("UI language")
        row.addWidget(self.btn_language)

        self.btn_theme = QPushButton()
        self.btn_theme.setProperty("variant", "header")
        self.btn_theme.setToolTip("Switch theme")
        row.addWidget(self.btn_theme)

        self.btn_new = QPushButton()
        self.btn_new.setObjectName("HeaderPrimary")
        row.addWidget(self.btn_new)

        self.btn_new.clicked.connect(self.new_job)
        self.btn_theme.clicked.connect(self.theme_toggled)
        self.btn_language.clicked.connect(self.language_toggled)

        self.retranslate()

    def retranslate(self) -> None:
        self.title.setText(self.i18n.t("app_title"))
        self.subtitle.setText(self.i18n.t("app_subtitle"))
        self.btn_language.setText("EN" if self.i18n.lang == "fa" else "فا")
        self.btn_theme.setText(
            self.i18n.t("theme_dark") if self.theme == "light" else self.i18n.t("theme_light")
        )
        self.btn_new.setText("+  " + self.i18n.t("new_job"))

    def set_theme(self, theme: str) -> None:
        self.theme = theme
        self.retranslate()
