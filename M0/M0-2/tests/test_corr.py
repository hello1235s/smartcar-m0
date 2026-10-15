import sys
import subprocess
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


def test_cli_resolves_csv_from_config_directory(tmp_path):
    inputs = tmp_path / 'inputs'
    inputs.mkdir()
    (inputs / 'new.csv').write_text('left,right\n10,30\n20,20\n30,10\n')
    (inputs / 'new.yaml').write_text('input_csv: new.csv\ncolumns: {x: left, y: right}\n')
    script = Path(__file__).resolve().parents[1] / 'corr_tool.py'
    for config in ('inputs/new.yaml', str(inputs / 'new.yaml')):
        run = subprocess.run([sys.executable, str(script), '--config', config],
                             cwd=tmp_path, text=True, capture_output=True)
        assert run.returncode == 0, run.stderr
        assert 'r = -1' in run.stdout
        assert 'n = 3' in run.stdout


def test_cli_missing_file_exits_nonzero_without_traceback(tmp_path):
    script = Path(__file__).resolve().parents[1] / 'corr_tool.py'
    run = subprocess.run([sys.executable, str(script), '--config', 'not-found.yaml'],
                         cwd=tmp_path, text=True, capture_output=True)
    assert run.returncode != 0
    assert '错误' in run.stderr and 'Traceback' not in run.stderr


def test_import_does_not_read_files_or_print(tmp_path):
    folder = Path(__file__).resolve().parents[1]
    run = subprocess.run([sys.executable, '-c',
                          f'import sys; sys.path.insert(0, {str(folder)!r}); import corr_tool'],
                         cwd=tmp_path, text=True, capture_output=True)
    assert run.returncode == 0 and run.stdout == '' and run.stderr == ''


def test_large_numbers_avoid_original_product_overflow():
    assert pearson([1e150, 2e150, 3e150], [6e150, 4e150, 2e150]) == pytest.approx(-1.0)
