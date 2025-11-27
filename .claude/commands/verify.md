---
description: Verify TRO motion compliance with 107-item checklist
---

# TRO Motion Compliance Verification

Verify document: $ARGUMENTS

## Instructions

You are a compliance verification subagent. Your task is to verify a document against the 107-item TRO Motion compliance checklist with REDUNDANCY VERIFICATION.

### Step 1: Parse Arguments
The user has requested to verify: `$ARGUMENTS`

If this is a document name, find it in the documents.json file.
If this is "all in [FILING_NAME]", verify all documents in that filing.

### Step 2: Read Document Data
Read the document storage file:
- Path: `~/Dropbox/Formarter Folder/documents.json`
- Find the document by name (case-insensitive match)
- Extract the `text_content` field AND `custom_title` field (caption info)

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

### Step 4: Run 107-Item Checklist with REDUNDANCY VERIFICATION

For each item, check compliance using PRIMARY pattern AND REDUNDANCY patterns.
A check PASSES if primary OR any redundancy pattern matches (unless it's a negative check like #15).

## VERIFICATION CRITERIA BY ITEM

### CRITICAL ITEMS (Must Pass - Auto Denial if Fail)
These items have `fail_severity: "critical"` - failure likely means motion denial:

| # | Check | Primary Pattern | Redundancy Patterns | Success Looks Like |
|---|-------|-----------------|---------------------|-------------------|
| 1 | Court name | `UNITED STATES DISTRICT COURT` | `U.S. DISTRICT COURT`, `DISTRICT COURT`, `IN THE UNITED STATES` | Header contains full court name in ALL CAPS |
| 2 | Plaintiff | `PLAINTIFF` | `Plaintiff,`, `Plaintiffs,`, `, Plaintiff`, `PRO SE PLAINTIFF` | Caption names plaintiff with designation |
| 3 | Defendant | `DEFENDANT` | `Defendant.`, `Defendants.`, `, Defendant`, `et al., Defendants` | Caption names all defendants |
| 4 | Case number | `\d:\d{2}-cv-\d+` | `Civil Action No.`, `Case No.`, `No. \d+` | Format like `3:24-cv-00178` |
| 5 | Motion title | `MOTION.*TEMPORARY RESTRAINING ORDER\|MOTION.*TRO` | `MOTION FOR.*RESTRAINING`, `TRO MOTION` | Clearly identifies as TRO motion |
| 10 | Movant identified | `(Plaintiff\|Movant).*moves\|hereby\\s+moves` | `Plaintiff moves`, `respectfully moves`, `comes now.*moves` | First paragraph states who is moving |
| 12 | Rule 65 cited | `65\\s*\\(b\\)\|Rule\\s*65` | `Fed. R. Civ. P. 65`, `FRCP 65`, `Rule 65(b)(1)` | Body references Rule 65 |
| 15 | NO case citations | `\d+\\s+(?:F\\.\\d+d?\|U\\.S\\.\|S\\.Ct\\.)\\s+\d+` | `\d+\\s+F\\.Supp`, `See [Name] v.` | **SUCCESS = NO MATCHES** (reverse check) |
| 21 | Irreparable harm | `irreparable\\s+(harm\|injury\|damage)` | `cannot be undone`, `no adequate remedy at law`, `permanent.*harm` | Uses "irreparable harm/injury" phrase |
| 22 | Notice certificate | `CERTIFICATE\\s+OF\\s+NOTICE\|notice\\s+effort` | `efforts to provide notice`, `attempted to notify` | Section describing notice attempts |
| 27 | Bond addressed | `65\\s*\\(c\\)\|security\|bond` | `security bond`, `injunction bond`, `waiver of bond` | Mentions bond requirement |
| 36 | Declaration exists | `DECLARATION\|VERIFICATION\|under penalty of perjury` | `I declare under penalty`, `AFFIDAVIT`, `sworn statement` | Contains declaration/affidavit |
| 37 | 1746 language | `28\\s*U\\.S\\.C\\.\\s*§?\\s*1746\|penalty of perjury` | `subject to penalty`, `perjury`, `subscribed and sworn` | "Under penalty of perjury" language |
| 38 | True and correct | `true\\s+and\\s+correct\|true\\s+and\\s+accurate` | `accurate to the best of my knowledge`, `true to my knowledge` | Certification of truthfulness |
| 54 | Page count | (count ~3000 chars = 1 page) | N/A | Motion body is 4 pages or less |
| 56 | Signature block | `Respectfully\\s+submitted\|/s/` | `Submitted by`, `signed`, `Pro Se Plaintiff` | Ends with signature block |
| 57 | Electronic sig | `/s/\\s*\\w+` | `electronically signed`, `/s/.*[A-Z]` | `/s/ FirstName LastName` format |
| 65 | Cert of Service | `CERTIFICATE\\s+OF\\s+SERVICE` | `I hereby certify`, `served.*following`, `service was made` | Service certificate at end |

### NORMAL ITEMS (Should Pass)
| # | Check | Primary Pattern | Redundancy Patterns |
|---|-------|-----------------|---------------------|
| 6 | Rule 65 in title | `Rule\\s*65\|Fed\\.?\\s*R\\.?\\s*Civ\\.?\\s*P\\.?\\s*65` | `FRCP 65`, `Rule 65(b)`, `pursuant to Rule 65` |
| 11 | Pro se stated | `pro\\s*se` | `self-represented`, `without counsel`, `in pro per` |
| 34 | Duration 14 days | `14\\s*days\|fourteen\\s*days` | `two weeks`, `for a period not exceeding 14`, `until hearing` |
| 35 | PI hearing request | `preliminary\\s+injunction\\s+hearing\|hearing.*preliminary` | `schedule.*hearing`, `expedited hearing`, `set for hearing` |
| 39 | Personal knowledge | `personal\\s+knowledge` | `I personally observed`, `I have firsthand knowledge` |
| 40 | Declaration signed | `/s/\|signature` | `signed`, `subscribed`, `executed by` |
| 61 | Phone number | `\\(\\d{3}\\)\\s*\\d{3}[-.]?\\d{4}` | `Phone:`, `Tel:`, `Telephone:` |
| 62 | Email address | `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}` | `Email:`, `E-mail:`, `@gmail`, `@yahoo` |
| 63 | Pro Se Plaintiff | `Pro\\s*Se\\s*Plaintiff` | `appearing pro se`, `Pro Se Litigant`, `Self-Represented` |
| 71 | Service method | `(mail\|email\|electronic\|hand.deliver\|CM/ECF)` | `U.S. mail`, `certified mail`, `overnight`, `in person` |
| 74 | Date line | `Dated:\|Date:\|dated this` | `day of.*202`, `this.*day of`, `\d{1,2}/\d{1,2}/\d{4}` |
| 79 | Proposed order | `PROPOSED\\s+ORDER\|ORDER\\s+GRANTING` | `ORDER GRANTING`, `ORDER FOR`, `IT IS HEREBY ORDERED` |
| 80 | Exhibit labels | `Exhibit\\s+[A-Z]\|EXHIBIT\\s+[A-Z]` | `Attachment`, `Ex.`, `Exhibit 1`, `Exhibit No.` |

### CONDITIONAL ITEMS (Only if Ex Parte/Urgent)
| # | Check | Pattern | When Required |
|---|-------|---------|---------------|
| 7 | EX PARTE | `EX\\s*PARTE` | Only if filing without notice |
| 8 | URGENT | `URGENT\|NECESSITOUS` | Only if expedited review needed |
| 9 | EMERGENCY | `EMERGENCY` | Only for true emergencies |
| 98 | URGENT in title | `URGENT` | Only if expedited review needed |

### MANUAL REVIEW ITEMS
These require human judgment - mark as `status: "manual"`:
- Items 13-14, 16-20: Content analysis
- Items 23-26, 28-30: Notice certificate details
- Items 31-33: Relief specifics
- Items 41-42, 43-53, 55: Formatting
- Items 58-60, 64: Signature details
- Items 66-70, 72-73, 75-77: Service details
- Items 78, 81-97: Exhibits and proposed order
- Items 99-107: Emergency procedures

### Step 5: REDUNDANCY VERIFICATION PROCESS

For each auto-checkable item:
1. Check PRIMARY pattern
2. If PRIMARY fails, check EACH redundancy pattern
3. Log which patterns matched/failed
4. PASS if primary OR any redundancy matches
5. For item #15 (no citations): FAIL if any pattern matches

Example redundancy log:
```json
{
  "item_id": 21,
  "description": "Irreparable harm stated",
  "primary_pattern": "irreparable\\s+(harm|injury|damage)",
  "primary_match": false,
  "redundancy_checks": [
    {"pattern": "cannot be undone", "match": true, "text": "...damage cannot be undone..."},
    {"pattern": "no adequate remedy at law", "match": false}
  ],
  "final_status": "pass",
  "note": "Passed via redundancy: 'cannot be undone'"
}
```

### Step 6: Calculate Summary
After all items:
- Count passed, failed, warnings, manual
- Calculate score: `(passed / (passed + failed)) * 100`
- Identify CRITICAL issues (items with fail_severity="critical" that failed)

### Step 7: Update Log to Completed
Set `status: "completed"` in the audit log.

### Step 8: Save Full Result
Save to: `~/Dropbox/Formarter Folder/audits/[document_id].json`

### Step 9: Report to User

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
🚨 CRITICAL ISSUES (may cause denial):
• #XX: [Description]
  └─ What's needed: [success_criteria]
  └─ Rule: [rule_citation] - [rule_explanation]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ FAILURES:
• #XX [Category]: [Description]
  └─ Primary: [pattern] - NOT FOUND
  └─ Redundancy: [patterns checked] - NOT FOUND
  └─ What success looks like: [success_criteria]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ WARNINGS:
• #XX [Category]: [Description] - [message]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ PASSED (via redundancy):
• #XX: [Description] - matched "[redundancy_pattern]"

Results saved to: ~/Dropbox/Formarter Folder/audits/
```

## Interaction Support

After reporting, the user may ask follow-up questions:
- "explain item 15" → Read checklist.py, explain what item 15 checks, its success_criteria, redundancy_patterns, and what was found
- "what's the status?" → Read audit_log.json and report current progress
- "show all failures" → List all items with status=fail with their success_criteria
- "how do I fix #21?" → Explain what the rule requires and give example language to add

## Communication Protocol

When reporting back to the main Claude instance:
1. Start with summary stats
2. List ALL critical failures first
3. For each failure, include:
   - Item number and description
   - Primary pattern checked
   - Redundancy patterns checked
   - What success looks like (from success_criteria)
   - The relevant rule explanation
4. Suggest specific fixes where possible

## Batch Verification

If user requested "verify all in [FILING_NAME]":
1. Read documents.json
2. Find the filing by name
3. Get all document_ids in that filing
4. Run verification for each document
5. Aggregate results and report combined summary
6. Identify common issues across documents
