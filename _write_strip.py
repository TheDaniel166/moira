"""Write the new profile_strip.py with cockpit design."""
import pathlib

content = """\
from __future__ import annotations
from datetime import datetime, timezone
from PySide6.QtCore import Qt, Signal, QTimer, QDateTime
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QComboBox, QDateTimeEdit, QDoubleSpinBox,
    QPushButton, QFrame,
)
from moira_ui.shared.theme import COLORS

HOUSE_SYSTEMS = [
    ("P","Placidus"),("K","Koch"),("O","Porphyry"),("R","Regiomontanus"),
    ("C","Campanus"),("H","Azimuthal"),("T","Topocentric"),("B","Alcabitius"),
    ("W","Whole Sign"),("E","Equal"),("V","Vehlow"),("M","Morinus"),
    ("X","Meridian"),("N","Sunshine"),("Y","APC"),("U","Krusinski"),
    ("CT","Carter"),("PS","Pullen SD"),("PR","Pullen SR"),
]
ZODIACS = [
    ("tropical","Tropical"),("fagan","Sidereal (Fagan-Bradley)"),
    ("lahiri","Sidereal (Lahiri)"),("krishna","Sidereal (Krishnamurti)"),
]

_DEBOUNCE_MS = 300
_STRIP_HEIGHT = 72


def _pod_qss():
    return (
        "QWidget#pod {"
        f"  background-color: {COLORS['bg_surface']};"
        f"  border: 1px solid {COLORS['border_subtle']};"
        "  border-radius: 5px;"
        "}"
        "QDateTimeEdit, QDoubleSpinBox {"
        "  background-color: transparent;"
        f"  color: {COLORS['fg_primary']};"
        "  border: none;"
        "  font-family: Cascadia Code, Consolas, Courier New, monospace;"
        "  font-size: 13px;"
        "  padding: 0;"
        "}"
        "QDateTimeEdit::up-button, QDateTimeEdit::down-button,"
        "QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {"
        "  width: 0; height: 0; border: none;"
        "}"
        "QComboBox {"
        "  background-color: transparent;"
        f"  color: {COLORS['fg_primary']};"
        "  border: none;"
        "  font-size: 12px;"
        "  padding: 0;"
        "}"
        "QComboBox::drop-down { border: none; width: 12px; }"
        "QComboBox QAbstractItemView {"
        f"  background-color: {COLORS['bg_surface']};"
        f"  color: {COLORS['fg_primary']};"
        f"  selection-background-color: {COLORS['bg_surface_alt']};"
        f"  border: 1px solid {COLORS['border_subtle']};"
        "}"
    )


def _etched(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {COLORS['fg_disabled']}; font-size: 9px;"
        " letter-spacing: 1.5px; background: transparent;"
        " font-family: Cascadia Code, Consolas, monospace;"
    )
    return lbl


def _dim(text):
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color: {COLORS['fg_disabled']}; font-size: 11px;"
        " background: transparent;"
        " font-family: Cascadia Code, Consolas, monospace;"
    )
    return lbl


class _Pod(QWidget):
    def __init__(self, label, parent=None):
        super().__init__(parent)
        self.setObjectName("pod")
        self.setStyleSheet(_pod_qss())
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 5, 10, 5)
        outer.setSpacing(2)
        outer.addWidget(_etched(label))
        self._row = QHBoxLayout()
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(6)
        outer.addLayout(self._row)

    @property
    def row(self):
        return self._row


class _StackedPod(QWidget):
    def __init__(self, label, parent=None):
        super().__init__(parent)
        self.setObjectName("pod")
        self.setStyleSheet(_pod_qss())
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 4, 10, 4)
        outer.setSpacing(1)
        outer.addWidget(_etched(label))
        self._row1 = QHBoxLayout()
        self._row1.setContentsMargins(0, 0, 0, 0)
        self._row1.setSpacing(6)
        outer.addLayout(self._row1)
        self._row2 = QHBoxLayout()
        self._row2.setContentsMargins(0, 0, 0, 0)
        self._row2.setSpacing(6)
        outer.addLayout(self._row2)

    @property
    def row1(self):
        return self._row1

    @property
    def row2(self):
        return self._row2


def _divider():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setFixedWidth(1)
    f.setFixedHeight(40)
    f.setStyleSheet(f"background-color: {COLORS['border_subtle']}; border: none;")
    return f


class ProfileStrip(QWidget):
    compute_requested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(_STRIP_HEIGHT)
        self.setObjectName("ProfileStrip")
        self.setStyleSheet(
            "QWidget#ProfileStrip {"
            "  background-color: #0c0c14;"
            f"  border-top: 1px solid {COLORS['accent_gold']};"
            f"  border-bottom: 1px solid {COLORS['border_subtle']};"
            "}"
        )
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(_DEBOUNCE_MS)
        self._debounce.timeout.connect(self._emit_params)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(6)

        # Pod 1 - SUBJECT
        subject_pod = _Pod("SUBJECT")
        self.subject_combo = QComboBox()
        self.subject_combo.setEditable(True)
        self.subject_combo.addItem("New Chart")
        self.subject_combo.setMinimumWidth(130)
        le = self.subject_combo.lineEdit()
        if le:
            le.setStyleSheet(
                f"background: transparent; color: {COLORS['fg_primary']};"
                " font-size: 13px; border: none; padding: 0;"
            )
        subject_pod.row.addWidget(self.subject_combo)
        layout.addWidget(subject_pod)
        layout.addWidget(_divider())

        # Pod 2 - EPOCH
        epoch_pod = _Pod("EPOCH  /  UTC")
        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd   HH:mm")
        self.datetime_edit.setCalendarPopup(True)
        now_utc = datetime.now(timezone.utc)
        self.datetime_edit.setDateTime(
            QDateTime(now_utc.year, now_utc.month, now_utc.day,
                      now_utc.hour, now_utc.minute, 0)
        )
        self.datetime_edit.setMinimumWidth(172)
        epoch_pod.row.addWidget(self.datetime_edit)
        layout.addWidget(epoch_pod)
        layout.addWidget(_divider())

        # Pod 3 - COORDINATES (stacked lat / lon)
        coord_pod = _StackedPod("COORDINATES")
        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(-90.0, 90.0)
        self.lat_spin.setDecimals(4)
        self.lat_spin.setValue(51.5074)
        self.lat_spin.setMinimumWidth(90)
        self.lat_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self._lat_dir = _dim("N")
        coord_pod.row1.addWidget(_dim("LAT"))
        coord_pod.row1.addWidget(self.lat_spin)
        coord_pod.row1.addWidget(self._lat_dir)
        coord_pod.row1.addStretch()
        self.lon_spin = QDoubleSpinBox()
        self.lon_spin.setRange(-180.0, 180.0)
        self.lon_spin.setDecimals(4)
        self.lon_spin.setValue(-0.1278)
        self.lon_spin.setMinimumWidth(90)
        self.lon_spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self._lon_dir = _dim("W")
        coord_pod.row2.addWidget(_dim("LON"))
        coord_pod.row2.addWidget(self.lon_spin)
        coord_pod.row2.addWidget(self._lon_dir)
        coord_pod.row2.addStretch()
        self.lat_spin.valueChanged.connect(self._update_lat_dir)
        self.lon_spin.valueChanged.connect(self._update_lon_dir)
        self._update_lat_dir(self.lat_spin.value())
        self._update_lon_dir(self.lon_spin.value())
        layout.addWidget(coord_pod)
        layout.addWidget(_divider())

        # Pod 4 - SCHEMA (house + zodiac stacked)
        schema_pod = _StackedPod("SCHEMA")
        self.house_combo = QComboBox()
        for code, lbl in HOUSE_SYSTEMS:
            self.house_combo.addItem(lbl, code)
        self.house_combo.setCurrentIndex(0)
        self.house_combo.setMinimumWidth(120)
        schema_pod.row1.addWidget(self.house_combo)
        self.zodiac_combo = QComboBox()
        for code, lbl in ZODIACS:
            self.zodiac_combo.addItem(lbl, code)
        self.zodiac_combo.setCurrentIndex(0)
        self.zodiac_combo.setMinimumWidth(120)
        schema_pod.row2.addWidget(self.zodiac_combo)
        layout.addWidget(schema_pod)
        layout.addStretch()

        # Trigger circle button
        self.compute_btn = QPushButton("\\u25b6")
        self.compute_btn.setFixedSize(36, 36)
        self.compute_btn.setToolTip("Compute chart  (or just edit any value)")
        self.compute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.compute_btn.setStyleSheet(
            "QPushButton {"
            "  background-color: transparent;"
            f"  color: {COLORS['accent_gold']};"
            f"  border: 1px solid {COLORS['accent_gold']};"
            "  border-radius: 18px;"
            "  font-size: 14px;"
            "  padding-left: 2px;"
            "}"
            "QPushButton:hover { background-color: rgba(255,215,0,0.10); }"
            "QPushButton:pressed { background-color: rgba(255,215,0,0.22); }"
        )
        self.compute_btn.clicked.connect(self._emit_params)
        layout.addWidget(self.compute_btn)

        for widget in (self.datetime_edit, self.lat_spin, self.lon_spin):
            widget.editingFinished.connect(self._schedule)
        for combo in (self.subject_combo, self.house_combo, self.zodiac_combo):
            combo.currentIndexChanged.connect(self._schedule)

    def _update_lat_dir(self, val):
        self._lat_dir.setText("S" if val < 0 else "N")

    def _update_lon_dir(self, val):
        self._lon_dir.setText("W" if val < 0 else "E")

    def params(self):
        dt = self.datetime_edit.dateTime()
        return {
            "subject":      self.subject_combo.currentText(),
            "year":         dt.date().year(),
            "month":        dt.date().month(),
            "day":          dt.date().day(),
            "hour":         dt.time().hour(),
            "minute":       dt.time().minute(),
            "latitude":     self.lat_spin.value(),
            "longitude":    self.lon_spin.value(),
            "house_system": self.house_combo.currentData(),
            "zodiac":       self.zodiac_combo.currentData(),
        }

    def _schedule(self):
        self._debounce.start()

    def _emit_params(self):
        self.compute_requested.emit(self.params())
"""

pathlib.Path("moira_ui/widgets/profile_strip.py").write_text(content, encoding="utf-8")
print("written ok")
