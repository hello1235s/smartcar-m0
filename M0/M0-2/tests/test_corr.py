import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from corr_tool import analyze, main, pearson


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


@pytest.mark.parametrize("xs,ys", [([], []), ([1], [2]), ([1, 2], [1]),
    ([2, 2], [3, 4]), ([1, 2], [4, 4]), ([1, float('nan')], [2, 3]),
    ([1, float('inf')], [2, 3])])
def test_rejects_undefined_correlations(xs, ys):
    with pytest.raises(ValueError):
        pearson(xs, ys)


@pytest.mark.parametrize("content", ['', 'a,c\n1,2\n', 'a,b\n',
    'a,b\n1,hello\n', 'a,b\n1\n', 'a,b\n1,2,3\n', 'a,a\n1,2\n'])
def test_invalid_csv_returns_readable_error(tmp_path, capsys, content):
    (tmp_path / 'data.csv').write_text(content)
    config = tmp_path / 'cfg.yaml'
    config.write_text('input_csv: data.csv\ncolumns: {x: a, y: b}\n')
    assert main(['--config', str(config)]) != 0
    error = capsys.readouterr().err
    assert '错误' in error and 'Traceback' not in error


@pytest.mark.parametrize("content", ['', '[]', 'columns: {x: a, y: b}',
    'input_csv: data.csv\ncolumns: {}', 'input_csv: [',
    'input_csv: absent.csv\ncolumns: {x: a, y: b}'])
def test_invalid_config_returns_error(tmp_path, capsys, content):
    config = tmp_path / 'cfg.yaml'
    config.write_text(content)
    assert main(['--config', str(config)]) != 0
    assert 'Traceback' not in capsys.readouterr().err
