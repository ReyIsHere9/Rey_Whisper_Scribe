from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from app.paths import data_dir, models_dir
from app.ui.i18n import I18n


class SettingsDialog(QDialog):
    def __init__(self, i18n: I18n, db, parent=None) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self.db = db
        self.theme_value = db.setting("theme", "light")
        self.lang_value = db.setting("language", "en")
        self.setWindowTitle(i18n.t("settings"))
        self.setModal(True)
        self.setMinimumWidth(620)
        self.resize(660, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(12)

        heading = QLabel(i18n.t("settings"))
        heading.setObjectName("Heading")
        layout.addWidget(heading)

        appearance = QGroupBox(i18n.t("appearance"))
        appearance_grid = QGridLayout(appearance)
        appearance_grid.setHorizontalSpacing(14)
        appearance_grid.setVerticalSpacing(10)
        appearance_grid.addWidget(QLabel(i18n.t("theme")), 0, 0)
        self.theme = QComboBox()
        self.theme.addItem(i18n.t("theme_light"), "light")
        self.theme.addItem(i18n.t("theme_dark"), "dark")
        self._select(self.theme, self.theme_value)
        appearance_grid.addWidget(self.theme, 0, 1)
        appearance_grid.addWidget(QLabel(i18n.t("interface_language")), 1, 0)
        self.lang = QComboBox()
        self.lang.addItem(i18n.t("lang_en"), "en")
        self.lang.addItem(i18n.t("lang_fa"), "fa")
        self._select(self.lang, self.lang_value)
        appearance_grid.addWidget(self.lang, 1, 1)
        layout.addWidget(appearance)

        defaults = QGroupBox(i18n.t("defaults"))
        defaults_grid = QGridLayout(defaults)
        defaults_grid.setHorizontalSpacing(14)
        defaults_grid.setVerticalSpacing(10)
        defaults_grid.addWidget(QLabel(i18n.t("default_language")), 0, 0)
        self.language = QComboBox()
        self.language.setMinimumWidth(170)
        self.language.addItem(i18n.t("lang_fa"), "fa")
        self.language.addItem(i18n.t("lang_mixed"), "mixed")
        self.language.addItem(i18n.t("lang_en"), "en")
        self.language.addItem(i18n.t("lang_auto"), "auto")
        self._select(self.language, db.setting("default_language", "fa"))
        defaults_grid.addWidget(self.language, 0, 1)

        defaults_grid.addWidget(QLabel(i18n.t("default_model")), 0, 2)
        self.model = QComboBox()
        self.model.setMinimumWidth(240)
        self.model.addItem(i18n.t("model_large"), "large-v3")
        self.model.addItem(i18n.t("model_turbo"), "turbo")
        self._select(self.model, db.setting("default_model", "large-v3"))
        defaults_grid.addWidget(self.model, 0, 3)

        defaults_grid.addWidget(QLabel(i18n.t("default_speakers")), 1, 0)
        self.expected = QSpinBox()
        self.expected.setRange(0, 20)
        self.expected.setSpecialValueText(i18n.t("auto_speakers"))
        try:
            expected = int(db.setting("default_expected_speakers", "0"))
        except ValueError:
            expected = 0
        self.expected.setValue(max(0, min(20, expected)))
        defaults_grid.addWidget(self.expected, 1, 1)

        defaults_grid.addWidget(QLabel(i18n.t("default_scope")), 1, 2)
        self.scope = QComboBox()
        self.scope.addItem(i18n.t("scope_global"), "global")
        self.scope.addItem(i18n.t("scope_job"), "job")
        self._select(self.scope, db.setting("default_scope", "global"))
        defaults_grid.addWidget(self.scope, 1, 3)

        self.diarize = QCheckBox(i18n.t("diarize"))
        self.diarize.setChecked(db.setting("default_diarize", "1") == "1")
        defaults_grid.addWidget(self.diarize, 2, 0, 1, 4)
        layout.addWidget(defaults)

        storage = QGroupBox(i18n.t("storage"))
        storage_grid = QGridLayout(storage)
        storage_grid.setHorizontalSpacing(10)
        storage_grid.setVerticalSpacing(10)
        storage_grid.addWidget(QLabel(i18n.t("model_folder")), 0, 0)
        self.model_path = QLineEdit(str(models_dir()))
        self.model_path.setReadOnly(True)
        storage_grid.addWidget(self.model_path, 0, 1)
        model_open = QPushButton(i18n.t("open_folder"))
        model_open.setObjectName("Ghost")
        model_open.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(models_dir())))
        )
        storage_grid.addWidget(model_open, 0, 2)

        storage_grid.addWidget(QLabel(i18n.t("data_folder")), 1, 0)
        self.data_path = QLineEdit(str(data_dir()))
        self.data_path.setReadOnly(True)
        storage_grid.addWidget(self.data_path, 1, 1)
        data_open = QPushButton(i18n.t("open_folder"))
        data_open.setObjectName("Ghost")
        data_open.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir())))
        )
        storage_grid.addWidget(data_open, 1, 2)
        layout.addWidget(storage)

        layout.addStretch(1)
        version = QLabel("Whisper Scribe 0.1.0")
        version.setObjectName("Muted")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton(i18n.t("cancel"))
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.reject)
        save = QPushButton(i18n.t("save"))
        save.setObjectName("Primary")
        save.clicked.connect(self._accept)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

    @staticmethod
    def _select(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        combo.setCurrentIndex(max(0, index))

    def _accept(self) -> None:
        self.theme_value = str(self.theme.currentData())
        self.lang_value = str(self.lang.currentData())
        self.db.set_setting("theme", self.theme_value)
        self.db.set_setting("language", self.lang_value)
        self.db.set_setting("default_language", str(self.language.currentData()))
        self.db.set_setting("default_model", str(self.model.currentData()))
        self.db.set_setting(
            "default_expected_speakers", str(self.expected.value())
        )
        self.db.set_setting("default_scope", str(self.scope.currentData()))
        self.db.set_setting("default_diarize", "1" if self.diarize.isChecked() else "0")
        self.accept()
