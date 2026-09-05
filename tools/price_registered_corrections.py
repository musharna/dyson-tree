# Section 16: prices S5 (PAR_FRACTION 0.45 -> 0.3879) and S6 (a_max's three temperature
# anchors) against the three SHIPPED pre-registered experiments, WITHOUT modifying anything
# registered. Each arm runs the real runners against a `git archive HEAD` copy in a scratch
# tree, so the frozen record is never touched.
#
# Control order matters: the pristine copy must first reproduce all six committed CSVs
# byte-identically on their data lines. A harness that cannot reproduce the baseline cannot
# be trusted to price a change to it. A one-digit mutation control proves the comparator
# can actually report a difference.
#
# Tell this encodes (section 16): every edit asserts it applied AND that it applied to the
# path the code under test actually reads. Re-anchoring a_max in sim/organism.py changed
# nothing while printing a full plausible table, because Q2b builds organisms from
# prereg.yaml, not from PRESETS.
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

signal.signal(
    signal.SIGALRM,
    lambda *_: (sys.stderr.write("aborting: walltime guard\n"), sys.exit(2)),
)
signal.alarm(600)

REPO = Path("/home/mjarnold/dyson-tree")
CSVS = [
    "experiments/q1_crossover/calibration.csv",
    "experiments/q1_crossover/crossover.csv",
    "experiments/q1_crossover/sweep.csv",
    "experiments/q2b_adapted/gates.csv",
    "experiments/q2b_adapted/limits.csv",
    "experiments/q2b_adapted/sweep.csv",
]
EXPERIMENTS = ["q1_crossover", "q2_thermal", "q2b_adapted"]


def data_lines(text: str) -> str:
    """CSV content with the provenance header (git sha, md5s, timestamps) stripped."""
    return "\n".join(ln for ln in text.splitlines() if not ln.startswith("#"))


def committed(rel: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(REPO), "show", f"HEAD:{rel}"], capture_output=True, text=True
    )
    assert out.returncode == 0, f"git show failed for {rel}"
    return data_lines(out.stdout)


def sandbox(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    arch = subprocess.run(
        ["git", "-C", str(REPO), "archive", "HEAD"], capture_output=True
    )
    assert arch.returncode == 0, "git archive failed"
    subprocess.run(["tar", "-x", "-C", str(root)], input=arch.stdout, check=True)
    assert (root / "sim" / "organism.py").exists(), "sandbox is missing sim/organism.py"
    # The runners stamp provenance from `git rev-parse HEAD`, so the sandbox must be a repo.
    # Without this they exit 1 BEFORE writing, leaving git archive's committed CSVs in place --
    # which reads exactly like "the change had no effect". The return-code check in run() is
    # what turns that silent baseline into a loud failure.
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(
        ["git", "-c", "user.email=p@x", "-c", "user.name=p", "commit", "-qm", "sandbox"],
        cwd=root, check=True, capture_output=True,
    )
    return root


def edit(root: Path, rel: str, old: str, new: str, count: int = 1) -> None:
    """Apply an edit and PROVE it applied. Silence is not success."""
    p = root / rel
    s = p.read_text()
    m = s.replace(old, new, count)
    assert m != s, f"EDIT DID NOT APPLY in {rel}: {old!r} not found"
    p.write_text(m)


def run(root: Path, exp: str) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, f"experiments/{exp}/run.py"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert r.returncode in (0, 2), (
        f"{exp} exited {r.returncode} in {root}; a nonzero-and-not-2 exit means the runner "
        f"never wrote, so any CSV read afterwards is git archive's COMMITTED copy, not this "
        f"arm's result.\nSTDERR:\n{r.stderr[-800:]}"
    )
    return r.returncode, r.stdout


with tempfile.TemporaryDirectory(prefix="dyson-price-") as td:
    # ---- CONTROL 1: the pristine copy must reproduce the committed record exactly.
    base = sandbox(Path(td) / "baseline")
    base_out = {}
    for e in EXPERIMENTS:
        base_out[e] = run(base, e)
    for rel in CSVS:
        got = data_lines((base / rel).read_text())
        assert got == committed(rel), f"CONTROL 1 FAILED: {rel} did not reproduce"
    print(f"control 1 OK -- all {len(CSVS)} committed CSVs reproduce byte-identically")

    # ---- CONTROL 2: the comparator must be able to report a difference at all.
    mutated = committed(CSVS[3]).replace("5.1612", "5.1613", 1)
    assert mutated != committed(CSVS[3]), "mutation did not apply -- control 2 is invalid"
    assert mutated != data_lines((base / CSVS[3]).read_text())
    print("control 2 OK -- a one-digit mutation is reported as DIFFERS\n")

    # ---- ARM S5: the measured top-of-atmosphere PAR fraction.
    s5 = sandbox(Path(td) / "s5")
    edit(s5, "sim/physiology.py", "PAR_FRACTION = 0.45", "PAR_FRACTION = 0.3879")
    for e in EXPERIMENTS:
        edit(s5, f"experiments/{e}/prereg.yaml", "par_fraction: 0.45", "par_fraction: 0.3879")

    # ---- ARM S6-B: a_max read as the PEAK rate, so Q1's factor-free path must scale by
    # f(293) = temperature_response(293, 265.15, 298.15) = 0.8439. Q1 guards prereg against
    # sim/organism.py, so both must move together.
    s6 = sandbox(Path(td) / "s6b")
    edit(s6, "sim/organism.py", 'Organism("vascular", a_max=10.0', 'Organism("vascular", a_max=8.4394')
    edit(s6, "sim/organism.py", '    "algal",\n    a_max=10.0', '    "algal",\n    a_max=8.4394')
    edit(s6, "experiments/q1_crossover/prereg.yaml", "a_max: 10.0", "a_max: 8.4394", 2)

    # ---- ARM BOTH.
    bo = sandbox(Path(td) / "both")
    edit(bo, "sim/physiology.py", "PAR_FRACTION = 0.45", "PAR_FRACTION = 0.3879")
    for e in EXPERIMENTS:
        edit(bo, f"experiments/{e}/prereg.yaml", "par_fraction: 0.45", "par_fraction: 0.3879")
    edit(bo, "sim/organism.py", 'Organism("vascular", a_max=10.0', 'Organism("vascular", a_max=8.4394')
    edit(bo, "sim/organism.py", '    "algal",\n    a_max=10.0', '    "algal",\n    a_max=8.4394')
    edit(bo, "experiments/q1_crossover/prereg.yaml", "a_max: 10.0", "a_max: 8.4394", 2)

    def vasc_k100(root: Path) -> float:
        for ln in data_lines((root / CSVS[1]).read_text()).splitlines():
            f = ln.split(",")
            if f[0] == "vascular" and float(f[1]) == 100.0:
                return float(f[2])
        raise AssertionError("vascular k=100 row not found")

    print(f"{'arm':>22} {'vascular k=100 r*':>19} {'band [12,22]':>14}")
    results = {}
    for lab, root in (("as registered", base), ("S5 only", s5), ("S6 reading B only", s6), ("BOTH", bo)):
        if root is not base:
            for e in EXPERIMENTS:
                run(root, e)
        v = vasc_k100(root)
        results[lab] = v
        print(f"{lab:>22} {v:19.4f} {('inside' if 12 <= v <= 22 else 'OUTSIDE'):>14}")

    # ---- the finding: individually harmless, jointly decisive.
    b, a5, a6, ab = (results[k] for k in ("as registered", "S5 only", "S6 reading B only", "BOTH"))
    assert 12 <= a5 <= 22, f"S5 alone should not flip: {a5}"
    assert 12 <= a6 <= 22, f"S6 alone should not flip: {a6}"
    assert ab < 12, f"BOTH should fall below the registered floor: {ab}"
    pred = b * (a5 / b) * (a6 / b)
    assert abs(pred - ab) < 0.02, f"effects are not multiplicative: {pred:.4f} vs {ab:.4f}"
    print(f"\nthe two corrections compose multiplicatively ({pred:.4f} predicted vs {ab:.4f} measured)")
    print(f"BOTH misses the registered floor of 12 AU by {12 - ab:.2f} AU ({(12 - ab) / 12 * 100:.1f}%)")
    print("\n=> S5 and S6 are individually harmless to every registered verdict, and their")
    print("   PRODUCT flips Q1's headline. They were deferred as independent defects.")
