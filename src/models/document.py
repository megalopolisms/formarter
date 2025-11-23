"""
Document data model for federal court filings.

Structure:
- Document contains Sections (I, II, III...)
- Sections may contain SubItems (a, b, c...)
- Paragraphs are numbered CONTINUOUSLY (1, 2, 3...) through entire document
- Each Paragraph belongs to a Section and optionally a SubItem
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CaseCaption:
    """
    Federal court case caption/header information.
    Appears at the top of every document.
    """
    court: str = "IN THE UNITED STATES DISTRICT COURT\nFOR THE SOUTHERN DISTRICT OF MISSISSIPPI"
    plaintiff: str = ""
    defendant: str = ""
    case_number: str = ""


@dataclass
class SignatureBlock:
    """
    Signature block and certificate of service information.
    Appears at the end of every document.
    """
    attorney_name: str = ""
    bar_number: str = ""
    firm_name: str = ""
    address: str = ""
    phone: str = ""
    email: str = ""
    # Certificate of Service is auto-generated with ECF language


@dataclass
class CaseProfile:
    """
    Pre-configured case profile for quick selection.
    Contains caption and signature info for a specific lawsuit.
    """
    name: str  # Display name for dropdown (e.g., "178 - Petrini v. Biloxi")
    caption: CaseCaption
    signature: SignatureBlock


@dataclass
class SpacingSettings:
    """
    Spacing settings for document formatting.
    Values represent number of blank lines (0, 1, or 2).
    """
    before_section: int = 1  # Lines before section header
    after_section: int = 1   # Lines after section header (before first para)
    between_paragraphs: int = 1  # Lines between paragraphs


@dataclass
class Paragraph:
    """
    A single numbered paragraph in the document.

    Paragraph numbers are CONTINUOUS throughout the entire document,
    regardless of which section or sub-item they belong to.
    """
    number: int  # Continuous number (1, 2, 3... through entire doc)
    text: str
    section_id: str  # Which section this belongs to (e.g., "I", "II")
    subitem_id: Optional[str] = None  # Optional sub-item (e.g., "a", "b")

    def get_display_text(self, max_length: int = 60) -> str:
        """Get truncated text for tree display."""
        if len(self.text) > max_length:
            return self.text[:max_length] + "..."
        return self.text


@dataclass
class SubItem:
    """
    A sub-item within a section (a, b, c...).

    Sub-items group related paragraphs within a section.
    Sub-item letters restart for each section.
    """
    id: str  # Letter identifier (a, b, c...)
    title: Optional[str] = None  # Optional descriptive title
    paragraph_ids: list[int] = field(default_factory=list)  # Paragraph numbers in this sub-item


@dataclass
class Section:
    """
    A major section of the document (I, II, III...).

    Sections organize the document but do NOT affect paragraph numbering.
    Section headers appear centered/bold in the final document.
    """
    id: str  # Roman numeral identifier (I, II, III...)
    title: str  # Section title (e.g., "PARTIES", "JURISDICTION")
    subitems: list[SubItem] = field(default_factory=list)
    paragraph_ids: list[int] = field(default_factory=list)  # Paragraphs directly in section (no sub-item)
    custom_spacing: Optional[SpacingSettings] = None  # Per-section override (None = use global)

    def get_all_paragraph_ids(self) -> list[int]:
        """Get all paragraph IDs in this section, including sub-items."""
        all_ids = list(self.paragraph_ids)
        for subitem in self.subitems:
            all_ids.extend(subitem.paragraph_ids)
        return sorted(all_ids)


@dataclass
class Document:
    """
    A federal court document with sections and continuously numbered paragraphs.

    Key rule: Paragraph numbers are CONTINUOUS (1, 2, 3...) throughout
    the entire document, never restarting at section boundaries.
    """
    title: str = "Untitled Document"
    sections: list[Section] = field(default_factory=list)
    paragraphs: dict[int, Paragraph] = field(default_factory=dict)  # number -> Paragraph
    caption: CaseCaption = field(default_factory=CaseCaption)
    signature: SignatureBlock = field(default_factory=SignatureBlock)

    def add_section(self, section_id: str, title: str) -> Section:
        """Add a new section to the document."""
        section = Section(id=section_id, title=title)
        self.sections.append(section)
        return section

    def add_paragraph(
        self,
        text: str,
        section_id: str,
        subitem_id: Optional[str] = None
    ) -> Paragraph:
        """
        Add a new paragraph with the next continuous number.

        Paragraph numbers are automatically assigned in sequence.
        """
        next_num = len(self.paragraphs) + 1
        para = Paragraph(
            number=next_num,
            text=text,
            section_id=section_id,
            subitem_id=subitem_id
        )
        self.paragraphs[next_num] = para

        # Add to appropriate section/subitem
        for section in self.sections:
            if section.id == section_id:
                if subitem_id:
                    for subitem in section.subitems:
                        if subitem.id == subitem_id:
                            subitem.paragraph_ids.append(next_num)
                            break
                else:
                    section.paragraph_ids.append(next_num)
                break

        return para

    def get_full_text(self) -> str:
        """Get the full document text with paragraph numbers."""
        lines = []
        for section in self.sections:
            # Section header
            lines.append(f"\n{' ' * 20}{section.id}. {section.title}\n")

            # Get all paragraphs in this section, in order
            all_para_ids = section.get_all_paragraph_ids()
            for para_id in all_para_ids:
                para = self.paragraphs.get(para_id)
                if para:
                    lines.append(f"{para.number}.  {para.text}\n")

        return "\n".join(lines)

    def renumber_paragraphs(self) -> None:
        """
        Renumber all paragraphs continuously after reordering.

        This ensures paragraph numbers stay continuous (1, 2, 3...)
        even after user rearranges the order.
        """
        # Collect all paragraphs in current order
        ordered_paras = []
        for section in self.sections:
            for para_id in section.paragraph_ids:
                if para_id in self.paragraphs:
                    ordered_paras.append(self.paragraphs[para_id])
            for subitem in section.subitems:
                for para_id in subitem.paragraph_ids:
                    if para_id in self.paragraphs:
                        ordered_paras.append(self.paragraphs[para_id])

        # Reassign numbers
        new_paragraphs = {}
        for i, para in enumerate(ordered_paras, start=1):
            old_num = para.number
            para.number = i
            new_paragraphs[i] = para

            # Update references in sections/subitems
            for section in self.sections:
                if old_num in section.paragraph_ids:
                    idx = section.paragraph_ids.index(old_num)
                    section.paragraph_ids[idx] = i
                for subitem in section.subitems:
                    if old_num in subitem.paragraph_ids:
                        idx = subitem.paragraph_ids.index(old_num)
                        subitem.paragraph_ids[idx] = i

        self.paragraphs = new_paragraphs
