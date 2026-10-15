import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corr_tool import pearson


@pytest.mark.parametrize("xs,ys,expected", [
    ([1, 2, 3], [2, 4, 6], 1.0),
    ([1, 2, 3], [6, 4, 2], -1.0),
    ([1, 0, -1, 0], [0, 1, 0, -1], 0.0),
])
def test_known_correlation(xs, ys, expected):
    assert pearson(xs, ys) == pytest.approx(expected, abs=1e-12)


def test_matches_numpy_for_new_data():
    rng = np.random.default_rng(20261015)
    xs = rng.normal(5, 20, 257)
    ys = 0.3 * xs + rng.normal(0, 10, 257)
    assert pearson(list(xs), list(ys)) == pytest.approx(np.corrcoef(xs, ys)[0, 1], abs=1e-6)
