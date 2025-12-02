# Document Formatting Guide for Formarter

## Overview

This guide explains how document formatting works in Formarter, specifically:
- How the **Executed Filings** tab displays content
- How **PDF Export** generates formatted output
- Best practices for creating documents

---

## CRITICAL: Editor Tab vs Executed Filings Tab

**These tabs are RELATED but NOT CONNECTED systems!**

### Editor Tab (Draft Documents)
- **Purpose**: Draft and edit legal documents before filing
- **Storage**: `documents.json`
- **Content**: Body text ONLY (no caption, no signature)
- **State**: Editable drafts
- **PDF Export**: Auto-generates caption/title/signature from templates

### Executed Filings Tab (Court-Submitted Documents)
- **Purpose**: Archive of documents ACTUALLY FILED with court
- **Storage**: `executed_filings/index.json` + `*.txt` files
- **Content**: Complete documents (caption + body + signature)
- **State**: Read-only archive
- **When populated**: AFTER document has been submitted to court

### Document Lifecycle
```
1. CREATE    → Editor tab (draft)
2. DRAFT     → Edit in Editor, preview PDF
3. EXPORT    → Generate PDF for court filing
4. FILE      → Submit to court (outside app)
5. ARCHIVE   → "Mark as Filed" links Editor doc to Executed Filings
               - Document becomes read-only in both tabs
               - Generates .txt + .pdf in executed_filings/
```

### Why They're Separate
- **Editor**: Working area - you want to edit freely without affecting filed records
- **Executed Filings**: Legal record - filed documents must not be modified
- **Linking**: "Mark as Filed" creates the bridge when a draft becomes official

---

## Critical Rule: NO Markdown in Text Files

**The Executed Filings tab uses `setPlainText()` which does NOT render markdown.**

This means:
- `**bold**` displays as literal `**bold**` (with asterisks visible)
- `_italic_` displays as literal `_italic_`
- `# Headers` display as literal `# Headers`

### Correct Format (Plain Text)
```
I. INTRODUCTION

Defendants seek a "protective order" under Federal Rule...

II. STATEMENT OF RELEVANT FACTS

A. Procedural Posture: No Discovery Has Occurred
```

### Wrong Format (Markdown - Don't Use)
```
**I. INTRODUCTION**

Defendants seek a "protective order" under Federal Rule...

**II. STATEMENT OF RELEVANT FACTS**

**A. Procedural Posture: No Discovery Has Occurred**
```

---

## How PDF Export Works

PDF export uses **ReportLab** with structured data, NOT raw text files.

### Auto-Bolded Elements

The PDF generator automatically bolds:

1. **Document Title** (`pdf_export.py:329`):
   ```python
   elements.append(Paragraph(f"<b>{document_title}</b>", title_style))
   ```

2. **Section Headers** (`pdf_export.py:676`):
   ```python
   section_text = f"<b>{section.id}. {section.title}</b>"
   ```

3. **Subsection Headers** (`pdf_export.py:694`):
   ```python
   subsection_text = f"<b>{upper_letter}. {subsection.title}</b>"
   ```

### What This Means

- Don't add bold markers to text files - they won't appear in PDF
- PDF uses structured `Section` objects, not raw text parsing
- Title comes from `document_title` parameter, not from file content

---

## Code Reference

### Executed Filings Tab Display
**File**: `/Users/yuripetrinim5/formarter/src/app.py`
**Line**: 5068

```python
self.filing_content.setPlainText(content)
```

This Qt method displays raw text with no formatting.

### Editor Tab Display
**File**: `/Users/yuripetrinim5/formarter/src/app.py`
**Line**: 6772

```python
self.text_editor.setPlainText(doc.text_content)
```

Also uses `setPlainText()` - no markdown rendering.

---

## Storage Architecture

### Executed Filings
```
/Users/yuripetrinim5/Dropbox/Formarter Folder/
├── executed_filings/
│   ├── index.json              # Filing metadata
│   ├── 178 Response to...txt   # Document text (plain text)
│   └── PSJ-01/                 # Subfolder for related docs
│       └── 178 PSJ-01...txt
└── documents.json              # Editor documents
```

### Editor Documents (Two-Part Storage)
For documents to appear in Editor tree view, they must exist in BOTH:
1. `documents[]` array (document data with `text_content`)
2. `cases[].filings[].document_ids[]` (references for tree view)

See: `EDITOR_DOCUMENT_CREATION.md` for details.

---

## Best Practices

1. **Keep text files clean** - use ALL CAPS for section headers, no markdown
2. **Follow existing patterns** - look at working files like PSJ-03 Motion
3. **Use structured Editor** for PDF - don't rely on text file formatting
4. **Test in app** - always verify how content displays before finalizing

---

## Qt Text Display Methods

| Method | Renders Formatting? | Used In Formarter |
|--------|--------------------|--------------------|
| `setPlainText()` | NO | Yes - everywhere |
| `setMarkdown()` | YES | Not used |
| `setHtml()` | YES | Not used |

---

## Future Enhancement

To add markdown support, would need to change display methods in `app.py`:

```python
# Current (no formatting):
self.filing_content.setPlainText(content)

# To enable markdown:
self.filing_content.setMarkdown(content)
```

This would require QTextEdit widget with markdown support enabled.
