"""
Filing Tree Widget for hierarchical Case → Filing → Document display.

Features:
- Collapsible folder-style containers
- Tag color badges displayed next to filing names
- Drag-drop support for moving documents between filings
- Right-click context menus
"""

from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QWidget, QHBoxLayout, QLabel,
    QStyledItemDelegate, QStyle, QStyleOptionViewItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QSize
from PyQt6.QtGui import QColor, QBrush, QFont, QIcon, QPainter, QPen, QDrag
from typing import Optional
import uuid


class TagBadgeWidget(QWidget):
    """Widget displaying colored tag badges."""

    def __init__(self, tags: list, tag_colors: dict, parent=None):
        super().__init__(parent)
        self.tags = tags
        self.tag_colors = tag_colors
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(3)

        for tag_id in self.tags[:3]:  # Show max 3 tags
            color = self.tag_colors.get(tag_id, "#808080")
            badge = QLabel()
            badge.setFixedSize(12, 12)
            badge.setStyleSheet(f"""
                background-color: {color};
                border-radius: 6px;
            """)
            badge.setToolTip(tag_id)
            layout.addWidget(badge)

        if len(self.tags) > 3:
            more = QLabel(f"+{len(self.tags) - 3}")
            more.setStyleSheet("color: #666; font-size: 10px;")
            layout.addWidget(more)

        layout.addStretch()


class FilingTreeWidget(QTreeWidget):
    """
    Custom tree widget for displaying Case → Filing → Document hierarchy.

    Signals:
        case_selected(str): Emitted when a case is clicked (case_id)
        filing_selected(str): Emitted when a filing is clicked (filing_id)
        document_selected(str): Emitted when a document is clicked (doc_id)
        filing_context_menu(str, QPoint): Right-click on filing
        document_context_menu(str, QPoint): Right-click on document
        case_context_menu(str, QPoint): Right-click on case
        document_moved(str, str, str): Document moved (doc_id, old_filing_id, new_filing_id)
    """

    case_selected = pyqtSignal(str)
    filing_selected = pyqtSignal(str)
    document_selected = pyqtSignal(str)
    filing_context_menu = pyqtSignal(str, object)  # filing_id, QPoint
    document_context_menu = pyqtSignal(str, object)  # doc_id, QPoint
    case_context_menu = pyqtSignal(str, object)  # case_id, QPoint
    document_moved = pyqtSignal(str, str, str)  # doc_id, old_filing_id, new_filing_id

    # Signals for Mark as Filed feature (links Editor doc to Executed Filings tab)
    mark_as_filed = pyqtSignal(str)    # doc_id - emitted when user clicks "Mark as Filed"
    unfile_document = pyqtSignal(str)  # doc_id - emitted when user clicks "Unfile Document"

    # Item types stored in UserRole
    ITEM_TYPE_CASE = "case"
    ITEM_TYPE_FILING = "filing"
    ITEM_TYPE_DOCUMENT = "document"
    ITEM_TYPE_UNFILED = "unfiled"
    ITEM_TYPE_EXHIBIT = "exhibit"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._cases = []
        self._tags = {}  # tag_id -> Tag
        self._documents = {}  # doc_id -> document data

        # Connect signals
        self.itemClicked.connect(self._on_item_clicked)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

    def _setup_ui(self):
        """Setup tree widget appearance."""
        self.setHeaderHidden(True)
        self.setIndentation(20)
        self.setAnimated(True)
        self.setExpandsOnDoubleClick(True)

        # Enable drag-drop
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)

        # Styling
        self.setStyleSheet("""
            QTreeWidget {
                background-color: #fafafa;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QTreeWidget::item {
                padding: 4px 0;
                border-radius: 2px;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            QTreeWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)

    def set_data(self, cases: list, tags: dict, documents: dict):
        """
        Set the tree data.

        Args:
            cases: List of Case objects
            tags: Dict of tag_id -> Tag objects
            documents: Dict of doc_id -> document data dict
        """
        self._cases = cases
        self._tags = tags
        self._documents = documents
        self._rebuild_tree()

    def _rebuild_tree(self):
        """Rebuild the tree from current data."""
        self.clear()

        # Build tag color map
        tag_colors = {tag_id: tag.color for tag_id, tag in self._tags.items()}

        for case in self._cases:
            # Create case item
            case_item = QTreeWidgetItem(self)
            case_item.setText(0, f"\U0001F4C1 {case.name}")  # Folder icon
            case_item.setData(0, Qt.ItemDataRole.UserRole, (self.ITEM_TYPE_CASE, case.id))

            # Bold font for case
            font = case_item.font(0)
            font.setBold(True)
            case_item.setFont(0, font)

            # Add filings
            for filing in case.filings:
                if filing.status == "archived":
                    continue  # Skip archived filings

                filing_item = QTreeWidgetItem(case_item)

                # Status indicator
                status_icon = {
                    "draft": "\U0001F4DD",      # Memo
                    "pending": "\u23F3",         # Hourglass
                    "filed": "\u2705",           # Check mark
                }.get(filing.status, "\U0001F4C4")  # Default: page

                filing_item.setText(0, f"{status_icon} {filing.name}")
                filing_item.setData(0, Qt.ItemDataRole.UserRole, (self.ITEM_TYPE_FILING, filing.id))

                # Tag badges as tooltip
                if filing.tags:
                    tag_names = [self._tags.get(t, {}).name if hasattr(self._tags.get(t, {}), 'name') else t for t in filing.tags]
                    filing_item.setToolTip(0, f"Tags: {', '.join(tag_names)}")

                    # Color indicator using background
                    if filing.tags and filing.tags[0] in self._tags:
                        first_tag = self._tags[filing.tags[0]]
                        if hasattr(first_tag, 'color'):
                            color = QColor(first_tag.color)
                            color.setAlpha(30)
                            filing_item.setBackground(0, QBrush(color))

                # Add documents in this filing
                for doc_id in filing.document_ids:
                    doc = self._documents.get(doc_id)
                    if doc:
                        doc_item = QTreeWidgetItem(filing_item)
                        doc_name = doc.get("name", doc_id) if isinstance(doc, dict) else getattr(doc, "name", doc_id)

                        # Check if document is filed (linked to Executed Filings tab)
                        is_filed = doc.get("is_filed", False) if isinstance(doc, dict) else getattr(doc, "is_filed", False)
                        if is_filed:
                            # Filed documents show lock icon and "(Filed)" badge
                            doc_item.setText(0, f"\U0001F512 {doc_name} (Filed)")  # Lock icon
                            doc_item.setForeground(0, QBrush(QColor("#2e7d32")))  # Green text
                            doc_item.setToolTip(0, "Filed with court - read-only")
                        else:
                            doc_item.setText(0, f"\U0001F4C4 {doc_name}")  # Page icon
                        doc_item.setData(0, Qt.ItemDataRole.UserRole, (self.ITEM_TYPE_DOCUMENT, doc_id))

                # Add exhibit files
                for exhibit in filing.exhibit_files:
                    exhibit_item = QTreeWidgetItem(filing_item)
                    exhibit_item.setText(0, f"\U0001F4CE {exhibit.filename}")  # Paperclip
                    exhibit_item.setData(0, Qt.ItemDataRole.UserRole, (self.ITEM_TYPE_EXHIBIT, exhibit.filename))
                    exhibit_item.setForeground(0, QBrush(QColor("#666")))

            # Add unfiled documents section
            if case.unfiled_document_ids:
                unfiled_item = QTreeWidgetItem(case_item)
                unfiled_item.setText(0, "\U0001F4E5 Unfiled Documents")  # Inbox
                unfiled_item.setData(0, Qt.ItemDataRole.UserRole, (self.ITEM_TYPE_UNFILED, case.id))
                unfiled_item.setForeground(0, QBrush(QColor("#888")))

                for doc_id in case.unfiled_document_ids:
                    doc = self._documents.get(doc_id)
                    if doc:
                        doc_item = QTreeWidgetItem(unfiled_item)
                        doc_name = doc.get("name", doc_id) if isinstance(doc, dict) else getattr(doc, "name", doc_id)
                        doc_item.setText(0, f"\U0001F4C4 {doc_name}")
                        doc_item.setData(0, Qt.ItemDataRole.UserRole, (self.ITEM_TYPE_DOCUMENT, doc_id))

            case_item.setExpanded(True)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type, item_id = data

        if item_type == self.ITEM_TYPE_CASE:
            self.case_selected.emit(item_id)
        elif item_type == self.ITEM_TYPE_FILING:
            self.filing_selected.emit(item_id)
        elif item_type == self.ITEM_TYPE_DOCUMENT:
            self.document_selected.emit(item_id)

    def _on_context_menu(self, position):
        """Handle right-click context menu."""
        item = self.itemAt(position)
        if not item:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type, item_id = data
        global_pos = self.mapToGlobal(position)

        if item_type == self.ITEM_TYPE_CASE:
            self.case_context_menu.emit(item_id, global_pos)
        elif item_type == self.ITEM_TYPE_FILING:
            self.filing_context_menu.emit(item_id, global_pos)
        elif item_type == self.ITEM_TYPE_DOCUMENT:
            self.document_context_menu.emit(item_id, global_pos)

    def get_selected_item_data(self) -> Optional[tuple]:
        """Get the data of the currently selected item."""
        items = self.selectedItems()
        if items:
            return items[0].data(0, Qt.ItemDataRole.UserRole)
        return None

    def select_document(self, doc_id: str):
        """Select a document by ID."""
        self._select_item_by_id(doc_id, self.ITEM_TYPE_DOCUMENT)

    def select_filing(self, filing_id: str):
        """Select a filing by ID."""
        self._select_item_by_id(filing_id, self.ITEM_TYPE_FILING)

    def _select_item_by_id(self, item_id: str, item_type: str):
        """Select an item by its ID and type."""
        iterator = QTreeWidgetItemIterator(self)
        while iterator.value():
            item = iterator.value()
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data[0] == item_type and data[1] == item_id:
                self.setCurrentItem(item)
                self.scrollToItem(item)
                break
            iterator += 1

    def refresh(self):
        """Refresh the tree display."""
        self._rebuild_tree()


# Import here to avoid circular import issues
from PyQt6.QtWidgets import QTreeWidgetItemIterator
