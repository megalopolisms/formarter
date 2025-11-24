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
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QTextCursor, QAction, QPixmap, QImage, QIcon

from .models import Document, Paragraph, Section, SpacingSettings, CaseCaption, SignatureBlock, CaseProfile
from .models.saved_document import SavedDocument
from .models.library_case import LibraryCase, Category, REPORTERS, COURTS
from .pdf_export import generate_pdf
from .storage import DocumentStorage
from .case_law_extractor import CaseLawExtractor
from .case_library import CaseLibrary, get_default_library_path


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
        """Create the Case Library tab for storing and organizing case law PDFs."""
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
            # Store case ID in first column
            name_item = QTableWidgetItem(case.case_name)
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
                document_title=self.document.title
            )

            # Open in system PDF viewer (Preview.app on macOS)
            if sys.platform == "darwin":
                # Close any existing Preview windows showing our preview file
                subprocess.run(["pkill", "-x", "Preview"], capture_output=True)
                subprocess.run(["open", str(preview_path)], check=True)
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
