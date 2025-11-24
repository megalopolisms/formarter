# Case Library Tab - Feature Specification

## Overview
A new tab in Formarter to store, organize, and access case law PDFs (primarily from Westlaw). The library provides a centralized repository for legal research materials with full-text search capabilities.

## Goals
1. **Centralized Storage**: Store all case law PDFs in one organized location synced via Dropbox
2. **Easy Access**: Quick retrieval of cases with search functionality
3. **Proper Citation**: Maintain Bluebook-formatted citations for each case
4. **Text Extraction**: Extract and store plain text for searching and reference
5. **Cross-Device Sync**: Files stored in Dropbox for access from any device

## Storage Location
```
~/Dropbox/Formarter Folder/case_library/
├── index.json                              # Metadata index for all cases
├── Smith v Jones 123 F3d 456.pdf          # PDF files (readable names)
├── Smith v Jones 123 F3d 456.txt          # Extracted text files
└── ...
```

## File Naming Convention
- **Format**: `{Case Name} {Volume} {Reporter} {Page}.pdf`
- **Example**: `Smith v Jones 123 F3d 456.pdf`
- **Sanitization**: Remove/replace unsafe filesystem characters: `< > : " / \ | ? *`
- **Readable**: Human-readable names that can be browsed in Finder/Explorer

## Metadata Storage (index.json)
```json
{
  "cases": [
    {
      "id": "uuid-string",
      "case_name": "Smith v. Jones",
      "volume": "123",
      "reporter": "F.3d",
      "page": "456",
      "year": "2020",
      "court": "5th Cir.",
      "pdf_filename": "Smith v Jones 123 F3d 456.pdf",
      "txt_filename": "Smith v Jones 123 F3d 456.txt",
      "bluebook_citation": "Smith v. Jones, 123 F.3d 456 (5th Cir. 2020)",
      "date_added": "2025-11-24T12:00:00",
      "notes": ""
    }
  ]
}
```

## User Interface

### Tab Layout
```
┌─────────────────────────────────────────────────────────────────┐
│ [+ Add Case]                    [Search: _________________ 🔍]  │
├─────────────────────────────────────────────────────────────────┤
│ Case Name          │ Citation              │ Court    │ Year   │
├────────────────────┼───────────────────────┼──────────┼────────┤
│ Smith v. Jones     │ 123 F.3d 456          │ 5th Cir. │ 2020   │
│ Brown v. Board     │ 347 U.S. 483          │ SCOTUS   │ 1954   │
│ ...                │ ...                   │ ...      │ ...    │
└─────────────────────────────────────────────────────────────────┘
│ Actions: [Open PDF] [View Text] [Copy Citation] [Delete]        │
└─────────────────────────────────────────────────────────────────┘
```

### Add Case Dialog
```
┌─────────────────────────────────────────────┐
│           Add Case to Library               │
├─────────────────────────────────────────────┤
│ PDF File: [Browse...]  selected_file.pdf    │
│                                             │
│ ─── Citation Information ───                │
│ Case Name:    [Smith v. Jones            ]  │
│ Volume:       [123  ]                       │
│ Reporter:     [F.3d ▼]  (dropdown)          │
│ Page:         [456  ]                       │
│ Year:         [2020 ]                       │
│ Court:        [5th Cir. ▼]  (dropdown)      │
│                                             │
│ Preview: Smith v. Jones, 123 F.3d 456       │
│          (5th Cir. 2020)                    │
│                                             │
│        [Cancel]  [Add to Library]           │
└─────────────────────────────────────────────┘
```

### Features

#### 1. Add Case
- Click "Add Case" button
- Select PDF file (typically from Westlaw download)
- Auto-extract citation from filename if possible (Westlaw format)
- Manually enter/edit citation fields
- Preview Bluebook citation before saving
- Copy PDF to library folder with proper name
- Extract text and save as .txt file

#### 2. Table View
- Columns: Case Name, Citation, Court, Year, Date Added
- Sortable columns (click header to sort)
- Row selection for actions

#### 3. Search (Full-Text)
- Search by case name
- Search within extracted text content
- Real-time filtering as you type

#### 4. Actions (per case)
- **Open PDF**: Open in system PDF viewer (Preview on Mac)
- **View Text**: Show extracted text in a panel/dialog
- **Copy Citation**: Copy Bluebook citation to clipboard
- **Delete**: Remove case from library (with confirmation)

## Technical Implementation

### New Files
1. `src/case_library.py` - CaseLibrary storage manager class
2. `src/models/library_case.py` - LibraryCase dataclass

### Dependencies
- `pymupdf` (fitz) - PDF text extraction (fast, reliable for legal docs)

### Data Model (LibraryCase)
```python
@dataclass
class LibraryCase:
    id: str                    # UUID
    case_name: str             # "Smith v. Jones"
    volume: str                # "123"
    reporter: str              # "F.3d"
    page: str                  # "456"
    year: str                  # "2020"
    court: str                 # "5th Cir."
    pdf_filename: str          # "Smith v Jones 123 F3d 456.pdf"
    txt_filename: str          # "Smith v Jones 123 F3d 456.txt"
    bluebook_citation: str     # Full formatted citation
    date_added: str            # ISO timestamp
    notes: str = ""            # Optional user notes
```

### CaseLibrary Class Methods
```python
class CaseLibrary:
    def __init__(self, storage_dir: Path)
    def add_case(self, pdf_path: str, case_info: dict) -> LibraryCase
    def list_all(self) -> list[LibraryCase]
    def get_by_id(self, case_id: str) -> LibraryCase
    def delete(self, case_id: str) -> bool
    def search(self, query: str) -> list[LibraryCase]
    def get_pdf_path(self, case_id: str) -> Path
    def get_txt_path(self, case_id: str) -> Path
    def extract_text(self, pdf_path: str) -> str
```

### Reporter Dropdown Options
Common legal reporters for the dropdown:
- Federal: F.4th, F.3d, F.2d, F., F. Supp. 3d, F. Supp. 2d
- Supreme Court: U.S., S. Ct., L. Ed. 2d
- State (Southern): So. 3d, So. 2d, Miss.
- Other regional: N.E.3d, N.W.2d, P.3d, S.E.2d, S.W.3d, A.3d

### Court Dropdown Options
- Federal Circuit Courts: 1st Cir., 2d Cir., 3d Cir., 4th Cir., 5th Cir., etc.
- Supreme Court: (leave blank for U.S. reporter)
- District Courts: S.D. Miss., N.D. Miss., etc.
- State Courts: Miss., Miss. Ct. App., etc.

## Future Enhancements (Not in v1)
- [ ] Drag-and-drop PDF import
- [ ] Batch import multiple PDFs
- [ ] Categories/tags for organizing cases
- [ ] Link cases to documents (show which cases are cited)
- [ ] Auto-detect duplicate cases
- [ ] Export library list
- [ ] Integration with Case Law tab citation extractor

## User Stories
1. As a user, I want to import a Westlaw PDF so I can store it for future reference
2. As a user, I want to search my case library so I can quickly find relevant cases
3. As a user, I want to copy a properly formatted citation so I can paste it into my document
4. As a user, I want to view the text of a case without opening the PDF
5. As a user, I want my case library synced across devices via Dropbox
