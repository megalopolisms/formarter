# How to Create New Documents in the Editor

## Overview

The Formarter Editor uses a **two-part storage system** for documents. Understanding this architecture is critical for documents to appear in the Editor tab.

---

## Storage Architecture

Documents are stored in `/Users/yuripetrinim5/Dropbox/Formarter Folder/documents.json`

This file has THREE main sections:

```json
{
  "documents": [...],    // Document data (content, metadata)
  "tags": {...},         // Tag definitions
  "cases": [...]         // Cases with filings that REFERENCE documents
}
```

### The Two-Part Requirement

For a document to appear in the Editor tree view, it must exist in **BOTH** places:

1. **`documents` array** - Contains the actual document data
2. **`cases[].filings[].document_ids` array** - References the document by ID

If a document is only in `documents[]` but NOT referenced in any filing's `document_ids[]`, **IT WILL NOT APPEAR** in the Editor tree.

---

## Step-by-Step: Creating a New Document

### Step 1: Create Document Entry in `documents` Array

Add a new object to the `documents` array with these fields:

```json
{
  "id": "unique-uuid-here",           // Generate a new UUID
  "name": "Document Display Name",     // Shows in tree view
  "case_id": "178",                    // Case number (string)
  "case_profile_index": 1,            // Index of case profile
  "document_type_index": 3,           // Document type (see below)
  "custom_title": "FULL DOCUMENT TITLE IN CAPS",
  "text_content": "",                 // Document body text
  "created_at": "2025-12-02T00:00:00.000000",
  "updated_at": "2025-12-02T00:00:00.000000",
  "sections": []                      // Optional section structure
}
```

### Step 2: Create or Find a Filing

Documents belong to Filings within Cases. Either:

**Option A: Add to existing filing**
- Find the appropriate filing in `cases[].filings[]`
- Add your document ID to its `document_ids` array

**Option B: Create new filing**
```json
{
  "id": "new-filing-uuid",
  "name": "Filing Display Name",
  "case_id": "case-uuid-from-cases-array",  // NOT the case number!
  "status": "draft",                         // draft, filed, etc.
  "document_ids": ["your-document-uuid"],    // Reference your document here
  "exhibit_files": []
}
```

### Step 3: Link Document to Filing

Add your document's `id` to the filing's `document_ids` array:

```json
"document_ids": ["fda77d7d-c9ed-4b2f-bf7e-2095c23b2ac8"]
```

---

## Important Notes

### Case ID Confusion

There are TWO different "case_id" concepts:

1. **In `documents[]`**: Uses the case NUMBER as string (e.g., `"178"`)
2. **In `filings[]`**: Uses the case UUID from the `cases` array (e.g., `"b0bd8643-a3a0-405d-9599-be74e602762e"`)

### Document Type Index Values

Common `document_type_index` values:
- `0` = Complaint
- `1` = Motion
- `2` = Brief/Memorandum
- `3` = Response
- `4` = Declaration
- `5` = Exhibit

### UUID Generation

Generate UUIDs using Python:
```python
import uuid
print(str(uuid.uuid4()))
```

---

## Common Issues

### Document Not Visible in Editor

**Symptom**: Document exists in `documents[]` but doesn't appear in tree view.

**Cause**: Document ID is not in any filing's `document_ids` array.

**Fix**: Add the document ID to a filing's `document_ids` array.

### "New Document" Button Not Working

This may indicate app issues. Check:
1. App console for errors
2. Whether `documents.json` is valid JSON
3. Whether case structure is complete

---

## Example: Complete Document Addition

### 1. Document entry (add to `documents` array):
```json
{
  "id": "abc12345-1234-5678-9abc-def012345678",
  "name": "Motion to Compel",
  "case_id": "178",
  "case_profile_index": 1,
  "document_type_index": 1,
  "custom_title": "PLAINTIFF'S MOTION TO COMPEL DISCOVERY",
  "text_content": "COMES NOW Plaintiff...",
  "created_at": "2025-12-02T12:00:00.000000",
  "updated_at": "2025-12-02T12:00:00.000000",
  "sections": []
}
```

### 2. Filing entry (add to `cases[0].filings` array):
```json
{
  "id": "xyz98765-9876-5432-1abc-fed987654321",
  "name": "Discovery Motions",
  "case_id": "b0bd8643-a3a0-405d-9599-be74e602762e",
  "status": "draft",
  "document_ids": ["abc12345-1234-5678-9abc-def012345678"],
  "exhibit_files": []
}
```

---

## Executed Filings vs Editor Documents

**Important**: The Executed Filings tab uses a DIFFERENT storage file:
- `executed_filings/index.json`

This is separate from the Editor's `documents.json`. Adding documents to one does not affect the other.

---

## Technical Reference

The tree view is rendered by `src/widgets/filing_tree.py`. Key code:

```python
# Documents only appear if their ID is in filing.document_ids
for doc_id in filing.document_ids:
    doc = self._documents.get(doc_id)
    if doc:
        doc_item = QTreeWidgetItem(filing_item)
        doc_name = doc.get("name", doc_id)
        doc_item.setText(0, f"📄 {doc_name}")
```

This confirms: documents MUST be referenced in `document_ids` to appear.
