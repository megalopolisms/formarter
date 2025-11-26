"""
Filter Bar Widget for searching and filtering by tags.

Features:
- Text search input
- Tag filter chips (multi-select)
- Clear all filters button
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton,
    QLabel, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from typing import Optional


class TagChip(QWidget):
    """A small clickable tag chip for filtering."""

    clicked = pyqtSignal(str)  # tag_id
    removed = pyqtSignal(str)  # tag_id

    def __init__(self, tag_id: str, name: str, color: str, active: bool = False, parent=None):
        super().__init__(parent)
        self.tag_id = tag_id
        self.name = name
        self.color = color
        self._active = active
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        # Color dot
        self.color_dot = QLabel()
        self.color_dot.setFixedSize(8, 8)
        self.color_dot.setStyleSheet(f"""
            background-color: {self.color};
            border-radius: 4px;
        """)
        layout.addWidget(self.color_dot)

        # Name
        self.name_label = QLabel(self.name)
        self.name_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.name_label)

        # Remove button (only when active)
        self.remove_btn = QPushButton("\u00D7")  # X symbol
        self.remove_btn.setFixedSize(14, 14)
        self.remove_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #666;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #333;
            }
        """)
        self.remove_btn.clicked.connect(lambda: self.removed.emit(self.tag_id))
        self.remove_btn.setVisible(self._active)
        layout.addWidget(self.remove_btn)

        self._update_style()

        # Make clickable
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _update_style(self):
        if self._active:
            bg_color = self.color
            text_color = "#fff" if self._is_dark_color(self.color) else "#000"
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: {bg_color};
                    border-radius: 12px;
                }}
                QLabel {{
                    color: {text_color};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QWidget {{
                    background-color: #f0f0f0;
                    border-radius: 12px;
                    border: 1px solid #ddd;
                }}
                QWidget:hover {{
                    background-color: #e5e5e5;
                }}
            """)

    def _is_dark_color(self, hex_color: str) -> bool:
        """Check if color is dark (for text contrast)."""
        color = QColor(hex_color)
        luminance = (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) / 255
        return luminance < 0.5

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tag_id)
        super().mousePressEvent(event)

    def set_active(self, active: bool):
        self._active = active
        self.remove_btn.setVisible(active)
        self._update_style()

    def is_active(self) -> bool:
        return self._active


class FilterBar(QWidget):
    """
    Filter bar with search input and tag chips.

    Signals:
        search_changed(str): Text search changed
        filters_changed(list): Active tag filters changed
        cleared(): All filters cleared
    """

    search_changed = pyqtSignal(str)
    filters_changed = pyqtSignal(list)  # List of active tag IDs
    cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tags = []  # List of Tag objects
        self._active_filters = set()  # Set of active tag IDs
        self._tag_chips = {}  # tag_id -> TagChip
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)

        # Top row: search + clear button
        top_layout = QHBoxLayout()

        # Search icon label
        search_icon = QLabel("\U0001F50D")  # Magnifying glass
        search_icon.setStyleSheet("color: #888;")
        top_layout.addWidget(search_icon)

        # Search input
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search documents...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 6px 10px;
                background: white;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
        """)
        self.search_input.textChanged.connect(self._on_search_changed)
        top_layout.addWidget(self.search_input)

        # Clear button
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #2196F3;
                padding: 6px 10px;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        self.clear_btn.clicked.connect(self._clear_all)
        top_layout.addWidget(self.clear_btn)

        main_layout.addLayout(top_layout)

        # Tag chips row (scrollable)
        self.tags_scroll = QScrollArea()
        self.tags_scroll.setWidgetResizable(True)
        self.tags_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.tags_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tags_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.tags_scroll.setFixedHeight(36)

        self.tags_container = QWidget()
        self.tags_layout = QHBoxLayout(self.tags_container)
        self.tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tags_layout.setSpacing(6)
        self.tags_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.tags_scroll.setWidget(self.tags_container)
        main_layout.addWidget(self.tags_scroll)

    def set_tags(self, tags: list):
        """
        Set available tags for filtering.

        Args:
            tags: List of Tag objects
        """
        self._tags = tags
        self._rebuild_chips()

    def _rebuild_chips(self):
        """Rebuild tag chips."""
        # Clear existing
        for i in reversed(range(self.tags_layout.count())):
            widget = self.tags_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        self._tag_chips.clear()

        # Add chips
        for tag in self._tags:
            chip = TagChip(
                tag.id,
                tag.name,
                tag.color,
                tag.id in self._active_filters
            )
            chip.clicked.connect(self._on_chip_clicked)
            chip.removed.connect(self._on_chip_removed)
            self._tag_chips[tag.id] = chip
            self.tags_layout.addWidget(chip)

        # Add stretch at end
        self.tags_layout.addStretch()

    def _on_search_changed(self, text: str):
        """Handle search text change."""
        self.search_changed.emit(text)

    def _on_chip_clicked(self, tag_id: str):
        """Handle chip click (toggle filter)."""
        chip = self._tag_chips.get(tag_id)
        if not chip:
            return

        if chip.is_active():
            self._active_filters.discard(tag_id)
            chip.set_active(False)
        else:
            self._active_filters.add(tag_id)
            chip.set_active(True)

        self.filters_changed.emit(list(self._active_filters))

    def _on_chip_removed(self, tag_id: str):
        """Handle chip removal (deactivate filter)."""
        self._active_filters.discard(tag_id)
        chip = self._tag_chips.get(tag_id)
        if chip:
            chip.set_active(False)
        self.filters_changed.emit(list(self._active_filters))

    def _clear_all(self):
        """Clear all filters."""
        self.search_input.clear()
        self._active_filters.clear()
        for chip in self._tag_chips.values():
            chip.set_active(False)
        self.cleared.emit()
        self.filters_changed.emit([])

    def get_search_text(self) -> str:
        """Get current search text."""
        return self.search_input.text()

    def get_active_filters(self) -> list:
        """Get list of active tag filter IDs."""
        return list(self._active_filters)

    def set_active_filters(self, tag_ids: list):
        """Set active filters programmatically."""
        self._active_filters = set(tag_ids)
        for tag_id, chip in self._tag_chips.items():
            chip.set_active(tag_id in self._active_filters)
