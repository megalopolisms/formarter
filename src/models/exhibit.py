"""
Exhibit model for the Exhibit Bank.

Stores metadata for exhibits including PDFs, images, and other documents.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ExhibitFolder:
    """Folder for organizing exhibits."""

    id: str
    name: str
    parent_id: str  # Parent folder ID, empty string for root
    color: str  # Hex color for UI display
    date_created: str
    date_modified: str

    @classmethod
    def create(cls, name: str, parent_id: str = "", color: str = "#3498db") -> "ExhibitFolder":
        """Create a new folder."""
        now = datetime.now().isoformat()
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            parent_id=parent_id,
            color=color,
            date_created=now,
            date_modified=now
        )

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'parent_id': self.parent_id,
            'color': self.color,
            'date_created': self.date_created,
            'date_modified': self.date_modified
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExhibitFolder":
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', 'Untitled'),
            parent_id=data.get('parent_id', ''),
            color=data.get('color', '#3498db'),
            date_created=data.get('date_created', datetime.now().isoformat()),
            date_modified=data.get('date_modified', datetime.now().isoformat())
        )


@dataclass
class Exhibit:
    """Represents an exhibit in the exhibit bank."""

    id: str
    title: str  # Short descriptive title
    description: str  # Longer description
    file_type: str  # pdf, image, document, etc.
    original_filename: str
    stored_filename: str  # Renamed for storage
    thumbnail_filename: str  # For preview
    tags: List[str]  # User-defined tags for search/filtering
    folder_id: str  # Folder ID, empty string for root
    date_added: str
    date_modified: str
    file_size: int  # bytes
    page_count: int  # For PDFs
    has_redacted_version: bool
    redacted_filename: str  # Redacted version filename
    notes: str  # Additional notes
    source: str  # Where this exhibit came from

    @classmethod
    def create(
        cls,
        title: str,
        original_filename: str,
        file_type: str,
        tags: List[str] = None,
        folder_id: str = "",
        description: str = "",
        notes: str = "",
        source: str = ""
    ) -> "Exhibit":
        """Create a new exhibit with generated ID and timestamps."""
        exhibit_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # Generate storage filename
        ext = original_filename.split('.')[-1] if '.' in original_filename else ''
        stored_filename = f"{exhibit_id}.{ext}" if ext else exhibit_id
        thumbnail_filename = f"{exhibit_id}_thumb.png"

        return cls(
            id=exhibit_id,
            title=title,
            description=description,
            file_type=file_type,
            original_filename=original_filename,
            stored_filename=stored_filename,
            thumbnail_filename=thumbnail_filename,
            tags=tags or [],
            folder_id=folder_id,
            date_added=now,
            date_modified=now,
            file_size=0,
            page_count=0,
            has_redacted_version=False,
            redacted_filename="",
            notes=notes,
            source=source
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'file_type': self.file_type,
            'original_filename': self.original_filename,
            'stored_filename': self.stored_filename,
            'thumbnail_filename': self.thumbnail_filename,
            'tags': self.tags,
            'folder_id': self.folder_id,
            'date_added': self.date_added,
            'date_modified': self.date_modified,
            'file_size': self.file_size,
            'page_count': self.page_count,
            'has_redacted_version': self.has_redacted_version,
            'redacted_filename': self.redacted_filename,
            'notes': self.notes,
            'source': self.source
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Exhibit":
        """Create from dictionary."""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            title=data.get('title', ''),
            description=data.get('description', ''),
            file_type=data.get('file_type', 'unknown'),
            original_filename=data.get('original_filename', ''),
            stored_filename=data.get('stored_filename', ''),
            thumbnail_filename=data.get('thumbnail_filename', ''),
            tags=data.get('tags', []),
            folder_id=data.get('folder_id', ''),
            date_added=data.get('date_added', datetime.now().isoformat()),
            date_modified=data.get('date_modified', datetime.now().isoformat()),
            file_size=data.get('file_size', 0),
            page_count=data.get('page_count', 0),
            has_redacted_version=data.get('has_redacted_version', False),
            redacted_filename=data.get('redacted_filename', ''),
            notes=data.get('notes', ''),
            source=data.get('source', '')
        )


@dataclass
class ExhibitTag:
    """Tag for categorizing exhibits."""

    id: str
    name: str
    color: str  # Hex color for UI display

    @classmethod
    def create(cls, name: str, color: str = "#3498db") -> "ExhibitTag":
        """Create a new tag."""
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            color=color
        )

    def to_dict(self) -> dict:
        return {'id': self.id, 'name': self.name, 'color': self.color}

    @classmethod
    def from_dict(cls, data: dict) -> "ExhibitTag":
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            color=data.get('color', '#3498db')
        )


# Default tags for common exhibit types
DEFAULT_TAGS = [
    ExhibitTag.create("Contract", "#2ecc71"),
    ExhibitTag.create("Invoice", "#e74c3c"),
    ExhibitTag.create("Photo", "#9b59b6"),
    ExhibitTag.create("Email", "#3498db"),
    ExhibitTag.create("Medical", "#1abc9c"),
    ExhibitTag.create("Financial", "#f39c12"),
    ExhibitTag.create("Government", "#34495e"),
    ExhibitTag.create("Correspondence", "#95a5a6"),
]


# File type mappings
FILE_TYPE_EXTENSIONS = {
    'pdf': ['pdf'],
    'image': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif', 'webp'],
    'document': ['doc', 'docx', 'txt', 'rtf', 'odt'],
    'spreadsheet': ['xls', 'xlsx', 'csv', 'ods'],
    'presentation': ['ppt', 'pptx', 'odp'],
    'video': ['mp4', 'avi', 'mov', 'mkv', 'wmv'],
    'audio': ['mp3', 'wav', 'aac', 'flac', 'm4a'],
}


def get_file_type(filename: str) -> str:
    """Determine file type from extension."""
    ext = filename.lower().split('.')[-1] if '.' in filename else ''
    for file_type, extensions in FILE_TYPE_EXTENSIONS.items():
        if ext in extensions:
            return file_type
    return 'other'
