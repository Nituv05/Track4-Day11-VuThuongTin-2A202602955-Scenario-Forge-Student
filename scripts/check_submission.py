"""Check that the submitted artifacts form a consistent, full-budget lab run."""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from avsim import core, space, studio
from lab11 import policy


def read(name):
    return json.loads((ROOT / "evidence" / f"{name}.json").read_text())


def check():
    report = (ROOT / "REPORT.md").read_text()
    sid = report.splitlines()[0].split(":", 1)[1].strip()
    assert sid == "202602955"
    nat, seeds = space.student_variant(sid)
    meta = read("meta")
    assert meta["seeds"] == seeds
    expected_steps = {"world", "replay", "mc", "hunt", "estimate", "fix", "mine", "export"}
    assert expected_steps <= meta["steps"].keys()
    assert all(not meta["steps"][step]["quick"] for step in expected_steps)
    for name in ("world", "replay", "mc", "hunt", "estimate", "fix", "mine"):
        run = read(name)["_run"]
        assert run["mssv"] == sid and run["town"] == nat.name
        assert not run["quick"] and not run["salted"]

    mc = read("mc")
    assert mc["n"] == 3000 and mc["crashes"] == sum(mc["modes"].values())
    assert mc["lo"] <= mc["p"] <= mc["hi"]
    hunts = read("hunt")
    for mode in ("bus_bypass", "crosswalk_block"):
        assert hunts[mode]["found"].get(mode, 0) > 0
    cloud = read("cloud")
    assert len(cloud) == 4 * 8 * 300
    assert all(c["out"] in {"safe", "near", "crash", "infeasible"} for c in cloud)

    est = read("estimate")
    assert len(est["seeds"]) == 3 and est["budget"] == 16800
    assert est["other"]["k"] == mc["modes"].get("other", 0)
    for seed in est["seeds"]:
        assert abs(seed["total"] - sum(v["p"] for v in seed["per"].values()) - est["other"]["p"]) < 1e-12
        for v in seed["per"].values():
            assert v["n"] == 600 and 0 <= v["top_share"] <= 1
            if v["hits"] == 0:
                assert v["upper_zero_hits"] == 3 / (0.2 * v["n"])

    fx = read("fix")
    assert fx["chosen"] == policy.choose_policy(fx["table"], fx["baseline_train"]["progress"])
    assert fx["chosen"]["progress"] >= 0.95 * fx["baseline_train"]["progress"]
    for name in ("chosen_test", "baseline_test"):
        assert fx[name]["other_crashes"]["n"] == 3000
        assert fx[name]["fail_hi"] >= fx[name]["fail_hi_seen"]

    doc = studio.load(ROOT / "hazard.json")
    assert not studio.check_space(doc) and studio.hazard_ok(doc["hazards"], doc["params"])
    assert doc["why"] and 0 < doc["exposure"] <= 1
    mine = read("mine")
    assert mine["accepted"] >= 0.5 and mine["world"] == "town"
    assert mine["exposure"] == doc["exposure"] and mine["space"] == doc["space"]
    R = core.rollout(doc["params"], policy=doc["policy"], hazards=doc["hazards"])
    assert (R.fire >= 0).all(), "The exact hazard must actually trigger"
    assert mine["exact"]["planner"] == [[e["a"], e["b"], e["t"]] for e in R.events[0]]
    for name in ("baseline", "chosen"):
        v = mine[name]
        assert v["crashes"] == v["avoidable"] + v["unavoidable"] + v["unattributed"]
        assert v["lo"] <= v["p"] <= v["hi"]
        assert abs(v["per_trip"] - doc["exposure"] * v["p"]) < 1e-12

    viewer = read("viewer")
    assert viewer["format"] == "avsim-viewer/1" and viewer["policy"] == fx["chosen"]["policy"]
    assert len(viewer["cloud"]["rows"]) == 6000
    manifest = json.loads((ROOT / "evidence/shots/manifest.json").read_text())
    assert len(manifest) == 5
    for shot in manifest:
        assert (ROOT / "evidence/shots" / shot["file"]).stat().st_size > 10000
    assert len(re.findall(r"^## [1-9]\.", report, flags=re.M)) == 9
    for target in re.findall(r"!\[[^]]*\]\(([^)]+)\)", report):
        assert (ROOT / target).is_file(), f"Missing report image: {target}"
    print("PASS: full budgets, provenance, estimates, TRAIN selection, hazard replay, screenshots and report structure.")


if __name__ == "__main__":
    check()
