"""
Exhibit Bank storage manager.

Handles storage, retrieval, and search of exhibits (PDFs, images, documents)
with metadata, tags, and redaction support.
"""

import json
import shutil
import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime

try:
    import fitz  # pymupdf
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from src.models.exhibit import (
    Exhibit, ExhibitTag, DEFAULT_TAGS, get_file_type
)


def get_default_exhibit_path() -> Path:
    """Get the default exhibit bank storage path."""
    return Path.home() / "Dropbox/Formarter Folder/exhibit_bank"


class ExhibitBank:
    """
    Manages the exhibit bank storage.

    Stores exhibits (PDFs, images, documents) in a Dropbox-synced folder
    with a JSON index for metadata.
    """

    INDEX_FILENAME = "index.json"
    THUMBNAILS_DIR = "thumbnails"
    REDACTED_DIR = "redacted"

    def __init__(self, storage_dir: Path = None):
        """
        Initialize the exhibit bank.

        Args:
            storage_dir: Path to storage directory. Uses default if None.
        """
        self.storage_dir = Path(storage_dir) if storage_dir else get_default_exhibit_path()
        self._ensure_storage_exists()
        self._load_index()

    def _ensure_storage_exists(self):
        """Create storage directories if they don't exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        (self.storage_dir / self.THUMBNAILS_DIR).mkdir(exist_ok=True)
        (self.storage_dir / self.REDACTED_DIR).mkdir(exist_ok=True)

    def _load_index(self):
        """Load the index from disk."""
        index_path = self.storage_dir / self.INDEX_FILENAME
        if index_path.exists():
            try:
                with open(index_path, 'r') as f:
                    data = json.load(f)
                self._tags = [
                    ExhibitTag.from_dict(t) for t in data.get("tags", [])
                ]
                self._exhibits = [
                    Exhibit.from_dict(e) for e in data.get("exhibits", [])
                ]
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading exhibit index: {e}")
                self._tags = list(DEFAULT_TAGS)
                self._exhibits = []
        else:
            self._tags = list(DEFAULT_TAGS)
            self._exhibits = []
            self._save_index()

    def _save_index(self):
        """Save the index to disk."""
        index_path = self.storage_dir / self.INDEX_FILENAME
        data = {
            "tags": [t.to_dict() for t in self._tags],
            "exhibits": [e.to_dict() for e in self._exhibits]
        }
        with open(index_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ========== Exhibit Management ==========

    def add_exhibit(
        self,
        file_path: str,
        title: str,
        tags: List[str] = None,
        description: str = "",
        notes: str = "",
        source: str = ""
    ) -> Exhibit:
        """
        Add an exhibit to the bank.

        Args:
            file_path: Path to the source file.
            title: Short descriptive title.
            tags: List of tag names.
            description: Longer description.
            notes: Additional notes.
            source: Where this exhibit came from.

        Returns:
            The created Exhibit object.
        """
        src_path = Path(file_path)
        if not src_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Determine file type
        file_type = get_file_type(src_path.name)

        # Create exhibit object
        exhibit = Exhibit.create(
            title=title,
            original_filename=src_path.name,
            file_type=file_type,
            tags=tags or [],
            description=description,
            notes=notes,
            source=source
        )

        # Copy file to storage
        dest_path = self.storage_dir / exhibit.stored_filename
        shutil.copy2(src_path, dest_path)

        # Update file size
        exhibit.file_size = dest_path.stat().st_size

        # Generate thumbnail and get page count
        if file_type == 'pdf':
            exhibit.page_count = self._get_pdf_page_count(dest_path)
            self._generate_pdf_thumbnail(dest_path, exhibit.thumbnail_filename)
        elif file_type == 'image':
            self._generate_image_thumbnail(dest_path, exhibit.thumbnail_filename)

        # Add to index
        self._exhibits.append(exhibit)
        self._save_index()

        return exhibit

    def update_exhibit(self, exhibit_id: str, **kwargs) -> Optional[Exhibit]:
        """
        Update exhibit metadata.

        Args:
            exhibit_id: ID of exhibit to update.
            **kwargs: Fields to update (title, description, tags, notes, source).

        Returns:
            Updated exhibit or None if not found.
        """
        for i, exhibit in enumerate(self._exhibits):
            if exhibit.id == exhibit_id:
                # Update allowed fields
                if 'title' in kwargs:
                    exhibit.title = kwargs['title']
                if 'description' in kwargs:
                    exhibit.description = kwargs['description']
                if 'tags' in kwargs:
                    exhibit.tags = kwargs['tags']
                if 'notes' in kwargs:
                    exhibit.notes = kwargs['notes']
                if 'source' in kwargs:
                    exhibit.source = kwargs['source']

                exhibit.date_modified = datetime.now().isoformat()
                self._exhibits[i] = exhibit
                self._save_index()
                return exhibit
        return None

    def delete_exhibit(self, exhibit_id: str) -> bool:
        """
        Delete an exhibit and its files.

        Args:
            exhibit_id: ID of exhibit to delete.

        Returns:
            True if deleted, False if not found.
        """
        for i, exhibit in enumerate(self._exhibits):
            if exhibit.id == exhibit_id:
                # Delete files
                stored_path = self.storage_dir / exhibit.stored_filename
                if stored_path.exists():
                    stored_path.unlink()

                thumb_path = self.storage_dir / self.THUMBNAILS_DIR / exhibit.thumbnail_filename
                if thumb_path.exists():
                    thumb_path.unlink()

                if exhibit.has_redacted_version:
                    redacted_path = self.storage_dir / self.REDACTED_DIR / exhibit.redacted_filename
                    if redacted_path.exists():
                        redacted_path.unlink()

                # Remove from index
                del self._exhibits[i]
                self._save_index()
                return True
        return False

    def get_exhibit(self, exhibit_id: str) -> Optional[Exhibit]:
        """Get exhibit by ID."""
        for exhibit in self._exhibits:
            if exhibit.id == exhibit_id:
                return exhibit
        return None

    def list_all(self) -> List[Exhibit]:
        """List all exhibits."""
        return list(self._exhibits)

    def search(
        self,
        query: str = "",
        tags: List[str] = None,
        file_type: str = None
    ) -> List[Exhibit]:
        """
        Search exhibits.

        Args:
            query: Search in title, description, notes.
            tags: Filter by tags (any match).
            file_type: Filter by file type.

        Returns:
            List of matching exhibits.
        """
        results = self._exhibits

        if query:
            query_lower = query.lower()
            results = [
                e for e in results
                if query_lower in e.title.lower()
                or query_lower in e.description.lower()
                or query_lower in e.notes.lower()
                or query_lower in e.original_filename.lower()
            ]

        if tags:
            results = [
                e for e in results
                if any(t in e.tags for t in tags)
            ]

        if file_type:
            results = [e for e in results if e.file_type == file_type]

        return results

    def get_file_path(self, exhibit_id: str) -> Optional[Path]:
        """Get the file path for an exhibit."""
        exhibit = self.get_exhibit(exhibit_id)
        if exhibit:
            return self.storage_dir / exhibit.stored_filename
        return None

    def get_thumbnail_path(self, exhibit_id: str) -> Optional[Path]:
        """Get the thumbnail path for an exhibit."""
        exhibit = self.get_exhibit(exhibit_id)
        if exhibit:
            thumb_path = self.storage_dir / self.THUMBNAILS_DIR / exhibit.thumbnail_filename
            if thumb_path.exists():
                return thumb_path
        return None

    # ========== Tag Management ==========

    def list_tags(self) -> List[ExhibitTag]:
        """List all tags."""
        return list(self._tags)

    def add_tag(self, name: str, color: str = "#3498db") -> ExhibitTag:
        """Add a new tag."""
        tag = ExhibitTag.create(name, color)
        self._tags.append(tag)
        self._save_index()
        return tag

    def delete_tag(self, tag_id: str) -> bool:
        """Delete a tag."""
        for i, tag in enumerate(self._tags):
            if tag.id == tag_id:
                del self._tags[i]
                self._save_index()
                return True
        return False

    def get_exhibits_by_tag(self, tag_name: str) -> List[Exhibit]:
        """Get all exhibits with a specific tag."""
        return [e for e in self._exhibits if tag_name in e.tags]

    # ========== Thumbnail Generation ==========

    def _get_pdf_page_count(self, pdf_path: Path) -> int:
        """Get page count from PDF."""
        if not HAS_PYMUPDF:
            return 0
        try:
            doc = fitz.open(str(pdf_path))
            count = len(doc)
            doc.close()
            return count
        except:
            return 0

    def _generate_pdf_thumbnail(self, pdf_path: Path, thumb_filename: str):
        """Generate thumbnail from first page of PDF."""
        if not HAS_PYMUPDF:
            return

        try:
            doc = fitz.open(str(pdf_path))
            if len(doc) > 0:
                page = doc[0]
                # Render at 150 DPI for thumbnail
                mat = fitz.Matrix(150/72, 150/72)
                pix = page.get_pixmap(matrix=mat)

                thumb_path = self.storage_dir / self.THUMBNAILS_DIR / thumb_filename
                pix.save(str(thumb_path))
            doc.close()
        except Exception as e:
            print(f"Error generating PDF thumbnail: {e}")

    def _generate_image_thumbnail(self, image_path: Path, thumb_filename: str):
        """Generate thumbnail from image."""
        if not HAS_PIL:
            return

        try:
            img = Image.open(str(image_path))
            # Create thumbnail (max 200x200)
            img.thumbnail((200, 200))

            thumb_path = self.storage_dir / self.THUMBNAILS_DIR / thumb_filename
            img.save(str(thumb_path), "PNG")
        except Exception as e:
            print(f"Error generating image thumbnail: {e}")

    # ========== Redaction Support ==========

    def create_redacted_version(
        self,
        exhibit_id: str,
        redactions: List[dict]
    ) -> Optional[str]:
        """
        Create a redacted version of a PDF exhibit.

        Args:
            exhibit_id: ID of exhibit to redact.
            redactions: List of redaction specs with page, x, y, width, height.

        Returns:
            Path to redacted file or None if failed.
        """
        if not HAS_PYMUPDF:
            return None

        exhibit = self.get_exhibit(exhibit_id)
        if not exhibit or exhibit.file_type != 'pdf':
            return None

        src_path = self.storage_dir / exhibit.stored_filename
        redacted_filename = f"{exhibit.id}_redacted.pdf"
        dest_path = self.storage_dir / self.REDACTED_DIR / redacted_filename

        try:
            doc = fitz.open(str(src_path))

            for redaction in redactions:
                page_num = redaction.get('page', 0)
                if page_num < len(doc):
                    page = doc[page_num]
                    rect = fitz.Rect(
                        redaction['x'],
                        redaction['y'],
                        redaction['x'] + redaction['width'],
                        redaction['y'] + redaction['height']
                    )
                    # Add redaction annotation
                    page.add_redact_annot(rect, fill=(0, 0, 0))

            # Apply all redactions
            for page in doc:
                page.apply_redactions()

            doc.save(str(dest_path))
            doc.close()

            # Update exhibit
            exhibit.has_redacted_version = True
            exhibit.redacted_filename = redacted_filename
            exhibit.date_modified = datetime.now().isoformat()
            self._save_index()

            return str(dest_path)

        except Exception as e:
            print(f"Error creating redacted version: {e}")
            return None

    def get_redacted_path(self, exhibit_id: str) -> Optional[Path]:
        """Get path to redacted version of exhibit."""
        exhibit = self.get_exhibit(exhibit_id)
        if exhibit and exhibit.has_redacted_version:
            return self.storage_dir / self.REDACTED_DIR / exhibit.redacted_filename
        return None

    # ========== Statistics ==========

    def get_stats(self) -> dict:
        """Get statistics about the exhibit bank."""
        total_size = sum(e.file_size for e in self._exhibits)
        type_counts = {}
        for e in self._exhibits:
            type_counts[e.file_type] = type_counts.get(e.file_type, 0) + 1

        return {
            'total_exhibits': len(self._exhibits),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'by_type': type_counts,
            'total_tags': len(self._tags),
            'redacted_count': sum(1 for e in self._exhibits if e.has_redacted_version)
        }
