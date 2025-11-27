# Auditor Tab Documentation

## Overview

The Auditor Tab is a TRO Motion Compliance Checker that audits legal documents against a 107-item Federal Court checklist based on Fed. R. Civ. P. 65 (TRO/Injunctions).

## Location

- **Tab:** "Auditor" tab in the main application
- **Source Files:**
  - `src/app.py` - UI and display logic
  - `src/auditor/checklist.py` - 107-item checklist with rules and fix suggestions
  - `src/auditor/detector.py` - Pattern matching and audit logic

## Features

### 1. Document Audit
- Select a document from Dropbox/Formarter Folder/drafts/
- Click "Audit Document" to run compliance check
- Results show in three lists: Passed, Failed, Manual Review

### 2. Audit Results Display

**Passed Items (Green):**
- Items that meet compliance requirements
- Shows item number, description, and status message

**Failed Items (Red):**
- Items that don't meet requirements
- Color-coded by severity:
  - **Critical (Dark Red):** Must fix before filing
  - **Warning (Orange):** Should fix
  - **Normal (Red):** Recommended fix
- **Hover over any failed item to see the FIX SUGGESTION in tooltip**

**Manual Review (Yellow):**
- Items that require human judgment
- Cannot be auto-checked by pattern matching

### 3. Fix Suggestions

Each auto-checkable item has a `fix_suggestion` field with specific language to add.

**To see fix suggestions:**
1. Hover over a failed item in the Failed list
2. Tooltip shows: Problem message + "HOW TO FIX" + "What success looks like"

**Or use the `/fix` command:**
```
/fix item 10
/fix all failures
/fix BRIEF CREEL
```

### 4. Case Profile Auto-Pass

When a Case Profile is selected, signature-related items auto-pass:
- #56: Signature block format
- #57: Electronic signature
- #58: Typed name below signature
- #59: Pro Se designation in signature
- #61: Phone number in signature
- #62: Email address in signature
- #63: Pro Se designation after name
- #65: Certificate of Service present
- #67: Dated signature
- #74: Date line present

## Checklist Categories

| Category | Items | Description |
|----------|-------|-------------|
| CAPTION | 1-9 | Case caption formatting |
| MOTION_CONTENT | 10-35 | Motion body requirements |
| DECLARATION | 36-45 | Declaration/verification |
| EXHIBITS | 46-55 | Evidence and exhibits |
| SIGNATURE | 56-67 | Signature block |
| FORMATTING | 68-80 | Document formatting |
| SERVICE | 81-90 | Service requirements |
| LOCAL_RULES | 91-100 | District-specific rules |
| CERTIFICATES | 101-107 | Required certificates |

## ChecklistItem Fields

```python
@dataclass
class ChecklistItem:
    id: int                      # Item number (1-107)
    category: CheckCategory      # Category enum
    description: str             # What the check is for
    rule_citation: str           # Legal rule reference
    auto_checkable: bool         # Can be auto-checked?
    pattern: str                 # Regex pattern to match
    check_method: str            # Method name in detector.py
    success_criteria: str        # What success looks like
    redundancy_patterns: list    # Backup patterns for verification
    fail_severity: str           # "critical", "warning", or "normal"
    rule_explanation: str        # Plain English explanation
    fix_suggestion: str          # How to fix the issue
```

## Common Failures & Fixes

### Item #10: Opening Paragraph Identifies Movant
```
Plaintiff [YOUR NAME], proceeding pro se, hereby moves this Court,
pursuant to Federal Rule of Civil Procedure 65(b), for a Temporary
Restraining Order against Defendant(s) [DEFENDANT NAME(S)].
```

### Item #12: Cites Fed. R. Civ. P. 65(b)
```
...pursuant to Federal Rule of Civil Procedure 65(b)...
```

### Item #21: Irreparable Harm
```
Plaintiff will suffer immediate and irreparable harm if this relief is not
granted because [DESCRIBE HARM]. This harm cannot be compensated by monetary
damages because [EXPLAIN WHY]. Without this Court's intervention, Plaintiff
will [DESCRIBE PERMANENT CONSEQUENCE].
```

### Item #22: Certificate of Notice Efforts
```
CERTIFICATE OF NOTICE EFFORTS

I certify that on [DATE], I made the following efforts to notify Defendant(s)
of this motion:

1. I called [PHONE NUMBER] at [TIME] and [RESULT].
2. I sent email to [EMAIL ADDRESS] at [TIME].
3. I sent notice by [METHOD] to [ADDRESS].

The responses received were: [DESCRIBE OR "No response was received"]

/s/ [YOUR NAME]
```

### Items #36-40: Declaration
```
DECLARATION OF [YOUR NAME]

I, [YOUR NAME], declare under penalty of perjury under the laws of the
United States of America that the following is true and correct:

1. I am the Plaintiff in this action. The facts stated herein are based on
my personal knowledge, and if called as a witness, I could and would testify
competently thereto.

2. [FACT 1]
3. [FACT 2]
[Continue...]

Executed on [DATE] at [CITY], [STATE].

/s/ [YOUR NAME]
[YOUR NAME]
```

### Item #27: Bond/Security
```
Pursuant to Fed. R. Civ. P. 65(c), Plaintiff respectfully requests that the
Court waive the security bond requirement because:

[ ] Plaintiff is proceeding in forma pauperis and is indigent;
[ ] This is a civil rights action involving constitutional protections;
[ ] Defendant is unlikely to suffer any damages from the TRO;
[ ] The public interest supports waiving the bond requirement.

In the alternative, Plaintiff requests that any bond be set at a nominal amount.
```

### Item #34: 14-Day Duration
```
Plaintiff requests that the Temporary Restraining Order remain in effect for
fourteen (14) days, or until the Court holds a hearing on Plaintiff's Motion
for Preliminary Injunction, whichever occurs first.
```

### Item #35: PI Hearing Request
```
Plaintiff respectfully requests that the Court schedule a hearing on
Plaintiff's forthcoming Motion for Preliminary Injunction at the earliest
available date.
```

## Audit Log

All audits are saved to:
```
~/Dropbox/Formarter Folder/audits/audit_log.json
```

Structure:
```json
{
  "document_name": {
    "timestamp": "2024-01-15T10:30:00",
    "results": {
      "1": {"passed": true, "message": "..."},
      "2": {"passed": false, "message": "..."}
    },
    "summary": {
      "total": 35,
      "passed": 28,
      "failed": 7,
      "manual_review": 72
    }
  }
}
```

## Subagent Commands

### `/fix` Command
Location: `.claude/commands/fix.md`

Usage:
- `/fix item 10` - Get fix for specific item
- `/fix all failures` - Get fixes for all failed items
- `/fix [document name]` - Get fixes for document's failures

## Future Improvements

- [ ] Show fix suggestions in dedicated panel (not just tooltips)
- [ ] "Fix All" button to generate complete fix text
- [ ] Export audit report as PDF
- [ ] Track fix progress across sessions
- [ ] District-specific rule variations
