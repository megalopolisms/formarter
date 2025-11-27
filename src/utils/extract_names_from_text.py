#!/usr/bin/env python3
"""
Extract case names from text content for cases with numeric/citation-style names.

This script reads the text files and extracts the actual case names using patterns
typical in Supreme Court Reporter and Federal Reporter documents.
"""

import json
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple, List


def is_problematic_name(name: str) -> bool:
    """Check if case name needs extraction from text."""
    if not name:
        return True

    # Problematic patterns
    # Starts with numbers like "111 S.Ct."
    if re.match(r'^[\d\s\.]+[A-Za-z\.]+[\d\s\.]*$', name):
        return True
    # Just reporter citation like "F.3d 752"
    if re.match(r'^[A-Za-z\.]+\d*[a-z]*\s+\d+$', name):
        return True
    # Missing "v." - not a proper case name
    if ' v. ' not in name and ' v ' not in name.lower():
        return True
    # Garbage entries
    if name.lower() in ['unknown case', 'wtf?', 'third lawsuit']:
        return True
    # Too short
    if len(name) < 5:
        return True

    return False


def extract_case_name_from_text(text: str, max_chars: int = 3000) -> Optional[Dict]:
    """
    Extract case name and citation from text content.

    Legal documents typically have the case name near the beginning,
    often in formats like:
    - PARTY NAME, Petitioner, v. OTHER PARTY
    - Party Name v. Other Party
    - In re PARTY NAME

    Citation info appears as: "123 U.S. 456" or "123 F.3d 456"
    """
    # Only look at first portion of text
    text = text[:max_chars]

    result = {
        'case_name': '',
        'volume': '',
        'reporter': '',
        'page': '',
        'year': '',
        'court': ''
    }

    # Try to find case name patterns
    case_name = None

    # Pattern 1: ALL-CAPS case names (very common in court documents)
    # Look for: "PARTY NAME, Petitioner,\nv.\nOTHER PARTY"
    # or "PARTY NAME v. OTHER PARTY"
    patterns = [
        # Supreme Court Reporter format: ALL CAPS with roles
        # SEMINOLE TRIBE OF FLORIDA,\nPetitioner,\nv.\nFLORIDA et al.
        r'([A-Z][A-Z\s\'\-\.]+?),?\s*\n?\s*(?:Petitioner|Appellant|Plaintiff)s?,?\s*\n?\s*v\.?\s*\n?\s*([A-Z][A-Z\s\'\-\.]+?)(?:\s*,?\s*(?:et\s+al\.?|Respondent|Appellee|Defendant))?(?:\s*\n|\s*No\.)',
        # Standard ALL-CAPS: PARTY v. PARTY
        r'\n([A-Z][A-Z\s\'\-\.]{3,40})\s+v\.?\s+([A-Z][A-Z\s\'\-\.]{3,40})(?:\s*\n|,)',
        # Mixed case with v.: "United States v. Party"
        r'\n(United\s+States|State\s+of\s+[A-Z][a-z]+)\s+v\.?\s+([A-Z][A-Za-z\s\'\-\.]+?)(?:\s*\n|,)',
        # In re format (ALL CAPS)
        r'\n(In\s+re\s+[A-Z][A-Z\s\'\-\.]+?)(?:\s*\n|,)',
        # In re format (mixed case)
        r'\n(In\s+re\s+[A-Z][A-Za-z\s\'\-\.]+?)(?:\s*\n|,)',
        # Ex parte format
        r'\n(Ex\s+parte\s+[A-Z][A-Za-z\s\'\-\.]+?)(?:\s*\n|,)',
    ]

    # Garbage patterns to filter out - be specific to avoid false positives
    garbage_phrases = ['since ', 'with the', 'see ', 'cf. ', 'governs', 'spirit of',
                       'full spirit', 'donald governs', 'eeoc was', 'case. cf']

    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
        if match:
            if match.lastindex == 2:
                party1 = clean_party_name(match.group(1))
                party2 = clean_party_name(match.group(2))
                # Validate: both parties should be reasonable names
                if party1 and party2 and len(party1) >= 3 and len(party2) >= 3:
                    # Filter out garbage phrases
                    full_name = f"{party1} v. {party2}".lower()
                    if any(phrase in full_name for phrase in garbage_phrases):
                        continue
                    case_name = f"{party1} v. {party2}"
                    break
            else:
                name = clean_party_name(match.group(1))
                if name and len(name) >= 5:
                    name_lower = name.lower()
                    if any(phrase in name_lower for phrase in garbage_phrases):
                        continue
                    case_name = name
                    break

    if case_name:
        result['case_name'] = case_name

    # Extract citation info: Volume Reporter Page
    # Pattern: digits + reporter abbreviation + digits
    citation_patterns = [
        # U.S. Reports: 517 U.S. 44
        r'(\d{1,3})\s+(U\.?\s*S\.?)\s+(\d{1,4})',
        # Supreme Court Reporter: 116 S.Ct. 1114
        r'(\d{1,3})\s+(S\.?\s*Ct\.?)\s+(\d{1,4})',
        # Federal Reporter: 123 F.3d 456
        r'(\d{1,3})\s+(F\.?\s*(?:4th|3d|2d|\.)?)\s+(\d{1,4})',
        # Federal Supplement: 123 F.Supp.3d 456
        r'(\d{1,3})\s+(F\.?\s*Supp\.?\s*(?:3d|2d)?)\s+(\d{1,4})',
        # L.Ed.2d: 134 L.Ed.2d 252
        r'(\d{1,3})\s+(L\.?\s*Ed\.?\s*2d)\s+(\d{1,4})',
        # So.2d/So.3d: 123 So.2d 456
        r'(\d{1,3})\s+(So\.?\s*(?:3d|2d))\s+(\d{1,4})',
    ]

    for pattern in citation_patterns:
        match = re.search(pattern, text)
        if match:
            result['volume'] = match.group(1)
            result['reporter'] = normalize_reporter(match.group(2))
            result['page'] = match.group(3)
            break

    # Extract year: (1996) or decided/argued dates
    year_match = re.search(r'\b(19\d{2}|20[0-2]\d)\b', text[:2000])
    if year_match:
        result['year'] = year_match.group(1)

    # Extract court for circuit/district cases
    court_match = re.search(r'\((\d+)(?:st|nd|rd|th)\s*Cir\.?\s*\d*\)', text)
    if court_match:
        result['court'] = f"{court_match.group(1)}th Cir."

    return result if result['case_name'] else None


def clean_party_name(name: str) -> str:
    """Clean up a party name."""
    if not name:
        return ''

    # Remove role designations
    name = re.sub(r',?\s*(?:Petitioner|Appellant|Plaintiff|Respondent|Appellee|Defendant)s?\.?', '', name, flags=re.IGNORECASE)
    # Remove et al.
    name = re.sub(r',?\s*et\s+al\.?', '', name, flags=re.IGNORECASE)
    # Clean whitespace
    name = ' '.join(name.split())
    # Remove trailing punctuation
    name = name.strip(' ,.')

    # Title case
    return title_case_party(name)


def title_case_party(party: str) -> str:
    """Title case a party name properly."""
    if not party:
        return ''

    lowercase_words = {'of', 'the', 'in', 'at', 'by', 'for', 'on', 'and', 'or', 'a', 'an', 'to'}
    uppercase_abbrevs = {'U.S.', 'US', 'USA', 'FBI', 'CIA', 'IRS', 'DOJ', 'SEC', 'FTC',
                         'LLC', 'LLP', 'INC', 'CORP', 'CO', 'IGRA'}

    words = party.split()
    result = []
    for i, word in enumerate(words):
        word_clean = word.rstrip('.,')
        word_upper = word_clean.upper()

        # Handle U.S. specifically
        if word_upper in ('U.S.', 'US', 'U.S'):
            result.append('U.S.')
        elif word_upper in uppercase_abbrevs:
            result.append(word_upper)
        elif i == 0:
            result.append(word.capitalize())
        elif word.lower() in lowercase_words:
            result.append(word.lower())
        elif party.isupper():
            # Convert all-caps to title case
            result.append(word.capitalize())
        else:
            result.append(word)

    return ' '.join(result)


def normalize_reporter(reporter: str) -> str:
    """Normalize reporter abbreviation to Bluebook format."""
    reporter = reporter.strip()

    normalizations = {
        'US': 'U.S.',
        'U S': 'U.S.',
        'U.S': 'U.S.',
        'SCt': 'S. Ct.',
        'S Ct': 'S. Ct.',
        'S.Ct': 'S. Ct.',
        'S.Ct.': 'S. Ct.',
        'F4th': 'F.4th',
        'F 4th': 'F.4th',
        'F3d': 'F.3d',
        'F 3d': 'F.3d',
        'F2d': 'F.2d',
        'F 2d': 'F.2d',
        'FSupp3d': 'F. Supp. 3d',
        'F Supp 3d': 'F. Supp. 3d',
        'FSupp2d': 'F. Supp. 2d',
        'F Supp 2d': 'F. Supp. 2d',
        'FSupp': 'F. Supp.',
        'F Supp': 'F. Supp.',
        'LEd2d': 'L. Ed. 2d',
        'L Ed 2d': 'L. Ed. 2d',
        'So3d': 'So. 3d',
        'So 3d': 'So. 3d',
        'So2d': 'So. 2d',
        'So 2d': 'So. 2d',
    }

    # Try exact match first
    reporter_clean = re.sub(r'\s+', ' ', reporter).strip()
    for pattern, replacement in normalizations.items():
        if reporter_clean.upper().replace('.', '').replace(' ', '') == pattern.upper().replace('.', '').replace(' ', ''):
            return replacement

    return reporter


def format_bluebook_citation(info: Dict) -> str:
    """Format proper Bluebook citation."""
    if not info.get('case_name') or not info.get('volume') or not info.get('reporter') or not info.get('page'):
        return ''

    citation = f"{info['case_name']}, {info['volume']} {info['reporter']} {info['page']}"

    if info.get('year') or info.get('court'):
        paren_parts = []
        if info.get('court') and info['court'] not in ['U.S.', 'US']:
            paren_parts.append(info['court'])
        if info.get('year'):
            paren_parts.append(info['year'])
        if paren_parts:
            citation += f" ({' '.join(paren_parts)})"

    return citation


def run_extraction(dry_run: bool = True, verbose: bool = True):
    """Run extraction on problematic cases."""
    library_path = Path.home() / "Dropbox/Formarter Folder/case_library"
    index_path = library_path / "index.json"

    if not index_path.exists():
        print(f"Index not found: {index_path}")
        return

    with open(index_path, 'r') as f:
        data = json.load(f)

    cases = data.get('cases', [])
    print(f"{'DRY RUN - ' if dry_run else ''}Processing {len(cases)} cases...\n")

    fixed_count = 0
    skipped = 0
    no_text = 0

    for i, case in enumerate(cases):
        name = case.get('case_name', '')

        if not is_problematic_name(name):
            continue

        # Try to extract from text file
        txt_file = library_path / case.get('txt_filename', '')
        if not txt_file.exists():
            if verbose:
                print(f"  [No txt] {name[:50]}")
            no_text += 1
            continue

        try:
            text = txt_file.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            if verbose:
                print(f"  [Error reading] {name[:50]}: {e}")
            skipped += 1
            continue

        extracted = extract_case_name_from_text(text)

        if not extracted or not extracted.get('case_name'):
            if verbose:
                print(f"  [No match] {name[:50]}")
            skipped += 1
            continue

        # Found a case name!
        new_name = extracted['case_name']

        if verbose:
            print(f"\n[{i}] FOUND: {name[:40]}")
            print(f"     -> {new_name}")

        changes = []

        if new_name and new_name != name:
            changes.append(f"case_name: '{name}' -> '{new_name}'")
            if not dry_run:
                cases[i]['case_name'] = new_name

        # Update citation fields if extracted
        if extracted.get('volume') and not case.get('volume'):
            changes.append(f"volume: '' -> '{extracted['volume']}'")
            if not dry_run:
                cases[i]['volume'] = extracted['volume']

        if extracted.get('reporter') and not case.get('reporter'):
            changes.append(f"reporter: '' -> '{extracted['reporter']}'")
            if not dry_run:
                cases[i]['reporter'] = extracted['reporter']

        if extracted.get('page') and not case.get('page'):
            changes.append(f"page: '' -> '{extracted['page']}'")
            if not dry_run:
                cases[i]['page'] = extracted['page']

        if extracted.get('year') and not case.get('year'):
            changes.append(f"year: '' -> '{extracted['year']}'")
            if not dry_run:
                cases[i]['year'] = extracted['year']

        # Regenerate bluebook citation
        info = {
            'case_name': new_name or name,
            'volume': extracted.get('volume') or case.get('volume', ''),
            'reporter': extracted.get('reporter') or case.get('reporter', ''),
            'page': extracted.get('page') or case.get('page', ''),
            'year': extracted.get('year') or case.get('year', ''),
            'court': extracted.get('court') or case.get('court', '')
        }

        new_citation = format_bluebook_citation(info)
        if new_citation and new_citation != case.get('bluebook_citation'):
            changes.append(f"bluebook_citation regenerated")
            if not dry_run:
                cases[i]['bluebook_citation'] = new_citation

        if changes:
            fixed_count += 1
            if verbose:
                for change in changes:
                    print(f"     {change}")

    print(f"\n{'='*60}")
    print(f"SUMMARY {'(DRY RUN)' if dry_run else ''}")
    print(f"{'='*60}")
    print(f"Cases with problematic names: {fixed_count + skipped + no_text}")
    print(f"Fixed from text: {fixed_count}")
    print(f"No text file: {no_text}")
    print(f"Could not extract: {skipped}")

    if not dry_run and fixed_count > 0:
        # Backup
        backup_path = index_path.with_suffix(f'.json.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        shutil.copy(index_path, backup_path)
        print(f"\nBackup saved to: {backup_path}")

        # Save
        with open(index_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Updated index saved to: {index_path}")

    return fixed_count


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Extract case names from text content')
    parser.add_argument('--live', action='store_true', help='Actually make changes')
    parser.add_argument('--quiet', action='store_true', help='Less verbose output')

    args = parser.parse_args()

    run_extraction(dry_run=not args.live, verbose=not args.quiet)
