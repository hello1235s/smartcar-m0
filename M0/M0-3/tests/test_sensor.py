import csv
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sensor_analyzer import analyze, clean_records, main


def test_sample_matches_independent_numpy_reference(tmp_path):
    sample = Path(__file__).resolve().parents[1] / 'sensor_data.csv'
    with sample.open() as stream:
        records = [(float(r['time']), float(r['value'])) for r in csv.DictReader(stream)]
    values = np.array([v for _, v in records])
    expected = [r for r in records if abs(r[1] - values.mean()) <= 2 * values.std(ddof=0)]
    count, mean, std, cleaned = analyze(sample, tmp_path / 'clean.csv')
    assert count == 60
    assert mean == pytest.approx(values.mean(), abs=1e-10)
    assert std == pytest.approx(values.std(ddof=0), abs=1e-10)
    assert cleaned == expected
    with (tmp_path / 'clean.csv').open() as stream:
        rows = list(csv.reader(stream))
    assert rows[0] == ['time', 'value']
    assert len(rows) == len(expected) + 1
    assert all(len(row) == 2 for row in rows)


def test_adjacent_outliers_both_sides_and_time_alignment():
    records = [(i, 0.0) for i in range(20)] + [(20, 100), (21, 100), (22, -100), (23, -100)]
    before = records[:]
    _, _, cleaned = clean_records(records)
    assert cleaned == before[:20]
    assert records == before


@pytest.mark.parametrize('records', [[(3, 8)], [(1, 5), (2, 5), (3, 5)]])
def test_zero_std_preserves_all_rows(records):
    _, std, cleaned = clean_records(records)
    assert std == 0 and cleaned == records


@pytest.mark.parametrize('content', ['', 'time,value\n', 'time,Value\n0,1\n',
    'time,value\n0,text\n', 'time,value\n0,\n', 'time,value\n0,nan\n',
    'time,value\ninf,1\n', 'time,value\n0\n', 'time,value\n0,1,extra\n',
    'time,value,value\n0,1,2\n'])
def test_invalid_input_is_readable(tmp_path, capsys, content):
    source = tmp_path / 'invalid.csv'
    source.write_text(content)
    assert main(['--input', str(source), '--output', str(tmp_path / 'out.csv')]) != 0
    assert not (tmp_path / 'out.csv').exists()
    assert 'Traceback' not in capsys.readouterr().err


def test_input_not_overwritten(tmp_path):
    source = tmp_path / 'data.csv'
    source.write_text('time,value\n0,5\n')
    with pytest.raises(ValueError):
        analyze(source, source)
    assert source.read_text() == 'time,value\n0,5\n'


def test_cli_default_and_explicit_contract(tmp_path):
    source = tmp_path / 'sensor_data.csv'
    source.write_text('time,value\n3,10\n4,20\n5,30\n')
    script = Path(__file__).resolve().parents[1] / 'sensor_analyzer.py'
    for options in ([], ['--input', str(source), '--output', 'cleaned_data.csv']):
        run = subprocess.run([sys.executable, str(script), *options], cwd=tmp_path,
                             capture_output=True, text=True)
        assert run.returncode == 0, run.stderr
        assert 'mean = 20' in run.stdout and 'std =' in run.stdout
        with (tmp_path / 'cleaned_data.csv').open() as stream:
            rows = list(csv.DictReader(stream))
        assert [float(r['time']) for r in rows] == [3, 4, 5]


def test_missing_file_exits_without_traceback(tmp_path):
    script = Path(__file__).resolve().parents[1] / 'sensor_analyzer.py'
    run = subprocess.run([sys.executable, str(script), '--input', 'missing.csv'],
                         cwd=tmp_path, capture_output=True, text=True)
    assert run.returncode != 0 and '错误' in run.stderr and 'Traceback' not in run.stderr
