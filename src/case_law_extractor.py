"""
Case law citation extractor with smart detection logic.

Identifies legal citations in text using multiple strategies:
- Full citations: Party v. Party, 123 F.3d 456 (5th Cir. 2020)
- Reporter-based: volume + reporter + page + year
- Short citations: Id., Id. at 123, supra, infra

Validation requires year (1800-2025) + at least one other legal element.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Citation:
    """A detected legal citation."""
    full_text: str  # The matched citation text
    case_name: Optional[str] = None  # Party v. Party (if detected)
    volume: Optional[str] = None
    reporter: Optional[str] = None
    page: Optional[str] = None
    year: Optional[str] = None
    court: Optional[str] = None
    citation_type: str = "full"  # full, short, or reference


@dataclass
class ParagraphCitations:
    """Citations found in a single paragraph."""
    paragraph_num: int
    paragraph_text: str
    citations: list[Citation]

    @property
    def preview(self) -> str:
        """Get truncated paragraph preview."""
        if len(self.paragraph_text) > 80:
            return self.paragraph_text[:80] + "..."
        return self.paragraph_text


class CaseLawExtractor:
    """
    Extracts legal citations from document text.

    Uses smart detection requiring year + another legal element
    to avoid false positives from dates or random numbers.
    """

    # Valid year range for citations
    MIN_YEAR = 1800
    MAX_YEAR = 2025

    # Federal reporters
    FEDERAL_REPORTERS = [
        r"F\.4th", r"F\.3d", r"F\.2d", r"F\.",  # Federal Reporter
        r"F\.\s*Supp\.\s*3d", r"F\.\s*Supp\.\s*2d", r"F\.\s*Supp\.",  # Federal Supplement
        r"F\.\s*App'x",  # Federal Appendix
        r"B\.R\.",  # Bankruptcy Reporter
    ]

    # Supreme Court reporters
    SUPREME_COURT_REPORTERS = [
        r"U\.S\.", r"S\.Ct\.", r"S\.\s*Ct\.",
        r"L\.Ed\.2d", r"L\.Ed\.",
    ]

    # State reporters (common ones, especially Mississippi)
    STATE_REPORTERS = [
        r"So\.3d", r"So\.2d", r"So\.",  # Southern Reporter (MS, LA, AL, FL)
        r"Miss\.",  # Mississippi Reports
        r"N\.E\.3d", r"N\.E\.2d", r"N\.E\.",  # North Eastern
        r"N\.W\.2d", r"N\.W\.",  # North Western
        r"P\.3d", r"P\.2d", r"P\.",  # Pacific
        r"S\.E\.2d", r"S\.E\.",  # South Eastern
        r"S\.W\.3d", r"S\.W\.2d", r"S\.W\.",  # South Western
        r"A\.3d", r"A\.2d", r"A\.",  # Atlantic
        r"Cal\.Rptr\.3d", r"Cal\.Rptr\.2d", r"Cal\.Rptr\.",  # California
        r"N\.Y\.S\.3d", r"N\.Y\.S\.2d",  # New York
    ]

    # Court abbreviations for parenthetical
    COURT_ABBREVS = [
        # Federal Circuit Courts
        r"1st\s*Cir\.", r"2d\s*Cir\.", r"2nd\s*Cir\.", r"3d\s*Cir\.", r"3rd\s*Cir\.",
        r"4th\s*Cir\.", r"5th\s*Cir\.", r"6th\s*Cir\.", r"7th\s*Cir\.",
        r"8th\s*Cir\.", r"9th\s*Cir\.", r"10th\s*Cir\.", r"11th\s*Cir\.",
        r"D\.C\.\s*Cir\.", r"Fed\.\s*Cir\.",
        # District Courts
        r"[NSEW]\.D\.\s*\w+\.", r"[NSEW]\.D\.\s*Miss\.",
        r"D\.\s*\w+\.",  # Generic district
        r"S\.D\.\s*Miss\.", r"N\.D\.\s*Miss\.",  # Mississippi districts
        # State courts
        r"Miss\.\s*Ct\.\s*App\.", r"Miss\.\s*App\.",
        # Supreme Court (no court abbrev needed, just year)
    ]

    # All reporters combined
    ALL_REPORTERS = FEDERAL_REPORTERS + SUPREME_COURT_REPORTERS + STATE_REPORTERS

    def __init__(self):
        """Initialize the extractor with compiled regex patterns."""
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for citation detection."""
        # Build reporter pattern (any reporter)
        reporter_pattern = "|".join(self.ALL_REPORTERS)

        # Pattern 1: Full citation with case name
        # Party v. Party, 123 F.3d 456 (5th Cir. 2020)
        # Also handles: Party v. Party, 123 F.3d 456, 460 (5th Cir. 2020) - pinpoint
        self.full_citation_pattern = re.compile(
            r"([A-Z][A-Za-z'\-\.]+(?:\s+[A-Za-z'\-\.]+)*)"  # First party
            r"\s+v\.?\s+"  # v. or vs
            r"([A-Z][A-Za-z'\-\.]+(?:\s+[A-Za-z'\-\.]+)*)"  # Second party
            r",?\s*"
            r"(\d{1,4})\s+"  # Volume
            r"(" + reporter_pattern + r")\s+"  # Reporter
            r"(\d+)"  # Page
            r"(?:,\s*(\d+))?"  # Optional pinpoint page
            r"(?:\s*\(([^)]+?)\s*(\d{4})\))?"  # Optional (Court Year)
            , re.IGNORECASE
        )

        # Pattern 2: In re / Ex parte citations
        # In re Smith, 123 F.3d 456 (5th Cir. 2020)
        self.in_re_pattern = re.compile(
            r"(In\s+re|Ex\s+parte)\s+"
            r"([A-Z][A-Za-z'\-\.]+(?:\s+[A-Za-z'\-\.]+)*)"  # Name
            r",?\s*"
            r"(\d{1,4})\s+"  # Volume
            r"(" + reporter_pattern + r")\s+"  # Reporter
            r"(\d+)"  # Page
            r"(?:\s*\(([^)]+?)\s*(\d{4})\))?"  # Optional (Court Year)
            , re.IGNORECASE
        )

        # Pattern 3: Reporter citation without full case name
        # 123 F.3d 456 (5th Cir. 2020)
        self.reporter_citation_pattern = re.compile(
            r"(\d{1,4})\s+"  # Volume
            r"(" + reporter_pattern + r")\s+"  # Reporter
            r"(\d+)"  # Page
            r"(?:,\s*(\d+))?"  # Optional pinpoint
            r"(?:\s*\(([^)]*?(\d{4}))\))?"  # Parenthetical with year
            , re.IGNORECASE
        )

        # Pattern 4: Short citations
        # Id., Id. at 123
        self.id_citation_pattern = re.compile(
            r"\bId\.(?:\s+at\s+(\d+(?:[-–]\d+)?))?"
            , re.IGNORECASE
        )

        # Pattern 5: Supra/Infra references
        # Smith, supra; Jones, supra at 123
        self.supra_infra_pattern = re.compile(
            r"([A-Z][A-Za-z'\-]+),?\s+(supra|infra)(?:\s+at\s+(\d+))?"
            , re.IGNORECASE
        )

        # Pattern 6: Year in parenthetical (for validation)
        self.year_pattern = re.compile(r"\((?:[^)]*?)(\d{4})\)")

        # Pattern 7: Standalone year near reporter (backup detection)
        self.year_near_reporter = re.compile(
            r"(\d{1,4})\s+(" + reporter_pattern + r")\s+(\d+)[^(]*?\(.*?(\d{4})\)"
            , re.IGNORECASE
        )

    def extract_from_text(self, text: str) -> list[Citation]:
        """
        Extract all citations from a text string.

        Args:
            text: The text to analyze.

        Returns:
            List of Citation objects found.
        """
        citations = []

        # Track what we've already found to avoid duplicates
        found_spans = set()

        # 1. Full citations (Party v. Party pattern)
        for match in self.full_citation_pattern.finditer(text):
            if self._is_valid_citation(match, text):
                citation = Citation(
                    full_text=match.group(0).strip(),
                    case_name=f"{match.group(1)} v. {match.group(2)}",
                    volume=match.group(3),
                    reporter=match.group(4),
                    page=match.group(5),
                    year=match.group(8) if match.group(8) else None,
                    court=match.group(7) if match.group(7) else None,
                    citation_type="full"
                )
                citations.append(citation)
                found_spans.add((match.start(), match.end()))

        # 2. In re / Ex parte citations
        for match in self.in_re_pattern.finditer(text):
            if (match.start(), match.end()) not in found_spans:
                if self._is_valid_citation(match, text):
                    citation = Citation(
                        full_text=match.group(0).strip(),
                        case_name=f"{match.group(1)} {match.group(2)}",
                        volume=match.group(3),
                        reporter=match.group(4),
                        page=match.group(5),
                        year=match.group(7) if match.group(7) else None,
                        court=match.group(6) if match.group(6) else None,
                        citation_type="full"
                    )
                    citations.append(citation)
                    found_spans.add((match.start(), match.end()))

        # 3. Reporter citations (without case name)
        for match in self.reporter_citation_pattern.finditer(text):
            # Check if this overlaps with already found citations
            overlaps = any(
                not (match.end() <= start or match.start() >= end)
                for start, end in found_spans
            )
            if not overlaps and self._is_valid_reporter_citation(match, text):
                year = None
                court = None
                if match.group(5):  # Parenthetical
                    year = match.group(6)
                    # Extract court from parenthetical
                    paren_text = match.group(5)
                    court = paren_text.replace(match.group(6), "").strip() if match.group(6) else None

                citation = Citation(
                    full_text=match.group(0).strip(),
                    volume=match.group(1),
                    reporter=match.group(2),
                    page=match.group(3),
                    year=year,
                    court=court,
                    citation_type="reporter"
                )
                citations.append(citation)
                found_spans.add((match.start(), match.end()))

        # 4. Id. citations
        for match in self.id_citation_pattern.finditer(text):
            citation = Citation(
                full_text=match.group(0).strip(),
                page=match.group(1) if match.group(1) else None,
                citation_type="short"
            )
            citations.append(citation)

        # 5. Supra/Infra references
        for match in self.supra_infra_pattern.finditer(text):
            citation = Citation(
                full_text=match.group(0).strip(),
                case_name=match.group(1),
                page=match.group(3) if match.group(3) else None,
                citation_type="reference"
            )
            citations.append(citation)

        return citations

    def _is_valid_citation(self, match, text: str) -> bool:
        """
        Validate that a match is a real citation.

        Requires year + at least one other legal element.
        """
        # Check for valid year in the match or nearby
        year = None
        if match.lastindex and match.lastindex >= 8 and match.group(8):
            year = match.group(8)
        elif match.lastindex and match.lastindex >= 7 and match.group(7):
            # Try to extract year from parenthetical
            year_match = re.search(r"(\d{4})", match.group(7))
            if year_match:
                year = year_match.group(1)

        if year:
            try:
                year_int = int(year)
                if not (self.MIN_YEAR <= year_int <= self.MAX_YEAR):
                    return False
            except ValueError:
                return False

        # Has reporter = valid
        if match.group(4):  # Reporter group
            return True

        # Has "v." = valid (case name pattern)
        return True

    def _is_valid_reporter_citation(self, match, text: str) -> bool:
        """
        Validate a reporter-only citation.

        Must have valid year to avoid false positives.
        """
        # Must have year in parenthetical
        if not match.group(6):  # Year group
            # Check if there's a year nearby in text
            context_start = max(0, match.start() - 10)
            context_end = min(len(text), match.end() + 50)
            context = text[context_start:context_end]
            year_match = re.search(r"\(.*?(\d{4})\)", context)
            if not year_match:
                return False
            year = year_match.group(1)
        else:
            year = match.group(6)

        try:
            year_int = int(year)
            if not (self.MIN_YEAR <= year_int <= self.MAX_YEAR):
                return False
        except ValueError:
            return False

        return True

    def extract_from_paragraphs(self, paragraphs: dict[int, str]) -> list[ParagraphCitations]:
        """
        Extract citations from numbered paragraphs.

        Args:
            paragraphs: Dict mapping paragraph number to text.

        Returns:
            List of ParagraphCitations with citations found.
        """
        results = []

        for para_num in sorted(paragraphs.keys()):
            text = paragraphs[para_num]
            citations = self.extract_from_text(text)

            if citations:
                results.append(ParagraphCitations(
                    paragraph_num=para_num,
                    paragraph_text=text,
                    citations=citations
                ))

        return results

    def generate_report(self, paragraph_citations: list[ParagraphCitations]) -> str:
        """
        Generate a text report of found citations.

        Args:
            paragraph_citations: List of ParagraphCitations from extract_from_paragraphs.

        Returns:
            Formatted report string.
        """
        if not paragraph_citations:
            return "No case law citations found in this document."

        lines = []
        total_citations = sum(len(pc.citations) for pc in paragraph_citations)

        lines.append(f"CASE LAW CITATION REPORT")
        lines.append("=" * 50)
        lines.append(f"Found {total_citations} citation(s) in {len(paragraph_citations)} paragraph(s)")
        lines.append("")

        for pc in paragraph_citations:
            lines.append(f"Paragraph {pc.paragraph_num}:")
            lines.append(f"  Preview: {pc.preview}")
            lines.append(f"  Citations ({len(pc.citations)}):")

            for i, citation in enumerate(pc.citations, 1):
                if citation.case_name:
                    lines.append(f"    {i}. {citation.case_name}")
                    lines.append(f"       {citation.full_text}")
                else:
                    lines.append(f"    {i}. {citation.full_text}")

                if citation.citation_type == "short":
                    lines.append(f"       [Short citation]")
                elif citation.citation_type == "reference":
                    lines.append(f"       [Reference]")

            lines.append("")

        return "\n".join(lines)
