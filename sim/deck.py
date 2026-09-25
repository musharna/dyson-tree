"""The gene deck (northstar design §12, M2b): a data table of cards, each moving ONE input.

A card moves an input; a card never moves an inequality. `sim/vessel.py` and
`classify_failure` do not import this module (the guard in `tests/test_deck.py` holds
that); this module imports the vessel only to build the inputs a played card hands it.

ROWS mirrors `web/deck.json` (the page's copy); `tests/test_deck.py` asserts parity.
Every row is {organism, trait, input, delta_or_range, cost, anchor, source}.

`delta_or_range`:
  op        "subtract" (input -= value) or "scale" (input *= value)
  range     [lo, hi] a single card may take
  total_cap the cap on the TOTAL across stacked cards of this row (None: no cap)
  max_stack how many copies of the card may be played

A DECLARED card applied to a registered run raises here; the page allows it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import fields, replace
from typing import TypedDict

from sim.organism import Organism
from sim.vessel import VesselInputs

ANCHORS = ("MEASURED", "DEMONSTRATED", "DECLARED")
ROW_KEYS = ("organism", "trait", "input", "delta_or_range", "cost", "anchor", "source")



class DeltaOrRange(TypedDict):
    op: str
    param: str
    unit: str
    range: list[float]
    total_cap: float | None
    max_stack: int
    clip_note: str


class Row(TypedDict):
    organism: str
    trait: str
    input: str
    delta_or_range: DeltaOrRange
    cost: str
    anchor: str
    source: str


ROWS: tuple[Row, ...] = (
    {
        "organism": "fish, insects",
        "trait": "antifreeze proteins",
        "input": "T_freeze_K",
        "delta_or_range": {
            "op": "subtract",
            "param": "dT_sc",
            "unit": "K",
            "range": [0.0, 5.0],
            "total_cap": 1.3,
            "max_stack": 3,
            "clip_note": (
                "real proteins give a few K (fish AFP ~1.5 K, insect hemolymph 5-10 K"
                " of thermal hysteresis); the TOTAL across stacked cards is clipped at"
                " 1.3 K, where the R 10 km, sigma 3.1 MPa FREEZE edge is 1.2695 AU;"
                " it leaves the registered box at 1.343 K"
            ),
        },
        "cost": (
            "protein synthesis: carbon charged to STARVE is not modelled in M2b"
            " (no cost term yet); thermal hysteresis is a non-equilibrium"
            " freezing-point depression, read here as an equilibrium T_freeze shift"
        ),
        "anchor": "DEMONSTRATED",
        "source": (
            "doi:10.1038/nbt0997-887 (Tyshenko, Doucet, Davies & Walker 1997,"
            " Nat Biotechnol 15:887-890: fish AFP thermal hysteresis ~1.5 C,"
            " insect hemolymph 5-10 C)"
        ),
    },
    {
        "organism": "none named",
        "trait": "reduced dark respiration",
        "input": "r_d",
        "delta_or_range": {
            "op": "scale",
            "param": "r_d factor",
            "unit": "",
            "range": [0.1, 0.1],
            "total_cap": None,
            "max_stack": 1,
            "clip_note": (
                "r_d to a tenth of the preset (algal 0.24 -> 0.024), never zero:"
                " respiration(0, T) = 0 would make STARVE undisplayable"
            ),
        },
        "cost": "none charged; DECLARED fantasy",
        "anchor": "DECLARED",
        "source": "DECLARED: no source",
    },
)

VESSEL_FIELDS = frozenset(f.name for f in fields(VesselInputs))
ORGANISM_FIELDS = frozenset(f.name for f in fields(Organism)) - {"cls"}


class DeclaredInRegisteredRun(ValueError):
    """A DECLARED card may not be played in a registered run (§12)."""


def input_exists(row: Row) -> bool:
    return row["input"] in VESSEL_FIELDS or row["input"] in ORGANISM_FIELDS


def row_by_trait(trait: str, rows: Sequence[Row] = ROWS) -> Row:
    for r in rows:
        if r["trait"] == trait:
            return r
    raise KeyError(trait)


def total(row: Row, values: Sequence[float]) -> tuple[float, str | None]:
    """The combined effect of playing `values` (one per card) of `row`; (total, clip)."""
    d = row["delta_or_range"]
    if len(values) > d["max_stack"]:
        raise ValueError(
            f"{row['trait']}: {len(values)} cards played, max_stack {d['max_stack']}"
        )
    lo, hi = d["range"]
    for v in values:
        if not lo <= v <= hi:
            raise ValueError(f"{row['trait']}: {v} outside the card range [{lo}, {hi}]")
    if d["op"] == "subtract":
        tot = float(sum(values))
    elif d["op"] == "scale":
        tot = 1.0
        for v in values:
            tot *= v
    else:
        raise ValueError(f"unknown op {d['op']!r}")
    cap = d["total_cap"]
    if cap is not None and tot > cap:
        return cap, f"{row['trait']}: total {tot:g} {d['unit']} clipped at {cap:g}"
    return tot, None


def reach(row: Row) -> list[float]:
    """Every total the row can reach at its edges: both card endpoints, and the max stack."""
    d = row["delta_or_range"]
    lo, hi = d["range"]
    pts = {total(row, [lo])[0], total(row, [hi])[0]}
    pts.add(total(row, [hi] * d["max_stack"])[0])
    return sorted(pts)


def apply(
    row: Row, tot: float, inputs: VesselInputs, organism: Organism
) -> tuple[VesselInputs, Organism]:
    """Move the row's ONE input by the total `tot`; returns (inputs, organism)."""
    name, op = row["input"], row["delta_or_range"]["op"]

    def moved(old: float) -> float:
        return old - tot if op == "subtract" else old * tot

    if name in VESSEL_FIELDS:
        return replace(inputs, **{name: moved(getattr(inputs, name))}), organism
    if name in ORGANISM_FIELDS:
        return inputs, replace(organism, **{name: moved(getattr(organism, name))})
    raise KeyError(f"{row['trait']}: input {name!r} does not exist")


def play(
    plays: Mapping[str, Sequence[float]],
    inputs: VesselInputs,
    organism: Organism,
    *,
    registered: bool,
    rows: Sequence[Row] = ROWS,
) -> tuple[VesselInputs, Organism, list[str]]:
    """Play {trait: [value per card]}; returns (inputs, organism, clips).

    Raises DeclaredInRegisteredRun if a DECLARED card is played with registered=True."""
    clips: list[str] = []
    for trait, values in plays.items():
        if not values:
            continue
        row = row_by_trait(trait, rows)
        if registered and row["anchor"] == "DECLARED":
            raise DeclaredInRegisteredRun(
                f"{trait} is DECLARED: it cannot be played in a registered run"
            )
        tot, clip = total(row, values)
        if clip:
            clips.append(clip)
        inputs, organism = apply(row, tot, inputs, organism)
    return inputs, organism, clips
