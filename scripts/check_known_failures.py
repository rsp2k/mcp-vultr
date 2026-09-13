#!/usr/bin/env python3
"""
Compare a pytest JUnit XML run against the recorded set of known failures.

The suite carries a long tail of pre-existing failures (63 distinct causes as
of 2026-09-13), so "all green" is not reachable in one pass and a workflow that
simply goes red teaches everyone to ignore it. This keeps the signal: the build
fails only when a test that used to pass starts failing.

Exit codes:
    0  no regressions (newly-fixed tests are reported, not punished)
    1  at least one test regressed
    2  the baseline file or the XML could not be read

Usage:
    check_known_failures.py results.xml tests/known_failures.txt
    check_known_failures.py results.xml tests/known_failures.txt --update
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def failing_tests(xml_path: Path) -> set[str]:
    """Return `classname::name` for every test that failed or errored."""
    root = ET.parse(xml_path).getroot()
    failing = set()
    for case in root.iter("testcase"):
        if case.find("failure") is not None or case.find("error") is not None:
            failing.add(f"{case.get('classname')}::{case.get('name')}")
    return failing


def all_tests(xml_path: Path) -> set[str]:
    root = ET.parse(xml_path).getroot()
    return {f"{c.get('classname')}::{c.get('name')}" for c in root.iter("testcase")}


def read_baseline(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    }


HEADER = """\
# Tests that were already failing when this guard was introduced (2026-09-13).
#
# The build fails if a test NOT in this list starts failing. Fixing one of
# these is welcome: delete its line in the same commit, and the guard will
# hold the new ground. Regenerate wholesale only when you mean to:
#     make test-known-failures-update
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("xml", type=Path, help="pytest JUnit XML")
    ap.add_argument("baseline", type=Path, help="known-failures file")
    ap.add_argument(
        "--update", action="store_true", help="rewrite the baseline from this run"
    )
    args = ap.parse_args()

    try:
        failing = failing_tests(args.xml)
        collected = all_tests(args.xml)
    except (OSError, ET.ParseError) as exc:
        print(f"error: cannot read {args.xml}: {exc}", file=sys.stderr)
        return 2

    if args.update:
        args.baseline.write_text(HEADER + "\n".join(sorted(failing)) + "\n")
        print(f"wrote {len(failing)} known failures to {args.baseline}")
        return 0

    known = read_baseline(args.baseline)
    regressions = sorted(failing - known)
    # Only count a known failure as fixed if it actually ran this time;
    # a test that was renamed or deselected has not been fixed.
    fixed = sorted((known - failing) & collected)
    missing = sorted(known - collected)

    print(f"collected {len(collected)}, failing {len(failing)}, known {len(known)}")

    if fixed:
        print(f"\n{len(fixed)} known failure(s) now pass. Remove them from "
              f"{args.baseline}:")
        for name in fixed:
            print(f"  {name}")

    if missing:
        print(f"\n{len(missing)} known failure(s) did not run (renamed or "
              f"deselected), left in place:")
        for name in missing[:10]:
            print(f"  {name}")

    if regressions:
        print(f"\nREGRESSION: {len(regressions)} test(s) newly failing:")
        for name in regressions:
            print(f"  {name}")
        return 1

    print("\nno regressions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
