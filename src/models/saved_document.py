"""
Saved document data model for persistent storage.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class SectionData:
    """Serializable section data for storage."""
    id: str
    title: str
    start_para: int  # Paragraph number where this section starts
    custom_spacing: Optional[dict] = None  # SpacingSettings as dict


@dataclass
class Annotation:
    """A note that can be standalone or linked to a paragraph.

    When linked to a paragraph:
    - paragraph_number is set (1-indexed)
    - paragraph_preview shows first ~50 chars of paragraph
    - The note "moves" with the paragraph when text changes

    When standalone (unlinked):
    - paragraph_number is None
    - paragraph_preview may still contain the last linked text for reference
    """
    id: str
    note: str  # User's note/comment
    paragraph_number: Optional[int] = None  # 1-indexed paragraph number, None = standalone
    paragraph_preview: str = ""  # First ~50 chars of the linked paragraph
    color: str = "#FFFF00"  # Highlight color (default yellow)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def is_linked(self) -> bool:
        """Check if this note is linked to a paragraph."""
        return self.paragraph_number is not None

    def unlink(self):
        """Unlink this note from its paragraph (make it standalone)."""
        self.paragraph_number = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "note": self.note,
            "paragraph_number": self.paragraph_number,
            "paragraph_preview": self.paragraph_preview,
            "color": self.color,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Annotation":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            note=data.get("note", ""),
            paragraph_number=data.get("paragraph_number"),  # Can be None
            paragraph_preview=data.get("paragraph_preview", ""),
            color=data.get("color", "#FFFF00"),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )


@dataclass
class SavedDocument:
    """
    A saved document with all state needed to restore the editor.

    Includes text content, sections, case profile, document type,
    spacing settings, and metadata (dates, PDF path).

    IMPORTANT: Tab Architecture - Editor vs Executed Filings
    =========================================================
    The Editor tab and Executed Filings tab are RELATED but NOT CONNECTED systems:

    EDITOR TAB (Draft Documents):
    - Uses documents.json for storage
    - Documents are editable drafts
    - text_content contains ONLY the body (no caption, no signature)
    - PDF export auto-generates caption/title/signature from templates

    EXECUTED FILINGS TAB (Court-Submitted Documents):
    - Uses executed_filings/index.json + *.txt files for storage
    - Documents that have been ACTUALLY FILED with the court
    - Contains complete documents (caption + body + signature)
    - Read-only archive of filed documents

    WORKFLOW:
    1. Draft in Editor tab → Preview PDF → Export PDF
    2. File document with court (outside app)
    3. Use "Mark as Filed" to link Editor doc to Executed Filings
       - Sets is_filed=True, is_locked=True
       - Generates .txt and .pdf in executed_filings/
       - Document appears in BOTH tabs (read-only)

    The new "filed" fields below enable this linking:
    - is_filed: True when document has been submitted to court
    - is_locked: True to prevent editing of filed documents
    - filed_date: Date document was filed with court
    - docket_number: Court docket/document number
    - executed_filing_id: Links to executed_filings/index.json entry
    """
    # Unique identifier
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Display name (user can rename)
    name: str = "Untitled Document"

    # Timestamps
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Editor content
    text_content: str = ""  # Raw text from editor

    # Section assignments (list of SectionData)
    sections: list[dict] = field(default_factory=list)

    # Case profile (index in CASE_PROFILES list, 0 = none selected)
    case_profile_index: int = 1  # Default to case 178

    # Case ID for cross-referencing with lawsuits.json (e.g., "178", "233", "254")
    case_id: Optional[str] = None

    # Document type (index in doc type dropdown)
    document_type_index: int = 1  # Default to MOTION
    custom_title: str = ""  # If document type is CUSTOM

    # Global spacing settings
    spacing_before_section: int = 1
    spacing_after_section: int = 1
    spacing_between_paragraphs: int = 1

    # Filing date
    filing_date: str = ""

    # Path to saved PDF (relative to storage directory)
    pdf_filename: Optional[str] = None

    # Annotations (notes attached to highlighted text)
    annotations: list = field(default_factory=list)

    # Filed document state (for linking to Executed Filings tab)
    is_filed: bool = False
    is_locked: bool = False
    filed_date: Optional[str] = None
    docket_number: Optional[str] = None
    executed_filing_id: Optional[str] = None  # Link to index.json entry

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "text_content": self.text_content,
            "sections": self.sections,
            "case_profile_index": self.case_profile_index,
            "case_id": self.case_id,
            "document_type_index": self.document_type_index,
            "custom_title": self.custom_title,
            "spacing_before_section": self.spacing_before_section,
            "spacing_after_section": self.spacing_after_section,
            "spacing_between_paragraphs": self.spacing_between_paragraphs,
            "filing_date": self.filing_date,
            "pdf_filename": self.pdf_filename,
            "annotations": [a.to_dict() if isinstance(a, Annotation) else a for a in self.annotations],
            "is_filed": self.is_filed,
            "is_locked": self.is_locked,
            "filed_date": self.filed_date,
            "docket_number": self.docket_number,
            "executed_filing_id": self.executed_filing_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SavedDocument":
        """Create instance from dictionary."""
        # Parse annotations from dict format
        annotations_data = data.get("annotations", [])
        annotations = [Annotation.from_dict(a) if isinstance(a, dict) else a for a in annotations_data]

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", "Untitled Document"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            modified_at=data.get("modified_at", datetime.now().isoformat()),
            text_content=data.get("text_content", ""),
            sections=data.get("sections", []),
            case_profile_index=data.get("case_profile_index", 1),
            case_id=data.get("case_id"),
            document_type_index=data.get("document_type_index", 1),
            custom_title=data.get("custom_title", ""),
            spacing_before_section=data.get("spacing_before_section", 1),
            spacing_after_section=data.get("spacing_after_section", 1),
            spacing_between_paragraphs=data.get("spacing_between_paragraphs", 1),
            filing_date=data.get("filing_date", ""),
            pdf_filename=data.get("pdf_filename"),
            annotations=annotations,
            # Filed document state
            is_filed=data.get("is_filed", False),
            is_locked=data.get("is_locked", False),
            filed_date=data.get("filed_date"),
            docket_number=data.get("docket_number"),
            executed_filing_id=data.get("executed_filing_id"),
        )

    def update_modified(self):
        """Update the modified timestamp."""
        self.modified_at = datetime.now().isoformat()

    def get_display_date(self, date_str: str) -> str:
        """Format a date string for display."""
        try:
            dt = datetime.fromisoformat(date_str)
            return dt.strftime("%m/%d/%Y %H:%M")
        except (ValueError, TypeError):
            return date_str

    @property
    def created_display(self) -> str:
        """Get formatted created date for display."""
        return self.get_display_date(self.created_at)

    @property
    def modified_display(self) -> str:
        """Get formatted modified date for display."""
        return self.get_display_date(self.modified_at)
