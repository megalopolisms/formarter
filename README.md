# Formarter

Federal Court Document Formatter for Mississippi District Court filings.

## Overview

Formarter is a Python GUI application designed for lawyers who file documents in federal court (Mississippi District). It formats legal documents according to court requirements:

- **Font:** Times New Roman, 12pt
- **Spacing:** Double-spaced
- **Margins:** 1 inch all sides (configurable)
- **Paragraphs:** Numbered (1. 2. 3.) with sub-paragraphs (1.a, 1.b)
- **Page Numbers:** Center bottom
- **Export:** PDF and DOCX

## How It Works

1. **Paste/type text** in the left editor (line-by-line view with line numbers)
2. **Paragraphs auto-detected** from blank lines
3. **Tree view on right** shows paragraph structure
4. **Organize via tree** - add sections, sub-paragraphs, reorder
5. **Export** to court-ready PDF or DOCX

---

## Development Iterations

### Iteration 1: GUI Shell with Mock Data (COMPLETE)

**Goal:** Create a working PyQt6 window with 2 panels that opens maximized, with mock legal document data.

**Status:**
- [x] Project structure created
- [x] requirements.txt (PyQt6)
- [x] main.py entry point
- [x] src/app.py with MainWindow
- [x] Window opens maximized
- [x] Left panel: text editor with mock legal document
- [x] Right panel: tree widget with sections and paragraphs
- [x] Panels resizable via splitter
- [x] Mock data: Sample federal court complaint with PARTIES, JURISDICTION, FACTUAL ALLEGATIONS, PRAYER FOR RELIEF sections

---

### Iteration 2: Line Numbers + Basic Sync (Planned)

- [ ] Line numbers in text editor
- [ ] Auto-detect paragraphs (blank line separator)
- [ ] Display paragraphs in tree
- [ ] Real-time sync between editor and tree

---

### Iteration 3: Tree Interactions (Planned)

- [ ] Click tree item → highlight lines in editor
- [ ] Collapsible paragraphs
- [ ] Preview text when collapsed ("1. The plaintiff...")
- [ ] Filter/search bar in tree

---

### Iteration 4: Sections & Sub-paragraphs (Planned)

- [ ] Add sections via right-click (FACTS, ARGUMENT, etc.)
- [ ] Custom section numbering (Roman, Arabic, none)
- [ ] Make sub-paragraphs via right-click
- [ ] Drag-drop reordering

---

### Iteration 5: Rich Text & Comments (Planned)

- [ ] Bold, Italic, Underline toolbar
- [ ] Inline comments (// and /* */) hidden in export
- [ ] Per-paragraph notes
- [ ] Smart paste (keep B/I, normalize font)

---

### Iteration 6: Export (Planned)

- [ ] Preview dialog
- [ ] PDF export (Times New Roman 12pt, double-spaced, margins)
- [ ] DOCX export
- [ ] Footnotes support
- [ ] Page numbers center-bottom

---

### Iteration 7: Save/Load & Polish (Planned)

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

# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Requirements

- Python 3.9+
- PyQt6

## License

MIT
