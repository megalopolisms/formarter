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
  "categories": [
    {
      "id": "cat-uuid",
      "name": "Civil Rights",
      "color": "#4A90D9"
    },
    {
      "id": "cat-uuid-2",
      "name": "Excessive Force",
      "color": "#D94A4A"
    }
  ],
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
      "notes": "",
      "category_id": "cat-uuid",
      "keywords": ["qualified immunity", "police misconduct", "fourth amendment"]
    }
  ]
}
```

## User Interface

### Tab Layout
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [+ Add Case] [+ Batch Import]     [Search: _________________ 🔍]            │
│ Category: [All ▼]                 Keywords: [________________]              │
├─────────────────────────────────────────────────────────────────────────────┤
│ Case Name          │ Citation       │ Court    │ Year │ Category │ Keywords │
├────────────────────┼────────────────┼──────────┼──────┼──────────┼──────────┤
│ Smith v. Jones     │ 123 F.3d 456   │ 5th Cir. │ 2020 │ Civil... │ qual...  │
│ Brown v. Board     │ 347 U.S. 483   │ SCOTUS   │ 1954 │ Civil... │ equal... │
│ ...                │ ...            │ ...      │ ...  │ ...      │ ...      │
└─────────────────────────────────────────────────────────────────────────────┘
│ Actions: [Open PDF] [View Text] [Copy Citation] [Edit Tags] [Delete]        │
└─────────────────────────────────────────────────────────────────────────────┘
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
│ ─── Organization ───                        │
│ Category:     [Civil Rights ▼] [+ New]      │
│ Keywords:     [qualified immunity, police]  │
│               (comma-separated)             │
│                                             │
│ Preview: Smith v. Jones, 123 F.3d 456       │
│          (5th Cir. 2020)                    │
│                                             │
│        [Cancel]  [Add to Library]           │
└─────────────────────────────────────────────┘
```

### Batch Import Dialog
```
┌─────────────────────────────────────────────────────────────┐
│              Batch Import Cases                             │
├─────────────────────────────────────────────────────────────┤
│ [Select PDFs...]  (12 files selected)                       │
│                                                             │
│ Default Category: [Civil Rights ▼] [+ New]                  │
│                                                             │
│ ─── Import Queue ───                                        │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ✓ Smith v Jones.pdf          → Smith v. Jones, 123...   │ │
│ │ ✓ Brown v Board.pdf          → Brown v. Board, 347...   │ │
│ │ ⚠ Graham v Connor.pdf        → (needs citation info)    │ │
│ │ ✗ duplicate_case.pdf         → Already in library       │ │
│ │ ...                                                     │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ Status: 10 ready, 1 needs info, 1 duplicate                 │
│                                                             │
│ Progress: ████████░░░░░░░░░░░░ 40%                         │
│                                                             │
│      [Cancel]  [Edit Selected]  [Import All Ready]          │
└─────────────────────────────────────────────────────────────┘
```

### Features

#### 1. Add Case
- Click "Add Case" button
- Select PDF file (typically from Westlaw download)
- Auto-extract citation from filename if possible (Westlaw format)
- Manually enter/edit citation fields
- Assign category and keywords for organization
- Preview Bluebook citation before saving
- Copy PDF to library folder with proper name
- Extract text and save as .txt file

#### 2. Batch Import
- Click "Batch Import" button
- Select multiple PDF files at once (Cmd+click or drag-select)
- System automatically:
  - Copies files to library folder
  - Attempts to parse citation from filename
  - Detects duplicates (by citation match) and skips them
  - Shows status for each file (ready, needs info, duplicate)
- Assign default category to all imported cases
- Edit individual cases that need citation info
- Progress bar shows import status
- Import summary shows success/skipped counts

#### 3. Categories
- Predefined categories for organizing cases by legal topic
- Each category has a name and color
- Create new categories on-the-fly with [+ New] button
- Filter table view by category dropdown
- Suggested default categories:
  - Civil Rights (42 U.S.C. § 1983)
  - Excessive Force
  - Qualified Immunity
  - Municipal Liability
  - Due Process
  - Equal Protection
  - First Amendment
  - Fourth Amendment
  - Employment
  - Contract
  - Torts
  - Procedure

#### 4. Keywords/Tags
- Comma-separated keywords for each case
- Used for searching and finding relevant cases
- Helpful for writing new lawsuits (find cases on specific topics)
- Search box filters by keywords in real-time
- Suggested keywords auto-complete from existing keywords
- Examples: "police misconduct", "failure to train", "deliberate indifference"

#### 5. Table View
- Columns: Case Name, Citation, Court, Year, Category, Keywords, Date Added
- Sortable columns (click header to sort)
- Row selection for actions
- Filter by category dropdown
- Filter by keyword search

#### 6. Search (Full-Text)
- Search by case name
- Search by keywords
- Search within extracted text content
- Real-time filtering as you type
- Combined filters (category + keyword + text)

#### 7. Actions (per case)
- **Open PDF**: Open in system PDF viewer (Preview on Mac)
- **View Text**: Show extracted text in a panel/dialog
- **Copy Citation**: Copy Bluebook citation to clipboard
- **Edit Tags**: Modify category and keywords
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
class Category:
    id: str                    # UUID
    name: str                  # "Civil Rights"
    color: str                 # "#4A90D9" (hex color for UI)

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
    category_id: str = ""      # Reference to Category.id
    keywords: list[str] = None # ["qualified immunity", "police misconduct"]
    notes: str = ""            # Optional user notes
```

### CaseLibrary Class Methods
```python
class CaseLibrary:
    def __init__(self, storage_dir: Path)

    # Case management
    def add_case(self, pdf_path: str, case_info: dict) -> LibraryCase
    def batch_import(self, pdf_paths: list[str], default_category_id: str = None) -> BatchImportResult
    def list_all(self) -> list[LibraryCase]
    def get_by_id(self, case_id: str) -> LibraryCase
    def update_case(self, case_id: str, updates: dict) -> LibraryCase
    def delete(self, case_id: str) -> bool
    def is_duplicate(self, citation: str) -> bool

    # Search and filtering
    def search(self, query: str) -> list[LibraryCase]
    def filter_by_category(self, category_id: str) -> list[LibraryCase]
    def filter_by_keyword(self, keyword: str) -> list[LibraryCase]
    def search_full_text(self, query: str) -> list[LibraryCase]

    # Category management
    def add_category(self, name: str, color: str) -> Category
    def list_categories(self) -> list[Category]
    def delete_category(self, category_id: str) -> bool

    # Keywords
    def get_all_keywords(self) -> list[str]  # For autocomplete
    def add_keyword_to_case(self, case_id: str, keyword: str) -> None
    def remove_keyword_from_case(self, case_id: str, keyword: str) -> None

    # File operations
    def get_pdf_path(self, case_id: str) -> Path
    def get_txt_path(self, case_id: str) -> Path
    def extract_text(self, pdf_path: str) -> str

@dataclass
class BatchImportResult:
    successful: list[LibraryCase]
    duplicates: list[str]           # Filenames that were skipped
    needs_info: list[str]           # Filenames that couldn't be parsed
    errors: list[tuple[str, str]]   # (filename, error message)
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
- [ ] Link cases to documents (show which cases are cited in current document)
- [ ] Export library list to CSV/Excel
- [ ] Integration with Case Law tab citation extractor (auto-highlight library cases)
- [ ] Smart keyword suggestions based on case text analysis
- [ ] Related cases feature (find similar cases by keywords/topic)

## User Stories

### Core Features
1. As a user, I want to import a Westlaw PDF so I can store it for future reference
2. As a user, I want to search my case library so I can quickly find relevant cases
3. As a user, I want to copy a properly formatted citation so I can paste it into my document
4. As a user, I want to view the text of a case without opening the PDF
5. As a user, I want my case library synced across devices via Dropbox

### Batch Import
6. As a user, I want to import multiple PDFs at once so I can quickly build my library
7. As a user, I want the system to skip duplicate cases so I don't have redundant entries
8. As a user, I want to see which files need manual citation info so I can fix them

### Categories & Keywords
9. As a user, I want to organize cases by legal topic (category) so I can find related cases
10. As a user, I want to add keywords to cases so I can search by specific legal concepts
11. As a user, I want to filter my library by category when researching a specific area of law
12. As a user, I want keyword autocomplete so I can use consistent terminology
13. As a user, I want to find cases for a new lawsuit by searching keywords like "failure to train"
