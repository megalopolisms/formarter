"""
Main application window for Formarter.
"""

import subprocess
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow,
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QMenu,
    QInputDialog,
    QPushButton,
    QFileDialog,
    QDialog,
    QScrollArea,
    QMessageBox,
    QSpinBox,
    QGroupBox,
    QCheckBox,
    QDialogButtonBox,
    QLineEdit,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QTextCursor, QAction, QPixmap, QImage, QIcon

from .models import Document, Paragraph, Section, SpacingSettings, CaseCaption, SignatureBlock, CaseProfile
from .models.saved_document import SavedDocument
from .pdf_export import generate_pdf
from .storage import DocumentStorage


class MainWindow(QMainWindow):
    """
    Main application window with three-panel layout:
    - Left: Text editor (user types here)
    - Middle: Section tree (paragraphs grouped by sections)
    - Right: Page tree (paragraphs grouped by page number)
    """

    # Roman numerals for section numbering
    ROMAN_NUMERALS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
                      "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"]

    # Page formatting constants (federal court standard)
    # Based on: 11" page - 2" margins = 9" usable, 24pt line spacing = 27 lines
    # But reportlab adds paragraph spacing, so ~22-24 short paragraphs fit per page
    LINES_PER_PAGE = 54  # Single-spaced equivalent lines (27 double-spaced * 2)
    CHARS_PER_LINE = 78  # ~6.5" width at 12 chars/inch for Times New Roman 12pt

    # Dual signature block for Yuri & Sumire cases (178, 233)
    PETRINI_MAEDA_SIGNATURE = SignatureBlock(
        attorney_name="Yuri Petrini",
        phone="(305) 504-1323",
        email="yuri@megalopolisms.com",
        attorney_name_2="Sumire Maeda",
        phone_2="(305) 504-1323",
        email_2="sumire@megalopolisms.com",
        address="929 Division Street, Biloxi, MS 39530",
    )

    # Single signature block for Yuri only case (254)
    PETRINI_SIGNATURE = SignatureBlock(
        attorney_name="Yuri Petrini",
        phone="(305) 504-1323",
        email="yuri@megalopolisms.com",
        address="929 Division Street, Biloxi, MS 39530",
    )

    # Pre-configured case profiles
    CASE_PROFILES = [
        CaseProfile(
            name="178 - Petrini & Maeda v. Biloxi",
            caption=CaseCaption(
                plaintiff="YURI PETRINI, SUMIRE MAEDA",
                defendant="CITY OF BILOXI, MISSISSIPPI, et al.",
                case_number="1:25-cv-00178",
            ),
            signature=PETRINI_MAEDA_SIGNATURE,
        ),
        CaseProfile(
            name="233 - Petrini & Maeda v. Biloxi",
            caption=CaseCaption(
                plaintiff="YURI PETRINI, SUMIRE MAEDA",
                defendant="CITY OF BILOXI, MISSISSIPPI, et al.",
                case_number="1:25-cv-00233",
            ),
            signature=PETRINI_MAEDA_SIGNATURE,
        ),
        CaseProfile(
            name="254 - Petrini v. Biloxi",
            caption=CaseCaption(
                plaintiff="YURI PETRINI",
                defendant="CITY OF BILOXI, MISSISSIPPI, et al.",
                case_number="1:25-cv-00254",
            ),
            signature=PETRINI_SIGNATURE,
        ),
    ]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Formarter - Federal Court Document Formatter")
        self.setMinimumSize(1400, 600)

        # Initialize storage manager
        self.storage = DocumentStorage()

        # Currently loaded document (None = new unsaved document)
        self._current_saved_doc: SavedDocument | None = None

        # Start with empty document
        self.document = Document(title="New Document")

        # Track line positions for each paragraph (para_num -> line_index)
        self._para_line_map: dict[int, int] = {}

        # Track which paragraph starts each section (para_num -> section)
        self._section_starts: dict[int, Section] = {}

        # Track page assignments (page_num -> list of para_nums)
        self._page_assignments: dict[int, list[int]] = {}

        # Global spacing settings
        self._global_spacing = SpacingSettings()

        # Flag to prevent recursive updates
        self._updating = False

        # Flag for sidebar visibility
        self._sidebar_visible = True

        self._setup_ui()

        # Set initial filing date from the date input
        self.document.signature.filing_date = self.date_input.text()

        # Auto-select case 178 (first case profile) by default
        self.case_dropdown.setCurrentIndex(1)  # Index 1 = "178 - Petrini & Maeda v. Biloxi"

        # Auto-select MOTION as default document type
        self.doc_type_dropdown.setCurrentIndex(1)  # Index 1 = "MOTION"

        # Load saved documents list
        self._refresh_document_list()

    def _setup_ui(self):
        """Set up the main user interface with toolbar, sidebar, and 3 panels."""
        # Create main container
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create toolbar
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)

        # Create main splitter that includes sidebar + content panels
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Create collapsible sidebar panel (saved documents)
        self.sidebar = self._create_sidebar_panel()
        self.main_splitter.addWidget(self.sidebar)

        # Left panel: Text Editor
        left_panel = self._create_editor_panel()
        self.main_splitter.addWidget(left_panel)

        # Middle panel: Section Tree
        middle_panel = self._create_section_tree_panel()
        self.main_splitter.addWidget(middle_panel)

        # Right panel: Page Tree
        right_panel = self._create_page_tree_panel()
        self.main_splitter.addWidget(right_panel)

        # Set initial sizes (sidebar/editor/sections/pages)
        self.main_splitter.setSizes([220, 400, 300, 300])

        main_layout.addWidget(self.main_splitter)

        # Set main widget as central widget
        self.setCentralWidget(main_widget)

    def _create_toolbar(self) -> QWidget:
        """Create toolbar with Preview and Export buttons."""
        toolbar = QWidget()
        toolbar.setFixedHeight(36)
        toolbar.setStyleSheet("background: #f0f0f0; border-bottom: 1px solid #ccc;")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(5, 2, 5, 2)

        # Sidebar toggle button
        self.sidebar_toggle_btn = QPushButton("<<")
        self.sidebar_toggle_btn.setFixedWidth(30)
        self.sidebar_toggle_btn.setStyleSheet("""
            QPushButton {
                background: #e0e0e0;
                border: 1px solid #ccc;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #d0d0d0;
            }
        """)
        self.sidebar_toggle_btn.setToolTip("Toggle sidebar")
        self.sidebar_toggle_btn.clicked.connect(self._toggle_sidebar)
        layout.addWidget(self.sidebar_toggle_btn)

        layout.addSpacing(5)

        # Case profile dropdown
        case_label = QLabel("Case:")
        case_label.setStyleSheet("font-weight: bold; margin-right: 3px;")
        layout.addWidget(case_label)

        self.case_dropdown = QComboBox()
        self.case_dropdown.addItem("-- Select Case --")
        for profile in self.CASE_PROFILES:
            self.case_dropdown.addItem(profile.name)
        self.case_dropdown.setMinimumWidth(200)
        self.case_dropdown.currentIndexChanged.connect(self._on_case_selected)
        layout.addWidget(self.case_dropdown)

        # Document type dropdown
        doc_type_label = QLabel("Type:")
        doc_type_label.setStyleSheet("font-weight: bold; margin-left: 10px; margin-right: 3px;")
        layout.addWidget(doc_type_label)

        self.doc_type_dropdown = QComboBox()
        self.doc_type_dropdown.addItems([
            "-- Select Type --",
            "MOTION",
            "COMPLAINT",
            "CUSTOM"
        ])
        self.doc_type_dropdown.setMinimumWidth(120)
        self.doc_type_dropdown.currentIndexChanged.connect(self._on_doc_type_selected)
        layout.addWidget(self.doc_type_dropdown)

        # Custom title input (hidden by default, shown when CUSTOM selected)
        self.custom_title_input = QLineEdit()
        self.custom_title_input.setPlaceholderText("Enter custom title...")
        self.custom_title_input.setFixedWidth(150)
        self.custom_title_input.setVisible(False)
        self.custom_title_input.textChanged.connect(self._on_custom_title_changed)
        layout.addWidget(self.custom_title_input)

        # Separator
        layout.addSpacing(10)

        # Preview button
        preview_btn = QPushButton("Preview PDF")
        preview_btn.setStyleSheet("""
            QPushButton {
                background: #4a90d9;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #357abd;
            }
        """)
        preview_btn.clicked.connect(self._on_preview_clicked)
        layout.addWidget(preview_btn)

        # Export button
        export_btn = QPushButton("Export PDF")
        export_btn.setStyleSheet("""
            QPushButton {
                background: #5cb85c;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #449d44;
            }
        """)
        export_btn.clicked.connect(self._on_export_clicked)
        layout.addWidget(export_btn)

        # Options button
        options_btn = QPushButton("Options")
        options_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        options_btn.clicked.connect(self._on_options_clicked)
        layout.addWidget(options_btn)

        # Caption button
        caption_btn = QPushButton("Caption")
        caption_btn.setStyleSheet("""
            QPushButton {
                background: #17a2b8;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #138496;
            }
        """)
        caption_btn.clicked.connect(self._on_caption_clicked)
        layout.addWidget(caption_btn)

        # Signature button
        signature_btn = QPushButton("Signature")
        signature_btn.setStyleSheet("""
            QPushButton {
                background: #6f42c1;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #5a32a3;
            }
        """)
        signature_btn.clicked.connect(self._on_signature_clicked)
        layout.addWidget(signature_btn)

        # Separator
        layout.addSpacing(10)

        # Date input for filing date
        date_label = QLabel("Date:")
        date_label.setStyleSheet("font-weight: bold; margin-right: 3px;")
        layout.addWidget(date_label)

        self.date_input = QLineEdit()
        self.date_input.setFixedWidth(100)
        self.date_input.setPlaceholderText("MM/DD/YYYY")
        # Set next business day as default (skip weekends)
        filing_date = self._get_next_business_day(date.today())
        self.date_input.setText(filing_date.strftime("%m/%d/%Y"))
        self.date_input.textChanged.connect(self._on_date_changed)
        layout.addWidget(self.date_input)

        # Spacer
        layout.addStretch()

        # Document info label
        self.doc_info_label = QLabel("0 paragraphs | 0 sections | 0 pages")
        self.doc_info_label.setStyleSheet("color: #666;")
        layout.addWidget(self.doc_info_label)

        return toolbar

    def _create_editor_panel(self) -> QWidget:
        """Create the left panel with text editor."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header label
        header = QLabel("Text Editor")
        header.setStyleSheet("font-weight: bold; padding: 5px; background: #e8f4e8;")
        layout.addWidget(header)

        # Text editor with Times New Roman font
        self.text_editor = QTextEdit()
        font = QFont("Times New Roman", 12)
        self.text_editor.setFont(font)
        self.text_editor.setPlaceholderText(
            "Type your document here...\n\n"
            "Press Enter to create a new paragraph.\n\n"
            "Right-click paragraphs in Section Tree to assign sections."
        )

        # Connect text changed signal for real-time paragraph detection
        self.text_editor.textChanged.connect(self._on_text_changed)

        layout.addWidget(self.text_editor)

        return panel

    def _create_section_tree_panel(self) -> QWidget:
        """Create the middle panel with section tree."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header label
        self.section_tree_header = QLabel("Section Tree (0 paragraphs)")
        self.section_tree_header.setStyleSheet("font-weight: bold; padding: 5px; background: #e8e8f4;")
        layout.addWidget(self.section_tree_header)

        # Tree widget
        self.section_tree = QTreeWidget()
        self.section_tree.setHeaderLabels(["Sections & Paragraphs"])
        self.section_tree.setAlternatingRowColors(True)

        # Set tree font
        font = QFont("Arial", 10)
        self.section_tree.setFont(font)

        # Enable right-click context menu
        self.section_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.section_tree.customContextMenuRequested.connect(self._on_section_tree_context_menu)

        # Connect click signal to highlight paragraph in editor
        self.section_tree.itemClicked.connect(self._on_tree_item_clicked)

        layout.addWidget(self.section_tree)

        return panel

    def _create_page_tree_panel(self) -> QWidget:
        """Create the right panel with page tree."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header label
        self.page_tree_header = QLabel("Page Tree (0 pages)")
        self.page_tree_header.setStyleSheet("font-weight: bold; padding: 5px; background: #f4e8e8;")
        layout.addWidget(self.page_tree_header)

        # Tree widget
        self.page_tree = QTreeWidget()
        self.page_tree.setHeaderLabels(["Pages & Paragraphs"])
        self.page_tree.setAlternatingRowColors(True)

        # Set tree font
        font = QFont("Arial", 10)
        self.page_tree.setFont(font)

        # Connect click signal to highlight paragraph in editor
        self.page_tree.itemClicked.connect(self._on_tree_item_clicked)

        layout.addWidget(self.page_tree)

        return panel

    def _create_sidebar_panel(self) -> QWidget:
        """Create the collapsible sidebar panel with saved documents."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        panel.setMinimumWidth(150)
        panel.setMaximumWidth(400)
        panel.setStyleSheet("""
            QFrame {
                background: #f8f8f8;
                border-right: 1px solid #ccc;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Header
        header = QLabel("Saved Documents")
        header.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
        layout.addWidget(header)

        # Storage location indicator
        storage_path = self.storage.get_storage_location()
        # Show only the folder name, not full path
        folder_name = Path(storage_path).name
        is_dropbox = "Dropbox" in storage_path
        storage_label = QLabel(f"{'Dropbox' if is_dropbox else 'Local'}: {folder_name}")
        storage_label.setStyleSheet("font-size: 10px; color: #666; padding: 2px 5px;")
        storage_label.setToolTip(storage_path)
        layout.addWidget(storage_label)

        # New document button
        new_btn = QPushButton("+ New Document")
        new_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #218838;
            }
        """)
        new_btn.clicked.connect(self._on_new_document)
        layout.addWidget(new_btn)

        # Save current button
        save_btn = QPushButton("Save Current")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #007bff;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #0069d9;
            }
        """)
        save_btn.clicked.connect(self._on_save_document)
        layout.addWidget(save_btn)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background: #ccc;")
        layout.addWidget(separator)

        # Document list
        self.doc_list = QListWidget()
        self.doc_list.setStyleSheet("""
            QListWidget {
                background: white;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background: #e3f2fd;
                color: black;
            }
            QListWidget::item:hover {
                background: #f5f5f5;
            }
        """)
        self.doc_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.doc_list.customContextMenuRequested.connect(self._on_doc_list_context_menu)
        self.doc_list.itemDoubleClicked.connect(self._on_doc_list_double_click)
        layout.addWidget(self.doc_list)

        return panel

    def _toggle_sidebar(self):
        """Toggle sidebar visibility."""
        self._sidebar_visible = not self._sidebar_visible
        if self._sidebar_visible:
            # Show sidebar with default width
            sizes = self.main_splitter.sizes()
            sizes[0] = 220
            self.main_splitter.setSizes(sizes)
        else:
            # Collapse sidebar to 0
            sizes = self.main_splitter.sizes()
            sizes[0] = 0
            self.main_splitter.setSizes(sizes)
        self.sidebar_toggle_btn.setText("<<" if self._sidebar_visible else ">>")

    def _get_case_name(self, case_profile_index: int) -> str:
        """Get short case name from profile index."""
        if case_profile_index <= 0 or case_profile_index > len(self.CASE_PROFILES):
            return "None"
        profile = self.CASE_PROFILES[case_profile_index - 1]
        # Extract case number (e.g., "178" from "178 - Petrini & Maeda v. Biloxi")
        return profile.name.split(" - ")[0]

    def _get_next_business_day(self, d: date) -> date:
        """
        Get the next business day (skip weekends).

        If the given date is a weekend (Saturday or Sunday),
        returns the following Monday.
        """
        # weekday(): Monday=0, Tuesday=1, ..., Saturday=5, Sunday=6
        while d.weekday() >= 5:  # 5=Saturday, 6=Sunday
            d += timedelta(days=1)
        return d

    def _refresh_document_list(self):
        """Refresh the document list from storage."""
        self.doc_list.clear()
        documents = self.storage.list_all()

        for doc in documents:
            item = QListWidgetItem()

            # Show full details for each document
            case_name = self._get_case_name(doc.case_profile_index)
            display_text = (
                f"{doc.name}\n"
                f"Case: {case_name}\n"
                f"Created: {doc.created_display}\n"
                f"Modified: {doc.modified_display}"
            )

            item.setText(display_text)
            item.setData(Qt.ItemDataRole.UserRole, doc.id)

            # Highlight current document
            if self._current_saved_doc and doc.id == self._current_saved_doc.id:
                font = item.font()
                font.setBold(True)
                item.setFont(font)

            self.doc_list.addItem(item)

    def _on_new_document(self):
        """Create a new document and save it immediately."""
        # Check if current document has unsaved changes
        if self._has_unsaved_changes():
            result = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Do you want to save the current document before creating a new one?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            if result == QMessageBox.StandardButton.Save:
                self._on_save_document()
            elif result == QMessageBox.StandardButton.Cancel:
                return

        # Clear editor and reset state
        self._updating = True
        try:
            self.text_editor.clear()
            self._section_starts.clear()
            self.document = Document(title="New Document")

            # Reset to defaults
            self.case_dropdown.setCurrentIndex(1)
            self.doc_type_dropdown.setCurrentIndex(1)
            self.document.signature.filing_date = self.date_input.text()
            self._on_case_selected(1)

            self._parse_paragraphs()
            self._calculate_pages()
            self._update_section_tree()
            self._update_page_tree()
            self._update_doc_info()
        finally:
            self._updating = False

        # Create and save new document immediately
        new_doc = SavedDocument(name="Untitled Document")
        self._save_current_to_doc(new_doc)
        self.storage.save(new_doc)
        self._current_saved_doc = new_doc

        self._refresh_document_list()

    def _on_save_document(self):
        """Save the current document."""
        if self._current_saved_doc:
            # Update existing document
            self._save_current_to_doc(self._current_saved_doc)
            self.storage.save(self._current_saved_doc)
            # Reload the saved doc to get updated modified timestamp
            self._current_saved_doc = self.storage.get_by_id(self._current_saved_doc.id)
            QMessageBox.information(
                self, "Saved",
                f"Document '{self._current_saved_doc.name}' saved."
            )
        else:
            # Create new document with name
            name, ok = QInputDialog.getText(
                self, "Save Document",
                "Document name:",
                text="Untitled Document"
            )
            if not ok or not name.strip():
                return

            new_doc = SavedDocument(name=name.strip())
            self._save_current_to_doc(new_doc)
            self.storage.save(new_doc)
            # Reload to get the saved version with updated timestamp
            self._current_saved_doc = self.storage.get_by_id(new_doc.id)
            QMessageBox.information(
                self, "Saved",
                f"Document '{new_doc.name}' created."
            )

        self._refresh_document_list()

    def _save_current_to_doc(self, doc: SavedDocument):
        """Save current editor state to a SavedDocument."""
        doc.text_content = self.text_editor.toPlainText()
        doc.case_profile_index = self.case_dropdown.currentIndex()
        doc.document_type_index = self.doc_type_dropdown.currentIndex()
        doc.custom_title = self.custom_title_input.text()
        doc.spacing_before_section = self._global_spacing.before_section
        doc.spacing_after_section = self._global_spacing.after_section
        doc.spacing_between_paragraphs = self._global_spacing.between_paragraphs
        doc.filing_date = self.date_input.text()

        # Save section assignments
        doc.sections = []
        for para_num, section in self._section_starts.items():
            section_data = {
                "id": section.id,
                "title": section.title,
                "start_para": para_num,
            }
            if section.custom_spacing:
                section_data["custom_spacing"] = {
                    "before_section": section.custom_spacing.before_section,
                    "after_section": section.custom_spacing.after_section,
                    "between_paragraphs": section.custom_spacing.between_paragraphs,
                }
            doc.sections.append(section_data)

    def _load_doc_to_editor(self, doc: SavedDocument):
        """Load a SavedDocument into the editor."""
        self._updating = True
        try:
            # Set text content
            self.text_editor.setPlainText(doc.text_content)

            # Set dropdowns
            self.case_dropdown.setCurrentIndex(doc.case_profile_index)
            self.doc_type_dropdown.setCurrentIndex(doc.document_type_index)
            self.custom_title_input.setText(doc.custom_title)
            self.date_input.setText(doc.filing_date)

            # Apply case profile if selected
            if doc.case_profile_index > 0:
                self._on_case_selected(doc.case_profile_index)

            # Apply document type
            self._on_doc_type_selected(doc.document_type_index)

            # Set global spacing
            self._global_spacing = SpacingSettings(
                before_section=doc.spacing_before_section,
                after_section=doc.spacing_after_section,
                between_paragraphs=doc.spacing_between_paragraphs,
            )

            # Restore section assignments
            self._section_starts.clear()
            for section_data in doc.sections:
                section = Section(
                    id=section_data["id"],
                    title=section_data["title"]
                )
                if "custom_spacing" in section_data:
                    cs = section_data["custom_spacing"]
                    section.custom_spacing = SpacingSettings(
                        before_section=cs["before_section"],
                        after_section=cs["after_section"],
                        between_paragraphs=cs["between_paragraphs"],
                    )
                self._section_starts[section_data["start_para"]] = section

            # Update current document reference
            self._current_saved_doc = doc

            # Refresh UI
            self._parse_paragraphs()
            self._calculate_pages()
            self._update_section_tree()
            self._update_page_tree()
            self._update_doc_info()
        finally:
            self._updating = False

    def _has_unsaved_changes(self) -> bool:
        """Check if current editor has unsaved changes."""
        current_text = self.text_editor.toPlainText()
        if self._current_saved_doc:
            return current_text != self._current_saved_doc.text_content
        else:
            return len(current_text.strip()) > 0

    def _on_doc_list_context_menu(self, position):
        """Show context menu for document list."""
        item = self.doc_list.itemAt(position)
        if not item:
            return

        doc_id = item.data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)

        # Load action
        load_action = menu.addAction("Open")
        load_action.triggered.connect(lambda: self._load_document(doc_id))

        menu.addSeparator()

        # Rename action
        rename_action = menu.addAction("Rename...")
        rename_action.triggered.connect(lambda: self._rename_document(doc_id))

        # Duplicate action
        duplicate_action = menu.addAction("Duplicate")
        duplicate_action.triggered.connect(lambda: self._duplicate_document(doc_id))

        menu.addSeparator()

        # Delete action
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self._delete_document(doc_id))

        menu.exec(self.doc_list.viewport().mapToGlobal(position))

    def _on_doc_list_double_click(self, item: QListWidgetItem):
        """Handle double-click on document list item."""
        doc_id = item.data(Qt.ItemDataRole.UserRole)
        self._load_document(doc_id)

    def _load_document(self, doc_id: str):
        """Load a document by ID."""
        # Check for unsaved changes
        if self._has_unsaved_changes():
            result = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Do you want to save the current document before loading another?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel
            )
            if result == QMessageBox.StandardButton.Save:
                self._on_save_document()
            elif result == QMessageBox.StandardButton.Cancel:
                return

        doc = self.storage.get_by_id(doc_id)
        if doc:
            self._load_doc_to_editor(doc)
            self._refresh_document_list()

    def _rename_document(self, doc_id: str):
        """Rename a document."""
        doc = self.storage.get_by_id(doc_id)
        if not doc:
            return

        name, ok = QInputDialog.getText(
            self, "Rename Document",
            "New name:",
            text=doc.name
        )
        if ok and name.strip():
            self.storage.rename(doc_id, name.strip())
            if self._current_saved_doc and self._current_saved_doc.id == doc_id:
                self._current_saved_doc.name = name.strip()
            self._refresh_document_list()

    def _duplicate_document(self, doc_id: str):
        """Duplicate a document."""
        doc = self.storage.get_by_id(doc_id)
        if not doc:
            return

        new_doc = self.storage.duplicate(doc_id)
        if new_doc:
            self._refresh_document_list()
            QMessageBox.information(
                self, "Duplicated",
                f"Created copy: '{new_doc.name}'"
            )

    def _delete_document(self, doc_id: str):
        """Delete a document."""
        doc = self.storage.get_by_id(doc_id)
        if not doc:
            return

        result = QMessageBox.question(
            self,
            "Delete Document",
            f"Are you sure you want to delete '{doc.name}'?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if result == QMessageBox.StandardButton.Yes:
            self.storage.delete(doc_id)
            if self._current_saved_doc and self._current_saved_doc.id == doc_id:
                self._current_saved_doc = None
            self._refresh_document_list()

    def _on_text_changed(self):
        """Handle text changes - detect paragraphs in real-time."""
        if self._updating:
            return

        self._updating = True
        try:
            self._parse_paragraphs()
            self._calculate_pages()
            self._update_section_tree()
            self._update_page_tree()
            self._update_doc_info()
        finally:
            self._updating = False

    def _parse_paragraphs(self):
        """Parse the editor text into paragraphs (each line = one paragraph)."""
        text = self.text_editor.toPlainText()
        lines = text.split("\n")

        # Remember old section assignments before clearing
        old_sections = dict(self._section_starts)

        # Clean up and filter empty lines
        self.document.paragraphs.clear()
        self._para_line_map.clear()

        para_num = 1
        for line_idx, line in enumerate(lines):
            cleaned = line.strip()
            if not cleaned:
                continue

            para = Paragraph(
                number=para_num,
                text=cleaned,
                section_id=""
            )
            self.document.paragraphs[para_num] = para
            self._para_line_map[para_num] = line_idx
            para_num += 1

        # Re-apply section assignments (adjust for paragraph count changes)
        new_section_starts = {}
        for old_para_num, section in old_sections.items():
            if old_para_num <= len(self.document.paragraphs):
                new_section_starts[old_para_num] = section
        self._section_starts = new_section_starts

    def _calculate_pages(self):
        """Calculate which paragraphs go on which page."""
        self._page_assignments.clear()

        if not self.document.paragraphs:
            return

        current_page = 1
        current_line_count = 0
        self._page_assignments[current_page] = []
        current_section = None

        for para_num in sorted(self.document.paragraphs.keys()):
            para = self.document.paragraphs[para_num]

            # Get spacing settings (section-specific or global)
            section = self._get_section_for_para(para_num)
            spacing = None
            if section and section.custom_spacing:
                spacing = section.custom_spacing
            else:
                spacing = self._global_spacing

            # Calculate lines this paragraph takes (matching PDF output)
            text_lines = max(1, (len(para.text) + self.CHARS_PER_LINE - 1) // self.CHARS_PER_LINE)
            para_lines = text_lines * 2 + spacing.between_paragraphs  # Double-spaced + spacing

            # Check if section header needs extra space
            if para_num in self._section_starts:
                section = self._section_starts[para_num]
                current_section = section
                section_spacing = section.custom_spacing or self._global_spacing
                para_lines += section_spacing.before_section * 2 + section_spacing.after_section

            # Check if we need a new page
            if current_line_count + para_lines > self.LINES_PER_PAGE and current_line_count > 0:
                current_page += 1
                current_line_count = 0
                self._page_assignments[current_page] = []

            # Add paragraph to current page
            self._page_assignments[current_page].append(para_num)
            current_line_count += para_lines

    def _update_section_tree(self):
        """Update the section tree widget with current paragraphs grouped by sections."""
        self.section_tree.clear()

        count = len(self.document.paragraphs)
        section_count = len(self._section_starts)
        self.section_tree_header.setText(
            f"Section Tree ({count} para, {section_count} sec)"
        )

        if not self.document.paragraphs:
            return

        para_nums = sorted(self.document.paragraphs.keys())
        current_section_item = None

        for para_num in para_nums:
            para = self.document.paragraphs[para_num]

            # Check if this paragraph starts a new section
            if para_num in self._section_starts:
                section = self._section_starts[para_num]
                section_text = f"{section.id}. {section.title}"

                current_section_item = QTreeWidgetItem([section_text])
                current_section_item.setData(0, Qt.ItemDataRole.UserRole, ("section", para_num))

                font = current_section_item.font(0)
                font.setBold(True)
                current_section_item.setFont(0, font)

                self.section_tree.addTopLevelItem(current_section_item)
                current_section_item.setExpanded(True)

            # Create paragraph item
            preview = para.get_display_text(40)
            para_text = f"{para.number}. {preview}"
            para_item = QTreeWidgetItem([para_text])
            para_item.setData(0, Qt.ItemDataRole.UserRole, ("para", para_num))

            if current_section_item is not None:
                current_section_item.addChild(para_item)
            else:
                self.section_tree.addTopLevelItem(para_item)

    def _update_page_tree(self):
        """Update the page tree widget with paragraphs grouped by page and section."""
        self.page_tree.clear()

        page_count = len(self._page_assignments)
        self.page_tree_header.setText(f"Page Tree ({page_count} page{'s' if page_count != 1 else ''})")

        if not self._page_assignments:
            return

        for page_num in sorted(self._page_assignments.keys()):
            para_nums = self._page_assignments[page_num]

            # Create page item
            page_text = f"Page {page_num}"
            page_item = QTreeWidgetItem([page_text])
            page_item.setData(0, Qt.ItemDataRole.UserRole, ("page", page_num))

            font = page_item.font(0)
            font.setBold(True)
            page_item.setFont(0, font)

            self.page_tree.addTopLevelItem(page_item)

            # Group paragraphs by section within this page
            section_groups: dict[str, list[int]] = {}  # section_key -> [para_nums]

            for para_num in para_nums:
                section = self._get_section_for_para(para_num)
                if section:
                    section_key = f"{section.id}. {section.title}"
                else:
                    section_key = "(No Section)"

                if section_key not in section_groups:
                    section_groups[section_key] = []
                section_groups[section_key].append(para_num)

            # Add sections and paragraphs under this page
            for section_key, section_para_nums in section_groups.items():
                # Create section item under page
                section_item = QTreeWidgetItem([section_key])
                section_item.setData(0, Qt.ItemDataRole.UserRole, ("page_section", section_key))

                # Make section text italic
                section_font = section_item.font(0)
                section_font.setItalic(True)
                section_item.setFont(0, section_font)

                page_item.addChild(section_item)

                # Add paragraphs under this section
                for para_num in section_para_nums:
                    para = self.document.paragraphs.get(para_num)
                    if para:
                        preview = para.get_display_text(40)
                        para_text = f"{para.number}. {preview}"
                        para_item = QTreeWidgetItem([para_text])
                        para_item.setData(0, Qt.ItemDataRole.UserRole, ("para", para_num))
                        section_item.addChild(para_item)

                section_item.setExpanded(True)

            page_item.setExpanded(True)

    def _on_section_tree_context_menu(self, position):
        """Show context menu on right-click in section tree."""
        item = self.section_tree.itemAt(position)
        if not item:
            return

        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data:
            return

        item_type, item_id = item_data

        menu = QMenu(self)

        if item_type == "para":
            para_num = item_id
            section_menu = menu.addMenu("Section")

            new_section_action = section_menu.addAction("Create new section...")
            new_section_action.triggered.connect(lambda: self._create_section_at(para_num))

            if self._section_starts:
                section_menu.addSeparator()
                for start_para, section in sorted(self._section_starts.items()):
                    action = section_menu.addAction(f"{section.id}. {section.title}")
                    action.triggered.connect(
                        lambda checked, s=section, p=para_num: self._assign_to_section(p, s)
                    )

            if self._get_section_for_para(para_num):
                section_menu.addSeparator()
                remove_action = section_menu.addAction("Remove from section")
                remove_action.triggered.connect(lambda: self._remove_from_section(para_num))

        elif item_type == "section":
            section_start_para = item_id

            remove_action = menu.addAction("Remove section")
            remove_action.triggered.connect(lambda: self._remove_section(section_start_para))

            rename_action = menu.addAction("Rename section...")
            rename_action.triggered.connect(lambda: self._rename_section(section_start_para))

            spacing_action = menu.addAction("Spacing...")
            spacing_action.triggered.connect(lambda: self._edit_section_spacing(section_start_para))

        menu.exec(self.section_tree.viewport().mapToGlobal(position))

    def _create_section_at(self, para_num: int):
        """Create a new section starting at the given paragraph."""
        name, ok = QInputDialog.getText(
            self, "Create Section",
            "Section name (e.g., PARTIES, JURISDICTION):"
        )
        if not ok or not name.strip():
            return

        name = name.strip().upper()

        existing_numerals = [s.id for s in self._section_starts.values()]
        for numeral in self.ROMAN_NUMERALS:
            if numeral not in existing_numerals:
                break
        else:
            numeral = f"S{len(self._section_starts) + 1}"

        section = Section(id=numeral, title=name)
        self._section_starts[para_num] = section

        self._calculate_pages()
        self._update_section_tree()
        self._update_page_tree()

    def _assign_to_section(self, para_num: int, section: Section):
        """Move section to start at a different paragraph."""
        current_start = None
        for start_para, s in self._section_starts.items():
            if s.id == section.id:
                current_start = start_para
                break

        if current_start is not None:
            del self._section_starts[current_start]

        self._section_starts[para_num] = section
        self._calculate_pages()
        self._update_section_tree()
        self._update_page_tree()

    def _remove_from_section(self, para_num: int):
        """Remove section that starts at this paragraph."""
        if para_num in self._section_starts:
            del self._section_starts[para_num]
            self._calculate_pages()
            self._update_section_tree()
            self._update_page_tree()

    def _remove_section(self, section_start_para: int):
        """Remove a section entirely."""
        if section_start_para in self._section_starts:
            del self._section_starts[section_start_para]
            self._calculate_pages()
            self._update_section_tree()
            self._update_page_tree()

    def _rename_section(self, section_start_para: int):
        """Rename a section."""
        if section_start_para not in self._section_starts:
            return

        section = self._section_starts[section_start_para]
        name, ok = QInputDialog.getText(
            self, "Rename Section",
            "New section name:",
            text=section.title
        )
        if ok and name.strip():
            section.title = name.strip().upper()
            self._update_section_tree()

    def _edit_section_spacing(self, section_start_para: int):
        """Edit spacing settings for a specific section."""
        if section_start_para not in self._section_starts:
            return

        section = self._section_starts[section_start_para]
        current_spacing = section.custom_spacing or self._global_spacing

        dialog = SpacingDialog(
            current_spacing,
            parent=self,
            section_name=f"{section.id}. {section.title}"
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            section.custom_spacing = dialog.get_spacing()
            self._calculate_pages()
            self._update_page_tree()

    def _get_section_for_para(self, para_num: int) -> Section | None:
        """Get the section that contains a paragraph."""
        relevant_starts = [p for p in self._section_starts.keys() if p <= para_num]
        if not relevant_starts:
            return None
        return self._section_starts[max(relevant_starts)]

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle click on tree item - highlight and scroll to paragraph in editor."""
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data:
            return

        item_type, item_id = item_data

        if item_type != "para":
            return

        para_num = item_id
        line_idx = self._para_line_map.get(para_num)
        if line_idx is None:
            return

        text = self.text_editor.toPlainText()
        lines = text.split("\n")

        if line_idx >= len(lines):
            return

        char_pos = sum(len(lines[i]) + 1 for i in range(line_idx))
        line_length = len(lines[line_idx])

        self._updating = True
        try:
            cursor = self.text_editor.textCursor()
            cursor.setPosition(char_pos)
            cursor.setPosition(char_pos + line_length, QTextCursor.MoveMode.KeepAnchor)
            self.text_editor.setTextCursor(cursor)
            self.text_editor.ensureCursorVisible()
            self.text_editor.setFocus()
        finally:
            self._updating = False

    def _update_doc_info(self):
        """Update the document info label in toolbar."""
        para_count = len(self.document.paragraphs)
        section_count = len(self._section_starts)
        page_count = len(self._page_assignments)
        self.doc_info_label.setText(
            f"{para_count} paragraph{'s' if para_count != 1 else ''} | "
            f"{section_count} section{'s' if section_count != 1 else ''} | "
            f"{page_count} page{'s' if page_count != 1 else ''}"
        )

    def _on_preview_clicked(self):
        """Handle Preview button click - generate PDF and open in system viewer."""
        # Allow preview even without paragraphs (to see header and signature)
        try:
            # Generate PDF to temp file
            pdf_path = generate_pdf(
                self.document.paragraphs,
                self._section_starts,
                global_spacing=self._global_spacing,
                caption=self.document.caption,
                signature=self.document.signature,
                document_title=self.document.title
            )

            # Open in system PDF viewer (Preview.app on macOS)
            if sys.platform == "darwin":
                subprocess.run(["open", pdf_path], check=True)
            elif sys.platform == "win32":
                subprocess.run(["start", "", pdf_path], shell=True, check=True)
            else:
                subprocess.run(["xdg-open", pdf_path], check=True)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Preview Error",
                f"Failed to generate preview:\n{str(e)}"
            )

    def _on_export_clicked(self):
        """Handle Export button click - save PDF to user-selected location."""
        # Allow export even without paragraphs (to see header and signature)

        # Show save dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export PDF",
            "document.pdf",
            "PDF Files (*.pdf)"
        )

        if not file_path:
            return

        # Ensure .pdf extension
        if not file_path.lower().endswith('.pdf'):
            file_path += '.pdf'

        try:
            # Generate PDF
            generate_pdf(
                self.document.paragraphs,
                self._section_starts,
                output_path=file_path,
                global_spacing=self._global_spacing,
                caption=self.document.caption,
                signature=self.document.signature,
                document_title=self.document.title
            )

            # Show success and offer to open
            result = QMessageBox.question(
                self,
                "Export Successful",
                f"PDF saved to:\n{file_path}\n\nOpen in PDF viewer?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if result == QMessageBox.StandardButton.Yes:
                if sys.platform == "darwin":
                    subprocess.run(["open", file_path], check=True)
                elif sys.platform == "win32":
                    subprocess.run(["start", "", file_path], shell=True, check=True)
                else:
                    subprocess.run(["xdg-open", file_path], check=True)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export PDF:\n{str(e)}"
            )

    def _on_options_clicked(self):
        """Handle Options button click - show spacing settings dialog."""
        dialog = SpacingDialog(self._global_spacing, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._global_spacing = dialog.get_spacing()
            self._calculate_pages()
            self._update_page_tree()

    def _on_caption_clicked(self):
        """Handle Caption button click - show case caption dialog."""
        dialog = CaptionDialog(self.document.caption, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.document.caption = dialog.get_caption()

    def _on_signature_clicked(self):
        """Handle Signature button click - show signature block dialog."""
        dialog = SignatureDialog(self.document.signature, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.document.signature = dialog.get_signature()

    def _on_date_changed(self, text: str):
        """Handle date input change - update signature's filing date."""
        self.document.signature.filing_date = text

    def _on_doc_type_selected(self, index: int):
        """Handle document type selection from dropdown."""
        if index == 0:  # "-- Select Type --" option
            self.document.title = ""
            self.custom_title_input.setVisible(False)
            return

        doc_type = self.doc_type_dropdown.currentText()
        if doc_type == "CUSTOM":
            self.custom_title_input.setVisible(True)
            self.document.title = self.custom_title_input.text().strip().upper()
        else:
            self.custom_title_input.setVisible(False)
            self.document.title = doc_type

    def _on_custom_title_changed(self, text: str):
        """Handle custom title input change."""
        self.document.title = text.strip().upper()

    def _on_case_selected(self, index: int):
        """Handle case profile selection from dropdown."""
        if index == 0:  # "-- Select Case --" option
            return

        # Get the selected profile (index - 1 because of placeholder item)
        profile = self.CASE_PROFILES[index - 1]

        # Apply caption and signature from profile
        self.document.caption = CaseCaption(
            court=profile.caption.court,
            plaintiff=profile.caption.plaintiff,
            defendant=profile.caption.defendant,
            case_number=profile.caption.case_number,
        )
        self.document.signature = SignatureBlock(
            attorney_name=profile.signature.attorney_name,
            phone=profile.signature.phone,
            email=profile.signature.email,
            attorney_name_2=profile.signature.attorney_name_2,
            phone_2=profile.signature.phone_2,
            email_2=profile.signature.email_2,
            address=profile.signature.address,
            bar_number=profile.signature.bar_number,
            firm_name=profile.signature.firm_name,
            filing_date=self.date_input.text(),  # Use current date from input
        )


class SpacingDialog(QDialog):
    """Dialog for configuring global spacing settings."""

    def __init__(self, current_spacing: SpacingSettings, parent=None, section_name: str = None):
        super().__init__(parent)
        self._section_name = section_name
        self._is_section = section_name is not None

        if self._is_section:
            self.setWindowTitle(f"Spacing - {section_name}")
        else:
            self.setWindowTitle("Global Spacing Options")

        self.setMinimumWidth(300)
        self._setup_ui(current_spacing)

    def _setup_ui(self, spacing: SpacingSettings):
        layout = QVBoxLayout(self)

        # Section override checkbox (only for per-section dialogs)
        if self._is_section:
            self.use_custom = QCheckBox("Use custom spacing for this section")
            self.use_custom.setChecked(spacing is not None)
            self.use_custom.toggled.connect(self._on_custom_toggled)
            layout.addWidget(self.use_custom)

        # Spacing group
        group = QGroupBox("Line Spacing (0, 1, or 2 blank lines)")
        form = QFormLayout(group)

        # Before section header
        self.before_section = QSpinBox()
        self.before_section.setRange(0, 2)
        self.before_section.setValue(spacing.before_section if spacing else 1)
        form.addRow("Before section header:", self.before_section)

        # After section header
        self.after_section = QSpinBox()
        self.after_section.setRange(0, 2)
        self.after_section.setValue(spacing.after_section if spacing else 1)
        form.addRow("After section header:", self.after_section)

        # Between paragraphs
        self.between_paragraphs = QSpinBox()
        self.between_paragraphs.setRange(0, 2)
        self.between_paragraphs.setValue(spacing.between_paragraphs if spacing else 1)
        form.addRow("Between paragraphs:", self.between_paragraphs)

        layout.addWidget(group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if self._is_section:
            self._on_custom_toggled(self.use_custom.isChecked())

    def _on_custom_toggled(self, checked: bool):
        """Enable/disable spacing controls based on checkbox."""
        self.before_section.setEnabled(checked)
        self.after_section.setEnabled(checked)
        self.between_paragraphs.setEnabled(checked)

    def get_spacing(self) -> SpacingSettings | None:
        """Get the configured spacing settings."""
        if self._is_section and not self.use_custom.isChecked():
            return None
        return SpacingSettings(
            before_section=self.before_section.value(),
            after_section=self.after_section.value(),
            between_paragraphs=self.between_paragraphs.value(),
        )


class CaptionDialog(QDialog):
    """Dialog for configuring case caption (court header)."""

    def __init__(self, current_caption: CaseCaption, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Case Caption")
        self.setMinimumWidth(400)
        self._setup_ui(current_caption)

    def _setup_ui(self, caption: CaseCaption):
        layout = QVBoxLayout(self)

        # Court name (read-only display)
        court_group = QGroupBox("Court")
        court_layout = QVBoxLayout(court_group)
        court_label = QLabel(caption.court.replace('\n', ' - '))
        court_label.setStyleSheet("font-weight: bold;")
        court_layout.addWidget(court_label)
        layout.addWidget(court_group)

        # Case information
        case_group = QGroupBox("Case Information")
        form = QFormLayout(case_group)

        # Plaintiff
        self.plaintiff_edit = QLineEdit()
        self.plaintiff_edit.setText(caption.plaintiff)
        self.plaintiff_edit.setPlaceholderText("e.g., JOHN DOE")
        form.addRow("Plaintiff:", self.plaintiff_edit)

        # Defendant
        self.defendant_edit = QLineEdit()
        self.defendant_edit.setText(caption.defendant)
        self.defendant_edit.setPlaceholderText("e.g., ACME CORPORATION")
        form.addRow("Defendant:", self.defendant_edit)

        # Case number
        self.case_number_edit = QLineEdit()
        self.case_number_edit.setText(caption.case_number)
        self.case_number_edit.setPlaceholderText("e.g., 3:24-cv-00123")
        form.addRow("Case Number:", self.case_number_edit)

        layout.addWidget(case_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_caption(self) -> CaseCaption:
        """Get the configured caption settings."""
        return CaseCaption(
            plaintiff=self.plaintiff_edit.text().strip(),
            defendant=self.defendant_edit.text().strip(),
            case_number=self.case_number_edit.text().strip(),
        )


class SignatureDialog(QDialog):
    """Dialog for configuring signature block information."""

    def __init__(self, current_signature: SignatureBlock, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Signature Block")
        self.setMinimumWidth(400)
        self._setup_ui(current_signature)

    def _setup_ui(self, signature: SignatureBlock):
        layout = QVBoxLayout(self)

        # Attorney information
        attorney_group = QGroupBox("Attorney Information")
        form = QFormLayout(attorney_group)

        # Attorney name
        self.attorney_name_edit = QLineEdit()
        self.attorney_name_edit.setText(signature.attorney_name)
        self.attorney_name_edit.setPlaceholderText("e.g., John Smith")
        form.addRow("Attorney Name:", self.attorney_name_edit)

        # Bar number
        self.bar_number_edit = QLineEdit()
        self.bar_number_edit.setText(signature.bar_number)
        self.bar_number_edit.setPlaceholderText("e.g., MSB 12345")
        form.addRow("Bar Number:", self.bar_number_edit)

        # Firm name
        self.firm_name_edit = QLineEdit()
        self.firm_name_edit.setText(signature.firm_name)
        self.firm_name_edit.setPlaceholderText("e.g., Smith & Associates, PLLC")
        form.addRow("Firm Name:", self.firm_name_edit)

        # Address
        self.address_edit = QLineEdit()
        self.address_edit.setText(signature.address)
        self.address_edit.setPlaceholderText("e.g., 123 Main St, Jackson, MS 39201")
        form.addRow("Address:", self.address_edit)

        # Phone
        self.phone_edit = QLineEdit()
        self.phone_edit.setText(signature.phone)
        self.phone_edit.setPlaceholderText("e.g., (601) 555-1234")
        form.addRow("Phone:", self.phone_edit)

        # Email
        self.email_edit = QLineEdit()
        self.email_edit.setText(signature.email)
        self.email_edit.setPlaceholderText("e.g., jsmith@lawfirm.com")
        form.addRow("Email:", self.email_edit)

        layout.addWidget(attorney_group)

        # Certificate of Service note
        cert_label = QLabel(
            "<i>Certificate of Service will be automatically added stating "
            "all counsel were served via ECF at time of filing.</i>"
        )
        cert_label.setWordWrap(True)
        cert_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(cert_label)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_signature(self) -> SignatureBlock:
        """Get the configured signature block settings."""
        return SignatureBlock(
            attorney_name=self.attorney_name_edit.text().strip(),
            bar_number=self.bar_number_edit.text().strip(),
            firm_name=self.firm_name_edit.text().strip(),
            address=self.address_edit.text().strip(),
            phone=self.phone_edit.text().strip(),
            email=self.email_edit.text().strip(),
        )
