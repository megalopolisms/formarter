"""
PDF export module for federal court documents.

Formatting per Mississippi District Court requirements:
- Times New Roman, 12pt
- Double-spaced
- 1 inch margins all sides
- Centered section headers (bold, Roman numerals)
- Numbered paragraphs with proper indentation
- Page numbers center-bottom
"""

import io
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

if TYPE_CHECKING:
    from .models import Document, Section


# Federal court formatting constants
PAGE_WIDTH, PAGE_HEIGHT = letter  # 8.5 x 11 inches
MARGIN = 1 * inch
FONT_SIZE = 12
LINE_SPACING = 24  # Double-spaced (12pt * 2)


def _register_fonts():
    """Register Times New Roman font if available."""
    # Try to register Times New Roman from system fonts
    try:
        # macOS font paths
        font_paths = [
            "/Library/Fonts/Times New Roman.ttf",
            "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
            "/System/Library/Fonts/Times.ttc",
        ]
        for path in font_paths:
            if Path(path).exists():
                if path.endswith('.ttc'):
                    # TTC files need special handling
                    pdfmetrics.registerFont(TTFont('TimesNewRoman', path, subfontIndex=0))
                else:
                    pdfmetrics.registerFont(TTFont('TimesNewRoman', path))
                return 'TimesNewRoman'
    except Exception:
        pass

    # Fall back to built-in Times
    return 'Times-Roman'


def _get_styles(font_name: str) -> dict:
    """Create paragraph styles for federal court document."""
    styles = getSampleStyleSheet()

    # Section header style (centered, bold, Roman numerals)
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Normal'],
        fontName=f'{font_name}' if font_name == 'Times-Roman' else font_name,
        fontSize=FONT_SIZE,
        leading=LINE_SPACING,
        alignment=TA_CENTER,
        spaceAfter=LINE_SPACING,
        spaceBefore=LINE_SPACING,
    )

    # Paragraph style (numbered, justified, double-spaced)
    para_style = ParagraphStyle(
        'NumberedParagraph',
        parent=styles['Normal'],
        fontName=font_name if font_name == 'Times-Roman' else font_name,
        fontSize=FONT_SIZE,
        leading=LINE_SPACING,
        alignment=TA_JUSTIFY,
        firstLineIndent=0.5 * inch,
        spaceAfter=LINE_SPACING / 2,
        leftIndent=0,
    )

    # Page number style
    page_num_style = ParagraphStyle(
        'PageNumber',
        parent=styles['Normal'],
        fontName=font_name if font_name == 'Times-Roman' else font_name,
        fontSize=FONT_SIZE,
        alignment=TA_CENTER,
    )

    return {
        'section': section_style,
        'paragraph': para_style,
        'page_number': page_num_style,
    }


def _add_page_number(canvas, doc):
    """Add page number to center bottom of each page."""
    canvas.saveState()
    page_num = canvas.getPageNumber()
    text = f"{page_num}"
    canvas.setFont('Times-Roman', 12)
    canvas.drawCentredString(PAGE_WIDTH / 2, 0.5 * inch, text)
    canvas.restoreState()


def generate_pdf(
    paragraphs: dict,
    section_starts: dict,
    output_path: str | None = None
) -> str:
    """
    Generate a PDF document with federal court formatting.

    Args:
        paragraphs: Dict of paragraph number -> Paragraph object
        section_starts: Dict of paragraph number -> Section object (where sections start)
        output_path: Optional path to save PDF. If None, creates temp file.

    Returns:
        Path to the generated PDF file.
    """
    # Register fonts
    font_name = _register_fonts()
    styles = _get_styles(font_name)

    # Create output file
    if output_path is None:
        temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        output_path = temp_file.name
        temp_file.close()

    # Create document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    # Build content
    story = []

    for para_num in sorted(paragraphs.keys()):
        para = paragraphs[para_num]

        # Check if this paragraph starts a new section
        if para_num in section_starts:
            section = section_starts[para_num]
            section_text = f"<b>{section.id}. {section.title}</b>"
            story.append(Spacer(1, LINE_SPACING))
            story.append(Paragraph(section_text, styles['section']))
            story.append(Spacer(1, LINE_SPACING / 2))

        # Add numbered paragraph
        # Escape any HTML-like characters in the text
        safe_text = para.text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        para_text = f"{para.number}.&nbsp;&nbsp;&nbsp;{safe_text}"
        story.append(Paragraph(para_text, styles['paragraph']))

    # Build PDF with page numbers
    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)

    return output_path


def generate_pdf_bytes(paragraphs: dict, section_starts: dict) -> bytes:
    """
    Generate PDF and return as bytes (for in-app preview).

    Args:
        paragraphs: Dict of paragraph number -> Paragraph object
        section_starts: Dict of paragraph number -> Section object

    Returns:
        PDF content as bytes.
    """
    # Generate to temp file
    pdf_path = generate_pdf(paragraphs, section_starts)

    # Read bytes
    with open(pdf_path, 'rb') as f:
        pdf_bytes = f.read()

    # Clean up temp file
    Path(pdf_path).unlink(missing_ok=True)

    return pdf_bytes
