#!/usr/bin/env python3
"""
Test script to show what rename_cases.py will do without running the full rename.
Shows a sample of renames that would occur.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path so we can import rename_cases
sys.path.insert(0, str(Path(__file__).parent))

from rename_cases import (
    generate_bluebook_filename,
    normalize_case_name,
    normalize_reporter,
)


def test_rename_sample():
    """Show a sample of what files would be renamed."""

    case_library = Path.home() / 'Dropbox/Formarter Folder/case_library'
    index_path = case_library / 'index.json'

    if not index_path.exists():
        print(f"Error: Index file not found at {index_path}")
        return

    # Load index
    with open(index_path, 'r', encoding='utf-8') as f:
        index_data = json.load(f)

    cases = index_data.get('cases', [])

    print("\n" + "="*100)
    print("SAMPLE RENAMING PREVIEW (First 10 cases that would change)")
    print("="*100 + "\n")

    samples_shown = 0
    max_samples = 10

    for i, case in enumerate(cases, 1):
        if samples_shown >= max_samples:
            break

        old_pdf = case.get('pdf_filename', '')
        old_txt = case.get('txt_filename', '')

        # Generate new filename
        new_base = generate_bluebook_filename(case)

        if not new_base:
            continue

        new_pdf = f"{new_base}.pdf"
        new_txt = f"{new_base}.txt"

        # Only show if it would change
        if old_pdf != new_pdf or old_txt != new_txt:
            samples_shown += 1

            print(f"[{samples_shown}] {case.get('case_name', 'N/A')}")
            print(f"    Case Info:")
            print(f"      Volume: {case.get('volume', 'N/A')}")
            print(f"      Reporter: {case.get('reporter', 'N/A')} → {normalize_reporter(case.get('reporter', ''))}")
            print(f"      Page: {case.get('page', 'N/A')}")
            print(f"      Year: {case.get('year', 'N/A')}")
            print(f"      Court: {case.get('court', 'N/A')}")

            print(f"\n    Current PDF: {old_pdf}")
            print(f"    New PDF:     {new_pdf}")

            if old_txt and old_txt != new_txt:
                print(f"\n    Current TXT: {old_txt}")
                print(f"    New TXT:     {new_txt}")

            print("\n" + "-"*100 + "\n")

    # Print statistics
    print("\n" + "="*100)
    print("STATISTICS FOR ALL CASES")
    print("="*100 + "\n")

    total = len(cases)
    would_rename = 0
    already_correct = 0
    insufficient_data = 0

    for case in cases:
        old_pdf = case.get('pdf_filename', '')
        new_base = generate_bluebook_filename(case)

        if not new_base:
            insufficient_data += 1
            continue

        new_pdf = f"{new_base}.pdf"

        if old_pdf == new_pdf:
            already_correct += 1
        else:
            would_rename += 1

    print(f"Total cases: {total}")
    print(f"Would be renamed: {would_rename}")
    print(f"Already correct: {already_correct}")
    print(f"Insufficient data: {insufficient_data}")
    print("\n" + "="*100 + "\n")


def test_normalizations():
    """Test reporter and case name normalizations."""

    print("\n" + "="*100)
    print("NORMALIZATION TESTS")
    print("="*100 + "\n")

    # Test reporter normalizations
    print("Reporter Normalizations:")
    print("-"*100)
    test_reporters = [
        ('F3d', 'F.3d'),
        ('F2d', 'F.2d'),
        ('US', 'U.S.'),
        ('SCt', 'S. Ct.'),
        ('S.Ct.', 'S. Ct.'),
        ('FSupp2d', 'F. Supp. 2d'),
        ('FSupp3d', 'F. Supp. 3d'),
    ]

    for input_rep, expected in test_reporters:
        actual = normalize_reporter(input_rep)
        status = "✓" if actual == expected else "✗"
        print(f"  {status} {input_rep:15} → {actual:15} (expected: {expected})")

    # Test case name normalizations
    print("\n\nCase Name Normalizations:")
    print("-"*100)
    test_names = [
        'JOHNSON v. JONES',
        'KEKO v. HINGLE',
        'Miranda v. Arizona',
        'smith V jones',
        'UNITED STATES v JOHNSON',
        'Deerfield Medical Center v. City of Deerfield Beach  661_F.2d_328',
    ]

    for name in test_names:
        normalized = normalize_case_name(name)
        print(f"  {name}")
        print(f"    → {normalized}\n")

    print("="*100 + "\n")


if __name__ == '__main__':
    test_normalizations()
    test_rename_sample()
