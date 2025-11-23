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
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    KeepTogether,
)
from reportlab.lib import colors
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


def _build_caption(caption, font_name: str) -> list:
    """
    Build the federal court case caption header.

    Format:
    - Court name centered at top (bold)
    - Case number right-aligned after court (size 10)
    - Plaintiff name on left, "Plaintiff," label on right
    - "v." on left
    - Defendant name on left, "Defendant." label on right
    """
    styles = getSampleStyleSheet()
    elements = []

    # Usable width (page width minus margins)
    usable_width = PAGE_WIDTH - 2 * MARGIN

    # Court name style (centered, bold, caps) - no space between lines
    court_style = ParagraphStyle(
        'CourtName',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=FONT_SIZE,
        leading=LINE_SPACING,
        alignment=TA_CENTER,
        spaceAfter=0,  # No space between court name lines
    )

    # Case number style (right aligned, size 10)
    case_style = ParagraphStyle(
        'CaseNumber',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,  # Size 10pt as requested
        leading=LINE_SPACING,
        alignment=TA_RIGHT,
    )

    # Party name style (left aligned)
    party_style = ParagraphStyle(
        'PartyName',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=FONT_SIZE,
        leading=LINE_SPACING,
        alignment=TA_LEFT,
    )

    # Label style (right aligned for Plaintiff/Defendant labels)
    label_style = ParagraphStyle(
        'PartyLabel',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=FONT_SIZE,
        leading=LINE_SPACING,
        alignment=TA_RIGHT,
    )

    # Court name (two lines centered, bold)
    court_lines = caption.court.split('\n')
    for line in court_lines:
        elements.append(Paragraph(f"<b>{line}</b>", court_style))

    # Case number right after court, right-aligned
    case_num_text = f"Case No. {caption.case_number}" if caption.case_number else ""
    if case_num_text:
        elements.append(Spacer(1, LINE_SPACING / 2))
        elements.append(Paragraph(case_num_text, case_style))

    elements.append(Spacer(1, LINE_SPACING / 2))

    # Build caption table
    # Left column: party names, Right column: labels (Plaintiff, Defendant)
    col_width = usable_width / 2

    plaintiff_text = caption.plaintiff.upper() if caption.plaintiff else ""
    defendant_text = caption.defendant.upper() if caption.defendant else ""

    # Table data
    table_data = []

    # Row 1: Plaintiff name on left, "Plaintiff," label on right
    if plaintiff_text:
        table_data.append([
            Paragraph(plaintiff_text + ",", party_style),
            Paragraph("Plaintiff,", label_style)
        ])

    # Row 2: v.
    table_data.append([
        Paragraph("<b>v.</b>", party_style),
        ""
    ])

    # Row 3: Defendant name on left, "Defendant." label on right
    if defendant_text:
        table_data.append([
            Paragraph(defendant_text + ",", party_style),
            Paragraph("Defendant.", label_style)
        ])

    if table_data:
        caption_table = Table(
            table_data,
            colWidths=[col_width, col_width],
        )
        caption_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(caption_table)

    elements.append(Spacer(1, LINE_SPACING))

    return elements


def _build_signature_and_certificate(signature, font_name: str) -> list:
    """
    Build the signature block and certificate of service.

    These are kept together on the same page using KeepTogether.
    """
    styles = getSampleStyleSheet()
    elements = []

    # Signature block style
    sig_style = ParagraphStyle(
        'SignatureBlock',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=FONT_SIZE,
        leading=LINE_SPACING,
        alignment=TA_LEFT,
        spaceAfter=0,
    )

    # Certificate header style (centered, bold)
    cert_header_style = ParagraphStyle(
        'CertHeader',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=FONT_SIZE,
        leading=LINE_SPACING,
        alignment=TA_CENTER,
        spaceAfter=LINE_SPACING / 2,
    )

    # Certificate body style
    cert_body_style = ParagraphStyle(
        'CertBody',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=FONT_SIZE,
        leading=LINE_SPACING,
        alignment=TA_JUSTIFY,
        firstLineIndent=0.5 * inch,
    )

    # Add some space before signature
    elements.append(Spacer(1, LINE_SPACING * 2))

    # Respectfully submitted
    elements.append(Paragraph("Respectfully submitted,", sig_style))
    elements.append(Spacer(1, LINE_SPACING * 2))

    # Signature line
    elements.append(Paragraph(f"/s/ {signature.attorney_name}", sig_style))

    # Attorney details
    if signature.attorney_name:
        elements.append(Paragraph(f"<b>{signature.attorney_name}</b>", sig_style))
    if signature.bar_number:
        elements.append(Paragraph(signature.bar_number, sig_style))
    if signature.firm_name:
        elements.append(Paragraph(signature.firm_name, sig_style))
    if signature.address:
        elements.append(Paragraph(signature.address, sig_style))
    if signature.phone:
        elements.append(Paragraph(f"Tel: {signature.phone}", sig_style))
    if signature.email:
        elements.append(Paragraph(signature.email, sig_style))

    # Certificate of Service
    elements.append(Spacer(1, LINE_SPACING * 2))
    elements.append(Paragraph("<b>CERTIFICATE OF SERVICE</b>", cert_header_style))

    cert_text = (
        "I hereby certify that on this date, I electronically filed the foregoing "
        "with the Clerk of Court using the CM/ECF system, which will send notification "
        "of such filing to all counsel of record."
    )
    elements.append(Paragraph(cert_text, cert_body_style))

    # Signature on certificate
    elements.append(Spacer(1, LINE_SPACING * 2))
    elements.append(Paragraph(f"/s/ {signature.attorney_name}", sig_style))

    # Wrap everything in KeepTogether so they stay on same page
    return [KeepTogether(elements)]


def generate_pdf(
    paragraphs: dict,
    section_starts: dict,
    output_path: str | None = None,
    global_spacing=None,
    caption=None,
    signature=None
) -> str:
    """
    Generate a PDF document with federal court formatting.

    Args:
        paragraphs: Dict of paragraph number -> Paragraph object
        section_starts: Dict of paragraph number -> Section object (where sections start)
        output_path: Optional path to save PDF. If None, creates temp file.
        global_spacing: Global SpacingSettings object (optional)
        caption: CaseCaption object for court header (optional)
        signature: SignatureBlock object for signature and certificate of service (optional)

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

    # Default spacing values
    default_before_section = 1
    default_after_section = 1
    default_between_paragraphs = 1

    if global_spacing:
        default_before_section = global_spacing.before_section
        default_after_section = global_spacing.after_section
        default_between_paragraphs = global_spacing.between_paragraphs

    # Build content
    story = []

    # Add caption if provided and has content
    if caption and (caption.plaintiff or caption.defendant or caption.case_number):
        story.extend(_build_caption(caption, font_name))
        story.append(Spacer(1, LINE_SPACING))

    current_section = None
    is_first_para_in_section = False

    for para_num in sorted(paragraphs.keys()):
        para = paragraphs[para_num]

        # Check if this paragraph starts a new section
        if para_num in section_starts:
            section = section_starts[para_num]
            current_section = section

            # Get spacing for this section (custom or global)
            spacing = section.custom_spacing if section.custom_spacing else None
            before_section = spacing.before_section if spacing else default_before_section
            after_section = spacing.after_section if spacing else default_after_section

            section_text = f"<b>{section.id}. {section.title}</b>"
            story.append(Spacer(1, LINE_SPACING * before_section))
            story.append(Paragraph(section_text, styles['section']))
            story.append(Spacer(1, LINE_SPACING * after_section / 2))
            is_first_para_in_section = True
        else:
            # Add spacing between paragraphs (not before first para in section)
            if story and not is_first_para_in_section:
                # Get current section's spacing
                spacing = current_section.custom_spacing if current_section and current_section.custom_spacing else None
                between = spacing.between_paragraphs if spacing else default_between_paragraphs
                if between > 0:
                    story.append(Spacer(1, LINE_SPACING * between / 2))

        is_first_para_in_section = False

        # Add numbered paragraph
        # Escape any HTML-like characters in the text
        safe_text = para.text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        para_text = f"{para.number}.&nbsp;&nbsp;&nbsp;{safe_text}"
        story.append(Paragraph(para_text, styles['paragraph']))

    # Add signature block and certificate of service if provided
    if signature and signature.attorney_name:
        story.extend(_build_signature_and_certificate(signature, font_name))

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
