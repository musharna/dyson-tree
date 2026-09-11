"""Provenance header for DERIVED csvs -- the ones under tools/derive_*.py.

The three experiment runners each stamp their own header (see
`experiments/*/run.py::provenance_lines`). Files written by a derivation tool
need one more line than those do -- `derived_by`, naming the script -- because a
reader who finds `candidates.csv` next to `limits.csv` must be able to tell at a
glance which one came out of the registered runner and which was computed
afterwards from committed inputs.

A derived file is NOT a measurement. Every tool here recomputes a number that
some document already reports, from inputs that are already committed, using the
runner's own functions rather than a reimplementation. The header records what
it ran against so that claim is checkable.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import platform
import subprocess
from pathlib import Path

import numpy as np
import scipy

REPO_ROOT = Path(__file__).resolve().parents[1]


def md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def git_sha() -> str:
    """HEAD sha, or a loud error carrying git's own stderr. A derived file whose
    provenance line silently said "unknown" would be worse than no file."""
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git rev-parse HEAD failed in {REPO_ROOT} "
            f"(exit {proc.returncode}): {proc.stderr.strip() or '<no stderr>'}"
        )
    return proc.stdout.strip()


def derived_header(script: Path | str, sources: list[Path | str]) -> list[str]:
    """Header lines for a derived CSV.

    `script` is the tool that produced it and `sources` the committed inputs it
    read, each recorded with its md5 so a later reader can tell whether the
    input has moved since. Paths are written repo-relative: an absolute path
    would leak the machine the file was built on.
    """
    lines = [
        f"# derived_by={Path(script).resolve().relative_to(REPO_ROOT).as_posix()}",
        f"# git_sha={git_sha()}",
    ]
    for src in sources:
        p = Path(src).resolve()
        rel = p.relative_to(REPO_ROOT).as_posix()
        lines.append(f"# source={rel} md5={md5(p)}")
    lines += [
        f"# python={platform.python_version()}",
        f"# numpy={np.__version__}",
        f"# scipy={scipy.__version__}",
        f"# written={dt.datetime.now().astimezone().isoformat(timespec='seconds')}",
    ]
    return lines


def write_derived_csv(
    path: Path, header: list[str], fieldnames: list[str], rows: list[dict]
) -> None:
    """Same on-disk shape as the runners' write_csv: header comments, then a
    normal CSV with `\\n` line endings on every platform."""
    import csv

    with open(path, "w", newline="") as fh:
        for line in header:
            fh.write(line + "\n")
        w = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)
