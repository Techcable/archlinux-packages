#!/usr/bin/env python
#
# NOTE: Python overhead dwarfed by `makepkg`

from __future__ import annotations

import sys
import tempfile
import subprocess
from enum import Enum
from pathlib import Path
from typing import NoReturn


def error(msg: str) -> None:
    if sys.stderr.isatty():
        prefix = "\x1b[1;31mERROR\x1b[0m:"
    else:
        prefix = "ERROR"
    print(prefix, msg, file=sys.stderr)


def fatal(msg: str) -> NoReturn:
    error(msg)
    sys.exit(1)


class SrcInfoStatus(Enum):
    MATCH = 0
    MISMATCH = 1


def check_srcinfo(pkgdir: Path) -> SrcInfoStatus:
    assert pkgdir.is_dir(), f"Missing pkgdir: {pkgdir!r}"
    actual_srcinfo_file = pkgdir / ".SRCINFO"
    if not actual_srcinfo_file.is_file():
        fatal("Missing .SRCINFO file in {pkgdir}")
    with tempfile.NamedTemporaryFile(
        suffix=".SRCINFO", delete=False
    ) as expected_srcinfo_file:
        try:
            subprocess.run(
                ["makepkg", "--printsrcinfo"],
                stdout=expected_srcinfo_file.file,
                cwd=pkgdir,
                check=True,
            )
        except subprocess.CalledProcessError:
            fatal("Failed to generate expected .SRCINFO file")
        actual_text = actual_srcinfo_file.read_text()
        expected_text = Path(expected_srcinfo_file.name).read_text()
        if actual_text == expected_text:
            return SrcInfoStatus.MATCH
        else:
            error("Expected .SRCINFO file doesn't match actual file (pkgdir: $pkgdir)")
            subprocess.run(
                [
                    "git",
                    "--no-pager",
                    "diff",
                    "--no-index",
                    actual_srcinfo_file,
                    expected_srcinfo_file.name,
                ],
                check=False,  # We do *not* care about exit code
            )
            return SrcInfoStatus.MISMATCH


def main(args: list[str]):
    target_pkgbuilds: list[Path]
    if not args:
        target_pkgbuilds = [
            target
            for target in Path(".").glob("**/PKGBUILD")
            if target.name == "PKGBUILD"
        ]
    else:
        target_pkgbuilds = [Path(target) for target in args]
    mismatched_files = []
    for pkgbuild_file in target_pkgbuilds:
        if pkgbuild_file.name != "PKGBUILD":
            fatal(f"File must be named `PKGBUILD`: `{pkgbuild_file}`")
        pkgdir = pkgbuild_file.parent
        print(
            "Checking validity of .SRCINFO based on PKGBUILD:", pkgdir, file=sys.stderr
        )
        match check_srcinfo(pkgdir):
            case SrcInfoStatus.MISMATCH:
                mismatched_files.append(pkgbuild_file)
            case SrcInfoStatus.MATCH:
                pass
    if mismatched_files:
        fatal("Mismatched .SRCINFO files: " + ", ".join(map(str, mismatched_files)))
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
