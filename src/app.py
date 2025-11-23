"""
Main application window for Formarter.
"""

from PyQt6.QtWidgets import (
    QMainWindow,
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
    QVBoxLayout,
    QLabel,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCursor

from .models import Document, Paragraph


class MainWindow(QMainWindow):
    """
    Main application window with two-panel layout:
    - Left: Text editor (user types here, blank lines create paragraphs)
    - Right: Paragraph tree (shows numbered paragraphs)
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Formarter - Federal Court Document Formatter")
        self.setMinimumSize(800, 600)

        # Start with empty document
        self.document = Document(title="New Document")

        # Track line positions for each paragraph (para_num -> line_index)
        self._para_line_map: dict[int, int] = {}

        # Flag to prevent recursive updates
        self._updating = False

        self._setup_ui()

    def _setup_ui(self):
        """Set up the main user interface."""
        # Create the main splitter for two-panel layout
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Text Editor
        left_panel = self._create_editor_panel()
        splitter.addWidget(left_panel)

        # Right panel: Paragraph Tree
        right_panel = self._create_tree_panel()
        splitter.addWidget(right_panel)

        # Set initial sizes (50/50 split)
        splitter.setSizes([500, 500])

        # Set splitter as central widget
        self.setCentralWidget(splitter)

    def _create_editor_panel(self) -> QWidget:
        """Create the left panel with text editor."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header label
        header = QLabel("Text Editor - Type here (Enter = new paragraph)")
        header.setStyleSheet("font-weight: bold; padding: 5px; background: #f0f0f0;")
        layout.addWidget(header)

        # Text editor with Times New Roman font
        self.text_editor = QTextEdit()
        font = QFont("Times New Roman", 12)
        self.text_editor.setFont(font)
        self.text_editor.setPlaceholderText(
            "Type your document here...\n\n"
            "Press Enter to create a new paragraph.\n\n"
            "Each paragraph will be automatically numbered.\n\n"
            "Click a paragraph in the tree to highlight it."
        )

        # Connect text changed signal for real-time paragraph detection
        self.text_editor.textChanged.connect(self._on_text_changed)

        layout.addWidget(self.text_editor)

        return panel

    def _create_tree_panel(self) -> QWidget:
        """Create the right panel with paragraph tree."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header label
        self.tree_header = QLabel("Paragraph Structure (0 paragraphs)")
        self.tree_header.setStyleSheet("font-weight: bold; padding: 5px; background: #f0f0f0;")
        layout.addWidget(self.tree_header)

        # Tree widget
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Paragraphs"])
        self.tree_widget.setAlternatingRowColors(True)

        # Set tree font
        font = QFont("Arial", 10)
        self.tree_widget.setFont(font)

        # Connect click signal to highlight paragraph in editor
        self.tree_widget.itemClicked.connect(self._on_tree_item_clicked)

        layout.addWidget(self.tree_widget)

        return panel

    def _on_text_changed(self):
        """Handle text changes - detect paragraphs in real-time."""
        if self._updating:
            return

        self._updating = True
        try:
            self._parse_paragraphs()
            self._update_tree()
        finally:
            self._updating = False

    def _parse_paragraphs(self):
        """Parse the editor text into paragraphs (each line = one paragraph)."""
        text = self.text_editor.toPlainText()

        # Split by ANY newline - each line of content is a paragraph
        # Empty lines are ignored (just visual spacing)
        lines = text.split("\n")

        # Clean up and filter empty lines
        self.document.paragraphs.clear()
        self._para_line_map.clear()

        para_num = 1
        for line_idx, line in enumerate(lines):
            # Clean up the line
            cleaned = line.strip()

            # Skip empty lines (they're just visual spacing)
            if not cleaned:
                continue

            # Create paragraph with continuous numbering
            para = Paragraph(
                number=para_num,
                text=cleaned,
                section_id=""  # No section assigned yet
            )
            self.document.paragraphs[para_num] = para

            # Track which line this paragraph is on
            self._para_line_map[para_num] = line_idx

            para_num += 1

    def _update_tree(self):
        """Update the tree widget with current paragraphs."""
        self.tree_widget.clear()

        # Update header with paragraph count
        count = len(self.document.paragraphs)
        self.tree_header.setText(f"Paragraph Structure ({count} paragraph{'s' if count != 1 else ''})")

        # Add each paragraph to the tree
        for para_num in sorted(self.document.paragraphs.keys()):
            para = self.document.paragraphs[para_num]

            # Format: "1. Preview text here..."
            preview = para.get_display_text(55)
            para_text = f"{para.number}. {preview}"

            para_item = QTreeWidgetItem([para_text])
            # Store paragraph number in item data for click handling
            para_item.setData(0, Qt.ItemDataRole.UserRole, para_num)
            self.tree_widget.addTopLevelItem(para_item)

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle click on tree item - highlight and scroll to paragraph in editor."""
        # Get paragraph number from item data
        para_num = item.data(0, Qt.ItemDataRole.UserRole)
        if para_num is None:
            return

        # Get the line index for this paragraph
        line_idx = self._para_line_map.get(para_num)
        if line_idx is None:
            return

        # Get the text and find the line position
        text = self.text_editor.toPlainText()
        lines = text.split("\n")

        if line_idx >= len(lines):
            return

        # Calculate character position for this line
        char_pos = sum(len(lines[i]) + 1 for i in range(line_idx))  # +1 for newline
        line_length = len(lines[line_idx])

        # Prevent triggering text changed while selecting
        self._updating = True
        try:
            # Create cursor and select the line
            cursor = self.text_editor.textCursor()

            # Move to start of line
            cursor.setPosition(char_pos)

            # Select the entire line
            cursor.setPosition(char_pos + line_length, QTextCursor.MoveMode.KeepAnchor)

            # Apply selection to editor
            self.text_editor.setTextCursor(cursor)

            # Ensure the line is visible
            self.text_editor.ensureCursorVisible()

            # Focus the editor
            self.text_editor.setFocus()
        finally:
            self._updating = False
