"""
Document storage manager for persisting saved documents.

Handles:
- JSON file storage for document metadata and content
- PDF file storage alongside documents
- CRUD operations (create, read, update, delete)
- Cross-device sync via Dropbox (tries multiple paths)
"""

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

from src.models.saved_document import SavedDocument


# Default storage paths to try (in order of priority)
# Dropbox paths for different platforms
DEFAULT_STORAGE_PATHS = [
    # macOS Dropbox path (both Macs)
    Path.home() / "Dropbox" / "Formarter Folder",
    # Windows Dropbox paths (common locations)
    Path("C:/Users") / os.getenv("USERNAME", "") / "Dropbox" / "Formarter Folder" if sys.platform == "win32" else None,
    Path("D:/Dropbox/Formarter Folder") if sys.platform == "win32" else None,
    # Fallback to local storage
    Path.home() / ".formarter",
]


class DocumentStorage:
    """
    Manages persistent storage of saved documents.

    Documents are stored in a JSON file with PDFs saved in a subdirectory.
    Default location: Dropbox/Formarter Folder (for cross-device sync)
    Fallback: ~/.formarter/
    """

    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize storage manager.

        Args:
            storage_dir: Custom storage directory. If not provided, tries
                         Dropbox paths first, then falls back to local storage.
        """
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            self.storage_dir = self._find_storage_path()

        self.documents_file = self.storage_dir / "documents.json"
        self.pdfs_dir = self.storage_dir / "pdfs"

        # Ensure directories exist
        self._ensure_directories()

    def _find_storage_path(self) -> Path:
        """
        Find the first available storage path from the default list.

        Tries Dropbox paths first for cross-device sync, falls back to local.
        """
        for path in DEFAULT_STORAGE_PATHS:
            if path is None:
                continue
            # Check if parent directory exists (Dropbox folder)
            if path.parent.exists():
                return path
        # Ultimate fallback
        return Path.home() / ".formarter"

    def get_storage_location(self) -> str:
        """Get the current storage location path as a string."""
        return str(self.storage_dir)

    def _ensure_directories(self):
        """Create storage directories if they don't exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.pdfs_dir.mkdir(parents=True, exist_ok=True)

    def _load_documents_file(self) -> dict:
        """Load the documents JSON file."""
        if not self.documents_file.exists():
            return {"documents": []}

        try:
            with open(self.documents_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # If file is corrupted, start fresh
            return {"documents": []}

    def _save_documents_file(self, data: dict):
        """Save data to the documents JSON file."""
        with open(self.documents_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def list_all(self) -> list[SavedDocument]:
        """
        Get all saved documents.

        Returns:
            List of SavedDocument objects, sorted by modified date (newest first).
        """
        data = self._load_documents_file()
        documents = [SavedDocument.from_dict(d) for d in data.get("documents", [])]

        # Sort by modified date, newest first
        documents.sort(key=lambda d: d.modified_at, reverse=True)
        return documents

    def get_by_id(self, doc_id: str) -> Optional[SavedDocument]:
        """
        Get a document by its ID.

        Args:
            doc_id: The document's unique identifier.

        Returns:
            SavedDocument if found, None otherwise.
        """
        data = self._load_documents_file()
        for doc_dict in data.get("documents", []):
            if doc_dict.get("id") == doc_id:
                return SavedDocument.from_dict(doc_dict)
        return None

    def save(self, document: SavedDocument) -> SavedDocument:
        """
        Save or update a document.

        If document with same ID exists, it will be updated.
        Otherwise, a new document is created.

        Args:
            document: The SavedDocument to save.

        Returns:
            The saved document (with updated modified timestamp).
        """
        document.update_modified()

        data = self._load_documents_file()
        documents = data.get("documents", [])

        # Check if document exists
        existing_index = None
        for i, doc_dict in enumerate(documents):
            if doc_dict.get("id") == document.id:
                existing_index = i
                break

        if existing_index is not None:
            # Update existing
            documents[existing_index] = document.to_dict()
        else:
            # Add new
            documents.append(document.to_dict())

        data["documents"] = documents
        self._save_documents_file(data)

        return document

    def delete(self, doc_id: str) -> bool:
        """
        Delete a document by ID.

        Also removes associated PDF file if it exists.

        Args:
            doc_id: The document's unique identifier.

        Returns:
            True if document was deleted, False if not found.
        """
        data = self._load_documents_file()
        documents = data.get("documents", [])

        # Find and remove document
        for i, doc_dict in enumerate(documents):
            if doc_dict.get("id") == doc_id:
                # Delete associated PDF if it exists
                pdf_filename = doc_dict.get("pdf_filename")
                if pdf_filename:
                    pdf_path = self.pdfs_dir / pdf_filename
                    if pdf_path.exists():
                        pdf_path.unlink()

                # Remove from list
                documents.pop(i)
                data["documents"] = documents
                self._save_documents_file(data)
                return True

        return False

    def rename(self, doc_id: str, new_name: str) -> Optional[SavedDocument]:
        """
        Rename a document.

        Args:
            doc_id: The document's unique identifier.
            new_name: The new name for the document.

        Returns:
            Updated SavedDocument if found, None otherwise.
        """
        document = self.get_by_id(doc_id)
        if document:
            document.name = new_name
            return self.save(document)
        return None

    def save_pdf(self, doc_id: str, source_pdf_path: str) -> Optional[str]:
        """
        Save a PDF file for a document.

        Copies the PDF to the storage directory and updates the document.

        Args:
            doc_id: The document's unique identifier.
            source_pdf_path: Path to the PDF file to save.

        Returns:
            The PDF filename if successful, None otherwise.
        """
        document = self.get_by_id(doc_id)
        if not document:
            return None

        if not os.path.exists(source_pdf_path):
            return None

        # Generate unique filename
        pdf_filename = f"{doc_id}.pdf"
        dest_path = self.pdfs_dir / pdf_filename

        # Copy PDF to storage
        shutil.copy2(source_pdf_path, dest_path)

        # Update document with PDF reference
        document.pdf_filename = pdf_filename
        self.save(document)

        return pdf_filename

    def get_pdf_path(self, doc_id: str) -> Optional[Path]:
        """
        Get the full path to a document's PDF.

        Args:
            doc_id: The document's unique identifier.

        Returns:
            Path to PDF if it exists, None otherwise.
        """
        document = self.get_by_id(doc_id)
        if not document or not document.pdf_filename:
            return None

        pdf_path = self.pdfs_dir / document.pdf_filename
        if pdf_path.exists():
            return pdf_path
        return None

    def create_new(self, name: str = "Untitled Document") -> SavedDocument:
        """
        Create a new empty document.

        Args:
            name: Name for the new document.

        Returns:
            The newly created SavedDocument.
        """
        document = SavedDocument(name=name)
        return self.save(document)

    def duplicate(self, doc_id: str, new_name: Optional[str] = None) -> Optional[SavedDocument]:
        """
        Duplicate an existing document.

        Args:
            doc_id: ID of document to duplicate.
            new_name: Name for the copy. Defaults to "Copy of {original name}".

        Returns:
            The new document copy, or None if original not found.
        """
        original = self.get_by_id(doc_id)
        if not original:
            return None

        # Create copy with new ID
        copy = SavedDocument(
            name=new_name or f"Copy of {original.name}",
            text_content=original.text_content,
            sections=original.sections.copy(),
            case_profile_index=original.case_profile_index,
            document_type_index=original.document_type_index,
            custom_title=original.custom_title,
            spacing_before_section=original.spacing_before_section,
            spacing_after_section=original.spacing_after_section,
            spacing_between_paragraphs=original.spacing_between_paragraphs,
            filing_date=original.filing_date,
        )

        return self.save(copy)
