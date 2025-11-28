"""
Lawsuit model - unifies docket, exhibits, templates, and case data.

A Lawsuit is the central entity that connects:
- Case information (number, court, parties)
- Docket entries with attached documents
- Exhibits from the Exhibit Bank
- Document templates
- Full text exports (TXT/JSON)
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

try:
    import fitz  # pymupdf
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


@dataclass
class Lawsuit:
    """Represents a lawsuit/case with all associated data."""

    id: str
    case_number: str  # e.g., "178" or "1:25-cv-00178-LG-RPM"
    short_name: str   # e.g., "Petrini v. City of Biloxi"
    court: str        # e.g., "U.S. District Court, Southern District of Mississippi"
    judge: str        # e.g., "Louis Guirola, Jr."
    magistrate: str   # e.g., "Robert P. Myers, Jr."
    date_filed: str
    plaintiff: str
    defendant: str
    case_type: str    # e.g., "Civil Rights"
    status: str       # e.g., "Open", "Closed"
    exhibit_tag: str  # Tag name in Exhibit Bank for this case
    notes: str
    date_created: str
    date_modified: str

    @classmethod
    def create(
        cls,
        case_number: str,
        short_name: str,
        court: str = "",
        judge: str = "",
        magistrate: str = "",
        date_filed: str = "",
        plaintiff: str = "",
        defendant: str = "",
        case_type: str = "",
        notes: str = ""
    ) -> "Lawsuit":
        """Create a new lawsuit."""
        lawsuit_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        # Generate exhibit tag from case number
        exhibit_tag = f"Case {case_number}"

        return cls(
            id=lawsuit_id,
            case_number=case_number,
            short_name=short_name,
            court=court,
            judge=judge,
            magistrate=magistrate,
            date_filed=date_filed,
            plaintiff=plaintiff,
            defendant=defendant,
            case_type=case_type,
            status="Open",
            exhibit_tag=exhibit_tag,
            notes=notes,
            date_created=now,
            date_modified=now
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'case_number': self.case_number,
            'short_name': self.short_name,
            'court': self.court,
            'judge': self.judge,
            'magistrate': self.magistrate,
            'date_filed': self.date_filed,
            'plaintiff': self.plaintiff,
            'defendant': self.defendant,
            'case_type': self.case_type,
            'status': self.status,
            'exhibit_tag': self.exhibit_tag,
            'notes': self.notes,
            'date_created': self.date_created,
            'date_modified': self.date_modified
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Lawsuit":
        """Create from dictionary."""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            case_number=data.get('case_number', ''),
            short_name=data.get('short_name', ''),
            court=data.get('court', ''),
            judge=data.get('judge', ''),
            magistrate=data.get('magistrate', ''),
            date_filed=data.get('date_filed', ''),
            plaintiff=data.get('plaintiff', ''),
            defendant=data.get('defendant', ''),
            case_type=data.get('case_type', ''),
            status=data.get('status', 'Open'),
            exhibit_tag=data.get('exhibit_tag', ''),
            notes=data.get('notes', ''),
            date_created=data.get('date_created', datetime.now().isoformat()),
            date_modified=data.get('date_modified', datetime.now().isoformat())
        )


class LawsuitManager:
    """
    Manages lawsuits and provides unified access to all case data.

    Stores lawsuits in a JSON file and provides methods to:
    - Create/update/delete lawsuits
    - Link docket entries and exhibits to lawsuits
    - Extract text from attached PDFs
    - Export full case data as TXT/JSON
    """

    INDEX_FILENAME = "lawsuits.json"

    def __init__(self, storage_dir: Path = None):
        """Initialize the lawsuit manager."""
        if storage_dir is None:
            storage_dir = Path.home() / "Dropbox/Formarter Folder"
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Create lawsuits subdirectory for exports
        self.exports_dir = self.storage_dir / "lawsuits"
        self.exports_dir.mkdir(exist_ok=True)

        self._load_index()

    def _load_index(self):
        """Load the lawsuits index from disk."""
        index_path = self.storage_dir / self.INDEX_FILENAME
        if index_path.exists():
            try:
                with open(index_path, 'r') as f:
                    data = json.load(f)
                self._lawsuits = [
                    Lawsuit.from_dict(l) for l in data.get('lawsuits', [])
                ]
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading lawsuits index: {e}")
                self._lawsuits = []
        else:
            self._lawsuits = []
            self._save_index()

    def _save_index(self):
        """Save the lawsuits index to disk."""
        index_path = self.storage_dir / self.INDEX_FILENAME
        data = {
            'lawsuits': [l.to_dict() for l in self._lawsuits]
        }
        with open(index_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ========== Lawsuit CRUD ==========

    def create_lawsuit(self, **kwargs) -> Lawsuit:
        """Create a new lawsuit."""
        lawsuit = Lawsuit.create(**kwargs)
        self._lawsuits.append(lawsuit)
        self._save_index()
        return lawsuit

    def get_lawsuit(self, lawsuit_id: str) -> Optional[Lawsuit]:
        """Get lawsuit by ID."""
        for lawsuit in self._lawsuits:
            if lawsuit.id == lawsuit_id:
                return lawsuit
        return None

    def get_lawsuit_by_number(self, case_number: str) -> Optional[Lawsuit]:
        """Get lawsuit by case number."""
        for lawsuit in self._lawsuits:
            if lawsuit.case_number == case_number:
                return lawsuit
        return None

    def list_lawsuits(self) -> List[Lawsuit]:
        """List all lawsuits."""
        return list(self._lawsuits)

    def update_lawsuit(self, lawsuit_id: str, **kwargs) -> Optional[Lawsuit]:
        """Update lawsuit fields."""
        for i, lawsuit in enumerate(self._lawsuits):
            if lawsuit.id == lawsuit_id:
                for key, value in kwargs.items():
                    if hasattr(lawsuit, key):
                        setattr(lawsuit, key, value)
                lawsuit.date_modified = datetime.now().isoformat()
                self._lawsuits[i] = lawsuit
                self._save_index()
                return lawsuit
        return None

    def delete_lawsuit(self, lawsuit_id: str) -> bool:
        """Delete a lawsuit."""
        for i, lawsuit in enumerate(self._lawsuits):
            if lawsuit.id == lawsuit_id:
                del self._lawsuits[i]
                self._save_index()
                return True
        return False

    # ========== Docket Integration ==========

    def get_docket_entries(self, case_number: str) -> List[dict]:
        """Get all docket entries for a case."""
        docket_path = self.storage_dir / "dockets" / "index.json"
        if not docket_path.exists():
            return []

        with open(docket_path, 'r') as f:
            data = json.load(f)

        entries = [
            e for e in data.get('entries', [])
            if e.get('case_id') == case_number
        ]
        return sorted(entries, key=lambda x: x.get('docket_number', 0))

    def extract_pdf_text(self, pdf_path: str) -> str:
        """Extract text from a PDF file."""
        if not HAS_PYMUPDF:
            return ""

        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return ""

    def extract_docket_texts(self, case_number: str) -> Dict[int, str]:
        """Extract text from all attached PDFs in docket entries."""
        entries = self.get_docket_entries(case_number)
        texts = {}

        for entry in entries:
            doc_path = entry.get('attached_document')
            if doc_path and Path(doc_path).exists():
                docket_num = entry.get('docket_number', 0)
                text = self.extract_pdf_text(doc_path)
                if text:
                    texts[docket_num] = text
                    # Save individual text file
                    self._save_entry_text(case_number, docket_num, text)

        return texts

    def _save_entry_text(self, case_number: str, docket_num: int, text: str):
        """Save extracted text for a docket entry."""
        case_dir = self.exports_dir / f"case_{case_number}"
        case_dir.mkdir(exist_ok=True)

        txt_path = case_dir / f"docket_{docket_num:03d}.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text)

    # ========== Exhibit Integration ==========

    def get_exhibits(self, case_number: str) -> List[dict]:
        """Get all exhibits tagged with this case."""
        exhibit_path = self.storage_dir / "exhibit_bank" / "index.json"
        if not exhibit_path.exists():
            return []

        with open(exhibit_path, 'r') as f:
            data = json.load(f)

        lawsuit = self.get_lawsuit_by_number(case_number)
        if not lawsuit:
            return []

        tag_name = lawsuit.exhibit_tag
        exhibits = [
            e for e in data.get('exhibits', [])
            if tag_name in e.get('tags', [])
        ]
        return exhibits

    def add_exhibit_tag(self, case_number: str) -> bool:
        """Add the case tag to the exhibit bank if it doesn't exist."""
        exhibit_path = self.storage_dir / "exhibit_bank" / "index.json"
        if not exhibit_path.exists():
            return False

        with open(exhibit_path, 'r') as f:
            data = json.load(f)

        lawsuit = self.get_lawsuit_by_number(case_number)
        tag_name = lawsuit.exhibit_tag if lawsuit else f"Case {case_number}"

        # Check if tag exists
        tags = data.get('tags', [])
        for tag in tags:
            if tag.get('name') == tag_name:
                return True  # Already exists

        # Add new tag
        new_tag = {
            'id': str(uuid.uuid4()),
            'name': tag_name,
            'color': '#e74c3c'  # Red for case tags
        }
        tags.append(new_tag)
        data['tags'] = tags

        with open(exhibit_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return True

    # ========== Export Functions ==========

    def generate_full_docket_txt(self, case_number: str) -> str:
        """Generate a complete text file of the docket."""
        lawsuit = self.get_lawsuit_by_number(case_number)
        entries = self.get_docket_entries(case_number)

        lines = []
        lines.append("=" * 80)
        lines.append(f"DOCKET: Case {case_number}")
        if lawsuit:
            lines.append(f"{lawsuit.short_name}")
            lines.append(f"Court: {lawsuit.court}")
            lines.append(f"Judge: {lawsuit.judge}")
            if lawsuit.magistrate:
                lines.append(f"Magistrate: {lawsuit.magistrate}")
        lines.append("=" * 80)
        lines.append("")

        for entry in entries:
            docket_num = entry.get('docket_number', 0)
            date = entry.get('date', '')
            text = entry.get('text', entry.get('description', ''))
            filed_by = entry.get('filed_by', '')

            lines.append(f"[{docket_num:03d}] {date}")
            lines.append("-" * 40)
            lines.append(text)
            if filed_by:
                lines.append(f"  Filed by: {filed_by}")

            # Include extracted text if available
            doc_path = entry.get('attached_document')
            if doc_path and Path(doc_path).exists():
                lines.append(f"  [Document: {Path(doc_path).name}]")
                extracted = entry.get('extracted_text', '')
                if extracted:
                    lines.append("")
                    lines.append("  --- DOCUMENT TEXT ---")
                    for line in extracted[:2000].split('\n'):
                        lines.append(f"  {line}")
                    if len(extracted) > 2000:
                        lines.append("  [... truncated ...]")

            lines.append("")

        full_text = "\n".join(lines)

        # Save to file
        case_dir = self.exports_dir / f"case_{case_number}"
        case_dir.mkdir(exist_ok=True)
        txt_path = case_dir / "full_docket.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(full_text)

        return str(txt_path)

    def export_case_json(self, case_number: str) -> str:
        """Export complete case data as JSON."""
        lawsuit = self.get_lawsuit_by_number(case_number)
        entries = self.get_docket_entries(case_number)
        exhibits = self.get_exhibits(case_number)

        # Extract texts from PDFs
        texts = self.extract_docket_texts(case_number)

        # Add extracted text to entries
        for entry in entries:
            docket_num = entry.get('docket_number', 0)
            if docket_num in texts:
                entry['extracted_text'] = texts[docket_num]

        data = {
            'case_info': lawsuit.to_dict() if lawsuit else {'case_number': case_number},
            'docket_entries': entries,
            'exhibits': exhibits,
            'export_date': datetime.now().isoformat(),
            'total_entries': len(entries),
            'total_exhibits': len(exhibits),
            'entries_with_documents': len([e for e in entries if e.get('attached_document')])
        }

        # Save to file
        case_dir = self.exports_dir / f"case_{case_number}"
        case_dir.mkdir(exist_ok=True)
        json_path = case_dir / "case_data.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return str(json_path)

    def get_case_summary(self, case_number: str) -> dict:
        """Get a summary of the case data."""
        lawsuit = self.get_lawsuit_by_number(case_number)
        entries = self.get_docket_entries(case_number)
        exhibits = self.get_exhibits(case_number)

        return {
            'case_number': case_number,
            'short_name': lawsuit.short_name if lawsuit else '',
            'status': lawsuit.status if lawsuit else 'Unknown',
            'total_docket_entries': len(entries),
            'entries_with_documents': len([e for e in entries if e.get('attached_document')]),
            'total_exhibits': len(exhibits),
            'latest_entry': entries[-1] if entries else None
        }
