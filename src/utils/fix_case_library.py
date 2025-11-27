#!/usr/bin/env python3
"""
Batch fix script for case library names and citations.

Fixes:
1. Parse underscore-separated filenames into proper components
2. Title case case names
3. Remove "Cite as" and other artifacts
4. Fix reporter typos (s.ct., S.CL, S0.2d)
5. Regenerate bluebook_citation
"""

import json
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple


# Reporter normalizations
REPORTER_FIXES = {
    r's\.ct\.': 'S. Ct.',
    r'S\.CL': 'S. Ct.',
    r'S0\.2d': 'So. 2d',
    r'S0\.3d': 'So. 3d',
    r'F\s*4th': 'F.4th',
    r'F\s*3d': 'F.3d',
    r'F\s*2d': 'F.2d',
    r'F3d': 'F.3d',
    r'F2d': 'F.2d',
    r'US': 'U.S.',
    r'So2d': 'So. 2d',
    r'So3d': 'So. 3d',
}

# Words to keep lowercase in case names
LOWERCASE_WORDS = {'v', 'v.', 'of', 'the', 'in', 'at', 'by', 'for', 'on', 'and', 'or', 'a', 'an', 'to', 'ex', 're'}

# Abbreviations to keep uppercase
UPPERCASE_ABBREVS = {'U.S.', 'US', 'USA', 'FBI', 'CIA', 'IRS', 'DOJ', 'SEC', 'FTC',
                     'LLC', 'LLP', 'INC', 'CORP', 'CO', 'MUT', 'AUTO', 'INS', 'ELEC'}


def normalize_reporter(reporter: str) -> str:
    """Normalize reporter to standard Bluebook format."""
    if not reporter:
        return reporter

    reporter = reporter.strip()

    for pattern, replacement in REPORTER_FIXES.items():
        if re.match(pattern, reporter, re.IGNORECASE):
            return replacement
        reporter = re.sub(pattern, replacement, reporter, flags=re.IGNORECASE)

    return reporter


def title_case_name(name: str) -> str:
    """Convert case name to proper title case."""
    if not name:
        return name

    words = name.split()
    result = []

    for i, word in enumerate(words):
        word_upper = word.upper().rstrip('.,')
        word_clean = word.rstrip('.,')

        # Handle U.S. specifically
        if word_clean.upper() in ('U.S.', 'US', 'U.S'):
            result.append('U.S.')
        # Keep uppercase abbreviations
        elif word_upper in UPPERCASE_ABBREVS:
            result.append(word.upper() if len(word_clean) <= 4 else word.capitalize())
        # Keep lowercase words (except first)
        elif word.lower() in LOWERCASE_WORDS and i > 0:
            result.append(word.lower())
        else:
            result.append(word.capitalize())

    return ' '.join(result)


def parse_underscore_citation(text: str) -> Optional[Dict]:
    """
    Parse underscore-separated citation string.

    Examples:
        University_of_Texas_v_Camenisch_451_US_390_1981
        Johnson_v_Avery_393_US_483_1969
        Sinclair_v_Hawke_314_F3d_934_8th_Cir_2003
    """
    if '_' not in text:
        return None

    # Pattern: Name_v_Name_Volume_Reporter_Page[_Court]_Year
    # Try to find the v/V separator first
    parts = text.split('_')

    # Find 'v' or 'V' position
    v_idx = None
    for i, p in enumerate(parts):
        if p.lower() == 'v':
            v_idx = i
            break

    if v_idx is None:
        return None

    # Everything before v is party1, need to find where citation starts
    # Look for volume (number) after party2
    citation_start = None
    for i in range(v_idx + 2, len(parts)):
        if parts[i].isdigit() and len(parts[i]) <= 4:
            citation_start = i
            break

    if citation_start is None:
        return None

    # Parse components
    party1 = ' '.join(parts[:v_idx])
    party2 = ' '.join(parts[v_idx + 1:citation_start])

    remaining = parts[citation_start:]

    # Expected: Volume, Reporter, Page, [Court], Year
    if len(remaining) < 3:
        return None

    volume = remaining[0]

    # Find reporter (letters/dots)
    reporter_parts = []
    page_idx = 1
    for i in range(1, len(remaining)):
        part = remaining[i]
        if part.isdigit():
            page_idx = i
            break
        reporter_parts.append(part)

    if not reporter_parts:
        return None

    reporter = '.'.join(reporter_parts).replace('..', '.')
    reporter = normalize_reporter(reporter)

    page = remaining[page_idx] if page_idx < len(remaining) else ''

    # Rest could be court and year
    rest = remaining[page_idx + 1:]
    year = ''
    court = ''

    for part in rest:
        if part.isdigit() and len(part) == 4:
            year = part
        elif not part.isdigit():
            court = part.replace('_', ' ')

    case_name = f"{title_case_name(party1)} v. {title_case_name(party2)}"

    return {
        'case_name': case_name,
        'volume': volume,
        'reporter': reporter,
        'page': page,
        'year': year,
        'court': court
    }


def clean_case_name(name: str) -> str:
    """Clean and normalize a case name."""
    if not name:
        return name

    # Remove "Cite as" and similar artifacts
    name = re.sub(r'\s*Cite\s+as.*$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*KeyCite.*$', '', name, flags=re.IGNORECASE)

    # Remove embedded citation numbers at end
    name = re.sub(r'\s+\d+\s*$', '', name)
    name = re.sub(r'\s+\d+_[A-Za-z.]+_\d+.*$', '', name)

    # Replace underscores with spaces
    name = name.replace('_', ' ')

    # Normalize "v" to "v."
    name = re.sub(r'\s+[vV]\s+', ' v. ', name)
    name = re.sub(r'\s+\.v\s+', ' v. ', name)

    # Clean up whitespace
    name = ' '.join(name.split())

    # Apply title case
    name = title_case_name(name)

    return name


def format_bluebook(case_name: str, volume: str, reporter: str, page: str,
                    court: str = '', year: str = '') -> str:
    """Format a proper Bluebook citation."""
    if not all([case_name, volume, reporter, page]):
        return ''

    citation = f"{case_name}, {volume} {reporter} {page}"

    if court or year:
        paren_parts = []
        if court and court not in ['U.S.', 'US']:
            paren_parts.append(court)
        if year:
            paren_parts.append(year)
        if paren_parts:
            citation += f" ({' '.join(paren_parts)})"

    return citation


def fix_case(case: Dict, dry_run: bool = True) -> Tuple[Dict, list]:
    """
    Fix a single case entry.
    Returns (fixed_case, list_of_changes)
    """
    changes = []
    fixed = case.copy()

    original_name = case.get('case_name', '')
    original_citation = case.get('bluebook_citation', '')

    # Check if we need to parse from underscore format
    needs_parsing = (
        not case.get('volume') or
        not case.get('reporter') or
        not case.get('page') or
        '_' in original_name
    )

    if needs_parsing:
        # Try to parse from bluebook_citation or case_name
        parse_source = original_citation if '_' in original_citation else original_name
        parsed = parse_underscore_citation(parse_source)

        if parsed:
            if parsed['case_name'] != original_name:
                fixed['case_name'] = parsed['case_name']
                changes.append(f"case_name: '{original_name}' -> '{parsed['case_name']}'")

            if parsed['volume'] and parsed['volume'] != case.get('volume'):
                fixed['volume'] = parsed['volume']
                changes.append(f"volume: '{case.get('volume', '')}' -> '{parsed['volume']}'")

            if parsed['reporter'] and parsed['reporter'] != case.get('reporter'):
                fixed['reporter'] = parsed['reporter']
                changes.append(f"reporter: '{case.get('reporter', '')}' -> '{parsed['reporter']}'")

            if parsed['page'] and parsed['page'] != case.get('page'):
                fixed['page'] = parsed['page']
                changes.append(f"page: '{case.get('page', '')}' -> '{parsed['page']}'")

            if parsed['year'] and parsed['year'] != case.get('year'):
                fixed['year'] = parsed['year']
                changes.append(f"year: '{case.get('year', '')}' -> '{parsed['year']}'")

            if parsed['court'] and parsed['court'] != case.get('court'):
                fixed['court'] = parsed['court']
                changes.append(f"court: '{case.get('court', '')}' -> '{parsed['court']}'")

    # Clean case name regardless
    cleaned_name = clean_case_name(fixed.get('case_name', ''))
    if cleaned_name and cleaned_name != fixed.get('case_name'):
        changes.append(f"case_name cleaned: '{fixed.get('case_name', '')}' -> '{cleaned_name}'")
        fixed['case_name'] = cleaned_name

    # Normalize reporter
    if fixed.get('reporter'):
        normalized = normalize_reporter(fixed['reporter'])
        if normalized != fixed['reporter']:
            changes.append(f"reporter normalized: '{fixed['reporter']}' -> '{normalized}'")
            fixed['reporter'] = normalized

    # Regenerate bluebook_citation if we have all components
    if all([fixed.get('case_name'), fixed.get('volume'), fixed.get('reporter'), fixed.get('page')]):
        new_citation = format_bluebook(
            fixed['case_name'],
            fixed['volume'],
            fixed['reporter'],
            fixed['page'],
            fixed.get('court', ''),
            fixed.get('year', '')
        )
        if new_citation and new_citation != fixed.get('bluebook_citation'):
            changes.append(f"bluebook_citation regenerated")
            fixed['bluebook_citation'] = new_citation

    return fixed, changes


def run_fix(dry_run: bool = True, verbose: bool = True):
    """Run the batch fix on the case library."""
    index_path = Path.home() / "Dropbox/Formarter Folder/case_library/index.json"

    if not index_path.exists():
        print(f"Index not found: {index_path}")
        return

    # Load index
    with open(index_path, 'r') as f:
        data = json.load(f)

    cases = data.get('cases', [])
    print(f"{'DRY RUN - ' if dry_run else ''}Processing {len(cases)} cases...\n")

    fixed_count = 0
    total_changes = 0
    flagged = []  # Cases that need manual review

    for i, case in enumerate(cases):
        fixed, changes = fix_case(case, dry_run)

        if changes:
            fixed_count += 1
            total_changes += len(changes)

            if verbose:
                print(f"\n[{i+1}] {case.get('case_name', 'Unknown')[:50]}...")
                for change in changes:
                    print(f"    - {change}")

            if not dry_run:
                cases[i] = fixed

        # Flag suspicious entries for manual review
        name = fixed.get('case_name', '')
        if (len(name) < 5 or
            not ' v. ' in name.lower() or
            name.lower() in ['unknown case', 'wtf?'] or
            re.match(r'^[\d._]+$', name)):
            flagged.append((i, name, case.get('bluebook_citation', '')))

    print(f"\n{'='*60}")
    print(f"SUMMARY {'(DRY RUN)' if dry_run else ''}")
    print(f"{'='*60}")
    print(f"Total cases: {len(cases)}")
    print(f"Cases fixed: {fixed_count}")
    print(f"Total changes: {total_changes}")
    print(f"Flagged for review: {len(flagged)}")

    if flagged and verbose:
        print(f"\nFLAGGED ENTRIES (need manual review):")
        for idx, name, citation in flagged[:20]:
            print(f"  [{idx}] {name[:40]} | {citation[:40]}")
        if len(flagged) > 20:
            print(f"  ... and {len(flagged) - 20} more")

    if not dry_run and fixed_count > 0:
        # Backup original
        backup_path = index_path.with_suffix(f'.json.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
        shutil.copy(index_path, backup_path)
        print(f"\nBackup saved to: {backup_path}")

        # Save fixed index
        with open(index_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Updated index saved to: {index_path}")

    return fixed_count, flagged


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Fix case library names and citations')
    parser.add_argument('--live', action='store_true', help='Actually make changes (default: dry run)')
    parser.add_argument('--quiet', action='store_true', help='Less verbose output')

    args = parser.parse_args()

    run_fix(dry_run=not args.live, verbose=not args.quiet)
