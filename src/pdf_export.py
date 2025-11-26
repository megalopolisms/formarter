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
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING


def _format_date_ordinal(date_str: str) -> str:
    """
    Convert MM/DD/YYYY to 'Xth day of Month, Year' format.
    E.g., '11/23/2025' -> '23rd day of November, 2025'
    """
    try:
        dt = datetime.strptime(date_str, "%m/%d/%Y")
        day = dt.day
        # Ordinal suffix
        if 11 <= day <= 13:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        month = dt.strftime("%B")  # Full month name
        year = dt.year
        return f"{day}{suffix} day of {month}, {year}"
    except (ValueError, TypeError):
        # If parsing fails, return original
        return date_str

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
    """Register Times New Roman font family (regular, bold, italic, bold-italic)."""
    from reportlab.pdfbase.pdfmetrics import registerFontFamily

    # Try to register Times New Roman from system fonts
    try:
        # macOS font paths for Times New Roman family
        font_dir = "/Library/Fonts/"
        alt_font_dir = "/System/Library/Fonts/Supplemental/"

        # Check which directory has the fonts
        if Path(font_dir + "Times New Roman.ttf").exists():
            base_dir = font_dir
        elif Path(alt_font_dir + "Times New Roman.ttf").exists():
            base_dir = alt_font_dir
        else:
            # Fall back to built-in Times
            return 'Times-Roman'

        # Register all variants
        pdfmetrics.registerFont(TTFont('TimesNewRoman', base_dir + "Times New Roman.ttf"))
        pdfmetrics.registerFont(TTFont('TimesNewRoman-Bold', base_dir + "Times New Roman Bold.ttf"))
        pdfmetrics.registerFont(TTFont('TimesNewRoman-Italic', base_dir + "Times New Roman Italic.ttf"))
        pdfmetrics.registerFont(TTFont('TimesNewRoman-BoldItalic', base_dir + "Times New Roman Bold Italic.ttf"))

        # Register the font family so <b> and <i> tags work
        registerFontFamily(
            'TimesNewRoman',
            normal='TimesNewRoman',
            bold='TimesNewRoman-Bold',
            italic='TimesNewRoman-Italic',
            boldItalic='TimesNewRoman-BoldItalic'
        )
        return 'TimesNewRoman'
    except Exception:
        pass

    # Fall back to built-in Times (which already has bold support)
    return 'Times-Roman'


def _get_styles(font_name: str) -> dict:
    """Create paragraph styles for federal court document."""
    styles = getSampleStyleSheet()

    # Section header style (centered, bold, Roman numerals)
    # Note: spaceBefore/spaceAfter handled manually via Spacer for more control
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Normal'],
        fontName=f'{font_name}' if font_name == 'Times-Roman' else font_name,
        fontSize=FONT_SIZE,
        leading=LINE_SPACING,
        alignment=TA_CENTER,
        spaceAfter=0,  # Handled manually
        spaceBefore=0,  # Handled manually
    )

    # Paragraph style (numbered, justified, double-spaced)
    # Number at left margin with hanging indent for wrapped text
    para_style = ParagraphStyle(
        'NumberedParagraph',
        parent=styles['Normal'],
        fontName=font_name if font_name == 'Times-Roman' else font_name,
        fontSize=FONT_SIZE,
        leading=LINE_SPACING,
        alignment=TA_JUSTIFY,
        firstLineIndent=-0.5 * inch,  # Negative = hanging indent (number outdented)
        spaceAfter=LINE_SPACING / 2,
        leftIndent=0.5 * inch,  # All lines start here, first line hangs back
    )

    # Subsection header style (left aligned, italic, uppercase letters)
    subsection_style = ParagraphStyle(
        'SubsectionHeader',
        parent=styles['Normal'],
        fontName=font_name if font_name == 'Times-Roman' else font_name,
        fontSize=FONT_SIZE,
        leading=LINE_SPACING,
        alignment=TA_LEFT,
        leftIndent=0,  # Start from left margin (no indent)
        spaceAfter=0,  # Handled manually
        spaceBefore=0,  # Handled manually
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
        'subsection': subsection_style,
        'paragraph': para_style,
        'page_number': page_num_style,
    }


def _add_page_number(canvas, doc):
    """Add page number to center bottom of each page (skip first page per federal court rules)."""
    page_num = canvas.getPageNumber()
    # Federal court rule: first page is not numbered, second page shows "2", etc.
    if page_num == 1:
        return  # No page number on first page
    canvas.saveState()
    text = f"{page_num}"
    canvas.setFont('Times-Roman', 12)
    canvas.drawCentredString(PAGE_WIDTH / 2, 0.5 * inch, text)
    canvas.restoreState()


def _build_caption(caption, font_name: str, document_title: str = "") -> list:
    """
    Build the federal court case caption header.

    Format:
    - Court name centered at top (bold)
    - Case number right-aligned after court (size 10)
    - Plaintiff name on left, "Plaintiff," label on right
    - "v." on left
    - Defendant name on left, "Defendant." label on right
    - Document title centered and bold after caption
    """
    styles = getSampleStyleSheet()
    elements = []

    # Usable width (page width minus margins)
    usable_width = PAGE_WIDTH - 2 * MARGIN

    # Single spacing for header (14pt leading for 12pt font)
    SINGLE_SPACING = 14

    # Court name style (centered, bold, caps) - single spaced
    court_style = ParagraphStyle(
        'CourtName',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=FONT_SIZE,
        leading=SINGLE_SPACING,
        alignment=TA_CENTER,
        spaceAfter=0,  # No space between court name lines
    )

    # Case number style (right aligned, size 10) - single spaced
    case_style = ParagraphStyle(
        'CaseNumber',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=10,  # Size 10pt as requested
        leading=SINGLE_SPACING,
        alignment=TA_RIGHT,
    )

    # Party name style (left aligned) - single spaced
    party_style = ParagraphStyle(
        'PartyName',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=FONT_SIZE,
        leading=SINGLE_SPACING,
        alignment=TA_LEFT,
    )

    # Label style (right aligned for Plaintiff/Defendant labels) - single spaced
    label_style = ParagraphStyle(
        'PartyLabel',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=FONT_SIZE,
        leading=SINGLE_SPACING,
        alignment=TA_RIGHT,
    )

    # Court name (two lines centered, bold)
    court_lines = caption.court.split('\n')
    for line in court_lines:
        elements.append(Paragraph(f"<b>{line}</b>", court_style))

    # Case number right after court, right-aligned
    case_num_text = f"Case No. {caption.case_number}" if caption.case_number else ""
    if case_num_text:
        elements.append(Spacer(1, SINGLE_SPACING / 2))
        elements.append(Paragraph(case_num_text, case_style))

    elements.append(Spacer(1, SINGLE_SPACING / 2))

    # Build caption table
    # Left column: party names, Right column: labels (Plaintiff, Defendant)
    col_width = usable_width / 2

    plaintiff_text = caption.plaintiff.upper() if caption.plaintiff else ""
    defendant_text = caption.defendant.upper() if caption.defendant else ""

    # Table data
    table_data = []

    # Determine if plural (multiple plaintiffs/defendants)
    # Check for comma or "et al." to detect multiple parties
    is_plural_plaintiff = "," in plaintiff_text or "ET AL" in plaintiff_text
    is_plural_defendant = "," in defendant_text or "ET AL" in defendant_text

    plaintiff_label = "PLAINTIFFS" if is_plural_plaintiff else "PLAINTIFF"
    defendant_label = "DEFENDANTS" if is_plural_defendant else "DEFENDANT"

    # Clean up "et al." formatting - remove comma before it, keep all caps
    # ", ET AL" -> " ET AL." (all caps, no comma)
    plaintiff_text = re.sub(r",?\s*ET\s*AL\.?", " ET AL.", plaintiff_text, flags=re.IGNORECASE)
    defendant_text = re.sub(r",?\s*ET\s*AL\.?", " ET AL.", defendant_text, flags=re.IGNORECASE)

    # Row 1: Plaintiff name on left, "Plaintiff(s)" label on right (no trailing punctuation)
    if plaintiff_text:
        table_data.append([
            Paragraph(plaintiff_text, party_style),
            Paragraph(plaintiff_label, label_style)
        ])

    # Row 2: v.
    table_data.append([
        Paragraph("<b>v.</b>", party_style),
        ""
    ])

    # Row 3: Defendant name on left, "Defendant(s)" label on right (no trailing punctuation)
    if defendant_text:
        table_data.append([
            Paragraph(defendant_text, party_style),
            Paragraph(defendant_label, label_style)
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

    # Add document title if provided (bold, centered)
    # Single line space before title, spacing after handled by first section
    if document_title:
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Normal'],
            fontName=font_name,
            fontSize=FONT_SIZE,
            leading=LINE_SPACING,
            alignment=TA_CENTER,
            spaceBefore=LINE_SPACING / 2,  # Single line before title
            spaceAfter=0,   # No extra space - let section handle it
        )
        elements.append(Paragraph(f"<b>{document_title}</b>", title_style))

    return elements


def _build_signature_and_certificate(signature, font_name: str) -> list:
    """
    Build the signature block and certificate of service.

    Supports dual signatures side by side (left and right).
    These are kept together on the same page using KeepTogether.
    """
    styles = getSampleStyleSheet()
    elements = []

    # Usable width for signature table
    usable_width = PAGE_WIDTH - 2 * MARGIN

    # Single spacing for signature block (14pt leading for 12pt font)
    SIG_SINGLE_SPACING = 14

    # Signature block style (left aligned, single spaced)
    sig_style_left = ParagraphStyle(
        'SignatureBlockLeft',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=FONT_SIZE,
        leading=SIG_SINGLE_SPACING,
        alignment=TA_LEFT,
        spaceAfter=0,
    )

    # Signature block style (right aligned, single spaced)
    sig_style_right = ParagraphStyle(
        'SignatureBlockRight',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=FONT_SIZE,
        leading=SIG_SINGLE_SPACING,
        alignment=TA_RIGHT,
        spaceAfter=0,
    )

    # Signature block style (centered - for address)
    sig_style_center = ParagraphStyle(
        'SignatureBlockCenter',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=FONT_SIZE,
        leading=SIG_SINGLE_SPACING,
        alignment=TA_CENTER,
        spaceAfter=0,
    )

    # Certificate header style (centered, bold, single spaced)
    cert_header_style = ParagraphStyle(
        'CertHeader',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=FONT_SIZE,
        leading=SIG_SINGLE_SPACING,
        alignment=TA_CENTER,
        spaceAfter=SIG_SINGLE_SPACING / 2,
    )

    # Certificate body style (single spaced)
    cert_body_style = ParagraphStyle(
        'CertBody',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=FONT_SIZE,
        leading=SIG_SINGLE_SPACING,
        alignment=TA_JUSTIFY,
        firstLineIndent=0.5 * inch,
    )

    # Add some space before signature
    elements.append(Spacer(1, LINE_SPACING * 2))

    # Respectfully submitted with formatted date
    filing_date = getattr(signature, 'filing_date', '') or ''
    if filing_date == "__BLANK__":
        # Special format for hand-filled date
        from datetime import datetime
        year = datetime.now().year
        elements.append(Paragraph(f"Respectfully submitted at this ___ day of ____________, {year}.", sig_style_left))
    elif filing_date:
        formatted_date = _format_date_ordinal(filing_date)
        elements.append(Paragraph(f"Respectfully submitted at this {formatted_date}.", sig_style_left))
    else:
        elements.append(Paragraph("Respectfully submitted,", sig_style_left))
    elements.append(Spacer(1, SIG_SINGLE_SPACING * 3))  # Space for hand signature

    # Check if we have dual signatures
    has_dual_sig = signature.attorney_name and getattr(signature, 'attorney_name_2', '')

    if has_dual_sig:
        # Dual signatures side by side using table (no /s/ - space for hand signature)
        # Each signer's info is centered within their column
        col_width = usable_width / 2
        sig_table_data = [
            # Signature line placeholders (blank for hand signature) - centered
            [
                Paragraph("_________________________", sig_style_center),
                Paragraph("_________________________", sig_style_center)
            ],
            # Names with "Pro Se" designation (bold) - centered
            [
                Paragraph(f"<b>{signature.attorney_name}, Pro Se</b>", sig_style_center),
                Paragraph(f"<b>{signature.attorney_name_2}, Pro Se</b>", sig_style_center)
            ],
        ]
        # Add phone for each - centered
        phone_2 = getattr(signature, 'phone_2', '')
        if signature.phone or phone_2:
            sig_table_data.append([
                Paragraph(f"Tel: {signature.phone}", sig_style_center) if signature.phone else "",
                Paragraph(f"Tel: {phone_2}", sig_style_center) if phone_2 else ""
            ])
        # Add email for each - centered
        email_2 = getattr(signature, 'email_2', '')
        if signature.email or email_2:
            sig_table_data.append([
                Paragraph(signature.email, sig_style_center) if signature.email else "",
                Paragraph(email_2, sig_style_center) if email_2 else ""
            ])

        sig_table = Table(sig_table_data, colWidths=[col_width, col_width])
        sig_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(sig_table)

        # Shared address below the table (centered)
        if signature.address:
            elements.append(Paragraph(signature.address, sig_style_center))
    else:
        # Single signature (no /s/ - space for hand signature)
        elements.append(Paragraph("_________________________", sig_style_center))
        if signature.attorney_name:
            elements.append(Paragraph(f"<b>{signature.attorney_name}, Pro Se</b>", sig_style_center))
        if signature.phone:
            elements.append(Paragraph(f"Tel: {signature.phone}", sig_style_center))
        if signature.email:
            elements.append(Paragraph(signature.email, sig_style_center))
        if signature.address:
            elements.append(Paragraph(signature.address, sig_style_center))

    # Certificate of Service (optional - can be excluded for emergency/standalone signature pages)
    include_certificate = getattr(signature, 'include_certificate', True)
    if include_certificate:
        elements.append(Spacer(1, LINE_SPACING))  # Single line before certificate
        elements.append(Paragraph("<b>CERTIFICATE OF SERVICE</b>", cert_header_style))

        cert_text = "I filed the foregoing in person with the Clerk of Court, which will send notification of such filing to all counsel of record."
        elements.append(Paragraph(cert_text, cert_body_style))

        # Add signature line and name for certificate of service
        elements.append(Spacer(1, SIG_SINGLE_SPACING * 2))  # Space for hand signature
        elements.append(Paragraph("_________________________", sig_style_center))
        if signature.attorney_name:
            elements.append(Paragraph(f"<b>{signature.attorney_name}</b>", sig_style_center))

    # Wrap everything in KeepTogether so they stay on same page
    return [KeepTogether(elements)]


def generate_pdf(
    paragraphs: dict,
    section_starts: dict,
    output_path: str | None = None,
    global_spacing=None,
    caption=None,
    signature=None,
    document_title: str = "",
    all_sections: list = None,
    skip_page_numbers: bool = False
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
        document_title: Title of document (e.g., "MOTION", "COMPLAINT") shown after caption
        all_sections: List of (section, para_num, is_subsection, parent_id, display_letter) tuples

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

    # Build a map of subsections by paragraph number
    # Format: {para_num: [(section, display_letter), ...]}
    subsection_map = {}
    if all_sections:
        for section, para_num, is_subsection, parent_id, display_letter in all_sections:
            if is_subsection:
                if para_num not in subsection_map:
                    subsection_map[para_num] = []
                subsection_map[para_num].append((section, display_letter))

    # Add caption if provided and has content
    has_caption_or_title = False
    if caption and (caption.plaintiff or caption.defendant or caption.case_number):
        story.extend(_build_caption(caption, font_name, document_title))
        has_caption_or_title = True
        # No extra spacer needed - spacing is in the title style

    current_section = None
    is_first_para_in_section = False
    is_first_section = True  # Track if this is the first section after caption/title
    is_first_para_after_title = True  # Track if this is the very first paragraph

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
            # For first section after title: single line space (LINE_SPACING / 2)
            # For other sections: use before_section setting
            if is_first_section and has_caption_or_title and document_title:
                story.append(Spacer(1, LINE_SPACING / 2))  # Single line after title
            else:
                story.append(Spacer(1, LINE_SPACING * before_section))
            story.append(Paragraph(section_text, styles['section']))
            story.append(Spacer(1, LINE_SPACING * after_section / 2))
            is_first_para_in_section = True
            is_first_section = False
            is_first_para_after_title = False

        # Check if this paragraph has subsections
        if para_num in subsection_map:
            for subsection, display_letter in subsection_map[para_num]:
                # Add subsection header (left aligned, bold, uppercase letters)
                upper_letter = display_letter.upper()
                subsection_text = f"<b>{upper_letter}. {subsection.title}</b>"
                story.append(Spacer(1, LINE_SPACING / 2))
                story.append(Paragraph(subsection_text, styles['subsection']))
                story.append(Spacer(1, LINE_SPACING / 4))
                is_first_para_in_section = True  # Treat first para after subsection like first para in section

        if para_num not in section_starts:
            # Add spacing between paragraphs (not before first para in section or first para after title)
            if story and not is_first_para_in_section and not (is_first_para_after_title and has_caption_or_title and document_title):
                # Get current section's spacing
                spacing = current_section.custom_spacing if current_section and current_section.custom_spacing else None
                between = spacing.between_paragraphs if spacing else default_between_paragraphs
                if between > 0:
                    story.append(Spacer(1, LINE_SPACING * between / 2))

        is_first_para_in_section = False
        is_first_para_after_title = False

        # Add extra spacing from multiple <line> tags (extra_lines_before)
        # <line><line> = 1 extra line, <line><line><line> = 2 extra lines, etc.
        if hasattr(para, 'extra_lines_before') and para.extra_lines_before > 0:
            extra_space = LINE_SPACING * para.extra_lines_before
            story.append(Spacer(1, extra_space))

        # Add numbered paragraph
        # Escape any HTML-like characters in the text
        safe_text = para.text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        para_text = f"{para.number}.&nbsp;&nbsp;&nbsp;{safe_text}"
        story.append(Paragraph(para_text, styles['paragraph']))

    # Add signature block and certificate of service if provided
    if signature and signature.attorney_name:
        story.extend(_build_signature_and_certificate(signature, font_name))

    # Build PDF with or without page numbers
    if skip_page_numbers:
        doc.build(story)
    else:
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
