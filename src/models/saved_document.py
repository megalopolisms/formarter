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
    """A note attached to highlighted text in the document."""
    id: str
    start_pos: int  # Character position where highlight starts
    end_pos: int  # Character position where highlight ends
    highlighted_text: str  # The text that was selected
    note: str  # User's note/comment
    color: str = "#FFFF00"  # Highlight color (default yellow)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "highlighted_text": self.highlighted_text,
            "note": self.note,
            "color": self.color,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Annotation":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            start_pos=data.get("start_pos", 0),
            end_pos=data.get("end_pos", 0),
            highlighted_text=data.get("highlighted_text", ""),
            note=data.get("note", ""),
            color=data.get("color", "#FFFF00"),
            created_at=data.get("created_at", datetime.now().isoformat()),
        )


@dataclass
class SavedDocument:
    """
    A saved document with all state needed to restore the editor.

    Includes text content, sections, case profile, document type,
    spacing settings, and metadata (dates, PDF path).
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
