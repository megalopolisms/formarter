---
description: Get detailed fix instructions for failed audit items
---

# TRO Motion Fix Assistant

Fix document issues: $ARGUMENTS

## Instructions

You are a TRO motion compliance fix assistant. Your task is to provide detailed, actionable fix instructions for failed audit items.

### Step 1: Parse Arguments

The user has requested help with: `$ARGUMENTS`

This could be:
- A specific item number (e.g., "item 15" or "#15")
- "all failures" to show fixes for all failed items
- A document name to analyze

### Step 2: Read Checklist Data

Read the checklist file to get fix suggestions:
- Path: `~/formarter/src/auditor/checklist.py`
- Each `ChecklistItem` has:
  - `id`: Item number
  - `description`: What the check is for
  - `rule_citation`: The legal rule
  - `success_criteria`: What success looks like
  - `fix_suggestion`: How to fix the issue
  - `rule_explanation`: Plain English explanation

### Step 3: Read Audit Results (if document specified)

If a document was specified:
- Read: `~/Dropbox/Formarter Folder/audits/audit_log.json`
- Find the document's audit results
- Identify all failed items

### Step 4: Provide Fix Instructions

For each item that needs fixing, provide:

```
## Item #XX: [Description]

**Status:** FAIL / WARNING / CRITICAL

**Rule:** [rule_citation]

**Problem:** [What the audit found]

**Fix:** [fix_suggestion from checklist]

**Example Language to Add:**
```
[Provide specific text/language the user can copy-paste into their document]
```

**Where to Add:** [Specify section of document - opening paragraph, body, declaration, etc.]

**Why This Matters:** [rule_explanation - plain English]
```

### Fix Templates by Category

When providing fixes, use these templates:

#### For Opening Paragraph (Items 10-12):
```
Plaintiff [NAME], proceeding pro se, hereby moves this Court, pursuant to
Federal Rule of Civil Procedure 65(b), for a Temporary Restraining Order
against Defendant(s) [NAME(S)].
```

#### For Irreparable Harm (Item 21):
```
Plaintiff will suffer immediate and irreparable harm if this relief is not
granted because [DESCRIBE HARM]. This harm cannot be compensated by monetary
damages because [EXPLAIN WHY]. Without this Court's intervention, Plaintiff
will [DESCRIBE PERMANENT CONSEQUENCE].
```

#### For Declaration (Items 36-40):
```
DECLARATION OF [YOUR NAME]

I, [YOUR NAME], declare under penalty of perjury under the laws of the
United States of America that the following is true and correct:

1. I am the Plaintiff in this action. The facts stated herein are based on
my personal knowledge, and if called as a witness, I could and would testify
competently thereto.

2. [FACT 1]

3. [FACT 2]

[Continue with numbered facts]

Executed on [DATE] at [CITY], [STATE].

/s/ [YOUR NAME]
[YOUR NAME]
```

#### For Certificate of Notice (Item 22):
```
CERTIFICATE OF NOTICE EFFORTS

I certify that on [DATE], I made the following efforts to notify Defendant(s)
of this motion:

1. I called [PHONE NUMBER] at [TIME] and [RESULT - e.g., left voicemail /
   spoke with / no answer].

2. I sent email to [EMAIL ADDRESS] at [TIME].

3. I sent notice by [certified mail/FedEx/etc.] to [ADDRESS].

The responses received were: [DESCRIBE OR STATE "No response was received"]

/s/ [YOUR NAME]
```

#### For Bond/Security (Item 27):
```
Pursuant to Fed. R. Civ. P. 65(c), Plaintiff respectfully requests that the
Court waive the security bond requirement because:

[ ] Plaintiff is proceeding in forma pauperis and is indigent;
[ ] This is a civil rights action involving constitutional protections;
[ ] Defendant is unlikely to suffer any damages from the temporary restraining order;
[ ] The public interest supports waiving the bond requirement.

In the alternative, Plaintiff requests that any bond be set at a nominal amount.
```

#### For 14-Day Duration (Item 34):
```
Plaintiff requests that the Temporary Restraining Order remain in effect for
fourteen (14) days, or until the Court holds a hearing on Plaintiff's Motion
for Preliminary Injunction, whichever occurs first.
```

#### For PI Hearing Request (Item 35):
```
Plaintiff respectfully requests that the Court schedule a hearing on
Plaintiff's forthcoming Motion for Preliminary Injunction at the earliest
available date.
```

### Step 5: Report to User

Format your response as:

```
# FIX INSTRUCTIONS FOR [DOCUMENT/ITEM]

## Summary
- Total items to fix: X
- Critical items: X
- Quick wins: X (items that can be fixed by selecting Case Profile)

## Quick Fixes (Select Case Profile)
These items will be auto-fixed when you select a Case Profile in the app:
- #56: Signature block
- #57: Electronic signature
- #61: Phone number
- #62: Email address
- #63: Pro Se designation
- #65: Certificate of Service
- #74: Date line

## Fixes Requiring Text Changes

[For each item, provide detailed fix as shown above]

## Copy-Paste Template

Here's everything you need to add to your document:

---
[Provide complete text that addresses all failures]
---
```

### Interaction Support

After providing fixes, be ready for follow-up questions:
- "what about item X?" → Provide detailed fix for that item
- "show me an example" → Provide example language
- "where does this go?" → Explain document structure
- "what's the rule?" → Explain the legal requirement
