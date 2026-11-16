import sys
import json
import time
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'M5/common'),str(ROOT/'M5/M5-3')]
from audit import Audit,verify
from referee_bridge import Referee


def test_hash_chain_detects_tampering(tmp_path):
    path=tmp_path/'audit.jsonl'; audit=Audit(path); audit.append('A'); audit.append('B'); assert verify(path)['valid']
    text=path.read_text().replace('"action": "A"','"action": "X"'); path.write_text(text)
    assert not verify(path)['valid']
    with pytest.raises(ValueError): Audit(path)


def test_pause_resume_time_and_penalty(monkeypatch):
    now=[0.]; monkeypatch.setattr(time,'monotonic',lambda:now[0]); actions=[]; r=Referee(lambda *a:actions.append(a))
    r.command('START'); now[0]=3.1; r.tick(); assert r.state=='RUNNING'
    now[0]=13.1; r.command('PAUSE'); frozen=r.snapshot()['remaining_s']; now[0]=30
    assert r.snapshot()['remaining_s']==frozen
    r.command('PENALTY',seconds=5); r.command('RESUME'); now[0]=32; r.command('STOP')
    assert r.snapshot()['remaining_s']==pytest.approx(163.)
    assert [a[0] for a in actions]==['start','pause','resume','stop']


def test_countdown_expiry_stops_without_referee_stop(monkeypatch):
    now=[0.]; monkeypatch.setattr(time,'monotonic',lambda:now[0]); actions=[]; r=Referee(lambda *a:actions.append(a))
    r.command('START'); now[0]=4; r.tick(); now[0]=185; r.tick(); assert r.state=='STOPPED'; assert actions[-1]==('stop','countdown_expired')


def test_invalid_protocol_does_not_change_state():
    r=Referee(lambda *a:None)
    for action in ['PAUSE','RESUME','BAD']:
        with pytest.raises(ValueError): r.command(action)
        assert r.state=='READY'


def test_fault_does_not_silently_end_competition(monkeypatch):
    now=[0.]; monkeypatch.setattr(time,'monotonic',lambda:now[0]); r=Referee(lambda *a:None)
    r.command('START'); now[0]=4; r.tick(); r.state='FAULT'
    assert r.snapshot()['competition_active'] is True
    r.command('STOP'); assert r.snapshot()['competition_active'] is False
