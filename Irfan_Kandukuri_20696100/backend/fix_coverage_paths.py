"""Rewrite coverage.xml so SonarQube can resolve file paths.

coverage.py (run from backend/) emits filenames relative to backend/
(e.g. "app/config.py"), but the SonarQube scanner resolves <source> entries
relative to the project root (one level up). This script prefixes every
class filename with "backend/" and points <sources> at the absolute project
root, matching what the scanner expects.
"""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent
COVERAGE_XML = BACKEND_DIR / "coverage.xml"


def main() -> None:
    tree = ET.parse(COVERAGE_XML)
    root = tree.getroot()

    sources = root.find("sources")
    for source in list(sources):
        sources.remove(source)
    new_source = ET.SubElement(sources, "source")
    new_source.text = str(PROJECT_ROOT)

    for cls in root.iter("class"):
        filename = cls.get("filename")
        if filename and not filename.startswith("backend/"):
            cls.set("filename", f"backend/{filename}")

    tree.write(COVERAGE_XML, encoding="UTF-8", xml_declaration=True)


if __name__ == "__main__":
    main()
    print(f"Rewrote {COVERAGE_XML} with project-root-relative paths.", file=sys.stderr)
