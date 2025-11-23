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
from PyQt6.QtGui import QFont

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
        header = QLabel("Text Editor - Type here (blank line = new paragraph)")
        header.setStyleSheet("font-weight: bold; padding: 5px; background: #f0f0f0;")
        layout.addWidget(header)

        # Text editor with Times New Roman font
        self.text_editor = QTextEdit()
        font = QFont("Times New Roman", 12)
        self.text_editor.setFont(font)
        self.text_editor.setPlaceholderText(
            "Type your document here...\n\n"
            "Press Enter twice (blank line) to create a new paragraph.\n\n"
            "Each paragraph will be automatically numbered."
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
        """Parse the editor text into paragraphs (separated by blank lines)."""
        text = self.text_editor.toPlainText()

        # Split by double newlines (blank lines)
        # A paragraph is text between blank lines
        raw_paragraphs = text.split("\n\n")

        # Clean up and filter empty paragraphs
        self.document.paragraphs.clear()

        para_num = 1
        for raw_para in raw_paragraphs:
            # Clean up the paragraph text
            cleaned = raw_para.strip()

            # Skip empty paragraphs
            if not cleaned:
                continue

            # Create paragraph with continuous numbering
            para = Paragraph(
                number=para_num,
                text=cleaned,
                section_id=""  # No section assigned yet
            )
            self.document.paragraphs[para_num] = para
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
            self.tree_widget.addTopLevelItem(para_item)
