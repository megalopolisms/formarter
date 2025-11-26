"""
TRO Motion Compliance Checklist - 107 Items

Based on:
- Fed. R. Civ. P. 65 (Injunctions and Restraining Orders)
- L.U.Civ.R. (Local Uniform Civil Rules)
- Federal court formatting requirements
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class CheckCategory(Enum):
    """Categories for checklist items."""
    CAPTION = "Caption and Title"
    MOTION_CONTENT = "Motion Content"
    CERTIFICATE_NOTICE = "Certificate of Notice Efforts"
    SECURITY_BOND = "Security/Bond"
    RELIEF_REQUESTED = "Relief Requested"
    VERIFICATION = "Verification/Declaration"
    FORMATTING = "Formatting"
    SIGNATURE = "Signature Block"
    CERTIFICATE_SERVICE = "Certificate of Service"
    DATE_FILING = "Date of Filing"
    EXHIBITS = "Exhibits and Attachments"
    PROPOSED_ORDER = "Proposed Order Requirements"
    URGENT_EMERGENCY = "Urgent/Emergency Procedures"
    PRO_SE = "Pro Se Filing Requirements"


class CheckStatus(Enum):
    """Status of a checklist item check."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    MANUAL = "manual"  # Requires manual verification
    NOT_APPLICABLE = "n/a"


@dataclass
class ChecklistItem:
    """A single item in the compliance checklist."""
    id: int
    category: CheckCategory
    description: str
    rule_citation: str
    auto_checkable: bool = False
    pattern: Optional[str] = None  # Regex pattern for auto-check
    required_text: Optional[str] = None  # Required text to find
    check_method: Optional[str] = None  # Name of detector method to call


# =============================================================================
# THE 107-ITEM TRO MOTION COMPLIANCE CHECKLIST
# =============================================================================

TRO_CHECKLIST: List[ChecklistItem] = [
    # =========================================================================
    # CATEGORY 1: CAPTION AND TITLE (Items 1-9)
    # =========================================================================
    ChecklistItem(
        id=1,
        category=CheckCategory.CAPTION,
        description="Caption includes full court name (UNITED STATES DISTRICT COURT)",
        rule_citation="L.U.Civ.R. 10(a)",
        auto_checkable=True,
        required_text="UNITED STATES DISTRICT COURT",
        check_method="check_court_name"
    ),
    ChecklistItem(
        id=2,
        category=CheckCategory.CAPTION,
        description="Caption includes plaintiff name and designation",
        rule_citation="Fed. R. Civ. P. 10(a)",
        auto_checkable=True,
        pattern=r"PLAINTIFF",
        check_method="check_plaintiff_designation"
    ),
    ChecklistItem(
        id=3,
        category=CheckCategory.CAPTION,
        description="Caption includes defendant names and designation",
        rule_citation="Fed. R. Civ. P. 10(a)",
        auto_checkable=True,
        pattern=r"DEFENDANT",
        check_method="check_defendant_designation"
    ),
    ChecklistItem(
        id=4,
        category=CheckCategory.CAPTION,
        description="Case number format is correct",
        rule_citation="L.U.Civ.R. 10(a)",
        auto_checkable=True,
        pattern=r"\d:\d{2}-cv-\d+",
        check_method="check_case_number"
    ),
    ChecklistItem(
        id=5,
        category=CheckCategory.CAPTION,
        description="Document title clearly identifies as MOTION",
        rule_citation="Fed. R. Civ. P. 7(b)(1)",
        auto_checkable=True,
        pattern=r"MOTION.*TEMPORARY RESTRAINING ORDER|MOTION.*TRO",
        check_method="check_motion_title"
    ),
    ChecklistItem(
        id=6,
        category=CheckCategory.CAPTION,
        description="Title cites Fed. R. Civ. P. 65",
        rule_citation="L.U.Civ.R. 65",
        auto_checkable=True,
        pattern=r"Rule\s*65|Fed\.?\s*R\.?\s*Civ\.?\s*P\.?\s*65",
        check_method="check_rule_65_in_title"
    ),
    ChecklistItem(
        id=7,
        category=CheckCategory.CAPTION,
        description="'EX PARTE' in title if no prior notice to defendants",
        rule_citation="Fed. R. Civ. P. 65(b)",
        auto_checkable=True,
        pattern=r"EX\s*PARTE",
        check_method="check_ex_parte"
    ),
    ChecklistItem(
        id=8,
        category=CheckCategory.CAPTION,
        description="'URGENT AND NECESSITOUS' in title if expedited review needed",
        rule_citation="L.U.Civ.R. 7(b)(5)",
        auto_checkable=True,
        pattern=r"URGENT|NECESSITOUS",
        check_method="check_urgent_title"
    ),
    ChecklistItem(
        id=9,
        category=CheckCategory.CAPTION,
        description="'EMERGENCY' in title if applicable",
        rule_citation="L.U.Civ.R. 7(b)(5)",
        auto_checkable=True,
        pattern=r"EMERGENCY",
        check_method="check_emergency_title"
    ),

    # =========================================================================
    # CATEGORY 2: MOTION CONTENT (Items 10-21)
    # =========================================================================
    ChecklistItem(
        id=10,
        category=CheckCategory.MOTION_CONTENT,
        description="Opening paragraph identifies movant",
        rule_citation="Fed. R. Civ. P. 7(b)(1)",
        auto_checkable=True,
        pattern=r"(Plaintiff|Movant).*moves|hereby\s+moves",
        check_method="check_movant_identified"
    ),
    ChecklistItem(
        id=11,
        category=CheckCategory.MOTION_CONTENT,
        description="States movant is proceeding 'pro se'",
        rule_citation="L.U.Civ.R. 83.1",
        auto_checkable=True,
        pattern=r"pro\s*se",
        check_method="check_pro_se_stated"
    ),
    ChecklistItem(
        id=12,
        category=CheckCategory.MOTION_CONTENT,
        description="Cites Fed. R. Civ. P. 65(b) in opening",
        rule_citation="Fed. R. Civ. P. 65(b)",
        auto_checkable=True,
        pattern=r"65\s*\(b\)|Rule\s*65",
        check_method="check_rule_65b_cited"
    ),
    ChecklistItem(
        id=13,
        category=CheckCategory.MOTION_CONTENT,
        description="States grounds for relief sought",
        rule_citation="Fed. R. Civ. P. 7(b)(1)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=14,
        category=CheckCategory.MOTION_CONTENT,
        description="Contains factual grounds only (no legal argument)",
        rule_citation="L.U.Civ.R. 7(b)(2)(A)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=15,
        category=CheckCategory.MOTION_CONTENT,
        description="NO case citations in motion (belong in brief)",
        rule_citation="L.U.Civ.R. 7(b)(2)(B)",
        auto_checkable=True,
        pattern=r"\d+\s+(?:F\.\d+d?|U\.S\.|S\.Ct\.|L\.Ed\.)\s+\d+",
        check_method="check_no_case_citations"
    ),
    ChecklistItem(
        id=16,
        category=CheckCategory.MOTION_CONTENT,
        description="NO legal argument in motion (belong in brief)",
        rule_citation="L.U.Civ.R. 7(b)(2)(B)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=17,
        category=CheckCategory.MOTION_CONTENT,
        description="NO quotations from authorities in motion",
        rule_citation="L.U.Civ.R. 7(b)(2)(B)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=18,
        category=CheckCategory.MOTION_CONTENT,
        description="Identifies each defendant to be restrained",
        rule_citation="Fed. R. Civ. P. 65(d)(2)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=19,
        category=CheckCategory.MOTION_CONTENT,
        description="Describes specific acts to be restrained",
        rule_citation="Fed. R. Civ. P. 65(d)(1)(C)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=20,
        category=CheckCategory.MOTION_CONTENT,
        description="Identifies whether relief is mandatory or prohibitory",
        rule_citation="Fed. R. Civ. P. 65(b)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=21,
        category=CheckCategory.MOTION_CONTENT,
        description="States specific facts showing irreparable injury",
        rule_citation="Fed. R. Civ. P. 65(b)(1)(A)",
        auto_checkable=True,
        pattern=r"irreparable\s+(harm|injury|damage)",
        check_method="check_irreparable_harm"
    ),

    # =========================================================================
    # CATEGORY 3: CERTIFICATE OF NOTICE EFFORTS (Items 22-26)
    # =========================================================================
    ChecklistItem(
        id=22,
        category=CheckCategory.CERTIFICATE_NOTICE,
        description="Certificate of notice efforts included",
        rule_citation="Fed. R. Civ. P. 65(b)(1)(B)",
        auto_checkable=True,
        pattern=r"CERTIFICATE\s+OF\s+NOTICE|notice\s+effort",
        check_method="check_certificate_notice"
    ),
    ChecklistItem(
        id=23,
        category=CheckCategory.CERTIFICATE_NOTICE,
        description="Certificate signed by movant",
        rule_citation="Fed. R. Civ. P. 65(b)(1)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=24,
        category=CheckCategory.CERTIFICATE_NOTICE,
        description="Describes specific efforts to give notice",
        rule_citation="Fed. R. Civ. P. 65(b)(1)(B)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=25,
        category=CheckCategory.CERTIFICATE_NOTICE,
        description="Describes responses received (if any)",
        rule_citation="Fed. R. Civ. P. 65(b)(1)(B)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=26,
        category=CheckCategory.CERTIFICATE_NOTICE,
        description="States reasons why notice should not be required (if applicable)",
        rule_citation="Fed. R. Civ. P. 65(b)(1)(B)",
        auto_checkable=False
    ),

    # =========================================================================
    # CATEGORY 4: SECURITY/BOND (Items 27-30)
    # =========================================================================
    ChecklistItem(
        id=27,
        category=CheckCategory.SECURITY_BOND,
        description="Addresses Rule 65(c) security/bond requirement",
        rule_citation="Fed. R. Civ. P. 65(c)",
        auto_checkable=True,
        pattern=r"65\s*\(c\)|security|bond",
        check_method="check_bond_addressed"
    ),
    ChecklistItem(
        id=28,
        category=CheckCategory.SECURITY_BOND,
        description="Proposes specific bond amount or waiver request",
        rule_citation="Fed. R. Civ. P. 65(c)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=29,
        category=CheckCategory.SECURITY_BOND,
        description="Explains basis for waiver if requesting one",
        rule_citation="Fed. R. Civ. P. 65(c)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=30,
        category=CheckCategory.SECURITY_BOND,
        description="States will not post bond until Court orders",
        rule_citation="Fed. R. Civ. P. 65(c)",
        auto_checkable=False
    ),

    # =========================================================================
    # CATEGORY 5: RELIEF REQUESTED (Items 31-35)
    # =========================================================================
    ChecklistItem(
        id=31,
        category=CheckCategory.RELIEF_REQUESTED,
        description="Clearly identifies specific relief sought",
        rule_citation="Fed. R. Civ. P. 65(b)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=32,
        category=CheckCategory.RELIEF_REQUESTED,
        description="Identifies specific acts to be enjoined",
        rule_citation="Fed. R. Civ. P. 65(d)(1)(C)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=33,
        category=CheckCategory.RELIEF_REQUESTED,
        description="Identifies persons to be bound by the order",
        rule_citation="Fed. R. Civ. P. 65(d)(2)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=34,
        category=CheckCategory.RELIEF_REQUESTED,
        description="Requests appropriate duration (max 14 days)",
        rule_citation="Fed. R. Civ. P. 65(b)(2)",
        auto_checkable=True,
        pattern=r"14\s*days|fourteen\s*days",
        check_method="check_duration_request"
    ),
    ChecklistItem(
        id=35,
        category=CheckCategory.RELIEF_REQUESTED,
        description="Requests setting of preliminary injunction hearing",
        rule_citation="Fed. R. Civ. P. 65(b)(3)",
        auto_checkable=True,
        pattern=r"preliminary\s+injunction\s+hearing|hearing.*preliminary",
        check_method="check_pi_hearing_request"
    ),

    # =========================================================================
    # CATEGORY 6: VERIFICATION/DECLARATION (Items 36-42)
    # =========================================================================
    ChecklistItem(
        id=36,
        category=CheckCategory.VERIFICATION,
        description="Declaration/verification included",
        rule_citation="Fed. R. Civ. P. 65(b)(1)(A)",
        auto_checkable=True,
        pattern=r"DECLARATION|VERIFICATION|under penalty of perjury",
        check_method="check_declaration_exists"
    ),
    ChecklistItem(
        id=37,
        category=CheckCategory.VERIFICATION,
        description="Contains 28 U.S.C. § 1746 language",
        rule_citation="28 U.S.C. § 1746",
        auto_checkable=True,
        pattern=r"28\s*U\.S\.C\.\s*§?\s*1746|penalty of perjury",
        check_method="check_1746_language"
    ),
    ChecklistItem(
        id=38,
        category=CheckCategory.VERIFICATION,
        description="'True and correct' statement included",
        rule_citation="28 U.S.C. § 1746",
        auto_checkable=True,
        pattern=r"true\s+and\s+correct|true\s+and\s+accurate",
        check_method="check_true_correct"
    ),
    ChecklistItem(
        id=39,
        category=CheckCategory.VERIFICATION,
        description="States based on personal knowledge",
        rule_citation="28 U.S.C. § 1746",
        auto_checkable=True,
        pattern=r"personal\s+knowledge",
        check_method="check_personal_knowledge"
    ),
    ChecklistItem(
        id=40,
        category=CheckCategory.VERIFICATION,
        description="Signed by declarant",
        rule_citation="28 U.S.C. § 1746",
        auto_checkable=True,
        pattern=r"/s/|signature",
        check_method="check_declaration_signed"
    ),
    ChecklistItem(
        id=41,
        category=CheckCategory.VERIFICATION,
        description="Includes date of declaration",
        rule_citation="28 U.S.C. § 1746",
        auto_checkable=False
    ),
    ChecklistItem(
        id=42,
        category=CheckCategory.VERIFICATION,
        description="Includes location (city, state)",
        rule_citation="28 U.S.C. § 1746",
        auto_checkable=False
    ),

    # =========================================================================
    # CATEGORY 7: FORMATTING (Items 43-55)
    # =========================================================================
    ChecklistItem(
        id=43,
        category=CheckCategory.FORMATTING,
        description="Font is Times New Roman 12pt or equivalent",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=44,
        category=CheckCategory.FORMATTING,
        description="Body text is double-spaced",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=45,
        category=CheckCategory.FORMATTING,
        description="Block quotations may be single-spaced",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=46,
        category=CheckCategory.FORMATTING,
        description="Headings may be single-spaced",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=47,
        category=CheckCategory.FORMATTING,
        description="Footnotes are 11pt minimum",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=48,
        category=CheckCategory.FORMATTING,
        description="Top margin is 1 inch",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=49,
        category=CheckCategory.FORMATTING,
        description="Bottom margin is 1 inch",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=50,
        category=CheckCategory.FORMATTING,
        description="Left margin is 1 inch",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=51,
        category=CheckCategory.FORMATTING,
        description="Right margin is 1 inch",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=52,
        category=CheckCategory.FORMATTING,
        description="Page numbers present",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=53,
        category=CheckCategory.FORMATTING,
        description="Page numbers within margins",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=54,
        category=CheckCategory.FORMATTING,
        description="Motion is 4 pages or less",
        rule_citation="L.U.Civ.R. 7(b)(2)(A)",
        auto_checkable=True,
        check_method="check_page_count"
    ),
    ChecklistItem(
        id=55,
        category=CheckCategory.FORMATTING,
        description="Paper size is 8.5 x 11 inches",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False
    ),

    # =========================================================================
    # CATEGORY 8: SIGNATURE BLOCK (Items 56-64)
    # =========================================================================
    ChecklistItem(
        id=56,
        category=CheckCategory.SIGNATURE,
        description="Signature block at end of document",
        rule_citation="Fed. R. Civ. P. 11(a)",
        auto_checkable=True,
        pattern=r"Respectfully\s+submitted|/s/",
        check_method="check_signature_block"
    ),
    ChecklistItem(
        id=57,
        category=CheckCategory.SIGNATURE,
        description="Actual or electronic signature present",
        rule_citation="Fed. R. Civ. P. 11(a)",
        auto_checkable=True,
        pattern=r"/s/\s*\w+",
        check_method="check_electronic_signature"
    ),
    ChecklistItem(
        id=58,
        category=CheckCategory.SIGNATURE,
        description="Full name printed below signature",
        rule_citation="Fed. R. Civ. P. 11(a)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=59,
        category=CheckCategory.SIGNATURE,
        description="Mailing address included",
        rule_citation="Fed. R. Civ. P. 11(a)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=60,
        category=CheckCategory.SIGNATURE,
        description="Physical address if different from mailing",
        rule_citation="L.U.Civ.R. 83.1(c)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=61,
        category=CheckCategory.SIGNATURE,
        description="Phone number included",
        rule_citation="Fed. R. Civ. P. 11(a)",
        auto_checkable=True,
        pattern=r"\(\d{3}\)\s*\d{3}[-.]?\d{4}|\d{3}[-.]?\d{3}[-.]?\d{4}",
        check_method="check_phone_number"
    ),
    ChecklistItem(
        id=62,
        category=CheckCategory.SIGNATURE,
        description="Email address included",
        rule_citation="Fed. R. Civ. P. 11(a)",
        auto_checkable=True,
        pattern=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        check_method="check_email_address"
    ),
    ChecklistItem(
        id=63,
        category=CheckCategory.SIGNATURE,
        description="'Pro Se Plaintiff' designation included",
        rule_citation="L.U.Civ.R. 83.1",
        auto_checkable=True,
        pattern=r"Pro\s*Se\s*Plaintiff",
        check_method="check_pro_se_designation"
    ),
    ChecklistItem(
        id=64,
        category=CheckCategory.SIGNATURE,
        description="Bar number NOT required for pro se",
        rule_citation="L.U.Civ.R. 83.1",
        auto_checkable=False
    ),

    # =========================================================================
    # CATEGORY 9: CERTIFICATE OF SERVICE (Items 65-73)
    # =========================================================================
    ChecklistItem(
        id=65,
        category=CheckCategory.CERTIFICATE_SERVICE,
        description="Certificate of service included",
        rule_citation="Fed. R. Civ. P. 5(d)(1)(B)",
        auto_checkable=True,
        pattern=r"CERTIFICATE\s+OF\s+SERVICE",
        check_method="check_certificate_service"
    ),
    ChecklistItem(
        id=66,
        category=CheckCategory.CERTIFICATE_SERVICE,
        description="States date of service",
        rule_citation="Fed. R. Civ. P. 5(d)(1)(B)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=67,
        category=CheckCategory.CERTIFICATE_SERVICE,
        description="Date matches actual service date",
        rule_citation="Fed. R. Civ. P. 5(d)(1)(B)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=68,
        category=CheckCategory.CERTIFICATE_SERVICE,
        description="Lists all parties served",
        rule_citation="Fed. R. Civ. P. 5(a)(1)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=69,
        category=CheckCategory.CERTIFICATE_SERVICE,
        description="Full name of each party served",
        rule_citation="Fed. R. Civ. P. 5(a)(1)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=70,
        category=CheckCategory.CERTIFICATE_SERVICE,
        description="Address of each party served",
        rule_citation="Fed. R. Civ. P. 5(b)(2)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=71,
        category=CheckCategory.CERTIFICATE_SERVICE,
        description="Method of service stated",
        rule_citation="Fed. R. Civ. P. 5(b)(2)",
        auto_checkable=True,
        pattern=r"(mail|email|electronic|hand.deliver|CM/ECF)",
        check_method="check_service_method"
    ),
    ChecklistItem(
        id=72,
        category=CheckCategory.CERTIFICATE_SERVICE,
        description="Signed by person making service",
        rule_citation="Fed. R. Civ. P. 5(d)(1)(B)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=73,
        category=CheckCategory.CERTIFICATE_SERVICE,
        description="Pro se: reflects mail or hand delivery (not CM/ECF)",
        rule_citation="L.U.Civ.R. 5(a)(2)",
        auto_checkable=False
    ),

    # =========================================================================
    # CATEGORY 10: DATE OF FILING (Items 74-77)
    # =========================================================================
    ChecklistItem(
        id=74,
        category=CheckCategory.DATE_FILING,
        description="Date line present on document",
        rule_citation="Fed. R. Civ. P. 11(a)",
        auto_checkable=True,
        pattern=r"Dated:|Date:|dated this",
        check_method="check_date_line"
    ),
    ChecklistItem(
        id=75,
        category=CheckCategory.DATE_FILING,
        description="Date matches intended filing date",
        rule_citation="Fed. R. Civ. P. 11(a)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=76,
        category=CheckCategory.DATE_FILING,
        description="Declaration date matches or precedes filing date",
        rule_citation="28 U.S.C. § 1746",
        auto_checkable=False
    ),
    ChecklistItem(
        id=77,
        category=CheckCategory.DATE_FILING,
        description="Service date matches filing date",
        rule_citation="Fed. R. Civ. P. 5(d)(1)",
        auto_checkable=False
    ),

    # =========================================================================
    # CATEGORY 11: EXHIBITS AND ATTACHMENTS (Items 78-86)
    # =========================================================================
    ChecklistItem(
        id=78,
        category=CheckCategory.EXHIBITS,
        description="Declaration/affidavit attached",
        rule_citation="Fed. R. Civ. P. 65(b)(1)(A)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=79,
        category=CheckCategory.EXHIBITS,
        description="Proposed order attached",
        rule_citation="L.U.Civ.R. 65(a)(2)",
        auto_checkable=True,
        pattern=r"PROPOSED\s+ORDER|ORDER\s+GRANTING",
        check_method="check_proposed_order"
    ),
    ChecklistItem(
        id=80,
        category=CheckCategory.EXHIBITS,
        description="Exhibits properly labeled (Exhibit A, B, etc.)",
        rule_citation="L.U.Civ.R. 10(c)",
        auto_checkable=True,
        pattern=r"Exhibit\s+[A-Z]|EXHIBIT\s+[A-Z]",
        check_method="check_exhibit_labels"
    ),
    ChecklistItem(
        id=81,
        category=CheckCategory.EXHIBITS,
        description="Exhibits have descriptive captions",
        rule_citation="L.U.Civ.R. 10(c)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=82,
        category=CheckCategory.EXHIBITS,
        description="Exhibits attached to motion (not filed separately)",
        rule_citation="L.U.Civ.R. 10(c)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=83,
        category=CheckCategory.EXHIBITS,
        description="Privacy redactions: SSN redacted to last 4 digits",
        rule_citation="Fed. R. Civ. P. 5.2(a)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=84,
        category=CheckCategory.EXHIBITS,
        description="Privacy redactions: Financial account numbers redacted",
        rule_citation="Fed. R. Civ. P. 5.2(a)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=85,
        category=CheckCategory.EXHIBITS,
        description="Privacy redactions: Birth dates show only year",
        rule_citation="Fed. R. Civ. P. 5.2(a)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=86,
        category=CheckCategory.EXHIBITS,
        description="Privacy redactions: Minor names redacted to initials",
        rule_citation="Fed. R. Civ. P. 5.2(a)",
        auto_checkable=False
    ),

    # =========================================================================
    # CATEGORY 12: PROPOSED ORDER REQUIREMENTS (Items 87-97)
    # =========================================================================
    ChecklistItem(
        id=87,
        category=CheckCategory.PROPOSED_ORDER,
        description="Proposed order states reasons for issuance",
        rule_citation="Fed. R. Civ. P. 65(d)(1)(A)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=88,
        category=CheckCategory.PROPOSED_ORDER,
        description="Proposed order states terms specifically",
        rule_citation="Fed. R. Civ. P. 65(d)(1)(B)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=89,
        category=CheckCategory.PROPOSED_ORDER,
        description="Proposed order describes acts restrained in detail",
        rule_citation="Fed. R. Civ. P. 65(d)(1)(C)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=90,
        category=CheckCategory.PROPOSED_ORDER,
        description="No incorporation by reference to complaint/motion",
        rule_citation="Fed. R. Civ. P. 65(d)(1)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=91,
        category=CheckCategory.PROPOSED_ORDER,
        description="Identifies parties bound by order",
        rule_citation="Fed. R. Civ. P. 65(d)(2)(A)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=92,
        category=CheckCategory.PROPOSED_ORDER,
        description="Identifies officers/agents/employees bound",
        rule_citation="Fed. R. Civ. P. 65(d)(2)(B)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=93,
        category=CheckCategory.PROPOSED_ORDER,
        description="Identifies persons in active concert bound",
        rule_citation="Fed. R. Civ. P. 65(d)(2)(C)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=94,
        category=CheckCategory.PROPOSED_ORDER,
        description="States duration of TRO (max 14 days)",
        rule_citation="Fed. R. Civ. P. 65(b)(2)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=95,
        category=CheckCategory.PROPOSED_ORDER,
        description="States bond amount or waiver",
        rule_citation="Fed. R. Civ. P. 65(c)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=96,
        category=CheckCategory.PROPOSED_ORDER,
        description="Signature line for judge",
        rule_citation="L.U.Civ.R. 65",
        auto_checkable=False
    ),
    ChecklistItem(
        id=97,
        category=CheckCategory.PROPOSED_ORDER,
        description="Word version of proposed order prepared",
        rule_citation="L.U.Civ.R. 65(a)(2)",
        auto_checkable=False
    ),

    # =========================================================================
    # CATEGORY 13: URGENT/EMERGENCY PROCEDURES (Items 98-103)
    # =========================================================================
    ChecklistItem(
        id=98,
        category=CheckCategory.URGENT_EMERGENCY,
        description="'URGENT' in title if expedited review needed",
        rule_citation="L.U.Civ.R. 7(b)(5)",
        auto_checkable=True,
        pattern=r"URGENT",
        check_method="check_urgent_in_title"
    ),
    ChecklistItem(
        id=99,
        category=CheckCategory.URGENT_EMERGENCY,
        description="Deputy clerk contacted re: emergency",
        rule_citation="L.U.Civ.R. 77(c)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=100,
        category=CheckCategory.URGENT_EMERGENCY,
        description="Hearing coordinated with clerk's office",
        rule_citation="L.U.Civ.R. 77(c)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=101,
        category=CheckCategory.URGENT_EMERGENCY,
        description="Notice of hearing prepared (if required)",
        rule_citation="L.U.Civ.R. 7(b)(4)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=102,
        category=CheckCategory.URGENT_EMERGENCY,
        description="Notice of hearing filed with motion",
        rule_citation="L.U.Civ.R. 7(b)(4)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=103,
        category=CheckCategory.URGENT_EMERGENCY,
        description="Notice of hearing served on all parties",
        rule_citation="L.U.Civ.R. 7(b)(4)",
        auto_checkable=False
    ),

    # =========================================================================
    # CATEGORY 14: PRO SE FILING REQUIREMENTS (Items 104-107)
    # =========================================================================
    ChecklistItem(
        id=104,
        category=CheckCategory.PRO_SE,
        description="Paper original prepared for filing (if not e-filing)",
        rule_citation="L.U.Civ.R. 5(a)(2)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=105,
        category=CheckCategory.PRO_SE,
        description="Copies prepared for file-stamping",
        rule_citation="L.U.Civ.R. 5(a)(2)",
        auto_checkable=False
    ),
    ChecklistItem(
        id=106,
        category=CheckCategory.PRO_SE,
        description="Filing fee paid or IFP granted/pending",
        rule_citation="28 U.S.C. § 1914",
        auto_checkable=False
    ),
    ChecklistItem(
        id=107,
        category=CheckCategory.PRO_SE,
        description="File-stamped copies retained for records",
        rule_citation="L.U.Civ.R. 5(a)(2)",
        auto_checkable=False
    ),
]


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_checklist_by_category(category: CheckCategory) -> List[ChecklistItem]:
    """Get all checklist items for a specific category."""
    return [item for item in TRO_CHECKLIST if item.category == category]


def get_auto_checkable_items() -> List[ChecklistItem]:
    """Get all items that can be auto-checked."""
    return [item for item in TRO_CHECKLIST if item.auto_checkable]


def get_manual_items() -> List[ChecklistItem]:
    """Get all items that require manual review."""
    return [item for item in TRO_CHECKLIST if not item.auto_checkable]


def get_item_by_id(item_id: int) -> Optional[ChecklistItem]:
    """Get a specific checklist item by ID."""
    for item in TRO_CHECKLIST:
        if item.id == item_id:
            return item
    return None


# Statistics
AUTO_CHECKABLE_COUNT = len(get_auto_checkable_items())
MANUAL_REVIEW_COUNT = len(get_manual_items())
TOTAL_ITEMS = len(TRO_CHECKLIST)
