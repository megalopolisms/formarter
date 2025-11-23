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

from .mock_data import create_mock_document, get_document_as_text
from .models import Document


class MainWindow(QMainWindow):
    """
    Main application window with two-panel layout:
    - Left: Text editor (line-by-line view with paragraph numbers)
    - Right: Paragraph tree (structural view with sections/sub-items)
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Formarter - Federal Court Document Formatter")
        self.setMinimumSize(800, 600)

        # Create mock document with 100 paragraphs
        self.document = create_mock_document()

        self._setup_ui()
        self._load_document()

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
        header = QLabel("Text Editor - 100 Paragraphs (Continuously Numbered)")
        header.setStyleSheet("font-weight: bold; padding: 5px; background: #f0f0f0;")
        layout.addWidget(header)

        # Text editor with Times New Roman font
        self.text_editor = QTextEdit()
        font = QFont("Times New Roman", 12)
        self.text_editor.setFont(font)
        self.text_editor.setPlaceholderText(
            "Paste or type your document text here...\n\n"
            "Blank lines will separate paragraphs."
        )
        layout.addWidget(self.text_editor)

        return panel

    def _create_tree_panel(self) -> QWidget:
        """Create the right panel with paragraph tree."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header label
        header = QLabel("Paragraph Structure (Sections + Sub-items)")
        header.setStyleSheet("font-weight: bold; padding: 5px; background: #f0f0f0;")
        layout.addWidget(header)

        # Tree widget
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Document Structure"])
        self.tree_widget.setAlternatingRowColors(True)

        # Set tree font
        font = QFont("Arial", 10)
        self.tree_widget.setFont(font)

        layout.addWidget(self.tree_widget)

        return panel

    def _load_document(self):
        """Load the document into both panels."""
        # Set the text in the editor
        full_text = get_document_as_text(self.document)
        self.text_editor.setText(full_text)

        # Populate the tree
        self._populate_tree()

    def _populate_tree(self):
        """Populate the tree widget with document structure."""
        self.tree_widget.clear()

        for section in self.document.sections:
            # Add section as top-level item
            section_text = f"{section.id}. {section.title}"
            section_item = QTreeWidgetItem([section_text])
            section_item.setFlags(
                section_item.flags() | Qt.ItemFlag.ItemIsAutoTristate
            )

            # Make section headers bold
            font = section_item.font(0)
            font.setBold(True)
            section_item.setFont(0, font)

            self.tree_widget.addTopLevelItem(section_item)

            if section.subitems:
                # Section has sub-items
                for subitem in section.subitems:
                    # Add sub-item as child of section
                    subitem_text = f"{subitem.id}. {subitem.title}" if subitem.title else f"{subitem.id}."
                    subitem_item = QTreeWidgetItem([subitem_text])

                    # Make sub-item headers italic
                    font = subitem_item.font(0)
                    font.setItalic(True)
                    subitem_item.setFont(0, font)

                    section_item.addChild(subitem_item)

                    # Add paragraphs under sub-item
                    for para_id in subitem.paragraph_ids:
                        para = self.document.paragraphs.get(para_id)
                        if para:
                            para_text = f"{para.number}. {para.get_display_text(50)}"
                            para_item = QTreeWidgetItem([para_text])
                            subitem_item.addChild(para_item)

                    # Expand sub-item
                    subitem_item.setExpanded(True)
            else:
                # Paragraphs directly under section (no sub-items)
                for para_id in section.paragraph_ids:
                    para = self.document.paragraphs.get(para_id)
                    if para:
                        para_text = f"{para.number}. {para.get_display_text(50)}"
                        para_item = QTreeWidgetItem([para_text])
                        section_item.addChild(para_item)

            # Expand section by default
            section_item.setExpanded(True)

        # Show count in header
        total_paras = len(self.document.paragraphs)
        self.tree_widget.setHeaderLabels([f"Document Structure ({total_paras} paragraphs)"])
