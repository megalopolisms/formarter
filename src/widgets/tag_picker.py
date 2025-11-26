"""
Tag Picker Dialog for selecting and creating tags.

Features:
- Multi-select predefined tags
- Create custom tags with color picker
- Search/filter tags
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QColorDialog,
    QWidget, QCheckBox, QScrollArea, QFrame, QGridLayout,
    QDialogButtonBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from typing import Optional
import uuid


class TagBadge(QWidget):
    """A clickable tag badge with checkbox."""

    clicked = pyqtSignal(str, bool)  # tag_id, is_selected

    def __init__(self, tag_id: str, name: str, color: str, selected: bool = False, parent=None):
        super().__init__(parent)
        self.tag_id = tag_id
        self.name = name
        self.color = color
        self._selected = selected
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 8, 2)
        layout.setSpacing(4)

        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(self._selected)
        self.checkbox.stateChanged.connect(self._on_state_changed)
        layout.addWidget(self.checkbox)

        # Color dot
        self.color_dot = QLabel()
        self.color_dot.setFixedSize(12, 12)
        self._update_color()
        layout.addWidget(self.color_dot)

        # Name
        self.name_label = QLabel(self.name)
        layout.addWidget(self.name_label)

        self.setStyleSheet("""
            QWidget {
                background-color: #f5f5f5;
                border-radius: 12px;
                padding: 2px;
            }
            QWidget:hover {
                background-color: #e0e0e0;
            }
        """)

    def _update_color(self):
        self.color_dot.setStyleSheet(f"""
            background-color: {self.color};
            border-radius: 6px;
        """)

    def _on_state_changed(self, state):
        self._selected = state == Qt.CheckState.Checked.value
        self.clicked.emit(self.tag_id, self._selected)

    def is_selected(self) -> bool:
        return self._selected

    def set_selected(self, selected: bool):
        self._selected = selected
        self.checkbox.setChecked(selected)


class TagPickerDialog(QDialog):
    """
    Dialog for selecting tags with multi-select support.

    Features:
    - Shows all available tags as colored badges
    - Multi-select with checkboxes
    - Create new custom tag with color picker
    - Search to filter tags
    """

    tags_selected = pyqtSignal(list)  # List of selected tag IDs
    tag_created = pyqtSignal(str, str, str)  # tag_id, name, color

    def __init__(self, available_tags: list, selected_tag_ids: list = None, parent=None):
        """
        Args:
            available_tags: List of Tag objects
            selected_tag_ids: List of currently selected tag IDs
        """
        super().__init__(parent)
        self.available_tags = available_tags
        self.selected_tag_ids = set(selected_tag_ids or [])
        self._tag_badges = {}  # tag_id -> TagBadge
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Select Tags")
        self.setMinimumSize(400, 500)

        layout = QVBoxLayout(self)

        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tags...")
        self.search_input.textChanged.connect(self._filter_tags)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Tags section
        tags_label = QLabel("Available Tags:")
        tags_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(tags_label)

        # Scrollable tag container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.tags_container = QWidget()
        self.tags_layout = QGridLayout(self.tags_container)
        self.tags_layout.setSpacing(8)
        self.tags_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self._populate_tags()

        scroll.setWidget(self.tags_container)
        layout.addWidget(scroll)

        # Create new tag section
        create_frame = QFrame()
        create_frame.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        create_layout = QVBoxLayout(create_frame)

        create_label = QLabel("Create New Tag:")
        create_label.setStyleSheet("font-weight: bold;")
        create_layout.addWidget(create_label)

        new_tag_layout = QHBoxLayout()

        self.new_tag_name = QLineEdit()
        self.new_tag_name.setPlaceholderText("Tag name...")
        new_tag_layout.addWidget(self.new_tag_name)

        self.color_btn = QPushButton()
        self.color_btn.setFixedSize(30, 30)
        self._new_tag_color = "#808080"
        self._update_color_button()
        self.color_btn.clicked.connect(self._pick_color)
        new_tag_layout.addWidget(self.color_btn)

        self.create_btn = QPushButton("Create")
        self.create_btn.clicked.connect(self._create_tag)
        new_tag_layout.addWidget(self.create_btn)

        create_layout.addLayout(new_tag_layout)
        layout.addWidget(create_frame)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _populate_tags(self):
        """Populate the tags grid."""
        # Clear existing
        for i in reversed(range(self.tags_layout.count())):
            self.tags_layout.itemAt(i).widget().setParent(None)
        self._tag_badges.clear()

        row = 0
        col = 0
        max_cols = 2

        for tag in self.available_tags:
            badge = TagBadge(
                tag.id,
                tag.name,
                tag.color,
                tag.id in self.selected_tag_ids
            )
            badge.clicked.connect(self._on_tag_clicked)
            self._tag_badges[tag.id] = badge
            self.tags_layout.addWidget(badge, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def _filter_tags(self, text: str):
        """Filter tags by search text."""
        text = text.lower()
        for tag_id, badge in self._tag_badges.items():
            visible = text in badge.name.lower() if text else True
            badge.setVisible(visible)

    def _on_tag_clicked(self, tag_id: str, selected: bool):
        """Handle tag selection."""
        if selected:
            self.selected_tag_ids.add(tag_id)
        else:
            self.selected_tag_ids.discard(tag_id)

    def _pick_color(self):
        """Open color picker for new tag."""
        color = QColorDialog.getColor(QColor(self._new_tag_color), self, "Pick Tag Color")
        if color.isValid():
            self._new_tag_color = color.name()
            self._update_color_button()

    def _update_color_button(self):
        """Update color button appearance."""
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._new_tag_color};
                border: 1px solid #ccc;
                border-radius: 4px;
            }}
        """)

    def _create_tag(self):
        """Create a new custom tag."""
        name = self.new_tag_name.text().strip()
        if not name:
            return

        tag_id = f"custom-{uuid.uuid4().hex[:8]}"

        # Emit signal for parent to handle
        self.tag_created.emit(tag_id, name, self._new_tag_color)

        # Add to local list and UI
        from src.models.document import Tag
        new_tag = Tag(tag_id, name, self._new_tag_color, False)
        self.available_tags.append(new_tag)
        self.selected_tag_ids.add(tag_id)

        # Re-populate
        self._populate_tags()
        self.new_tag_name.clear()

    def _on_accept(self):
        """Handle OK button."""
        self.tags_selected.emit(list(self.selected_tag_ids))
        self.accept()

    def get_selected_tags(self) -> list:
        """Get list of selected tag IDs."""
        return list(self.selected_tag_ids)
