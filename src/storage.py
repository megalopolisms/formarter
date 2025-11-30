"""
Document storage manager for persisting saved documents.

Handles:
- JSON file storage for document metadata and content
- PDF file storage alongside documents
- CRUD operations (create, read, update, delete)
- Cross-device sync via Dropbox (tries multiple paths)
- Filing system with Case → Filing → Document hierarchy
"""

import json
import os
import shutil
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.models.saved_document import SavedDocument
from src.models.document import (
    Tag, PREDEFINED_TAGS, Filing, Case, CommentEntry, EditHistoryEntry, ExhibitFile
)


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
            case_id=original.case_id,
            document_type_index=original.document_type_index,
            custom_title=original.custom_title,
            spacing_before_section=original.spacing_before_section,
            spacing_after_section=original.spacing_after_section,
            spacing_between_paragraphs=original.spacing_between_paragraphs,
            filing_date=original.filing_date,
        )

        return self.save(copy)

    # =========================================================================
    # FILING SYSTEM METHODS
    # =========================================================================

    def _ensure_filing_structure(self, data: dict) -> dict:
        """Ensure the data has the filing system structure."""
        if "tags" not in data:
            # Initialize with predefined tags
            data["tags"] = [
                {"id": t.id, "name": t.name, "color": t.color, "is_predefined": t.is_predefined}
                for t in PREDEFINED_TAGS
            ]

        if "cases" not in data:
            data["cases"] = []

        return data

    def get_tags(self) -> list[Tag]:
        """Get all available tags."""
        data = self._load_documents_file()
        data = self._ensure_filing_structure(data)

        tags = []
        for t in data.get("tags", []):
            tags.append(Tag(
                id=t["id"],
                name=t["name"],
                color=t["color"],
                is_predefined=t.get("is_predefined", False)
            ))
        return tags

    def save_tag(self, tag: Tag) -> Tag:
        """Save a new or updated tag."""
        data = self._load_documents_file()
        data = self._ensure_filing_structure(data)

        tags = data.get("tags", [])

        # Check if tag exists
        existing_index = None
        for i, t in enumerate(tags):
            if t["id"] == tag.id:
                existing_index = i
                break

        tag_dict = {
            "id": tag.id,
            "name": tag.name,
            "color": tag.color,
            "is_predefined": tag.is_predefined
        }

        if existing_index is not None:
            tags[existing_index] = tag_dict
        else:
            tags.append(tag_dict)

        data["tags"] = tags
        self._save_documents_file(data)
        return tag

    def delete_tag(self, tag_id: str) -> bool:
        """Delete a custom tag (predefined tags cannot be deleted)."""
        data = self._load_documents_file()
        data = self._ensure_filing_structure(data)

        tags = data.get("tags", [])
        for i, t in enumerate(tags):
            if t["id"] == tag_id:
                if t.get("is_predefined", False):
                    return False  # Can't delete predefined
                tags.pop(i)
                data["tags"] = tags
                self._save_documents_file(data)
                return True
        return False

    def get_cases(self) -> list[Case]:
        """Get all cases with their filings."""
        data = self._load_documents_file()
        data = self._ensure_filing_structure(data)

        cases = []
        for c in data.get("cases", []):
            filings = []
            for f in c.get("filings", []):
                comment_log = [
                    CommentEntry(timestamp=ce["timestamp"], text=ce["text"])
                    for ce in f.get("comment_log", [])
                ]
                edit_history = [
                    EditHistoryEntry(
                        timestamp=eh["timestamp"],
                        action=eh["action"],
                        details=eh.get("details", "")
                    )
                    for eh in f.get("edit_history", [])
                ]
                exhibit_files = [
                    ExhibitFile(
                        filename=ef["filename"],
                        original_path=ef["original_path"],
                        added_date=ef["added_date"],
                        file_type=ef["file_type"]
                    )
                    for ef in f.get("exhibit_files", [])
                ]

                filing = Filing(
                    id=f["id"],
                    name=f["name"],
                    case_id=f["case_id"],
                    document_ids=f.get("document_ids", []),
                    tags=f.get("tags", []),
                    main_note=f.get("main_note", ""),
                    comment_log=comment_log,
                    status=f.get("status", "draft"),
                    filing_date=f.get("filing_date", ""),
                    created_date=f.get("created_date", ""),
                    edit_history=edit_history,
                    exhibit_files=exhibit_files
                )
                filings.append(filing)

            case = Case(
                id=c["id"],
                name=c["name"],
                case_number=c.get("case_number", ""),
                filings=filings,
                unfiled_document_ids=c.get("unfiled_document_ids", [])
            )
            cases.append(case)

        return cases

    def save_case(self, case: Case) -> Case:
        """Save a new or updated case."""
        data = self._load_documents_file()
        data = self._ensure_filing_structure(data)

        cases = data.get("cases", [])

        case_dict = {
            "id": case.id,
            "name": case.name,
            "case_number": case.case_number,
            "filings": [
                {
                    "id": f.id,
                    "name": f.name,
                    "case_id": f.case_id,
                    "document_ids": f.document_ids,
                    "tags": f.tags,
                    "main_note": f.main_note,
                    "comment_log": [
                        {"timestamp": ce.timestamp, "text": ce.text}
                        for ce in f.comment_log
                    ],
                    "status": f.status,
                    "filing_date": f.filing_date,
                    "created_date": f.created_date,
                    "edit_history": [
                        {"timestamp": eh.timestamp, "action": eh.action, "details": eh.details}
                        for eh in f.edit_history
                    ],
                    "exhibit_files": [
                        {
                            "filename": ef.filename,
                            "original_path": ef.original_path,
                            "added_date": ef.added_date,
                            "file_type": ef.file_type
                        }
                        for ef in f.exhibit_files
                    ]
                }
                for f in case.filings
            ],
            "unfiled_document_ids": case.unfiled_document_ids
        }

        # Check if case exists
        existing_index = None
        for i, c in enumerate(cases):
            if c["id"] == case.id:
                existing_index = i
                break

        if existing_index is not None:
            cases[existing_index] = case_dict
        else:
            cases.append(case_dict)

        data["cases"] = cases
        self._save_documents_file(data)
        return case

    def delete_case(self, case_id: str) -> bool:
        """Delete a case and all its filings."""
        data = self._load_documents_file()
        data = self._ensure_filing_structure(data)

        cases = data.get("cases", [])
        for i, c in enumerate(cases):
            if c["id"] == case_id:
                cases.pop(i)
                data["cases"] = cases
                self._save_documents_file(data)
                return True
        return False

    def get_filing(self, filing_id: str) -> Optional[Filing]:
        """Get a filing by ID."""
        cases = self.get_cases()
        for case in cases:
            for filing in case.filings:
                if filing.id == filing_id:
                    return filing
        return None

    def save_filing(self, filing: Filing) -> Filing:
        """Save a filing (updates the parent case)."""
        cases = self.get_cases()
        for case in cases:
            if case.id == filing.case_id:
                # Find or add filing
                found = False
                for i, f in enumerate(case.filings):
                    if f.id == filing.id:
                        case.filings[i] = filing
                        found = True
                        break
                if not found:
                    case.filings.append(filing)
                self.save_case(case)
                return filing
        return filing

    def delete_filing(self, filing_id: str) -> bool:
        """Delete a filing."""
        cases = self.get_cases()
        for case in cases:
            for i, f in enumerate(case.filings):
                if f.id == filing_id:
                    case.filings.pop(i)
                    self.save_case(case)
                    return True
        return False

    def create_filing(self, name: str, case_id: str) -> Filing:
        """Create a new filing in a case."""
        now = datetime.now().isoformat()
        filing = Filing(
            id=str(uuid.uuid4()),
            name=name,
            case_id=case_id,
            created_date=now,
            edit_history=[
                EditHistoryEntry(timestamp=now, action="created", details=f"Filing '{name}' created")
            ]
        )
        return self.save_filing(filing)

    def create_case(self, name: str, case_number: str = "") -> Case:
        """Create a new case."""
        case = Case(
            id=str(uuid.uuid4()),
            name=name,
            case_number=case_number
        )
        return self.save_case(case)

    def move_document_to_filing(self, doc_id: str, filing_id: str) -> bool:
        """Move a document into a filing."""
        cases = self.get_cases()

        # First, remove from any existing location
        for case in cases:
            if doc_id in case.unfiled_document_ids:
                case.unfiled_document_ids.remove(doc_id)
                self.save_case(case)
            for filing in case.filings:
                if doc_id in filing.document_ids:
                    filing.document_ids.remove(doc_id)
                    self.save_filing(filing)

        # Then add to target filing
        filing = self.get_filing(filing_id)
        if filing:
            filing.document_ids.append(doc_id)
            filing.edit_history.append(
                EditHistoryEntry(
                    timestamp=datetime.now().isoformat(),
                    action="document_added",
                    details=f"Document {doc_id} added"
                )
            )
            self.save_filing(filing)
            return True
        return False

    def move_document_to_unfiled(self, doc_id: str, case_id: str) -> bool:
        """Move a document to unfiled in a case."""
        cases = self.get_cases()

        # First, remove from any filing
        for case in cases:
            for filing in case.filings:
                if doc_id in filing.document_ids:
                    filing.document_ids.remove(doc_id)
                    self.save_filing(filing)

        # Add to unfiled
        for case in cases:
            if case.id == case_id:
                if doc_id not in case.unfiled_document_ids:
                    case.unfiled_document_ids.append(doc_id)
                    self.save_case(case)
                return True
        return False

    def add_comment_to_filing(self, filing_id: str, text: str) -> bool:
        """Add a comment to a filing's log."""
        filing = self.get_filing(filing_id)
        if filing:
            filing.comment_log.append(
                CommentEntry(timestamp=datetime.now().isoformat(), text=text)
            )
            self.save_filing(filing)
            return True
        return False

    def set_filing_tags(self, filing_id: str, tag_ids: list[str]) -> bool:
        """Set tags for a filing."""
        filing = self.get_filing(filing_id)
        if filing:
            filing.tags = tag_ids
            self.save_filing(filing)
            return True
        return False

    def get_exhibits_dir(self, filing_id: str) -> Path:
        """Get the exhibits directory for a filing."""
        exhibits_dir = self.storage_dir / "exhibits" / filing_id
        exhibits_dir.mkdir(parents=True, exist_ok=True)
        return exhibits_dir

    def add_exhibit_file(self, filing_id: str, source_path: str) -> Optional[ExhibitFile]:
        """Add an exhibit file to a filing."""
        filing = self.get_filing(filing_id)
        if not filing:
            return None

        source = Path(source_path)
        if not source.exists():
            return None

        # Copy file to exhibits directory
        exhibits_dir = self.get_exhibits_dir(filing_id)
        dest = exhibits_dir / source.name

        # Handle duplicate filenames
        counter = 1
        while dest.exists():
            stem = source.stem
            suffix = source.suffix
            dest = exhibits_dir / f"{stem}_{counter}{suffix}"
            counter += 1

        shutil.copy2(source, dest)

        # Create exhibit record
        exhibit = ExhibitFile(
            filename=dest.name,
            original_path=str(source),
            added_date=datetime.now().isoformat(),
            file_type=source.suffix.lstrip(".")
        )

        filing.exhibit_files.append(exhibit)
        filing.edit_history.append(
            EditHistoryEntry(
                timestamp=datetime.now().isoformat(),
                action="exhibit_added",
                details=f"Added exhibit: {exhibit.filename}"
            )
        )
        self.save_filing(filing)

        return exhibit

    def remove_exhibit_file(self, filing_id: str, filename: str) -> bool:
        """Remove an exhibit file from a filing."""
        filing = self.get_filing(filing_id)
        if not filing:
            return False

        for i, ef in enumerate(filing.exhibit_files):
            if ef.filename == filename:
                # Delete file
                exhibits_dir = self.get_exhibits_dir(filing_id)
                file_path = exhibits_dir / filename
                if file_path.exists():
                    file_path.unlink()

                # Remove from list
                filing.exhibit_files.pop(i)
                filing.edit_history.append(
                    EditHistoryEntry(
                        timestamp=datetime.now().isoformat(),
                        action="exhibit_removed",
                        details=f"Removed exhibit: {filename}"
                    )
                )
                self.save_filing(filing)
                return True

        return False

    def migrate_to_filing_system(self) -> bool:
        """
        Migrate existing documents to the filing system structure.

        Creates a default case and moves all existing documents to unfiled.
        """
        data = self._load_documents_file()

        # Already migrated if cases exist
        if "cases" in data and data["cases"]:
            return False

        data = self._ensure_filing_structure(data)

        # Create default case if documents exist
        documents = data.get("documents", [])
        if documents:
            # Group by case_profile_index
            case_profiles = {}
            for doc in documents:
                profile_idx = doc.get("case_profile_index", 0)
                if profile_idx not in case_profiles:
                    case_profiles[profile_idx] = []
                case_profiles[profile_idx].append(doc["id"])

            # Create cases for each profile
            cases = []
            case_names = {
                0: "Default Case",
                1: "Case 130",
                2: "Case 131",
                3: "Case 178 - Petrini v. Biloxi",
            }

            for profile_idx, doc_ids in case_profiles.items():
                case = {
                    "id": str(uuid.uuid4()),
                    "name": case_names.get(profile_idx, f"Case {profile_idx}"),
                    "case_number": "",
                    "filings": [],
                    "unfiled_document_ids": doc_ids
                }
                cases.append(case)

            data["cases"] = cases

        self._save_documents_file(data)
        return True
