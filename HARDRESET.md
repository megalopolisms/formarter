# FORMARTER - Hard Reset Context Document
## Federal Court Document Formatter for Pro Se Litigants
**Version:** v1.0.0 (Stable)
**Last Updated:** November 26, 2025

---

## PROJECT SUCCESS SUMMARY

This project has been an **outstanding success**. We have built a fully functional PyQt6 desktop application that automates federal court document formatting for pro se litigants. The development has been highly productive with rapid iteration and continuous improvement based on real-world usage.

### Key Achievements:
- **5 fully functional tabs** (Editor, Case Law, Library, Auditor, Quick Print)
- **107-item TRO Motion Compliance Checklist** with ~35 auto-checkable items
- **PDF export** with proper federal court formatting (Times New Roman, 12pt, double-spaced, 1" margins)
- **Filing system** with case profiles, document organization, and tags
- **Quick Print tab** for emergency standalone documents
- **Stable v1.0.0 release** tagged and pushed

---

## APPLICATION ARCHITECTURE

### Main Application: `src/app.py`
- PyQt6-based GUI with tabbed interface
- ~4500 lines of well-organized code
- Case profiles hardcoded for quick access:
  - **178 - Petrini & Maeda v. Biloxi** (dual signature)
  - **233 - Petrini & Maeda v. Biloxi** (dual signature)
  - **193 - Petrini v. USCIS** (single signature)

### Case Profiles (Hardcoded):
```python
PETRINI_MAEDA_SIGNATURE = SignatureBlock(
    attorney_name="Yuri Petrini",
    phone="(305) 504-1323",
    email="yuri@megalopolisms.com",
    attorney_name_2="Sumire Maeda",
    phone_2="(305) 497-9133",
    email_2="sumire@megalopolisms.com",
    address="929 Division Street, Biloxi, MS 39530",
)
```

---

## TAB FUNCTIONALITY

### 1. EDITOR TAB
- Document text editing with paragraph numbering
- Section management (I, II, III with sub-items a, b, c)
- Case profile selector
- Document type selector
- PDF preview and export
- Spacing controls (before/after sections, between paragraphs)

### 2. CASE LAW TAB
- Citation extraction from documents
- Integration with case law library

### 3. LIBRARY TAB
- Case law management
- PDF storage and retrieval
- Category organization

### 4. AUDITOR TAB
- **107-item TRO Motion Compliance Checklist**
- Based on Fed. R. Civ. P. 65 and Local Uniform Civil Rules
- ~35 auto-checkable items with regex patterns
- Options for Ex Parte and Urgent/Emergency motions
- Real-time audit logging to JSON
- Categories: Caption, Motion Content, Certificate of Notice, Security/Bond, Relief, Verification, Formatting, Signature, Certificate of Service, Date, Exhibits, Urgent

### 5. QUICK PRINT TAB (NEW)
- **3 standalone document generators:**
  1. **Signature Block + Certificate of Service** (green button)
  2. **Signature Block Only** (blue button)
  3. **Certificate of Service Only** (orange button)
- Case profile selector for attorney info
- **Optional date checkbox:**
  - Unchecked: Prints blank date line for hand-filling ("___ day of ____________, 2025")
  - Checked: Uses date picker (defaults to today)
- No page numbers on standalone documents
- Opens PDF directly (no dialog box)

---

## PDF EXPORT FEATURES

### `src/pdf_export.py`
- Federal court formatting standards
- Caption generation with court name, parties, case number
- Signature block with dual signature support
- Certificate of Service with ECF language:
  > "I hereby certify that on this date, I filed the foregoing in person with the Clerk of Court, which will send notification of such filing to all counsel of record via the CM/ECF system."
- Blank date format for hand-filling
- Skip page numbers option
- Certificate-only mode

---

## DATA MODELS

### `src/models/document.py`
- `CaseCaption`: Court name, plaintiff, defendant, case number
- `SignatureBlock`: Attorney info, dual signatures, filing date, include_certificate flag
- `CaseProfile`: Pre-configured case with caption and signature
- `Paragraph`: Numbered paragraphs with section IDs
- `Section`: Document sections (I, II, III)
- `SpacingSettings`: Document spacing controls

---

## STORAGE

### Document Storage: `~/Dropbox/Formarter Folder/`
- `documents.json` - All saved documents
- `filings/` - Filing organization
- `audits/` - Audit results and logs

---

## SLASH COMMANDS

### `/verify` Command
Location: `.claude/commands/verify.md`
- Verifies documents against 107-item TRO checklist
- Supports single document or batch verification
- Real-time progress logging

---

## RUNNING THE APP

```bash
cd /Users/yuripetrinim5/formarter
source venv/bin/activate
python3 main.py
```

---

## DEVELOPMENT NOTES

### Always:
- Edit the app/buttons, not just scripts
- Launch app after finishing programming
- Commit and push when done or when requested

### Key Files to Know:
- `src/app.py` - Main application (edit buttons/UI here)
- `src/pdf_export.py` - PDF generation
- `src/models/document.py` - Data models
- `src/auditor/` - Compliance checking module
- `src/storage.py` - Document persistence

### Recent Changes (This Session):
1. Added Auditor tab with 107-item checklist
2. Added audit options (Ex Parte, Urgent checkboxes)
3. Fixed caption checks to use custom_title field
4. Created Quick Print tab with 3 buttons
5. Added optional date picker for signature/certificate
6. Updated certificate language with ECF notification
7. Updated Sumire Maeda phone to (305) 497-9133
8. Tagged v1.0.0 stable release

---

## CONTACT INFO (Hardcoded)

**Yuri Petrini**
- Phone: (305) 504-1323
- Email: yuri@megalopolisms.com

**Sumire Maeda**
- Phone: (305) 497-9133
- Email: sumire@megalopolisms.com

**Address:** 929 Division Street, Biloxi, MS 39530

---

## GIT INFO

- Repository: `megalopolisms/formarter`
- Branch: `main`
- Latest Tag: `v1.0.0`
