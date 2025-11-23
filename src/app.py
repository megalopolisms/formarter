"""
Main application window for Formarter.
"""

import subprocess
import sys
import tempfile
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
    QLabel,
    QMenu,
    QInputDialog,
    QPushButton,
    QFileDialog,
    QDialog,
    QScrollArea,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QTextCursor, QAction, QPixmap, QImage

from .models import Document, Paragraph, Section
from .pdf_export import generate_pdf


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
    LINES_PER_PAGE = 25  # Approximate lines per page (double-spaced, 1" margins)
    CHARS_PER_LINE = 65  # Approximate characters per line (Times New Roman 12pt, 1" margins)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Formarter - Federal Court Document Formatter")
        self.setMinimumSize(1200, 600)

        # Start with empty document
        self.document = Document(title="New Document")

        # Track line positions for each paragraph (para_num -> line_index)
        self._para_line_map: dict[int, int] = {}

        # Track which paragraph starts each section (para_num -> section)
        self._section_starts: dict[int, Section] = {}

        # Track page assignments (page_num -> list of para_nums)
        self._page_assignments: dict[int, list[int]] = {}

        # Flag to prevent recursive updates
        self._updating = False

        self._setup_ui()

    def _setup_ui(self):
        """Set up the main user interface with toolbar and 3 panels."""
        # Create main container
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create toolbar
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)

        # Create the main splitter for three-panel layout
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Text Editor
        left_panel = self._create_editor_panel()
        splitter.addWidget(left_panel)

        # Middle panel: Section Tree
        middle_panel = self._create_section_tree_panel()
        splitter.addWidget(middle_panel)

        # Right panel: Page Tree
        right_panel = self._create_page_tree_panel()
        splitter.addWidget(right_panel)

        # Set initial sizes (40/30/30 split)
        splitter.setSizes([400, 300, 300])

        main_layout.addWidget(splitter)

        # Set main widget as central widget
        self.setCentralWidget(main_widget)

    def _create_toolbar(self) -> QWidget:
        """Create toolbar with Preview and Export buttons."""
        toolbar = QWidget()
        toolbar.setFixedHeight(36)
        toolbar.setStyleSheet("background: #f0f0f0; border-bottom: 1px solid #ccc;")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(5, 2, 5, 2)

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

        for para_num in sorted(self.document.paragraphs.keys()):
            para = self.document.paragraphs[para_num]

            # Calculate lines this paragraph takes (double-spaced)
            # Each paragraph = ceil(len(text) / CHARS_PER_LINE) lines * 2 (double-spaced) + 1 (spacing)
            text_lines = max(1, (len(para.text) + self.CHARS_PER_LINE - 1) // self.CHARS_PER_LINE)
            para_lines = text_lines * 2 + 1  # Double-spaced + spacing between paragraphs

            # Check if we need a new page
            if current_line_count + para_lines > self.LINES_PER_PAGE and current_line_count > 0:
                current_page += 1
                current_line_count = 0
                self._page_assignments[current_page] = []

            # Add paragraph to current page
            self._page_assignments[current_page].append(para_num)
            current_line_count += para_lines

            # Check if section header needs extra space
            if para_num in self._section_starts:
                current_line_count += 2  # Extra space for section header

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
        if not self.document.paragraphs:
            QMessageBox.warning(
                self,
                "No Content",
                "Please add some paragraphs before previewing."
            )
            return

        try:
            # Generate PDF to temp file
            pdf_path = generate_pdf(
                self.document.paragraphs,
                self._section_starts
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
        if not self.document.paragraphs:
            QMessageBox.warning(
                self,
                "No Content",
                "Please add some paragraphs before exporting."
            )
            return

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
                output_path=file_path
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
