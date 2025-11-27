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
    # NEW: Success criteria for subagent verification
    success_criteria: str = ""  # What success looks like (detailed description)
    redundancy_patterns: Optional[List[str]] = None  # Alternative patterns to verify (backup checks)
    fail_severity: str = "normal"  # "critical", "normal", "minor" - how serious is a failure
    rule_explanation: str = ""  # Plain English explanation of the rule
    fix_suggestion: str = ""  # Specific language or steps to fix a failure


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
        check_method="check_court_name",
        success_criteria="Document header contains 'UNITED STATES DISTRICT COURT' followed by district name (e.g., 'FOR THE SOUTHERN DISTRICT OF MISSISSIPPI'). Must be in ALL CAPS, typically centered at top of first page.",
        redundancy_patterns=["U.S. DISTRICT COURT", "DISTRICT COURT", "IN THE UNITED STATES"],
        fail_severity="critical",
        rule_explanation="Per L.U.Civ.R. 10(a), all documents must contain proper court identification in the caption.",
        fix_suggestion="Select a Case Profile from the dropdown. The app will auto-generate the caption with: UNITED STATES DISTRICT COURT FOR THE SOUTHERN DISTRICT OF MISSISSIPPI"
    ),
    ChecklistItem(
        id=2,
        category=CheckCategory.CAPTION,
        description="Caption includes plaintiff name and designation",
        rule_citation="Fed. R. Civ. P. 10(a)",
        auto_checkable=True,
        pattern=r"PLAINTIFF",
        check_method="check_plaintiff_designation",
        success_criteria="Caption contains plaintiff's full legal name followed by 'Plaintiff' or 'Plaintiffs' designation. Example: 'JOHN DOE, Plaintiff' or 'JOHN DOE and JANE DOE, Plaintiffs'. Pro se plaintiffs should see their name clearly listed.",
        redundancy_patterns=["Plaintiff,", "Plaintiffs,", ", Plaintiff", "PRO SE PLAINTIFF"],
        fail_severity="critical",
        rule_explanation="Fed. R. Civ. P. 10(a) requires caption to name all parties; plaintiff identification is mandatory.",
        fix_suggestion="Select a Case Profile from the dropdown. The caption will include plaintiff designation automatically."
    ),
    ChecklistItem(
        id=3,
        category=CheckCategory.CAPTION,
        description="Caption includes defendant names and designation",
        rule_citation="Fed. R. Civ. P. 10(a)",
        auto_checkable=True,
        pattern=r"DEFENDANT",
        check_method="check_defendant_designation",
        success_criteria="Caption contains defendant's name(s) followed by 'Defendant' or 'Defendants' designation. Example: 'CITY OF BILOXI, Defendant'. Government entities should be named with full official name.",
        redundancy_patterns=["Defendant.", "Defendants.", ", Defendant", "et al., Defendants"],
        fail_severity="critical",
        rule_explanation="Fed. R. Civ. P. 10(a) requires all parties to be named in the caption.",
        fix_suggestion="Select a Case Profile from the dropdown. The caption will include defendant designation automatically."
    ),
    ChecklistItem(
        id=4,
        category=CheckCategory.CAPTION,
        description="Case number format is correct",
        rule_citation="L.U.Civ.R. 10(a)",
        auto_checkable=True,
        pattern=r"\d:\d{2}-cv-\d+",
        check_method="check_case_number",
        success_criteria="Case number follows federal format: 'X:XX-cv-XXXXX' where X is division number, XX is year, and XXXXX is case number. Examples: '3:24-cv-00178', '1:23-cv-00042'. Must appear in caption area.",
        redundancy_patterns=[r"Civil Action No\.", r"Case No\.", r"No\. \d+", r"\d{1,2}:\d{2}-cv"],
        fail_severity="critical",
        rule_explanation="Case number identifies the matter; incorrect format may cause filing rejection.",
        fix_suggestion="Select a Case Profile from the dropdown. The case number (e.g., 3:24-cv-00178) will be auto-generated in the caption."
    ),
    ChecklistItem(
        id=5,
        category=CheckCategory.CAPTION,
        description="Document title clearly identifies as MOTION",
        rule_citation="Fed. R. Civ. P. 7(b)(1)",
        auto_checkable=True,
        pattern=r"MOTION.*TEMPORARY RESTRAINING ORDER|MOTION.*TRO",
        check_method="check_motion_title",
        success_criteria="Document title clearly states 'MOTION FOR TEMPORARY RESTRAINING ORDER' or equivalent (e.g., 'MOTION FOR TRO', 'EMERGENCY MOTION FOR TEMPORARY RESTRAINING ORDER'). Title appears after caption, typically centered and in bold/caps.",
        redundancy_patterns=["MOTION FOR.*RESTRAINING", "TRO MOTION", "APPLICATION FOR.*RESTRAINING ORDER"],
        fail_severity="critical",
        rule_explanation="Fed. R. Civ. P. 7(b)(1) requires motions to state their purpose; unclear titles may delay processing.",
        fix_suggestion="Set the 'Document Title' field to: MOTION FOR TEMPORARY RESTRAINING ORDER PURSUANT TO FED. R. CIV. P. 65"
    ),
    ChecklistItem(
        id=6,
        category=CheckCategory.CAPTION,
        description="Title cites Fed. R. Civ. P. 65",
        rule_citation="L.U.Civ.R. 65",
        auto_checkable=True,
        pattern=r"Rule\s*65|Fed\.?\s*R\.?\s*Civ\.?\s*P\.?\s*65",
        check_method="check_rule_65_in_title",
        success_criteria="Document title or subtitle references Rule 65, the federal rule governing TROs. Examples: 'MOTION...PURSUANT TO FED. R. CIV. P. 65', 'MOTION...UNDER RULE 65'. Should appear in title line.",
        redundancy_patterns=["FRCP 65", "Rule 65(b)", "Fed.R.Civ.P. 65", "pursuant to Rule 65"],
        fail_severity="normal",
        rule_explanation="Citing the governing rule helps the court immediately identify the type of relief sought.",
        fix_suggestion="Add 'PURSUANT TO FED. R. CIV. P. 65' to your document title. Example: MOTION FOR TEMPORARY RESTRAINING ORDER PURSUANT TO FED. R. CIV. P. 65"
    ),
    ChecklistItem(
        id=7,
        category=CheckCategory.CAPTION,
        description="'EX PARTE' in title if no prior notice to defendants",
        rule_citation="Fed. R. Civ. P. 65(b)",
        auto_checkable=True,
        pattern=r"EX\s*PARTE",
        check_method="check_ex_parte",
        success_criteria="If seeking TRO without advance notice to opposing party, title MUST include 'EX PARTE'. Example: 'EX PARTE MOTION FOR TEMPORARY RESTRAINING ORDER'. Not required if notice was given.",
        redundancy_patterns=["WITHOUT NOTICE", "WITHOUT PRIOR NOTICE", "EX-PARTE"],
        fail_severity="normal",
        rule_explanation="Fed. R. Civ. P. 65(b) allows TRO without notice only in specific circumstances; 'ex parte' designation alerts court.",
        fix_suggestion="Add 'EX PARTE' to your title: EX PARTE MOTION FOR TEMPORARY RESTRAINING ORDER. Only use if filing without giving notice to defendants."
    ),
    ChecklistItem(
        id=8,
        category=CheckCategory.CAPTION,
        description="'URGENT AND NECESSITOUS' in title if expedited review needed",
        rule_citation="L.U.Civ.R. 7(b)(5)",
        auto_checkable=True,
        pattern=r"URGENT|NECESSITOUS",
        check_method="check_urgent_title",
        success_criteria="If expedited review is needed, title should include 'URGENT' or 'URGENT AND NECESSITOUS'. This alerts the clerk to prioritize the filing. Example: 'URGENT MOTION FOR TEMPORARY RESTRAINING ORDER'.",
        redundancy_patterns=["TIME-SENSITIVE", "EXPEDITED", "IMMEDIATE"],
        fail_severity="minor",
        rule_explanation="L.U.Civ.R. 7(b)(5) requires 'urgent and necessitous' designation for matters requiring immediate attention.",
        fix_suggestion="Add 'URGENT AND NECESSITOUS' to your title: URGENT AND NECESSITOUS MOTION FOR TEMPORARY RESTRAINING ORDER"
    ),
    ChecklistItem(
        id=9,
        category=CheckCategory.CAPTION,
        description="'EMERGENCY' in title if applicable",
        rule_citation="L.U.Civ.R. 7(b)(5)",
        auto_checkable=True,
        pattern=r"EMERGENCY",
        check_method="check_emergency_title",
        success_criteria="For true emergencies requiring same-day or immediate attention, title should include 'EMERGENCY'. Example: 'EMERGENCY MOTION FOR TEMPORARY RESTRAINING ORDER'. Use only for genuine emergencies.",
        redundancy_patterns=["EMERGENT", "IMMEDIATE RELIEF"],
        fail_severity="minor",
        rule_explanation="'Emergency' designation triggers expedited processing; misuse may result in sanctions.",
        fix_suggestion="Add 'EMERGENCY' to your title: EMERGENCY MOTION FOR TEMPORARY RESTRAINING ORDER. Use only for true emergencies requiring same-day action."
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
        check_method="check_movant_identified",
        success_criteria="First paragraph states who is filing the motion. Example: 'Plaintiff John Doe hereby moves this Court...' or 'Movant respectfully moves...'. Must clearly identify the party seeking relief.",
        redundancy_patterns=["Plaintiff moves", "Plaintiffs move", "respectfully moves", "comes now.*moves"],
        fail_severity="critical",
        rule_explanation="Fed. R. Civ. P. 7(b)(1) requires motions to state the relief sought and grounds; identifying movant is fundamental.",
        fix_suggestion="Add to your opening paragraph: 'Plaintiff [YOUR NAME], proceeding pro se, hereby moves this Court for a Temporary Restraining Order...'"
    ),
    ChecklistItem(
        id=11,
        category=CheckCategory.MOTION_CONTENT,
        description="States movant is proceeding 'pro se'",
        rule_citation="L.U.Civ.R. 83.1",
        auto_checkable=True,
        pattern=r"pro\s*se",
        check_method="check_pro_se_stated",
        success_criteria="Document explicitly states plaintiff is proceeding 'pro se' (representing themselves without attorney). Example: 'Plaintiff, proceeding pro se, moves...' or 'Pro se Plaintiff respectfully requests...'",
        redundancy_patterns=["self-represented", "without counsel", "in pro per", "appearing pro se"],
        fail_severity="normal",
        rule_explanation="Pro se status affects court procedures and gives notice that special accommodations may apply.",
        fix_suggestion="Add 'proceeding pro se' after your name in the opening: 'Plaintiff [NAME], proceeding pro se, respectfully moves...'"
    ),
    ChecklistItem(
        id=12,
        category=CheckCategory.MOTION_CONTENT,
        description="Cites Fed. R. Civ. P. 65(b) in opening",
        rule_citation="Fed. R. Civ. P. 65(b)",
        auto_checkable=True,
        pattern=r"65\s*\(b\)|Rule\s*65",
        check_method="check_rule_65b_cited",
        success_criteria="Motion body (not just title) references Rule 65 or Rule 65(b). Example: 'Pursuant to Federal Rule of Civil Procedure 65(b)...' or 'Under Rule 65, Plaintiff seeks...'. Rule must be cited in opening paragraphs.",
        redundancy_patterns=["Fed. R. Civ. P. 65", "FRCP 65", "Rule 65(b)(1)", "temporary restraining order under Rule"],
        fail_severity="critical",
        rule_explanation="Rule 65(b) is the governing rule for TROs; citing it shows the motion is properly grounded in law.",
        fix_suggestion="Add to your motion: 'Pursuant to Federal Rule of Civil Procedure 65(b), Plaintiff seeks a temporary restraining order...'"
    ),
    ChecklistItem(
        id=13,
        category=CheckCategory.MOTION_CONTENT,
        description="States grounds for relief sought",
        rule_citation="Fed. R. Civ. P. 7(b)(1)",
        auto_checkable=False,
        success_criteria="Motion explains WHY relief is needed - the factual basis. Look for: (1) what defendant is doing, (2) how it harms plaintiff, (3) why court action is needed. Should be factual, not legal argument.",
        fail_severity="critical",
        rule_explanation="Fed. R. Civ. P. 7(b)(1) requires motions to state 'the grounds for seeking the order.'"
    ),
    ChecklistItem(
        id=14,
        category=CheckCategory.MOTION_CONTENT,
        description="Contains factual grounds only (no legal argument)",
        rule_citation="L.U.Civ.R. 7(b)(2)(A)",
        auto_checkable=False,
        success_criteria="Motion contains FACTS only - what happened, when, where, who did what. NO legal analysis like 'this constitutes a violation of...' or 'under the standard for preliminary injunctions...' Legal argument belongs in the brief.",
        fail_severity="normal",
        rule_explanation="Southern District of Mississippi separates motions (facts) from briefs (law); this is LOCAL RULE specific."
    ),
    ChecklistItem(
        id=15,
        category=CheckCategory.MOTION_CONTENT,
        description="NO case citations in motion (belong in brief)",
        rule_citation="L.U.Civ.R. 7(b)(2)(B)",
        auto_checkable=True,
        pattern=r"\d+\s+(?:F\.\d+d?|U\.S\.|S\.Ct\.|L\.Ed\.)\s+\d+",
        check_method="check_no_case_citations",
        success_criteria="Motion should NOT contain case citations like '123 F.3d 456' or '500 U.S. 100'. Case law belongs in the supporting brief/memorandum, not the motion itself. SUCCESS = no case citations found.",
        redundancy_patterns=[r"\d+\s+F\.Supp", r"\d+\s+F\.App", r"v\.\s+.*,\s+\d+\s+F\.", r"See\s+[A-Z][a-z]+\s+v\."],
        fail_severity="critical",
        rule_explanation="L.U.Civ.R. 7(b)(2)(B) prohibits legal citations in motions; they must appear in briefs.",
        fix_suggestion="REMOVE all case citations (e.g., '123 F.3d 456') from the motion. Move them to your SUPPORTING BRIEF/MEMORANDUM. The motion should contain only facts, not legal citations."
    ),
    ChecklistItem(
        id=16,
        category=CheckCategory.MOTION_CONTENT,
        description="NO legal argument in motion (belong in brief)",
        rule_citation="L.U.Civ.R. 7(b)(2)(B)",
        auto_checkable=False,
        success_criteria="Motion should NOT argue the law. Watch for phrases like: 'Under the Winter factors...', 'The likelihood of success standard requires...', 'This Court should find...'. Legal analysis belongs in brief.",
        fail_severity="normal",
        rule_explanation="Local rules require separation of facts (motion) and law (brief)."
    ),
    ChecklistItem(
        id=17,
        category=CheckCategory.MOTION_CONTENT,
        description="NO quotations from authorities in motion",
        rule_citation="L.U.Civ.R. 7(b)(2)(B)",
        auto_checkable=False,
        success_criteria="Motion should NOT quote cases, statutes (except Rule 65), or other authorities. Block quotes from decisions = FAIL. Keep motion to plain facts only.",
        fail_severity="minor",
        rule_explanation="Quotations are legal argument that belong in the brief."
    ),
    ChecklistItem(
        id=18,
        category=CheckCategory.MOTION_CONTENT,
        description="Identifies each defendant to be restrained",
        rule_citation="Fed. R. Civ. P. 65(d)(2)",
        auto_checkable=False,
        success_criteria="Motion names EACH defendant who should be restrained. Example: 'Plaintiff seeks to restrain Defendant City of Biloxi and Defendant John Smith from...' All defendants to be bound must be specifically identified.",
        fail_severity="critical",
        rule_explanation="Rule 65(d)(2) requires the order to identify parties bound; motion must set this up."
    ),
    ChecklistItem(
        id=19,
        category=CheckCategory.MOTION_CONTENT,
        description="Describes specific acts to be restrained",
        rule_citation="Fed. R. Civ. P. 65(d)(1)(C)",
        auto_checkable=False,
        success_criteria="Motion must describe EXACTLY what defendant should be ordered to stop doing. Example: 'Defendant must be restrained from demolishing the property at 123 Main St.' Vague requests like 'stop harassing' = FAIL.",
        fail_severity="critical",
        rule_explanation="Rule 65(d)(1)(C) requires TROs to describe prohibited acts in reasonable detail."
    ),
    ChecklistItem(
        id=20,
        category=CheckCategory.MOTION_CONTENT,
        description="Identifies whether relief is mandatory or prohibitory",
        rule_citation="Fed. R. Civ. P. 65(b)",
        auto_checkable=False,
        success_criteria="Motion should clarify if it seeks: (1) PROHIBITORY relief (stop defendant from doing something), or (2) MANDATORY relief (force defendant to do something). Mandatory injunctions face higher scrutiny.",
        fail_severity="minor",
        rule_explanation="Mandatory injunctions are disfavored and require stronger showing; court needs to know which type."
    ),
    ChecklistItem(
        id=21,
        category=CheckCategory.MOTION_CONTENT,
        description="States specific facts showing irreparable injury",
        rule_citation="Fed. R. Civ. P. 65(b)(1)(A)",
        auto_checkable=True,
        pattern=r"irreparable\s+(harm|injury|damage)",
        check_method="check_irreparable_harm",
        success_criteria="Motion MUST use the phrase 'irreparable harm', 'irreparable injury', or 'irreparable damage' AND describe specific non-monetary harm. Example: 'Plaintiff will suffer irreparable harm because the property will be destroyed...'",
        redundancy_patterns=["cannot be undone", "no adequate remedy at law", "monetary damages.*inadequate", "permanent.*harm"],
        fail_severity="critical",
        rule_explanation="Rule 65(b)(1)(A) REQUIRES showing 'immediate and irreparable injury' - this is a mandatory element.",
        fix_suggestion="Add a paragraph stating: 'Plaintiff will suffer immediate and irreparable harm/injury because [describe specific harm that cannot be fixed with money]. Without this Court's intervention, [describe what will be permanently lost or damaged].'"
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
        check_method="check_certificate_notice",
        success_criteria="Document contains a section titled 'CERTIFICATE OF NOTICE' or 'CERTIFICATE OF NOTICE EFFORTS' that describes attempts to notify opposing parties before filing. Required for ex parte TROs.",
        redundancy_patterns=["efforts to provide notice", "attempted to notify", "notice was given", "without notice because"],
        fail_severity="critical",
        rule_explanation="Rule 65(b)(1)(B) REQUIRES certification describing 'efforts made to give notice and the reasons why it should not be required.'",
        fix_suggestion="Add a section titled 'CERTIFICATE OF NOTICE EFFORTS' stating: 'I certify that on [DATE], I made the following efforts to notify Defendant(s) of this motion: [describe calls, emails, letters sent]. [State responses received or that no response was received].'"
    ),
    ChecklistItem(
        id=23,
        category=CheckCategory.CERTIFICATE_NOTICE,
        description="Certificate signed by movant",
        rule_citation="Fed. R. Civ. P. 65(b)(1)",
        auto_checkable=False,
        success_criteria="The certificate of notice must be signed by movant's attorney or by pro se movant. Look for '/s/' signature line at end of certificate section. Certificate is sworn statement.",
        fail_severity="critical",
        rule_explanation="The certificate is a signed certification under Rule 65(b)(1); unsigned certificate is invalid."
    ),
    ChecklistItem(
        id=24,
        category=CheckCategory.CERTIFICATE_NOTICE,
        description="Describes specific efforts to give notice",
        rule_citation="Fed. R. Civ. P. 65(b)(1)(B)",
        auto_checkable=False,
        success_criteria="Certificate describes SPECIFIC attempts: 'On [date], I called defendant at [number]...', 'I emailed opposing counsel at [address]...', 'I sent notice by certified mail on [date]...'. Vague statements = FAIL.",
        fail_severity="critical",
        rule_explanation="Rule 65(b)(1)(B) requires 'efforts made to give notice' - must be specific, not conclusory."
    ),
    ChecklistItem(
        id=25,
        category=CheckCategory.CERTIFICATE_NOTICE,
        description="Describes responses received (if any)",
        rule_citation="Fed. R. Civ. P. 65(b)(1)(B)",
        auto_checkable=False,
        success_criteria="Certificate states what responses were received to notice attempts. Examples: 'Defendant did not respond', 'Defendant's voicemail was full', 'Counsel stated they could not appear.' If no response, explicitly state 'no response received.'",
        fail_severity="normal",
        rule_explanation="Court needs to know the outcome of notice efforts to assess ex parte status."
    ),
    ChecklistItem(
        id=26,
        category=CheckCategory.CERTIFICATE_NOTICE,
        description="States reasons why notice should not be required (if applicable)",
        rule_citation="Fed. R. Civ. P. 65(b)(1)(B)",
        auto_checkable=False,
        success_criteria="If seeking truly ex parte relief (no notice), certificate must explain WHY: (1) giving notice would allow defendant to cause irreparable harm, or (2) notice is impossible. Example: 'Notice would allow defendant to destroy evidence.'",
        fail_severity="normal",
        rule_explanation="Rule 65(b)(1)(B) requires reasons why notice 'should not be required' for true ex parte orders."
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
        check_method="check_bond_addressed",
        success_criteria="Motion addresses the bond/security requirement. Must mention 'bond', 'security', or 'Rule 65(c)'. Can request waiver but MUST address it. Example: 'Plaintiff requests waiver of bond under Rule 65(c).'",
        redundancy_patterns=["security bond", "injunction bond", "Rule 65(c)", "waiver of bond", "nominal bond"],
        fail_severity="critical",
        rule_explanation="Rule 65(c) requires security for TROs to protect defendant from wrongful restraint damages.",
        fix_suggestion="Add: 'Pursuant to Fed. R. Civ. P. 65(c), Plaintiff requests that the Court waive the security bond requirement because Plaintiff is proceeding in forma pauperis / this is a civil rights action / Defendant is unlikely to suffer damages from the restraining order.'"
    ),
    ChecklistItem(
        id=28,
        category=CheckCategory.SECURITY_BOND,
        description="Proposes specific bond amount or waiver request",
        rule_citation="Fed. R. Civ. P. 65(c)",
        auto_checkable=False,
        success_criteria="Motion proposes SPECIFIC amount ('Plaintiff offers $500 bond') OR requests waiver ('Plaintiff requests bond be waived') OR requests nominal bond ('Plaintiff requests $1 nominal bond'). Must be explicit.",
        fail_severity="normal",
        rule_explanation="Court needs a specific proposal to rule on; helps expedite bond determination."
    ),
    ChecklistItem(
        id=29,
        category=CheckCategory.SECURITY_BOND,
        description="Explains basis for waiver if requesting one",
        rule_citation="Fed. R. Civ. P. 65(c)",
        auto_checkable=False,
        success_criteria="If requesting bond waiver, must explain why: (1) indigency/IFP status, (2) public interest case, (3) defendant unlikely to suffer damages, (4) constitutional rights at stake. Waiver without justification = FAIL.",
        fail_severity="normal",
        rule_explanation="Courts have discretion to waive bond but need justification; common in civil rights and indigent cases."
    ),
    ChecklistItem(
        id=30,
        category=CheckCategory.SECURITY_BOND,
        description="States will not post bond until Court orders",
        rule_citation="Fed. R. Civ. P. 65(c)",
        auto_checkable=False,
        success_criteria="If not requesting waiver, motion should state plaintiff will post bond as ordered by Court. Example: 'Plaintiff is prepared to post security as this Court may require.' Shows good faith.",
        fail_severity="minor",
        rule_explanation="Demonstrates willingness to comply with Rule 65(c) if court orders bond."
    ),

    # =========================================================================
    # CATEGORY 5: RELIEF REQUESTED (Items 31-35)
    # =========================================================================
    ChecklistItem(
        id=31,
        category=CheckCategory.RELIEF_REQUESTED,
        description="Clearly identifies specific relief sought",
        rule_citation="Fed. R. Civ. P. 65(b)",
        auto_checkable=False,
        success_criteria="Motion has clear 'RELIEF REQUESTED' or 'WHEREFORE' section listing EXACTLY what plaintiff wants. Example: 'WHEREFORE, Plaintiff requests this Court: (1) Issue a TRO restraining Defendant from...; (2) Set hearing on preliminary injunction.'",
        fail_severity="critical",
        rule_explanation="Court cannot grant relief not specifically requested; clarity is essential."
    ),
    ChecklistItem(
        id=32,
        category=CheckCategory.RELIEF_REQUESTED,
        description="Identifies specific acts to be enjoined",
        rule_citation="Fed. R. Civ. P. 65(d)(1)(C)",
        auto_checkable=False,
        success_criteria="Relief section lists SPECIFIC prohibited conduct. Good: 'Enjoin defendant from demolishing 123 Main St.' Bad: 'Enjoin defendant from causing harm.' Must be specific enough for defendant to know exactly what's prohibited.",
        fail_severity="critical",
        rule_explanation="Rule 65(d)(1)(C) requires TROs to describe prohibited acts 'in reasonable detail.'"
    ),
    ChecklistItem(
        id=33,
        category=CheckCategory.RELIEF_REQUESTED,
        description="Identifies persons to be bound by the order",
        rule_citation="Fed. R. Civ. P. 65(d)(2)",
        auto_checkable=False,
        success_criteria="Motion identifies WHO should be bound: defendants by name, AND typically 'officers, agents, servants, employees, and all persons in active concert or participation.' This is standard TRO language.",
        redundancy_patterns=["officers, agents", "active concert", "persons bound"],
        fail_severity="normal",
        rule_explanation="Rule 65(d)(2) specifies who can be bound by injunctions; motion should match."
    ),
    ChecklistItem(
        id=34,
        category=CheckCategory.RELIEF_REQUESTED,
        description="Requests appropriate duration (max 14 days)",
        rule_citation="Fed. R. Civ. P. 65(b)(2)",
        auto_checkable=True,
        pattern=r"14\s*days|fourteen\s*days",
        check_method="check_duration_request",
        success_criteria="Motion requests TRO duration of 14 days or less. Example: 'TRO effective for 14 days' or 'until preliminary injunction hearing, not to exceed 14 days.' TROs cannot exceed 14 days without extension.",
        redundancy_patterns=["two weeks", "for a period not exceeding 14", "maximum duration", "until hearing"],
        fail_severity="normal",
        rule_explanation="Rule 65(b)(2) limits TROs to 14 days (extendable once for good cause).",
        fix_suggestion="Add to your relief section: 'Plaintiff requests the TRO remain in effect for fourteen (14) days or until the preliminary injunction hearing, whichever occurs first.'"
    ),
    ChecklistItem(
        id=35,
        category=CheckCategory.RELIEF_REQUESTED,
        description="Requests setting of preliminary injunction hearing",
        rule_citation="Fed. R. Civ. P. 65(b)(3)",
        auto_checkable=True,
        pattern=r"preliminary\s+injunction\s+hearing|hearing.*preliminary",
        check_method="check_pi_hearing_request",
        success_criteria="Motion requests expedited hearing on preliminary injunction. Example: 'Plaintiff requests the Court set hearing on preliminary injunction at the earliest available date.' TRO is temporary; PI hearing is required.",
        redundancy_patterns=["schedule.*hearing", "expedited hearing", "set for hearing", "preliminary injunction motion"],
        fail_severity="normal",
        rule_explanation="Rule 65(b)(3) requires court to schedule PI hearing 'at the earliest possible time' after TRO.",
        fix_suggestion="Add: 'Plaintiff respectfully requests that the Court schedule a preliminary injunction hearing at the earliest available date.'"
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
        check_method="check_declaration_exists",
        success_criteria="Document contains a DECLARATION or VERIFICATION section (or attachment). Look for 'DECLARATION OF [NAME]' or 'VERIFICATION' as section header. This sworn statement supports the factual allegations.",
        redundancy_patterns=["I declare under penalty", "AFFIDAVIT", "sworn statement", "I verify"],
        fail_severity="critical",
        rule_explanation="Rule 65(b)(1)(A) requires 'specific facts in an affidavit or a verified complaint' - declaration fulfills this.",
        fix_suggestion="Add a DECLARATION section: 'DECLARATION OF [YOUR NAME]' followed by 'I, [NAME], declare under penalty of perjury under the laws of the United States that the foregoing is true and correct based on my personal knowledge.'"
    ),
    ChecklistItem(
        id=37,
        category=CheckCategory.VERIFICATION,
        description="Contains 28 U.S.C. § 1746 language",
        rule_citation="28 U.S.C. § 1746",
        auto_checkable=True,
        pattern=r"28\s*U\.S\.C\.\s*§?\s*1746|penalty of perjury",
        check_method="check_1746_language",
        success_criteria="Declaration contains statutory language: 'under penalty of perjury' AND 'the foregoing is true and correct' (or substantially similar). This makes unsworn declaration equivalent to notarized affidavit.",
        redundancy_patterns=["subject to penalty", "perjury", "subscribed and sworn", "laws of the United States"],
        fail_severity="critical",
        rule_explanation="28 U.S.C. § 1746 allows unsworn declarations to substitute for affidavits if proper language used.",
        fix_suggestion="Add to your declaration: 'I declare under penalty of perjury under the laws of the United States of America that the foregoing is true and correct.'"
    ),
    ChecklistItem(
        id=38,
        category=CheckCategory.VERIFICATION,
        description="'True and correct' statement included",
        rule_citation="28 U.S.C. § 1746",
        auto_checkable=True,
        pattern=r"true\s+and\s+correct|true\s+and\s+accurate",
        check_method="check_true_correct",
        success_criteria="Declaration contains 'true and correct' or 'true and accurate' statement. Standard language: 'I declare under penalty of perjury that the foregoing is true and correct.'",
        redundancy_patterns=["accurate to the best of my knowledge", "true to my knowledge", "truthful"],
        fail_severity="critical",
        rule_explanation="The 'true and correct' certification is required by 28 U.S.C. § 1746 for valid declarations.",
        fix_suggestion="Add to your declaration: '...that the foregoing is true and correct to the best of my knowledge.'"
    ),
    ChecklistItem(
        id=39,
        category=CheckCategory.VERIFICATION,
        description="States based on personal knowledge",
        rule_citation="28 U.S.C. § 1746",
        auto_checkable=True,
        pattern=r"personal\s+knowledge",
        check_method="check_personal_knowledge",
        success_criteria="Declaration states facts are based on 'personal knowledge'. Example: 'The following facts are based on my personal knowledge.' Hearsay must be identified as such.",
        redundancy_patterns=["I personally observed", "I have firsthand knowledge", "within my knowledge"],
        fail_severity="normal",
        rule_explanation="Declarations must distinguish personal knowledge from information and belief.",
        fix_suggestion="Add to your declaration: 'The facts stated herein are based on my personal knowledge, and if called as a witness, I could and would testify competently thereto.'"
    ),
    ChecklistItem(
        id=40,
        category=CheckCategory.VERIFICATION,
        description="Signed by declarant",
        rule_citation="28 U.S.C. § 1746",
        auto_checkable=True,
        pattern=r"/s/|signature",
        check_method="check_declaration_signed",
        success_criteria="Declaration contains signature line with '/s/' electronic signature followed by declarant's name. Example: '/s/ John Doe'. Declaration must be signed by the person making it.",
        redundancy_patterns=["signed", "subscribed", "executed by"],
        fail_severity="critical",
        rule_explanation="Unsigned declarations are invalid; 28 U.S.C. § 1746 requires signature.",
        fix_suggestion="Select a Case Profile - the signature block will be auto-generated. Or add '/s/ [Your Full Name]' at the end of your declaration."
    ),
    ChecklistItem(
        id=41,
        category=CheckCategory.VERIFICATION,
        description="Includes date of declaration",
        rule_citation="28 U.S.C. § 1746",
        auto_checkable=False,
        success_criteria="Declaration includes execution date. Look for 'Dated: [date]' or 'Executed on [date]' or date in signature block. Date should match or precede filing date.",
        fail_severity="normal",
        rule_explanation="Date establishes when declarant swore to the facts; must not postdate filing."
    ),
    ChecklistItem(
        id=42,
        category=CheckCategory.VERIFICATION,
        description="Includes location (city, state)",
        rule_citation="28 U.S.C. § 1746",
        auto_checkable=False,
        success_criteria="Declaration includes location where executed. Example: 'Executed at Biloxi, Mississippi' or 'Signed in Harrison County, Mississippi.' Shows where declarant physically was.",
        fail_severity="minor",
        rule_explanation="Location establishes jurisdiction and provides additional verification of declarant's identity."
    ),

    # =========================================================================
    # CATEGORY 7: FORMATTING (Items 43-55)
    # =========================================================================
    ChecklistItem(
        id=43,
        category=CheckCategory.FORMATTING,
        description="Font is Times New Roman 12pt or equivalent",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False,
        success_criteria="Document uses Times New Roman, 12 point font (or equivalent professional font like Arial 11pt). Body text must be readable professional font. Comic Sans = FAIL.",
        fail_severity="normal",
        rule_explanation="L.U.Civ.R. 5(c)(1) requires readable font; Times New Roman 12pt is standard."
    ),
    ChecklistItem(
        id=44,
        category=CheckCategory.FORMATTING,
        description="Body text is double-spaced",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False,
        success_criteria="Body paragraphs are double-spaced (approximately 24 points between lines). Single-spaced body text = FAIL. Double-spacing improves readability and allows for annotations.",
        fail_severity="normal",
        rule_explanation="L.U.Civ.R. 5(c)(1) requires double-spacing for most text."
    ),
    ChecklistItem(
        id=45,
        category=CheckCategory.FORMATTING,
        description="Block quotations may be single-spaced",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False,
        success_criteria="Block quotations (quotes > 50 words) may be single-spaced and indented. This is an exception to double-spacing requirement. Not mandatory but acceptable.",
        fail_severity="minor",
        rule_explanation="Single-spacing block quotes is permitted; helps distinguish quoted material."
    ),
    ChecklistItem(
        id=46,
        category=CheckCategory.FORMATTING,
        description="Headings may be single-spaced",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False,
        success_criteria="Section headings (I. PARTIES, II. FACTS, etc.) may be single-spaced. Headings should be clearly distinguished from body text (bold, centered, or both).",
        fail_severity="minor",
        rule_explanation="Single-spacing headings is permitted to distinguish them from body text."
    ),
    ChecklistItem(
        id=47,
        category=CheckCategory.FORMATTING,
        description="Footnotes are 11pt minimum",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False,
        success_criteria="If document contains footnotes, they must be at least 11 point font. Tiny unreadable footnotes = FAIL. Footnotes should be limited in legal documents.",
        fail_severity="minor",
        rule_explanation="Readable footnotes prevent 'hiding' information in small text."
    ),
    ChecklistItem(
        id=48,
        category=CheckCategory.FORMATTING,
        description="Top margin is 1 inch",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False,
        success_criteria="Document has 1 inch (72 points) top margin. Text should not start at very top of page. Approximately thumb-width from top edge.",
        fail_severity="normal",
        rule_explanation="Standard margin allows for court stamps and filing marks."
    ),
    ChecklistItem(
        id=49,
        category=CheckCategory.FORMATTING,
        description="Bottom margin is 1 inch",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False,
        success_criteria="Document has 1 inch bottom margin. Text should not extend to bottom of page. Page numbers may appear in margin area.",
        fail_severity="normal",
        rule_explanation="Consistent margins ensure professional appearance and allow binding."
    ),
    ChecklistItem(
        id=50,
        category=CheckCategory.FORMATTING,
        description="Left margin is 1 inch",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False,
        success_criteria="Document has 1 inch left margin. Some courts allow 1.5 inch for binding. Paragraph numbers should align properly.",
        fail_severity="normal",
        rule_explanation="Left margin allows for binding and hole punching."
    ),
    ChecklistItem(
        id=51,
        category=CheckCategory.FORMATTING,
        description="Right margin is 1 inch",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False,
        success_criteria="Document has 1 inch right margin. Text should not extend to edge of page. Consistent margins throughout.",
        fail_severity="normal",
        rule_explanation="Right margin ensures text doesn't get cut off in printing or copying."
    ),
    ChecklistItem(
        id=52,
        category=CheckCategory.FORMATTING,
        description="Page numbers present",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False,
        success_criteria="All pages are numbered, typically 'Page X of Y' at bottom center or bottom right. First page may or may not be numbered depending on local practice.",
        fail_severity="normal",
        rule_explanation="Page numbers ensure document integrity and make reference easier."
    ),
    ChecklistItem(
        id=53,
        category=CheckCategory.FORMATTING,
        description="Page numbers within margins",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False,
        success_criteria="Page numbers appear within the margin area (typically bottom center or bottom right). Should not interfere with body text.",
        fail_severity="minor",
        rule_explanation="Consistent placement makes multi-page documents easier to navigate."
    ),
    ChecklistItem(
        id=54,
        category=CheckCategory.FORMATTING,
        description="Motion is 4 pages or less",
        rule_citation="L.U.Civ.R. 7(b)(2)(A)",
        auto_checkable=True,
        check_method="check_page_count",
        success_criteria="Motion (not including brief, declaration, or exhibits) is 4 pages or fewer. Count only the motion itself. L.U.Civ.R. limits motion length; legal argument goes in brief.",
        fail_severity="critical",
        rule_explanation="L.U.Civ.R. 7(b)(2)(A) limits motions to 4 pages; supporting brief is separate.",
        fix_suggestion="Your motion is too long. Move legal argument (case citations, legal analysis) to a separate SUPPORTING BRIEF/MEMORANDUM. Keep only facts in the motion. The motion should state WHAT you want and WHY (facts only)."
    ),
    ChecklistItem(
        id=55,
        category=CheckCategory.FORMATTING,
        description="Paper size is 8.5 x 11 inches",
        rule_citation="L.U.Civ.R. 5(c)(1)",
        auto_checkable=False,
        success_criteria="Document uses standard letter size paper (8.5 x 11 inches). A4 or legal size paper = likely FAIL. PDF should be formatted for letter size.",
        fail_severity="normal",
        rule_explanation="U.S. courts require standard letter size for all filings."
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
        check_method="check_signature_block",
        success_criteria="Document ends with signature block containing 'Respectfully submitted' (or similar) followed by signature line. Signature block appears after body text and before certificate of service.",
        redundancy_patterns=["Submitted by", "signed", "Pro Se Plaintiff"],
        fail_severity="critical",
        rule_explanation="Rule 11(a) requires every pleading be signed; signature block is standard format.",
        fix_suggestion="Select a Case Profile from the dropdown - signature block will be auto-generated. Or add: 'Respectfully submitted,' followed by '/s/ [Your Name]' and contact information."
    ),
    ChecklistItem(
        id=57,
        category=CheckCategory.SIGNATURE,
        description="Actual or electronic signature present",
        rule_citation="Fed. R. Civ. P. 11(a)",
        auto_checkable=True,
        pattern=r"/s/\s*\w+",
        check_method="check_electronic_signature",
        success_criteria="Signature line contains '/s/' followed by full name. Example: '/s/ John Doe'. For paper filing, actual ink signature. Electronic signature format: /s/ First Last",
        redundancy_patterns=["electronically signed", "/s/.*[A-Z]", "digital signature"],
        fail_severity="critical",
        rule_explanation="Rule 11(a) signature certifies document to court; unsigned filings may be stricken.",
        fix_suggestion="Select a Case Profile from the dropdown - electronic signature will be auto-generated. Or add: '/s/ [Your Full Legal Name]'"
    ),
    ChecklistItem(
        id=58,
        category=CheckCategory.SIGNATURE,
        description="Full name printed below signature",
        rule_citation="Fed. R. Civ. P. 11(a)",
        auto_checkable=False,
        success_criteria="Signer's full legal name appears printed below signature line. Example: signature '/s/ John Doe' followed by printed 'JOHN DOE'. Name should match caption.",
        fail_severity="normal",
        rule_explanation="Printed name confirms identity of signer and matches party name in caption."
    ),
    ChecklistItem(
        id=59,
        category=CheckCategory.SIGNATURE,
        description="Mailing address included",
        rule_citation="Fed. R. Civ. P. 11(a)",
        auto_checkable=False,
        success_criteria="Signature block includes complete mailing address: street, city, state, ZIP. Example: '929 Division Street, Biloxi, MS 39530'. P.O. Box acceptable if that's mailing address.",
        redundancy_patterns=["Street", "Drive", "Avenue", r"MS \d{5}", r", [A-Z]{2} \d{5}"],
        fail_severity="normal",
        rule_explanation="Rule 11(a) requires address for service of process and court communications."
    ),
    ChecklistItem(
        id=60,
        category=CheckCategory.SIGNATURE,
        description="Physical address if different from mailing",
        rule_citation="L.U.Civ.R. 83.1(c)",
        auto_checkable=False,
        success_criteria="If mailing address is P.O. Box, physical street address should also be provided. Pro se parties must provide physical address where they can receive service.",
        fail_severity="minor",
        rule_explanation="Physical address ensures party can receive personal service if needed."
    ),
    ChecklistItem(
        id=61,
        category=CheckCategory.SIGNATURE,
        description="Phone number included",
        rule_citation="Fed. R. Civ. P. 11(a)",
        auto_checkable=True,
        pattern=r"\(\d{3}\)\s*\d{3}[-.]?\d{4}|\d{3}[-.]?\d{3}[-.]?\d{4}",
        check_method="check_phone_number",
        success_criteria="Signature block includes phone number in format (XXX) XXX-XXXX or XXX-XXX-XXXX. Must be working number where party can be reached.",
        redundancy_patterns=["Phone:", "Tel:", "Telephone:", r"\d{10}"],
        fail_severity="normal",
        rule_explanation="Phone number allows court and parties to contact filer for scheduling and urgent matters.",
        fix_suggestion="Select a Case Profile from the dropdown - phone number will be auto-generated. Or add your phone number in the signature block: '(305) 555-1234'"
    ),
    ChecklistItem(
        id=62,
        category=CheckCategory.SIGNATURE,
        description="Email address included",
        rule_citation="Fed. R. Civ. P. 11(a)",
        auto_checkable=True,
        pattern=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        check_method="check_email_address",
        success_criteria="Signature block includes valid email address. Example: 'yuri@megalopolisms.com'. Email enables electronic communication and service notifications.",
        redundancy_patterns=["Email:", "E-mail:", "@gmail", "@yahoo", "@outlook"],
        fail_severity="normal",
        rule_explanation="Email address required for electronic service and court communications.",
        fix_suggestion="Select a Case Profile from the dropdown - email will be auto-generated. Or add your email in the signature block: 'Email: your.email@example.com'"
    ),
    ChecklistItem(
        id=63,
        category=CheckCategory.SIGNATURE,
        description="'Pro Se Plaintiff' designation included",
        rule_citation="L.U.Civ.R. 83.1",
        auto_checkable=True,
        pattern=r"Pro\s*Se\s*Plaintiff",
        check_method="check_pro_se_designation",
        success_criteria="Signature block identifies party as 'Pro Se Plaintiff' or 'Plaintiff, Pro Se'. This designation appears below name and indicates self-representation.",
        redundancy_patterns=["appearing pro se", "Pro Se Litigant", "Self-Represented"],
        fail_severity="normal",
        rule_explanation="Pro se designation alerts court that party is unrepresented and may need accommodations.",
        fix_suggestion="Select a Case Profile from the dropdown - Pro Se designation will be auto-generated. Or add 'Pro Se Plaintiff' below your signature."
    ),
    ChecklistItem(
        id=64,
        category=CheckCategory.SIGNATURE,
        description="Bar number NOT required for pro se",
        rule_citation="L.U.Civ.R. 83.1",
        auto_checkable=False,
        success_criteria="Pro se filers do NOT need bar number. If bar number appears, verify filer is actually an attorney. Pro se = no bar admission required. This is an informational check.",
        fail_severity="minor",
        rule_explanation="Only attorneys need bar numbers; pro se parties are not admitted to practice."
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
        check_method="check_certificate_service",
        success_criteria="Document contains 'CERTIFICATE OF SERVICE' section at end. This certifies how and when document was served on opposing parties. Required for all filed documents.",
        redundancy_patterns=["I hereby certify", "served.*following", "service was made"],
        fail_severity="critical",
        rule_explanation="Rule 5(d)(1)(B) requires certificate of service to be filed with every document.",
        fix_suggestion="Select a Case Profile from the dropdown - Certificate of Service will be auto-generated with CM/ECF notification language."
    ),
    ChecklistItem(
        id=66,
        category=CheckCategory.CERTIFICATE_SERVICE,
        description="States date of service",
        rule_citation="Fed. R. Civ. P. 5(d)(1)(B)",
        auto_checkable=False,
        success_criteria="Certificate states specific date of service. Example: 'I hereby certify that on November 26, 2025...' or 'Served this 26th day of November, 2025.' Date must be specified.",
        fail_severity="normal",
        rule_explanation="Date of service establishes when opposing parties received the document."
    ),
    ChecklistItem(
        id=67,
        category=CheckCategory.CERTIFICATE_SERVICE,
        description="Date matches actual service date",
        rule_citation="Fed. R. Civ. P. 5(d)(1)(B)",
        auto_checkable=False,
        success_criteria="Service date in certificate matches actual date service was made. Service date should typically match or precede filing date. False certificate = potential sanctions.",
        fail_severity="normal",
        rule_explanation="Accurate service dates are required for calculating response deadlines."
    ),
    ChecklistItem(
        id=68,
        category=CheckCategory.CERTIFICATE_SERVICE,
        description="Lists all parties served",
        rule_citation="Fed. R. Civ. P. 5(a)(1)",
        auto_checkable=False,
        success_criteria="Certificate lists ALL opposing parties who were served. Each defendant (or their counsel if represented) should be named. Missing party = incomplete service.",
        fail_severity="critical",
        rule_explanation="Rule 5(a)(1) requires service on every party; certificate must reflect this."
    ),
    ChecklistItem(
        id=69,
        category=CheckCategory.CERTIFICATE_SERVICE,
        description="Full name of each party served",
        rule_citation="Fed. R. Civ. P. 5(a)(1)",
        auto_checkable=False,
        success_criteria="Each served party's full legal name appears in certificate. Example: 'City of Biloxi' not just 'Biloxi'. If serving counsel, include counsel's name and firm.",
        fail_severity="normal",
        rule_explanation="Full names ensure clarity about who received service."
    ),
    ChecklistItem(
        id=70,
        category=CheckCategory.CERTIFICATE_SERVICE,
        description="Address of each party served",
        rule_citation="Fed. R. Civ. P. 5(b)(2)",
        auto_checkable=False,
        success_criteria="Certificate includes address where each party was served. For mail service: complete mailing address. For email: email address. For CM/ECF: may state 'via CM/ECF system'.",
        fail_severity="normal",
        rule_explanation="Address confirms service was sent to correct location."
    ),
    ChecklistItem(
        id=71,
        category=CheckCategory.CERTIFICATE_SERVICE,
        description="Method of service stated",
        rule_citation="Fed. R. Civ. P. 5(b)(2)",
        auto_checkable=True,
        pattern=r"(mail|email|electronic|hand.deliver|CM/ECF)",
        check_method="check_service_method",
        success_criteria="Certificate states HOW service was made: 'by first-class mail', 'by email', 'by hand delivery', 'via CM/ECF'. Method must be listed for each party.",
        redundancy_patterns=["U.S. mail", "certified mail", "overnight", "in person", "electronic service"],
        fail_severity="normal",
        rule_explanation="Different service methods have different effective dates; must be stated clearly.",
        fix_suggestion="Select a Case Profile from the dropdown - CM/ECF service method will be auto-generated. Or add: 'I served this document via CM/ECF electronic notification' or 'by first-class mail to [addresses].'"
    ),
    ChecklistItem(
        id=72,
        category=CheckCategory.CERTIFICATE_SERVICE,
        description="Signed by person making service",
        rule_citation="Fed. R. Civ. P. 5(d)(1)(B)",
        auto_checkable=False,
        success_criteria="Certificate is signed by person who made service (usually party or counsel). Look for '/s/' signature. Certificate is a sworn statement; must be signed.",
        fail_severity="critical",
        rule_explanation="Unsigned certificate is invalid; signer attests to truthfulness of service claims."
    ),
    ChecklistItem(
        id=73,
        category=CheckCategory.CERTIFICATE_SERVICE,
        description="Pro se: reflects mail or hand delivery (not CM/ECF)",
        rule_citation="L.U.Civ.R. 5(a)(2)",
        auto_checkable=False,
        success_criteria="For pro se filers not registered for CM/ECF: service should be by mail, hand delivery, or email (if agreed). Pro se cannot use CM/ECF unless specifically registered.",
        fail_severity="normal",
        rule_explanation="Pro se parties typically cannot file electronically; service method must match filing method."
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
        check_method="check_date_line",
        success_criteria="Document contains date line, typically near signature block. Example: 'Dated: November 26, 2025' or 'Dated this 26th day of November, 2025.' Date line shows when document was executed.",
        redundancy_patterns=["day of.*202", "this.*day of", r"\d{1,2}/\d{1,2}/\d{4}"],
        fail_severity="normal",
        rule_explanation="Date establishes when party signed/certified the document.",
        fix_suggestion="Select a Case Profile from the dropdown - date line will be auto-generated. Or add: 'Dated: [Month Day, Year]' near your signature block."
    ),
    ChecklistItem(
        id=75,
        category=CheckCategory.DATE_FILING,
        description="Date matches intended filing date",
        rule_citation="Fed. R. Civ. P. 11(a)",
        auto_checkable=False,
        success_criteria="Date on document should match or precede actual filing date. Document dated after filing date = problem. Date can be same day or earlier.",
        fail_severity="normal",
        rule_explanation="Documents cannot be predated; should reflect actual execution date."
    ),
    ChecklistItem(
        id=76,
        category=CheckCategory.DATE_FILING,
        description="Declaration date matches or precedes filing date",
        rule_citation="28 U.S.C. § 1746",
        auto_checkable=False,
        success_criteria="Date on declaration/verification must be same day as or before filing date. Declaration dated AFTER filing = invalid. Declarant must have sworn before filing.",
        fail_severity="critical",
        rule_explanation="Declaration must exist at time of filing; cannot swear to facts after the fact."
    ),
    ChecklistItem(
        id=77,
        category=CheckCategory.DATE_FILING,
        description="Service date matches filing date",
        rule_citation="Fed. R. Civ. P. 5(d)(1)",
        auto_checkable=False,
        success_criteria="Certificate of service date should typically match filing date (for same-day service) or be very close. Filing without service = incomplete.",
        fail_severity="normal",
        rule_explanation="Documents should be served promptly after filing; same-day service is standard."
    ),

    # =========================================================================
    # CATEGORY 11: EXHIBITS AND ATTACHMENTS (Items 78-86)
    # =========================================================================
    ChecklistItem(
        id=78,
        category=CheckCategory.EXHIBITS,
        description="Declaration/affidavit attached",
        rule_citation="Fed. R. Civ. P. 65(b)(1)(A)",
        auto_checkable=False,
        success_criteria="TRO motion includes attached declaration or affidavit supporting factual claims. May be separate exhibit or integrated into motion. MUST be present for TRO.",
        fail_severity="critical",
        rule_explanation="Rule 65(b)(1)(A) requires 'specific facts in an affidavit or verified complaint' - no declaration = automatic denial."
    ),
    ChecklistItem(
        id=79,
        category=CheckCategory.EXHIBITS,
        description="Proposed order attached",
        rule_citation="L.U.Civ.R. 65(a)(2)",
        auto_checkable=True,
        pattern=r"PROPOSED\s+ORDER|ORDER\s+GRANTING",
        check_method="check_proposed_order",
        success_criteria="Motion includes PROPOSED ORDER as attachment. Look for 'PROPOSED ORDER' or '[PROPOSED] ORDER GRANTING TEMPORARY RESTRAINING ORDER'. Judge will modify and sign if granting.",
        redundancy_patterns=["ORDER GRANTING", "ORDER FOR", "IT IS HEREBY ORDERED", "the Court ORDERS"],
        fail_severity="normal",
        rule_explanation="Many courts require proposed orders to expedite relief; saves judge drafting time.",
        fix_suggestion="Create a separate PROPOSED ORDER document stating: 'ORDER GRANTING TEMPORARY RESTRAINING ORDER. IT IS HEREBY ORDERED that Defendant(s) are restrained from [specific actions]...' Include blank signature line for judge."
    ),
    ChecklistItem(
        id=80,
        category=CheckCategory.EXHIBITS,
        description="Exhibits properly labeled (Exhibit A, B, etc.)",
        rule_citation="L.U.Civ.R. 10(c)",
        auto_checkable=True,
        pattern=r"Exhibit\s+[A-Z]|EXHIBIT\s+[A-Z]",
        check_method="check_exhibit_labels",
        success_criteria="Each exhibit is labeled sequentially: 'Exhibit A', 'Exhibit B', etc. Labels should appear on exhibit cover sheets or at top of each exhibit. Referenced in motion body.",
        redundancy_patterns=["Attachment", "Ex.", "Exhibit 1", "Exhibit No."],
        fail_severity="normal",
        rule_explanation="Proper labeling allows court and parties to reference specific exhibits.",
        fix_suggestion="Label your exhibits as 'Exhibit A', 'Exhibit B', etc. Reference them in your motion: 'See Exhibit A (attached hereto).'"
    ),
    ChecklistItem(
        id=81,
        category=CheckCategory.EXHIBITS,
        description="Exhibits have descriptive captions",
        rule_citation="L.U.Civ.R. 10(c)",
        auto_checkable=False,
        success_criteria="Each exhibit has brief description. Example: 'Exhibit A - Contract dated January 1, 2024' or 'Exhibit B - Email from Defendant'. Description helps identify exhibit contents.",
        fail_severity="minor",
        rule_explanation="Descriptions help court quickly identify exhibit contents without reading entire document."
    ),
    ChecklistItem(
        id=82,
        category=CheckCategory.EXHIBITS,
        description="Exhibits attached to motion (not filed separately)",
        rule_citation="L.U.Civ.R. 10(c)",
        auto_checkable=False,
        success_criteria="Exhibits are physically attached to/filed with motion as single filing, not as separate docket entries. All exhibits in one PDF for electronic filing.",
        fail_severity="minor",
        rule_explanation="Attached exhibits ensure complete record; separately filed exhibits may get lost."
    ),
    ChecklistItem(
        id=83,
        category=CheckCategory.EXHIBITS,
        description="Privacy redactions: SSN redacted to last 4 digits",
        rule_citation="Fed. R. Civ. P. 5.2(a)",
        auto_checkable=False,
        success_criteria="Any Social Security numbers appear as 'XXX-XX-1234' (last 4 only). Full SSN in court documents = privacy violation. Check all exhibits for SSNs.",
        fail_severity="critical",
        rule_explanation="Rule 5.2(a) REQUIRES SSN redaction; failure may require document withdrawal and refiling."
    ),
    ChecklistItem(
        id=84,
        category=CheckCategory.EXHIBITS,
        description="Privacy redactions: Financial account numbers redacted",
        rule_citation="Fed. R. Civ. P. 5.2(a)",
        auto_checkable=False,
        success_criteria="Bank account, credit card numbers redacted to last 4 digits. Full account numbers = privacy violation. Check bank statements, financial documents in exhibits.",
        fail_severity="critical",
        rule_explanation="Rule 5.2(a) requires financial account redaction to prevent identity theft."
    ),
    ChecklistItem(
        id=85,
        category=CheckCategory.EXHIBITS,
        description="Privacy redactions: Birth dates show only year",
        rule_citation="Fed. R. Civ. P. 5.2(a)",
        auto_checkable=False,
        success_criteria="Birth dates appear as year only (e.g., 'born 1985') not full date. Full DOB = privacy violation. Check declarations and exhibits.",
        fail_severity="normal",
        rule_explanation="Rule 5.2(a) allows only birth year to protect personal information."
    ),
    ChecklistItem(
        id=86,
        category=CheckCategory.EXHIBITS,
        description="Privacy redactions: Minor names redacted to initials",
        rule_citation="Fed. R. Civ. P. 5.2(a)",
        auto_checkable=False,
        success_criteria="Names of minors (under 18) appear as initials only (e.g., 'J.D.' not 'John Doe'). Full minor names = privacy violation. Check all documents for children's names.",
        fail_severity="critical",
        rule_explanation="Rule 5.2(a) protects minor children's identities in public court records."
    ),

    # =========================================================================
    # CATEGORY 12: PROPOSED ORDER REQUIREMENTS (Items 87-97)
    # =========================================================================
    ChecklistItem(
        id=87,
        category=CheckCategory.PROPOSED_ORDER,
        description="Proposed order states reasons for issuance",
        rule_citation="Fed. R. Civ. P. 65(d)(1)(A)",
        auto_checkable=False,
        success_criteria="Proposed order explains WHY TRO is being granted. Example: 'Based on Plaintiff's showing of irreparable harm from...' Reasons justify the restraint.",
        fail_severity="normal",
        rule_explanation="Rule 65(d)(1)(A) requires order to state reasons; helps appellate review."
    ),
    ChecklistItem(
        id=88,
        category=CheckCategory.PROPOSED_ORDER,
        description="Proposed order states terms specifically",
        rule_citation="Fed. R. Civ. P. 65(d)(1)(B)",
        auto_checkable=False,
        success_criteria="Order states SPECIFIC terms of restraint. Example: 'Defendant shall not enter property at 123 Main St.' Vague terms like 'shall not harass' = insufficient.",
        fail_severity="critical",
        rule_explanation="Rule 65(d)(1)(B) requires 'specific' terms so defendant knows exactly what's prohibited."
    ),
    ChecklistItem(
        id=89,
        category=CheckCategory.PROPOSED_ORDER,
        description="Proposed order describes acts restrained in detail",
        rule_citation="Fed. R. Civ. P. 65(d)(1)(C)",
        auto_checkable=False,
        success_criteria="Order describes prohibited acts 'in reasonable detail'. Each prohibited action clearly specified. Example: 'Defendant is restrained from: (1) demolishing...; (2) selling...; (3) transferring...'",
        fail_severity="critical",
        rule_explanation="Rule 65(d)(1)(C) requires detailed description so defendant understands scope of restraint."
    ),
    ChecklistItem(
        id=90,
        category=CheckCategory.PROPOSED_ORDER,
        description="No incorporation by reference to complaint/motion",
        rule_citation="Fed. R. Civ. P. 65(d)(1)",
        auto_checkable=False,
        success_criteria="Order does NOT say 'as stated in the complaint' or 'per the motion'. Order must stand alone with all terms stated. Incorporation by reference = FAIL.",
        fail_severity="critical",
        rule_explanation="Rule 65(d)(1) prohibits incorporation by reference; order must be self-contained."
    ),
    ChecklistItem(
        id=91,
        category=CheckCategory.PROPOSED_ORDER,
        description="Identifies parties bound by order",
        rule_citation="Fed. R. Civ. P. 65(d)(2)(A)",
        auto_checkable=False,
        success_criteria="Order names each party bound. Example: 'Defendant City of Biloxi is hereby ORDERED...' Named defendants must be specifically listed.",
        redundancy_patterns=["are hereby restrained", "is hereby enjoined", "shall not"],
        fail_severity="critical",
        rule_explanation="Rule 65(d)(2)(A) requires identification of bound parties for enforcement."
    ),
    ChecklistItem(
        id=92,
        category=CheckCategory.PROPOSED_ORDER,
        description="Identifies officers/agents/employees bound",
        rule_citation="Fed. R. Civ. P. 65(d)(2)(B)",
        auto_checkable=False,
        success_criteria="Order includes standard language binding 'officers, agents, servants, employees, and attorneys' of defendant. This extends restraint to people acting for defendant.",
        fail_severity="normal",
        rule_explanation="Rule 65(d)(2)(B) allows binding those who act on defendant's behalf."
    ),
    ChecklistItem(
        id=93,
        category=CheckCategory.PROPOSED_ORDER,
        description="Identifies persons in active concert bound",
        rule_citation="Fed. R. Civ. P. 65(d)(2)(C)",
        auto_checkable=False,
        success_criteria="Order includes 'persons in active concert or participation' with defendant. Standard language: '...and all those acting in active concert or participation with them.'",
        fail_severity="normal",
        rule_explanation="Rule 65(d)(2)(C) binds third parties who knowingly assist in violating the order."
    ),
    ChecklistItem(
        id=94,
        category=CheckCategory.PROPOSED_ORDER,
        description="States duration of TRO (max 14 days)",
        rule_citation="Fed. R. Civ. P. 65(b)(2)",
        auto_checkable=False,
        success_criteria="Order specifies duration: 'This Order shall remain in effect for 14 days' or 'until [date]' or 'until preliminary injunction hearing.' Cannot exceed 14 days.",
        fail_severity="critical",
        rule_explanation="Rule 65(b)(2) limits TROs to 14 days; unlimited duration orders are void."
    ),
    ChecklistItem(
        id=95,
        category=CheckCategory.PROPOSED_ORDER,
        description="States bond amount or waiver",
        rule_citation="Fed. R. Civ. P. 65(c)",
        auto_checkable=False,
        success_criteria="Order addresses bond: 'Plaintiff shall post bond in the amount of $____' OR 'Bond is waived' OR 'Nominal bond of $1 is required.' Must be addressed.",
        fail_severity="normal",
        rule_explanation="Rule 65(c) requires security; order should specify amount or waiver."
    ),
    ChecklistItem(
        id=96,
        category=CheckCategory.PROPOSED_ORDER,
        description="Signature line for judge",
        rule_citation="L.U.Civ.R. 65",
        auto_checkable=False,
        success_criteria="Order has signature line at end for judge. Format: line for signature, then 'UNITED STATES DISTRICT JUDGE' and blank for date. Order is not effective until signed.",
        fail_severity="normal",
        rule_explanation="Judge's signature makes order effective; proposed orders need signature line."
    ),
    ChecklistItem(
        id=97,
        category=CheckCategory.PROPOSED_ORDER,
        description="Word version of proposed order prepared",
        rule_citation="L.U.Civ.R. 65(a)(2)",
        auto_checkable=False,
        success_criteria="Have Word (.docx) version of proposed order ready to email to court if requested. Some courts require editable version for judge to modify. PDF alone may be insufficient.",
        fail_severity="minor",
        rule_explanation="Editable format allows judge to modify order quickly; expedites relief."
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
        check_method="check_urgent_in_title",
        success_criteria="Document title includes 'URGENT' for expedited matters. Example: 'URGENT MOTION FOR TEMPORARY RESTRAINING ORDER'. Alerts clerk to prioritize filing.",
        redundancy_patterns=["EXPEDITED", "EMERGENCY", "TIME-SENSITIVE", "NECESSITOUS"],
        fail_severity="minor",
        rule_explanation="L.U.Civ.R. 7(b)(5) requires 'urgent and necessitous' designation for matters needing immediate attention.",
        fix_suggestion="If this is urgent, add 'URGENT' to your document title: URGENT AND NECESSITOUS MOTION FOR TEMPORARY RESTRAINING ORDER"
    ),
    ChecklistItem(
        id=99,
        category=CheckCategory.URGENT_EMERGENCY,
        description="Deputy clerk contacted re: emergency",
        rule_citation="L.U.Civ.R. 77(c)",
        auto_checkable=False,
        success_criteria="For true emergencies: verify you called deputy clerk to alert them to filing. Document the call (date, time, who you spoke with). After-hours emergencies may require different procedures.",
        fail_severity="minor",
        rule_explanation="Phone notice to clerk ensures emergency filings are processed immediately, not queued."
    ),
    ChecklistItem(
        id=100,
        category=CheckCategory.URGENT_EMERGENCY,
        description="Hearing coordinated with clerk's office",
        rule_citation="L.U.Civ.R. 77(c)",
        auto_checkable=False,
        success_criteria="If seeking hearing: coordinated date/time with clerk before filing. Emergency hearings require advance coordination. Note: Many TROs decided on papers without hearing.",
        fail_severity="minor",
        rule_explanation="Coordinating ensures court has judge available and avoids scheduling conflicts."
    ),
    ChecklistItem(
        id=101,
        category=CheckCategory.URGENT_EMERGENCY,
        description="Notice of hearing prepared (if required)",
        rule_citation="L.U.Civ.R. 7(b)(4)",
        auto_checkable=False,
        success_criteria="If hearing is scheduled: prepare Notice of Hearing with date, time, location, and matter to be heard. Format per local rules. May not be needed if deciding on papers.",
        fail_severity="minor",
        rule_explanation="Notice of hearing ensures all parties know when and where to appear."
    ),
    ChecklistItem(
        id=102,
        category=CheckCategory.URGENT_EMERGENCY,
        description="Notice of hearing filed with motion",
        rule_citation="L.U.Civ.R. 7(b)(4)",
        auto_checkable=False,
        success_criteria="If hearing scheduled: Notice of Hearing filed simultaneously with motion. Both documents should be submitted together. Check local procedures for combined filings.",
        fail_severity="minor",
        rule_explanation="Filing notice ensures hearing is on the record and parties are informed."
    ),
    ChecklistItem(
        id=103,
        category=CheckCategory.URGENT_EMERGENCY,
        description="Notice of hearing served on all parties",
        rule_citation="L.U.Civ.R. 7(b)(4)",
        auto_checkable=False,
        success_criteria="If hearing scheduled: all parties must be served with Notice of Hearing per Rule 5. Include in certificate of service. Even ex parte TROs may require post-issuance notice.",
        fail_severity="minor",
        rule_explanation="All parties must know about hearings; due process requires notice."
    ),

    # =========================================================================
    # CATEGORY 14: PRO SE FILING REQUIREMENTS (Items 104-107)
    # =========================================================================
    ChecklistItem(
        id=104,
        category=CheckCategory.PRO_SE,
        description="Paper original prepared for filing (if not e-filing)",
        rule_citation="L.U.Civ.R. 5(a)(2)",
        auto_checkable=False,
        success_criteria="If filing in person (not CM/ECF): have paper original signed and ready. Pro se litigants may not have CM/ECF access; paper filing is default. Original plus copies needed.",
        fail_severity="normal",
        rule_explanation="Pro se parties often file in paper; need original signed document for clerk."
    ),
    ChecklistItem(
        id=105,
        category=CheckCategory.PRO_SE,
        description="Copies prepared for file-stamping",
        rule_citation="L.U.Civ.R. 5(a)(2)",
        auto_checkable=False,
        success_criteria="Bring copies of all documents for clerk to file-stamp. Typically: original for court + one copy for yourself + copies for each opposing party. Check local requirements for exact number.",
        fail_severity="normal",
        rule_explanation="File-stamped copies are your proof of filing; keep for records."
    ),
    ChecklistItem(
        id=106,
        category=CheckCategory.PRO_SE,
        description="Filing fee paid or IFP granted/pending",
        rule_citation="28 U.S.C. § 1914",
        auto_checkable=False,
        success_criteria="Verify filing fee is handled: (1) pay fee at filing, (2) IFP (In Forma Pauperis) already granted, or (3) IFP application filed simultaneously. Motion filing fee is approximately $402.",
        fail_severity="critical",
        rule_explanation="28 U.S.C. § 1914 requires filing fees; documents may be rejected without payment or IFP."
    ),
    ChecklistItem(
        id=107,
        category=CheckCategory.PRO_SE,
        description="File-stamped copies retained for records",
        rule_citation="L.U.Civ.R. 5(a)(2)",
        auto_checkable=False,
        success_criteria="After filing: retain file-stamped copies showing date/time filed. These prove you filed on time. Keep in secure location with other case documents.",
        fail_severity="minor",
        rule_explanation="File-stamped copies are official proof of filing; important for deadlines and appeals."
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
