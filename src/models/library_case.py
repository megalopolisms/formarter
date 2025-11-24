"""
Data models for the Case Library feature.

Stores case law PDFs with metadata, categories, and keywords
for organizing legal research materials.
"""

from dataclasses import dataclass, field
from typing import Optional
import uuid
from datetime import datetime


@dataclass
class Category:
    """A category for organizing cases by legal topic."""
    id: str
    name: str
    color: str  # Hex color for UI display

    @classmethod
    def create(cls, name: str, color: str = "#4A90D9") -> "Category":
        """Create a new category with auto-generated ID."""
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            color=color
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Category":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            color=data.get("color", "#4A90D9")
        )


@dataclass
class LibraryCase:
    """A case law entry in the library."""
    id: str
    case_name: str              # "Smith v. Jones"
    volume: str                 # "123"
    reporter: str               # "F.3d"
    page: str                   # "456"
    year: str                   # "2020"
    court: str                  # "5th Cir."
    pdf_filename: str           # "Smith v Jones 123 F3d 456.pdf"
    txt_filename: str           # "Smith v Jones 123 F3d 456.txt"
    bluebook_citation: str      # Full formatted citation
    date_added: str             # ISO timestamp
    category_id: str = ""       # Reference to Category.id
    keywords: list[str] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def create(
        cls,
        case_name: str,
        volume: str,
        reporter: str,
        page: str,
        year: str = "",
        court: str = "",
        category_id: str = "",
        keywords: list[str] = None,
        notes: str = ""
    ) -> "LibraryCase":
        """Create a new library case with auto-generated fields."""
        # Generate filename from citation components
        # Remove periods from reporter for filename
        reporter_clean = reporter.replace(".", "").replace(" ", "")
        case_name_clean = cls._sanitize_filename(case_name)
        base_filename = f"{case_name_clean} {volume} {reporter_clean} {page}"

        # Format Bluebook citation
        bluebook = cls._format_bluebook(case_name, volume, reporter, page, court, year)

        return cls(
            id=str(uuid.uuid4()),
            case_name=case_name,
            volume=volume,
            reporter=reporter,
            page=page,
            year=year,
            court=court,
            pdf_filename=f"{base_filename}.pdf",
            txt_filename=f"{base_filename}.txt",
            bluebook_citation=bluebook,
            date_added=datetime.now().isoformat(),
            category_id=category_id,
            keywords=keywords or [],
            notes=notes
        )

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """Remove/replace unsafe filesystem characters."""
        # Characters not allowed in filenames
        unsafe_chars = '<>:"/\\|?*'
        result = name
        for char in unsafe_chars:
            result = result.replace(char, "")
        # Replace periods in case name (but keep v.)
        result = result.replace("v.", "v")
        return result.strip()

    @staticmethod
    def _format_bluebook(
        case_name: str,
        volume: str,
        reporter: str,
        page: str,
        court: str,
        year: str
    ) -> str:
        """Format a Bluebook citation."""
        # Basic format: Case Name, Volume Reporter Page (Court Year)
        citation = f"{case_name}, {volume} {reporter} {page}"
        if court or year:
            paren_parts = []
            if court:
                paren_parts.append(court)
            if year:
                paren_parts.append(year)
            citation += f" ({' '.join(paren_parts)})"
        return citation

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "case_name": self.case_name,
            "volume": self.volume,
            "reporter": self.reporter,
            "page": self.page,
            "year": self.year,
            "court": self.court,
            "pdf_filename": self.pdf_filename,
            "txt_filename": self.txt_filename,
            "bluebook_citation": self.bluebook_citation,
            "date_added": self.date_added,
            "category_id": self.category_id,
            "keywords": self.keywords,
            "notes": self.notes
        }

    @classmethod
    def from_dict(cls, data: dict) -> "LibraryCase":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            case_name=data["case_name"],
            volume=data["volume"],
            reporter=data["reporter"],
            page=data["page"],
            year=data.get("year", ""),
            court=data.get("court", ""),
            pdf_filename=data["pdf_filename"],
            txt_filename=data["txt_filename"],
            bluebook_citation=data["bluebook_citation"],
            date_added=data["date_added"],
            category_id=data.get("category_id", ""),
            keywords=data.get("keywords", []),
            notes=data.get("notes", "")
        )

    @property
    def short_citation(self) -> str:
        """Get short citation format: Volume Reporter Page."""
        return f"{self.volume} {self.reporter} {self.page}"


@dataclass
class BatchImportResult:
    """Result of a batch import operation."""
    successful: list[LibraryCase] = field(default_factory=list)
    duplicates: list[str] = field(default_factory=list)      # Filenames skipped
    needs_info: list[str] = field(default_factory=list)      # Couldn't parse
    errors: list[tuple[str, str]] = field(default_factory=list)  # (filename, error)

    @property
    def total_processed(self) -> int:
        """Total number of files processed."""
        return (
            len(self.successful) +
            len(self.duplicates) +
            len(self.needs_info) +
            len(self.errors)
        )

    @property
    def summary(self) -> str:
        """Get a summary string of the import results."""
        parts = []
        if self.successful:
            parts.append(f"{len(self.successful)} imported")
        if self.duplicates:
            parts.append(f"{len(self.duplicates)} duplicates skipped")
        if self.needs_info:
            parts.append(f"{len(self.needs_info)} need citation info")
        if self.errors:
            parts.append(f"{len(self.errors)} errors")
        return ", ".join(parts) if parts else "No files processed"


# Default categories for legal research
DEFAULT_CATEGORIES = [
    Category.create("Civil Rights", "#4A90D9"),
    Category.create("Excessive Force", "#D94A4A"),
    Category.create("Qualified Immunity", "#9B59B6"),
    Category.create("Municipal Liability", "#E67E22"),
    Category.create("Due Process", "#27AE60"),
    Category.create("Equal Protection", "#16A085"),
    Category.create("First Amendment", "#2980B9"),
    Category.create("Fourth Amendment", "#8E44AD"),
    Category.create("Employment", "#F39C12"),
    Category.create("Contract", "#1ABC9C"),
    Category.create("Torts", "#E74C3C"),
    Category.create("Procedure", "#95A5A6"),
]

# Common legal reporters for dropdown
REPORTERS = [
    # Federal
    "F.4th", "F.3d", "F.2d", "F.",
    "F. Supp. 3d", "F. Supp. 2d", "F. Supp.",
    "F. App'x",
    "B.R.",
    # Supreme Court
    "U.S.", "S. Ct.", "L. Ed. 2d", "L. Ed.",
    # State - Southern (MS, LA, AL, FL)
    "So. 3d", "So. 2d", "So.",
    "Miss.",
    # Regional
    "N.E.3d", "N.E.2d", "N.E.",
    "N.W.2d", "N.W.",
    "P.3d", "P.2d", "P.",
    "S.E.2d", "S.E.",
    "S.W.3d", "S.W.2d", "S.W.",
    "A.3d", "A.2d", "A.",
    # California
    "Cal. Rptr. 3d", "Cal. Rptr. 2d", "Cal. Rptr.",
    # New York
    "N.Y.S.3d", "N.Y.S.2d",
]

# Common court abbreviations for dropdown
COURTS = [
    # Federal Circuit Courts
    "1st Cir.", "2d Cir.", "3d Cir.", "4th Cir.", "5th Cir.",
    "6th Cir.", "7th Cir.", "8th Cir.", "9th Cir.", "10th Cir.",
    "11th Cir.", "D.C. Cir.", "Fed. Cir.",
    # Mississippi District Courts
    "S.D. Miss.", "N.D. Miss.",
    # Other common districts
    "E.D. La.", "W.D. La.", "M.D. La.",
    "S.D. Tex.", "N.D. Tex.", "E.D. Tex.", "W.D. Tex.",
    "S.D.N.Y.", "E.D.N.Y.",
    # State Courts
    "Miss.", "Miss. Ct. App.",
    "La.", "La. Ct. App.",
    "Ala.", "Ala. Civ. App.",
    # Leave blank for U.S. Supreme Court (reporter indicates it)
    "",
]
