"""Boundary cases supplementing the supplied TODO tests."""
import numpy as np
import pytest

from avsim import core, space
from lab11 import metrics, policy, search
from test_todos import fake_rollout


def test_pedestrian_leader_and_no_leader():
    R = fake_rollout(K=2)
    e, p = core.IX["ego"], core.IX["P1"]
    R.F[:, :, e, 0] = 0
    R.F[:, :, e, 4] = 5
    R.F[:, :, p, 0] = 12.6
    R.F[:, :, p, 4] = 0
    R.EGO[0, :, 3] = p
    assert metrics.min_ttc(R) == pytest.approx([2, 10])


@pytest.mark.parametrize("dx,dz", [(2.3, 0), (-2.3, 0), (4, 1.6)])
def test_contact_thresholds_are_strict(dx, dz):
    R = fake_rollout()
    R.F[0, 0, core.IX["ego"], :4] = [0, 0, 1, 0]
    R.F[0, 0, core.IX["C2"], :4] = [dx, dz, 1, 0]
    assert metrics.contact_type(R, 0, dict(a="ego", b="C2", f=0)) == "side"


def test_equal_elite_scores_keep_earlier_rows():
    Z = np.arange(4)[:, None] * np.ones((4, space.D))
    B = np.zeros((4, space.B))
    prev = search.natural_proposal(space.Natural())
    out = search.cem_update(Z, B, np.ones(4), prev, rho=0.1, smooth=1)
    assert np.allclose(out["mean"], 0.5)
    assert out["level"] == 1
    assert np.allclose(prev["mean"], 0)  # the previous proposal is not mutated


def test_policy_tie_prefers_progress_and_accepts_loss_boundary():
    table = [dict(policy="a", fail_hi=0.1, progress=95),
             dict(policy="b", fail_hi=0.1, progress=96),
             dict(policy="c", fail_hi=0.01, progress=94)]
    assert policy.choose_policy(table, 100)["policy"] == "b"
    assert policy.choose_policy(table[:1], 100)["policy"] == "a"
    assert policy.choose_policy([], 100) is None
