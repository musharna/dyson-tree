"""The committed spectral table, checked without its sources (§6's table checks).

`ASTMG173.csv` and `iop2008.dat` are gitignored (`.gitignore:9-10`), so in CI they
are absent BY CONSTRUCTION. Everything here except `test_regenerate_spectral_table`
runs against the committed file alone: the digest of the data rows, the row count,
the monotone grid, and four pinned `k` rows. Endpoints alone would let a doubled
interior pass (round-3 audit), which is why the four interior rows are pinned.

`test_regenerate_spectral_table` is the only check that can say "table follows from
sources"; it SKIPS -- never passes -- when either source is missing, so a green CI
run claims only "rows follow from table".
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "sim" / "spectral_table.csv"

# sha256 over the DATA rows (the header carries the producer's commit, which moves
# with every commit; the table itself does not).
TABLE_DIGEST = "2cfea122d9f6f8aae04b3cc53221d67f6d010f94ead1ff39a81a78f4398da0b8"

# §6: "four pinned `k` rows, 0.00074 /m at 400 nm, 0.05230 at 550, 0.38623 at 680
# and 0.52061 at 700". The tolerance is the printed digits' half-ulp.
PINNED_K = {400.0: 0.00074, 550.0: 0.05230, 680.0: 0.38623, 700.0: 0.52061}


def _text() -> str:
    return TABLE.read_text()


def _data_text() -> str:
    return "".join(
        ln for ln in _text().splitlines(keepends=True) if not ln.startswith("#")
    )


def _rows() -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(_data_text())))


def test_table_digest_is_pinned():
    digest = hashlib.sha256(_data_text().encode()).hexdigest()
    assert digest == TABLE_DIGEST, f"spectral table changed: sha256 {digest}"


def test_row_count_is_2002():
    assert len(_rows()) == 2002


def test_columns_and_line_endings():
    assert _rows()[0].keys() == {"lambda_nm", "k_per_m", "E_AM0", "n_ph"}
    raw = TABLE.read_bytes()
    assert b"\r" not in raw, "formatter pins \\n line ends"


def test_lambda_strictly_increasing_280_to_4000():
    lam = [float(r["lambda_nm"]) for r in _rows()]
    assert lam[0] == 280.0 and lam[-1] == 4000.0
    assert all(b > a for a, b in zip(lam, lam[1:])), "lambda not strictly increasing"


@pytest.mark.parametrize("lam_nm,k_spec", sorted(PINNED_K.items()))
def test_four_pinned_k_rows(lam_nm, k_spec):
    hit = [r for r in _rows() if float(r["lambda_nm"]) == lam_nm]
    assert len(hit) == 1, f"{lam_nm} nm not on the grid exactly once"
    k = float(hit[0]["k_per_m"])
    # the spec's printed digits: 5 decimals
    assert round(k, 5) == k_spec, f"k({lam_nm} nm) = {k:.5f}, spec {k_spec:.5f}"


def test_provenance_header():
    text = _text()
    for needle in (
        "trapezoid",
        "2d0ed71e1308293b3081979404f8e90f2f2dde1e",
        "md5 b31870bd3500b58414100af7e4b0e04c",
        "size 57708 B",
        "md5 cf5f76d58a31aa5f994fa038c390a856",
        "size 16514 B",
        "producer_commit:",
    ):
        assert needle in text, f"provenance header missing {needle!r}"


def test_regenerate_spectral_table():
    """Re-run the producer on the two sources; compare PARSED values at rtol 1e-12.

    A host-side formatting difference must read as a formatting defect, never as a
    table defect (round-5 audit), so this compares numbers and not bytes; the
    header's md5 is provenance, not the assertion.
    """
    for name in ("ASTMG173.csv", "iop2008.dat"):
        if not (ROOT / name).exists():
            pytest.skip(f"source {name} absent (gitignored); cannot regenerate")

    spec = importlib.util.spec_from_file_location(
        "make_spectral_table", ROOT / "tools" / "make_spectral_table.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    fresh = "".join(
        ln for ln in mod.build().splitlines(keepends=True) if not ln.startswith("#")
    )
    new = list(csv.DictReader(io.StringIO(fresh)))
    old = _rows()
    assert len(new) == len(old)
    for i, (a, b) in enumerate(zip(old, new)):
        for col in ("lambda_nm", "k_per_m", "E_AM0", "n_ph"):
            x, y = float(a[col]), float(b[col])
            assert x == pytest.approx(y, rel=1e-12, abs=0.0), (
                f"row {i} column {col}: committed {x!r} regenerated {y!r}"
            )
