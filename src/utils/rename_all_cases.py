#!/usr/bin/env python3
"""
Rename ALL case library PDF files to consistent Bluebook format.

This script processes both indexed and non-indexed PDFs, parsing citation
info from filenames when possible.

Target Format: Party v. Party, Volume Reporter Page (Year).pdf
"""

import json
import os
import re
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple


# Reporter patterns and normalizations
REPORTER_PATTERNS = [
    (r'F\.?\s*Supp\.?\s*3d', 'F. Supp. 3d'),
    (r'F\.?\s*Supp\.?\s*2d', 'F. Supp. 2d'),
    (r'F\.?\s*Supp\.?', 'F. Supp.'),
    (r'F\.?\s*App\'?x', "F. App'x"),
    (r'F\.?4th', 'F.4th'),
    (r'F\.?3d', 'F.3d'),
    (r'F\.?2d', 'F.2d'),
    (r'F\.(?!\d)', 'F.'),
    (r'U\.?\s*S\.?(?!\s*C)', 'U.S.'),
    (r'S\.?\s*Ct\.?', 'S. Ct.'),
    (r'L\.?\s*Ed\.?\s*2d', 'L. Ed. 2d'),
    (r'L\.?\s*Ed\.?', 'L. Ed.'),
    (r'So\.?\s*3d', 'So. 3d'),
    (r'So\.?\s*2d', 'So. 2d'),
]


def parse_underscore_filename(filename: str) -> Optional[Dict]:
    """
    Parse citation from underscore-formatted filenames.

    Examples:
        Miranda_v_Arizona_384_US_436_1966.pdf
        Moore_v_Texas_581_US_1_2017.pdf
        Johnson_v_Avery_393_US_483_1969.pdf
        Sinclair_v_Hawke_314_F3d_934_8th_Cir_2003.pdf
    """
    name = Path(filename).stem

    # Pattern for: Name_v_Name_Volume_Reporter_Page_Year
    # or: Name_v_Name_Volume_Reporter_Page_Court_Year

    # Try to find v or V separator
    match = re.match(
        r'^([A-Za-z_]+)_[vV]_([A-Za-z_]+)_(\d+)_([A-Za-z]+\d*[A-Za-z]*)_(\d+)(?:_([A-Za-z0-9_]+))?_(\d{4})',
        name
    )

    if match:
        party1 = match.group(1).replace('_', ' ')
        party2 = match.group(2).replace('_', ' ')
        volume = match.group(3)
        reporter = match.group(4)
        page = match.group(5)
        court_or_year = match.group(6)
        year = match.group(7)

        # Determine if group 6 is a court or part of the year
        court = ""
        if court_or_year and not court_or_year.isdigit():
            court = court_or_year.replace('_', ' ')

        # Normalize reporter
        reporter = normalize_reporter(reporter)

        return {
            'case_name': f"{party1} v. {party2}",
            'volume': volume,
            'reporter': reporter,
            'page': page,
            'year': year,
            'court': court
        }

    return None


def parse_citation_from_filename(filename: str) -> Optional[Dict]:
    """
    Try to parse citation info from various filename formats.
    """
    name = Path(filename).stem

    # Try underscore format first
    result = parse_underscore_filename(filename)
    if result:
        return result

    # Try pattern: "Case Name, Volume Reporter Page (Court Year).pdf"
    match = re.match(
        r'^(.+?),?\s+(\d+)\s+([A-Za-z\.\s]+?)\s+(\d+)\s*\(([^)]+)\)',
        name
    )
    if match:
        case_name = match.group(1)
        volume = match.group(2)
        reporter = normalize_reporter(match.group(3).strip())
        page = match.group(4)
        paren_content = match.group(5)

        # Parse parenthetical (could be "Court Year" or just "Year")
        year_match = re.search(r'(\d{4})', paren_content)
        year = year_match.group(1) if year_match else ""
        court = re.sub(r'\d{4}', '', paren_content).strip()

        return {
            'case_name': case_name,
            'volume': volume,
            'reporter': reporter,
            'page': page,
            'year': year,
            'court': court
        }

    # Try pattern: "Volume_Reporter_Page.pdf" (citation-only filenames)
    match = re.match(r'^(\d+)_([A-Za-z\._]+)_(\d+)', name)
    if match:
        return {
            'case_name': '',  # Will need to get from text content
            'volume': match.group(1),
            'reporter': normalize_reporter(match.group(2).replace('_', ' ')),
            'page': match.group(3),
            'year': '',
            'court': ''
        }

    return None


def normalize_reporter(reporter: str) -> str:
    """Normalize reporter to Bluebook format."""
    reporter = reporter.strip()

    for pattern, replacement in REPORTER_PATTERNS:
        if re.match(pattern, reporter, re.IGNORECASE):
            return replacement

    # Try replacing underscores and normalizing
    reporter = reporter.replace('_', ' ').replace('  ', ' ')

    for pattern, replacement in REPORTER_PATTERNS:
        reporter = re.sub(pattern, replacement, reporter, flags=re.IGNORECASE)

    return reporter


def normalize_case_name(case_name: str) -> str:
    """Normalize case name to title case with proper v."""
    if not case_name:
        return ""

    # Clean up embedded citation info
    case_name = re.sub(r'\s+\d+[_\s].*$', '', case_name)
    case_name = re.sub(r'\s+Cite as.*$', '', case_name, flags=re.IGNORECASE)

    # Normalize v separator
    case_name = re.sub(r'\s+[vV]\.?\s+', ' v. ', case_name)

    # Title case party names
    parts = case_name.split(' v. ')
    if len(parts) == 2:
        party1 = title_case_party(parts[0].strip())
        party2 = title_case_party(parts[1].strip())
        return f"{party1} v. {party2}"

    return title_case_party(case_name)


def title_case_party(party: str) -> str:
    """Title case a party name with special handling."""
    lowercase_words = {'of', 'the', 'in', 'at', 'by', 'for', 'on', 'and', 'or', 'a', 'an'}
    uppercase_abbrevs = {'U.S.', 'US', 'USA', 'FBI', 'CIA', 'IRS', 'DOJ', 'SEC', 'FTC'}

    words = party.split()
    result = []

    for i, word in enumerate(words):
        if word.upper() in uppercase_abbrevs or word in uppercase_abbrevs:
            if word.upper() in ('U.S.', 'US'):
                result.append('U.S.')
            else:
                result.append(word.upper())
        elif i == 0:
            result.append(word.capitalize())
        elif word.lower() in lowercase_words:
            result.append(word.lower())
        else:
            result.append(word.capitalize())

    return ' '.join(result)


def sanitize_filename(filename: str) -> str:
    """Remove problematic characters from filename."""
    replacements = {
        '<': '(', '>': ')', ':': '-', '"': "'",
        '/': '-', '\\': '-', '|': '-', '?': '', '*': ''
    }

    for char, replacement in replacements.items():
        filename = filename.replace(char, replacement)

    return re.sub(r'\s+', ' ', filename).strip()


def generate_bluebook_filename(info: Dict) -> Optional[str]:
    """Generate Bluebook filename from citation info."""
    case_name = normalize_case_name(info.get('case_name', ''))
    volume = info.get('volume', '').strip()
    reporter = normalize_reporter(info.get('reporter', ''))
    page = info.get('page', '').strip()
    year = info.get('year', '').strip()
    court = info.get('court', '').strip()

    if not volume or not reporter or not page or not year:
        return None

    if case_name:
        if court and court not in ['U.S.', 'US']:
            filename = f"{case_name}, {volume} {reporter} {page} ({court} {year})"
        else:
            filename = f"{case_name}, {volume} {reporter} {page} ({year})"
    else:
        # No case name - use citation only format
        if court and court not in ['U.S.', 'US']:
            filename = f"{volume} {reporter} {page} ({court} {year})"
        else:
            filename = f"{volume} {reporter} {page} ({year})"

    return sanitize_filename(filename)


def process_non_indexed_files(case_library_path: Path, index_data: Dict, dry_run: bool = True) -> Dict:
    """Process PDFs that aren't in the index."""
    stats = {'processed': 0, 'renamed': 0, 'skipped': 0, 'added_to_index': 0}

    indexed_pdfs = {c['pdf_filename'] for c in index_data.get('cases', [])}

    for pdf_path in case_library_path.glob("*.pdf"):
        if pdf_path.name in indexed_pdfs:
            continue

        stats['processed'] += 1

        # Try to parse citation from filename
        info = parse_citation_from_filename(pdf_path.name)

        if not info:
            print(f"  ⚠️  Could not parse: {pdf_path.name}")
            stats['skipped'] += 1
            continue

        new_filename = generate_bluebook_filename(info)

        if not new_filename:
            print(f"  ⚠️  Incomplete citation data: {pdf_path.name}")
            stats['skipped'] += 1
            continue

        new_filename = f"{new_filename}.pdf"

        if new_filename == pdf_path.name:
            print(f"  ✓  Already correct: {pdf_path.name}")
            continue

        new_path = case_library_path / new_filename

        if dry_run:
            print(f"  📄 Would rename: {pdf_path.name}")
            print(f"      → {new_filename}")
        else:
            if new_path.exists():
                print(f"  ⚠️  Target exists, skipping: {new_filename}")
                stats['skipped'] += 1
                continue

            try:
                shutil.move(str(pdf_path), str(new_path))
                print(f"  ✓  Renamed: {pdf_path.name} → {new_filename}")
                stats['renamed'] += 1

                # Add to index
                import uuid
                from datetime import datetime

                new_case = {
                    'id': str(uuid.uuid4()),
                    'case_name': info.get('case_name', ''),
                    'volume': info.get('volume', ''),
                    'reporter': info.get('reporter', ''),
                    'page': info.get('page', ''),
                    'year': info.get('year', ''),
                    'court': info.get('court', ''),
                    'pdf_filename': new_filename,
                    'txt_filename': new_filename.replace('.pdf', '.txt'),
                    'bluebook_citation': generate_bluebook_filename(info) or '',
                    'date_added': datetime.now().isoformat(),
                    'category_id': '',
                    'keywords': [],
                    'notes': ''
                }
                index_data['cases'].append(new_case)
                stats['added_to_index'] += 1

            except Exception as e:
                print(f"  ❌ Error renaming: {str(e)}")
                stats['skipped'] += 1

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Rename ALL case library files to Bluebook format')
    parser.add_argument('--case-library',
                       default=os.path.expanduser('~/Dropbox/Formarter Folder/case_library/'))
    parser.add_argument('--live', action='store_true', help='Actually rename files')
    parser.add_argument('--quiet', action='store_true')

    args = parser.parse_args()

    case_library_path = Path(args.case_library)
    index_path = case_library_path / 'index.json'

    if not index_path.exists():
        print("Index not found, creating empty index")
        index_data = {'categories': [], 'cases': []}
    else:
        with open(index_path, 'r') as f:
            index_data = json.load(f)

    print(f"\n{'='*80}")
    print(f"{'DRY RUN' if not args.live else 'LIVE MODE'}")
    print(f"{'='*80}\n")

    total_pdfs = len(list(case_library_path.glob("*.pdf")))
    indexed = len(index_data.get('cases', []))
    print(f"Total PDFs: {total_pdfs}")
    print(f"Indexed: {indexed}")
    print(f"Non-indexed: {total_pdfs - indexed}")

    print(f"\n--- Processing non-indexed files ---\n")
    stats = process_non_indexed_files(case_library_path, index_data, dry_run=not args.live)

    print(f"\n--- Summary ---")
    print(f"Processed: {stats['processed']}")
    print(f"Renamed: {stats['renamed']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Added to index: {stats['added_to_index']}")

    # Save updated index
    if args.live and stats['added_to_index'] > 0:
        backup = case_library_path / 'index.json.backup'
        shutil.copy(str(index_path), str(backup))

        with open(index_path, 'w') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Updated index.json")


if __name__ == '__main__':
    main()
