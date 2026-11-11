#!/usr/bin/env python3
"""Build a local installable skill ZIP from an explicit safe file allowlist."""

from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def package(output: Path) -> tuple[Path, int]:
    entry = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not re.match(r"\A---\nname: kouyu\ndescription: [^\n]+\n---", entry):
        raise ValueError("invalid kouyu skill frontmatter")
    if output.exists():
        raise ValueError("output already exists; choose another filename instead of overwriting")
    files = [ROOT / name for name in ("SKILL.md", "README.md")]
    for folder, patterns in {
        "agents": ("*.yaml",), "references": ("*.md",),
        "curriculum": ("*.md", "*.json"), "assets/workbench": ("*.html", "*.js", "*.css"),
        "docs/screenshots": ("*.png",), "scripts": ("*.py",),
        "tests": ("*.py", "*.cjs", "*.mjs", "fixtures/*.json"),
    }.items():
        for pattern in patterns:
            files.extend(path for path in (ROOT / folder).rglob(pattern) if path.is_file())
    files = sorted(set(files))
    # No recursive catch-all: never package workbench-data, user sessions, caches or local settings.
    for path in files:
        if path.is_symlink():
            raise ValueError(f"refuse symlink: {path}")
        path.resolve().relative_to(ROOT)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, Path("kouyu") / path.relative_to(ROOT))
    return output, len(files)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        path, count = package(args.output.resolve())
    except (ValueError, OSError) as error:
        parser.exit(2, f"package: {error}\n")
    print(f"Packaged {count} files: {path}")


if __name__ == "__main__":
    main()
