# Why the adaptation premise is retired, and why the pressure vessel is not optional

Analysis note, 2026-09-03. No new registered question; nothing here edits a frozen
pre-registration. Written after Q2b shipped, because the reason its gate behaved as it
did turns out to invalidate the gate rather than the organism.

## 1. Gate B compared two different kinds of temperature

Q2b's Gate B compared a model-predicted optimum against a measured one:

- **Predicted:** `T_eq(1 AU, geometry)` — the temperature of a body in **vacuum** whose
  only heat exchange is radiative.
- **Measured:** the photosynthetic optimum of **terrestrial** organisms — Colesie et al.
  2014's Antarctic soil crusts (5, 7 °C) and Scafaro et al. 2023's cool-grown C3 plants
  (29.4 °C).

Terrestrial tissue temperature is not set by radiation alone. It is set by radiation plus
conduction to substrate, convection through an atmosphere, and evaporative loss. The scale
of the difference is not subtle: **Earth's own blackbody equilibrium temperature is −18 °C
while its mean surface temperature is about +15 °C.** That 33 K gap _is_ the non-radiative
physics.

So Gate B asked whether a vacuum-radiative temperature matches an Earth-thermodynamic one.
There is no reason it should, and the gate could not have been informative either way.
**This is a design error in `docs/superpowers/specs/2026-09-02-q2b-adapted-optimum-design.md`,
not a property of the organisms.**

It also explains Q2b's pattern better than the explanation shipped in its RESULTS.md. Every
class fails under its own honest geometry (algal crust at ratio 1 → 120.44 °C, at ratio 2 →
57.82 °C, vascular lamina → 57.82 °C, all against windows of [0, 12] and [24.4, 34.4] °C).
The single pass came from modelling a flat soil crust as a sphere. That was a coincidence,
not a signal.

## 2. There is no measurement to recalibrate against

The obvious repair is to compare against organisms whose temperature genuinely IS
radiatively set — vacuum-exposed. Lichens have been flown on ISS exposure facilities
(ESA's BIOMEX on EXPOSE-R2; de Vera et al. 2019, _Astrobiology_ 19:145,
doi:10.1089/ast.2018.1897). But those experiments report, in the paper's own framing,
_"analysis on the viability of the investigated organisms"_ after exposure — assays run
post-return, on Earth. A photosynthetic temperature optimum measured that way is another
Earth optimum.

That is not an accident of experimental design. See §3.

## 3. The reason no such measurement exists: liquid water

An organism at free radiative equilibrium in vacuum cannot photosynthesise at all, because
it cannot hold liquid water. Saturation vapour pressure (Buck equation) at each modelled
temperature, against an ambient of effectively zero:

| modelled body             | T_eq at 1 AU | P_sat      |
| ------------------------- | ------------ | ---------- |
| algal sphere (ratio 4)    | 5.16 °C      | 882 Pa     |
| vascular lamina (ratio 2) | 57.82 °C     | 18,017 Pa  |
| crust mat (ratio 1)       | 120.44 °C    | 200,686 Pa |

Water boils when its saturation pressure exceeds ambient. In vacuum, all three lose water
immediately. There is no liquid phase, so there is no photosynthesis, so there is no
optimum to measure and none to adapt.

## 4. What that means for the project

**The pressure vessel is a precondition, not an extension.** Q1's spec listed it under "Out
of scope (v1)" and every question since has inherited that deferral. But Q1, Q2 and Q2b all
model photosynthesis proceeding at a vacuum equilibrium temperature — which requires
containment holding enough pressure for liquid water, which is the deferred item.

The carbon numbers those questions produced are not wrong arithmetic. They are arithmetic
about an organism that, as modelled, has no liquid water to run the arithmetic with.

This reframes the backlog. "Insulation / pressure vessel" has been ranked third or fourth on
the roadmap since Q1. It is first, and it is not optional:

- What containment holds liquid water at distance r?
- What does that containment cost in carbon, mass, and absorbed light?
- Does a contained organism's temperature still follow `T_eq`, or does the vessel set it?

The third of those is the one that decides whether any of the existing thermal model
survives into the next question.

## 5. Status of the three shipped questions

Nothing is retracted. Q1, Q2 and Q2b remain reproducible, their records byte-identical, and
their pre-registrations frozen. What changes is the reading:

- **Q1** measured a carbon crossover at fixed tissue temperature. Still arithmetically
  correct; the temperature it holds fixed is unattainable without containment.
- **Q2** registered a gate that failed and reported no limits. That failure stands, and the
  grounding that followed it (`docs/bio_grounding_2026-09-02.md` §4d) stands.

  > ⚠️ **NARROWED 2026-09-10 (release 1.0).** The bullet below says the Q2b
  > falsification is unaffected by this note. That is true **within the algal
  > class**, which is the only class Q2b answered — but retiring Gate B readmits the
  > vascular class, and running Q2b's own `classify_limit` there gives `carbon` as
  > the binding limit at Ω = 25 and Ω = 30, where the registered prediction would
  > have HELD. The falsification stands for algal; whether it generalises is open.
  > Superseded text is bannered, not rewritten. See `docs/FINDINGS.md`.

- **Q2b** registered a prediction that was falsified. **The falsification itself is not
  affected by this note** ⚠️ _scoped → true for the **algal** class only; retiring Gate B
  readmits vascular, where carbon binds at Ω = 25, 30 (see the banner above and
  `docs/FINDINGS.md`)_ — it compared the thermal floor against the carbon crossing, both
  computed inside the model, and `temperature` won at every Ω regardless of whether Gate B
  was meaningful. What this note retires is Gate B, not the Q2b result.

## Method note

Every number here was computed this session against the live `sim/` code or from the Buck
equation, not recalled. The BIOMEX characterisation rests on that paper's abstract, which was
read; its exposure protocol was not read in full, so §2 claims only what the abstract states.
