# Blind 10-second test — visual-first page (2026-09-25)

Plan: `docs/superpowers/plans/2026-09-25-visual-first-dyson.md`, Task 5 step 3.

Each screenshot (1400×900, viewport only) went to a separate fresh agent with only:
"In one sentence each: what is being tested, and what is the current result?"
The file was renamed `page.png` in both cases so the name gave nothing away.

## Before — live page (musharna.github.io/dyson-tree, pre-merge)

1. Tests whether an ice-sphere "Dyson tree" vessel holding a photosynthetic
   organism in vacuum stays alive, by checking five sequential inequalities
   (burst, freeze, boil, starve, opaque) against the slider/dropdown inputs.
2. With the current settings (radius 1.000 km, auto wall 1.400 m, auto pressure
   1960.5 Pa, distance 1.100 AU, algal organism) the vessel is "alive: every
   line holds", with all five checks passing (BURST and BOIL at exactly 0 Pa
   margin, since the auto-design sits on those limits).

Confidence: 1 high, 2 high.

## After — new build at defaults (branch `visual`, before the critic rounds)

1. Tests whether a vacuum-grown photosynthetic "vessel" (Dyson tree) can
   survive, mapping which structural line (burst, freeze, or opaque) fails first
   as a function of distance from the sun (AU) and vessel radius (km) for an
   algal design at σ 0.7 MPa.
2. The current design (~1.1 AU, 1 km radius) holds — "alive: every line holds"
   — with only a thin green band near ~1–1.3 AU surviving (anything closer
   bursts, farther freezes); the pre-registered P1 and P2 bands are labelled
   HELD and the measured r_close is 1.2049 AU.

Confidence: 1 medium, 2 high.

## Verdict: PASS

The new page's reader names the test and the result correctly, and also reads
the landscape (where the vessel works, what kills it on each side) and the
registered results from the first screen; the old page's reader gets the
result but not where it holds. The one weakness — the new reader named only the
three lines visible on the map — was fixed afterwards with an always-visible
"checked in order: BURST → FREEZE → BOIL → STARVE → OPAQUE" legend line, and
the "HELD" wording on registered labels (which critic round 1 showed reads as
"your design survives") became "prediction … confirmed".
