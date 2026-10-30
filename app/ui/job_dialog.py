from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.core.audio import SUPPORTED_EXTS, is_supported
from app.ui.i18n import I18n


class JobDialog(QDialog):
    def __init__(self, i18n: I18n, db, initial_file: str = "", parent=None) -> None:
        super().__init__(parent)
        self.i18n = i18n
        self.db = db
        self.job_id: int | None = None
        self.setWindowTitle(i18n.t("new_job"))
        self.setModal(True)
        self.setMinimumWidth(600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(12)

        heading = QLabel(i18n.t("new_job"))
        heading.setObjectName("Heading")
        layout.addWidget(heading)

        file_label = QLabel(i18n.t("drop_hint"))
        file_label.setObjectName("Muted")
        layout.addWidget(file_label)

        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        self.file_edit = QLineEdit(initial_file)
        browse = QPushButton(i18n.t("choose_file"))
        browse.clicked.connect(self._browse)
        file_row.addWidget(self.file_edit, 1)
        file_row.addWidget(browse)
        layout.addLayout(file_row)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)

        grid.addWidget(self._eyebrow(i18n.t("language")), 0, 0)
        self.language = QComboBox()
        self.language.addItem(i18n.t("lang_fa"), "fa")
        self.language.addItem(i18n.t("lang_mixed"), "mixed")
        self.language.addItem(i18n.t("lang_en"), "en")
        self.language.addItem(i18n.t("lang_auto"), "auto")
        grid.addWidget(self.language, 1, 0)

        grid.addWidget(self._eyebrow(i18n.t("model")), 0, 1)
        self.model = QComboBox()
        self.model.addItem(i18n.t("model_large"), "large-v3")
        self.model.addItem(i18n.t("model_turbo"), "turbo")
        grid.addWidget(self.model, 1, 1)

        grid.addWidget(self._eyebrow(i18n.t("scope")), 2, 0)
        self.scope = QComboBox()
        self.scope.addItem(i18n.t("scope_global"), "global")
        self.scope.addItem(i18n.t("scope_job"), "job")
        grid.addWidget(self.scope, 3, 0, 1, 2)
        layout.addLayout(grid)

        self.diarize = QCheckBox(i18n.t("diarize"))
        self.diarize.setChecked(True)
        layout.addWidget(self.diarize)

        self.advanced_toggle = QPushButton(i18n.t("advanced"))
        self.advanced_toggle.setObjectName("Ghost")
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.advanced_toggle)

        self.advanced_box = QWidget()
        advanced_layout = QVBoxLayout(self.advanced_box)
        advanced_layout.setContentsMargins(14, 6, 0, 0)
        advanced_layout.setSpacing(6)
        advanced_layout.addWidget(self._eyebrow(i18n.t("expected_speakers")))
        self.expected = QSpinBox()
        self.expected.setRange(0, 20)
        self.expected.setValue(0)
        self.expected.setSpecialValueText(i18n.t("auto_speakers"))
        self.expected.setFixedWidth(120)
        advanced_layout.addWidget(self.expected)
        self.advanced_box.setVisible(False)
        self.advanced_toggle.toggled.connect(self.advanced_box.setVisible)
        layout.addWidget(self.advanced_box)

        layout.addStretch(1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton(i18n.t("cancel"))
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.reject)
        start = QPushButton(i18n.t("start"))
        start.setObjectName("Primary")
        start.clicked.connect(self._accept)
        buttons.addWidget(cancel)
        buttons.addWidget(start)
        layout.addLayout(buttons)

    @staticmethod
    def _eyebrow(text: str) -> QLabel:
        label = QLabel(text.upper())
        label.setObjectName("Eyebrow")
        return label

    def _browse(self) -> None:
        patterns = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTS))
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.i18n.t("choose_file"),
            "",
            f"{self.i18n.t('file_dialog')} ({patterns})",
        )
        if path:
            self.file_edit.setText(path)

    def _accept(self) -> None:
        path = self.file_edit.text().strip()
        if not path or not Path(path).exists():
            QMessageBox.warning(self, self.i18n.t("new_job"), self.i18n.t("drop_hint"))
            return
        if not is_supported(path):
            QMessageBox.warning(self, self.i18n.t("new_job"), self.i18n.t("drop_supported"))
            return

        title = Path(path).stem
        self.job_id = self.db.add_job(
            title=title,
            source_path=path,
            language=self.language.currentData(),
            model=self.model.currentData(),
            speaker_scope=self.scope.currentData(),
            expected_speakers=self.expected.value() if self.diarize.isChecked() else 0,
            diarize=self.diarize.isChecked(),
            status="queued",
        )
        self.accept()
