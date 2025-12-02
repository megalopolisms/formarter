"""
File Document Dialog - Dialog for "Mark as Filed" feature.

This dialog prompts the user for filing details when marking an Editor
document as filed with the court. The document will then be linked to
the Executed Filings tab and become read-only.

WORKFLOW:
1. User right-clicks document in Editor tree → "Mark as Filed"
2. This dialog opens with document details pre-filled
3. User enters filing date and optional docket number
4. On accept, the document is:
   - Marked as is_filed=True, is_locked=True
   - .txt and .pdf generated in executed_filings/
   - Added to executed_filings/index.json
   - Displayed in BOTH Editor (locked) and Executed Filings tabs
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QDateEdit, QPushButton, QFormLayout, QGroupBox, QTextEdit
)
from PyQt6.QtCore import Qt, QDate
from datetime import datetime


class FileDocumentDialog(QDialog):
    """
    Dialog for collecting filing details when marking a document as filed.

    Properties after exec():
        filing_date: str - ISO format date string (YYYY-MM-DD)
        docket_number: str - Court docket/document number (optional)
    """

    def __init__(self, doc_name: str, doc_title: str, case_id: str, parent=None):
        """
        Initialize the dialog.

        Args:
            doc_name: Display name of the document
            doc_title: Full document title (custom_title field)
            case_id: Case number (e.g., "178")
            parent: Parent widget
        """
        super().__init__(parent)
        self.doc_name = doc_name
        self.doc_title = doc_title
        self.case_id = case_id

        # Return values
        self.filing_date = ""
        self.docket_number = ""

        self._setup_ui()

    def _setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Mark Document as Filed")
        self.setModal(True)
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)

        # Info section
        info_group = QGroupBox("Document Information")
        info_layout = QFormLayout(info_group)

        self.name_label = QLabel(self.doc_name)
        self.name_label.setWordWrap(True)
        info_layout.addRow("Document:", self.name_label)

        self.title_label = QLabel(self.doc_title or "(No custom title)")
        self.title_label.setWordWrap(True)
        info_layout.addRow("Title:", self.title_label)

        self.case_label = QLabel(f"Case {self.case_id}")
        info_layout.addRow("Case:", self.case_label)

        layout.addWidget(info_group)

        # Filing details section
        filing_group = QGroupBox("Filing Details")
        filing_layout = QFormLayout(filing_group)

        # Filing date picker
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setDisplayFormat("MMMM d, yyyy")
        filing_layout.addRow("Filing Date:", self.date_edit)

        # Docket number
        self.docket_edit = QLineEdit()
        self.docket_edit.setPlaceholderText("e.g., Doc 99 (optional)")
        filing_layout.addRow("Docket Number:", self.docket_edit)

        layout.addWidget(filing_group)

        # What will happen section
        what_group = QGroupBox("What will happen")
        what_layout = QVBoxLayout(what_group)

        what_text = QLabel(
            "• Document will be marked as FILED and become read-only\n"
            "• A .txt file will be generated in executed_filings/\n"
            "• A PDF will be generated with full caption and signature\n"
            "• Document will appear in both Editor and Executed Filings tabs\n"
            "• You can 'Unfile' later to restore editing capability"
        )
        what_text.setStyleSheet("color: #666; font-size: 11px;")
        what_layout.addWidget(what_text)

        layout.addWidget(what_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.file_btn = QPushButton("Mark as Filed")
        self.file_btn.setStyleSheet("""
            QPushButton {
                background-color: #2e7d32;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1b5e20;
            }
        """)
        self.file_btn.clicked.connect(self._on_file_clicked)
        button_layout.addWidget(self.file_btn)

        layout.addLayout(button_layout)

    def _on_file_clicked(self):
        """Handle the file button click."""
        # Get the filing date as ISO string
        qdate = self.date_edit.date()
        self.filing_date = f"{qdate.year()}-{qdate.month():02d}-{qdate.day():02d}"

        # Get docket number (can be empty)
        self.docket_number = self.docket_edit.text().strip()

        self.accept()
