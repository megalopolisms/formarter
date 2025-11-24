"""
Case Library storage manager.

Handles storage, retrieval, and search of case law PDFs
with metadata, categories, and keywords.
"""

import json
import shutil
import re
from pathlib import Path
from typing import Optional

try:
    import fitz  # pymupdf
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import pytesseract
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False

from src.models.library_case import (
    LibraryCase, Category, BatchImportResult, DEFAULT_CATEGORIES
)


class CaseLibrary:
    """
    Manages the case law library storage.

    Stores PDFs and extracted text in a Dropbox-synced folder
    with a JSON index for metadata.
    """

    INDEX_FILENAME = "index.json"

    def __init__(self, storage_dir: Path):
        """
        Initialize the case library.

        Args:
            storage_dir: Path to the library storage directory.
        """
        self.storage_dir = Path(storage_dir)
        self._ensure_storage_exists()
        self._load_index()

    def _ensure_storage_exists(self):
        """Create storage directory if it doesn't exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _load_index(self):
        """Load the index from disk."""
        index_path = self.storage_dir / self.INDEX_FILENAME
        if index_path.exists():
            try:
                with open(index_path, 'r') as f:
                    data = json.load(f)
                self._categories = [
                    Category.from_dict(c) for c in data.get("categories", [])
                ]
                self._cases = [
                    LibraryCase.from_dict(c) for c in data.get("cases", [])
                ]
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading index: {e}")
                self._categories = list(DEFAULT_CATEGORIES)
                self._cases = []
        else:
            # Initialize with default categories
            self._categories = list(DEFAULT_CATEGORIES)
            self._cases = []
            self._save_index()

    def _save_index(self):
        """Save the index to disk."""
        index_path = self.storage_dir / self.INDEX_FILENAME
        data = {
            "categories": [c.to_dict() for c in self._categories],
            "cases": [c.to_dict() for c in self._cases]
        }
        with open(index_path, 'w') as f:
            json.dump(data, f, indent=2)

    # ========== Case Management ==========

    def add_case(
        self,
        pdf_path: str,
        case_name: str,
        volume: str,
        reporter: str,
        page: str,
        year: str = "",
        court: str = "",
        category_id: str = "",
        keywords: list[str] = None
    ) -> LibraryCase:
        """
        Add a case to the library.

        Args:
            pdf_path: Path to the source PDF file.
            case_name: Name of the case (e.g., "Smith v. Jones").
            volume: Volume number.
            reporter: Reporter abbreviation (e.g., "F.3d").
            page: Starting page number.
            year: Year of decision.
            court: Court abbreviation.
            category_id: Category ID for organization.
            keywords: List of keywords/tags.

        Returns:
            The created LibraryCase object.
        """
        # Create the case object
        case = LibraryCase.create(
            case_name=case_name,
            volume=volume,
            reporter=reporter,
            page=page,
            year=year,
            court=court,
            category_id=category_id,
            keywords=keywords or []
        )

        # Copy PDF to library
        src_pdf = Path(pdf_path)
        dest_pdf = self.storage_dir / case.pdf_filename
        shutil.copy2(src_pdf, dest_pdf)

        # Extract text and save
        text = self.extract_text(str(dest_pdf))
        if text:
            dest_txt = self.storage_dir / case.txt_filename
            with open(dest_txt, 'w', encoding='utf-8') as f:
                f.write(text)

            # Extract and save citations from text
            citations = self.extract_citations_from_text(text)
            if citations:
                citations_filename = case.txt_filename.replace('.txt', '_citations.txt')
                dest_citations = self.storage_dir / citations_filename
                with open(dest_citations, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(citations))

        # Add to index and save
        self._cases.append(case)
        self._save_index()

        return case

    def list_all(self) -> list[LibraryCase]:
        """Get all cases in the library."""
        return list(self._cases)

    def get_by_id(self, case_id: str) -> Optional[LibraryCase]:
        """Get a case by its ID."""
        for case in self._cases:
            if case.id == case_id:
                return case
        return None

    def update_case(self, case_id: str, updates: dict) -> Optional[LibraryCase]:
        """
        Update a case's metadata.

        Args:
            case_id: The case ID to update.
            updates: Dictionary of fields to update.

        Returns:
            The updated case, or None if not found.
        """
        for i, case in enumerate(self._cases):
            if case.id == case_id:
                # Update allowed fields
                for field in ['category_id', 'keywords', 'notes']:
                    if field in updates:
                        setattr(case, field, updates[field])
                self._cases[i] = case
                self._save_index()
                return case
        return None

    def delete(self, case_id: str) -> bool:
        """
        Delete a case from the library.

        Args:
            case_id: The case ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        for i, case in enumerate(self._cases):
            if case.id == case_id:
                # Delete files
                pdf_path = self.storage_dir / case.pdf_filename
                txt_path = self.storage_dir / case.txt_filename
                if pdf_path.exists():
                    pdf_path.unlink()
                if txt_path.exists():
                    txt_path.unlink()

                # Remove from index
                self._cases.pop(i)
                self._save_index()
                return True
        return False

    def is_duplicate(self, volume: str, reporter: str, page: str) -> bool:
        """Check if a case with the same citation exists."""
        for case in self._cases:
            if (case.volume == volume and
                case.reporter == reporter and
                case.page == page):
                return True
        return False

    # ========== Search and Filtering ==========

    def search(self, query: str) -> list[LibraryCase]:
        """
        Search cases by name, citation, or keywords.

        Args:
            query: Search query string.

        Returns:
            List of matching cases.
        """
        query_lower = query.lower()
        results = []

        for case in self._cases:
            # Search in case name
            if query_lower in case.case_name.lower():
                results.append(case)
                continue

            # Search in citation
            if query_lower in case.bluebook_citation.lower():
                results.append(case)
                continue

            # Search in keywords
            if any(query_lower in kw.lower() for kw in case.keywords):
                results.append(case)
                continue

        return results

    def filter_by_category(self, category_id: str) -> list[LibraryCase]:
        """Get all cases in a category."""
        if not category_id:
            return list(self._cases)
        return [c for c in self._cases if c.category_id == category_id]

    def filter_by_keyword(self, keyword: str) -> list[LibraryCase]:
        """Get all cases with a specific keyword."""
        keyword_lower = keyword.lower()
        return [
            c for c in self._cases
            if any(keyword_lower in kw.lower() for kw in c.keywords)
        ]

    def search_full_text(self, query: str) -> list[LibraryCase]:
        """
        Search within extracted text content.

        Args:
            query: Search query string.

        Returns:
            List of cases where text contains the query.
        """
        query_lower = query.lower()
        results = []

        for case in self._cases:
            txt_path = self.storage_dir / case.txt_filename
            if txt_path.exists():
                try:
                    with open(txt_path, 'r', encoding='utf-8') as f:
                        text = f.read().lower()
                    if query_lower in text:
                        results.append(case)
                except Exception:
                    pass

        return results

    # ========== Category Management ==========

    def add_category(self, name: str, color: str = "#4A90D9") -> Category:
        """Add a new category."""
        category = Category.create(name, color)
        self._categories.append(category)
        self._save_index()
        return category

    def list_categories(self) -> list[Category]:
        """Get all categories."""
        return list(self._categories)

    def get_category(self, category_id: str) -> Optional[Category]:
        """Get a category by ID."""
        for cat in self._categories:
            if cat.id == category_id:
                return cat
        return None

    def delete_category(self, category_id: str) -> bool:
        """Delete a category (cases keep their category_id but it becomes orphaned)."""
        for i, cat in enumerate(self._categories):
            if cat.id == category_id:
                self._categories.pop(i)
                self._save_index()
                return True
        return False

    # ========== Keywords ==========

    def get_all_keywords(self) -> list[str]:
        """Get all unique keywords across all cases (for autocomplete)."""
        keywords = set()
        for case in self._cases:
            keywords.update(case.keywords)
        return sorted(keywords)

    def add_keyword_to_case(self, case_id: str, keyword: str) -> bool:
        """Add a keyword to a case."""
        case = self.get_by_id(case_id)
        if case and keyword not in case.keywords:
            case.keywords.append(keyword)
            self._save_index()
            return True
        return False

    def remove_keyword_from_case(self, case_id: str, keyword: str) -> bool:
        """Remove a keyword from a case."""
        case = self.get_by_id(case_id)
        if case and keyword in case.keywords:
            case.keywords.remove(keyword)
            self._save_index()
            return True
        return False

    # ========== File Operations ==========

    def get_pdf_path(self, case_id: str) -> Optional[Path]:
        """Get the full path to a case's PDF."""
        case = self.get_by_id(case_id)
        if case:
            return self.storage_dir / case.pdf_filename
        return None

    def get_txt_path(self, case_id: str) -> Optional[Path]:
        """Get the full path to a case's extracted text."""
        case = self.get_by_id(case_id)
        if case:
            return self.storage_dir / case.txt_filename
        return None

    def get_case_text(self, case_id: str) -> Optional[str]:
        """Get the extracted text content for a case."""
        txt_path = self.get_txt_path(case_id)
        if txt_path and txt_path.exists():
            with open(txt_path, 'r', encoding='utf-8') as f:
                return f.read()
        return None

    @staticmethod
    def extract_text(pdf_path: str) -> str:
        """
        Extract text from a PDF file with page markers.

        Falls back to OCR if the PDF is image-based (scanned) with no text layer.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Extracted text content with page markers (e.g., "--- Page 1 ---").
        """
        if not HAS_PYMUPDF:
            return ""

        try:
            doc = fitz.open(pdf_path)
            text_parts = []
            needs_ocr = False

            for page_num, page in enumerate(doc, start=1):
                # Add page marker
                text_parts.append(f"\n--- Page {page_num:02d} ---\n")

                # Try normal text extraction first
                page_text = page.get_text()

                # If page has very little text (less than 50 chars), it might be scanned
                if len(page_text.strip()) < 50:
                    needs_ocr = True

                    # Try OCR if available
                    if HAS_OCR:
                        try:
                            # Convert page to image
                            pix = page.get_pixmap(dpi=300)  # Higher DPI for better OCR
                            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                            # Perform OCR
                            ocr_text = pytesseract.image_to_string(img)

                            if len(ocr_text.strip()) > len(page_text.strip()):
                                # OCR produced more text, use it instead
                                page_text = ocr_text
                                print(f"  OCR used for page {page_num} ({len(ocr_text)} chars extracted)")
                        except Exception as ocr_error:
                            print(f"  OCR failed for page {page_num}: {ocr_error}")
                            # Keep the original text extraction (even if minimal)

                text_parts.append(page_text)

            doc.close()

            if needs_ocr:
                print(f"Scanned PDF detected: {pdf_path}")

            return "\n".join(text_parts)
        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {e}")
            return ""

    @staticmethod
    def extract_first_page_text(pdf_path: str) -> str:
        """
        Extract text from just the first page of a PDF.

        Falls back to OCR if the page is image-based (scanned) with no text layer.
        """
        if not HAS_PYMUPDF:
            return ""

        try:
            doc = fitz.open(pdf_path)
            if len(doc) > 0:
                page = doc[0]
                text = page.get_text()

                # If page has very little text (less than 50 chars), try OCR
                if len(text.strip()) < 50 and HAS_OCR:
                    try:
                        # Convert page to image
                        pix = page.get_pixmap(dpi=300)
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                        # Perform OCR
                        ocr_text = pytesseract.image_to_string(img)

                        if len(ocr_text.strip()) > len(text.strip()):
                            text = ocr_text
                            print(f"  OCR used for first page ({len(ocr_text)} chars extracted)")
                    except Exception as ocr_error:
                        print(f"  OCR failed for first page: {ocr_error}")
            else:
                text = ""
            doc.close()
            return text
        except Exception:
            return ""

    def extract_citation_from_pdf(self, pdf_path: str) -> Optional[dict]:
        """
        Extract citation information from a Westlaw PDF.

        Westlaw PDFs have a specific header format:
        - Line 1: Page number (e.g., "639")
        - Line 2: Case name (e.g., "KEKO v. HINGLE")
        - Line 3: "Cite as 318 F.3d 639 (5th Cir. 2002)"

        Returns:
            Dictionary with case_name, volume, reporter, page, court, year
            or None if extraction fails.
        """
        text = self.extract_first_page_text(pdf_path)
        if not text:
            # Try filename as fallback
            filename = Path(pdf_path).stem
            return self._parse_westlaw_filename(filename)

        # Strategy 1: Parse Westlaw header format (most reliable for Westlaw PDFs)
        result = self._parse_westlaw_header(text)
        if result:
            return result

        # Strategy 2: Try filename as fallback
        filename = Path(pdf_path).stem
        return self._parse_westlaw_filename(filename)

    def _parse_westlaw_header(self, text: str) -> Optional[dict]:
        """
        Parse Westlaw-style PDF header.

        Expected format:
        Line 1: Page number (digits only)
        Line 2: CASE NAME v. OTHER PARTY
        Line 3: Cite as Volume Reporter Page (Court Year)
        """
        lines = text.strip().split('\n')

        # Need at least 3 lines
        if len(lines) < 3:
            return None

        case_name = None
        cite_line = None

        # Find case name (line with "v." or "v ") and cite line
        for i, line in enumerate(lines[:10]):  # Check first 10 lines
            line = line.strip()
            if not line:
                continue

            # Skip page number lines (just digits)
            if line.isdigit():
                continue

            # Look for case name line (has "v." pattern)
            if case_name is None and (' v. ' in line or ' V. ' in line):
                case_name = line.strip()
                continue

            # Look for "Cite as" line
            if 'Cite as' in line or 'cite as' in line.lower():
                cite_line = line.strip()
                break

        if not cite_line:
            return None

        # Parse the "Cite as" line
        # Format: "Cite as 318 F.3d 639 (5th Cir. 2002)"
        cite_pattern = r"Cite\s+as\s+(\d+)\s+([\w\.\s]+?)\s+(\d+)\s*\(([^)]+)\)"
        match = re.search(cite_pattern, cite_line, re.IGNORECASE)

        if match:
            volume = match.group(1)
            reporter = match.group(2).strip()
            page = match.group(3)
            paren_content = match.group(4).strip()

            # Parse parenthetical: "(5th Cir. 2002)" -> court="5th Cir.", year="2002"
            # Or for Supreme Court: "(1995)" -> court="", year="1995"
            court = ""
            year = ""

            # Check if it's just a year (Supreme Court cases)
            if re.match(r"^\d{4}$", paren_content):
                year = paren_content
            else:
                # Try to parse "Court Year" format
                paren_match = re.match(r"(.+?)\s+(\d{4})$", paren_content)
                if paren_match:
                    court = paren_match.group(1).strip()
                    year = paren_match.group(2)
                else:
                    # Maybe just a year somewhere
                    year_match = re.search(r"(\d{4})", paren_content)
                    if year_match:
                        year = year_match.group(1)

            # Infer court from reporter if not present
            if not court:
                court = self._infer_court_from_reporter(reporter)

            # Clean up case name
            if case_name:
                case_name = self._clean_case_name_westlaw(case_name)
            else:
                # Try to extract from filename or use generic name
                case_name = "Unknown Case"

            return {
                'case_name': case_name,
                'volume': volume,
                'reporter': self._normalize_reporter(reporter),
                'page': page,
                'court': court,
                'year': year
            }

        return None

    def _infer_court_from_reporter(self, reporter: str) -> str:
        """Infer court name from reporter abbreviation."""
        reporter_clean = reporter.strip().upper().replace('.', '').replace(' ', '')

        # Supreme Court reporters
        if reporter_clean in ['US', 'SCT', 'LEED', 'LEED2D']:
            return "U.S."

        # Federal Circuit Courts - can't infer which circuit from reporter alone
        # Federal District Courts - can't infer which district from reporter alone
        # These need the court from the citation

        return ""

    def _clean_case_name_westlaw(self, name: str) -> str:
        """Clean up case name by removing Westlaw boilerplate."""
        # Remove common Westlaw artifacts
        patterns_to_remove = [
            r'\s*Cite\s+as.*$',  # "Cite as..." at end
            r'^\s*KeyCite\s*',
            r'^\s*Citing References\s*',
            r'^\s*History\s*',
        ]
        for pattern in patterns_to_remove:
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)

        name = name.strip().rstrip(',').strip()
        name = re.sub(r'\s+', ' ', name)
        return name

    # ========== Batch Import ==========

    def batch_import(
        self,
        pdf_paths: list[str],
        default_category_id: str = ""
    ) -> BatchImportResult:
        """
        Import multiple PDFs at once.

        Extracts citation from PDF content. Rejects empty PDFs.

        Args:
            pdf_paths: List of paths to PDF files.
            default_category_id: Category to assign to all imported cases.

        Returns:
            BatchImportResult with success/failure details.
        """
        result = BatchImportResult()

        for pdf_path in pdf_paths:
            try:
                path = Path(pdf_path)

                # Check if PDF is empty (0 bytes)
                if path.stat().st_size == 0:
                    result.errors.append((path.name, "PDF file is empty (0 bytes)"))
                    continue

                # Try to extract text first to verify PDF has content
                text = self.extract_first_page_text(pdf_path)
                if not text or len(text.strip()) < 50:
                    result.errors.append((path.name, "PDF has no extractable text"))
                    continue

                # Try to extract citation from PDF content
                parsed = self.extract_citation_from_pdf(pdf_path)

                if parsed:
                    # Check for duplicate by citation
                    if self.is_duplicate(parsed['volume'], parsed['reporter'], parsed['page']):
                        result.duplicates.append(path.name)
                        continue

                    # Add the case with extracted info
                    case = self.add_case(
                        pdf_path=pdf_path,
                        case_name=parsed['case_name'],
                        volume=parsed['volume'],
                        reporter=parsed['reporter'],
                        page=parsed['page'],
                        year=parsed.get('year', ''),
                        court=parsed.get('court', ''),
                        category_id=default_category_id
                    )
                    result.successful.append(case)
                else:
                    # Couldn't parse citation - import with original filename
                    case = self.add_case_from_filename(pdf_path, default_category_id)
                    result.successful.append(case)

            except Exception as e:
                result.errors.append((Path(pdf_path).name, str(e)))

        return result

    def add_case_from_filename(
        self,
        pdf_path: str,
        category_id: str = ""
    ) -> LibraryCase:
        """
        Add a case using just the filename when citation extraction fails.

        The PDF is still copied and text extracted. User can edit citation info later.
        """
        src_pdf = Path(pdf_path)
        filename_stem = src_pdf.stem  # Filename without extension

        # Create case with filename as name, no citation info
        case = LibraryCase.create(
            case_name=filename_stem,
            volume="",
            reporter="",
            page="",
            year="",
            court="",
            category_id=category_id,
            keywords=[]
        )

        # Override the generated filenames to use original name
        case.pdf_filename = src_pdf.name
        case.txt_filename = filename_stem + ".txt"
        case.bluebook_citation = filename_stem  # Use filename as placeholder

        # Copy PDF to library (keep original name)
        dest_pdf = self.storage_dir / case.pdf_filename
        if dest_pdf.exists():
            # Handle duplicate filename by adding a suffix
            counter = 1
            while dest_pdf.exists():
                case.pdf_filename = f"{filename_stem}_{counter}.pdf"
                case.txt_filename = f"{filename_stem}_{counter}.txt"
                dest_pdf = self.storage_dir / case.pdf_filename
                counter += 1

        shutil.copy2(src_pdf, dest_pdf)

        # Extract text and save
        text = self.extract_text(str(dest_pdf))
        if text:
            dest_txt = self.storage_dir / case.txt_filename
            with open(dest_txt, 'w', encoding='utf-8') as f:
                f.write(text)

            # Extract and save citations from text
            citations = self.extract_citations_from_text(text)
            if citations:
                citations_filename = case.txt_filename.replace('.txt', '_citations.txt')
                dest_citations = self.storage_dir / citations_filename
                with open(dest_citations, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(citations))

        # Add to index and save
        self._cases.append(case)
        self._save_index()

        return case

    def _parse_westlaw_filename(self, filename: str) -> Optional[dict]:
        """
        Try to parse citation info from a Westlaw-style filename.

        Westlaw filenames often look like:
        - "Smith v. Jones, 123 F.3d 456"
        - "Brown v Board of Education 347 US 483"
        - "123 F.3d 456 Smith v Jones"

        Returns:
            Dictionary with case_name, volume, reporter, page, or None if can't parse.
        """
        # Build reporter pattern for filename (less strict about periods)
        reporter_pattern = (
            r"F\.?\s*(?:4th|3d|2d)|"
            r"F\.?\s*Supp\.?\s*(?:3d|2d)?|"
            r"F\.?\s*App['\']?x|"
            r"U\.?S\.?|"
            r"S\.?\s*Ct\.?|"
            r"So\.?\s*(?:3d|2d)|"
            r"N\.?E\.?\s*(?:3d|2d)|"
            r"N\.?W\.?\s*2d|"
            r"P\.?\s*(?:3d|2d)|"
            r"S\.?E\.?\s*2d|"
            r"S\.?W\.?\s*(?:3d|2d)|"
            r"A\.?\s*(?:3d|2d)|"
            r"B\.?R\.?|"
            r"WL"
        )

        # Pattern 1: Case Name, Volume Reporter Page (most common)
        pattern1 = rf"^(.+?)[,\s]+(\d{{1,4}})\s+({reporter_pattern})\s+(\d+)"
        match = re.match(pattern1, filename, re.IGNORECASE)
        if match and self._has_case_name(match.group(1)):
            return {
                'case_name': self._clean_case_name(match.group(1)),
                'volume': match.group(2),
                'reporter': self._normalize_reporter(match.group(3)),
                'page': match.group(4)
            }

        # Pattern 2: Volume Reporter Page Case Name (alternate format)
        pattern2 = rf"^(\d{{1,4}})\s+({reporter_pattern})\s+(\d+)\s+(.+)"
        match = re.match(pattern2, filename, re.IGNORECASE)
        if match and self._has_case_name(match.group(4)):
            return {
                'case_name': self._clean_case_name(match.group(4)),
                'volume': match.group(1),
                'reporter': self._normalize_reporter(match.group(2)),
                'page': match.group(3)
            }

        # Pattern 3: Try to find Volume Reporter Page anywhere, case name before it
        pattern3 = rf"(.+?)\s+(\d{{1,4}})\s+({reporter_pattern})\s+(\d+)"
        match = re.search(pattern3, filename, re.IGNORECASE)
        if match and self._has_case_name(match.group(1)):
            return {
                'case_name': self._clean_case_name(match.group(1)),
                'volume': match.group(2),
                'reporter': self._normalize_reporter(match.group(3)),
                'page': match.group(4)
            }

        return None

    def _has_case_name(self, text: str) -> bool:
        """Check if text contains a case name (has 'v' or 'v.')."""
        text_lower = text.lower()
        return ' v ' in text_lower or ' v. ' in text_lower or text_lower.endswith(' v')

    def _clean_case_name(self, name: str) -> str:
        """Clean up case name formatting."""
        name = name.strip().rstrip(',').strip()
        # Normalize whitespace
        name = re.sub(r'\s+', ' ', name)
        # Ensure v. is properly formatted
        name = re.sub(r'\s+v\s+', ' v. ', name, flags=re.IGNORECASE)
        return name

    def extract_citations_from_text(self, text: str) -> list[str]:
        """
        Extract all case citations from text with case names.

        Finds patterns like: "Case Name v. Other Party, Volume Reporter Page (Court Year)"
        Returns unique citations in order of appearance.

        Args:
            text: The full text to search for citations.

        Returns:
            List of unique citation strings with case names.
        """
        # Build comprehensive reporter pattern
        reporter_pattern = (
            # Federal reporters
            r"F\.?\s*(?:4th|3d|2d)|"
            r"F\.\s+Supp\.?\s*(?:3d|2d)?|"
            r"F\.\s+App'?x|"
            r"B\.?R\.?|"
            # Supreme Court reporters
            r"U\.?S\.?|"
            r"S\.\s*Ct\.?|"
            r"L\.\s*Ed\.?\s*(?:2d)?|"
            # Southern reporter (MS, LA, AL, FL)
            r"So\.?\s*(?:3d|2d)|"
            r"Miss\.?|"
            # Regional reporters
            r"N\.?E\.?\s*(?:3d|2d)|"
            r"N\.?W\.?\s*(?:2d)|"
            r"P\.?\s*(?:3d|2d)|"
            r"S\.?E\.?\s*(?:2d)|"
            r"S\.?W\.?\s*(?:3d|2d)|"
            r"A\.?\s*(?:3d|2d)|"
            # California
            r"Cal\.\s*Rptr\.?\s*(?:3d|2d)?|"
            # New York
            r"N\.?Y\.?S\.?\s*(?:3d|2d)"
        )

        # Pattern 1: Case Name v. Party, Volume Reporter Page (Paren)
        # Example: United States v. Smith, 123 F.3d 456 (5th Cir. 2000)
        full_citation_pattern = rf"([A-Z][A-Za-z\.\s&]+?\s+v\.?\s+[A-Za-z][A-Za-z\.\s&,']+?),\s*(\d{{1,4}})\s+({reporter_pattern})\s+(\d{{1,5}})\s*(\([^)]+\))?"

        # Pattern 2: Case Name v. Party without comma before citation
        # Example: Webb v. C.I.R. 394 F.2d 366 (5th Cir. 1968)
        alt_citation_pattern = rf"([A-Z][A-Za-z\.\s&]+?\s+v\.?\s+[A-Za-z][A-Za-z\.\s&,']+?)\s+(\d{{1,4}})\s+({reporter_pattern})\s+(\d{{1,5}})\s*(\([^)]+\))?"

        # Pattern 3: Just the citation without case name (fallback)
        bare_citation_pattern = rf"(\d{{1,4}})\s+({reporter_pattern})\s+(\d{{1,5}})\s*(\([^)]+\))?"

        # Store unique citations (preserve order)
        seen = set()
        citations = []

        # Try full citations first (with case names)
        for match in re.finditer(full_citation_pattern, text, re.IGNORECASE):
            case_name = match.group(1).strip()
            volume = match.group(2)
            reporter = match.group(3)
            page = match.group(4)
            paren = match.group(5) if match.group(5) else ""

            # Normalize the reporter
            reporter_normalized = self._normalize_reporter(reporter)

            # Clean case name
            case_name = self._clean_case_name(case_name)

            # Create full citation string
            citation = f"{case_name}, {volume} {reporter_normalized} {page}"
            if paren:
                citation += f" {paren}"

            # Add if not seen before (use just vol/reporter/page as key)
            cite_key = f"{volume} {reporter_normalized} {page}"
            if cite_key not in seen:
                seen.add(cite_key)
                citations.append(citation)

        # Try alternative pattern (without comma)
        for match in re.finditer(alt_citation_pattern, text, re.IGNORECASE):
            case_name = match.group(1).strip()
            volume = match.group(2)
            reporter = match.group(3)
            page = match.group(4)
            paren = match.group(5) if match.group(5) else ""

            cite_key = f"{volume} {self._normalize_reporter(reporter)} {page}"
            if cite_key in seen:
                continue  # Already found with first pattern

            # Normalize the reporter
            reporter_normalized = self._normalize_reporter(reporter)

            # Clean case name
            case_name = self._clean_case_name(case_name)

            # Create full citation string
            citation = f"{case_name}, {volume} {reporter_normalized} {page}"
            if paren:
                citation += f" {paren}"

            seen.add(cite_key)
            citations.append(citation)

        # Fallback: bare citations without case names
        for match in re.finditer(bare_citation_pattern, text, re.IGNORECASE):
            volume = match.group(1)
            reporter = match.group(2)
            page = match.group(3)
            paren = match.group(4) if match.group(4) else ""

            cite_key = f"{volume} {self._normalize_reporter(reporter)} {page}"
            if cite_key in seen:
                continue  # Already found with case name

            # Normalize the reporter
            reporter_normalized = self._normalize_reporter(reporter)

            # Create citation string
            citation = f"{volume} {reporter_normalized} {page}"
            if paren:
                citation += f" {paren}"

            seen.add(cite_key)
            citations.append(citation)

        return citations

    def get_citations_path(self, case_id: str) -> Optional[Path]:
        """Get the full path to a case's extracted citations file."""
        case = self.get_by_id(case_id)
        if case:
            citations_filename = case.txt_filename.replace('.txt', '_citations.txt')
            return self.storage_dir / citations_filename
        return None

    def get_case_citations(self, case_id: str) -> Optional[list[str]]:
        """Get the extracted citations for a case."""
        citations_path = self.get_citations_path(case_id)
        if citations_path and citations_path.exists():
            with open(citations_path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        return None

    def regenerate_citations_for_case(self, case_id: str) -> bool:
        """
        Regenerate citations for a specific case from its text file.

        Args:
            case_id: The case ID to regenerate citations for.

        Returns:
            True if successful, False if case not found or no text file.
        """
        case = self.get_by_id(case_id)
        if not case:
            return False

        # Get text file path
        txt_path = self.storage_dir / case.txt_filename
        if not txt_path.exists():
            return False

        # Read the text
        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"Error reading text file for {case.case_name}: {e}")
            return False

        # Extract citations
        citations = self.extract_citations_from_text(text)

        # Save citations file
        if citations:
            citations_filename = case.txt_filename.replace('.txt', '_citations.txt')
            citations_path = self.storage_dir / citations_filename
            try:
                with open(citations_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(citations))
                return True
            except Exception as e:
                print(f"Error saving citations for {case.case_name}: {e}")
                return False

        return False

    def regenerate_all_citations(self) -> tuple[int, int]:
        """
        Regenerate citations for all cases in the library.

        Returns:
            Tuple of (successful_count, failed_count)
        """
        successful = 0
        failed = 0

        for case in self._cases:
            if self.regenerate_citations_for_case(case.id):
                successful += 1
            else:
                failed += 1

        return (successful, failed)

    def parse_citation_components(self, citation: str) -> Optional[dict]:
        """
        Parse a citation string to extract volume, reporter, and page.

        Args:
            citation: Citation string like "318 F.3d 639" or "115 S.Ct. 2151"

        Returns:
            Dict with 'volume', 'reporter', 'page' keys, or None if parsing fails.
        """
        # Pattern to match: volume reporter page
        # Examples: "318 F.3d 639", "115 S.Ct. 2151", "123 F. Supp. 2d 456"
        pattern = r'^(\d+)\s+([A-Za-z.\s\']+?)\s+(\d+)'
        match = re.match(pattern, citation.strip())

        if match:
            volume = match.group(1)
            reporter = match.group(2).strip()
            page = match.group(3)

            # Normalize the reporter
            reporter_normalized = self._normalize_reporter(reporter)

            return {
                'volume': volume,
                'reporter': reporter_normalized,
                'page': page
            }

        return None

    def find_citation_in_library(self, citation: str) -> Optional[LibraryCase]:
        """
        Check if a citation exists in the library by matching volume/reporter/page.

        Args:
            citation: Citation string to search for.

        Returns:
            The LibraryCase if found, None otherwise.
        """
        components = self.parse_citation_components(citation)
        if not components:
            return None

        volume = components['volume']
        reporter = components['reporter']
        page = components['page']

        # Search through library cases for a match
        for case in self._cases:
            # Normalize the case's reporter for comparison
            case_reporter_normalized = self._normalize_reporter(case.reporter)

            if (case.volume == volume and
                case_reporter_normalized == reporter and
                case.page == page):
                return case

        return None

    def find_citation_context(self, case_id: str, citation: str, context_chars: int = 300) -> Optional[str]:
        """
        Find the context (surrounding text) where a citation appears in a case.

        Args:
            case_id: The ID of the case containing the citation.
            citation: The citation string to find context for.
            context_chars: Number of characters to include before and after.

        Returns:
            String containing the citation with surrounding context, or None if not found.
        """
        case = self.get_by_id(case_id)
        if not case:
            return None

        # Read the case text file
        txt_path = self.storage_dir / case.txt_filename
        if not txt_path.exists():
            return None

        try:
            with open(txt_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"Error reading text file: {e}")
            return None

        # Parse the citation to get its components
        components = self.parse_citation_components(citation)
        if not components:
            # If we can't parse it, try to find the exact string
            idx = text.find(citation)
            if idx >= 0:
                start = max(0, idx - context_chars)
                end = min(len(text), idx + len(citation) + context_chars)
                context = text[start:end]
                # Clean up and add ellipsis if truncated
                if start > 0:
                    context = "..." + context
                if end < len(text):
                    context = context + "..."
                return context.strip()
            return None

        # Build search pattern for the citation
        volume = components['volume']
        reporter = components['reporter']
        page = components['page']

        # Create a flexible pattern that matches different reporter formats
        # Escape special regex characters and replace dots/spaces flexibly
        reporter_pattern = re.escape(reporter)
        reporter_pattern = reporter_pattern.replace(r'\.', r'\.?\s*')
        reporter_pattern = reporter_pattern.replace(r'\ ', r'\s+')

        # Pattern to find citation in text: volume reporter page
        pattern = rf'\b{volume}\s+{reporter_pattern}\s*{page}\b'

        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            idx = match.start()
            start = max(0, idx - context_chars)
            end = min(len(text), match.end() + context_chars)
            context = text[start:end]

            # Clean up and add ellipsis if truncated
            if start > 0:
                context = "..." + context
            if end < len(text):
                context = context + "..."

            return context.strip()

        return None

    def _normalize_reporter(self, reporter: str) -> str:
        """Normalize reporter abbreviation to standard format."""
        reporter = reporter.strip()
        # Common normalizations
        normalizations = {
            r"F\s*4th": "F.4th",
            r"F\s*3d": "F.3d",
            r"F\s*2d": "F.2d",
            r"F\s*Supp\s*3d": "F. Supp. 3d",
            r"F\s*Supp\s*2d": "F. Supp. 2d",
            r"F\s*Supp": "F. Supp.",
            r"US": "U.S.",
            r"U\s*S": "U.S.",
            r"S\s*Ct": "S. Ct.",
            r"So\s*3d": "So. 3d",
            r"So\s*2d": "So. 2d",
        }
        for pattern, replacement in normalizations.items():
            if re.match(pattern, reporter, re.IGNORECASE):
                return replacement
        return reporter


# Default storage location
def get_default_library_path() -> Path:
    """Get the default case library storage path."""
    return Path.home() / "Dropbox" / "Formarter Folder" / "case_library"
