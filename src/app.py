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


# Mock legal document text for demonstration
MOCK_DOCUMENT = """Plaintiff, John Smith, by and through undersigned counsel, respectfully submits this Complaint against Defendant, ABC Corporation, and in support thereof states as follows:

Plaintiff is an individual residing in Jackson, Mississippi. Plaintiff has been a resident of Hinds County, Mississippi for the past fifteen years.

Defendant ABC Corporation is a Delaware corporation with its principal place of business in Biloxi, Mississippi. Defendant regularly conducts business throughout the State of Mississippi.

This Court has subject matter jurisdiction over this action pursuant to 28 U.S.C. Section 1332 because there is complete diversity of citizenship between the parties and the amount in controversy exceeds $75,000, exclusive of interest and costs.

Venue is proper in this District pursuant to 28 U.S.C. Section 1391(b) because a substantial part of the events giving rise to the claims occurred in this District.

On or about January 15, 2024, Plaintiff entered into a written contract with Defendant for the purchase of commercial equipment valued at $150,000.

Defendant expressly warranted that the equipment would be delivered within thirty days of the contract date and would conform to all specifications outlined in Exhibit A attached hereto.

Despite Plaintiff's full performance under the contract, including payment of the full purchase price, Defendant failed to deliver the equipment as promised.

As a direct and proximate result of Defendant's breach, Plaintiff has suffered damages in excess of $200,000, including lost business revenue, additional equipment rental costs, and consequential damages.

WHEREFORE, Plaintiff respectfully requests that this Court enter judgment in favor of Plaintiff and against Defendant, awarding compensatory damages, consequential damages, attorney's fees and costs, and such other relief as the Court deems just and proper."""


class MainWindow(QMainWindow):
    """
    Main application window with two-panel layout:
    - Left: Text editor (line-by-line view)
    - Right: Paragraph tree (structural view)
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Formarter - Federal Court Document Formatter")
        self.setMinimumSize(800, 600)

        self._setup_ui()
        self._load_mock_data()

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
        header = QLabel("Text Editor")
        header.setStyleSheet("font-weight: bold; padding: 5px; background: #f0f0f0;")
        layout.addWidget(header)

        # Text editor
        self.text_editor = QTextEdit()
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
        header = QLabel("Paragraph Structure")
        header.setStyleSheet("font-weight: bold; padding: 5px; background: #f0f0f0;")
        layout.addWidget(header)

        # Tree widget
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["Paragraphs"])
        self.tree_widget.setAlternatingRowColors(True)
        layout.addWidget(self.tree_widget)

        return panel

    def _load_mock_data(self):
        """Load mock legal document for demonstration."""
        # Set the mock text in the editor
        self.text_editor.setText(MOCK_DOCUMENT)

        # Parse paragraphs and populate tree
        paragraphs = [p.strip() for p in MOCK_DOCUMENT.split("\n\n") if p.strip()]

        # Create section headers and paragraphs
        sections = {
            "PARTIES": paragraphs[0:3],
            "JURISDICTION AND VENUE": paragraphs[3:5],
            "FACTUAL ALLEGATIONS": paragraphs[5:9],
            "PRAYER FOR RELIEF": paragraphs[9:],
        }

        para_num = 1
        for section_name, section_paras in sections.items():
            # Add section as parent item
            section_item = QTreeWidgetItem([section_name])
            section_item.setFlags(
                section_item.flags() | Qt.ItemFlag.ItemIsAutoTristate
            )
            self.tree_widget.addTopLevelItem(section_item)

            # Add paragraphs as children
            for para in section_paras:
                # Truncate long paragraphs for display
                preview = para[:60] + "..." if len(para) > 60 else para
                para_item = QTreeWidgetItem([f"{para_num}. {preview}"])
                section_item.addChild(para_item)
                para_num += 1

            # Expand section by default
            section_item.setExpanded(True)
