"""
Main application window for Formarter.
"""

import re
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
    QTableWidget,
    QTableWidgetItem,
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
    QRadioButton,
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
    QTabWidget,
    QApplication,
    QGridLayout,
    QDateEdit,
)
from PyQt6.QtCore import Qt, QSize, QDate
from PyQt6.QtGui import QFont, QTextCursor, QAction, QPixmap, QImage, QIcon, QSyntaxHighlighter, QTextCharFormat, QColor

from .models import Document, Paragraph, Section, SpacingSettings, CaseCaption, SignatureBlock, CaseProfile
from .models.saved_document import SavedDocument
from .models.library_case import LibraryCase, Category, REPORTERS, COURTS
from .models.document import Tag, PREDEFINED_TAGS, Filing, Case
from .pdf_export import generate_pdf
from .storage import DocumentStorage
from .case_law_extractor import CaseLawExtractor
from .case_library import CaseLibrary, get_default_library_path
from .exhibit_bank import ExhibitBank, get_default_exhibit_path
from .models.exhibit import Exhibit, ExhibitTag, DEFAULT_TAGS, get_file_type
from .models.lawsuit import LawsuitManager, Lawsuit
from .widgets.filing_tree import FilingTreeWidget
from .widgets.tag_picker import TagPickerDialog
from .widgets.filter_bar import FilterBar
from .widgets.file_document_dialog import FileDocumentDialog
from .auditor import (
    TRO_CHECKLIST, CheckCategory, CheckStatus,
    ComplianceDetector, AuditResult, ItemResult, AuditOptions,
    save_audit_result, load_audit_result, load_audit_log
)


def format_case_name(name: str) -> str:
    """Format case name with proper title case for legal citations.

    Handles: "smith v. jones" -> "Smith v. Jones"
    Preserves: U.S., FBI, Inc., LLC, etc.
    """
    if not name:
        return name

    # Words to keep lowercase (unless first)
    lowercase_words = {'v', 'v.', 'of', 'the', 'in', 'at', 'by', 'for', 'on', 'and', 'or', 'a', 'an', 'to'}
    # Abbreviations to keep uppercase
    uppercase_abbrevs = {'U.S.', 'US', 'USA', 'FBI', 'CIA', 'IRS', 'DOJ', 'SEC', 'FTC', 'LLC', 'LLP', 'INC', 'CORP'}

    words = name.split()
    result = []

    for i, word in enumerate(words):
        word_upper = word.upper().rstrip('.,')

        # Keep uppercase abbreviations
        if word_upper in uppercase_abbrevs or word.upper() in uppercase_abbrevs:
            if word_upper == 'US':
                result.append('U.S.')
            else:
                result.append(word.upper() if word_upper in uppercase_abbrevs else word)
        # Keep lowercase words (except first word)
        elif word.lower() in lowercase_words and i > 0:
            result.append(word.lower())
        # Title case everything else
        else:
            result.append(word.capitalize())

    return ' '.join(result)


class SectionTagHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for section and subsection tags in the editor.

    - Valid <SECTION>...</SECTION> tags: Green
    - Valid <SUBSECTION>...</SUBSECTION> tags: Blue
    - Malformed/incomplete tags: Red/Orange
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Format for valid section tags
        self.section_format = QTextCharFormat()
        self.section_format.setForeground(QColor("#2E7D32"))  # Dark green
        self.section_format.setFontWeight(QFont.Weight.Bold)

        # Format for valid subsection tags
        self.subsection_format = QTextCharFormat()
        self.subsection_format.setForeground(QColor("#1565C0"))  # Dark blue
        self.subsection_format.setFontItalic(True)

        # Format for malformed tags (opening without closing)
        self.error_format = QTextCharFormat()
        self.error_format.setForeground(QColor("#D32F2F"))  # Red
        self.error_format.setBackground(QColor("#FFEBEE"))  # Light red background

        # Format for <line> tags
        self.line_format = QTextCharFormat()
        self.line_format.setForeground(QColor("#7B1FA2"))  # Purple
        self.line_format.setFontWeight(QFont.Weight.Light)

        # Patterns for valid tags (complete)
        self.section_pattern = re.compile(r'<SECTION>.*?</SECTION>', re.IGNORECASE)
        self.subsection_pattern = re.compile(r'<SUBSECTION>.*?</SUBSECTION>', re.IGNORECASE)
        self.line_pattern = re.compile(r'<line>', re.IGNORECASE)

        # Patterns for malformed tags (opening without closing)
        self.malformed_section = re.compile(r'<SECTION>(?!.*</SECTION>).*$', re.IGNORECASE)
        self.malformed_subsection = re.compile(r'<SUBSECTION>(?!.*</SUBSECTION>).*$', re.IGNORECASE)

    def highlightBlock(self, text: str):
        """Apply syntax highlighting to a block of text."""

        # Highlight valid section tags
        for match in self.section_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.section_format)

        # Highlight valid subsection tags
        for match in self.subsection_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.subsection_format)

        # Highlight malformed section tags
        for match in self.malformed_section.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.error_format)

        # Highlight malformed subsection tags
        for match in self.malformed_subsection.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.error_format)

        # Highlight <line> tags
        for match in self.line_pattern.finditer(text):
            self.setFormat(match.start(), match.end() - match.start(), self.line_format)


class LineBreakTextEdit(QTextEdit):
    """Custom QTextEdit that handles <line> tags for line breaks.

    Features:
    - When Enter is pressed, inserts <line> on its own line
    - When pasting text, converts line breaks to <line> tags
    - The <line> tag represents a line break in the PDF output

    This allows users to have proper line spacing in the exported PDF.
    """

    def keyPressEvent(self, event):
        """Override Enter key to insert <line> tag for line breaks."""
        from PyQt6.QtCore import Qt

        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            # Insert newline, then <line> tag, then another newline
            self.insertPlainText('\n<line>\n')
            return  # Don't call super, we handled it

        # For all other keys, use default behavior
        super().keyPressEvent(event)

    def insertFromMimeData(self, source):
        """Override paste behavior to convert line breaks to <line> tags."""
        if source.hasText():
            text = source.text()
            # Convert newlines to <line> tags
            # But preserve double newlines (paragraph breaks) as single newlines
            # So that paragraph detection still works
            lines = text.split('\n')
            converted_lines = []
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped:
                    converted_lines.append(stripped)
                else:
                    # Empty line = paragraph break, keep as newline
                    converted_lines.append('')

            # Join with <line> for non-empty consecutive lines
            result_parts = []
            i = 0
            while i < len(converted_lines):
                if converted_lines[i] == '':
                    # Paragraph break - add newline
                    result_parts.append('\n')
                    i += 1
                else:
                    # Content line
                    result_parts.append(converted_lines[i])
                    # Check if next line is also content (not empty)
                    if i + 1 < len(converted_lines) and converted_lines[i + 1] != '':
                        result_parts.append('<line>')
                    i += 1

            converted_text = ''.join(result_parts)
            # Clean up any double newlines that might have appeared
            converted_text = re.sub(r'\n{3,}', '\n\n', converted_text)
            self.insertPlainText(converted_text)
        else:
            super().insertFromMimeData(source)


class AnnotationTextEdit(LineBreakTextEdit):
    """
    Extended text editor with paragraph-based annotation support.

    Features:
    - Highlights entire paragraphs that have linked notes
    - Shows [NOTE] tag at start of paragraphs with notes
    - Provides paragraph info for annotation management
    """

    from PyQt6.QtCore import pyqtSignal

    # Signal emitted when annotations need to be synced after text changes
    annotations_need_sync = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._annotations = []  # List of Annotation objects
        self._paragraph_boundaries = []  # List of (start_pos, end_pos) for each paragraph
        self._updating_highlights = False

    def set_annotations(self, annotations: list):
        """Set annotations from loaded document."""
        self._annotations = annotations

    def get_annotations(self) -> list:
        """Get current annotations."""
        return self._annotations

    def add_annotation(self, annotation):
        """Add a new annotation."""
        self._annotations.append(annotation)

    def remove_annotation(self, annotation_id: str):
        """Remove an annotation by ID."""
        self._annotations = [a for a in self._annotations if a.id != annotation_id]

    def get_annotation_by_id(self, annotation_id: str):
        """Get annotation by ID."""
        for a in self._annotations:
            if a.id == annotation_id:
                return a
        return None

    def get_annotations_for_paragraph(self, para_num: int) -> list:
        """Get all annotations linked to a specific paragraph."""
        return [a for a in self._annotations if a.paragraph_number == para_num]

    def get_standalone_annotations(self) -> list:
        """Get all unlinked (standalone) annotations."""
        return [a for a in self._annotations if a.paragraph_number is None]

    def clear_annotations(self):
        """Clear all annotations."""
        self._annotations = []
        self._paragraph_boundaries = []
        self.setExtraSelections([])  # Clear highlights

    def update_paragraph_boundaries(self, boundaries: list):
        """
        Update paragraph boundary information.
        boundaries: list of (start_pos, end_pos) tuples for each paragraph (1-indexed in list)
        """
        self._paragraph_boundaries = boundaries

    def apply_paragraph_highlights(self, paragraphs_with_notes: set):
        """
        Apply yellow highlight to paragraphs that have notes.
        paragraphs_with_notes: set of 1-indexed paragraph numbers that have linked notes
        """
        if self._updating_highlights or not self._paragraph_boundaries:
            return

        self._updating_highlights = True
        try:
            extra_selections = []
            highlight_format = QTextCharFormat()
            highlight_format.setBackground(QColor("#FFFACD"))  # Light yellow (lemon chiffon)

            for para_num in paragraphs_with_notes:
                if 1 <= para_num <= len(self._paragraph_boundaries):
                    start_pos, end_pos = self._paragraph_boundaries[para_num - 1]
                    cursor = QTextCursor(self.document())
                    cursor.setPosition(start_pos)
                    cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)

                    selection = QTextEdit.ExtraSelection()
                    selection.cursor = cursor
                    selection.format = highlight_format
                    extra_selections.append(selection)

            self.setExtraSelections(extra_selections)
        finally:
            self._updating_highlights = False

    def scroll_to_paragraph(self, para_num: int):
        """Scroll to and select a specific paragraph."""
        if 1 <= para_num <= len(self._paragraph_boundaries):
            start_pos, end_pos = self._paragraph_boundaries[para_num - 1]
            cursor = QTextCursor(self.document())
            cursor.setPosition(start_pos)
            cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(cursor)
            self.ensureCursorVisible()

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

    # Section tag pattern for bidirectional sync: <SECTION>I. TITLE</SECTION>
    SECTION_TAG_PATTERN = re.compile(r'^<SECTION>(.+)</SECTION>$', re.IGNORECASE)

    # Subsection tag pattern: <SUBSECTION>a. Background</SUBSECTION>
    SUBSECTION_TAG_PATTERN = re.compile(r'^<SUBSECTION>(.+)</SUBSECTION>$', re.IGNORECASE)

    # Dual signature block for Yuri & Sumire cases (178, 233)
    PETRINI_MAEDA_SIGNATURE = SignatureBlock(
        attorney_name="Yuri Petrini",
        phone="(305) 504-1323",
        email="yuri@megalopolisms.com",
        attorney_name_2="Sumire Maeda",
        phone_2="(305) 497-9133",
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
                case_number="1:25-cv-00178-LG-RPM",
            ),
            signature=PETRINI_MAEDA_SIGNATURE,
        ),
        CaseProfile(
            name="233 - Petrini & Maeda v. Biloxi",
            caption=CaseCaption(
                plaintiff="YURI PETRINI, SUMIRE MAEDA",
                defendant="CITY OF BILOXI, MISSISSIPPI, et al.",
                case_number="1:25-cv-00233-LG-RPM",
            ),
            signature=PETRINI_MAEDA_SIGNATURE,
        ),
        CaseProfile(
            name="254 - Petrini v. Biloxi",
            caption=CaseCaption(
                plaintiff="YURI PETRINI",
                defendant="CITY OF BILOXI, MISSISSIPPI, et al.",
                case_number="1:25-cv-00254-LG-RPM",
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

        # Initialize case library
        self.case_library = CaseLibrary(get_default_library_path())

        # Initialize lawsuit manager
        self.lawsuit_manager = LawsuitManager()

        # Current active lawsuit (for filtering dockets/exhibits)
        self._active_lawsuit_number = "178"  # Default to case 178

        # Currently loaded document (None = new unsaved document)
        self._current_saved_doc: SavedDocument | None = None

        # Start with empty document
        self.document = Document(title="New Document")

        # Track line positions for each paragraph (para_num -> line_index)
        self._para_line_map: dict[int, int] = {}

        # Track which paragraph starts each section (para_num -> section)
        self._section_starts: dict[int, Section] = {}

        # Track line positions for each section tag (section_id -> line_index)
        self._section_line_map: dict[str, int] = {}

        # Track all sections/subsections in order: (section, para_num, is_subsection, parent_id, display_letter)
        self._all_sections: list[tuple[Section, int, bool, str | None, str]] = []

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
        """Set up the main user interface with tabs."""
        # Create main container
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create tab widget for browser-style tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                background: #e0e0e0;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #ffffff;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background: #f0f0f0;
            }
        """)

        # Tab 1: Editor (main document editor)
        editor_tab = self._create_editor_tab()
        self.tab_widget.addTab(editor_tab, "Editor")

        # Tab 2: Case Law Extractor
        case_law_tab = self._create_case_law_tab()
        self.tab_widget.addTab(case_law_tab, "Case Law")

        # Tab 3: Library
        library_tab = self._create_library_tab()
        self.tab_widget.addTab(library_tab, "Library")

        # Tab 4: Auditor (TRO Compliance Checker)
        auditor_tab = self._create_auditor_tab()
        self.tab_widget.addTab(auditor_tab, "Auditor")

        # Tab 5: Quick Print (Emergency standalone documents)
        quick_print_tab = self._create_quick_print_tab()
        self.tab_widget.addTab(quick_print_tab, "Quick Print")

        # Tab 6: Executed Filings (Case 178 - Current Lawsuit)
        filings_tab = self._create_executed_filings_tab()
        self.tab_widget.addTab(filings_tab, "Executed Filings")

        # Tab 7: Exhibit Bank (Document storage for exhibits)
        exhibit_bank_tab = self._create_exhibit_bank_tab()
        self.tab_widget.addTab(exhibit_bank_tab, "Exhibit Bank")

        # Tab 8: Dockets (Track case dockets and deadlines)
        dockets_tab = self._create_dockets_tab()
        self.tab_widget.addTab(dockets_tab, "Dockets")

        main_layout.addWidget(self.tab_widget)

        # Set main widget as central widget
        self.setCentralWidget(main_widget)

    def _create_editor_tab(self) -> QWidget:
        """Create the Editor tab with toolbar, sidebar, and panels."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

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

        layout.addWidget(self.main_splitter)

        return tab

    def _create_case_law_tab(self) -> QWidget:
        """Create the Case Law Extractor tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("Case Law Citation Extractor")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(header)

        description = QLabel(
            "Select a saved document to extract all case law citations. "
            "The extractor identifies federal and state case citations, "
            "including short citations (Id., supra, infra)."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(description)

        # Document selector
        selector_layout = QHBoxLayout()

        doc_label = QLabel("Select Document:")
        doc_label.setStyleSheet("font-weight: bold;")
        selector_layout.addWidget(doc_label)

        self.case_law_doc_dropdown = QComboBox()
        self.case_law_doc_dropdown.setMinimumWidth(300)
        self._refresh_case_law_doc_list()
        selector_layout.addWidget(self.case_law_doc_dropdown)

        selector_layout.addStretch()

        layout.addLayout(selector_layout)

        # Buttons
        btn_layout = QHBoxLayout()

        extract_btn = QPushButton("Extract Citations")
        extract_btn.setStyleSheet("""
            QPushButton {
                background: #4a90d9;
                color: white;
                border: none;
                padding: 10px 25px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #357abd;
            }
        """)
        extract_btn.clicked.connect(self._on_extract_citations)
        btn_layout.addWidget(extract_btn)

        copy_btn = QPushButton("Copy Report")
        copy_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                padding: 10px 25px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        copy_btn.clicked.connect(self._on_copy_report)
        btn_layout.addWidget(copy_btn)

        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        # Results area
        results_label = QLabel("Results:")
        results_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(results_label)

        self.case_law_results = QTextEdit()
        self.case_law_results.setReadOnly(True)
        self.case_law_results.setFont(QFont("Courier New", 11))
        self.case_law_results.setStyleSheet("""
            QTextEdit {
                background: #f8f9fa;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        self.case_law_results.setPlaceholderText("Select a document and click 'Extract Citations' to see results...")
        layout.addWidget(self.case_law_results)

        return tab

    def _create_library_tab(self) -> QWidget:
        """Create the Case Library tab with sub-tabs for Cases and Federal Rules."""
        # Main container with sub-tabs
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create sub-tab widget
        self.library_subtabs = QTabWidget()
        self.library_subtabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ddd;
                background: white;
            }
            QTabBar::tab {
                padding: 8px 20px;
                margin-right: 2px;
                background: #f0f0f0;
                border: 1px solid #ddd;
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover:!selected {
                background: #e0e0e0;
            }
        """)

        # Sub-tab 1: Cases
        cases_tab = self._create_cases_subtab()
        self.library_subtabs.addTab(cases_tab, "Cases")

        # Sub-tab 2: Civil Rules (Fed. R. Civ. P.)
        civil_rules_tab = self._create_civil_rules_subtab()
        self.library_subtabs.addTab(civil_rules_tab, "Civil Rules")

        # Sub-tab 3: MS Criminal Rules (Mississippi Rules of Criminal Procedure)
        criminal_rules_tab = self._create_criminal_rules_subtab()
        self.library_subtabs.addTab(criminal_rules_tab, "MS Criminal Rules")

        main_layout.addWidget(self.library_subtabs)
        return container

    def _create_cases_subtab(self) -> QWidget:
        """Create the Cases sub-tab for storing and organizing case law PDFs."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("Case Library")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(header)

        description = QLabel(
            "Store and organize case law PDFs with Bluebook citations. "
            "Search by case name, citation, keywords, or full text content."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(description)

        # Toolbar with buttons and filters
        toolbar_layout = QHBoxLayout()

        # Add Case button
        add_case_btn = QPushButton("+ Add Case")
        add_case_btn.setStyleSheet("""
            QPushButton {
                background: #4a90d9;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #357abd;
            }
        """)
        add_case_btn.clicked.connect(self._on_add_case)
        toolbar_layout.addWidget(add_case_btn)

        # Batch Import button
        batch_import_btn = QPushButton("+ Batch Import")
        batch_import_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        batch_import_btn.clicked.connect(self._on_batch_import)
        toolbar_layout.addWidget(batch_import_btn)

        # Regenerate All Citations button
        regenerate_all_btn = QPushButton("Regenerate All Citations")
        regenerate_all_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #218838;
            }
        """)
        regenerate_all_btn.clicked.connect(self._on_regenerate_all_citations)
        toolbar_layout.addWidget(regenerate_all_btn)

        toolbar_layout.addSpacing(20)

        # Category filter
        cat_label = QLabel("Category:")
        cat_label.setStyleSheet("font-weight: bold;")
        toolbar_layout.addWidget(cat_label)

        self.library_category_dropdown = QComboBox()
        self.library_category_dropdown.setMinimumWidth(150)
        self._refresh_library_categories()
        self.library_category_dropdown.currentIndexChanged.connect(self._on_library_filter_changed)
        toolbar_layout.addWidget(self.library_category_dropdown)

        toolbar_layout.addSpacing(10)

        # Search box
        search_label = QLabel("Search:")
        search_label.setStyleSheet("font-weight: bold;")
        toolbar_layout.addWidget(search_label)

        self.library_search_input = QLineEdit()
        self.library_search_input.setPlaceholderText("Search cases...")
        self.library_search_input.setMinimumWidth(200)
        self.library_search_input.textChanged.connect(self._on_library_search_changed)
        toolbar_layout.addWidget(self.library_search_input)

        toolbar_layout.addStretch()

        layout.addLayout(toolbar_layout)

        # Case table
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
        self.library_table = QTableWidget()
        self.library_table.setColumnCount(6)
        self.library_table.setHorizontalHeaderLabels([
            "Case Name", "Citation", "Court", "Year", "Category", "Keywords"
        ])
        self.library_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.library_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.library_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.library_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.library_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.library_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.library_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.library_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.library_table.setAlternatingRowColors(True)
        self.library_table.setStyleSheet("""
            QTableWidget {
                background: white;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QTableWidget::item:selected {
                background: #4a90d9;
                color: white;
            }
            QHeaderView::section {
                background: #f0f0f0;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #ccc;
                font-weight: bold;
            }
        """)
        self.library_table.itemSelectionChanged.connect(self._on_library_selection_changed)
        layout.addWidget(self.library_table)

        # Action buttons
        action_layout = QHBoxLayout()

        self.lib_open_pdf_btn = QPushButton("Open PDF")
        self.lib_open_pdf_btn.setEnabled(False)
        self.lib_open_pdf_btn.clicked.connect(self._on_library_open_pdf)
        action_layout.addWidget(self.lib_open_pdf_btn)

        self.lib_view_text_btn = QPushButton("View Text")
        self.lib_view_text_btn.setEnabled(False)
        self.lib_view_text_btn.clicked.connect(self._on_library_view_text)
        action_layout.addWidget(self.lib_view_text_btn)

        self.lib_copy_citation_btn = QPushButton("Copy Citation")
        self.lib_copy_citation_btn.setEnabled(False)
        self.lib_copy_citation_btn.clicked.connect(self._on_library_copy_citation)
        action_layout.addWidget(self.lib_copy_citation_btn)

        self.lib_view_citations_btn = QPushButton("View Citations")
        self.lib_view_citations_btn.setEnabled(False)
        self.lib_view_citations_btn.clicked.connect(self._on_library_view_citations)
        action_layout.addWidget(self.lib_view_citations_btn)

        self.lib_edit_btn = QPushButton("Edit Tags")
        self.lib_edit_btn.setEnabled(False)
        self.lib_edit_btn.clicked.connect(self._on_library_edit_tags)
        action_layout.addWidget(self.lib_edit_btn)

        self.lib_delete_btn = QPushButton("Delete")
        self.lib_delete_btn.setEnabled(False)
        self.lib_delete_btn.setStyleSheet("""
            QPushButton {
                color: #dc3545;
            }
            QPushButton:hover {
                background: #dc3545;
                color: white;
            }
        """)
        self.lib_delete_btn.clicked.connect(self._on_library_delete)
        action_layout.addWidget(self.lib_delete_btn)

        action_layout.addStretch()

        # Case count label
        self.library_count_label = QLabel("0 cases")
        self.library_count_label.setStyleSheet("color: #666;")
        action_layout.addWidget(self.library_count_label)

        layout.addLayout(action_layout)

        # Load initial data
        self._refresh_library_table()

        return tab

    def _create_civil_rules_subtab(self) -> QWidget:
        """Create the Civil Rules sub-tab for Federal Rules of Civil Procedure."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Header
        header = QLabel("Federal Rules of Civil Procedure")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(header)

        description = QLabel(
            "Browse and search the Federal Rules of Civil Procedure. "
            "Select a rule to view its full text."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #666;")
        layout.addWidget(description)

        # Search and Full Text button row
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_label.setStyleSheet("font-weight: bold;")
        search_layout.addWidget(search_label)

        self.civil_rules_search = QLineEdit()
        self.civil_rules_search.setPlaceholderText("Search rules...")
        self.civil_rules_search.textChanged.connect(self._on_civil_rules_search)
        search_layout.addWidget(self.civil_rules_search)

        # Full Text button
        self.civil_full_text_btn = QPushButton("Full Text")
        self.civil_full_text_btn.setStyleSheet("""
            QPushButton {
                background: #5a9fd4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #4a8fc4;
            }
        """)
        self.civil_full_text_btn.clicked.connect(self._show_civil_full_text)
        search_layout.addWidget(self.civil_full_text_btn)
        layout.addLayout(search_layout)

        # Split view: rules list and rule content
        from PyQt6.QtWidgets import QSplitter
        from PyQt6.QtCore import Qt
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Rules list
        self.civil_rules_list = QListWidget()
        self.civil_rules_list.setStyleSheet("""
            QListWidget {
                background: white;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background: #4a90d9;
                color: white;
            }
        """)
        self.civil_rules_list.itemClicked.connect(self._on_civil_rule_selected)
        splitter.addWidget(self.civil_rules_list)

        # Rule content viewer
        self.civil_rule_content = QTextEdit()
        self.civil_rule_content.setReadOnly(True)
        self.civil_rule_content.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-family: 'Times New Roman', serif;
                font-size: 14px;
                padding: 10px;
            }
        """)
        splitter.addWidget(self.civil_rule_content)

        splitter.setSizes([300, 500])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)  # Stretch factor 1 to fill vertical space

        # Load rules
        self._load_civil_rules()

        return tab

    def _show_civil_full_text(self):
        """Show the full text of Federal Rules of Civil Procedure."""
        if hasattr(self, 'civil_rules_full_text'):
            self.civil_rules_list.clearSelection()
            self.civil_rule_content.setPlainText(self.civil_rules_full_text)

    def _create_criminal_rules_subtab(self) -> QWidget:
        """Create the Criminal Rules sub-tab for Mississippi Rules of Criminal Procedure."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Header
        header = QLabel("Mississippi Rules of Criminal Procedure")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(header)

        description = QLabel(
            "Browse and search the Mississippi Rules of Criminal Procedure. "
            "Select a rule to view its full text."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #666;")
        layout.addWidget(description)

        # Search and Full Text button row
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_label.setStyleSheet("font-weight: bold;")
        search_layout.addWidget(search_label)

        self.criminal_rules_search = QLineEdit()
        self.criminal_rules_search.setPlaceholderText("Search rules...")
        self.criminal_rules_search.textChanged.connect(self._on_criminal_rules_search)
        search_layout.addWidget(self.criminal_rules_search)

        # Full Text button
        self.criminal_full_text_btn = QPushButton("Full Text")
        self.criminal_full_text_btn.setStyleSheet("""
            QPushButton {
                background: #5a9fd4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #4a8fc4;
            }
        """)
        self.criminal_full_text_btn.clicked.connect(self._show_criminal_full_text)
        search_layout.addWidget(self.criminal_full_text_btn)
        layout.addLayout(search_layout)

        # Split view: rules list and rule content
        from PyQt6.QtWidgets import QSplitter
        from PyQt6.QtCore import Qt
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Rules list
        self.criminal_rules_list = QListWidget()
        self.criminal_rules_list.setStyleSheet("""
            QListWidget {
                background: white;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background: #4a90d9;
                color: white;
            }
        """)
        self.criminal_rules_list.itemClicked.connect(self._on_criminal_rule_selected)
        splitter.addWidget(self.criminal_rules_list)

        # Rule content viewer
        self.criminal_rule_content = QTextEdit()
        self.criminal_rule_content.setReadOnly(True)
        self.criminal_rule_content.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 1px solid #ddd;
                border-radius: 5px;
                font-family: 'Times New Roman', serif;
                font-size: 14px;
                padding: 10px;
            }
        """)
        splitter.addWidget(self.criminal_rule_content)

        splitter.setSizes([300, 500])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)  # Stretch factor 1 to fill vertical space

        # Load rules
        self._load_criminal_rules()

        return tab

    def _show_criminal_full_text(self):
        """Show the full text of Mississippi Rules of Criminal Procedure."""
        if hasattr(self, 'criminal_rules_full_text'):
            self.criminal_rules_list.clearSelection()
            self.criminal_rule_content.setPlainText(self.criminal_rules_full_text)

    def _load_civil_rules(self):
        """Load and parse Federal Rules of Civil Procedure."""
        import re
        from pathlib import Path

        txt_path = Path.home() / "Dropbox/Formarter Folder/case_library/Federal Rules of Civil Procedure.txt"
        if not txt_path.exists():
            self.civil_rules_list.addItem("Rules file not found")
            return

        text = txt_path.read_text(encoding='utf-8')
        self.civil_rules_full_text = text  # Store full text for "Full Text" view

        # Parse rules - find "Rule X. Title" patterns
        # Store rules as (rule_number, title, start_pos, end_pos)
        self.civil_rules_data = []
        rule_pattern = re.compile(r'^Rule (\d+(?:\.\d+)?)\.\s+(.+?)$', re.MULTILINE)

        matches = list(rule_pattern.finditer(text))
        seen_rules = set()

        for i, match in enumerate(matches):
            rule_num = match.group(1)
            title = match.group(2).strip()
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            # Skip if this is in the table of contents (actual rules start ~44000)
            if match.start() < 44000:
                continue

            # Skip TOC entries (they have dots like "........")
            if '....' in title or title.endswith('.'):
                continue

            # Clean title - remove any trailing dots/page numbers
            title = re.sub(r'\s*\.+\s*\d*$', '', title).strip()

            # Skip duplicates
            if rule_num in seen_rules:
                continue
            seen_rules.add(rule_num)

            rule_content = text[start:end].strip()
            self.civil_rules_data.append({
                'number': rule_num,
                'title': title,
                'content': rule_content
            })

        # Sort rules numerically
        def sort_key(r):
            parts = r['number'].split('.')
            return [int(p) if p.isdigit() else 0 for p in parts]
        self.civil_rules_data.sort(key=sort_key)

        # Add to list widget
        for rule in self.civil_rules_data:
            item = QListWidgetItem(f"Rule {rule['number']}. {rule['title']}")
            item.setData(256, rule)  # Store rule data
            self.civil_rules_list.addItem(item)

    def _load_criminal_rules(self):
        """Load and parse Mississippi Rules of Criminal Procedure."""
        import re
        from pathlib import Path

        txt_path = Path.home() / "Dropbox/Formarter Folder/case_library/Federal Rules of Criminal Procedure.txt"
        if not txt_path.exists():
            self.criminal_rules_list.addItem("Rules file not found")
            return

        text = txt_path.read_text(encoding='utf-8')
        self.criminal_rules_full_text = text  # Store full text for "Full Text" view

        # Find where the TOC ends - look for the header before actual content
        toc_end_marker = "MISSISSIPPI RULES OF CRIMINAL PROCEDURE\nRule 1  General Provisions"
        toc_end = text.find(toc_end_marker)
        if toc_end == -1:
            toc_end = 1100  # Fallback

        # Parse MS rules - format: "Rule X.Y  Title." or "Rule X  Title"
        self.criminal_rules_data = []
        # Match patterns like "Rule 1.1  Scope." or "Rule 2  Commencement" (2+ spaces)
        rule_pattern = re.compile(r'^Rule (\d+(?:\.\d+)?)\s{2,}(.+?)\.?$', re.MULTILINE)

        matches = list(rule_pattern.finditer(text))
        seen_rules = set()  # Track seen rules to avoid duplicates

        for i, match in enumerate(matches):
            rule_num = match.group(1)
            title = match.group(2).strip().rstrip('.')
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            # Skip TOC entries
            if match.start() < toc_end:
                continue

            # Filter out false positives from comments (titles that look like sentences)
            # Real rule titles start with uppercase and are reasonably short
            if not title or not title[0].isupper():
                continue
            if title.lower().startswith(('is ', 'are ', 'was ', 'were ', 'has ', 'have ', 'and ', 'or ', 'but ', 'the ')):
                continue

            # Skip duplicate rules (by number only - take the first occurrence)
            if rule_num in seen_rules:
                continue
            seen_rules.add(rule_num)

            rule_content = text[start:end].strip()
            self.criminal_rules_data.append({
                'number': rule_num,
                'title': title,
                'content': rule_content
            })

        # Sort rules numerically
        def sort_key(r):
            parts = r['number'].split('.')
            return [int(p) for p in parts]
        self.criminal_rules_data.sort(key=sort_key)

        # Add to list widget
        for rule in self.criminal_rules_data:
            item = QListWidgetItem(f"Rule {rule['number']}  {rule['title']}")
            item.setData(256, rule)  # Store rule data
            self.criminal_rules_list.addItem(item)

    def _on_civil_rule_selected(self, item):
        """Handle selection of a civil rule."""
        rule_data = item.data(256)
        if rule_data:
            self.civil_rule_content.setPlainText(rule_data['content'])

    def _on_criminal_rule_selected(self, item):
        """Handle selection of a criminal rule."""
        rule_data = item.data(256)
        if rule_data:
            self.criminal_rule_content.setPlainText(rule_data['content'])

    def _on_civil_rules_search(self, query):
        """Filter civil rules by search query."""
        query = query.lower().strip()
        for i in range(self.civil_rules_list.count()):
            item = self.civil_rules_list.item(i)
            rule_data = item.data(256)
            if rule_data:
                visible = (query in item.text().lower() or
                          query in rule_data.get('content', '').lower())
                item.setHidden(not visible)
            else:
                item.setHidden(bool(query))

    def _on_criminal_rules_search(self, query):
        """Filter criminal rules by search query."""
        query = query.lower().strip()
        for i in range(self.criminal_rules_list.count()):
            item = self.criminal_rules_list.item(i)
            rule_data = item.data(256)
            if rule_data:
                visible = (query in item.text().lower() or
                          query in rule_data.get('content', '').lower())
                item.setHidden(not visible)
            else:
                item.setHidden(bool(query))

    # ========== Library Tab Methods ==========

    def _refresh_library_categories(self):
        """Refresh the category dropdown in Library tab."""
        self.library_category_dropdown.clear()
        self.library_category_dropdown.addItem("All Categories", "")

        for cat in self.case_library.list_categories():
            self.library_category_dropdown.addItem(cat.name, cat.id)

    def _refresh_library_table(self):
        """Refresh the library table with current filter/search."""
        # Get filter criteria
        category_id = self.library_category_dropdown.currentData() or ""
        search_query = self.library_search_input.text().strip()

        # Get cases
        if category_id:
            cases = self.case_library.filter_by_category(category_id)
        else:
            cases = self.case_library.list_all()

        # Apply search filter
        if search_query:
            search_lower = search_query.lower()
            cases = [
                c for c in cases
                if search_lower in c.case_name.lower()
                or search_lower in c.bluebook_citation.lower()
                or any(search_lower in kw.lower() for kw in c.keywords)
            ]

        # Update table
        self.library_table.setRowCount(len(cases))
        for row, case in enumerate(cases):
            # Store case ID in first column - format case name with proper title case
            name_item = QTableWidgetItem(format_case_name(case.case_name))
            name_item.setData(Qt.ItemDataRole.UserRole, case.id)
            self.library_table.setItem(row, 0, name_item)

            self.library_table.setItem(row, 1, QTableWidgetItem(case.short_citation))
            self.library_table.setItem(row, 2, QTableWidgetItem(case.court))
            self.library_table.setItem(row, 3, QTableWidgetItem(case.year))

            # Get category name
            cat = self.case_library.get_category(case.category_id)
            cat_name = cat.name if cat else ""
            self.library_table.setItem(row, 4, QTableWidgetItem(cat_name))

            self.library_table.setItem(row, 5, QTableWidgetItem(", ".join(case.keywords)))

        # Update count
        self.library_count_label.setText(f"{len(cases)} case{'s' if len(cases) != 1 else ''}")

    def _get_selected_library_case_id(self) -> str:
        """Get the ID of the currently selected case in the library table."""
        selected = self.library_table.selectedItems()
        if selected:
            # Get the item in the first column of the selected row
            row = selected[0].row()
            name_item = self.library_table.item(row, 0)
            if name_item:
                return name_item.data(Qt.ItemDataRole.UserRole)
        return ""

    def _on_library_filter_changed(self):
        """Handle category filter change."""
        self._refresh_library_table()

    def _on_library_search_changed(self):
        """Handle search text change."""
        self._refresh_library_table()

    def _on_library_selection_changed(self):
        """Handle selection change in library table."""
        has_selection = len(self.library_table.selectedItems()) > 0
        self.lib_open_pdf_btn.setEnabled(has_selection)
        self.lib_view_text_btn.setEnabled(has_selection)
        self.lib_copy_citation_btn.setEnabled(has_selection)
        self.lib_view_citations_btn.setEnabled(has_selection)
        self.lib_edit_btn.setEnabled(has_selection)
        self.lib_delete_btn.setEnabled(has_selection)

    def _on_add_case(self):
        """Import a single PDF - processes immediately without prompts."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF File", "", "PDF Files (*.pdf)"
        )
        if not file_path:
            return

        # Process immediately with batch import (handles single file too)
        result = self.case_library.batch_import([file_path])

        if result.successful:
            case = result.successful[0]
            # Show what was imported - citation if extracted, filename otherwise
            display_name = case.bluebook_citation if case.volume else case.case_name
            QMessageBox.information(
                self, "Imported",
                f"Added to library: {display_name}"
            )
        elif result.duplicates:
            QMessageBox.information(
                self, "Duplicate",
                f"This case is already in the library."
            )
        elif result.errors:
            QMessageBox.critical(
                self, "Error",
                f"Failed to import: {result.errors[0][1]}"
            )

        self._refresh_library_table()
        self._refresh_library_categories()

    def _on_batch_import(self):
        """Import multiple PDFs - processes immediately without dialogs."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select PDF Files", "", "PDF Files (*.pdf)"
        )
        if not file_paths:
            return

        # Process all files immediately
        result = self.case_library.batch_import(file_paths)

        # Show summary
        msg_parts = []
        if result.successful:
            msg_parts.append(f"{len(result.successful)} imported")
        if result.duplicates:
            msg_parts.append(f"{len(result.duplicates)} duplicates skipped")
        if result.errors:
            msg_parts.append(f"{len(result.errors)} errors")

        msg = "\n".join(msg_parts) if msg_parts else "No files processed"
        QMessageBox.information(self, "Import Complete", msg)

        self._refresh_library_table()
        self._refresh_library_categories()

    def _on_library_open_pdf(self):
        """Open the selected case's PDF in the default viewer."""
        case_id = self._get_selected_library_case_id()
        if case_id:
            pdf_path = self.case_library.get_pdf_path(case_id)
            if pdf_path and pdf_path.exists():
                import subprocess
                subprocess.run(["open", str(pdf_path)])
            else:
                QMessageBox.warning(self, "PDF Not Found", "The PDF file could not be found.")

    def _on_library_view_text(self):
        """Show the extracted text for the selected case."""
        case_id = self._get_selected_library_case_id()
        if case_id:
            case = self.case_library.get_by_id(case_id)
            text = self.case_library.get_case_text(case_id)
            if text:
                dialog = QDialog(self)
                dialog.setWindowTitle(f"Text: {case.case_name}")
                dialog.resize(700, 500)
                layout = QVBoxLayout(dialog)

                text_edit = QTextEdit()
                text_edit.setReadOnly(True)
                text_edit.setPlainText(text)
                text_edit.setFont(QFont("Courier New", 11))
                layout.addWidget(text_edit)

                close_btn = QPushButton("Close")
                close_btn.clicked.connect(dialog.accept)
                layout.addWidget(close_btn)

                dialog.exec()
            else:
                QMessageBox.information(self, "No Text", "No extracted text available for this case.")

    def _on_library_copy_citation(self):
        """Copy the Bluebook citation to clipboard."""
        case_id = self._get_selected_library_case_id()
        if case_id:
            case = self.case_library.get_by_id(case_id)
            if case:
                clipboard = QApplication.clipboard()
                clipboard.setText(case.bluebook_citation)
                QMessageBox.information(self, "Copied", "Citation copied to clipboard.")

    def _on_library_view_citations(self):
        """View the extracted citations for the selected case with enhanced table view."""
        case_id = self._get_selected_library_case_id()
        if case_id:
            citations = self.case_library.get_case_citations(case_id)
            if citations:
                # Create a dialog to display citations
                dialog = QDialog(self)
                dialog.setWindowTitle("Extracted Citations - Enhanced View")
                dialog.setMinimumSize(1000, 600)

                layout = QVBoxLayout(dialog)

                # Header label
                case = self.case_library.get_by_id(case_id)
                header = QLabel(f"Citations extracted from: {case.case_name}")
                header.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
                layout.addWidget(header)

                # Create table widget
                table = QTableWidget()
                table.setColumnCount(4)
                table.setHorizontalHeaderLabels(["Citation", "Context", "In Library", "Actions"])
                table.setRowCount(len(citations))
                table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
                table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
                table.setAlternatingRowColors(True)

                # Set column widths
                table.setColumnWidth(0, 200)  # Citation
                table.setColumnWidth(1, 400)  # Context
                table.setColumnWidth(2, 100)  # In Library
                table.setColumnWidth(3, 150)  # Actions

                # Populate table
                for row, citation in enumerate(citations):
                    # Column 0: Citation
                    citation_item = QTableWidgetItem(citation)
                    citation_item.setFont(QFont("Arial", 10))
                    table.setItem(row, 0, citation_item)

                    # Column 1: Context (extract from source text)
                    context = self.case_library.find_citation_context(case_id, citation, context_chars=200)
                    context_text = context if context else "Context not found"
                    context_item = QTableWidgetItem(context_text)
                    context_item.setFont(QFont("Arial", 9))
                    context_item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
                    context_item.setToolTip(context_text)  # Show full context on hover
                    table.setItem(row, 1, context_item)

                    # Column 2: In Library (check if citation exists)
                    matched_case = self.case_library.find_citation_in_library(citation)
                    if matched_case:
                        status_item = QTableWidgetItem("✓ Yes")
                        status_item.setForeground(QColor("#27AE60"))  # Green
                        status_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                        status_item.setToolTip(f"Matched to: {matched_case.case_name}")
                        # Highlight row in green
                        citation_item.setBackground(QColor("#D5F4E6"))
                        context_item.setBackground(QColor("#D5F4E6"))
                        status_item.setBackground(QColor("#D5F4E6"))
                    else:
                        status_item = QTableWidgetItem("✗ No")
                        status_item.setForeground(QColor("#E67E22"))  # Orange
                        status_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                        status_item.setToolTip("This case is not in your library")
                        # Highlight row in orange
                        citation_item.setBackground(QColor("#FFF3E0"))
                        context_item.setBackground(QColor("#FFF3E0"))
                        status_item.setBackground(QColor("#FFF3E0"))
                    table.setItem(row, 2, status_item)

                    # Column 3: Actions (button to open case if in library)
                    if matched_case:
                        open_btn = QPushButton("Open Case")
                        open_btn.setStyleSheet("""
                            QPushButton {
                                background: #27AE60;
                                color: white;
                                border: none;
                                padding: 5px 10px;
                                border-radius: 3px;
                                font-weight: bold;
                            }
                            QPushButton:hover {
                                background: #229954;
                            }
                        """)
                        # Store the case ID for the button click handler
                        open_btn.clicked.connect(lambda checked, cid=matched_case.id: self._open_library_case_pdf(cid))
                        table.setCellWidget(row, 3, open_btn)
                    else:
                        action_item = QTableWidgetItem("—")
                        action_item.setForeground(QColor("#BDC3C7"))  # Gray
                        action_item.setBackground(QColor("#FFF3E0"))
                        table.setItem(row, 3, action_item)

                # Adjust row heights to fit content
                table.resizeRowsToContents()

                layout.addWidget(table)

                # Summary label
                in_library_count = sum(1 for c in citations if self.case_library.find_citation_in_library(c))
                missing_count = len(citations) - in_library_count
                summary = QLabel(f"Total: {len(citations)} citations | In Library: {in_library_count} | Missing: {missing_count}")
                summary.setStyleSheet("font-size: 12px; color: #7F8C8D; margin-top: 10px;")
                layout.addWidget(summary)

                # Close button
                close_btn = QPushButton("Close")
                close_btn.clicked.connect(dialog.accept)
                layout.addWidget(close_btn)

                dialog.exec()
            else:
                QMessageBox.information(
                    self, "No Citations",
                    "No citations have been extracted for this case yet."
                )

    def _open_library_case_pdf(self, case_id: str):
        """Open a library case PDF by its ID."""
        case = self.case_library.get_by_id(case_id)
        if case:
            pdf_path = self.case_library.storage_dir / case.pdf_filename
            if pdf_path.exists():
                import subprocess
                import platform

                system = platform.system()
                try:
                    if system == "Darwin":  # macOS
                        subprocess.run(["open", str(pdf_path)])
                    elif system == "Windows":
                        subprocess.run(["start", str(pdf_path)], shell=True)
                    else:  # Linux
                        subprocess.run(["xdg-open", str(pdf_path)])
                except Exception as e:
                    QMessageBox.warning(
                        self, "Error",
                        f"Could not open PDF: {e}"
                    )
            else:
                QMessageBox.warning(
                    self, "File Not Found",
                    f"PDF file not found: {case.pdf_filename}"
                )

    def _on_regenerate_all_citations(self):
        """Regenerate citations for all cases in the library."""
        reply = QMessageBox.question(
            self, "Regenerate All Citations",
            "This will regenerate citations for all cases in the library using the current extraction logic. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            successful, failed = self.case_library.regenerate_all_citations()
            QMessageBox.information(
                self, "Citations Regenerated",
                f"Successfully regenerated citations for {successful} cases.\n{failed} cases failed."
            )

    def _on_library_edit_tags(self):
        """Edit the category and keywords for the selected case."""
        case_id = self._get_selected_library_case_id()
        if case_id:
            case = self.case_library.get_by_id(case_id)
            if case:
                dialog = EditTagsDialog(self.case_library, case, self)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    self._refresh_library_table()
                    self._refresh_library_categories()

    def _on_library_delete(self):
        """Delete the selected case from the library."""
        case_id = self._get_selected_library_case_id()
        if case_id:
            case = self.case_library.get_by_id(case_id)
            if case:
                reply = QMessageBox.question(
                    self, "Confirm Delete",
                    f"Are you sure you want to delete:\n\n{case.bluebook_citation}\n\nThis will remove the PDF and text files.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.case_library.delete(case_id)
                    self._refresh_library_table()

    # =========================================================================
    # AUDITOR TAB - TRO Motion Compliance Checker
    # =========================================================================

    def _create_auditor_tab(self) -> QWidget:
        """Create the Auditor tab for TRO motion compliance checking."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Top bar: Document selector + Options + Run button
        top_bar = QHBoxLayout()

        doc_label = QLabel("Document:")
        doc_label.setStyleSheet("font-weight: bold;")
        top_bar.addWidget(doc_label)

        self.auditor_doc_dropdown = QComboBox()
        self.auditor_doc_dropdown.setMinimumWidth(350)
        self._refresh_auditor_doc_list()
        top_bar.addWidget(self.auditor_doc_dropdown)

        # Options checkboxes
        self.audit_ex_parte_cb = QCheckBox("Ex Parte")
        self.audit_ex_parte_cb.setToolTip("Check if this is an ex parte motion")
        top_bar.addWidget(self.audit_ex_parte_cb)

        self.audit_urgent_cb = QCheckBox("Urgent")
        self.audit_urgent_cb.setToolTip("Check if this requires expedited review")
        top_bar.addWidget(self.audit_urgent_cb)

        audit_btn = QPushButton("RUN AUDIT")
        audit_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 30px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        audit_btn.clicked.connect(self._on_run_audit)
        top_bar.addWidget(audit_btn)

        top_bar.addStretch()
        layout.addLayout(top_bar)

        # Summary bar with score
        self.audit_summary = QLabel("Select a document and click RUN AUDIT")
        self.audit_summary.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        self.audit_summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.audit_summary)

        # Main content: 3-column layout (Pass | Fail | Preview)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Column 1: PASSED items (green)
        pass_widget = QWidget()
        pass_layout = QVBoxLayout(pass_widget)
        pass_layout.setContentsMargins(0, 0, 0, 0)
        pass_layout.setSpacing(5)

        pass_header = QLabel("PASSED")
        pass_header.setStyleSheet("""
            QLabel {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                font-weight: bold;
                font-size: 14px;
                border-radius: 4px 4px 0 0;
            }
        """)
        pass_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pass_layout.addWidget(pass_header)

        self.audit_pass_list = QTreeWidget()
        self.audit_pass_list.setHeaderLabels(["#", "Item", "Rule"])
        self.audit_pass_list.setColumnWidth(0, 35)
        self.audit_pass_list.setColumnWidth(1, 250)
        self.audit_pass_list.setRootIsDecorated(False)
        self.audit_pass_list.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #4CAF50;
                border-top: none;
                background-color: #f1f8e9;
            }
            QTreeWidget::item {
                padding: 3px;
            }
        """)
        pass_layout.addWidget(self.audit_pass_list)
        main_splitter.addWidget(pass_widget)

        # Column 2: FAILED + WARNING items (red/orange)
        fail_widget = QWidget()
        fail_layout = QVBoxLayout(fail_widget)
        fail_layout.setContentsMargins(0, 0, 0, 0)
        fail_layout.setSpacing(5)

        fail_header = QLabel("FAILED / WARNINGS")
        fail_header.setStyleSheet("""
            QLabel {
                background-color: #f44336;
                color: white;
                padding: 8px;
                font-weight: bold;
                font-size: 14px;
                border-radius: 4px 4px 0 0;
            }
        """)
        fail_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fail_layout.addWidget(fail_header)

        self.audit_fail_list = QTreeWidget()
        self.audit_fail_list.setHeaderLabels(["#", "Item", "Status", "Message"])
        self.audit_fail_list.setColumnWidth(0, 35)
        self.audit_fail_list.setColumnWidth(1, 200)
        self.audit_fail_list.setColumnWidth(2, 60)
        self.audit_fail_list.setRootIsDecorated(False)
        self.audit_fail_list.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #f44336;
                border-top: none;
                background-color: #ffebee;
            }
            QTreeWidget::item {
                padding: 3px;
            }
        """)
        fail_layout.addWidget(self.audit_fail_list)
        main_splitter.addWidget(fail_widget)

        # Column 3: Document Preview
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(5)

        preview_header = QLabel("DOCUMENT PREVIEW")
        preview_header.setStyleSheet("""
            QLabel {
                background-color: #2196F3;
                color: white;
                padding: 8px;
                font-weight: bold;
                font-size: 14px;
                border-radius: 4px 4px 0 0;
            }
        """)
        preview_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(preview_header)

        self.audit_preview = QTextEdit()
        self.audit_preview.setReadOnly(True)
        self.audit_preview.setPlaceholderText("Document content will appear here...")
        self.audit_preview.setStyleSheet("""
            QTextEdit {
                border: 1px solid #2196F3;
                border-top: none;
                font-family: 'Courier New', monospace;
                font-size: 11px;
                background-color: #e3f2fd;
            }
        """)
        preview_layout.addWidget(self.audit_preview)
        main_splitter.addWidget(preview_widget)

        # Set initial sizes (equal thirds)
        main_splitter.setSizes([300, 300, 400])

        layout.addWidget(main_splitter, 1)  # stretch factor 1 to fill space

        # Keep the old checklist tree for reference (hidden)
        self.checklist_tree = QTreeWidget()
        self._populate_checklist_tree()

        return tab

    def _refresh_auditor_doc_list(self):
        """Refresh the document dropdown in Auditor tab."""
        self.auditor_doc_dropdown.clear()
        self.auditor_doc_dropdown.addItem("-- Select a Document --", None)

        documents = self.storage.list_all()
        for doc in documents:
            case_name = self._get_case_name(doc.case_profile_index)
            display = f"{doc.name} (Case {case_name})"
            self.auditor_doc_dropdown.addItem(display, doc.id)

    def _populate_checklist_tree(self):
        """Populate the checklist tree with all 107 items grouped by category."""
        self.checklist_tree.clear()

        # Group items by category
        categories = {}
        for item in TRO_CHECKLIST:
            cat = item.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)

        # Add category nodes
        for category in CheckCategory:
            if category in categories:
                cat_item = QTreeWidgetItem(self.checklist_tree)
                cat_item.setText(0, "")
                cat_item.setText(1, category.value)
                cat_item.setText(2, "")
                cat_item.setText(3, "")
                cat_item.setExpanded(True)

                font = cat_item.font(1)
                font.setBold(True)
                cat_item.setFont(1, font)
                cat_item.setBackground(0, QColor("#e0e0e0"))
                cat_item.setBackground(1, QColor("#e0e0e0"))
                cat_item.setBackground(2, QColor("#e0e0e0"))
                cat_item.setBackground(3, QColor("#e0e0e0"))

                # Add items under this category
                for item in categories[category]:
                    child = QTreeWidgetItem(cat_item)
                    child.setText(0, str(item.id))
                    child.setText(1, item.description)
                    child.setText(2, "-")
                    child.setText(3, item.rule_citation)
                    child.setData(0, Qt.ItemDataRole.UserRole, item.id)

    def _on_run_audit(self):
        """Run compliance audit on selected document."""
        doc_id = self.auditor_doc_dropdown.currentData()
        if not doc_id:
            QMessageBox.warning(
                self, "No Document Selected",
                "Please select a document to audit."
            )
            return

        doc = self.storage.get_by_id(doc_id)
        if not doc:
            QMessageBox.warning(
                self, "Document Not Found",
                "The selected document could not be found."
            )
            return

        # Show document in preview
        self.audit_preview.setPlainText(doc.text_content)

        # Get case number from case profile
        case_number = ""
        if doc.case_profile_index and doc.case_profile_index <= len(self.CASE_PROFILES):
            case_profile = self.CASE_PROFILES[doc.case_profile_index - 1]
            case_number = case_profile.caption.case_number or ""

        # Build audit options from UI
        # Check if a case profile is selected (signature block will be auto-generated)
        has_case_profile = bool(doc.case_profile_index and doc.case_profile_index > 0)

        options = AuditOptions(
            is_ex_parte=self.audit_ex_parte_cb.isChecked(),
            is_urgent=self.audit_urgent_cb.isChecked(),
            custom_title=doc.custom_title or "",
            case_number=case_number,
            has_case_profile=has_case_profile
        )

        # Run the compliance detector with options
        detector = ComplianceDetector(
            document_text=doc.text_content,
            document_id=doc.id,
            document_name=doc.name,
            options=options
        )

        # Run all checks with real-time logging
        result = detector.run_all_checks(self.storage.storage_dir)

        # Update the checklist tree with results
        self._display_audit_results(result)

        # Update summary
        self._update_audit_summary(result)

    def _display_audit_results(self, result: AuditResult):
        """Update the PASS and FAIL lists with audit results."""
        # Clear existing lists
        self.audit_pass_list.clear()
        self.audit_fail_list.clear()

        # Get checklist items for descriptions
        from src.auditor.checklist import TRO_CHECKLIST
        checklist_map = {item.id: item for item in TRO_CHECKLIST}

        # Sort results into pass/fail lists
        passed_items = []
        failed_items = []
        warning_items = []
        manual_items = []
        na_items = []

        for item_result in result.items:
            status = item_result.status
            item_id = item_result.item_id
            checklist_item = checklist_map.get(item_id)

            if status == CheckStatus.PASS.value:
                passed_items.append((item_id, item_result, checklist_item))
            elif status == CheckStatus.FAIL.value:
                failed_items.append((item_id, item_result, checklist_item))
            elif status == CheckStatus.WARNING.value:
                warning_items.append((item_id, item_result, checklist_item))
            elif status == CheckStatus.MANUAL.value:
                manual_items.append((item_id, item_result, checklist_item))
            elif status == CheckStatus.NOT_APPLICABLE.value:
                na_items.append((item_id, item_result, checklist_item))

        # Add PASSED items to left list (sorted by ID)
        for item_id, item_result, checklist_item in sorted(passed_items, key=lambda x: x[0]):
            description = checklist_item.description if checklist_item else f"Item {item_id}"
            rule = checklist_item.rule_citation if checklist_item else ""
            tree_item = QTreeWidgetItem([str(item_id), description, rule])
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item_id)
            tree_item.setToolTip(1, item_result.message)
            for col in range(3):
                tree_item.setBackground(col, QColor("#e8f5e9"))  # Light green
            self.audit_pass_list.addTopLevelItem(tree_item)

        # Add N/A items to pass list
        for item_id, item_result, checklist_item in sorted(na_items, key=lambda x: x[0]):
            description = checklist_item.description if checklist_item else f"Item {item_id}"
            rule = checklist_item.rule_citation if checklist_item else ""
            tree_item = QTreeWidgetItem([str(item_id), f"{description} [N/A]", rule])
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item_id)
            tree_item.setToolTip(1, item_result.message)
            for col in range(3):
                tree_item.setBackground(col, QColor("#f5f5f5"))  # Light gray
                tree_item.setForeground(col, QColor("#888888"))
            self.audit_pass_list.addTopLevelItem(tree_item)

        # Add FAILED items to right list (sorted by ID, critical first)
        failed_items_sorted = sorted(
            failed_items,
            key=lambda x: (0 if x[2] and x[2].fail_severity == "critical" else 1, x[0])
        )
        for item_id, item_result, checklist_item in failed_items_sorted:
            description = checklist_item.description if checklist_item else f"Item {item_id}"
            severity = checklist_item.fail_severity if checklist_item else "normal"
            success_criteria = checklist_item.success_criteria if checklist_item else ""
            fix_suggestion = checklist_item.fix_suggestion if checklist_item else ""

            # Mark critical items
            status_text = "CRITICAL" if severity == "critical" else "FAIL"
            tree_item = QTreeWidgetItem([str(item_id), description, status_text, item_result.message[:50]])
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item_id)
            tooltip = item_result.message
            if fix_suggestion:
                tooltip += f"\n\n🔧 HOW TO FIX:\n{fix_suggestion}"
            if success_criteria:
                tooltip += f"\n\n✓ What success looks like:\n{success_criteria}"
            tree_item.setToolTip(1, tooltip)

            if severity == "critical":
                for col in range(4):
                    tree_item.setBackground(col, QColor("#ffcdd2"))  # Light red
                    tree_item.setForeground(col, QColor("#c62828"))  # Dark red
            else:
                for col in range(4):
                    tree_item.setBackground(col, QColor("#ffebee"))  # Very light red
                    tree_item.setForeground(col, QColor("#d32f2f"))

            self.audit_fail_list.addTopLevelItem(tree_item)

        # Add WARNING items to fail list
        for item_id, item_result, checklist_item in sorted(warning_items, key=lambda x: x[0]):
            description = checklist_item.description if checklist_item else f"Item {item_id}"
            fix_suggestion = checklist_item.fix_suggestion if checklist_item else ""
            tree_item = QTreeWidgetItem([str(item_id), description, "WARN", item_result.message[:50]])
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item_id)
            tooltip = item_result.message
            if fix_suggestion:
                tooltip += f"\n\n🔧 HOW TO FIX:\n{fix_suggestion}"
            tree_item.setToolTip(1, tooltip)
            for col in range(4):
                tree_item.setBackground(col, QColor("#fff9c4"))  # Light yellow
                tree_item.setForeground(col, QColor("#f57f17"))  # Orange
            self.audit_fail_list.addTopLevelItem(tree_item)

        # Add MANUAL items to fail list (need attention)
        for item_id, item_result, checklist_item in sorted(manual_items, key=lambda x: x[0]):
            description = checklist_item.description if checklist_item else f"Item {item_id}"
            success_criteria = checklist_item.success_criteria if checklist_item else ""
            tree_item = QTreeWidgetItem([str(item_id), description, "MANUAL", item_result.message[:50]])
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item_id)
            tooltip = item_result.message
            if success_criteria:
                tooltip += f"\n\nWhat success looks like:\n{success_criteria}"
            tree_item.setToolTip(1, tooltip)
            for col in range(4):
                tree_item.setBackground(col, QColor("#e0e0e0"))  # Gray
                tree_item.setForeground(col, QColor("#616161"))
            self.audit_fail_list.addTopLevelItem(tree_item)

    def _update_audit_summary(self, result: AuditResult):
        """Update the audit summary display."""
        summary_text = f"""
<b style="font-size: 16px;">{result.document_name}</b><br>
<span style="color: #666;">Audited: {result.audit_date[:19].replace('T', ' ')}</span>
<br><br>
<b>Score: {result.score:.1f}%</b> ({result.checked_count} items checked)<br><br>
<span style="color: #2e7d32;">PASSED: {result.passed}</span> |
<span style="color: #c62828;">FAILED: {result.failed}</span> |
<span style="color: #f57f17;">WARNING: {result.warnings}</span> |
<span style="color: #616161;">MANUAL: {result.manual_review}</span>
"""

        if result.critical_issues:
            summary_text += "<br><br><b style='color: #c62828;'>Critical Issues:</b><ul>"
            for issue in result.critical_issues[:5]:  # Show max 5
                summary_text += f"<li>{issue}</li>"
            summary_text += "</ul>"

        self.audit_summary.setText(summary_text)

    def _on_checklist_item_clicked(self, item, column):
        """Handle click on checklist item - jump to location in preview."""
        line_num = item.data(1, Qt.ItemDataRole.UserRole)
        if line_num:
            # Move cursor to that line in preview
            cursor = self.audit_preview.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)

            for _ in range(line_num - 1):
                cursor.movePosition(QTextCursor.MoveOperation.Down)

            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            self.audit_preview.setTextCursor(cursor)
            self.audit_preview.ensureCursorVisible()

            # Highlight the line
            extra_selections = []
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor("#fff9c4"))  # Yellow highlight
            selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
            selection.cursor = cursor
            extra_selections.append(selection)
            self.audit_preview.setExtraSelections(extra_selections)

    # =========================================================================
    # QUICK PRINT TAB - Emergency Standalone Documents
    # =========================================================================

    def _create_quick_print_tab(self) -> QWidget:
        """Create the Quick Print tab for emergency standalone documents."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header
        header = QLabel("Quick Print - Emergency Documents")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(header)

        description = QLabel(
            "Generate standalone documents for emergency filing. "
            "These pages can be printed separately and attached to your filing."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #666;")
        layout.addWidget(description)

        # Case Profile selector
        profile_layout = QHBoxLayout()
        profile_label = QLabel("Case Profile:")
        profile_label.setStyleSheet("font-weight: bold;")
        profile_layout.addWidget(profile_label)

        self.quick_print_profile_dropdown = QComboBox()
        self.quick_print_profile_dropdown.setMinimumWidth(300)
        for i, profile in enumerate(self.CASE_PROFILES):
            self.quick_print_profile_dropdown.addItem(profile.name, i)
        profile_layout.addWidget(self.quick_print_profile_dropdown)
        profile_layout.addStretch()
        layout.addLayout(profile_layout)

        # Date option
        date_layout = QHBoxLayout()
        self.quick_print_date_cb = QCheckBox("Add specific date?")
        self.quick_print_date_cb.setChecked(False)
        self.quick_print_date_cb.stateChanged.connect(self._on_quick_print_date_toggle)
        date_layout.addWidget(self.quick_print_date_cb)

        from PyQt6.QtWidgets import QDateEdit
        from PyQt6.QtCore import QDate
        self.quick_print_date_edit = QDateEdit()
        self.quick_print_date_edit.setDate(QDate.currentDate())
        self.quick_print_date_edit.setCalendarPopup(True)
        self.quick_print_date_edit.setEnabled(False)  # Disabled by default
        self.quick_print_date_edit.setStyleSheet("QDateEdit:disabled { color: #999; }")
        date_layout.addWidget(self.quick_print_date_edit)

        date_hint = QLabel("<i>(When unchecked, prints blank lines to fill by hand)</i>")
        date_hint.setStyleSheet("color: #666;")
        date_layout.addWidget(date_hint)
        date_layout.addStretch()
        layout.addLayout(date_layout)

        # Buttons grid
        buttons_group = QGroupBox("Standalone Documents")
        buttons_layout = QGridLayout(buttons_group)
        buttons_layout.setSpacing(15)

        # Signature Block button
        sig_btn = QPushButton("Signature Block\n+ Certificate of Service")
        sig_btn.setMinimumSize(200, 80)
        sig_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 15px;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        sig_btn.clicked.connect(lambda: self._on_print_signature_block(include_cert=True))
        buttons_layout.addWidget(sig_btn, 0, 0)

        # Signature Block Only button
        sig_only_btn = QPushButton("Signature Block\nOnly")
        sig_only_btn.setMinimumSize(200, 80)
        sig_only_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 15px;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        sig_only_btn.clicked.connect(lambda: self._on_print_signature_block(include_cert=False))
        buttons_layout.addWidget(sig_only_btn, 0, 1)

        # Certificate of Service Only button
        cert_only_btn = QPushButton("Certificate of Service\nOnly")
        cert_only_btn.setMinimumSize(200, 80)
        cert_only_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 15px;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        cert_only_btn.clicked.connect(self._on_print_certificate_only)
        buttons_layout.addWidget(cert_only_btn, 0, 2)

        layout.addWidget(buttons_group)

        # Preview area
        preview_label = QLabel("Preview")
        preview_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
        layout.addWidget(preview_label)

        self.quick_print_preview = QTextEdit()
        self.quick_print_preview.setReadOnly(True)
        self.quick_print_preview.setPlaceholderText("Click a button above to generate a preview...")
        self.quick_print_preview.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                font-family: 'Times New Roman', serif;
                font-size: 12px;
                background-color: white;
            }
        """)
        layout.addWidget(self.quick_print_preview)

        return tab

    def _create_executed_filings_tab(self) -> QWidget:
        """Create the Executed Filings tab with 3 case sub-tabs."""
        from pathlib import Path
        import json

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Define the 3 cases
        self._lawsuit_cases = [
            {'id': '178', 'name': 'Petrini v. City of Biloxi', 'number': '1:25-cv-00178-LG-RPM'},
            {'id': '233', 'name': 'Case 233 (TBD)', 'number': '1:25-cv-00233'},
            {'id': '254', 'name': 'Case 254 (TBD)', 'number': '1:25-cv-00254'},
        ]

        # Main case tabs at top level
        self.case_tabs = QTabWidget()
        self.case_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: white;
            }
            QTabBar::tab {
                padding: 10px 20px;
                margin-right: 3px;
                background: #E3F2FD;
                border: 1px solid #1976D2;
                border-bottom: none;
                border-radius: 6px 6px 0 0;
                font-weight: bold;
                color: #1565C0;
            }
            QTabBar::tab:selected {
                background: #1976D2;
                color: white;
            }
        """)

        # Create a tab for each case
        self._case_widgets = {}
        for case in self._lawsuit_cases:
            case_widget = self._create_case_content_widget(case)
            self.case_tabs.addTab(case_widget, f"Case {case['id']}")
            self._case_widgets[case['id']] = case_widget

        layout.addWidget(self.case_tabs)

        # Load timeline data from JSON
        self._timeline_data = self._load_timeline_data()

        # Initialize current case
        self._current_case_id = '178'
        self._refresh_case_filings('178')

        return tab

    def _create_exhibit_bank_tab(self) -> QWidget:
        """Create the Exhibit Bank tab for storing and managing exhibits."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Initialize exhibit bank
        self.exhibit_bank = ExhibitBank()
        self._current_folder_id = ""  # Empty string = root folder

        # Header
        header = QLabel("Exhibit Bank")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(header)

        description = QLabel(
            "Store, organize, and manage exhibits (PDFs, images, documents) for use in filings. "
            "Add tags for easy searching and create redacted versions when needed."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(description)

        # Toolbar with buttons
        toolbar_layout = QHBoxLayout()

        # Add Exhibit button
        add_exhibit_btn = QPushButton("+ Add Exhibit")
        add_exhibit_btn.setStyleSheet("""
            QPushButton {
                background: #4a90d9;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #357abd;
            }
        """)
        add_exhibit_btn.clicked.connect(self._on_add_exhibit)
        toolbar_layout.addWidget(add_exhibit_btn)

        # New Folder button
        new_folder_btn = QPushButton("+ New Folder")
        new_folder_btn.setStyleSheet("""
            QPushButton {
                background: #f39c12;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #e67e22;
            }
        """)
        new_folder_btn.clicked.connect(self._on_create_folder)
        toolbar_layout.addWidget(new_folder_btn)

        # Manage Tags button
        manage_tags_btn = QPushButton("Manage Tags")
        manage_tags_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        manage_tags_btn.clicked.connect(self._on_manage_exhibit_tags)
        toolbar_layout.addWidget(manage_tags_btn)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #218838;
            }
        """)
        refresh_btn.clicked.connect(self._refresh_exhibit_list)
        toolbar_layout.addWidget(refresh_btn)

        # Open File button
        open_file_btn = QPushButton("Open File")
        open_file_btn.setStyleSheet("""
            QPushButton {
                background: #17a2b8;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #138496;
            }
        """)
        open_file_btn.clicked.connect(self._on_open_exhibit_file)
        toolbar_layout.addWidget(open_file_btn)

        # Generate Exhibit Tags button
        gen_tags_btn = QPushButton("Generate Exhibit Tags")
        gen_tags_btn.setStyleSheet("""
            QPushButton {
                background: #9b59b6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #8e44ad;
            }
        """)
        gen_tags_btn.clicked.connect(self._on_generate_exhibit_tags)
        toolbar_layout.addWidget(gen_tags_btn)

        toolbar_layout.addStretch()

        # Stats label
        self.exhibit_stats_label = QLabel("")
        self.exhibit_stats_label.setStyleSheet("color: #666;")
        toolbar_layout.addWidget(self.exhibit_stats_label)

        layout.addLayout(toolbar_layout)

        # Filter row
        filter_layout = QHBoxLayout()

        # Search box
        search_label = QLabel("Search:")
        filter_layout.addWidget(search_label)

        self.exhibit_search_edit = QLineEdit()
        self.exhibit_search_edit.setPlaceholderText("Search by title, description, notes...")
        self.exhibit_search_edit.textChanged.connect(self._on_exhibit_search_changed)
        self.exhibit_search_edit.setMaximumWidth(300)
        filter_layout.addWidget(self.exhibit_search_edit)

        # Tag filter
        tag_label = QLabel("Tag:")
        filter_layout.addWidget(tag_label)

        self.exhibit_tag_filter = QComboBox()
        self.exhibit_tag_filter.addItem("All Tags", "")
        for tag in self.exhibit_bank.list_tags():
            self.exhibit_tag_filter.addItem(tag.name, tag.name)
        self.exhibit_tag_filter.currentIndexChanged.connect(self._on_exhibit_filter_changed)
        self.exhibit_tag_filter.setMinimumWidth(150)
        filter_layout.addWidget(self.exhibit_tag_filter)

        # Type filter
        type_label = QLabel("Type:")
        filter_layout.addWidget(type_label)

        self.exhibit_type_filter = QComboBox()
        self.exhibit_type_filter.addItem("All Types", "")
        self.exhibit_type_filter.addItem("PDF", "pdf")
        self.exhibit_type_filter.addItem("Image", "image")
        self.exhibit_type_filter.addItem("Document", "document")
        self.exhibit_type_filter.addItem("Other", "other")
        self.exhibit_type_filter.currentIndexChanged.connect(self._on_exhibit_filter_changed)
        filter_layout.addWidget(self.exhibit_type_filter)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Folder navigation / breadcrumb bar
        folder_nav_layout = QHBoxLayout()
        folder_nav_layout.setContentsMargins(0, 5, 0, 5)

        self.folder_breadcrumb = QLabel("Root")
        self.folder_breadcrumb.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #333;
                padding: 5px 10px;
                background: #f8f9fa;
                border-radius: 5px;
            }
        """)
        folder_nav_layout.addWidget(self.folder_breadcrumb)

        # Up button (go to parent folder)
        self.folder_up_btn = QPushButton("Up")
        self.folder_up_btn.setStyleSheet("""
            QPushButton {
                background: #e9ecef;
                color: #333;
                border: none;
                padding: 5px 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #dee2e6;
            }
            QPushButton:disabled {
                background: #f8f9fa;
                color: #adb5bd;
            }
        """)
        self.folder_up_btn.clicked.connect(self._on_folder_up)
        self.folder_up_btn.setEnabled(False)
        folder_nav_layout.addWidget(self.folder_up_btn)

        folder_nav_layout.addStretch()
        layout.addLayout(folder_nav_layout)

        # Main content area with splitter
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left side - exhibit list
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(0, 0, 0, 0)

        self.exhibit_table = QTreeWidget()
        self.exhibit_table.setColumnCount(5)
        self.exhibit_table.setHeaderLabels(["Title", "Type", "Tags", "Date Added", "Size"])
        self.exhibit_table.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        self.exhibit_table.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.exhibit_table.setEditTriggers(QTreeWidget.EditTrigger.NoEditTriggers)
        self.exhibit_table.header().setStretchLastSection(True)
        self.exhibit_table.setColumnWidth(0, 250)  # Title
        self.exhibit_table.setColumnWidth(1, 80)   # Type
        self.exhibit_table.setColumnWidth(2, 150)  # Tags
        self.exhibit_table.setColumnWidth(3, 100)  # Date
        self.exhibit_table.setColumnWidth(4, 80)   # Size
        self.exhibit_table.itemSelectionChanged.connect(self._on_exhibit_selected)
        self.exhibit_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.exhibit_table.customContextMenuRequested.connect(self._on_exhibit_context_menu)
        self.exhibit_table.itemDoubleClicked.connect(self._on_exhibit_double_clicked)

        # Enable drag and drop for file import and internal reordering
        self.exhibit_table.setAcceptDrops(True)
        self.exhibit_table.setDragEnabled(True)
        self.exhibit_table.setDragDropMode(QTreeWidget.DragDropMode.DragDrop)
        self.exhibit_table.viewport().setAcceptDrops(True)
        self.exhibit_table.setDropIndicatorShown(True)

        # Install event filter to handle drops
        self.exhibit_table.viewport().installEventFilter(self)

        list_layout.addWidget(self.exhibit_table)
        content_splitter.addWidget(list_widget)

        # Right side - exhibit details/preview
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(10, 0, 0, 0)

        detail_header = QLabel("Exhibit Details")
        detail_header.setStyleSheet("font-size: 14px; font-weight: bold;")
        detail_layout.addWidget(detail_header)

        # Detail fields
        self.exhibit_detail_title = QLabel("")
        self.exhibit_detail_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        self.exhibit_detail_title.setWordWrap(True)
        detail_layout.addWidget(self.exhibit_detail_title)

        self.exhibit_detail_info = QLabel("")
        self.exhibit_detail_info.setStyleSheet("color: #666;")
        self.exhibit_detail_info.setWordWrap(True)
        detail_layout.addWidget(self.exhibit_detail_info)

        # Tags display
        self.exhibit_detail_tags = QLabel("")
        self.exhibit_detail_tags.setWordWrap(True)
        detail_layout.addWidget(self.exhibit_detail_tags)

        # Description
        desc_label = QLabel("Description:")
        desc_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        detail_layout.addWidget(desc_label)

        self.exhibit_detail_desc = QLabel("")
        self.exhibit_detail_desc.setWordWrap(True)
        self.exhibit_detail_desc.setStyleSheet("color: #333;")
        detail_layout.addWidget(self.exhibit_detail_desc)

        # Notes
        notes_label = QLabel("Notes:")
        notes_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        detail_layout.addWidget(notes_label)

        self.exhibit_detail_notes = QLabel("")
        self.exhibit_detail_notes.setWordWrap(True)
        self.exhibit_detail_notes.setStyleSheet("color: #333;")
        detail_layout.addWidget(self.exhibit_detail_notes)

        # Thumbnail/Preview
        self.exhibit_thumbnail = QLabel()
        self.exhibit_thumbnail.setFixedSize(200, 200)
        self.exhibit_thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.exhibit_thumbnail.setStyleSheet("background: #f0f0f0; border: 1px solid #ddd;")
        detail_layout.addWidget(self.exhibit_thumbnail)

        # Action buttons
        action_layout = QHBoxLayout()

        open_btn = QPushButton("Open")
        open_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        open_btn.clicked.connect(self._on_open_exhibit)
        action_layout.addWidget(open_btn)

        edit_btn = QPushButton("Edit")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        edit_btn.clicked.connect(self._on_edit_exhibit)
        action_layout.addWidget(edit_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        delete_btn.clicked.connect(self._on_delete_exhibit)
        action_layout.addWidget(delete_btn)

        action_layout.addStretch()
        detail_layout.addLayout(action_layout)

        detail_layout.addStretch()
        content_splitter.addWidget(detail_widget)

        # Set splitter sizes
        content_splitter.setSizes([600, 300])
        layout.addWidget(content_splitter)

        # Load initial data
        self._refresh_exhibit_list()

        return tab

    # ========== Exhibit Bank Event Handlers ==========

    def _on_add_exhibit(self):
        """Add a new exhibit to the bank."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files to Add",
            str(Path.home()),
            "All Files (*);;PDF Files (*.pdf);;Images (*.jpg *.jpeg *.png *.gif *.bmp);;Documents (*.doc *.docx *.txt *.rtf)"
        )

        if not file_paths:
            return

        for file_path in file_paths:
            # Show dialog to get metadata
            dialog = ExhibitMetadataDialog(self, file_path, self.exhibit_bank.list_tags())
            if dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    exhibit = self.exhibit_bank.add_exhibit(
                        file_path=file_path,
                        title=dialog.title,
                        tags=dialog.tags,
                        folder_id=self._current_folder_id,
                        description=dialog.description,
                        notes=dialog.notes,
                        source=dialog.source
                    )
                    QMessageBox.information(
                        self, "Success",
                        f"Added exhibit: {exhibit.title}"
                    )
                except Exception as e:
                    QMessageBox.warning(
                        self, "Error",
                        f"Failed to add exhibit: {str(e)}"
                    )

        self._refresh_exhibit_list()

    def _on_manage_exhibit_tags(self):
        """Open dialog to manage exhibit tags."""
        dialog = ManageExhibitTagsDialog(self, self.exhibit_bank)
        dialog.exec()
        # Refresh tag filter
        self.exhibit_tag_filter.clear()
        self.exhibit_tag_filter.addItem("All Tags", "")
        for tag in self.exhibit_bank.list_tags():
            self.exhibit_tag_filter.addItem(tag.name, tag.name)

    def _refresh_exhibit_list(self):
        """Refresh the exhibit list tree with collapsible folders."""
        # Get current filters
        query = self.exhibit_search_edit.text() if hasattr(self, 'exhibit_search_edit') else ""
        tag_filter = self.exhibit_tag_filter.currentData() if hasattr(self, 'exhibit_tag_filter') else None
        type_filter = self.exhibit_type_filter.currentData() if hasattr(self, 'exhibit_type_filter') else None

        # Update breadcrumb navigation
        self._update_folder_breadcrumb()

        # Clear the tree
        self.exhibit_table.clear()

        # If there's a search query, search all exhibits (flat view)
        if query or tag_filter or type_filter:
            tags = [tag_filter] if tag_filter else None
            exhibits = self.exhibit_bank.search(query=query, tags=tags, file_type=type_filter if type_filter else None)
            # Add exhibits as flat items
            for exhibit in exhibits:
                item = self._create_exhibit_tree_item(exhibit)
                self.exhibit_table.addTopLevelItem(item)
        else:
            # Get all folders and exhibits recursively for tree view
            self._populate_tree_recursive(self._current_folder_id, None)

        # Update stats
        stats = self.exhibit_bank.get_stats()
        self.exhibit_stats_label.setText(
            f"{stats['total_exhibits']} exhibits | {stats['total_size_mb']} MB"
        )

    def _populate_tree_recursive(self, parent_folder_id: str, parent_item):
        """Recursively populate tree with folders and their contents."""
        contents = self.exhibit_bank.get_folder_contents(parent_folder_id)
        folders = contents['folders']
        exhibits = contents['exhibits']

        # Add folders first (as collapsible items)
        for folder in folders:
            folder_item = QTreeWidgetItem()
            folder_item.setText(0, folder.name)
            folder_item.setText(1, "Folder")
            folder_item.setText(2, "")
            folder_item.setText(3, folder.date_created[:10] if folder.date_created else "")
            folder_item.setText(4, "")
            folder_item.setData(0, Qt.ItemDataRole.UserRole, folder.id)
            folder_item.setData(0, Qt.ItemDataRole.UserRole + 1, "folder")
            folder_item.setForeground(0, QColor("#f39c12"))
            folder_item.setForeground(1, QColor("#f39c12"))
            font = folder_item.font(0)
            font.setBold(True)
            folder_item.setFont(0, font)

            if parent_item:
                parent_item.addChild(folder_item)
            else:
                self.exhibit_table.addTopLevelItem(folder_item)

            # Recursively add children
            self._populate_tree_recursive(folder.id, folder_item)

            # Expand folder by default
            folder_item.setExpanded(True)

        # Add exhibits
        for exhibit in exhibits:
            exhibit_item = self._create_exhibit_tree_item(exhibit)
            if parent_item:
                parent_item.addChild(exhibit_item)
            else:
                self.exhibit_table.addTopLevelItem(exhibit_item)

    def _create_exhibit_tree_item(self, exhibit) -> QTreeWidgetItem:
        """Create a tree item for an exhibit."""
        item = QTreeWidgetItem()
        item.setText(0, exhibit.title)
        item.setText(1, exhibit.file_type)
        tags_str = ", ".join(exhibit.tags) if exhibit.tags else ""
        item.setText(2, tags_str)
        date_str = exhibit.date_added[:10] if exhibit.date_added else ""
        item.setText(3, date_str)
        size_kb = exhibit.file_size / 1024
        if size_kb > 1024:
            size_str = f"{size_kb/1024:.1f} MB"
        else:
            size_str = f"{size_kb:.1f} KB"
        item.setText(4, size_str)
        item.setData(0, Qt.ItemDataRole.UserRole, exhibit.id)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, "exhibit")
        return item

    def _update_folder_breadcrumb(self):
        """Update the folder breadcrumb navigation."""
        if not self._current_folder_id:
            self.folder_breadcrumb.setText("Root")
            self.folder_up_btn.setEnabled(False)
        else:
            path = self.exhibit_bank.get_folder_path(self._current_folder_id)
            path_names = ["Root"] + [f.name for f in path]
            self.folder_breadcrumb.setText(" > ".join(path_names))
            self.folder_up_btn.setEnabled(True)

    def _on_exhibit_search_changed(self, text):
        """Handle search text change."""
        self._refresh_exhibit_list()

    def _on_exhibit_filter_changed(self, index):
        """Handle filter change."""
        self._refresh_exhibit_list()

    def _on_create_folder(self):
        """Create a new folder in the current directory."""
        name, ok = QInputDialog.getText(
            self, "Create Folder", "Folder name:",
            QLineEdit.EchoMode.Normal, ""
        )
        if ok and name.strip():
            self.exhibit_bank.create_folder(
                name=name.strip(),
                parent_id=self._current_folder_id
            )
            self._refresh_exhibit_list()

    def _on_folder_up(self):
        """Navigate to parent folder."""
        if self._current_folder_id:
            folder = self.exhibit_bank.get_folder(self._current_folder_id)
            if folder:
                self._current_folder_id = folder.parent_id
            else:
                self._current_folder_id = ""
            self._refresh_exhibit_list()

    def _on_exhibit_double_clicked(self, item, column):
        """Handle double-click on tree item."""
        if not item:
            return

        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
        item_id = item.data(0, Qt.ItemDataRole.UserRole)

        if item_type == "folder":
            # Toggle folder expansion instead of navigating
            item.setExpanded(not item.isExpanded())
        else:
            # Open exhibit
            self._on_open_exhibit()

    def eventFilter(self, obj, event):
        """Handle drag and drop events for the exhibit table."""
        from PyQt6.QtCore import QEvent, QMimeData, QUrl
        from PyQt6.QtGui import QDragEnterEvent, QDropEvent

        # Only handle events for exhibit table viewport
        if hasattr(self, 'exhibit_table') and obj == self.exhibit_table.viewport():
            if event.type() == QEvent.Type.DragEnter:
                mime_data = event.mimeData()
                if mime_data.hasUrls():
                    # Check if any URLs are files
                    for url in mime_data.urls():
                        if url.isLocalFile():
                            event.acceptProposedAction()
                            return True
                # Check for internal drag (exhibit/folder)
                if mime_data.hasFormat("application/x-exhibit-id"):
                    event.acceptProposedAction()
                    return True

            elif event.type() == QEvent.Type.DragMove:
                mime_data = event.mimeData()
                if mime_data.hasUrls() or mime_data.hasFormat("application/x-exhibit-id"):
                    event.acceptProposedAction()
                    return True

            elif event.type() == QEvent.Type.Drop:
                mime_data = event.mimeData()

                # Handle file drops from filesystem
                if mime_data.hasUrls():
                    file_paths = []
                    for url in mime_data.urls():
                        if url.isLocalFile():
                            file_paths.append(url.toLocalFile())

                    if file_paths:
                        self._handle_file_drop(file_paths, event.position().toPoint())
                        event.acceptProposedAction()
                        return True

                # Handle internal exhibit/folder drag
                elif mime_data.hasFormat("application/x-exhibit-id"):
                    exhibit_id = mime_data.data("application/x-exhibit-id").data().decode()
                    target_folder_id = self._get_drop_target_folder(event.position().toPoint())
                    if target_folder_id is not None:
                        self.exhibit_bank.move_exhibit_to_folder(exhibit_id, target_folder_id)
                        self._refresh_exhibit_list()
                        event.acceptProposedAction()
                        return True

        return super().eventFilter(obj, event)

    def _handle_file_drop(self, file_paths: list, drop_pos):
        """Handle files dropped onto the exhibit table - adds directly without dialog."""
        # Determine target folder from drop position
        target_folder_id = self._get_drop_target_folder(drop_pos)
        if target_folder_id is None:
            target_folder_id = self._current_folder_id

        added_count = 0
        for file_path in file_paths:
            # Check if it's a valid file
            path = Path(file_path)
            if not path.is_file():
                continue

            # Add exhibit directly using filename as title
            try:
                # Use filename without extension as title
                title = path.stem
                self.exhibit_bank.add_exhibit(
                    file_path=file_path,
                    title=title,
                    tags=[],
                    folder_id=target_folder_id,
                    description="",
                    notes="",
                    source=""
                )
                added_count += 1
            except Exception as e:
                print(f"Failed to add exhibit {path.name}: {e}")

        if added_count > 0:
            self._refresh_exhibit_list()

    def _get_drop_target_folder(self, pos) -> str:
        """Get the folder ID at the drop position, or current folder."""
        # Get item at drop position (QTreeWidget)
        item = self.exhibit_table.itemAt(pos)
        if item:
            item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if item_type == "folder":
                # Dropping onto a folder
                return item.data(0, Qt.ItemDataRole.UserRole)
            # If dropping onto an exhibit, get its parent folder
            parent = item.parent()
            if parent:
                return parent.data(0, Qt.ItemDataRole.UserRole)

        # Not dropping on a folder, use current folder
        return self._current_folder_id

    def _on_exhibit_selected(self):
        """Handle exhibit selection."""
        current_item = self.exhibit_table.currentItem()
        if not current_item:
            return

        # Get the tree item (column 0 contains the data)
        tree_item = current_item
        if current_item.treeWidget().currentColumn() != 0:
            # Get parent item for column 0 data
            tree_item = self.exhibit_table.currentItem()

        item_type = tree_item.data(0, Qt.ItemDataRole.UserRole + 1)
        item_id = tree_item.data(0, Qt.ItemDataRole.UserRole)

        # If folder is selected, show folder info instead of exhibit
        if item_type == "folder":
            folder = self.exhibit_bank.get_folder(item_id)
            if folder:
                self.exhibit_detail_title.setText(folder.name)
                self.exhibit_detail_info.setText("Type: Folder")
                self.exhibit_detail_tags.setText("")
                self.exhibit_detail_desc.setText("Double-click to open folder")
                self.exhibit_detail_notes.setText("")
                self.exhibit_thumbnail.setText("[FOLDER]")
                self._current_exhibit_id = None
            return

        exhibit = self.exhibit_bank.get_exhibit(item_id)

        if not exhibit:
            return

        # Update detail view
        self.exhibit_detail_title.setText(exhibit.title)

        info_parts = [f"Type: {exhibit.file_type}"]
        if exhibit.page_count:
            info_parts.append(f"Pages: {exhibit.page_count}")
        info_parts.append(f"Original: {exhibit.original_filename}")
        if exhibit.source:
            info_parts.append(f"Source: {exhibit.source}")
        self.exhibit_detail_info.setText(" | ".join(info_parts))

        if exhibit.tags:
            tags_html = " ".join([f'<span style="background: #e0e0e0; padding: 2px 8px; border-radius: 10px; margin-right: 5px;">{t}</span>' for t in exhibit.tags])
            self.exhibit_detail_tags.setText(tags_html)
        else:
            self.exhibit_detail_tags.setText("No tags")

        self.exhibit_detail_desc.setText(exhibit.description or "No description")
        self.exhibit_detail_notes.setText(exhibit.notes or "No notes")

        # Load thumbnail
        thumb_path = self.exhibit_bank.get_thumbnail_path(item_id)
        if thumb_path and thumb_path.exists():
            pixmap = QPixmap(str(thumb_path))
            scaled = pixmap.scaled(200, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.exhibit_thumbnail.setPixmap(scaled)
        else:
            self.exhibit_thumbnail.setText(f"[{exhibit.file_type.upper()}]")

        # Store current exhibit ID
        self._current_exhibit_id = item_id

    def _on_exhibit_context_menu(self, pos):
        """Show context menu for exhibit."""
        item = self.exhibit_table.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)

        open_action = menu.addAction("Open")
        open_action.triggered.connect(self._on_open_exhibit)

        edit_action = menu.addAction("Edit Metadata")
        edit_action.triggered.connect(self._on_edit_exhibit)

        menu.addSeparator()

        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(self._on_delete_exhibit)

        menu.exec(self.exhibit_table.mapToGlobal(pos))

    def _on_open_exhibit(self):
        """Open the selected exhibit."""
        if not hasattr(self, '_current_exhibit_id'):
            return

        file_path = self.exhibit_bank.get_file_path(self._current_exhibit_id)
        if file_path and file_path.exists():
            subprocess.run(['open', str(file_path)])

    def _on_edit_exhibit(self):
        """Edit the selected exhibit metadata."""
        if not hasattr(self, '_current_exhibit_id'):
            return

        exhibit = self.exhibit_bank.get_exhibit(self._current_exhibit_id)
        if not exhibit:
            return

        dialog = EditExhibitDialog(self, exhibit, self.exhibit_bank.list_tags())
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.exhibit_bank.update_exhibit(
                self._current_exhibit_id,
                title=dialog.title,
                description=dialog.description,
                tags=dialog.tags,
                notes=dialog.notes,
                source=dialog.source
            )
            self._refresh_exhibit_list()
            self._on_exhibit_selected()

    def _on_delete_exhibit(self):
        """Delete the selected exhibit."""
        if not hasattr(self, '_current_exhibit_id'):
            return

        exhibit = self.exhibit_bank.get_exhibit(self._current_exhibit_id)
        if not exhibit:
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete exhibit '{exhibit.title}'?\n\nThis will remove the file from the exhibit bank.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.exhibit_bank.delete_exhibit(self._current_exhibit_id)
            self._current_exhibit_id = None
            self._refresh_exhibit_list()
            # Clear detail view
            self.exhibit_detail_title.setText("")
            self.exhibit_detail_info.setText("")
            self.exhibit_detail_tags.setText("")
            self.exhibit_detail_desc.setText("")
            self.exhibit_detail_notes.setText("")
            self.exhibit_thumbnail.clear()

    def _on_open_exhibit_file(self):
        """Open the selected exhibit file in the default application."""
        import subprocess
        import platform

        if not hasattr(self, '_current_exhibit_id') or not self._current_exhibit_id:
            QMessageBox.information(self, "No Selection", "Please select an exhibit first.")
            return

        exhibit = self.exhibit_bank.get_exhibit(self._current_exhibit_id)
        if not exhibit:
            return

        # Get the full path to the stored file
        file_path = self.exhibit_bank.storage_dir / "files" / exhibit.stored_filename
        if not file_path.exists():
            QMessageBox.warning(self, "File Not Found", f"File not found: {file_path}")
            return

        # Open with default application
        try:
            if platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', str(file_path)])
            elif platform.system() == 'Windows':
                subprocess.run(['start', '', str(file_path)], shell=True)
            else:  # Linux
                subprocess.run(['xdg-open', str(file_path)])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open file: {e}")

    def _on_generate_exhibit_tags(self):
        """Generate exhibit tags for civil rules format (Exhibit A, B, C... or 1, 2, 3...)."""
        # Get all exhibits in current folder
        contents = self.exhibit_bank.get_folder_contents(self._current_folder_id)
        exhibits = contents.get('exhibits', [])

        if not exhibits:
            QMessageBox.information(self, "No Exhibits", "No exhibits in current folder to tag.")
            return

        # Ask user for format preference
        dialog = QDialog(self)
        dialog.setWindowTitle("Generate Exhibit Tags")
        dialog.setMinimumWidth(300)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("Choose exhibit numbering format:"))

        # Radio buttons for format
        letter_radio = QRadioButton("Letters (Exhibit A, B, C...)")
        letter_radio.setChecked(True)
        layout.addWidget(letter_radio)

        number_radio = QRadioButton("Numbers (Exhibit 1, 2, 3...)")
        layout.addWidget(number_radio)

        plaintiff_radio = QRadioButton("Plaintiff format (PX-1, PX-2...)")
        layout.addWidget(plaintiff_radio)

        defendant_radio = QRadioButton("Defendant format (DX-1, DX-2...)")
        layout.addWidget(defendant_radio)

        # Starting value
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Start from:"))
        start_edit = QLineEdit("1")
        start_edit.setMaximumWidth(50)
        start_layout.addWidget(start_edit)
        start_layout.addStretch()
        layout.addLayout(start_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        apply_btn = QPushButton("Apply Tags")
        apply_btn.setStyleSheet("background: #4a90d9; color: white;")
        apply_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(apply_btn)
        layout.addLayout(btn_layout)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # Generate tags
        try:
            start = int(start_edit.text()) - 1
        except ValueError:
            start = 0

        updated_count = 0
        for i, exhibit in enumerate(exhibits):
            idx = start + i

            if letter_radio.isChecked():
                # A-Z, then AA, AB, etc.
                if idx < 26:
                    tag = chr(65 + idx)  # A=65
                else:
                    first = chr(65 + (idx // 26) - 1)
                    second = chr(65 + (idx % 26))
                    tag = first + second
                new_title = f"Exhibit {tag}"
            elif number_radio.isChecked():
                new_title = f"Exhibit {idx + 1}"
            elif plaintiff_radio.isChecked():
                new_title = f"PX-{idx + 1}"
            else:  # defendant
                new_title = f"DX-{idx + 1}"

            # Update the exhibit title
            self.exhibit_bank.update_exhibit(exhibit.id, title=new_title)
            updated_count += 1

        self._refresh_exhibit_list()
        QMessageBox.information(
            self, "Tags Generated",
            f"Updated {updated_count} exhibit(s) with civil rules format tags."
        )

    # ========== Dockets Tab (Timeline View) ==========

    def _create_dockets_tab(self) -> QWidget:
        """Create the Dockets tab as a timeline with court-style numbering and comments."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        # Header
        header = QLabel("Case Docket Timeline")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        layout.addWidget(header)

        description = QLabel(
            "Court docket timeline with sequential numbering (like ECF). "
            "Add entries and comments to track case progress."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #666; margin-bottom: 5px;")
        layout.addWidget(description)

        # Toolbar
        toolbar_layout = QHBoxLayout()

        # Add Entry button
        add_entry_btn = QPushButton("+ Add Docket Entry")
        add_entry_btn.setStyleSheet("""
            QPushButton {
                background: #4a90d9;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: #357abd;
            }
        """)
        add_entry_btn.clicked.connect(self._on_add_docket_entry)
        toolbar_layout.addWidget(add_entry_btn)

        # Import PACER button
        import_btn = QPushButton("Import PACER")
        import_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        import_btn.clicked.connect(self._on_import_pacer)
        toolbar_layout.addWidget(import_btn)

        # Export Case button
        export_btn = QPushButton("Export Case (TXT/JSON)")
        export_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #218838;
            }
        """)
        export_btn.clicked.connect(self._on_export_case)
        toolbar_layout.addWidget(export_btn)

        toolbar_layout.addStretch()

        # Entry count label
        self.docket_count_label = QLabel("")
        self.docket_count_label.setStyleSheet("color: #666; font-size: 12px;")
        toolbar_layout.addWidget(self.docket_count_label)

        layout.addLayout(toolbar_layout)

        # Filter row
        filter_layout = QHBoxLayout()

        # Case filter
        case_label = QLabel("Case:")
        filter_layout.addWidget(case_label)

        self.docket_case_filter = QComboBox()
        # Load all cases from lawsuit manager
        for lawsuit in self.lawsuit_manager.list_lawsuits():
            self.docket_case_filter.addItem(
                f"Case {lawsuit.case_number} ({lawsuit.short_name})",
                lawsuit.case_number
            )
        self.docket_case_filter.setMinimumWidth(280)
        self.docket_case_filter.currentIndexChanged.connect(self._on_docket_filter_changed)
        filter_layout.addWidget(self.docket_case_filter)

        # Entry type filter
        type_label = QLabel("Type:")
        filter_layout.addWidget(type_label)

        self.docket_type_filter = QComboBox()
        self.docket_type_filter.addItem("All Types", "")
        self.docket_type_filter.addItem("Order", "Order")
        self.docket_type_filter.addItem("Motion", "Motion")
        self.docket_type_filter.addItem("Response/Reply", "Response")
        self.docket_type_filter.addItem("Notice", "Notice")
        self.docket_type_filter.addItem("Complaint", "Complaint")
        self.docket_type_filter.addItem("Summons", "Summons")
        self.docket_type_filter.addItem("Discovery", "Discovery")
        self.docket_type_filter.addItem("Subpoena", "Subpoena")
        self.docket_type_filter.addItem("Judgment", "Judgment")
        self.docket_type_filter.addItem("Other", "Other")
        self.docket_type_filter.setMinimumWidth(140)
        self.docket_type_filter.currentIndexChanged.connect(self._on_docket_filter_changed)
        filter_layout.addWidget(self.docket_type_filter)

        # Search
        search_label = QLabel("Search:")
        filter_layout.addWidget(search_label)

        self.docket_search_edit = QLineEdit()
        self.docket_search_edit.setPlaceholderText("Search docket text...")
        self.docket_search_edit.textChanged.connect(self._on_docket_search_changed)
        self.docket_search_edit.setMaximumWidth(250)
        filter_layout.addWidget(self.docket_search_edit)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Main content area - horizontal layout with list and button panel
        main_layout = QHBoxLayout()

        # Left side - Timeline scroll area (takes full height)
        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setWidgetResizable(True)
        self.timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.timeline_scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #ddd;
                background: #fafafa;
            }
        """)

        self.timeline_widget = QWidget()
        self.timeline_layout = QVBoxLayout(self.timeline_widget)
        self.timeline_layout.setContentsMargins(10, 10, 10, 10)
        self.timeline_layout.setSpacing(0)
        self.timeline_layout.addStretch()

        self.timeline_scroll.setWidget(self.timeline_widget)
        main_layout.addWidget(self.timeline_scroll, stretch=1)

        # Right side - Vertical button panel
        button_panel = QWidget()
        button_panel.setFixedWidth(140)
        button_layout = QVBoxLayout(button_panel)
        button_layout.setContentsMargins(10, 0, 0, 0)
        button_layout.setSpacing(10)

        # Edit Entry button
        edit_btn = QPushButton("Edit Entry")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 12px 16px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        edit_btn.clicked.connect(self._on_edit_docket_entry)
        button_layout.addWidget(edit_btn)

        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 12px 16px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        delete_btn.clicked.connect(self._on_delete_docket_entry)
        button_layout.addWidget(delete_btn)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #ddd;")
        button_layout.addWidget(separator)

        # Comments button
        comments_btn = QPushButton("Comments")
        comments_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                padding: 12px 16px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
        """)
        comments_btn.clicked.connect(self._on_show_docket_comments)
        button_layout.addWidget(comments_btn)

        # View Details button
        details_btn = QPushButton("View Details")
        details_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                padding: 12px 16px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
        """)
        details_btn.clicked.connect(self._on_view_docket_details)
        button_layout.addWidget(details_btn)

        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setStyleSheet("background-color: #ddd;")
        button_layout.addWidget(separator2)

        # Attach Document button
        attach_btn = QPushButton("Attach Doc")
        attach_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 12px 16px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        attach_btn.clicked.connect(self._on_attach_docket_document)
        button_layout.addWidget(attach_btn)

        # Open Attached button
        open_attach_btn = QPushButton("Open Doc")
        open_attach_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px 16px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        open_attach_btn.clicked.connect(self._on_open_docket_document)
        button_layout.addWidget(open_attach_btn)

        button_layout.addStretch()
        main_layout.addWidget(button_panel)

        layout.addLayout(main_layout, stretch=1)

        # Store reference for detail display (hidden initially, shown in dialogs)
        self.docket_detail_number = QLabel("")
        self.docket_detail_date = QLabel("")
        self.docket_detail_text = QLabel("")
        self.docket_detail_filed = QLabel("")
        self.docket_comments_edit = QTextEdit()
        self.docket_detail_frame = QFrame()

        # Initialize docket storage
        self._init_docket_storage()

        # Load initial data
        self._refresh_dockets()

        return tab

    def _init_docket_storage(self):
        """Initialize docket storage with timeline structure."""
        self.docket_storage_path = Path.home() / "Dropbox/Formarter Folder/dockets"
        self.docket_storage_path.mkdir(parents=True, exist_ok=True)
        self.docket_index_path = self.docket_storage_path / "index.json"

        if self.docket_index_path.exists():
            try:
                import json
                with open(self.docket_index_path, 'r') as f:
                    self._docket_data = json.load(f)
                # Ensure new fields exist
                if "next_number" not in self._docket_data:
                    self._docket_data["next_number"] = {}
            except:
                self._docket_data = {"cases": {}, "entries": [], "deadlines": [], "next_number": {}}
        else:
            self._docket_data = {"cases": {}, "entries": [], "deadlines": [], "next_number": {"178": 1}}
            self._save_docket_data()

        self._current_docket_entry_id = None

    def _save_docket_data(self):
        """Save docket data to disk."""
        import json
        with open(self.docket_index_path, 'w') as f:
            json.dump(self._docket_data, f, indent=2, ensure_ascii=False)

    def _get_next_docket_number(self, case_id: str) -> int:
        """Get and increment the next docket number for a case."""
        if case_id not in self._docket_data.get("next_number", {}):
            # Find the highest existing number for this case
            existing = [e.get('docket_number', 0) for e in self._docket_data.get('entries', [])
                        if e.get('case_id') == case_id]
            next_num = max(existing) + 1 if existing else 1
            self._docket_data.setdefault("next_number", {})[case_id] = next_num

        num = self._docket_data["next_number"][case_id]
        self._docket_data["next_number"][case_id] = num + 1
        return num

    def _detect_entry_type(self, text: str) -> str:
        """Auto-detect entry type from docket text."""
        text_lower = text.lower()

        # Check for specific entry types (order matters - more specific first)
        if 'order' in text_lower and ('granting' in text_lower or 'denying' in text_lower or 'dismissing' in text_lower):
            return 'Order'
        if 'order' in text_lower:
            return 'Order'
        if 'motion' in text_lower:
            return 'Motion'
        if 'response' in text_lower or 'reply' in text_lower or 'opposition' in text_lower:
            return 'Response'
        if 'notice' in text_lower:
            return 'Notice'
        if 'complaint' in text_lower:
            return 'Complaint'
        if 'summons' in text_lower:
            return 'Summons'
        if 'discovery' in text_lower or 'interrogatories' in text_lower or 'request for production' in text_lower:
            return 'Discovery'
        if 'subpoena' in text_lower:
            return 'Subpoena'
        if 'judgment' in text_lower or 'verdict' in text_lower:
            return 'Judgment'

        return 'Other'

    def _get_entry_type_color(self, entry_type: str) -> str:
        """Get color for entry type badge."""
        colors = {
            'Order': '#9b59b6',       # Purple
            'Motion': '#3498db',      # Blue
            'Response': '#2ecc71',    # Green
            'Notice': '#f39c12',      # Orange
            'Complaint': '#e74c3c',   # Red
            'Summons': '#1abc9c',     # Teal
            'Discovery': '#34495e',   # Dark gray
            'Subpoena': '#e67e22',    # Dark orange
            'Judgment': '#c0392b',    # Dark red
            'Other': '#95a5a6',       # Gray
        }
        return colors.get(entry_type, '#95a5a6')

    def _calculate_deadlines(self, entry_date: str, entry_type: str, is_gov_party: bool = True) -> list:
        """
        Calculate response/appeal deadlines based on entry type and date.
        Returns list of (action, deadline_date, days_remaining, rule) tuples.

        Federal Rules:
        - FRAP 4: Notice of Appeal = 30 days (60 if gov't party)
        - Rule 59(e): Motion to Alter/Amend = 28 days
        - Rule 60(b): Motion for Relief = 1 year
        - Rule 54(b): Reconsideration = Before final judgment (flexible)
        """
        from datetime import datetime, timedelta

        deadlines = []

        try:
            # Parse the entry date
            if not entry_date:
                return deadlines

            date_obj = datetime.strptime(entry_date, "%Y-%m-%d")
            today = datetime.now()

            if entry_type in ['Order', 'Judgment']:
                # Notice of Appeal deadline (FRAP Rule 4)
                appeal_days = 60 if is_gov_party else 30
                appeal_deadline = date_obj + timedelta(days=appeal_days)
                days_remaining = (appeal_deadline - today).days
                deadlines.append({
                    'action': 'Notice of Appeal',
                    'deadline': appeal_deadline.strftime("%Y-%m-%d"),
                    'days_remaining': days_remaining,
                    'rule': f'FRAP 4 ({appeal_days} days)',
                    'urgent': days_remaining <= 7
                })

                # Motion to Alter/Amend (Rule 59(e))
                alter_deadline = date_obj + timedelta(days=28)
                days_remaining_59 = (alter_deadline - today).days
                deadlines.append({
                    'action': 'Motion to Alter/Amend',
                    'deadline': alter_deadline.strftime("%Y-%m-%d"),
                    'days_remaining': days_remaining_59,
                    'rule': 'FRCP 59(e) (28 days)',
                    'urgent': days_remaining_59 <= 7
                })

                # Motion for Relief (Rule 60(b))
                relief_deadline = date_obj + timedelta(days=365)
                days_remaining_60 = (relief_deadline - today).days
                deadlines.append({
                    'action': 'Motion for Relief',
                    'deadline': relief_deadline.strftime("%Y-%m-%d"),
                    'days_remaining': days_remaining_60,
                    'rule': 'FRCP 60(b) (1 year)',
                    'urgent': False
                })

            elif entry_type == 'Motion':
                # Response to motion typically 14-21 days (varies by local rules)
                response_deadline = date_obj + timedelta(days=21)
                days_remaining = (response_deadline - today).days
                deadlines.append({
                    'action': 'Response to Motion',
                    'deadline': response_deadline.strftime("%Y-%m-%d"),
                    'days_remaining': days_remaining,
                    'rule': 'Local Rules (~21 days)',
                    'urgent': days_remaining <= 7
                })

            elif entry_type == 'Complaint':
                # Answer deadline = 21 days (60 if waiver)
                answer_deadline = date_obj + timedelta(days=21)
                days_remaining = (answer_deadline - today).days
                deadlines.append({
                    'action': 'Answer/Response',
                    'deadline': answer_deadline.strftime("%Y-%m-%d"),
                    'days_remaining': days_remaining,
                    'rule': 'FRCP 12(a)(1) (21 days)',
                    'urgent': days_remaining <= 7
                })

            elif entry_type == 'Discovery':
                # Objections typically 30 days
                objection_deadline = date_obj + timedelta(days=30)
                days_remaining = (objection_deadline - today).days
                deadlines.append({
                    'action': 'Response/Objections',
                    'deadline': objection_deadline.strftime("%Y-%m-%d"),
                    'days_remaining': days_remaining,
                    'rule': 'FRCP 33/34 (30 days)',
                    'urgent': days_remaining <= 7
                })

        except Exception as e:
            print(f"Error calculating deadlines: {e}")

        return deadlines

    def _refresh_dockets(self):
        """Refresh the timeline display."""
        # Clear existing timeline
        while self.timeline_layout.count() > 1:
            item = self.timeline_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get filters
        case_filter = self.docket_case_filter.currentData() if hasattr(self, 'docket_case_filter') else "178"
        type_filter = self.docket_type_filter.currentData() if hasattr(self, 'docket_type_filter') else ""
        search_query = self.docket_search_edit.text().lower() if hasattr(self, 'docket_search_edit') else ""

        # Filter entries
        entries = self._docket_data.get("entries", [])
        if case_filter:
            entries = [e for e in entries if e.get('case_id') == case_filter]

        # Apply type filter (detect type from text if not stored)
        if type_filter:
            filtered_entries = []
            for e in entries:
                entry_type = e.get('entry_type') or self._detect_entry_type(e.get('text', ''))
                if entry_type == type_filter:
                    filtered_entries.append(e)
            entries = filtered_entries

        if search_query:
            entries = [e for e in entries if search_query in e.get('text', '').lower() or
                       search_query in e.get('description', '').lower()]

        # Sort by docket number descending (newest first)
        entries = sorted(entries, key=lambda x: (x.get('date', ''), x.get('docket_number', 0)), reverse=True)

        # Update count
        self.docket_count_label.setText(f"{len(entries)} entries")

        # Create timeline entries
        for i, entry in enumerate(entries):
            entry_widget = self._create_timeline_entry_widget(entry, is_last=(i == len(entries) - 1))
            self.timeline_layout.insertWidget(i, entry_widget)

        # Clear detail view if no selection
        if not entries:
            self._clear_detail_view()

    def _create_timeline_entry_widget(self, entry: dict, is_last: bool = False) -> QWidget:
        """Create a timeline entry widget."""
        widget = QFrame()
        widget.setProperty("entry_id", entry.get('id'))
        widget.setCursor(Qt.CursorShape.PointingHandCursor)
        widget.mousePressEvent = lambda e, eid=entry.get('id'): self._on_timeline_entry_clicked(eid)

        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Left side - Number and timeline connector
        left_widget = QWidget()
        left_widget.setFixedWidth(60)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Docket number circle - green if exhibit attached, blue otherwise
        has_exhibit = bool(entry.get('attached_document'))
        circle_color = "#2ecc71" if has_exhibit else "#4a90d9"  # Green for exhibit, blue otherwise

        number_label = QLabel(str(entry.get('docket_number', '')))
        number_label.setFixedSize(40, 40)
        number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        number_label.setStyleSheet(f"""
            QLabel {{
                background: {circle_color};
                color: white;
                border-radius: 20px;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        left_layout.addWidget(number_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Timeline connector line
        if not is_last:
            line = QFrame()
            line.setFixedWidth(2)
            line.setMinimumHeight(30)
            line.setStyleSheet(f"background: {circle_color};")
            left_layout.addWidget(line, alignment=Qt.AlignmentFlag.AlignHCenter)

        left_layout.addStretch()
        layout.addWidget(left_widget)

        # Right side - Content
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(2)

        # Date
        date_label = QLabel(entry.get('date', ''))
        date_label.setStyleSheet("font-size: 11px; color: #888;")
        content_layout.addWidget(date_label)

        # Text (truncated)
        text = entry.get('text', entry.get('description', ''))
        if len(text) > 100:
            text = text[:100] + "..."
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setStyleSheet("font-size: 12px; color: #333;")
        content_layout.addWidget(text_label)

        # Indicators row
        indicators_layout = QHBoxLayout()
        indicators_layout.setSpacing(8)

        # Entry type badge (auto-detected or stored)
        entry_type = entry.get('entry_type') or self._detect_entry_type(entry.get('text', ''))
        type_color = self._get_entry_type_color(entry_type)
        type_badge = QLabel(entry_type)
        type_badge.setStyleSheet(f"""
            QLabel {{
                font-size: 10px;
                color: white;
                font-weight: bold;
                background: {type_color};
                border-radius: 3px;
                padding: 2px 6px;
            }}
        """)
        indicators_layout.addWidget(type_badge)

        # Show "Signed by" for Orders/Judgments
        signed_by = entry.get('signed_by', '')
        if signed_by and entry_type in ['Order', 'Judgment']:
            signed_label = QLabel(f"Signed by {signed_by}")
            signed_label.setStyleSheet("""
                font-size: 10px;
                color: #8e44ad;
                font-style: italic;
            """)
            indicators_layout.addWidget(signed_label)

        if entry.get('comments'):
            comment_indicator = QLabel("[Comments]")
            comment_indicator.setStyleSheet("font-size: 10px; color: #9C27B0; font-weight: bold;")
            indicators_layout.addWidget(comment_indicator)

        if entry.get('attached_document'):
            doc_path = entry.get('attached_document')
            doc_name = Path(doc_path).name if doc_path else "PDF"
            # Truncate long names
            if len(doc_name) > 30:
                doc_name = doc_name[:27] + "..."

            # Clickable PDF button
            pdf_btn = QPushButton(f"📄 {doc_name}")
            pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            pdf_btn.setStyleSheet("""
                QPushButton {
                    font-size: 10px;
                    color: #FF9800;
                    font-weight: bold;
                    background: transparent;
                    border: 1px solid #FF9800;
                    border-radius: 3px;
                    padding: 2px 5px;
                }
                QPushButton:hover {
                    background: #FFF3E0;
                }
            """)
            pdf_btn.clicked.connect(lambda checked, p=doc_path: self._open_pdf_document(p))
            indicators_layout.addWidget(pdf_btn)

        indicators_layout.addStretch()
        content_layout.addLayout(indicators_layout)

        # Add deadline display for Orders/Judgments/Motions
        entry_date = entry.get('date', '')
        if entry_type in ['Order', 'Judgment', 'Motion', 'Complaint']:
            deadlines = self._calculate_deadlines(entry_date, entry_type, is_gov_party=True)
            # Filter to show only pending deadlines
            active_deadlines = [d for d in deadlines if d['days_remaining'] >= 0]

            if active_deadlines:
                deadlines_layout = QHBoxLayout()
                deadlines_layout.setSpacing(5)

                deadline_icon = QLabel("⏰")
                deadline_icon.setStyleSheet("font-size: 11px;")
                deadlines_layout.addWidget(deadline_icon)

                for dl in active_deadlines[:2]:  # Show max 2 most urgent deadlines
                    days = dl['days_remaining']
                    if days <= 7:
                        color = "#e74c3c"  # Red - urgent
                        text_color = "white"
                    elif days <= 21:
                        color = "#f39c12"  # Orange - soon
                        text_color = "white"
                    else:
                        color = "#27ae60"  # Green - future
                        text_color = "white"

                    deadline_text = f"{dl['action']}: {days}d"
                    deadline_badge = QLabel(deadline_text)
                    deadline_badge.setToolTip(f"{dl['rule']} - Due: {dl['deadline']}")
                    deadline_badge.setStyleSheet(f"""
                        QLabel {{
                            font-size: 9px;
                            color: {text_color};
                            font-weight: bold;
                            background: {color};
                            border-radius: 3px;
                            padding: 2px 5px;
                        }}
                    """)
                    deadlines_layout.addWidget(deadline_badge)

                deadlines_layout.addStretch()
                content_layout.addLayout(deadlines_layout)

        layout.addWidget(content_widget, stretch=1)

        # Style the widget - light green background if exhibit attached
        if has_exhibit:
            widget.setStyleSheet("""
                QFrame {
                    background: #e8f8e8;
                    border: 1px solid #2ecc71;
                    border-radius: 5px;
                    margin-bottom: 5px;
                }
                QFrame:hover {
                    background: #d4f0d4;
                    border-color: #27ae60;
                }
            """)
        else:
            widget.setStyleSheet("""
                QFrame {
                    background: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 5px;
                    margin-bottom: 5px;
                }
                QFrame:hover {
                    background: #f5f5f5;
                    border-color: #4a90d9;
                }
            """)

        return widget

    def _open_pdf_document(self, pdf_path: str):
        """Open a PDF document in the default viewer."""
        if pdf_path and Path(pdf_path).exists():
            subprocess.run(['open', pdf_path])
        else:
            QMessageBox.warning(self, "File Not Found", f"PDF file not found:\n{pdf_path}")

    def _on_timeline_entry_clicked(self, entry_id: str):
        """Handle click on timeline entry - shows full text dialog."""
        self._current_docket_entry_id = entry_id

        # Find the entry
        entry = None
        for e in self._docket_data.get('entries', []):
            if e.get('id') == entry_id:
                entry = e
                break

        if not entry:
            return

        # Build full text content
        docket_num = entry.get('docket_number', '')
        date = entry.get('date', '')
        docket_text = entry.get('text', entry.get('description', ''))
        comments = entry.get('comments', '')
        doc_path = entry.get('attached_document', '')

        # Try to read extracted text
        extracted_text = ""
        case_number = entry.get('case_id', '178')
        txt_path = Path.home() / f"Dropbox/Formarter Folder/lawsuits/case_{case_number}/docket_{docket_num:03d}.txt"
        if txt_path.exists():
            try:
                extracted_text = txt_path.read_text(encoding='utf-8')
            except:
                pass

        # If no pre-extracted text, try to extract from PDF
        if not extracted_text and doc_path and Path(doc_path).exists():
            extracted_text = self.lawsuit_manager.extract_pdf_text(doc_path)

        # Calculate deadlines for this entry
        entry_type = entry.get('entry_type') or self._detect_entry_type(docket_text)
        deadlines = self._calculate_deadlines(date, entry_type, is_gov_party=True)

        # Show dialog with full content
        dialog = DocketEntryDetailDialog(
            self,
            docket_num=docket_num,
            date=date,
            docket_text=docket_text,
            extracted_text=extracted_text,
            comments=comments,
            doc_path=doc_path,
            entry_type=entry_type,
            deadlines=deadlines
        )
        dialog.exec()

    def _clear_detail_view(self):
        """Clear the selection."""
        self._current_docket_entry_id = None

    def _on_docket_comment_changed(self):
        """Save comment when changed (legacy - now uses dialog)."""
        if not self._current_docket_entry_id:
            return

        # No longer needed - comments are saved via dialog
        pass

    def _on_docket_comment_changed_legacy(self):
        """Legacy: Save comment when changed."""
        if not self._current_docket_entry_id:
            return

        comment_text = self.docket_comments_edit.toPlainText()

        # Update entry
        for entry in self._docket_data.get('entries', []):
            if entry.get('id') == self._current_docket_entry_id:
                entry['comments'] = comment_text
                break

        self._save_docket_data()

    def _on_add_docket_entry(self):
        """Add a new docket entry with auto-numbering."""
        case_id = self.docket_case_filter.currentData() if hasattr(self, 'docket_case_filter') else "178"

        # Get lawsuit info for judge/magistrate
        lawsuit_info = {}
        lawsuit = self.lawsuit_manager.get_lawsuit_by_number(case_id)
        if lawsuit:
            lawsuit_info = {
                'judge': lawsuit.judge,
                'magistrate': lawsuit.magistrate
            }

        dialog = AddDocketEntryDialog(self, case_id, self._docket_data, lawsuit_info)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            import uuid

            # Get next sequential number
            docket_number = self._get_next_docket_number(case_id)

            entry = {
                'id': str(uuid.uuid4()),
                'case_id': case_id,
                'docket_number': docket_number,
                'date': dialog.date,
                'text': dialog.text,
                'description': dialog.text,  # Keep for compatibility
                'filed_by': dialog.filed_by,
                'entry_type': dialog.entry_type,
                'signed_by': dialog.signed_by,
                'comments': ''
            }
            self._docket_data['entries'].append(entry)
            self._save_docket_data()
            self._refresh_dockets()

            # Select the new entry
            self._on_timeline_entry_clicked(entry['id'])

    def _on_import_pacer(self):
        """Import docket from PACER HTML file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PACER Docket File",
            str(Path.home()),
            "HTML Files (*.html *.htm);;All Files (*)"
        )

        if file_path:
            QMessageBox.information(
                self, "Import PACER",
                "PACER import functionality coming soon.\n\n"
                "For now, you can manually add docket entries."
            )

    def _on_export_case(self):
        """Export the current case to TXT and JSON files."""
        # Get current case number from filter
        case_number = self.docket_case_filter.currentData()
        if not case_number:
            case_number = "178"  # Default

        try:
            # Extract texts from attached PDFs
            texts = self.lawsuit_manager.extract_docket_texts(case_number)

            # Generate full docket TXT
            txt_path = self.lawsuit_manager.generate_full_docket_txt(case_number)

            # Export case JSON
            json_path = self.lawsuit_manager.export_case_json(case_number)

            # Get summary
            summary = self.lawsuit_manager.get_case_summary(case_number)

            QMessageBox.information(
                self,
                "Case Exported",
                f"Case {case_number} exported successfully!\n\n"
                f"Files saved to:\n"
                f"  ~/Dropbox/Formarter Folder/lawsuits/case_{case_number}/\n\n"
                f"Summary:\n"
                f"  - {summary['total_docket_entries']} docket entries\n"
                f"  - {summary['entries_with_documents']} entries with documents\n"
                f"  - {len(texts)} PDFs converted to text\n"
                f"  - {summary['total_exhibits']} exhibits\n\n"
                f"Generated files:\n"
                f"  - full_docket.txt\n"
                f"  - case_data.json\n"
                f"  - docket_XXX.txt (for each attached PDF)"
            )

            # Open the folder in Finder
            subprocess.run(['open', str(Path(txt_path).parent)])

        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export case: {str(e)}"
            )

    def _on_docket_filter_changed(self, index):
        """Handle docket filter change."""
        self._clear_detail_view()
        self._refresh_dockets()

    def _on_docket_search_changed(self, text):
        """Handle docket search change."""
        self._refresh_dockets()

    def _on_edit_docket_entry(self):
        """Edit the selected docket entry."""
        if not self._current_docket_entry_id:
            QMessageBox.information(self, "No Selection", "Please select a docket entry first.")
            return

        # Find entry
        entry = None
        for e in self._docket_data.get('entries', []):
            if e.get('id') == self._current_docket_entry_id:
                entry = e
                break

        if not entry:
            return

        dialog = EditDocketEntryDialog(self, entry)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            entry['date'] = dialog.date
            entry['text'] = dialog.text
            entry['description'] = dialog.text
            entry['filed_by'] = dialog.filed_by
            entry['comments'] = dialog.comments
            self._save_docket_data()
            self._refresh_dockets()
            self._on_timeline_entry_clicked(self._current_docket_entry_id)

    def _on_delete_docket_entry(self):
        """Delete the selected docket entry."""
        if not self._current_docket_entry_id:
            QMessageBox.information(self, "No Selection", "Please select a docket entry first.")
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Delete this docket entry?\n\nNote: This won't renumber other entries.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._docket_data['entries'] = [
                e for e in self._docket_data.get('entries', [])
                if e.get('id') != self._current_docket_entry_id
            ]
            self._save_docket_data()
            self._clear_detail_view()
            self._refresh_dockets()

    def _on_show_docket_comments(self):
        """Show/edit comments for the selected docket entry."""
        if not self._current_docket_entry_id:
            QMessageBox.information(self, "No Selection", "Please select a docket entry first.")
            return

        # Find entry
        entry = None
        for e in self._docket_data.get('entries', []):
            if e.get('id') == self._current_docket_entry_id:
                entry = e
                break

        if not entry:
            return

        # Create comments dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Comments - Docket #{entry.get('docket_number', 0)}")
        dialog.setMinimumSize(500, 350)

        layout = QVBoxLayout(dialog)

        # Entry info
        info_label = QLabel(f"<b>#{entry.get('docket_number', 0)}</b> - {entry.get('date', '')}")
        info_label.setStyleSheet("color: #4a90d9; font-size: 14px;")
        layout.addWidget(info_label)

        text_preview = QLabel(entry.get('text', '')[:200] + "..." if len(entry.get('text', '')) > 200 else entry.get('text', ''))
        text_preview.setWordWrap(True)
        text_preview.setStyleSheet("color: #666; font-size: 11px; margin-bottom: 10px;")
        layout.addWidget(text_preview)

        # Comments edit
        comments_edit = QTextEdit()
        comments_edit.setPlaceholderText("Add your notes and comments about this docket entry...")
        comments_edit.setText(entry.get('comments', ''))
        comments_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        layout.addWidget(comments_edit)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("Save Comments")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        save_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            entry['comments'] = comments_edit.toPlainText()
            self._save_docket_data()

    def _on_view_docket_details(self):
        """View full details for the selected docket entry."""
        if not self._current_docket_entry_id:
            QMessageBox.information(self, "No Selection", "Please select a docket entry first.")
            return

        # Find entry
        entry = None
        for e in self._docket_data.get('entries', []):
            if e.get('id') == self._current_docket_entry_id:
                entry = e
                break

        if not entry:
            return

        # Create details dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Docket Entry #{entry.get('docket_number', 0)} Details")
        dialog.setMinimumSize(600, 450)

        layout = QVBoxLayout(dialog)

        # Docket number
        num_label = QLabel(f"#{entry.get('docket_number', 0)}")
        num_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #4a90d9;")
        layout.addWidget(num_label)

        # Date
        date_label = QLabel(f"Date: {entry.get('date', 'N/A')}")
        date_label.setStyleSheet("font-size: 14px; color: #666;")
        layout.addWidget(date_label)

        # Filed by
        filed_label = QLabel(f"Filed by: {entry.get('filed_by', 'N/A')}")
        filed_label.setStyleSheet("font-size: 12px; color: #888; margin-bottom: 15px;")
        layout.addWidget(filed_label)

        # Full text (scrollable)
        text_label = QLabel("Docket Text:")
        text_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(text_label)

        text_scroll = QScrollArea()
        text_scroll.setWidgetResizable(True)
        text_scroll.setStyleSheet("border: 1px solid #ddd; background: white;")

        text_widget = QLabel(entry.get('text', entry.get('description', '')))
        text_widget.setWordWrap(True)
        text_widget.setStyleSheet("padding: 10px; font-size: 12px;")
        text_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        text_scroll.setWidget(text_widget)
        layout.addWidget(text_scroll)

        # Comments (if any)
        if entry.get('comments'):
            comments_label = QLabel("Comments/Notes:")
            comments_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
            layout.addWidget(comments_label)

            comments_text = QLabel(entry.get('comments'))
            comments_text.setWordWrap(True)
            comments_text.setStyleSheet("color: #9C27B0; font-style: italic; padding: 5px;")
            layout.addWidget(comments_text)

        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        dialog.exec()

    def _on_attach_docket_document(self):
        """Attach a document (PDF, etc.) to the selected docket entry."""
        if not self._current_docket_entry_id:
            QMessageBox.information(self, "No Selection", "Please select a docket entry first.")
            return

        # Find entry
        entry = None
        for e in self._docket_data.get('entries', []):
            if e.get('id') == self._current_docket_entry_id:
                entry = e
                break

        if not entry:
            return

        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Attach Document to Docket #{entry.get('docket_number', 0)}",
            str(Path.home() / "Downloads"),
            "Documents (*.pdf *.doc *.docx *.txt);;All Files (*)"
        )

        if file_path:
            # Store path in entry
            entry['attached_document'] = file_path
            entry['attached_filename'] = Path(file_path).name
            self._save_docket_data()
            self._refresh_dockets()
            QMessageBox.information(
                self, "Document Attached",
                f"Attached: {Path(file_path).name}\nto Docket #{entry.get('docket_number', 0)}"
            )

    def _on_open_docket_document(self):
        """Open the attached document for the selected docket entry."""
        if not self._current_docket_entry_id:
            QMessageBox.information(self, "No Selection", "Please select a docket entry first.")
            return

        # Find entry
        entry = None
        for e in self._docket_data.get('entries', []):
            if e.get('id') == self._current_docket_entry_id:
                entry = e
                break

        if not entry:
            return

        doc_path = entry.get('attached_document', '')
        if not doc_path:
            QMessageBox.information(
                self, "No Document",
                f"No document attached to Docket #{entry.get('docket_number', 0)}.\n\nUse 'Attach Doc' to add one."
            )
            return

        if not Path(doc_path).exists():
            QMessageBox.warning(
                self, "File Not Found",
                f"The attached file no longer exists:\n{doc_path}"
            )
            return

        # Open with default application
        import subprocess
        subprocess.run(['open', doc_path])

    def _create_case_content_widget(self, case: dict) -> QWidget:
        """Create the content widget for a single case."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main horizontal splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - filing list + search
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setSpacing(5)

        # Search box
        search_box = QLineEdit()
        search_box.setPlaceholderText("Search filings...")
        search_box.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 12px;
            }
        """)
        search_box.textChanged.connect(lambda text, cid=case['id']: self._on_search_text_changed(cid, text))
        left_layout.addWidget(search_box)
        widget.search_box = search_box

        list_label = QLabel("Filed Documents")
        list_label.setStyleSheet("font-weight: bold; font-size: 13px; padding: 5px;")
        left_layout.addWidget(list_label)

        filings_list = QListWidget()
        filings_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 12px;
            }
            QListWidget::item {
                padding: 6px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #1976D2;
                color: white;
            }
        """)
        filings_list.itemClicked.connect(lambda item, cid=case['id']: self._on_case_filing_selected(cid, item))
        left_layout.addWidget(filings_list)
        widget.filings_list = filings_list

        # Buttons row
        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(lambda _, cid=case['id']: self._refresh_case_filings(cid))
        btn_row.addWidget(refresh_btn)
        open_pdf_btn = QPushButton("Open PDF")
        open_pdf_btn.clicked.connect(lambda _, cid=case['id']: self._open_case_filing_pdf(cid))
        btn_row.addWidget(open_pdf_btn)
        left_layout.addLayout(btn_row)

        main_splitter.addWidget(left_panel)

        # Right panel - sub-tabs
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        subtabs = QTabWidget()
        subtabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ddd; background: white; }
            QTabBar::tab { padding: 8px 12px; margin-right: 2px; background: #f0f0f0;
                border: 1px solid #ddd; border-bottom: none; border-radius: 4px 4px 0 0; }
            QTabBar::tab:selected { background: white; font-weight: bold; }
        """)
        widget.subtabs = subtabs

        # Sub-tab 1: Case Info
        info_tab = QWidget()
        info_layout = QVBoxLayout(info_tab)
        info_layout.setContentsMargins(10, 10, 10, 10)
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setStyleSheet("QTextEdit { border: none; font-family: 'Helvetica Neue', Arial; font-size: 13px; }")
        info_layout.addWidget(info_text)
        subtabs.addTab(info_tab, "Case Info")
        widget.info_text = info_text

        # Sub-tab 2: Paragraphs (NEW)
        para_tab = QWidget()
        para_layout = QVBoxLayout(para_tab)
        para_layout.setContentsMargins(0, 0, 0, 0)
        para_splitter = QSplitter(Qt.Orientation.Horizontal)
        para_list = QListWidget()
        para_list.setStyleSheet("""
            QListWidget { border: none; border-right: 1px solid #ddd; font-size: 12px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #eee; }
            QListWidget::item:selected { background-color: #1976D2; color: white; }
        """)
        para_splitter.addWidget(para_list)
        widget.para_list = para_list

        para_detail_widget = QWidget()
        para_detail_layout = QVBoxLayout(para_detail_widget)
        para_detail_layout.setContentsMargins(10, 10, 10, 10)
        para_detail = QTextEdit()
        para_detail.setReadOnly(True)
        para_detail.setStyleSheet("QTextEdit { border: none; font-family: 'Times New Roman'; font-size: 13px; }")
        para_detail_layout.addWidget(para_detail)
        copy_cite_btn = QPushButton("Copy with Citation")
        copy_cite_btn.setStyleSheet("QPushButton { background: #4CAF50; color: white; padding: 10px; border-radius: 4px; font-weight: bold; }")
        copy_cite_btn.clicked.connect(lambda _, cid=case['id']: self._copy_paragraph_citation(cid))
        para_detail_layout.addWidget(copy_cite_btn)
        para_splitter.addWidget(para_detail_widget)
        para_splitter.setSizes([300, 700])
        widget.para_detail = para_detail

        para_list.itemClicked.connect(lambda item, cid=case['id']: self._on_paragraph_selected(cid, item))
        para_layout.addWidget(para_splitter)
        subtabs.addTab(para_tab, "Paragraphs")

        # Sub-tab 3: Timeline (NEW)
        timeline_tab = QWidget()
        timeline_layout = QVBoxLayout(timeline_tab)
        timeline_layout.setContentsMargins(10, 10, 10, 10)

        # Add event form
        add_event_group = QGroupBox("Add Timeline Event")
        add_event_layout = QHBoxLayout(add_event_group)
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        date_edit.setDate(QDate.currentDate())
        date_edit.setStyleSheet("padding: 5px;")
        add_event_layout.addWidget(QLabel("Date:"))
        add_event_layout.addWidget(date_edit)
        event_input = QLineEdit()
        event_input.setPlaceholderText("Event description...")
        add_event_layout.addWidget(event_input)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(lambda _, cid=case['id']: self._add_timeline_event(cid))
        add_event_layout.addWidget(add_btn)
        timeline_layout.addWidget(add_event_group)
        widget.timeline_date = date_edit
        widget.timeline_event = event_input

        # Timeline list
        timeline_list = QListWidget()
        timeline_list.setStyleSheet("""
            QListWidget { border: 1px solid #ddd; border-radius: 4px; font-size: 12px; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #eee; }
        """)
        timeline_layout.addWidget(timeline_list)
        widget.timeline_list = timeline_list
        subtabs.addTab(timeline_tab, "Timeline")

        # Sub-tab 4: Causes of Action
        causes_tab = QWidget()
        causes_layout = QVBoxLayout(causes_tab)
        causes_layout.setContentsMargins(0, 0, 0, 0)
        causes_splitter = QSplitter(Qt.Orientation.Horizontal)
        causes_list = QListWidget()
        causes_list.setStyleSheet("""
            QListWidget { border: none; border-right: 1px solid #ddd; font-size: 12px; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #eee; }
            QListWidget::item:selected { background-color: #1976D2; color: white; }
        """)
        causes_splitter.addWidget(causes_list)
        cause_detail = QTextEdit()
        cause_detail.setReadOnly(True)
        cause_detail.setStyleSheet("QTextEdit { border: none; font-family: 'Times New Roman'; font-size: 13px; padding: 10px; }")
        causes_splitter.addWidget(cause_detail)
        causes_splitter.setSizes([300, 700])
        causes_list.itemClicked.connect(lambda item: cause_detail.setPlainText(item.data(Qt.ItemDataRole.UserRole) or ''))
        causes_layout.addWidget(causes_splitter)
        subtabs.addTab(causes_tab, "Causes")
        widget.causes_list = causes_list
        widget.cause_detail = cause_detail

        # Sub-tab 5: Full Text
        fulltext_tab = QWidget()
        fulltext_layout = QVBoxLayout(fulltext_tab)
        fulltext_layout.setContentsMargins(0, 0, 0, 0)
        filing_content = QTextEdit()
        filing_content.setReadOnly(True)
        filing_content.setStyleSheet("QTextEdit { border: none; font-family: 'Times New Roman'; font-size: 12px; padding: 15px; }")
        filing_content.setPlaceholderText("Select a filing to view content...")
        fulltext_layout.addWidget(filing_content)
        subtabs.addTab(fulltext_tab, "Full Text")
        widget.filing_content = filing_content

        right_layout.addWidget(subtabs)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([200, 800])
        layout.addWidget(main_splitter)

        # Store parsed data
        widget._paragraphs = []
        widget._causes = []
        widget._current_para_idx = 0

        return widget

    def _get_case_filings_folder(self, case_id: str) -> Path:
        """Get filings folder for a specific case."""
        from pathlib import Path
        return Path.home() / "Dropbox" / "Formarter Folder" / "executed_filings"

    def _refresh_case_filings(self, case_id: str):
        """Refresh filings list for a specific case."""
        widget = self._case_widgets.get(case_id)
        if not widget:
            return

        widget.filings_list.clear()
        folder = self._get_case_filings_folder(case_id)
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
            return

        # Collect all filings (PDFs and TXTs) including from subfolders
        filings = []

        # Get PDFs directly in folder
        for pdf_path in folder.glob(f"{case_id}*.pdf"):
            filings.append(('pdf', pdf_path))

        # Get PDFs from subfolders
        for pdf_path in folder.glob(f"**/{case_id}*.pdf"):
            if pdf_path.parent != folder:  # Avoid duplicates
                filings.append(('pdf', pdf_path))

        # Get TXT files directly in folder (without PDF counterpart)
        for txt_path in folder.glob(f"{case_id}*.txt"):
            pdf_counterpart = txt_path.with_suffix('.pdf')
            if not pdf_counterpart.exists():
                filings.append(('txt', txt_path))

        # Get TXT files from subfolders (without PDF counterpart)
        for txt_path in folder.glob(f"**/{case_id}*.txt"):
            if txt_path.parent != folder:
                pdf_counterpart = txt_path.with_suffix('.pdf')
                if not pdf_counterpart.exists():
                    filings.append(('txt', txt_path))

        # Sort by filename and add to list
        for file_type, file_path in sorted(filings, key=lambda x: x[1].name):
            # Show folder prefix for subfolder items
            if file_path.parent != folder:
                display_name = f"[{file_path.parent.name}] {file_path.stem}"
            else:
                display_name = file_path.stem

            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, str(file_path))
            item.setData(Qt.ItemDataRole.UserRole + 2, file_type)  # Store file type
            widget.filings_list.addItem(item)

        # Auto-select first
        if widget.filings_list.count() > 0:
            widget.filings_list.setCurrentRow(0)
            self._on_case_filing_selected(case_id, widget.filings_list.item(0))

        # Load timeline
        self._refresh_timeline(case_id)

    def _on_case_filing_selected(self, case_id: str, item):
        """Handle filing selection for a case."""
        import re
        widget = self._case_widgets.get(case_id)
        if not widget or not item:
            return

        file_path = Path(item.data(Qt.ItemDataRole.UserRole))
        file_type = item.data(Qt.ItemDataRole.UserRole + 2)  # 'pdf' or 'txt'

        # Determine txt path based on file type
        if file_type == 'txt' or file_path.suffix.lower() == '.txt':
            txt_path = file_path
        else:
            txt_path = file_path.with_suffix('.txt')

        if not txt_path.exists():
            widget.filing_content.setPlainText("No text file. Extract text from PDF first.")
            return

        content = txt_path.read_text(encoding='utf-8')
        widget.filing_content.setPlainText(content)

        # Parse case info
        self._parse_case_info(widget, content, case_id)

        # Parse paragraphs
        self._parse_filing_paragraphs(widget, content)

        # Parse causes
        self._parse_case_causes(widget, content)

    def _parse_filing_paragraphs(self, widget, content: str):
        """Parse numbered paragraphs from filing content."""
        import re
        widget.para_list.clear()
        widget._paragraphs = []

        # Match paragraphs like "15. Some text here"
        pattern = r'^(\d+)\.\s+(.+?)(?=^\d+\.|^[IVX]+\.|^COUNT|$)'
        matches = list(re.finditer(pattern, content, re.MULTILINE | re.DOTALL))

        for match in matches:
            para_num = match.group(1)
            para_text = match.group(2).strip()
            preview = para_text[:80].replace('\n', ' ') + ('...' if len(para_text) > 80 else '')

            item = QListWidgetItem(f"¶{para_num}. {preview}")
            item.setData(Qt.ItemDataRole.UserRole, para_text)
            item.setData(Qt.ItemDataRole.UserRole + 1, para_num)
            widget.para_list.addItem(item)
            widget._paragraphs.append({'num': para_num, 'text': para_text})

        if widget.para_list.count() > 0:
            widget.para_list.setCurrentRow(0)
            self._on_paragraph_selected_widget(widget, widget.para_list.item(0))

    def _on_paragraph_selected(self, case_id: str, item):
        """Handle paragraph selection."""
        widget = self._case_widgets.get(case_id)
        if widget:
            self._on_paragraph_selected_widget(widget, item)

    def _on_paragraph_selected_widget(self, widget, item):
        """Display selected paragraph."""
        if not item:
            return
        text = item.data(Qt.ItemDataRole.UserRole)
        para_num = item.data(Qt.ItemDataRole.UserRole + 1)
        widget.para_detail.setPlainText(text)
        widget._current_para_idx = para_num

    def _copy_paragraph_citation(self, case_id: str):
        """Copy paragraph with proper legal citation."""
        from PyQt6.QtWidgets import QApplication
        widget = self._case_widgets.get(case_id)
        if not widget:
            return

        para_num = widget._current_para_idx
        text = widget.para_detail.toPlainText()

        # Get filing name for citation
        current = widget.filings_list.currentItem()
        if current:
            filename = current.text()
            # Generate citation: "Second Am. Compl. ¶ 15, ECF No. 178"
            doc_type = "Compl." if "COMPLAINT" in filename.upper() or "AMMENDMENT" in filename.upper() else "Filing"
            if "SECOND" in filename.upper():
                doc_type = "Second Am. Compl."
            elif "FIRST" in filename.upper() or "AMENDED" in filename.upper():
                doc_type = "Am. Compl."

            ecf_num = case_id  # Use case ID as ECF for now
            citation = f"{doc_type} ¶ {para_num}, ECF No. {ecf_num}"

            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setText(f"{text}\n\n{citation}")

    def _parse_case_info(self, widget, content: str, case_id: str):
        """Parse and display case info."""
        import re
        case_data = next((c for c in self._lawsuit_cases if c['id'] == case_id), None)

        # Extract basic info
        plaintiffs = []
        defendants = []
        lines = content.split('\n')

        for i, line in enumerate(lines[:50]):
            if 'Plaintiffs' in line:
                for j in range(max(0, i-3), i):
                    pline = lines[j].strip()
                    if pline and 'COURT' not in pline.upper():
                        if ' and ' in pline:
                            plaintiffs.extend([p.strip().rstrip(',') for p in pline.split(' and ')])
                        elif pline:
                            plaintiffs.append(pline.rstrip(','))
            if 'Defendants' in line:
                for j in range(max(0, i-5), i):
                    dline = lines[j].strip()
                    if dline and 'v.' not in dline and 'Plaintiffs' not in dline:
                        for d in dline.split(';'):
                            d = d.strip().rstrip(',')
                            if d and 'COURT' not in d.upper():
                                defendants.append(d)

        html = f"""
        <h2 style="color: #1565C0;">{case_data['number'] if case_data else case_id}</h2>
        <h3 style="color: #2E7D32;">Plaintiffs ({len(plaintiffs)})</h3>
        <ul>{''.join(f'<li>{p}</li>' for p in plaintiffs if p)}</ul>
        <h3 style="color: #C62828;">Defendants ({len(defendants)})</h3>
        <ul>{''.join(f'<li>{d}</li>' for d in defendants if d)}</ul>
        """
        widget.info_text.setHtml(html)

    def _parse_case_causes(self, widget, content: str):
        """Parse causes of action."""
        import re
        widget.causes_list.clear()

        pattern = r'(COUNT\s+[IVX]+\s*[-–—]\s*.+?)(?=COUNT\s+[IVX]+|VI\.\s+PRAYER|$)'
        for match in re.finditer(pattern, content, re.DOTALL | re.IGNORECASE):
            full_text = match.group(1).strip()
            title_lines = [l.strip() for l in full_text.split('\n')[:2] if l.strip() and not l.strip().isdigit()]
            title = ' '.join(title_lines)[:80]

            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, full_text)
            widget.causes_list.addItem(item)

    def _on_search_text_changed(self, case_id: str, text: str):
        """Handle search text changes."""
        widget = self._case_widgets.get(case_id)
        if not widget:
            return

        search_text = text.lower()
        for i in range(widget.filings_list.count()):
            item = widget.filings_list.item(i)
            item.setHidden(search_text not in item.text().lower())

    def _open_case_filing_pdf(self, case_id: str):
        """Open selected PDF for a case."""
        import subprocess
        widget = self._case_widgets.get(case_id)
        if not widget:
            return

        current = widget.filings_list.currentItem()
        if current:
            pdf_path = current.data(Qt.ItemDataRole.UserRole)
            if pdf_path and Path(pdf_path).exists():
                subprocess.run(['open', pdf_path])

    # Timeline methods
    def _load_timeline_data(self) -> dict:
        """Load timeline data from JSON."""
        import json
        timeline_file = Path.home() / "Dropbox" / "Formarter Folder" / "executed_filings" / "timeline.json"
        if timeline_file.exists():
            return json.loads(timeline_file.read_text())
        return {'178': [], '233': [], '254': []}

    def _save_timeline_data(self):
        """Save timeline data to JSON."""
        import json
        timeline_file = Path.home() / "Dropbox" / "Formarter Folder" / "executed_filings" / "timeline.json"
        timeline_file.write_text(json.dumps(self._timeline_data, indent=2))

    def _add_timeline_event(self, case_id: str):
        """Add event to timeline."""
        widget = self._case_widgets.get(case_id)
        if not widget:
            return

        date_str = widget.timeline_date.date().toString("yyyy-MM-dd")
        event_text = widget.timeline_event.text().strip()
        if not event_text:
            return

        if case_id not in self._timeline_data:
            self._timeline_data[case_id] = []

        self._timeline_data[case_id].append({'date': date_str, 'event': event_text})
        self._timeline_data[case_id].sort(key=lambda x: x['date'])
        self._save_timeline_data()
        widget.timeline_event.clear()
        self._refresh_timeline(case_id)

    def _refresh_timeline(self, case_id: str):
        """Refresh timeline display."""
        widget = self._case_widgets.get(case_id)
        if not widget:
            return

        widget.timeline_list.clear()
        events = self._timeline_data.get(case_id, [])
        for ev in events:
            item = QListWidgetItem(f"{ev['date']}  —  {ev['event']}")
            widget.timeline_list.addItem(item)

    def _get_filings_folder(self) -> Path:
        """Get the executed filings folder path."""
        from pathlib import Path
        return Path.home() / "Dropbox" / "Formarter Folder" / "executed_filings"

    def _refresh_filings_list(self):
        """Refresh the list of executed filings."""
        self.filings_list.clear()
        filings_folder = self._get_filings_folder()

        if not filings_folder.exists():
            return

        # Get all PDFs and sort by name
        pdf_files = sorted(filings_folder.glob("*.pdf"))

        for pdf_path in pdf_files:
            # Extract filing number from filename (e.g., "178" from "178 SECOND AMMENDMENT.pdf")
            name = pdf_path.stem
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, str(pdf_path))
            self.filings_list.addItem(item)

        # Select first item if available
        if self.filings_list.count() > 0:
            self.filings_list.setCurrentRow(0)
            self._on_filing_selected(self.filings_list.item(0))

    def _on_filing_selected(self, item):
        """Handle filing selection - load and parse all content."""
        import re
        if not item:
            return

        pdf_path = Path(item.data(Qt.ItemDataRole.UserRole))
        txt_path = pdf_path.with_suffix('.txt')

        if not txt_path.exists():
            self.filing_content.setPlainText("Text file not found. Please extract text from the PDF first.")
            return

        try:
            content = txt_path.read_text(encoding='utf-8')
            self.filing_content.setPlainText(content)

            # Parse case info
            self._parse_filing_info(content)

            # Parse causes of action
            self._parse_causes_of_action(content)

            # Parse sections
            self._parse_sections(content)

        except Exception as e:
            self.filing_content.setPlainText(f"Error reading file: {str(e)}")

    def _parse_filing_info(self, content: str):
        """Parse and display case information."""
        import re
        lines = content.split('\n')

        # Extract info
        case_number = ""
        court = ""
        division = ""
        plaintiffs = []
        defendants = []
        document_title = ""

        # Parse header lines
        for i, line in enumerate(lines[:50]):
            line = line.strip()
            if 'DISTRICT COURT' in line.upper():
                court = line
            if 'DIVISION' in line.upper() and 'NO.' in line.upper():
                parts = line.split('NO.')
                if len(parts) > 1:
                    division = parts[0].strip()
                    case_number = 'No. ' + parts[1].strip()
            elif 'NO.' in line and 'cv' in line.lower():
                case_number = line.strip()
            if 'Plaintiffs' in line:
                # Look back for plaintiff names
                for j in range(max(0, i-3), i):
                    pline = lines[j].strip()
                    if pline and 'COURT' not in pline.upper() and 'DIVISION' not in pline.upper():
                        if ' and ' in pline:
                            plaintiffs.extend([p.strip().rstrip(',') for p in pline.split(' and ')])
                        elif pline and pline not in plaintiffs:
                            plaintiffs.append(pline.rstrip(','))
            if 'Defendants' in line:
                # Look back for defendant names
                for j in range(max(0, i-5), i):
                    dline = lines[j].strip()
                    if dline and 'v.' not in dline and 'Plaintiffs' not in dline:
                        # Split on semicolons
                        for d in dline.split(';'):
                            d = d.strip().rstrip(',')
                            if d and d not in defendants and 'COURT' not in d.upper():
                                defendants.append(d)
            if 'COMPLAINT' in line.upper() or 'MOTION' in line.upper() or 'AMENDED' in line.upper():
                if not document_title:
                    document_title = line

        # Build HTML info display
        html = f"""
        <div style="font-family: 'Helvetica Neue', Arial, sans-serif;">
            <h2 style="color: #1565C0; border-bottom: 2px solid #1565C0; padding-bottom: 10px;">
                {case_number or 'Case Information'}
            </h2>

            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <tr>
                    <td style="padding: 8px; font-weight: bold; width: 150px; vertical-align: top;">Court:</td>
                    <td style="padding: 8px;">{court}</td>
                </tr>
                <tr style="background-color: #f5f5f5;">
                    <td style="padding: 8px; font-weight: bold; vertical-align: top;">Division:</td>
                    <td style="padding: 8px;">{division}</td>
                </tr>
                <tr>
                    <td style="padding: 8px; font-weight: bold; vertical-align: top;">Case Number:</td>
                    <td style="padding: 8px; font-size: 14px; color: #1565C0;"><b>{case_number}</b></td>
                </tr>
                <tr style="background-color: #f5f5f5;">
                    <td style="padding: 8px; font-weight: bold; vertical-align: top;">Document:</td>
                    <td style="padding: 8px;">{document_title}</td>
                </tr>
            </table>

            <h3 style="color: #2E7D32; margin-top: 25px; border-bottom: 1px solid #2E7D32; padding-bottom: 5px;">
                Plaintiffs ({len(plaintiffs)})
            </h3>
            <ul style="margin: 10px 0; padding-left: 25px;">
        """
        for p in plaintiffs:
            if p:
                html += f"<li style='padding: 5px 0;'>{p}</li>"
        html += "</ul>"

        html += f"""
            <h3 style="color: #C62828; margin-top: 25px; border-bottom: 1px solid #C62828; padding-bottom: 5px;">
                Defendants ({len(defendants)})
            </h3>
            <ul style="margin: 10px 0; padding-left: 25px;">
        """
        for d in defendants:
            if d:
                html += f"<li style='padding: 5px 0;'>{d}</li>"
        html += "</ul></div>"

        self.filing_info_text.setHtml(html)

    def _parse_causes_of_action(self, content: str):
        """Parse causes of action from filing."""
        import re
        self.causes_list.clear()
        self._filing_causes = []

        # Find all COUNT lines
        pattern = r'(COUNT\s+[IVX]+\s*[-–—]\s*.+?)(?=COUNT\s+[IVX]+|VI\.\s+PRAYER|$)'
        matches = list(re.finditer(pattern, content, re.DOTALL | re.IGNORECASE))

        for match in matches:
            full_text = match.group(1).strip()
            # Get title (first line or two)
            lines = full_text.split('\n')
            title_parts = []
            for line in lines[:3]:
                line = line.strip()
                if line and not line.isdigit():
                    title_parts.append(line)
                    if len(title_parts) >= 2:
                        break

            title = ' '.join(title_parts)
            # Clean up title
            title = re.sub(r'\s+', ' ', title)
            if len(title) > 80:
                title = title[:77] + '...'

            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, full_text)
            self.causes_list.addItem(item)
            self._filing_causes.append({'title': title, 'text': full_text})

        # Select first if available
        if self.causes_list.count() > 0:
            self.causes_list.setCurrentRow(0)
            self._on_cause_selected(self.causes_list.item(0))

    def _on_cause_selected(self, item):
        """Display selected cause of action."""
        if not item:
            return
        text = item.data(Qt.ItemDataRole.UserRole)
        self.cause_detail.setPlainText(text)

    def _parse_sections(self, content: str):
        """Parse major sections from filing."""
        import re
        self.sections_list.clear()
        self._filing_sections = []

        # Find Roman numeral sections
        pattern = r'^([IVX]+\.\s+[A-Z][A-Z\s]+)$'
        lines = content.split('\n')

        current_section = None
        current_text = []

        for line in lines:
            line_stripped = line.strip()
            match = re.match(pattern, line_stripped)
            if match:
                # Save previous section
                if current_section:
                    self._filing_sections.append({
                        'title': current_section,
                        'text': '\n'.join(current_text)
                    })
                current_section = match.group(1)
                current_text = [line]
            elif current_section:
                current_text.append(line)

        # Save last section
        if current_section:
            self._filing_sections.append({
                'title': current_section,
                'text': '\n'.join(current_text)
            })

        # Populate list
        for section in self._filing_sections:
            item = QListWidgetItem(section['title'])
            item.setData(Qt.ItemDataRole.UserRole, section['text'])
            self.sections_list.addItem(item)

        # Select first if available
        if self.sections_list.count() > 0:
            self.sections_list.setCurrentRow(0)
            self._on_section_selected(self.sections_list.item(0))

    def _on_section_selected(self, item):
        """Display selected section."""
        if not item:
            return
        text = item.data(Qt.ItemDataRole.UserRole)
        self.section_detail.setPlainText(text)

    def _open_selected_filing_pdf(self):
        """Open the selected filing's PDF in the default viewer."""
        import subprocess

        current_item = self.filings_list.currentItem()
        if not current_item:
            return

        pdf_path = current_item.data(Qt.ItemDataRole.UserRole)
        if pdf_path and Path(pdf_path).exists():
            subprocess.run(['open', pdf_path])

    def _on_quick_print_date_toggle(self, state):
        """Enable/disable date edit based on checkbox."""
        self.quick_print_date_edit.setEnabled(state == 2)  # Qt.Checked = 2

    def _on_print_signature_block(self, include_cert=True):
        """Generate and export a standalone signature block."""
        import tempfile
        import subprocess
        from .pdf_export import generate_pdf

        # Get selected case profile
        profile_idx = self.quick_print_profile_dropdown.currentData()
        if profile_idx is None:
            profile_idx = 0
        profile = self.CASE_PROFILES[profile_idx]

        # Determine filing date
        if self.quick_print_date_cb.isChecked():
            # Use specific date from date picker (format: MM/DD/YYYY)
            filing_date = self.quick_print_date_edit.date().toString("MM/dd/yyyy")
        else:
            # Use blank date for hand-filling
            filing_date = "__BLANK__"

        # Create signature block
        signature = SignatureBlock(
            attorney_name=profile.signature.attorney_name,
            attorney_name_2=getattr(profile.signature, 'attorney_name_2', ''),
            phone=profile.signature.phone,
            phone_2=getattr(profile.signature, 'phone_2', ''),
            email=profile.signature.email,
            email_2=getattr(profile.signature, 'email_2', ''),
            address=profile.signature.address,
            bar_number=profile.signature.bar_number,
            firm_name=profile.signature.firm_name,
            filing_date=filing_date,  # Use selected date or blank
            include_certificate=include_cert  # Include certificate based on button
        )

        # No body content - just signature block
        paragraphs = {}

        # Generate PDF
        try:
            # Create temp file
            temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            output_path = temp_file.name
            temp_file.close()

            # Generate with minimal content, no page numbers
            generate_pdf(
                paragraphs=paragraphs,
                section_starts={},
                output_path=output_path,
                caption=None,  # No caption
                signature=signature,
                document_title="",  # No title
                all_sections=[],
                skip_page_numbers=True  # No page numbers for signature page
            )

            # Show preview
            from datetime import datetime
            year = datetime.now().year
            cert_section = ""
            if include_cert:
                cert_section = f"""
CERTIFICATE OF SERVICE
I filed the foregoing in person with the Clerk... (ECF notification)

_________________________
{signature.attorney_name}
"""
            preview_text = f"""
SIGNATURE BLOCK PREVIEW
=======================

Respectfully submitted at this ___ day of ____________, {year}.


_________________________
{signature.attorney_name}, Pro Se
Tel: {signature.phone}
{signature.email}
{signature.address}
{cert_section}
PDF Generated: {output_path}
"""
            self.quick_print_preview.setPlainText(preview_text)

            # Open PDF directly (no message box)
            if sys.platform == "darwin":
                subprocess.run(["open", output_path])
            elif sys.platform == "win32":
                subprocess.run(["start", output_path], shell=True)
            else:
                subprocess.run(["xdg-open", output_path])

        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to generate signature block PDF:\n{str(e)}"
            )

    def _on_print_certificate_only(self):
        """Generate and export a certificate of service only."""
        import tempfile
        import subprocess
        from .pdf_export import generate_pdf

        # Get selected case profile
        profile_idx = self.quick_print_profile_dropdown.currentData()
        if profile_idx is None:
            profile_idx = 0
        profile = self.CASE_PROFILES[profile_idx]

        # Determine filing date
        if self.quick_print_date_cb.isChecked():
            filing_date = self.quick_print_date_edit.date().toString("MM/dd/yyyy")
        else:
            filing_date = "__BLANK__"

        # Create signature block with date for certificate
        signature = SignatureBlock(
            attorney_name=profile.signature.attorney_name,
            filing_date=filing_date,
        )

        # Generate PDF
        try:
            # Create temp file
            temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            output_path = temp_file.name
            temp_file.close()

            # Generate certificate only
            generate_pdf(
                paragraphs={},
                section_starts={},
                output_path=output_path,
                caption=None,
                signature=signature,
                document_title="",
                all_sections=[],
                skip_page_numbers=True,
                certificate_only=True
            )

            # Show preview
            from datetime import datetime
            year = datetime.now().year
            date_line = f"Dated this ___ day of ____________, {year}." if filing_date == "__BLANK__" else f"Dated this {filing_date}."
            preview_text = f"""
CERTIFICATE OF SERVICE PREVIEW
==============================

CERTIFICATE OF SERVICE

I hereby certify that on this date, I filed the foregoing in person
with the Clerk of Court, which will send notification of such filing
to all counsel of record via the CM/ECF system.

{date_line}

_________________________
{signature.attorney_name}

PDF Generated: {output_path}
"""
            self.quick_print_preview.setPlainText(preview_text)

            # Open PDF directly
            if sys.platform == "darwin":
                subprocess.run(["open", output_path])
            elif sys.platform == "win32":
                subprocess.run(["start", output_path], shell=True)
            else:
                subprocess.run(["xdg-open", output_path])

        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to generate certificate PDF:\n{str(e)}"
            )

    def _refresh_case_law_doc_list(self):
        """Refresh the document dropdown in Case Law tab."""
        self.case_law_doc_dropdown.clear()
        self.case_law_doc_dropdown.addItem("-- Select a Document --", None)

        documents = self.storage.list_all()
        for doc in documents:
            case_name = self._get_case_name(doc.case_profile_index)
            display = f"{doc.name} (Case {case_name})"
            self.case_law_doc_dropdown.addItem(display, doc.id)

    def _on_extract_citations(self):
        """Extract citations from selected document."""
        doc_id = self.case_law_doc_dropdown.currentData()
        if not doc_id:
            QMessageBox.warning(
                self, "No Document Selected",
                "Please select a document to analyze."
            )
            return

        doc = self.storage.get_by_id(doc_id)
        if not doc:
            QMessageBox.warning(
                self, "Document Not Found",
                "The selected document could not be found."
            )
            return

        # Parse paragraphs from text content
        paragraphs = {}
        lines = doc.text_content.split("\n")
        para_num = 1
        for line in lines:
            cleaned = line.strip()
            if cleaned:
                paragraphs[para_num] = cleaned
                para_num += 1

        if not paragraphs:
            self.case_law_results.setPlainText("No paragraphs found in this document.")
            return

        # Extract citations
        extractor = CaseLawExtractor()
        results = extractor.extract_from_paragraphs(paragraphs)

        # Generate report
        report = extractor.generate_report(results)
        self.case_law_results.setPlainText(report)

    def _on_copy_report(self):
        """Copy the case law report to clipboard."""
        text = self.case_law_results.toPlainText()
        if not text or text == self.case_law_results.placeholderText():
            QMessageBox.information(
                self, "Nothing to Copy",
                "Extract citations first to generate a report."
            )
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        QMessageBox.information(
            self, "Copied",
            "Report copied to clipboard."
        )

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
        """Create the left panel with text editor and annotations panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header label
        header = QLabel("Text Editor")
        header.setStyleSheet("font-weight: bold; padding: 5px; background: #e8f4e8;")
        layout.addWidget(header)

        # Create splitter to hold editor and annotations panel
        editor_splitter = QSplitter(Qt.Orientation.Vertical)

        # Text editor with Times New Roman font (using AnnotationTextEdit for annotation support)
        self.text_editor = AnnotationTextEdit()
        font = QFont("Times New Roman", 12)
        self.text_editor.setFont(font)
        self.text_editor.setPlaceholderText(
            "Type your document here...\n\n"
            "Press Enter to create a new paragraph.\n\n"
            "Right-click text to add notes.\n"
            "Right-click paragraphs in Section Tree to assign sections."
        )

        # Connect text changed signal for real-time paragraph detection
        self.text_editor.textChanged.connect(self._on_text_changed)

        # Connect annotation sync signal
        self.text_editor.annotations_need_sync.connect(self._on_annotation_changed)

        # Add syntax highlighting for section/subsection tags
        self._highlighter = SectionTagHighlighter(self.text_editor.document())

        editor_splitter.addWidget(self.text_editor)

        # Annotations panel (collapsible notes view)
        annotations_widget = QWidget()
        annotations_layout = QVBoxLayout(annotations_widget)
        annotations_layout.setContentsMargins(0, 0, 0, 0)
        annotations_layout.setSpacing(2)

        # Annotations header with count and Add Note button
        annotations_header_widget = QWidget()
        annotations_header_layout = QHBoxLayout(annotations_header_widget)
        annotations_header_layout.setContentsMargins(3, 3, 3, 3)
        annotations_header_layout.setSpacing(5)

        self.annotations_header = QLabel("Notes (0)")
        self.annotations_header.setStyleSheet("font-weight: bold;")
        annotations_header_layout.addWidget(self.annotations_header)

        annotations_header_layout.addStretch()

        add_note_btn = QPushButton("+ Add Note")
        add_note_btn.setMaximumWidth(80)
        add_note_btn.setToolTip("Add a standalone note (not linked to any paragraph)")
        add_note_btn.clicked.connect(self._add_standalone_note)
        annotations_header_layout.addWidget(add_note_btn)

        annotations_header_widget.setStyleSheet("background: #fff8dc;")
        annotations_layout.addWidget(annotations_header_widget)

        # Annotations list
        self.annotations_list = QListWidget()
        self.annotations_list.setAlternatingRowColors(True)
        self.annotations_list.setStyleSheet("""
            QListWidget {
                font-size: 11px;
                background: #fffef0;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background: #fff3cd;
            }
        """)
        self.annotations_list.itemClicked.connect(self._on_annotation_list_clicked)
        self.annotations_list.itemDoubleClicked.connect(self._on_annotation_list_double_clicked)
        # Enable right-click context menu
        self.annotations_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.annotations_list.customContextMenuRequested.connect(self._annotations_list_context_menu)
        annotations_layout.addWidget(self.annotations_list)

        editor_splitter.addWidget(annotations_widget)

        # Set initial splitter sizes (editor gets 75%, annotations get 25%)
        editor_splitter.setSizes([600, 200])

        layout.addWidget(editor_splitter)

        return panel

    def _on_annotation_changed(self):
        """Handle annotation changes - refresh the annotations list and highlights."""
        self._refresh_annotations_list()
        self._update_paragraph_highlights()

    def _on_annotation_list_clicked(self, item):
        """Handle click on annotation in list - scroll to paragraph if linked."""
        annotation_id = item.data(Qt.ItemDataRole.UserRole)
        if annotation_id:
            annotation = self.text_editor.get_annotation_by_id(annotation_id)
            if annotation and annotation.is_linked:
                self.text_editor.scroll_to_paragraph(annotation.paragraph_number)

    def _on_annotation_list_double_clicked(self, item):
        """Handle double-click on annotation - edit the note."""
        annotation_id = item.data(Qt.ItemDataRole.UserRole)
        if annotation_id:
            annotation = self.text_editor.get_annotation_by_id(annotation_id)
            if annotation:
                self._edit_annotation(annotation)

    def _add_standalone_note(self):
        """Add a new standalone note (not linked to any paragraph)."""
        import uuid
        from src.models.saved_document import Annotation

        note, ok = QInputDialog.getMultiLineText(
            self,
            "Add Standalone Note",
            "Enter your note:",
            ""
        )

        if ok and note.strip():
            annotation = Annotation(
                id=str(uuid.uuid4()),
                note=note.strip(),
                paragraph_number=None,  # Standalone
                paragraph_preview="[Standalone note]"
            )
            self.text_editor.add_annotation(annotation)
            self._on_annotation_changed()

    def _add_note_for_paragraph(self, para_num: int):
        """Add a note linked to a specific paragraph."""
        import uuid
        from src.models.saved_document import Annotation

        # Get paragraph text for preview from document.paragraphs
        if para_num in self.document.paragraphs:
            para_text = self.document.paragraphs[para_num].text
            preview = para_text[:50] + ("..." if len(para_text) > 50 else "")
        else:
            preview = f"Paragraph {para_num}"

        note, ok = QInputDialog.getMultiLineText(
            self,
            "Add Note",
            f"Note for paragraph {para_num}:\n\"{preview}\"",
            ""
        )

        if ok and note.strip():
            annotation = Annotation(
                id=str(uuid.uuid4()),
                note=note.strip(),
                paragraph_number=para_num,
                paragraph_preview=preview
            )
            self.text_editor.add_annotation(annotation)
            self._on_annotation_changed()

    def _show_notes_for_paragraph(self, para_num: int):
        """Show all notes for a specific paragraph in a dialog."""
        notes = self.text_editor.get_annotations_for_paragraph(para_num)
        if not notes:
            QMessageBox.information(self, "Notes", f"No notes for paragraph {para_num}")
            return

        # Build message with all notes
        msg_lines = [f"Notes for paragraph {para_num}:\n"]
        for i, note in enumerate(notes, 1):
            msg_lines.append(f"{i}. {note.note}\n")

        QMessageBox.information(self, f"Notes ({len(notes)})", "\n".join(msg_lines))

    def _edit_annotation(self, annotation):
        """Edit an existing annotation."""
        if annotation.is_linked:
            title = f"Edit Note (Paragraph {annotation.paragraph_number})"
        else:
            title = "Edit Standalone Note"

        note, ok = QInputDialog.getMultiLineText(
            self,
            title,
            f"Reference: \"{annotation.paragraph_preview}\"",
            annotation.note
        )

        if ok:
            annotation.note = note.strip()
            self._on_annotation_changed()

    def _delete_annotation(self, annotation_id: str):
        """Delete an annotation by ID."""
        annotation = self.text_editor.get_annotation_by_id(annotation_id)
        if not annotation:
            return

        if annotation.is_linked:
            msg = f"Delete note for paragraph {annotation.paragraph_number}?"
        else:
            msg = "Delete this standalone note?"

        reply = QMessageBox.question(
            self,
            "Delete Note",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.text_editor.remove_annotation(annotation_id)
            self._on_annotation_changed()

    def _update_paragraph_highlights(self):
        """Update highlights for paragraphs that have notes."""
        paragraphs_with_notes = set()
        for annotation in self.text_editor.get_annotations():
            if annotation.is_linked:
                paragraphs_with_notes.add(annotation.paragraph_number)
        self.text_editor.apply_paragraph_highlights(paragraphs_with_notes)

    def _refresh_annotations_list(self):
        """Refresh the annotations list widget."""
        self.annotations_list.clear()
        annotations = self.text_editor.get_annotations()
        self.annotations_header.setText(f"Notes ({len(annotations)})")

        # Sort: linked notes first (by paragraph number), then standalone
        linked = [a for a in annotations if a.is_linked]
        standalone = [a for a in annotations if not a.is_linked]
        linked.sort(key=lambda a: a.paragraph_number)

        for annotation in linked + standalone:
            # Create display text
            if annotation.is_linked:
                para_tag = f"[P{annotation.paragraph_number}]"
            else:
                para_tag = "[Standalone]"

            note_preview = annotation.note[:50]
            if len(annotation.note) > 50:
                note_preview += "..."

            item_text = f"{para_tag} {note_preview}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, annotation.id)

            # Color-code: linked notes yellow background, standalone white
            if annotation.is_linked:
                item.setBackground(QColor("#FFFACD"))
            item.setToolTip(f"Paragraph: {annotation.paragraph_preview}\n\nNote: {annotation.note}")
            self.annotations_list.addItem(item)

    def _annotations_list_context_menu(self, position):
        """Show context menu for annotation list items."""
        item = self.annotations_list.itemAt(position)
        if not item:
            return

        annotation_id = item.data(Qt.ItemDataRole.UserRole)
        annotation = self.text_editor.get_annotation_by_id(annotation_id)
        if not annotation:
            return

        menu = QMenu(self)

        edit_action = menu.addAction("Edit Note")
        edit_action.triggered.connect(lambda: self._edit_annotation(annotation))

        if annotation.is_linked:
            unlink_action = menu.addAction("Unlink from Paragraph")
            unlink_action.triggered.connect(lambda: self._unlink_annotation(annotation_id))

        menu.addSeparator()
        delete_action = menu.addAction("Delete Note")
        delete_action.triggered.connect(lambda: self._delete_annotation(annotation_id))

        menu.exec(self.annotations_list.mapToGlobal(position))

    def _unlink_annotation(self, annotation_id: str):
        """Unlink an annotation from its paragraph."""
        annotation = self.text_editor.get_annotation_by_id(annotation_id)
        if annotation and annotation.is_linked:
            annotation.unlink()
            self._on_annotation_changed()

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
        """Create the collapsible sidebar panel with filing tree."""
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
        header = QLabel("Documents & Filings")
        header.setStyleSheet("font-weight: bold; font-size: 12px; padding: 5px;")
        layout.addWidget(header)

        # Storage location indicator
        storage_path = self.storage.get_storage_location()
        folder_name = Path(storage_path).name
        is_dropbox = "Dropbox" in storage_path
        storage_label = QLabel(f"{'Dropbox' if is_dropbox else 'Local'}: {folder_name}")
        storage_label.setStyleSheet("font-size: 10px; color: #666; padding: 2px 5px;")
        storage_label.setToolTip(storage_path)
        layout.addWidget(storage_label)

        # Buttons row
        btn_layout = QHBoxLayout()

        # New document button
        new_btn = QPushButton("+ New")
        new_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                border: none;
                padding: 6px 10px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #218838;
            }
        """)
        new_btn.clicked.connect(self._on_new_document)
        btn_layout.addWidget(new_btn)

        # Save current button
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet("""
            QPushButton {
                background: #007bff;
                color: white;
                border: none;
                padding: 6px 10px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #0069d9;
            }
        """)
        save_btn.clicked.connect(self._on_save_document)
        btn_layout.addWidget(save_btn)

        # New Filing button
        new_filing_btn = QPushButton("+ Filing")
        new_filing_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border: none;
                padding: 6px 10px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        new_filing_btn.clicked.connect(self._on_new_filing)
        btn_layout.addWidget(new_filing_btn)

        layout.addLayout(btn_layout)

        # Filter bar for tag-based filtering
        self.filter_bar = FilterBar()
        self.filter_bar.search_changed.connect(self._on_filter_search_changed)
        self.filter_bar.filters_changed.connect(self._on_filter_tags_changed)
        self.filter_bar.cleared.connect(self._on_filters_cleared)
        layout.addWidget(self.filter_bar)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background: #ccc;")
        layout.addWidget(separator)

        # Filing Tree (replaces doc_list for hierarchical view)
        self.filing_tree = FilingTreeWidget()
        self.filing_tree.document_selected.connect(self._on_filing_tree_document_selected)
        self.filing_tree.filing_selected.connect(self._on_filing_tree_filing_selected)
        self.filing_tree.case_selected.connect(self._on_filing_tree_case_selected)
        self.filing_tree.filing_context_menu.connect(self._on_filing_context_menu)
        self.filing_tree.document_context_menu.connect(self._on_doc_context_menu)
        self.filing_tree.case_context_menu.connect(self._on_case_context_menu)
        layout.addWidget(self.filing_tree)

        # Also keep a simple doc_list for backward compatibility (hidden by default)
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
        self.doc_list.hide()  # Hidden by default, filing tree is primary
        layout.addWidget(self.doc_list)

        # Migrate existing documents to filing system on startup
        self.storage.migrate_to_filing_system()

        return panel

    # =========================================================================
    # FILING SYSTEM METHODS
    # =========================================================================

    def _on_new_filing(self):
        """Create a new filing in the current case."""
        cases = self.storage.get_cases()
        if not cases:
            QMessageBox.warning(
                self, "No Case",
                "Please create a case first before creating filings."
            )
            return

        # Get filing name
        name, ok = QInputDialog.getText(
            self, "New Filing", "Filing name:"
        )
        if not ok or not name.strip():
            return

        # If multiple cases, ask which one
        if len(cases) > 1:
            case_names = [c.name for c in cases]
            case_name, ok = QInputDialog.getItem(
                self, "Select Case", "Create filing in:",
                case_names, 0, False
            )
            if not ok:
                return
            case = next(c for c in cases if c.name == case_name)
        else:
            case = cases[0]

        # Create filing
        self.storage.create_filing(name.strip(), case.id)
        self._refresh_document_list()

    def _on_filing_tree_document_selected(self, doc_id: str):
        """Handle document selection in filing tree."""
        doc = self.storage.get_by_id(doc_id)
        if doc:
            self._load_doc_to_editor(doc)

    def _on_filing_tree_filing_selected(self, filing_id: str):
        """Handle filing selection in filing tree."""
        filing = self.storage.get_filing(filing_id)
        if filing:
            # Show filing info in status or a panel
            pass  # Future: show filing details panel

    def _on_filing_tree_case_selected(self, case_id: str):
        """Handle case selection in filing tree."""
        pass  # Future: show case details

    def _on_filing_context_menu(self, filing_id: str, pos):
        """Show context menu for filing."""
        menu = QMenu(self)

        # Add Tag
        add_tag_action = menu.addAction("Add Tag...")
        add_tag_action.triggered.connect(lambda: self._add_tag_to_filing(filing_id))

        # Add Comment
        add_comment_action = menu.addAction("Add Comment...")
        add_comment_action.triggered.connect(lambda: self._add_comment_to_filing(filing_id))

        menu.addSeparator()

        # Rename
        rename_action = menu.addAction("Rename...")
        rename_action.triggered.connect(lambda: self._rename_filing(filing_id))

        # Set Status
        status_menu = menu.addMenu("Set Status")
        for status in ["draft", "pending", "filed"]:
            action = status_menu.addAction(status.title())
            action.triggered.connect(lambda checked, s=status: self._set_filing_status(filing_id, s))

        # Set Filing Date
        set_date_action = menu.addAction("Set Filing Date...")
        set_date_action.triggered.connect(lambda: self._set_filing_date(filing_id))

        menu.addSeparator()

        # Add Exhibit
        add_exhibit_action = menu.addAction("Add Exhibit File...")
        add_exhibit_action.triggered.connect(lambda: self._add_exhibit_to_filing(filing_id))

        # Export All PDFs
        export_action = menu.addAction("Export All PDFs")
        export_action.triggered.connect(lambda: self._export_filing_pdfs(filing_id))

        menu.addSeparator()

        # Archive
        archive_action = menu.addAction("Archive")
        archive_action.triggered.connect(lambda: self._archive_filing(filing_id))

        # Delete
        delete_action = menu.addAction("Delete...")
        delete_action.triggered.connect(lambda: self._delete_filing(filing_id))

        menu.exec(pos)

    def _on_doc_context_menu(self, doc_id: str, pos):
        """Show context menu for document in filing tree."""
        menu = QMenu(self)

        # Load
        load_action = menu.addAction("Open")
        load_action.triggered.connect(lambda: self._on_filing_tree_document_selected(doc_id))

        menu.addSeparator()

        # Move to Filing
        move_menu = menu.addMenu("Move to Filing...")
        cases = self.storage.get_cases()
        for case in cases:
            case_menu = move_menu.addMenu(case.name)
            for filing in case.filings:
                action = case_menu.addAction(filing.name)
                action.triggered.connect(
                    lambda checked, fid=filing.id: self._move_doc_to_filing(doc_id, fid)
                )
            # Unfiled option
            unfiled_action = case_menu.addAction("Unfiled")
            unfiled_action.triggered.connect(
                lambda checked, cid=case.id: self._move_doc_to_unfiled(doc_id, cid)
            )

        menu.addSeparator()

        # Rename
        rename_action = menu.addAction("Rename...")
        rename_action.triggered.connect(lambda: self._rename_document(doc_id))

        # Duplicate
        duplicate_action = menu.addAction("Duplicate")
        duplicate_action.triggered.connect(lambda: self._duplicate_document(doc_id))

        # Delete
        delete_action = menu.addAction("Delete...")
        delete_action.triggered.connect(lambda: self._delete_document(doc_id))

        menu.exec(pos)

    def _on_case_context_menu(self, case_id: str, pos):
        """Show context menu for case."""
        menu = QMenu(self)

        # New Filing
        new_filing_action = menu.addAction("New Filing...")
        new_filing_action.triggered.connect(lambda: self._create_filing_in_case(case_id))

        menu.addSeparator()

        # Rename Case
        rename_action = menu.addAction("Rename Case...")
        rename_action.triggered.connect(lambda: self._rename_case(case_id))

        menu.exec(pos)

    def _add_tag_to_filing(self, filing_id: str):
        """Add tags to a filing."""
        filing = self.storage.get_filing(filing_id)
        if not filing:
            return

        tags = self.storage.get_tags()
        dialog = TagPickerDialog(tags, filing.tags, self)
        dialog.tag_created.connect(
            lambda tid, name, color: self.storage.save_tag(Tag(tid, name, color, False))
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_tags = dialog.get_selected_tags()
            self.storage.set_filing_tags(filing_id, selected_tags)
            self._refresh_document_list()

    def _add_comment_to_filing(self, filing_id: str):
        """Add a comment to a filing's log."""
        text, ok = QInputDialog.getMultiLineText(
            self, "Add Comment", "Comment:"
        )
        if ok and text.strip():
            self.storage.add_comment_to_filing(filing_id, text.strip())

    def _rename_filing(self, filing_id: str):
        """Rename a filing."""
        filing = self.storage.get_filing(filing_id)
        if not filing:
            return

        name, ok = QInputDialog.getText(
            self, "Rename Filing", "New name:", text=filing.name
        )
        if ok and name.strip():
            filing.name = name.strip()
            self.storage.save_filing(filing)
            self._refresh_document_list()

    def _set_filing_status(self, filing_id: str, status: str):
        """Set filing status."""
        filing = self.storage.get_filing(filing_id)
        if filing:
            filing.status = status
            self.storage.save_filing(filing)
            self._refresh_document_list()

    def _set_filing_date(self, filing_id: str):
        """Set filing date."""
        from PyQt6.QtWidgets import QDateEdit
        from PyQt6.QtCore import QDate

        filing = self.storage.get_filing(filing_id)
        if not filing:
            return

        # Simple date input
        date_str, ok = QInputDialog.getText(
            self, "Set Filing Date",
            "Filing date (MM/DD/YYYY):",
            text=filing.filing_date
        )
        if ok:
            filing.filing_date = date_str.strip()
            self.storage.save_filing(filing)
            self._refresh_document_list()

    def _add_exhibit_to_filing(self, filing_id: str):
        """Add an exhibit file to a filing."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Exhibit File", "",
            "All Files (*);;PDF Files (*.pdf);;Images (*.png *.jpg *.jpeg);;Documents (*.doc *.docx)"
        )
        if file_path:
            exhibit = self.storage.add_exhibit_file(filing_id, file_path)
            if exhibit:
                self._refresh_document_list()
                QMessageBox.information(
                    self, "Exhibit Added",
                    f"Added exhibit: {exhibit.filename}"
                )

    def _export_filing_pdfs(self, filing_id: str):
        """Export all documents in a filing as PDFs."""
        filing = self.storage.get_filing(filing_id)
        if not filing or not filing.document_ids:
            QMessageBox.warning(self, "No Documents", "This filing has no documents.")
            return

        # Get export directory
        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Export Directory"
        )
        if not dir_path:
            return

        exported = 0
        for doc_id in filing.document_ids:
            doc = self.storage.get_by_id(doc_id)
            if doc:
                # Generate PDF (reuse existing logic)
                self._load_doc_to_editor(doc)
                pdf_path = Path(dir_path) / f"{doc.name}.pdf"
                # Export using existing PDF generation
                self._on_export_pdf_to_path(str(pdf_path))
                exported += 1

        QMessageBox.information(
            self, "Export Complete",
            f"Exported {exported} document(s) to {dir_path}"
        )

    def _archive_filing(self, filing_id: str):
        """Archive a filing (hide from main view)."""
        filing = self.storage.get_filing(filing_id)
        if filing:
            filing.status = "archived"
            self.storage.save_filing(filing)
            self._refresh_document_list()

    def _delete_filing(self, filing_id: str):
        """Delete a filing."""
        reply = QMessageBox.question(
            self, "Delete Filing",
            "Are you sure you want to delete this filing?\n\n"
            "Documents will be moved to Unfiled.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            filing = self.storage.get_filing(filing_id)
            if filing:
                # Move documents to unfiled
                for doc_id in filing.document_ids:
                    self.storage.move_document_to_unfiled(doc_id, filing.case_id)
                # Delete filing
                self.storage.delete_filing(filing_id)
                self._refresh_document_list()

    def _move_doc_to_filing(self, doc_id: str, filing_id: str):
        """Move a document to a filing."""
        self.storage.move_document_to_filing(doc_id, filing_id)
        self._refresh_document_list()

    def _move_doc_to_unfiled(self, doc_id: str, case_id: str):
        """Move a document to unfiled."""
        self.storage.move_document_to_unfiled(doc_id, case_id)
        self._refresh_document_list()

    def _create_filing_in_case(self, case_id: str):
        """Create a new filing in a specific case."""
        name, ok = QInputDialog.getText(
            self, "New Filing", "Filing name:"
        )
        if ok and name.strip():
            self.storage.create_filing(name.strip(), case_id)
            self._refresh_document_list()

    def _rename_case(self, case_id: str):
        """Rename a case."""
        cases = self.storage.get_cases()
        case = next((c for c in cases if c.id == case_id), None)
        if not case:
            return

        name, ok = QInputDialog.getText(
            self, "Rename Case", "New name:", text=case.name
        )
        if ok and name.strip():
            case.name = name.strip()
            self.storage.save_case(case)
            self._refresh_document_list()

    def _on_filter_search_changed(self, text: str):
        """Handle search text change in filter bar."""
        # TODO: Implement filtering
        pass

    def _on_filter_tags_changed(self, tag_ids: list):
        """Handle tag filter change."""
        # TODO: Implement tag filtering
        pass

    def _on_filters_cleared(self):
        """Handle filters cleared."""
        self._refresh_document_list()

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
        """Refresh the document list and filing tree from storage."""
        # Get all data
        documents = self.storage.list_all()
        cases = self.storage.get_cases()
        tags = self.storage.get_tags()

        # Build document lookup dict
        doc_dict = {doc.id: {"name": doc.name, "id": doc.id} for doc in documents}

        # Build tag dict
        tag_dict = {t.id: t for t in tags}

        # Update filing tree
        if hasattr(self, 'filing_tree'):
            self.filing_tree.set_data(cases, tag_dict, doc_dict)

        # Update filter bar with available tags
        if hasattr(self, 'filter_bar'):
            self.filter_bar.set_tags(tags)

        # Also update doc_list for backward compatibility (hidden by default)
        self.doc_list.clear()
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
            self.text_editor.clear_annotations()  # Clear annotations for new doc
            self._refresh_annotations_list()  # Update UI
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

        # Save annotations
        doc.annotations = self.text_editor.get_annotations()

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

            # Load annotations
            self.text_editor.set_annotations(doc.annotations)
            self._refresh_annotations_list()

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

        # Mark as Filed / Unfile action (links Editor doc to Executed Filings tab)
        doc = self.storage.get_by_id(doc_id)
        if doc and doc.is_filed:
            unfile_action = menu.addAction("\U0001F513 Unfile Document")  # Unlock icon
            unfile_action.triggered.connect(lambda: self._on_unfile_document(doc_id))
        else:
            file_action = menu.addAction("\U0001F512 Mark as Filed...")  # Lock icon
            file_action.triggered.connect(lambda: self._on_mark_as_filed(doc_id))

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

            # Make editor read-only if document is filed
            # Filed documents are linked to Executed Filings tab and should not be edited
            if doc.is_filed or doc.is_locked:
                self.text_editor.setReadOnly(True)
                self.statusBar().showMessage(
                    f"'{doc.name}' is filed with the court - read-only mode", 5000
                )
            else:
                self.text_editor.setReadOnly(False)

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

    # ==========================================================================
    # MARK AS FILED FEATURE
    # Links Editor documents to the Executed Filings tab
    # ==========================================================================

    def _on_mark_as_filed(self, doc_id: str):
        """
        Mark a document as filed with the court.

        This links the Editor document to the Executed Filings tab:
        1. Shows dialog to collect filing date and docket number
        2. Generates .txt and .pdf files in executed_filings/
        3. Adds entry to executed_filings/index.json
        4. Marks document as is_filed=True, is_locked=True
        5. Document appears in both tabs (read-only)
        """
        doc = self.storage.get_by_id(doc_id)
        if not doc:
            return

        # Already filed?
        if doc.is_filed:
            QMessageBox.information(
                self, "Already Filed",
                f"'{doc.name}' is already marked as filed."
            )
            return

        # Show the filing dialog
        dialog = FileDocumentDialog(
            doc_name=doc.name,
            doc_title=doc.custom_title,
            case_id=doc.case_id or "178",
            parent=self
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # Get values from dialog
        filing_date = dialog.filing_date
        docket_number = dialog.docket_number

        try:
            # Generate the full document content (caption + body + signature)
            full_content = self._generate_filed_document_text(doc)

            # Create filenames
            case_id = doc.case_id or "178"
            title_part = doc.custom_title or doc.name
            # Clean the title for filename
            safe_title = "".join(c for c in title_part if c.isalnum() or c in " -_").strip()
            txt_filename = f"{case_id} {safe_title}.txt"
            pdf_filename = f"{case_id} {safe_title}.pdf"

            # Get executed_filings path
            ef_path = Path(self.storage.data_dir) / "executed_filings"
            ef_path.mkdir(exist_ok=True)

            # Write .txt file
            txt_path = ef_path / txt_filename
            txt_path.write_text(full_content, encoding="utf-8")

            # Generate PDF using existing PDF export
            pdf_path = ef_path / pdf_filename
            self._generate_filed_pdf(doc, pdf_path)

            # Update index.json
            index_path = ef_path / "index.json"
            import json
            from datetime import datetime

            if index_path.exists():
                with open(index_path, "r", encoding="utf-8") as f:
                    index_data = json.load(f)
            else:
                index_data = {"filings": [], "folders": []}

            # Create filing entry with link back to Editor document
            filing_entry = {
                "id": f"ef-{doc.id}",
                "case_id": case_id,
                "title": doc.custom_title or doc.name,
                "filename": pdf_filename,
                "txt_filename": txt_filename,
                "docket_number": docket_number or None,
                "date_filed": filing_date,
                "date_created": datetime.now().isoformat(),
                "status": "filed",
                "source_document_id": doc.id,  # Link back to Editor doc
                "notes": f"Filed from Editor document: {doc.name}"
            }
            index_data["filings"].append(filing_entry)

            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(index_data, f, indent=2)

            # Update the document
            doc.is_filed = True
            doc.is_locked = True
            doc.filed_date = filing_date
            doc.docket_number = docket_number
            doc.executed_filing_id = filing_entry["id"]
            self.storage.save(doc)

            # Update current doc if it's the one we just filed
            if self._current_saved_doc and self._current_saved_doc.id == doc_id:
                self._current_saved_doc = doc
                # Make editor read-only
                self.text_editor.setReadOnly(True)

            # Refresh UI
            self._refresh_document_list()
            self._refresh_executed_filings()

            QMessageBox.information(
                self, "Document Filed",
                f"'{doc.name}' has been marked as filed.\n\n"
                f"Files generated:\n"
                f"• {txt_filename}\n"
                f"• {pdf_filename}\n\n"
                f"The document is now read-only and appears in both\n"
                f"the Editor tab and Executed Filings tab."
            )

        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to mark document as filed:\n{str(e)}"
            )

    def _on_unfile_document(self, doc_id: str):
        """
        Remove the 'filed' status from a document.

        This unlocks the document for editing but does NOT delete
        the generated files from executed_filings/.
        """
        doc = self.storage.get_by_id(doc_id)
        if not doc:
            return

        if not doc.is_filed:
            return

        result = QMessageBox.question(
            self,
            "Unfile Document",
            f"Are you sure you want to unfile '{doc.name}'?\n\n"
            "This will:\n"
            "• Unlock the document for editing\n"
            "• Remove it from the Executed Filings tab\n\n"
            "Note: The generated .txt and .pdf files will NOT be deleted.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if result != QMessageBox.StandardButton.Yes:
            return

        try:
            # Remove from index.json
            ef_path = Path(self.storage.data_dir) / "executed_filings"
            index_path = ef_path / "index.json"

            if index_path.exists() and doc.executed_filing_id:
                import json
                with open(index_path, "r", encoding="utf-8") as f:
                    index_data = json.load(f)

                # Remove the filing entry
                index_data["filings"] = [
                    f for f in index_data["filings"]
                    if f.get("id") != doc.executed_filing_id
                ]

                with open(index_path, "w", encoding="utf-8") as f:
                    json.dump(index_data, f, indent=2)

            # Update document
            doc.is_filed = False
            doc.is_locked = False
            doc.filed_date = None
            doc.docket_number = None
            doc.executed_filing_id = None
            self.storage.save(doc)

            # Update current doc if it's the one we just unfiled
            if self._current_saved_doc and self._current_saved_doc.id == doc_id:
                self._current_saved_doc = doc
                # Make editor editable again
                self.text_editor.setReadOnly(False)

            # Refresh UI
            self._refresh_document_list()
            self._refresh_executed_filings()

            QMessageBox.information(
                self, "Document Unfiled",
                f"'{doc.name}' has been unfiled and is now editable."
            )

        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to unfile document:\n{str(e)}"
            )

    def _generate_filed_document_text(self, doc: SavedDocument) -> str:
        """
        Generate the full document text for the filed .txt file.

        This generates a simple text file with title and body content.
        The full formatted version (with caption/signature) is in the PDF.
        """
        lines = []

        # Add title
        if doc.custom_title:
            lines.append(doc.custom_title.upper())
            lines.append("")
            lines.append("=" * 60)
            lines.append("")

        # Add document name if no custom title
        elif doc.name:
            lines.append(doc.name.upper())
            lines.append("")
            lines.append("=" * 60)
            lines.append("")

        # Add filing metadata
        lines.append(f"Case: {doc.case_id or '178'}")
        lines.append(f"Filed: {doc.filed_date or date.today().isoformat()}")
        if doc.docket_number:
            lines.append(f"Docket: {doc.docket_number}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("")

        # Add body content
        lines.append(doc.text_content)

        return "\n".join(lines)

    def _generate_filed_pdf(self, doc: SavedDocument, pdf_path: Path):
        """
        Generate a PDF for the filed document.

        Uses the existing PDF export functionality with current editor state.
        """
        try:
            # Use existing PDF export with current document state
            # The document should already have caption/signature from editor
            generate_pdf(
                output_path=str(pdf_path),
                document_title=doc.custom_title or doc.name,
                caption=self.document.caption if self.document else CaseCaption(),
                signature_block=self.document.signature if self.document else SignatureBlock(),
                paragraphs=list(self.document.paragraphs.values()) if self.document else [],
                sections=self.document.sections if self.document else [],
                global_spacing=self._global_spacing,
                filing_date=doc.filed_date or date.today().isoformat(),
                include_certificate=True
            )
        except Exception as e:
            # If PDF generation fails, create a simple text-based PDF
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas

            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            c.setFont("Times-Roman", 12)

            # Title
            title = doc.custom_title or doc.name
            c.drawCentredString(306, 750, title.upper())
            c.line(72, 740, 540, 740)

            # Filing info
            y = 720
            c.drawString(72, y, f"Case: {doc.case_id or '178'}")
            y -= 15
            c.drawString(72, y, f"Filed: {doc.filed_date or date.today().isoformat()}")
            if doc.docket_number:
                y -= 15
                c.drawString(72, y, f"Docket: {doc.docket_number}")

            y -= 30

            # Body text (wrap lines)
            text = doc.text_content
            lines = text.split('\n')
            for line in lines:
                if y < 72:
                    c.showPage()
                    c.setFont("Times-Roman", 12)
                    y = 750
                c.drawString(72, y, line[:80])  # Truncate long lines
                y -= 15

            c.save()

    def _refresh_executed_filings(self):
        """Refresh the Executed Filings tab display."""
        # This method should already exist - if not, we'll handle the call gracefully
        if hasattr(self, '_load_executed_filings'):
            self._load_executed_filings()

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
        """Parse the editor text into paragraphs (each line = one paragraph).

        Section tags like <SECTION>I. PARTIES</SECTION> are detected and create
        sections in the tree. They do not count as paragraphs.

        Subsection tags like <SUBSECTION>a. Background</SUBSECTION> are also supported.
        """
        text = self.text_editor.toPlainText()
        lines = text.split("\n")

        # Clear all tracking data - sections are now parsed from text
        self.document.paragraphs.clear()
        self._para_line_map.clear()
        self._section_starts.clear()
        self._section_line_map.clear()
        self._all_sections.clear()

        para_num = 1
        # Queue of pending sections: (section, line_idx, is_subsection, parent_section_id)
        pending_sections: list[tuple[Section, int, bool, str | None]] = []
        # Track current section ID for subsection parenting
        current_section_id: str | None = None

        # Track accumulated paragraph text
        accumulated_text = ""
        accumulated_line_idx = 0
        # Track consecutive <line> tags for extra spacing
        line_tag_count = 0
        accumulated_extra_lines = 0  # Extra lines for current paragraph

        for line_idx, line in enumerate(lines):
            cleaned = line.strip()

            # Check if this is a <line> tag = paragraph break
            # Multiple <line> tags add extra spacing: <line><line> = 1 extra line
            if cleaned.lower() == '<line>':
                # Flush any accumulated text as a paragraph
                if accumulated_text:
                    para = Paragraph(
                        number=para_num,
                        text=accumulated_text,
                        section_id="",
                        extra_lines_before=accumulated_extra_lines  # Use saved value
                    )
                    self.document.paragraphs[para_num] = para
                    self._para_line_map[para_num] = accumulated_line_idx

                    # Assign pending sections to this paragraph
                    for section, section_line, is_subsection, parent_id in pending_sections:
                        if not is_subsection:
                            self._section_starts[para_num] = section
                            current_section_id = section.id
                        self._section_line_map[section.id] = section_line
                        display_letter = section.id.split("-")[-1] if is_subsection else section.id
                        self._all_sections.append((section, para_num, is_subsection, parent_id, display_letter))
                    pending_sections.clear()

                    para_num += 1
                    accumulated_text = ""
                    accumulated_extra_lines = 0  # Reset after flush
                # Count consecutive <line> tags for NEXT paragraph's extra spacing
                line_tag_count += 1
                continue

            if not cleaned:
                # Empty line - same as <line>, creates paragraph break
                if accumulated_text:
                    para = Paragraph(
                        number=para_num,
                        text=accumulated_text,
                        section_id="",
                        extra_lines_before=accumulated_extra_lines  # Use saved value
                    )
                    self.document.paragraphs[para_num] = para
                    self._para_line_map[para_num] = accumulated_line_idx

                    # Assign pending sections to this paragraph
                    for section, section_line, is_subsection, parent_id in pending_sections:
                        if not is_subsection:
                            self._section_starts[para_num] = section
                            current_section_id = section.id
                        self._section_line_map[section.id] = section_line
                        display_letter = section.id.split("-")[-1] if is_subsection else section.id
                        self._all_sections.append((section, para_num, is_subsection, parent_id, display_letter))
                    pending_sections.clear()

                    para_num += 1
                    accumulated_text = ""
                    accumulated_extra_lines = 0  # Reset after flush
                # Count empty lines as extra spacing too
                line_tag_count += 1
                continue

            # Check if this line is a section tag
            match = self.SECTION_TAG_PATTERN.match(cleaned)
            if match:
                # Flush accumulated text before section
                if accumulated_text:
                    para = Paragraph(number=para_num, text=accumulated_text, section_id="", extra_lines_before=accumulated_extra_lines)
                    self.document.paragraphs[para_num] = para
                    self._para_line_map[para_num] = accumulated_line_idx
                    for section, section_line, is_subsection, parent_id in pending_sections:
                        if not is_subsection:
                            self._section_starts[para_num] = section
                            current_section_id = section.id
                        self._section_line_map[section.id] = section_line
                        display_letter = section.id.split("-")[-1] if is_subsection else section.id
                        self._all_sections.append((section, para_num, is_subsection, parent_id, display_letter))
                    pending_sections.clear()
                    para_num += 1
                    accumulated_text = ""
                    accumulated_extra_lines = 0  # Reset after flush

                # Parse section content: "I. PARTIES" or "II. JURISDICTION"
                section_content = match.group(1).strip()

                # Try to parse Roman numeral and title
                parts = section_content.split(".", 1)
                if len(parts) == 2:
                    numeral = parts[0].strip()
                    title = parts[1].strip()
                else:
                    # No dot found, use whole content as title, auto-assign numeral
                    title = section_content
                    existing_numerals = [s.id for s in self._section_starts.values()]
                    for sec, _, _, _ in pending_sections:
                        existing_numerals.append(sec.id)
                    for numeral in self.ROMAN_NUMERALS:
                        if numeral not in existing_numerals:
                            break
                    else:
                        numeral = f"S{len(self._section_starts) + len(pending_sections) + 1}"

                # Create section (will be assigned to next paragraph)
                section = Section(id=numeral, title=title.upper())
                pending_sections.append((section, line_idx, False, None))  # Sections have no parent
                current_section_id = numeral  # Update current section for subsections
                # Reset spacing - sections act as boundaries (no carry-over from before)
                line_tag_count = 0
                accumulated_extra_lines = 0
                continue  # Skip paragraph creation for section tag

            # Check if this line is a subsection tag
            subsection_match = self.SUBSECTION_TAG_PATTERN.match(cleaned)
            if subsection_match:
                # Flush accumulated text before subsection
                if accumulated_text:
                    para = Paragraph(number=para_num, text=accumulated_text, section_id="", extra_lines_before=accumulated_extra_lines)
                    self.document.paragraphs[para_num] = para
                    self._para_line_map[para_num] = accumulated_line_idx
                    for section, section_line, is_subsection, parent_id in pending_sections:
                        if not is_subsection:
                            self._section_starts[para_num] = section
                            current_section_id = section.id
                        self._section_line_map[section.id] = section_line
                        display_letter = section.id.split("-")[-1] if is_subsection else section.id
                        self._all_sections.append((section, para_num, is_subsection, parent_id, display_letter))
                    pending_sections.clear()
                    para_num += 1
                    accumulated_text = ""
                    accumulated_extra_lines = 0  # Reset after flush
                # Subsections are displayed but don't affect paragraph numbering
                subsection_content = subsection_match.group(1).strip()
                # Create section for display with uppercase letter
                parts = subsection_content.split(".", 1)
                if len(parts) == 2:
                    letter = parts[0].strip().upper()
                    title = parts[1].strip()
                else:
                    letter = "SUB"
                    title = subsection_content

                # Use composite ID to avoid collisions: "I-a", "II-a"
                parent = current_section_id
                if parent:
                    # Check pending sections for most recent section
                    for sec, _, is_sub, _ in reversed(pending_sections):
                        if not is_sub:
                            parent = sec.id
                            break
                unique_id = f"{parent}-{letter}" if parent else letter

                subsection = Section(id=unique_id, title=title.upper())
                pending_sections.append((subsection, line_idx, True, parent))
                # Reset spacing - subsections act as boundaries (no carry-over from before)
                line_tag_count = 0
                accumulated_extra_lines = 0
                continue

            # Each text line starts a new paragraph
            # If there was accumulated text, flush it first (shouldn't happen normally)
            if accumulated_text:
                para = Paragraph(
                    number=para_num,
                    text=accumulated_text,
                    section_id="",
                    extra_lines_before=accumulated_extra_lines
                )
                self.document.paragraphs[para_num] = para
                self._para_line_map[para_num] = accumulated_line_idx
                for section, section_line, is_subsection, parent_id in pending_sections:
                    if not is_subsection:
                        self._section_starts[para_num] = section
                        current_section_id = section.id
                    self._section_line_map[section.id] = section_line
                    display_letter = section.id.split("-")[-1] if is_subsection else section.id
                    self._all_sections.append((section, para_num, is_subsection, parent_id, display_letter))
                pending_sections.clear()
                para_num += 1
                accumulated_extra_lines = 0  # Reset after flush

            # THE KEY FIX: Save extra lines for THIS paragraph BEFORE resetting
            # First <line> = normal break (extra=0), two <line> = skip 1 line (extra=1), etc.
            accumulated_extra_lines = max(0, line_tag_count - 1)
            accumulated_text = cleaned
            accumulated_line_idx = line_idx
            line_tag_count = 0  # Reset for next paragraph

        # Flush any remaining accumulated text as final paragraph
        if accumulated_text:
            para = Paragraph(
                number=para_num,
                text=accumulated_text,
                section_id="",
                extra_lines_before=accumulated_extra_lines
            )
            self.document.paragraphs[para_num] = para
            self._para_line_map[para_num] = accumulated_line_idx

            # Assign pending sections to this paragraph
            for section, section_line, is_subsection, parent_id in pending_sections:
                if not is_subsection:
                    self._section_starts[para_num] = section
                    current_section_id = section.id
                self._section_line_map[section.id] = section_line
                display_letter = section.id.split("-")[-1] if is_subsection else section.id
                self._all_sections.append((section, para_num, is_subsection, parent_id, display_letter))
            pending_sections.clear()

        # Handle sections/subsections at end of document with no following paragraphs
        # These would otherwise be lost in pending_sections
        for section, section_line, is_subsection, parent_id in pending_sections:
            self._section_line_map[section.id] = section_line
            display_letter = section.id.split("-")[-1] if is_subsection else section.id
            # Use para_num=0 to indicate no following paragraph
            self._all_sections.append((section, 0, is_subsection, parent_id, display_letter))

        # Build paragraph boundaries for highlighting annotations
        # Map para_num -> (start_pos, end_pos) in the text
        paragraph_boundaries = []
        current_pos = 0
        for line_idx, line in enumerate(lines):
            cleaned = line.strip()
            # Skip special tags - they're not paragraphs
            if cleaned.lower() == '<line>' or not cleaned:
                current_pos += len(line) + 1  # +1 for newline
                continue
            if self.SECTION_TAG_PATTERN.match(cleaned):
                current_pos += len(line) + 1
                continue
            if self.SUBSECTION_TAG_PATTERN.match(cleaned):
                current_pos += len(line) + 1
                continue
            # This is a paragraph line
            start_pos = current_pos
            end_pos = current_pos + len(line)
            paragraph_boundaries.append((start_pos, end_pos))
            current_pos = end_pos + 1  # +1 for newline

        # Update text editor with boundaries for highlighting
        self.text_editor.update_paragraph_boundaries(paragraph_boundaries)

        # Sync annotations - unlink notes for deleted paragraphs
        total_paragraphs = len(paragraph_boundaries)
        changed = False
        for annotation in self.text_editor.get_annotations():
            if annotation.is_linked and annotation.paragraph_number > total_paragraphs:
                annotation.unlink()
                changed = True
            elif annotation.is_linked and annotation.paragraph_number in self.document.paragraphs:
                # Update preview text
                para_text = self.document.paragraphs[annotation.paragraph_number].text
                new_preview = para_text[:50] + ("..." if len(para_text) > 50 else "")
                if annotation.paragraph_preview != new_preview:
                    annotation.paragraph_preview = new_preview
                    changed = True

        if changed:
            self._refresh_annotations_list()

        self._update_paragraph_highlights()

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
        """Update the section tree widget with current paragraphs grouped by sections/subsections."""
        self.section_tree.clear()

        count = len(self.document.paragraphs)
        section_count = len([s for s in self._all_sections if not s[2]])  # Count non-subsections
        subsection_count = len([s for s in self._all_sections if s[2]])
        header_text = f"Section Tree ({count} para, {section_count} sec"
        if subsection_count > 0:
            header_text += f", {subsection_count} sub"
        header_text += ")"
        self.section_tree_header.setText(header_text)

        if not self.document.paragraphs:
            return

        para_nums = sorted(self.document.paragraphs.keys())
        current_section_item = None
        current_subsection_item = None

        # Build a map of para_num -> list of (section, is_subsection, display_letter)
        para_sections: dict[int, list[tuple[Section, bool, str]]] = {}
        for section, para_num, is_subsection, parent_id, display_letter in self._all_sections:
            if para_num not in para_sections:
                para_sections[para_num] = []
            para_sections[para_num].append((section, is_subsection, display_letter))

        for para_num in para_nums:
            para = self.document.paragraphs[para_num]

            # Check if this paragraph has sections/subsections
            if para_num in para_sections:
                for section, is_subsection, display_letter in para_sections[para_num]:
                    # Use display_letter for showing (e.g., "a" instead of "I-a")
                    section_text = f"{display_letter}. {section.title}"

                    if is_subsection:
                        # Create subsection item (nested under current section)
                        subsection_item = QTreeWidgetItem([section_text])
                        subsection_item.setData(0, Qt.ItemDataRole.UserRole, ("subsection", section.id))

                        font = subsection_item.font(0)
                        font.setItalic(True)
                        subsection_item.setFont(0, font)

                        if current_section_item is not None:
                            current_section_item.addChild(subsection_item)
                            subsection_item.setExpanded(True)
                        else:
                            self.section_tree.addTopLevelItem(subsection_item)
                            subsection_item.setExpanded(True)

                        current_subsection_item = subsection_item
                    else:
                        # Create section item (top level)
                        current_section_item = QTreeWidgetItem([section_text])
                        current_section_item.setData(0, Qt.ItemDataRole.UserRole, ("section", para_num))

                        font = current_section_item.font(0)
                        font.setBold(True)
                        current_section_item.setFont(0, font)

                        self.section_tree.addTopLevelItem(current_section_item)
                        current_section_item.setExpanded(True)
                        current_subsection_item = None  # Reset subsection

            # Create paragraph item
            preview = para.get_display_text(40)
            para_text = f"{para.number}. {preview}"
            para_item = QTreeWidgetItem([para_text])
            para_item.setData(0, Qt.ItemDataRole.UserRole, ("para", para_num))

            # Add to appropriate parent
            if current_subsection_item is not None:
                current_subsection_item.addChild(para_item)
            elif current_section_item is not None:
                current_section_item.addChild(para_item)
            else:
                self.section_tree.addTopLevelItem(para_item)

        # Display empty sections at end of document (para_num=0)
        if 0 in para_sections:
            for section, is_subsection, display_letter in para_sections[0]:
                section_text = f"{display_letter}. {section.title}"

                if is_subsection:
                    subsection_item = QTreeWidgetItem([section_text])
                    subsection_item.setData(0, Qt.ItemDataRole.UserRole, ("subsection", section.id))

                    font = subsection_item.font(0)
                    font.setItalic(True)
                    subsection_item.setFont(0, font)

                    if current_section_item is not None:
                        current_section_item.addChild(subsection_item)
                    else:
                        self.section_tree.addTopLevelItem(subsection_item)
                else:
                    section_item = QTreeWidgetItem([section_text + " (empty)"])
                    section_item.setData(0, Qt.ItemDataRole.UserRole, ("section", 0))

                    font = section_item.font(0)
                    font.setBold(True)
                    section_item.setFont(0, font)

                    self.section_tree.addTopLevelItem(section_item)
                    current_section_item = section_item

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

            # Add subsection option if paragraph is under a section
            section_for_para = self._get_section_for_para(para_num)
            if section_for_para:
                menu.addSeparator()
                # Find the section's starting paragraph number
                section_start_para = None
                for start_para, sec in self._section_starts.items():
                    if sec.id == section_for_para.id:
                        section_start_para = start_para
                        break
                if section_start_para is not None:
                    add_sub_action = menu.addAction(f"Add subsection under {section_for_para.id}. {section_for_para.title}...")
                    add_sub_action.triggered.connect(lambda: self._create_subsection_at(section_start_para))

            # Add convert options
            menu.addSeparator()
            convert_section_action = menu.addAction("Convert to section header")
            convert_section_action.triggered.connect(lambda: self._convert_para_to_section(para_num))

            convert_subsection_action = menu.addAction("Convert to subsection header")
            convert_subsection_action.triggered.connect(lambda: self._convert_para_to_subsection(para_num))

            # Add note option
            menu.addSeparator()
            notes_for_para = self.text_editor.get_annotations_for_paragraph(para_num)
            if notes_for_para:
                notes_label = f"Notes ({len(notes_for_para)})"
                view_notes_action = menu.addAction(notes_label)
                view_notes_action.triggered.connect(lambda checked=False, p=para_num: self._show_notes_for_paragraph(p))
            add_note_action = menu.addAction("Add Note...")
            add_note_action.triggered.connect(lambda checked=False, p=para_num: self._add_note_for_paragraph(p))

        elif item_type == "section":
            section_start_para = item_id

            add_subsection_action = menu.addAction("Add subsection...")
            add_subsection_action.triggered.connect(lambda: self._create_subsection_at(section_start_para))

            menu.addSeparator()

            remove_action = menu.addAction("Remove section")
            remove_action.triggered.connect(lambda: self._remove_section(section_start_para))

            rename_action = menu.addAction("Rename section...")
            rename_action.triggered.connect(lambda: self._rename_section(section_start_para))

            spacing_action = menu.addAction("Spacing...")
            spacing_action.triggered.connect(lambda: self._edit_section_spacing(section_start_para))

        elif item_type == "subsection":
            subsection_id = item_id  # Composite ID like "I-a"

            remove_action = menu.addAction("Remove subsection")
            remove_action.triggered.connect(lambda: self._remove_subsection(subsection_id))

            rename_action = menu.addAction("Rename subsection...")
            rename_action.triggered.connect(lambda: self._rename_subsection(subsection_id))

        menu.exec(self.section_tree.viewport().mapToGlobal(position))

    def _create_section_at(self, para_num: int):
        """Create a new section starting at the given paragraph.

        Inserts a <SECTION>...</SECTION> tag line before the paragraph in the editor.
        The text change will trigger parsing which creates the section.
        """
        name, ok = QInputDialog.getText(
            self, "Create Section",
            "Section name (e.g., PARTIES, JURISDICTION):"
        )
        if not ok or not name.strip():
            return

        name = name.strip().upper()

        # Find next available Roman numeral
        existing_numerals = [s.id for s in self._section_starts.values()]
        for numeral in self.ROMAN_NUMERALS:
            if numeral not in existing_numerals:
                break
        else:
            numeral = f"S{len(self._section_starts) + 1}"

        # Build the section tag text
        section_tag = f"<SECTION>{numeral}. {name}</SECTION>"

        # Find the line position of the target paragraph
        line_idx = self._para_line_map.get(para_num)
        if line_idx is None:
            return

        # Insert the section tag before the paragraph
        text = self.text_editor.toPlainText()
        lines = text.split("\n")

        # Calculate character position for the start of the target line
        char_pos = sum(len(lines[i]) + 1 for i in range(line_idx))

        # Insert section tag with newline
        self._updating = True
        try:
            cursor = self.text_editor.textCursor()
            cursor.setPosition(char_pos)
            cursor.insertText(section_tag + "\n")
        finally:
            self._updating = False

        # Trigger re-parse (this will create the section from the tag)
        self._on_text_changed()

    def _create_subsection_at(self, para_num: int):
        """Create a new subsection for the section starting at para_num.

        Inserts a <SUBSECTION>...</SUBSECTION> tag line AFTER the section tag in the editor.
        """
        # Get the section this subsection belongs to
        section = self._section_starts.get(para_num)
        if not section:
            return  # No section at this paragraph

        # Get section's line position
        section_line_idx = self._section_line_map.get(section.id)
        if section_line_idx is None:
            return

        name, ok = QInputDialog.getText(
            self, "Create Subsection",
            "Subsection name (e.g., Background, The Contract):"
        )
        if not ok or not name.strip():
            return

        name = name.strip().upper()

        # Find next available lowercase letter for THIS section
        # Get display letters (last part of composite ID) for subsections in this section
        existing_letters = []
        for s in self._all_sections:
            if s[2] and s[3] == section.id:  # is_subsection=True and same parent
                existing_letters.append(s[4])  # display_letter

        letters = "abcdefghijklmnopqrstuvwxyz"
        for letter in letters:
            if letter not in existing_letters:
                break
        else:
            letter = f"sub{len(existing_letters) + 1}"

        # Build the subsection tag text
        subsection_tag = f"<SUBSECTION>{letter}. {name}</SUBSECTION>"

        # Find the last subsection line for this section (to insert after it)
        # This ensures new subsections appear AFTER existing ones, not before
        last_subsection_line = section_line_idx
        for s in self._all_sections:
            if s[2] and s[3] == section.id:  # is_subsection=True and same parent
                sub_line = self._section_line_map.get(s[0].id)
                if sub_line is not None and sub_line > last_subsection_line:
                    last_subsection_line = sub_line

        # Insert AFTER the last subsection (or section if none exist)
        text = self.text_editor.toPlainText()
        lines = text.split("\n")

        # Calculate character position for the line AFTER the last subsection/section
        insert_line = last_subsection_line + 1
        char_pos = sum(len(lines[i]) + 1 for i in range(insert_line))

        # Insert subsection tag with newline
        self._updating = True
        try:
            cursor = self.text_editor.textCursor()
            cursor.setPosition(char_pos)
            cursor.insertText(subsection_tag + "\n")
        finally:
            self._updating = False

        # Trigger re-parse
        self._on_text_changed()

    def _assign_to_section(self, para_num: int, section: Section):
        """Move section to start at a different paragraph.

        Removes the old section tag and inserts it before the new paragraph.
        """
        # Find current section tag line
        old_line_idx = self._section_line_map.get(section.id)
        new_line_idx = self._para_line_map.get(para_num)

        if old_line_idx is None or new_line_idx is None:
            return

        text = self.text_editor.toPlainText()
        lines = text.split("\n")

        if old_line_idx >= len(lines) or new_line_idx >= len(lines):
            return

        # Build section tag
        section_tag = f"<SECTION>{section.id}. {section.title}</SECTION>"

        self._updating = True
        try:
            # First, remove the old section tag
            char_start = sum(len(lines[i]) + 1 for i in range(old_line_idx))
            char_end = char_start + len(lines[old_line_idx]) + 1  # +1 for newline

            cursor = self.text_editor.textCursor()
            cursor.setPosition(char_start)
            cursor.setPosition(char_end, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()

            # Recalculate new line index after removal
            # If old was before new, new index shifts up by 1
            if old_line_idx < new_line_idx:
                new_line_idx -= 1

            # Reget text after removal
            text = self.text_editor.toPlainText()
            lines = text.split("\n")

            # Insert at new location
            char_pos = sum(len(lines[i]) + 1 for i in range(new_line_idx))
            cursor = self.text_editor.textCursor()
            cursor.setPosition(char_pos)
            cursor.insertText(section_tag + "\n")
        finally:
            self._updating = False

        # Trigger re-parse
        self._on_text_changed()

    def _remove_from_section(self, para_num: int):
        """Remove section that starts at this paragraph (same as _remove_section)."""
        self._remove_section(para_num)

    def _remove_section(self, section_start_para: int):
        """Remove a section entirely by removing its tag from the editor."""
        if section_start_para not in self._section_starts:
            return

        section = self._section_starts[section_start_para]
        line_idx = self._section_line_map.get(section.id)
        if line_idx is None:
            return

        # Remove the section tag line from the editor
        text = self.text_editor.toPlainText()
        lines = text.split("\n")

        if line_idx >= len(lines):
            return

        # Calculate character positions
        char_start = sum(len(lines[i]) + 1 for i in range(line_idx))
        char_end = char_start + len(lines[line_idx]) + 1  # +1 for newline

        self._updating = True
        try:
            cursor = self.text_editor.textCursor()
            cursor.setPosition(char_start)
            cursor.setPosition(char_end, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
        finally:
            self._updating = False

        # Trigger re-parse
        self._on_text_changed()

    def _rename_section(self, section_start_para: int):
        """Rename a section by updating its tag in the editor."""
        if section_start_para not in self._section_starts:
            return

        section = self._section_starts[section_start_para]
        name, ok = QInputDialog.getText(
            self, "Rename Section",
            "New section name:",
            text=section.title
        )
        if not ok or not name.strip():
            return

        new_name = name.strip().upper()
        line_idx = self._section_line_map.get(section.id)
        if line_idx is None:
            return

        # Update the section tag in the editor
        text = self.text_editor.toPlainText()
        lines = text.split("\n")

        if line_idx >= len(lines):
            return

        # Build new section tag
        new_tag = f"<SECTION>{section.id}. {new_name}</SECTION>"

        # Calculate character positions
        char_start = sum(len(lines[i]) + 1 for i in range(line_idx))
        char_end = char_start + len(lines[line_idx])

        self._updating = True
        try:
            cursor = self.text_editor.textCursor()
            cursor.setPosition(char_start)
            cursor.setPosition(char_end, QTextCursor.MoveMode.KeepAnchor)
            cursor.insertText(new_tag)
        finally:
            self._updating = False

        # Trigger re-parse
        self._on_text_changed()

    def _remove_subsection(self, subsection_id: str):
        """Remove a subsection by removing its tag from the editor."""
        line_idx = self._section_line_map.get(subsection_id)
        if line_idx is None:
            return

        text = self.text_editor.toPlainText()
        lines = text.split("\n")

        if line_idx >= len(lines):
            return

        # Calculate character positions
        char_start = sum(len(lines[i]) + 1 for i in range(line_idx))
        char_end = char_start + len(lines[line_idx]) + 1  # +1 for newline

        self._updating = True
        try:
            cursor = self.text_editor.textCursor()
            cursor.setPosition(char_start)
            cursor.setPosition(char_end, QTextCursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
        finally:
            self._updating = False

        # Trigger re-parse
        self._on_text_changed()

    def _rename_subsection(self, subsection_id: str):
        """Rename a subsection by updating its tag in the editor."""
        line_idx = self._section_line_map.get(subsection_id)
        if line_idx is None:
            return

        # Get current title and display letter from _all_sections
        current_title = ""
        display_letter = subsection_id.split("-")[-1] if "-" in subsection_id else subsection_id
        for s in self._all_sections:
            if s[0].id == subsection_id:
                current_title = s[0].title
                break

        name, ok = QInputDialog.getText(
            self, "Rename Subsection",
            "New subsection name:",
            text=current_title
        )
        if not ok or not name.strip():
            return

        new_name = name.strip().upper()

        text = self.text_editor.toPlainText()
        lines = text.split("\n")

        if line_idx >= len(lines):
            return

        # Build new subsection tag
        new_tag = f"<SUBSECTION>{display_letter}. {new_name}</SUBSECTION>"

        # Calculate character positions
        char_start = sum(len(lines[i]) + 1 for i in range(line_idx))
        char_end = char_start + len(lines[line_idx])

        self._updating = True
        try:
            cursor = self.text_editor.textCursor()
            cursor.setPosition(char_start)
            cursor.setPosition(char_end, QTextCursor.MoveMode.KeepAnchor)
            cursor.insertText(new_tag)
        finally:
            self._updating = False

        # Trigger re-parse
        self._on_text_changed()

    def _convert_para_to_section(self, para_num: int):
        """Convert a paragraph into a section header."""
        if para_num not in self.document.paragraphs:
            return

        para = self.document.paragraphs[para_num]
        line_idx = self._para_line_map.get(para_num)
        if line_idx is None:
            return

        # Get paragraph text to use as section title
        para_text = para.text.strip().upper()

        # Find next available Roman numeral
        existing_numerals = [s.id for s in self._section_starts.values()]
        for numeral in self.ROMAN_NUMERALS:
            if numeral not in existing_numerals:
                break
        else:
            numeral = f"S{len(self._section_starts) + 1}"

        # Build section tag
        section_tag = f"<SECTION>{numeral}. {para_text}</SECTION>"

        # Replace the paragraph with section tag
        text = self.text_editor.toPlainText()
        lines = text.split("\n")

        if line_idx >= len(lines):
            return

        # Calculate character positions
        char_start = sum(len(lines[i]) + 1 for i in range(line_idx))
        char_end = char_start + len(lines[line_idx])

        self._updating = True
        try:
            cursor = self.text_editor.textCursor()
            cursor.setPosition(char_start)
            cursor.setPosition(char_end, QTextCursor.MoveMode.KeepAnchor)
            cursor.insertText(section_tag)
        finally:
            self._updating = False

        # Trigger re-parse
        self._on_text_changed()

    def _convert_para_to_subsection(self, para_num: int):
        """Convert a paragraph into a subsection header."""
        if para_num not in self.document.paragraphs:
            return

        para = self.document.paragraphs[para_num]
        line_idx = self._para_line_map.get(para_num)
        if line_idx is None:
            return

        # Get the section this paragraph belongs to
        section = self._get_section_for_para(para_num)
        parent_section_id = section.id if section else None

        # Find next available letter for this section
        existing_letters = []
        for s in self._all_sections:
            if s[2] and s[3] == parent_section_id:  # is_subsection and same parent
                existing_letters.append(s[4])

        letters = "abcdefghijklmnopqrstuvwxyz"
        for letter in letters:
            if letter not in existing_letters:
                break
        else:
            letter = f"sub{len(existing_letters) + 1}"

        # Get paragraph text to use as subsection title
        para_text = para.text.strip().upper()

        # Build subsection tag
        subsection_tag = f"<SUBSECTION>{letter}. {para_text}</SUBSECTION>"

        # Replace the paragraph with subsection tag
        text = self.text_editor.toPlainText()
        lines = text.split("\n")

        if line_idx >= len(lines):
            return

        # Calculate character positions
        char_start = sum(len(lines[i]) + 1 for i in range(line_idx))
        char_end = char_start + len(lines[line_idx])

        self._updating = True
        try:
            cursor = self.text_editor.textCursor()
            cursor.setPosition(char_start)
            cursor.setPosition(char_end, QTextCursor.MoveMode.KeepAnchor)
            cursor.insertText(subsection_tag)
        finally:
            self._updating = False

        # Trigger re-parse
        self._on_text_changed()

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
        """Handle click on tree item - highlight and scroll to paragraph or section in editor."""
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data:
            return

        item_type, item_id = item_data

        # Determine which line to highlight
        if item_type == "para":
            line_idx = self._para_line_map.get(item_id)
        elif item_type == "section":
            # item_id is the para_num where section starts
            section = self._section_starts.get(item_id)
            if section:
                line_idx = self._section_line_map.get(section.id)
            else:
                return
        elif item_type == "subsection":
            # item_id is the section.id (lowercase letter like "a", "b")
            line_idx = self._section_line_map.get(item_id)
        else:
            return

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
            # Use a fixed preview path so Preview.app can refresh the same file
            preview_path = Path(tempfile.gettempdir()) / "formarter_preview.pdf"

            # Generate PDF to the fixed preview path
            generate_pdf(
                self.document.paragraphs,
                self._section_starts,
                output_path=str(preview_path),
                global_spacing=self._global_spacing,
                caption=self.document.caption,
                signature=self.document.signature,
                document_title=self.document.title,
                all_sections=self._all_sections
            )

            # Open in system PDF viewer (Preview.app on macOS)
            if sys.platform == "darwin":
                # Close any existing Preview windows showing our preview file
                subprocess.run(["pkill", "-x", "Preview"], capture_output=True)
                # Small delay to ensure Preview has closed before reopening
                import time
                time.sleep(0.5)
                # Use explicit path to Preview.app to avoid error -600
                subprocess.run(["/usr/bin/open", "-a", "Preview", str(preview_path)], check=True)
            elif sys.platform == "win32":
                subprocess.run(["start", "", str(preview_path)], shell=True, check=True)
            else:
                subprocess.run(["xdg-open", str(preview_path)], check=True)

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
                document_title=self.document.title,
                all_sections=self._all_sections
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

        # Certificate of Service option
        cert_group = QGroupBox("Certificate of Service")
        cert_layout = QVBoxLayout(cert_group)

        self.include_certificate_cb = QCheckBox("Include Certificate of Service")
        self.include_certificate_cb.setChecked(getattr(signature, 'include_certificate', True))
        cert_layout.addWidget(self.include_certificate_cb)

        cert_label = QLabel(
            "<i>Uncheck for emergency/standalone signature page (no date, no certificate)</i>"
        )
        cert_label.setWordWrap(True)
        cert_label.setStyleSheet("color: #666; padding: 5px;")
        cert_layout.addWidget(cert_label)
        layout.addWidget(cert_group)

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
            include_certificate=self.include_certificate_cb.isChecked(),
        )


# ========== Library Dialog Classes ==========

class AddCaseDialog(QDialog):
    """Dialog for adding a new case to the library."""

    def __init__(self, case_library, parent=None):
        super().__init__(parent)
        self.case_library = case_library
        self.pdf_path = ""
        self.setWindowTitle("Add Case to Library")
        self.setMinimumWidth(500)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # PDF file selection
        file_group = QGroupBox("PDF File")
        file_layout = QHBoxLayout(file_group)

        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #666;")
        file_layout.addWidget(self.file_label, 1)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._on_browse)
        file_layout.addWidget(browse_btn)

        layout.addWidget(file_group)

        # Citation information
        citation_group = QGroupBox("Citation Information")
        form = QFormLayout(citation_group)

        self.case_name_edit = QLineEdit()
        self.case_name_edit.setPlaceholderText("e.g., Smith v. Jones")
        self.case_name_edit.textChanged.connect(self._update_preview)
        form.addRow("Case Name:", self.case_name_edit)

        self.volume_edit = QLineEdit()
        self.volume_edit.setPlaceholderText("e.g., 123")
        self.volume_edit.setMaximumWidth(80)
        self.volume_edit.textChanged.connect(self._update_preview)
        form.addRow("Volume:", self.volume_edit)

        self.reporter_combo = QComboBox()
        self.reporter_combo.setEditable(True)
        from .models.library_case import REPORTERS
        self.reporter_combo.addItems(REPORTERS)
        self.reporter_combo.currentTextChanged.connect(self._update_preview)
        form.addRow("Reporter:", self.reporter_combo)

        self.page_edit = QLineEdit()
        self.page_edit.setPlaceholderText("e.g., 456")
        self.page_edit.setMaximumWidth(80)
        self.page_edit.textChanged.connect(self._update_preview)
        form.addRow("Page:", self.page_edit)

        self.year_edit = QLineEdit()
        self.year_edit.setPlaceholderText("e.g., 2020")
        self.year_edit.setMaximumWidth(80)
        self.year_edit.textChanged.connect(self._update_preview)
        form.addRow("Year:", self.year_edit)

        self.court_combo = QComboBox()
        self.court_combo.setEditable(True)
        from .models.library_case import COURTS
        self.court_combo.addItems(COURTS)
        self.court_combo.currentTextChanged.connect(self._update_preview)
        form.addRow("Court:", self.court_combo)

        layout.addWidget(citation_group)

        # Organization
        org_group = QGroupBox("Organization")
        org_form = QFormLayout(org_group)

        self.category_combo = QComboBox()
        self.category_combo.addItem("-- No Category --", "")
        for cat in self.case_library.list_categories():
            self.category_combo.addItem(cat.name, cat.id)
        org_form.addRow("Category:", self.category_combo)

        self.keywords_edit = QLineEdit()
        self.keywords_edit.setPlaceholderText("e.g., qualified immunity, police misconduct")
        org_form.addRow("Keywords:", self.keywords_edit)

        layout.addWidget(org_group)

        # Citation preview
        preview_group = QGroupBox("Citation Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_label = QLabel("")
        self.preview_label.setStyleSheet("font-style: italic; color: #333; padding: 10px;")
        self.preview_label.setWordWrap(True)
        preview_layout.addWidget(self.preview_label)
        layout.addWidget(preview_group)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_browse(self):
        """Browse for a PDF file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select PDF File", "", "PDF Files (*.pdf)"
        )
        if file_path:
            self.pdf_path = file_path
            self.file_label.setText(Path(file_path).name)
            self.file_label.setStyleSheet("color: #333;")

            # Try to extract citation from PDF content first, then filename
            parsed = self.case_library.extract_citation_from_pdf(file_path)
            if parsed:
                self.case_name_edit.setText(parsed.get('case_name', ''))
                self.volume_edit.setText(parsed.get('volume', ''))
                self.reporter_combo.setCurrentText(parsed.get('reporter', ''))
                self.page_edit.setText(parsed.get('page', ''))
                if 'year' in parsed:
                    self.year_edit.setText(parsed['year'])
                if 'court' in parsed:
                    self.court_combo.setCurrentText(parsed['court'])

    def _update_preview(self):
        """Update the citation preview."""
        case_name = self.case_name_edit.text().strip()
        volume = self.volume_edit.text().strip()
        reporter = self.reporter_combo.currentText().strip()
        page = self.page_edit.text().strip()
        year = self.year_edit.text().strip()
        court = self.court_combo.currentText().strip()

        if case_name and volume and reporter and page:
            citation = f"{case_name}, {volume} {reporter} {page}"
            if court or year:
                paren_parts = []
                if court:
                    paren_parts.append(court)
                if year:
                    paren_parts.append(year)
                citation += f" ({' '.join(paren_parts)})"
            self.preview_label.setText(citation)
        else:
            self.preview_label.setText("(Enter citation details above)")

    def _on_accept(self):
        """Validate and accept the dialog."""
        if not self.pdf_path:
            QMessageBox.warning(self, "Missing PDF", "Please select a PDF file.")
            return

        case_name = self.case_name_edit.text().strip()
        volume = self.volume_edit.text().strip()
        reporter = self.reporter_combo.currentText().strip()
        page = self.page_edit.text().strip()

        if not all([case_name, volume, reporter, page]):
            QMessageBox.warning(
                self, "Missing Information",
                "Please fill in Case Name, Volume, Reporter, and Page."
            )
            return

        # Check for duplicate
        if self.case_library.is_duplicate(volume, reporter, page):
            QMessageBox.warning(
                self, "Duplicate Case",
                f"A case with citation {volume} {reporter} {page} already exists in the library."
            )
            return

        # Parse keywords
        keywords_text = self.keywords_edit.text().strip()
        keywords = [k.strip() for k in keywords_text.split(",") if k.strip()] if keywords_text else []

        # Add the case
        try:
            self.case_library.add_case(
                pdf_path=self.pdf_path,
                case_name=case_name,
                volume=volume,
                reporter=reporter,
                page=page,
                year=self.year_edit.text().strip(),
                court=self.court_combo.currentText().strip(),
                category_id=self.category_combo.currentData() or "",
                keywords=keywords
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add case: {e}")


class BatchImportDialog(QDialog):
    """Dialog for batch importing multiple PDFs."""

    def __init__(self, case_library, parent=None):
        super().__init__(parent)
        self.case_library = case_library
        self.pdf_paths = []
        self.setWindowTitle("Batch Import Cases")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # File selection
        file_layout = QHBoxLayout()

        select_btn = QPushButton("Select PDFs...")
        select_btn.clicked.connect(self._on_select_files)
        file_layout.addWidget(select_btn)

        self.file_count_label = QLabel("No files selected")
        self.file_count_label.setStyleSheet("color: #666;")
        file_layout.addWidget(self.file_count_label)

        file_layout.addStretch()

        layout.addLayout(file_layout)

        # Default category
        cat_layout = QHBoxLayout()
        cat_layout.addWidget(QLabel("Default Category:"))

        self.category_combo = QComboBox()
        self.category_combo.addItem("-- No Category --", "")
        for cat in self.case_library.list_categories():
            self.category_combo.addItem(cat.name, cat.id)
        cat_layout.addWidget(self.category_combo)

        cat_layout.addStretch()

        layout.addLayout(cat_layout)

        # Import queue list
        queue_label = QLabel("Import Queue:")
        queue_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(queue_label)

        self.queue_list = QListWidget()
        self.queue_list.setAlternatingRowColors(True)
        layout.addWidget(self.queue_list)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; margin-top: 5px;")
        layout.addWidget(self.status_label)

        # Buttons
        btn_layout = QHBoxLayout()

        import_btn = QPushButton("Import All Ready")
        import_btn.setStyleSheet("""
            QPushButton {
                background: #4a90d9;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #357abd;
            }
        """)
        import_btn.clicked.connect(self._on_import)
        btn_layout.addWidget(import_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        btn_layout.addStretch()

        layout.addLayout(btn_layout)

    def _on_select_files(self):
        """Select multiple PDF files."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select PDF Files", "", "PDF Files (*.pdf)"
        )
        if file_paths:
            self.pdf_paths = file_paths
            self.file_count_label.setText(f"{len(file_paths)} file(s) selected")
            self._analyze_files()

    def _analyze_files(self):
        """Analyze selected files and populate the queue."""
        self.queue_list.clear()

        ready_count = 0
        needs_info_count = 0
        duplicate_count = 0

        for pdf_path in self.pdf_paths:
            # Extract citation from PDF content first
            parsed = self.case_library.extract_citation_from_pdf(pdf_path)

            item = QListWidgetItem()

            if parsed:
                # Check for duplicate
                if self.case_library.is_duplicate(parsed['volume'], parsed['reporter'], parsed['page']):
                    item.setText(f"[DUPLICATE] {Path(pdf_path).name}")
                    item.setForeground(Qt.GlobalColor.gray)
                    duplicate_count += 1
                else:
                    citation = f"{parsed['case_name']}, {parsed['volume']} {parsed['reporter']} {parsed['page']}"
                    item.setText(f"[READY] {Path(pdf_path).name} -> {citation}")
                    item.setForeground(Qt.GlobalColor.darkGreen)
                    ready_count += 1
            else:
                item.setText(f"[NEEDS INFO] {Path(pdf_path).name}")
                item.setForeground(Qt.GlobalColor.darkYellow)
                needs_info_count += 1

            item.setData(Qt.ItemDataRole.UserRole, pdf_path)
            self.queue_list.addItem(item)

        self.status_label.setText(
            f"{ready_count} ready, {needs_info_count} need info, {duplicate_count} duplicates"
        )

    def _on_import(self):
        """Import all ready files."""
        if not self.pdf_paths:
            QMessageBox.warning(self, "No Files", "Please select PDF files first.")
            return

        default_category_id = self.category_combo.currentData() or ""

        result = self.case_library.batch_import(self.pdf_paths, default_category_id)

        # Show results
        msg = result.summary
        if result.successful:
            QMessageBox.information(self, "Import Complete", msg)
            self.accept()
        else:
            QMessageBox.warning(self, "Import Results", msg)


class EditTagsDialog(QDialog):
    """Dialog for editing case category and keywords."""

    def __init__(self, case_library, case, parent=None):
        super().__init__(parent)
        self.case_library = case_library
        self.case = case
        self.setWindowTitle(f"Edit Tags: {case.case_name}")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Citation display
        citation_label = QLabel(self.case.bluebook_citation)
        citation_label.setStyleSheet("font-style: italic; color: #333; padding: 10px; background: #f0f0f0; border-radius: 5px;")
        citation_label.setWordWrap(True)
        layout.addWidget(citation_label)

        # Category
        form = QFormLayout()

        self.category_combo = QComboBox()
        self.category_combo.addItem("-- No Category --", "")
        current_index = 0
        for i, cat in enumerate(self.case_library.list_categories()):
            self.category_combo.addItem(cat.name, cat.id)
            if cat.id == self.case.category_id:
                current_index = i + 1
        self.category_combo.setCurrentIndex(current_index)
        form.addRow("Category:", self.category_combo)

        # Keywords
        self.keywords_edit = QLineEdit()
        self.keywords_edit.setText(", ".join(self.case.keywords))
        self.keywords_edit.setPlaceholderText("e.g., qualified immunity, police misconduct")
        form.addRow("Keywords:", self.keywords_edit)

        layout.addLayout(form)

        # Keyword suggestions
        all_keywords = self.case_library.get_all_keywords()
        if all_keywords:
            suggest_label = QLabel("Existing keywords: " + ", ".join(all_keywords[:10]))
            suggest_label.setStyleSheet("color: #666; font-size: 11px;")
            suggest_label.setWordWrap(True)
            layout.addWidget(suggest_label)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        """Save the changes."""
        keywords_text = self.keywords_edit.text().strip()
        keywords = [k.strip() for k in keywords_text.split(",") if k.strip()] if keywords_text else []

        self.case_library.update_case(self.case.id, {
            'category_id': self.category_combo.currentData() or "",
            'keywords': keywords
        })
        self.accept()


# ========== Exhibit Bank Dialogs ==========

class ExhibitMetadataDialog(QDialog):
    """Dialog for entering exhibit metadata when adding new exhibit."""

    def __init__(self, parent, file_path: str, tags: list):
        super().__init__(parent)
        self.file_path = file_path
        self.available_tags = tags

        self.title = ""
        self.tags = []
        self.description = ""
        self.notes = ""
        self.source = ""

        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Add Exhibit")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # File info
        file_label = QLabel(f"File: {Path(self.file_path).name}")
        file_label.setStyleSheet("color: #666;")
        layout.addWidget(file_label)

        # Form
        form = QFormLayout()

        # Title (default to filename without extension)
        self.title_edit = QLineEdit()
        default_title = Path(self.file_path).stem.replace('_', ' ').replace('-', ' ')
        self.title_edit.setText(default_title)
        form.addRow("Title:", self.title_edit)

        # Tags (checkboxes)
        tags_widget = QWidget()
        tags_layout = QGridLayout(tags_widget)
        tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_checkboxes = {}
        for i, tag in enumerate(self.available_tags):
            cb = QCheckBox(tag.name)
            self.tag_checkboxes[tag.name] = cb
            tags_layout.addWidget(cb, i // 4, i % 4)
        form.addRow("Tags:", tags_widget)

        # Description
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(80)
        self.desc_edit.setPlaceholderText("Brief description of the exhibit...")
        form.addRow("Description:", self.desc_edit)

        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setPlaceholderText("Internal notes (not for court use)...")
        form.addRow("Notes:", self.notes_edit)

        # Source
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("e.g., Discovery Response, Deposition Exhibit...")
        form.addRow("Source:", self.source_edit)

        layout.addLayout(form)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        self.title = self.title_edit.text().strip() or Path(self.file_path).stem
        self.tags = [name for name, cb in self.tag_checkboxes.items() if cb.isChecked()]
        self.description = self.desc_edit.toPlainText().strip()
        self.notes = self.notes_edit.toPlainText().strip()
        self.source = self.source_edit.text().strip()
        self.accept()


class EditExhibitDialog(QDialog):
    """Dialog for editing exhibit metadata."""

    def __init__(self, parent, exhibit, tags: list):
        super().__init__(parent)
        self.exhibit = exhibit
        self.available_tags = tags

        self.title = exhibit.title
        self.tags = list(exhibit.tags)
        self.description = exhibit.description
        self.notes = exhibit.notes
        self.source = exhibit.source

        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Edit Exhibit")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # Form
        form = QFormLayout()

        # Title
        self.title_edit = QLineEdit()
        self.title_edit.setText(self.exhibit.title)
        form.addRow("Title:", self.title_edit)

        # Tags (checkboxes)
        tags_widget = QWidget()
        tags_layout = QGridLayout(tags_widget)
        tags_layout.setContentsMargins(0, 0, 0, 0)
        self.tag_checkboxes = {}
        for i, tag in enumerate(self.available_tags):
            cb = QCheckBox(tag.name)
            cb.setChecked(tag.name in self.exhibit.tags)
            self.tag_checkboxes[tag.name] = cb
            tags_layout.addWidget(cb, i // 4, i % 4)
        form.addRow("Tags:", tags_widget)

        # Description
        self.desc_edit = QTextEdit()
        self.desc_edit.setMaximumHeight(80)
        self.desc_edit.setText(self.exhibit.description)
        form.addRow("Description:", self.desc_edit)

        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        self.notes_edit.setText(self.exhibit.notes)
        form.addRow("Notes:", self.notes_edit)

        # Source
        self.source_edit = QLineEdit()
        self.source_edit.setText(self.exhibit.source)
        form.addRow("Source:", self.source_edit)

        layout.addLayout(form)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        self.title = self.title_edit.text().strip() or self.exhibit.title
        self.tags = [name for name, cb in self.tag_checkboxes.items() if cb.isChecked()]
        self.description = self.desc_edit.toPlainText().strip()
        self.notes = self.notes_edit.toPlainText().strip()
        self.source = self.source_edit.text().strip()
        self.accept()


class ManageExhibitTagsDialog(QDialog):
    """Dialog for managing exhibit tags."""

    def __init__(self, parent, exhibit_bank):
        super().__init__(parent)
        self.exhibit_bank = exhibit_bank
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Manage Tags")
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)

        layout = QVBoxLayout(self)

        # Tag list
        self.tag_list = QListWidget()
        self._refresh_tags()
        layout.addWidget(self.tag_list)

        # Add tag row
        add_layout = QHBoxLayout()
        self.new_tag_edit = QLineEdit()
        self.new_tag_edit.setPlaceholderText("New tag name...")
        add_layout.addWidget(self.new_tag_edit)

        add_btn = QPushButton("Add Tag")
        add_btn.clicked.connect(self._on_add_tag)
        add_layout.addWidget(add_btn)
        layout.addLayout(add_layout)

        # Delete button
        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self._on_delete_tag)
        layout.addWidget(delete_btn)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def _refresh_tags(self):
        self.tag_list.clear()
        for tag in self.exhibit_bank.list_tags():
            item = QListWidgetItem(tag.name)
            item.setData(Qt.ItemDataRole.UserRole, tag.id)
            self.tag_list.addItem(item)

    def _on_add_tag(self):
        name = self.new_tag_edit.text().strip()
        if name:
            self.exhibit_bank.add_tag(name)
            self.new_tag_edit.clear()
            self._refresh_tags()

    def _on_delete_tag(self):
        item = self.tag_list.currentItem()
        if item:
            tag_id = item.data(Qt.ItemDataRole.UserRole)
            self.exhibit_bank.delete_tag(tag_id)
            self._refresh_tags()


# ========== Docket Dialogs ==========

class AddDocketEntryDialog(QDialog):
    """Dialog for adding a new docket entry to the timeline."""

    def __init__(self, parent, case_id: str, docket_data: dict, lawsuit_info: dict = None):
        super().__init__(parent)
        self.case_id = case_id
        self._docket_data = docket_data
        self._lawsuit_info = lawsuit_info or {}
        self.date = ""
        self.text = ""
        self.filed_by = ""
        self.entry_type = ""
        self.signed_by = ""

        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Add Docket Entry")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # Show next docket number info
        next_num = self._docket_data.get('next_number', {}).get(self.case_id, 1)
        info_label = QLabel(f"This entry will be assigned Docket Number: {next_num}")
        info_label.setStyleSheet("font-weight: bold; color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(info_label)

        # Form
        form = QFormLayout()

        # Entry Type
        self.entry_type_combo = QComboBox()
        self.entry_type_combo.addItems([
            "",
            "Order",
            "Motion",
            "Response",
            "Notice",
            "Complaint",
            "Answer",
            "Discovery",
            "Judgment",
            "Other"
        ])
        self.entry_type_combo.currentTextChanged.connect(self._on_entry_type_changed)
        form.addRow("Entry Type:", self.entry_type_combo)

        # Date
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Date Filed:", self.date_edit)

        # Signed By (for Orders/Judgments) - initially hidden
        self.signed_by_label = QLabel("Signed By:")
        self.signed_by_combo = QComboBox()
        self.signed_by_combo.setEditable(True)
        # Populate with judge and magistrate from lawsuit info
        judge = self._lawsuit_info.get('judge', '')
        magistrate = self._lawsuit_info.get('magistrate', '')
        judges = [""]
        if judge:
            judges.append(f"Judge {judge}")
        if magistrate:
            judges.append(f"Magistrate {magistrate}")
        self.signed_by_combo.addItems(judges)
        form.addRow(self.signed_by_label, self.signed_by_combo)
        # Initially hide signed by field
        self.signed_by_label.setVisible(False)
        self.signed_by_combo.setVisible(False)

        # Text/Description
        self.text_edit = QTextEdit()
        self.text_edit.setMinimumHeight(120)
        self.text_edit.setPlaceholderText("Enter docket entry text (e.g., MOTION for Summary Judgment by Defendant...)")
        form.addRow("Entry Text:", self.text_edit)

        # Filed by
        self.filed_by_combo = QComboBox()
        self.filed_by_combo.setEditable(True)
        self.filed_by_combo.addItems([
            "",
            "Plaintiff",
            "Defendant",
            "Court",
            "Clerk",
            "Multiple Parties"
        ])
        self.filed_by_combo.setCurrentText("")
        form.addRow("Filed By:", self.filed_by_combo)

        layout.addLayout(form)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_entry_type_changed(self, entry_type: str):
        """Show/hide signed by field based on entry type."""
        is_order = entry_type in ['Order', 'Judgment']
        self.signed_by_label.setVisible(is_order)
        self.signed_by_combo.setVisible(is_order)
        # Auto-set filed by to Court for Orders
        if is_order:
            self.filed_by_combo.setCurrentText("Court")

    def _on_accept(self):
        self.date = self.date_edit.date().toString("yyyy-MM-dd")
        self.text = self.text_edit.toPlainText().strip()
        self.filed_by = self.filed_by_combo.currentText().strip()
        self.entry_type = self.entry_type_combo.currentText().strip()
        self.signed_by = self.signed_by_combo.currentText().strip()

        if not self.text:
            QMessageBox.warning(self, "Required Field", "Please enter the docket entry text.")
            return

        self.accept()


class EditDocketEntryDialog(QDialog):
    """Dialog for editing an existing docket entry."""

    def __init__(self, parent, entry: dict):
        super().__init__(parent)
        self.entry = entry.copy()
        self.date = entry.get('date', '')
        self.text = entry.get('text', entry.get('description', ''))
        self.filed_by = entry.get('filed_by', '')
        self.comments = entry.get('comments', '')

        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Edit Docket Entry")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # Show docket number (read-only)
        docket_num = self.entry.get('docket_number', '?')
        info_label = QLabel(f"Docket Entry #{docket_num}")
        info_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(info_label)

        # Form
        form = QFormLayout()

        # Date
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        if self.date:
            try:
                date_obj = QDate.fromString(self.date, "yyyy-MM-dd")
                if date_obj.isValid():
                    self.date_edit.setDate(date_obj)
                else:
                    self.date_edit.setDate(QDate.currentDate())
            except:
                self.date_edit.setDate(QDate.currentDate())
        else:
            self.date_edit.setDate(QDate.currentDate())
        form.addRow("Date Filed:", self.date_edit)

        # Text/Description
        self.text_edit = QTextEdit()
        self.text_edit.setMinimumHeight(120)
        self.text_edit.setPlainText(self.text)
        form.addRow("Entry Text:", self.text_edit)

        # Filed by
        self.filed_by_combo = QComboBox()
        self.filed_by_combo.setEditable(True)
        self.filed_by_combo.addItems([
            "",
            "Plaintiff",
            "Defendant",
            "Court",
            "Clerk",
            "Multiple Parties"
        ])
        self.filed_by_combo.setCurrentText(self.filed_by)
        form.addRow("Filed By:", self.filed_by_combo)

        # Comments
        self.comments_edit = QTextEdit()
        self.comments_edit.setMinimumHeight(80)
        self.comments_edit.setPlaceholderText("Add your notes/comments about this entry...")
        self.comments_edit.setPlainText(self.comments)
        form.addRow("Comments:", self.comments_edit)

        layout.addLayout(form)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        self.date = self.date_edit.date().toString("yyyy-MM-dd")
        self.text = self.text_edit.toPlainText().strip()
        self.filed_by = self.filed_by_combo.currentText().strip()
        self.comments = self.comments_edit.toPlainText().strip()

        if not self.text:
            QMessageBox.warning(self, "Required Field", "Please enter the docket entry text.")
            return

        self.accept()


class DocketEntryDetailDialog(QDialog):
    """Dialog showing full docket entry details including extracted PDF text."""

    def __init__(
        self,
        parent,
        docket_num,
        date: str,
        docket_text: str,
        extracted_text: str,
        comments: str,
        doc_path: str,
        entry_type: str = "",
        deadlines: list = None
    ):
        super().__init__(parent)
        self.doc_path = doc_path
        self.deadlines = deadlines or []
        self.entry_type = entry_type
        self._setup_ui(docket_num, date, docket_text, extracted_text, comments)

    def _setup_ui(self, docket_num, date, docket_text, extracted_text, comments):
        self.setWindowTitle(f"Docket Entry #{docket_num}")
        self.setMinimumSize(700, 600)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"Docket Entry #{docket_num}")
        header.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            padding: 10px;
        """)
        layout.addWidget(header)

        # Date and Entry Type
        info_layout = QHBoxLayout()
        date_label = QLabel(f"Filed: {date}")
        date_label.setStyleSheet("font-size: 12px; color: #7f8c8d; padding-left: 10px;")
        info_layout.addWidget(date_label)

        if self.entry_type:
            type_label = QLabel(f"Type: {self.entry_type}")
            type_label.setStyleSheet("font-size: 12px; color: #2980b9; padding-left: 20px; font-weight: bold;")
            info_layout.addWidget(type_label)

        info_layout.addStretch()
        layout.addLayout(info_layout)

        # Deadlines section (if any active deadlines)
        active_deadlines = [d for d in self.deadlines if d.get('days_remaining', -1) >= 0]
        if active_deadlines:
            deadlines_frame = QFrame()
            deadlines_frame.setStyleSheet("""
                QFrame {
                    background: #fef9e7;
                    border: 1px solid #f39c12;
                    border-radius: 5px;
                    margin: 5px 10px;
                    padding: 10px;
                }
            """)
            dl_layout = QVBoxLayout(deadlines_frame)
            dl_layout.setContentsMargins(10, 5, 10, 5)

            dl_header = QLabel("Response/Appeal Deadlines")
            dl_header.setStyleSheet("font-size: 13px; font-weight: bold; color: #d35400;")
            dl_layout.addWidget(dl_header)

            for dl in active_deadlines:
                days = dl.get('days_remaining', 0)
                if days <= 7:
                    color = "#e74c3c"
                    status = "URGENT"
                elif days <= 21:
                    color = "#f39c12"
                    status = "Soon"
                else:
                    color = "#27ae60"
                    status = ""

                dl_row = QHBoxLayout()
                action_label = QLabel(f"{dl['action']}")
                action_label.setStyleSheet("font-size: 12px; font-weight: bold;")
                dl_row.addWidget(action_label)

                deadline_label = QLabel(f"Due: {dl['deadline']} ({days} days)")
                deadline_label.setStyleSheet(f"font-size: 12px; color: {color};")
                dl_row.addWidget(deadline_label)

                if status:
                    status_label = QLabel(status)
                    status_label.setStyleSheet(f"""
                        font-size: 10px;
                        color: white;
                        font-weight: bold;
                        background: {color};
                        border-radius: 3px;
                        padding: 2px 6px;
                    """)
                    dl_row.addWidget(status_label)

                rule_label = QLabel(f"({dl['rule']})")
                rule_label.setStyleSheet("font-size: 10px; color: #888;")
                dl_row.addWidget(rule_label)

                dl_row.addStretch()
                dl_layout.addLayout(dl_row)

            layout.addWidget(deadlines_frame)

        # Tabs for different content
        tabs = QTabWidget()

        # Tab 1: Docket Text
        docket_tab = QWidget()
        docket_layout = QVBoxLayout(docket_tab)
        docket_label = QLabel("Docket Entry Text:")
        docket_label.setStyleSheet("font-weight: bold;")
        docket_layout.addWidget(docket_label)

        docket_edit = QTextEdit()
        docket_edit.setPlainText(docket_text)
        docket_edit.setReadOnly(True)
        docket_edit.setStyleSheet("""
            QTextEdit {
                font-family: Georgia, serif;
                font-size: 13px;
                line-height: 1.5;
                padding: 10px;
            }
        """)
        docket_layout.addWidget(docket_edit)
        tabs.addTab(docket_tab, "Docket Entry")

        # Tab 2: Document Text (if available)
        if extracted_text:
            doc_tab = QWidget()
            doc_layout = QVBoxLayout(doc_tab)

            doc_header = QHBoxLayout()
            doc_label = QLabel("Extracted Document Text:")
            doc_label.setStyleSheet("font-weight: bold;")
            doc_header.addWidget(doc_label)

            if self.doc_path:
                open_btn = QPushButton("Open PDF")
                open_btn.setStyleSheet("""
                    QPushButton {
                        background: #3498db;
                        color: white;
                        border: none;
                        padding: 5px 15px;
                        border-radius: 3px;
                    }
                    QPushButton:hover { background: #2980b9; }
                """)
                open_btn.clicked.connect(self._open_pdf)
                doc_header.addWidget(open_btn)

            doc_header.addStretch()
            doc_layout.addLayout(doc_header)

            doc_edit = QTextEdit()
            doc_edit.setPlainText(extracted_text)
            doc_edit.setReadOnly(True)
            doc_edit.setStyleSheet("""
                QTextEdit {
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                    padding: 10px;
                }
            """)
            doc_layout.addWidget(doc_edit)

            char_count = QLabel(f"Characters: {len(extracted_text):,}")
            char_count.setStyleSheet("font-size: 10px; color: #888;")
            doc_layout.addWidget(char_count)

            tabs.addTab(doc_tab, f"Document Text ({len(extracted_text):,} chars)")

        # Tab 3: Comments (if available)
        if comments:
            comments_tab = QWidget()
            comments_layout = QVBoxLayout(comments_tab)
            comments_label = QLabel("Your Comments:")
            comments_label.setStyleSheet("font-weight: bold;")
            comments_layout.addWidget(comments_label)

            comments_edit = QTextEdit()
            comments_edit.setPlainText(comments)
            comments_edit.setReadOnly(True)
            comments_edit.setStyleSheet("""
                QTextEdit {
                    font-size: 13px;
                    padding: 10px;
                    background: #fffde7;
                }
            """)
            comments_layout.addWidget(comments_edit)
            tabs.addTab(comments_tab, "Comments")

        layout.addWidget(tabs)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #95a5a6;
                color: white;
                border: none;
                padding: 8px 25px;
                border-radius: 4px;
                font-size: 13px;
            }
            QPushButton:hover { background: #7f8c8d; }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _open_pdf(self):
        if self.doc_path and Path(self.doc_path).exists():
            subprocess.run(['open', self.doc_path])
