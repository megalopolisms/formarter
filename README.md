# Formarter

Federal Court Document Formatter for Mississippi District Court filings.

## Overview

Formarter is a Python GUI application designed for lawyers who file documents in federal court (Mississippi District). It formats legal documents according to court requirements:

- **Font:** Times New Roman, 12pt
- **Spacing:** Double-spaced
- **Margins:** 1 inch all sides (configurable)
- **Paragraphs:** Numbered continuously (1, 2, 3...) through entire document
- **Sections:** Roman numerals (I, II, III...) as organizational headers
- **Sub-items:** Lowercase letters (a, b, c...) for grouping within sections
- **Page Numbers:** Center bottom
- **Export:** PDF and DOCX

## Federal Court Numbering Rules (Per FRCP Rule 10)

```
                         I. PARTIES

1.   Plaintiff John Smith is a resident of Jackson, Mississippi...

2.   Defendant ABC Corporation is a Delaware corporation...

                      II. JURISDICTION

3.   This Court has subject matter jurisdiction...

4.   Venue is proper in this District...

                   III. FACTUAL ALLEGATIONS

     a. Background

5.   On or about January 15, 2024...

6.   The contract provided that...

     b. Breach

7.   Defendant failed to deliver...
```

**Key Rules:**
- **Paragraph numbers (1, 2, 3...)** are CONTINUOUS through the entire document
- **Section headers (I, II, III...)** organize content but DON'T restart paragraph numbering
- **Sub-items (a, b, c...)** group related paragraphs within a section

## How It Works

1. **Paste/type text** in the left editor (paragraph numbers shown)
2. **Paragraphs auto-detected** from blank lines
3. **Tree view on right** shows section/sub-item structure
4. **Organize via tree** - add sections, sub-items, reorder
5. **Export** to court-ready PDF or DOCX

---

## Development Iterations

### Iteration 1: GUI Shell with Mock Data (COMPLETE)

**Goal:** Create a working PyQt6 window with 2 panels that opens maximized.

**Status:** COMPLETE
- [x] Project structure created
- [x] requirements.txt (PyQt6)
- [x] main.py entry point
- [x] src/app.py with MainWindow
- [x] Window opens maximized
- [x] Left panel: text editor
- [x] Right panel: tree widget
- [x] Panels resizable via splitter

---

### Iteration 2: 100 Paragraphs + Correct Data Model (COMPLETE)

**Goal:** Implement correct federal court numbering with 100 mock paragraphs.

**Status:** COMPLETE
- [x] Data model: Document, Section, SubItem, Paragraph classes
- [x] 100 mock paragraphs numbered 1-100 continuously
- [x] 5 sections: PARTIES, JURISDICTION, FACTUAL ALLEGATIONS, CAUSES OF ACTION, PRAYER FOR RELIEF
- [x] Sub-items in sections III and IV (a, b, c, d groupings)
- [x] Tree displays hierarchy: Section > Sub-item > Paragraphs
- [x] Paragraph numbers always continuous (never restart)
- [x] Times New Roman 12pt font in editor

**Document Structure:**
```
├─ I. PARTIES (paras 1-8)
├─ II. JURISDICTION AND VENUE (paras 9-14)
├─ III. FACTUAL ALLEGATIONS (paras 15-75)
│  ├─ a. Background (15-25)
│  ├─ b. The Contract (26-40)
│  ├─ c. Defendant's Breach (41-55)
│  └─ d. Damages Suffered (56-75)
├─ IV. CAUSES OF ACTION (paras 76-92)
│  ├─ a. Breach of Contract (76-82)
│  ├─ b. Fraud (83-88)
│  └─ c. Negligent Misrepresentation (89-92)
└─ V. PRAYER FOR RELIEF (paras 93-100)
```

---

### Iteration 3: Live Paragraph Detection (COMPLETE)

**Goal:** Remove mock data, real-time paragraph creation from user input.

**Status:** COMPLETE
- [x] App starts with empty document (no mock data)
- [x] User types in left editor
- [x] Blank line (Enter twice) creates new paragraph
- [x] Paragraphs auto-numbered 1, 2, 3... in real-time
- [x] Tree shows paragraph numbers: "1. [preview text]"
- [x] Numbers update as user adds/removes text
- [x] No sections by default (user creates later)

---

### Iteration 4: Tree Interactions & Sections (COMPLETE)

**Goal:** Click-to-highlight, sections via right-click menu.

**Status:** COMPLETE
- [x] Click tree item → highlight paragraph in editor
- [x] Click tree item → scroll to and select paragraph text
- [x] Create sections via right-click (Roman numerals I, II, III...)
- [x] Assign paragraphs to existing sections
- [x] Remove/rename sections via context menu
- [x] Sections display as parent nodes with paragraphs as children

---

### Iteration 4.5: Page Tree (COMPLETE)

**Goal:** Add third panel showing paragraphs grouped by calculated page number.

**Status:** COMPLETE
- [x] Three-panel layout: Editor | Section Tree | Page Tree
- [x] Auto-calculate page breaks based on federal court formatting
- [x] 25 lines per page, 65 characters per line, double-spaced
- [x] Page Tree shows "Page 1", "Page 2", etc. with paragraphs as children
- [x] Click paragraph in Page Tree → highlight in editor
- [x] Color-coded panel headers (green, blue, red)

---

### Iteration 5: Sub-items & Drag-Drop (Planned)

- [ ] Add sub-items via right-click (a. b. c.)
- [ ] Drag-drop reordering of paragraphs
- [ ] Auto-renumber paragraphs after reorder
- [ ] Filter/search bar in tree

---

### Iteration 6: Rich Text & Comments (Planned)

- [ ] Bold, Italic, Underline toolbar
- [ ] Inline comments (// and /* */) hidden in export
- [ ] Per-paragraph notes
- [ ] Smart paste (keep B/I, normalize font)

---

### Iteration 7: Export (Planned)

- [ ] Preview dialog
- [ ] PDF export (Times New Roman 12pt, double-spaced, margins)
- [ ] DOCX export
- [ ] Footnotes support
- [ ] Page numbers center-bottom

---

### Iteration 8: Save/Load & Polish (Planned)

- [ ] Save project as JSON
- [ ] Load project from JSON
- [ ] Recent files list
- [ ] Settings panel (margins, spacing)

---

## Installation

```bash
# Clone the repository
git clone https://github.com/megalopolisms/formarter.git
cd formarter

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Requirements

- Python 3.9+
- PyQt6

## Project Structure

```
formarter/
├── main.py                 # Entry point
├── requirements.txt        # Dependencies
├── README.md              # This file
└── src/
    ├── __init__.py
    ├── app.py             # Main window
    ├── mock_data.py       # 100 mock paragraphs generator
    └── models/
        ├── __init__.py
        └── document.py    # Document, Section, SubItem, Paragraph
```

## License

MIT
