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
    QMenu,
    QInputDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QTextCursor, QAction

from .models import Document, Paragraph, Section


class MainWindow(QMainWindow):
    """
    Main application window with two-panel layout:
    - Left: Text editor (user types here, blank lines create paragraphs)
    - Right: Paragraph tree (shows numbered paragraphs grouped by sections)
    """

    # Roman numerals for section numbering
    ROMAN_NUMERALS = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
                      "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Formarter - Federal Court Document Formatter")
        self.setMinimumSize(800, 600)

        # Start with empty document
        self.document = Document(title="New Document")

        # Track line positions for each paragraph (para_num -> line_index)
        self._para_line_map: dict[int, int] = {}

        # Track which paragraph starts each section (para_num -> section)
        self._section_starts: dict[int, Section] = {}

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
            "Right-click paragraphs in tree to assign sections."
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

        # Enable right-click context menu
        self.tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_widget.customContextMenuRequested.connect(self._on_tree_context_menu)

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
            # Keep section if paragraph still exists
            if old_para_num <= len(self.document.paragraphs):
                new_section_starts[old_para_num] = section
        self._section_starts = new_section_starts

    def _update_tree(self):
        """Update the tree widget with current paragraphs grouped by sections."""
        self.tree_widget.clear()

        count = len(self.document.paragraphs)
        section_count = len(self._section_starts)
        self.tree_header.setText(
            f"Paragraph Structure ({count} paragraph{'s' if count != 1 else ''}, "
            f"{section_count} section{'s' if section_count != 1 else ''})"
        )

        if not self.document.paragraphs:
            return

        # Sort paragraph numbers
        para_nums = sorted(self.document.paragraphs.keys())

        # Find which paragraphs start sections
        section_start_paras = sorted(self._section_starts.keys())

        current_section_item = None
        current_section_start = None

        for para_num in para_nums:
            para = self.document.paragraphs[para_num]

            # Check if this paragraph starts a new section
            if para_num in self._section_starts:
                section = self._section_starts[para_num]
                section_text = f"{section.id}. {section.title}"

                current_section_item = QTreeWidgetItem([section_text])
                current_section_item.setData(0, Qt.ItemDataRole.UserRole, ("section", para_num))

                # Make section headers bold
                font = current_section_item.font(0)
                font.setBold(True)
                current_section_item.setFont(0, font)

                self.tree_widget.addTopLevelItem(current_section_item)
                current_section_item.setExpanded(True)
                current_section_start = para_num

            # Create paragraph item
            preview = para.get_display_text(50)
            para_text = f"{para.number}. {preview}"
            para_item = QTreeWidgetItem([para_text])
            para_item.setData(0, Qt.ItemDataRole.UserRole, ("para", para_num))

            # Add to section or top level
            if current_section_item is not None:
                current_section_item.addChild(para_item)
            else:
                self.tree_widget.addTopLevelItem(para_item)

    def _on_tree_context_menu(self, position):
        """Show context menu on right-click."""
        item = self.tree_widget.itemAt(position)
        if not item:
            return

        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data:
            return

        item_type, item_id = item_data

        menu = QMenu(self)

        if item_type == "para":
            # Right-clicked on a paragraph
            para_num = item_id

            # Section submenu
            section_menu = menu.addMenu("Section")

            # Option to create new section
            new_section_action = section_menu.addAction("Create new section...")
            new_section_action.triggered.connect(lambda: self._create_section_at(para_num))

            # List existing sections to assign to
            if self._section_starts:
                section_menu.addSeparator()
                for start_para, section in sorted(self._section_starts.items()):
                    action = section_menu.addAction(f"{section.id}. {section.title}")
                    action.triggered.connect(
                        lambda checked, s=section, p=para_num: self._assign_to_section(p, s)
                    )

            # Option to remove from section (if in a section)
            if self._get_section_for_para(para_num):
                section_menu.addSeparator()
                remove_action = section_menu.addAction("Remove from section")
                remove_action.triggered.connect(lambda: self._remove_from_section(para_num))

        elif item_type == "section":
            # Right-clicked on a section header
            section_start_para = item_id

            # Option to remove section
            remove_action = menu.addAction("Remove section")
            remove_action.triggered.connect(lambda: self._remove_section(section_start_para))

            # Option to rename section
            rename_action = menu.addAction("Rename section...")
            rename_action.triggered.connect(lambda: self._rename_section(section_start_para))

        menu.exec(self.tree_widget.viewport().mapToGlobal(position))

    def _create_section_at(self, para_num: int):
        """Create a new section starting at the given paragraph."""
        # Ask for section name
        name, ok = QInputDialog.getText(
            self, "Create Section",
            "Section name (e.g., PARTIES, JURISDICTION):"
        )
        if not ok or not name.strip():
            return

        name = name.strip().upper()

        # Determine Roman numeral
        existing_numerals = [s.id for s in self._section_starts.values()]
        for numeral in self.ROMAN_NUMERALS:
            if numeral not in existing_numerals:
                break
        else:
            numeral = f"S{len(self._section_starts) + 1}"

        # Create section
        section = Section(id=numeral, title=name)
        self._section_starts[para_num] = section

        # Update tree
        self._update_tree()

    def _assign_to_section(self, para_num: int, section: Section):
        """Move section to start at a different paragraph."""
        # Find current start of this section
        current_start = None
        for start_para, s in self._section_starts.items():
            if s.id == section.id:
                current_start = start_para
                break

        if current_start is not None:
            del self._section_starts[current_start]

        self._section_starts[para_num] = section
        self._update_tree()

    def _remove_from_section(self, para_num: int):
        """Remove section that starts at this paragraph."""
        if para_num in self._section_starts:
            del self._section_starts[para_num]
            self._update_tree()

    def _remove_section(self, section_start_para: int):
        """Remove a section entirely."""
        if section_start_para in self._section_starts:
            del self._section_starts[section_start_para]
            self._update_tree()

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
            self._update_tree()

    def _get_section_for_para(self, para_num: int) -> Section | None:
        """Get the section that contains a paragraph."""
        # Find the most recent section start before or at para_num
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

        # Only handle paragraph clicks, not section clicks
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
