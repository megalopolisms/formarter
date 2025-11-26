---
description: Verify TRO motion compliance with 107-item checklist
---

# TRO Motion Compliance Verification

Verify document: $ARGUMENTS

## Instructions

You are a compliance verification subagent. Your task is to verify a document against the 107-item TRO Motion compliance checklist.

### Step 1: Parse Arguments
The user has requested to verify: `$ARGUMENTS`

If this is a document name, find it in the documents.json file.
If this is "all in [FILING_NAME]", verify all documents in that filing.

### Step 2: Read Document Data
Read the document storage file:
- Path: `~/Dropbox/Formarter Folder/documents.json`
- Find the document by name (case-insensitive match)
- Extract the `text_content` field

### Step 3: Initialize Audit Log
Create/update the audit log at:
- Path: `~/Dropbox/Formarter Folder/audits/audit_log.json`

Initialize with:
```json
{
  "session_id": "audit-[TIMESTAMP]",
  "started": "[ISO_TIMESTAMP]",
  "document_id": "[DOC_ID]",
  "document_name": "[DOC_NAME]",
  "status": "in_progress",
  "progress": {"total_items": 107, "items_checked": 0, "percent_complete": 0},
  "summary": {"passed": 0, "failed": 0, "warnings": 0, "manual_review": 0, "score": 0},
  "results": [],
  "critical_issues": [],
  "last_updated": "[ISO_TIMESTAMP]"
}
```

### Step 4: Run 107-Item Checklist

For each item, check compliance and update the log file.

#### Auto-Checkable Items (check these patterns):

**Caption & Title (1-9):**
1. Court name: `UNITED STATES DISTRICT COURT` - PASS if found
2. Plaintiff: `PLAINTIFF` designation - PASS if found
3. Defendant: `DEFENDANT` designation - PASS if found
4. Case number: Pattern `X:XX-cv-XXXXX` - PASS if found
5. Motion title: `MOTION.*TEMPORARY RESTRAINING ORDER` - PASS if found
6. Rule 65 in title (first 20 lines): `Rule 65` or `Fed. R. Civ. P. 65` - PASS if found
7. EX PARTE: `EX PARTE` - WARNING if not found (may not be needed)
8. URGENT: `URGENT|NECESSITOUS` - WARNING if not found
9. EMERGENCY: `EMERGENCY` - WARNING if not found

**Motion Content (10-21):**
10. Movant identified: `moves`, `hereby moves` - PASS if found
11. Pro se stated: `pro se` - PASS if found
12. Rule 65(b) cited: `65(b)` - FAIL if not found (CRITICAL)
15. No case citations: `\d+ F.\d+d? \d+` pattern - FAIL if found (CRITICAL)
21. Irreparable harm: `irreparable harm|injury|damage` - FAIL if not found (CRITICAL)

**Certificate of Notice (22-26):**
22. Certificate included: `CERTIFICATE OF NOTICE` - PASS if found

**Security/Bond (27-30):**
27. Bond addressed: `65(c)`, `bond`, `security` - PASS if found

**Relief (31-35):**
34. Duration: `14 days` - WARNING if not found
35. PI hearing: `preliminary injunction hearing` - WARNING if not found

**Verification (36-42):**
36. Declaration: `DECLARATION|VERIFICATION|penalty of perjury` - PASS if found
37. 1746 language: `28 U.S.C. § 1746|penalty of perjury` - PASS if found
38. True and correct: `true and correct` - PASS if found
39. Personal knowledge: `personal knowledge` - PASS if found
40. Signed: `/s/` - PASS if found

**Formatting (43-55):**
54. Page count: ~3000 chars/page, max 4 pages - WARNING if exceeds (CRITICAL)

**Signature (56-64):**
56. Signature block: `Respectfully submitted|/s/` - PASS if found
57. Electronic sig: `/s/ [name]` - PASS if found
61. Phone: `(\d{3}) \d{3}-\d{4}` pattern - PASS if found
62. Email: `@` pattern - PASS if found
63. Pro Se Plaintiff: `Pro Se Plaintiff` - PASS if found

**Certificate of Service (65-73):**
65. COS included: `CERTIFICATE OF SERVICE` - FAIL if not found (CRITICAL)
71. Service method: `mail|email|electronic|hand` - PASS if found

**Date (74-77):**
74. Date line: `Dated:|Date:` - PASS if found

**Exhibits (78-86):**
79. Proposed order: `PROPOSED ORDER` - WARNING if not found
80. Exhibit labels: `Exhibit [A-Z]` - WARNING if not found

**Urgent (98-103):**
98. URGENT in title: Check first 10 lines - WARNING if not found

#### Manual Review Items
Items 13-14, 16-20, 23-26, 28-30, 31-33, 41-42, 43-53, 55, 58-60, 64, 66-70, 72-77, 78, 81-97, 99-107
Mark these as `status: "manual"` with message "Requires manual review"

### Step 5: Calculate Summary
After all items:
- Count passed, failed, warnings, manual
- Calculate score: `(passed / (passed + failed + warnings)) * 100`
- Identify critical issues (items 12, 15, 21, 54, 65 that failed)

### Step 6: Update Log to Completed
Set `status: "completed"` in the audit log.

### Step 7: Save Full Result
Save to: `~/Dropbox/Formarter Folder/audits/[document_id].json`

### Step 8: Report to User

Format your response like this:

```
📋 COMPLIANCE REPORT: [DOCUMENT_NAME]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Score: XX.X% (XX/XX checkable items)

✅ PASSED: XX
❌ FAILED: XX
⚠️ WARNING: XX
👁️ MANUAL: XX

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL ISSUES:
• #XX: [Issue description]
• #XX: [Issue description]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FAILURES:
• #XX [Category]: [Description] - [Message]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WARNINGS:
• #XX [Category]: [Description] - [Message]

Results saved to: ~/Dropbox/Formarter Folder/audits/
```

## Interaction Support

After reporting, the user may ask follow-up questions:
- "explain item 15" → Read the audit log, explain what item 15 checks and what was found
- "what's the status?" → Read audit_log.json and report current progress
- "show all failures" → List all items with status=fail

## Batch Verification

If user requested "verify all in [FILING_NAME]":
1. Read documents.json
2. Find the filing by name
3. Get all document_ids in that filing
4. Run verification for each document
5. Aggregate results and report combined summary
