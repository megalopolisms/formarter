#!/usr/bin/env python3
"""
Rename case library PDF files to consistent Bluebook format.

This script reads the index.json file, generates proper Bluebook filenames
for each case, and renames the PDF and TXT files accordingly.

Target Format: Party v. Party, Volume Reporter Page (Year).pdf

Examples:
    - Miranda v. Arizona, 384 U.S. 436 (1966).pdf
    - Keko v. Hingle, 318 F.3d 639 (2002).pdf
    - Smith v. Jones, 123 F. Supp. 2d 456 (5th Cir. 2020).pdf
"""

import json
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional


# Reporter normalizations for Bluebook format
REPORTER_NORMALIZATIONS = {
    'F3d': 'F.3d',
    'F.3d': 'F.3d',
    'F2d': 'F.2d',
    'F.2d': 'F.2d',
    'Fd': 'F.',
    'F.': 'F.',
    'US': 'U.S.',
    'U.S.': 'U.S.',
    'SCt': 'S. Ct.',
    'S.Ct.': 'S. Ct.',
    'S. Ct.': 'S. Ct.',
    'FSupp3d': 'F. Supp. 3d',
    'F.Supp.3d': 'F. Supp. 3d',
    'F. Supp. 3d': 'F. Supp. 3d',
    'FSupp2d': 'F. Supp. 2d',
    'F.Supp.2d': 'F. Supp. 2d',
    'F. Supp. 2d': 'F. Supp. 2d',
    'FSupp': 'F. Supp.',
    'F.Supp.': 'F. Supp.',
    'F. Supp.': 'F. Supp.',
}


def normalize_reporter(reporter: str) -> str:
    """
    Normalize reporter abbreviation to Bluebook format.

    Args:
        reporter: Raw reporter string (e.g., 'F3d', 'US', 'SCt')

    Returns:
        Normalized reporter string (e.g., 'F.3d', 'U.S.', 'S. Ct.')
    """
    # Remove any extra spaces
    reporter = reporter.strip()

    # Check direct mappings
    if reporter in REPORTER_NORMALIZATIONS:
        return REPORTER_NORMALIZATIONS[reporter]

    # Try case-insensitive match
    for key, value in REPORTER_NORMALIZATIONS.items():
        if reporter.upper() == key.upper():
            return value

    # Return as-is if no match found
    return reporter


def normalize_case_name(case_name: str) -> str:
    """
    Normalize case name to proper Bluebook format.

    Args:
        case_name: Raw case name (e.g., 'JOHNSON v. JONES')

    Returns:
        Normalized case name with proper capitalization and v. separator
    """
    # Remove any citation info that might be embedded in the name
    # (e.g., "Deerfield Medical Center v. City of Deerfield Beach  661_F.2d_328")
    case_name = re.sub(r'\s+\d+[_\s].*$', '', case_name)

    # Replace various v separators with standard ' v. '
    case_name = re.sub(r'\s+(v\.?|vs\.?|V\.?|VS\.?)\s+', ' v. ', case_name, flags=re.IGNORECASE)

    # Title case the party names
    parts = case_name.split(' v. ')
    if len(parts) == 2:
        # Title case each part
        party1 = title_case_party(parts[0].strip())
        party2 = title_case_party(parts[1].strip())
        case_name = f"{party1} v. {party2}"
    else:
        # Fallback: just title case the whole thing
        case_name = title_case_party(case_name)

    # Remove extra spaces
    case_name = re.sub(r'\s+', ' ', case_name).strip()

    return case_name


def smart_capitalize(word: str) -> str:
    """
    Capitalize a word while preserving internal capitals (e.g., O'Brien, McDonald).

    Args:
        word: Word to capitalize

    Returns:
        Capitalized word with internal capitals preserved where appropriate
    """
    if not word:
        return word

    # Handle special cases with apostrophes (O'Brien, D'Angelo, etc.)
    if "'" in word:
        parts = word.split("'")
        return "'".join([part.capitalize() for part in parts])

    # Handle special cases with hyphens (Smith-Jones, etc.)
    if "-" in word:
        parts = word.split("-")
        return "-".join([part.capitalize() for part in parts])

    # Handle names starting with Mc or Mac (McDonald, MacArthur)
    if word.lower().startswith('mc') and len(word) > 2:
        return 'Mc' + word[2:].capitalize()
    if word.lower().startswith('mac') and len(word) > 3:
        return 'Mac' + word[3:].capitalize()

    # Default: just capitalize first letter
    return word.capitalize()


def title_case_party(party: str) -> str:
    """
    Title case a party name with special handling for legal terms.

    Args:
        party: Party name to title case

    Returns:
        Title cased party name
    """
    # Words that should stay lowercase unless at the beginning
    lowercase_words = {'of', 'the', 'in', 'at', 'by', 'for', 'on', 'and', 'or', 'a', 'an'}

    # Special abbreviations that should stay uppercase
    uppercase_abbrevs = {'U.S.', 'US', 'USA', 'FBI', 'CIA', 'IRS', 'DOJ', 'SEC', 'FTC'}

    words = party.split()
    result = []

    for i, word in enumerate(words):
        # Check if it's a special abbreviation that should stay uppercase
        if word.upper() in uppercase_abbrevs or word in uppercase_abbrevs:
            # Preserve U.S. format if it has periods, otherwise use U.S.
            if word.upper() == 'U.S.' or word.upper() == 'US':
                result.append('U.S.')
            else:
                result.append(word.upper())
        # First word is always capitalized
        elif i == 0:
            result.append(smart_capitalize(word))
        # Check if word should stay lowercase
        elif word.lower() in lowercase_words:
            result.append(word.lower())
        # Otherwise capitalize
        else:
            result.append(smart_capitalize(word))

    return ' '.join(result)


def sanitize_filename(filename: str) -> str:
    """
    Remove or replace characters that aren't allowed in filenames.

    Args:
        filename: Proposed filename

    Returns:
        Sanitized filename safe for all file systems
    """
    # Characters not allowed in filenames on various systems
    # Windows: < > : " / \ | ? *
    # macOS/Linux: / (and null)

    # Replace problematic characters with safe alternatives
    replacements = {
        '<': '(',
        '>': ')',
        ':': '-',
        '"': "'",
        '/': '-',
        '\\': '-',
        '|': '-',
        '?': '',
        '*': '',
        '\x00': '',
    }

    for char, replacement in replacements.items():
        filename = filename.replace(char, replacement)

    # Remove any double spaces created by replacements
    filename = re.sub(r'\s+', ' ', filename).strip()

    return filename


def generate_bluebook_filename(case: Dict) -> Optional[str]:
    """
    Generate a proper Bluebook-formatted filename for a case.

    Args:
        case: Case dictionary from index.json

    Returns:
        Bluebook-formatted filename without extension, or None if insufficient data
    """
    # Extract case information
    case_name = case.get('case_name', '').strip()
    volume = case.get('volume', '').strip()
    reporter = case.get('reporter', '').strip()
    page = case.get('page', '').strip()
    year = case.get('year', '').strip()
    court = case.get('court', '').strip()

    # Check if we have minimum required information
    if not case_name or not volume or not reporter or not page or not year:
        return None

    # Normalize case name and reporter
    case_name = normalize_case_name(case_name)
    reporter = normalize_reporter(reporter)

    # Build the filename
    # Format: Party v. Party, Volume Reporter Page (Court Year)
    if court and court not in ['U.S.', 'US']:
        filename = f"{case_name}, {volume} {reporter} {page} ({court} {year})"
    else:
        filename = f"{case_name}, {volume} {reporter} {page} ({year})"

    # Sanitize for filesystem
    filename = sanitize_filename(filename)

    return filename


def find_actual_file(case_library_path: Path, filename: str) -> Optional[Path]:
    """
    Find the actual file in the case library, handling case-insensitive matching.

    Args:
        case_library_path: Path to case library directory
        filename: Filename to search for

    Returns:
        Path to the actual file if found, None otherwise
    """
    exact_path = case_library_path / filename
    if exact_path.exists():
        return exact_path

    # Try case-insensitive search
    filename_lower = filename.lower()
    for file in case_library_path.iterdir():
        if file.name.lower() == filename_lower:
            return file

    return None


def rename_cases(case_library_path: str, dry_run: bool = True, verbose: bool = True) -> Dict:
    """
    Rename case PDF and TXT files to Bluebook format.

    Args:
        case_library_path: Path to case_library directory
        dry_run: If True, only show what would be renamed without actually renaming
        verbose: If True, print detailed information

    Returns:
        Dictionary with statistics about the renaming operation
    """
    case_library_path = Path(case_library_path)
    index_path = case_library_path / 'index.json'

    # Validate paths
    if not case_library_path.exists():
        raise FileNotFoundError(f"Case library directory not found: {case_library_path}")
    if not index_path.exists():
        raise FileNotFoundError(f"Index file not found: {index_path}")

    # Load index
    with open(index_path, 'r', encoding='utf-8') as f:
        index_data = json.load(f)

    cases = index_data.get('cases', [])

    # Statistics
    stats = {
        'total_cases': len(cases),
        'renamed': 0,
        'skipped_insufficient_data': 0,
        'skipped_already_correct': 0,
        'skipped_file_not_found': 0,
        'errors': 0,
        'error_details': []
    }

    # Track renames to update index
    renames = []

    print(f"\n{'='*80}")
    print(f"{'DRY RUN MODE - NO FILES WILL BE CHANGED' if dry_run else 'LIVE MODE - FILES WILL BE RENAMED'}")
    print(f"{'='*80}\n")

    for i, case in enumerate(cases, 1):
        case_id = case.get('id', 'unknown')
        old_pdf = case.get('pdf_filename', '')
        old_txt = case.get('txt_filename', '')

        if verbose:
            print(f"\n[{i}/{len(cases)}] Processing case ID: {case_id}")
            print(f"  Current name: {case.get('case_name', 'N/A')}")

        # Generate new filename
        new_base = generate_bluebook_filename(case)

        if not new_base:
            stats['skipped_insufficient_data'] += 1
            if verbose:
                print(f"  ⚠️  SKIPPED: Insufficient data for Bluebook format")
                print(f"     Missing: ", end='')
                missing = []
                for field in ['case_name', 'volume', 'reporter', 'page', 'year']:
                    if not case.get(field, '').strip():
                        missing.append(field)
                print(', '.join(missing))
            continue

        new_pdf = f"{new_base}.pdf"
        new_txt = f"{new_base}.txt"

        # Check if already in correct format
        if old_pdf == new_pdf and old_txt == new_txt:
            stats['skipped_already_correct'] += 1
            if verbose:
                print(f"  ✓  Already correct: {new_pdf}")
            continue

        if verbose:
            print(f"  New name: {new_pdf}")

        # Process PDF file
        pdf_renamed = False
        if old_pdf:
            old_pdf_path = find_actual_file(case_library_path, old_pdf)
            new_pdf_path = case_library_path / new_pdf

            if old_pdf_path and old_pdf_path.exists():
                # Check if new filename already exists (and is different file)
                if new_pdf_path.exists() and new_pdf_path != old_pdf_path:
                    stats['errors'] += 1
                    error_msg = f"Target PDF already exists: {new_pdf}"
                    stats['error_details'].append({'case_id': case_id, 'error': error_msg})
                    if verbose:
                        print(f"  ❌ ERROR: {error_msg}")
                elif old_pdf_path != new_pdf_path:
                    if dry_run:
                        print(f"  📄 Would rename PDF: {old_pdf} → {new_pdf}")
                    else:
                        try:
                            shutil.move(str(old_pdf_path), str(new_pdf_path))
                            print(f"  ✓  Renamed PDF: {old_pdf} → {new_pdf}")
                            pdf_renamed = True
                        except Exception as e:
                            stats['errors'] += 1
                            error_msg = f"Failed to rename PDF: {str(e)}"
                            stats['error_details'].append({'case_id': case_id, 'error': error_msg})
                            if verbose:
                                print(f"  ❌ ERROR: {error_msg}")
            else:
                if verbose:
                    print(f"  ⚠️  PDF file not found: {old_pdf}")

        # Process TXT file
        txt_renamed = False
        if old_txt:
            old_txt_path = find_actual_file(case_library_path, old_txt)
            new_txt_path = case_library_path / new_txt

            if old_txt_path and old_txt_path.exists():
                # Check if new filename already exists (and is different file)
                if new_txt_path.exists() and new_txt_path != old_txt_path:
                    stats['errors'] += 1
                    error_msg = f"Target TXT already exists: {new_txt}"
                    stats['error_details'].append({'case_id': case_id, 'error': error_msg})
                    if verbose:
                        print(f"  ❌ ERROR: {error_msg}")
                elif old_txt_path != new_txt_path:
                    if dry_run:
                        print(f"  📝 Would rename TXT: {old_txt} → {new_txt}")
                    else:
                        try:
                            shutil.move(str(old_txt_path), str(new_txt_path))
                            print(f"  ✓  Renamed TXT: {old_txt} → {new_txt}")
                            txt_renamed = True
                        except Exception as e:
                            stats['errors'] += 1
                            error_msg = f"Failed to rename TXT: {str(e)}"
                            stats['error_details'].append({'case_id': case_id, 'error': error_msg})
                            if verbose:
                                print(f"  ❌ ERROR: {error_msg}")
            else:
                if verbose and old_txt:
                    print(f"  ⚠️  TXT file not found: {old_txt}")

        # Track rename for index update
        if pdf_renamed or txt_renamed or dry_run:
            renames.append({
                'case_id': case_id,
                'old_pdf': old_pdf,
                'new_pdf': new_pdf,
                'old_txt': old_txt,
                'new_txt': new_txt
            })
            stats['renamed'] += 1

    # Update index.json with new filenames
    if not dry_run and renames:
        print(f"\n{'='*80}")
        print(f"Updating index.json with new filenames...")
        print(f"{'='*80}\n")

        for rename in renames:
            for case in cases:
                if case.get('id') == rename['case_id']:
                    case['pdf_filename'] = rename['new_pdf']
                    case['txt_filename'] = rename['new_txt']
                    break

        # Backup original index
        backup_path = case_library_path / 'index.json.backup'
        shutil.copy(str(index_path), str(backup_path))
        print(f"✓ Created backup: {backup_path}")

        # Write updated index
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, indent=2, ensure_ascii=False)
        print(f"✓ Updated index.json with new filenames")

    # Print summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total cases: {stats['total_cases']}")
    print(f"Renamed: {stats['renamed']}")
    print(f"Already correct: {stats['skipped_already_correct']}")
    print(f"Insufficient data: {stats['skipped_insufficient_data']}")
    print(f"Errors: {stats['errors']}")

    if stats['error_details']:
        print(f"\nError details:")
        for error in stats['error_details']:
            print(f"  - Case {error['case_id']}: {error['error']}")

    print(f"{'='*80}\n")

    return stats


def main():
    """Main entry point for the script."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Rename case library files to Bluebook format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Dry run (see what would be renamed):
  python rename_cases.py

  # Actually rename files:
  python rename_cases.py --live

  # Quiet mode (only show summary):
  python rename_cases.py --live --quiet
        '''
    )

    parser.add_argument(
        '--case-library',
        default=os.path.expanduser('~/Dropbox/Formarter Folder/case_library/'),
        help='Path to case library directory (default: ~/Dropbox/Formarter Folder/case_library/)'
    )

    parser.add_argument(
        '--live',
        action='store_true',
        help='Actually rename files (default is dry-run mode)'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Only show summary, not individual file operations'
    )

    args = parser.parse_args()

    try:
        stats = rename_cases(
            case_library_path=args.case_library,
            dry_run=not args.live,
            verbose=not args.quiet
        )

        # Exit with non-zero code if there were errors
        if stats['errors'] > 0:
            exit(1)

    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == '__main__':
    main()
