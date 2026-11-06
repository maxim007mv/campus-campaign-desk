from datetime import date
from pathlib import Path

from desk_agents.logic import Board, handoff_line, plan, strip_mentions, triage

DEMO = Path(__file__).resolve().parent.parent / "demo"
TODAY = date(2026, 11, 6)


def load(name):
    return (DEMO / name).read_text()


def test_online_ctf_is_go():
    t = triage(load("01-online-ctf.md"), TODAY)
    assert t.status == "GO"
    assert t.fmt == "online"
    assert t.certificate == "yes"
    assert t.deadline_date == date(2027, 3, 12)
    assert "4" in t.team_size
    assert handoff_line(t, "desk-ops").startswith("@desk-ops please plan:")
    assert "collect the certificate" in plan(t)


def test_hybrid_hackathon_is_check():
    t = triage(load("02-hybrid-hackathon.md"), TODAY)
    assert t.status == "CHECK"
    assert t.fmt == "hybrid"
    assert t.certificate == "not stated"
    assert t.deadline_date == date(2027, 4, 15)
    p = plan(t)
    assert "Question to organisers" in p and "online" in p and "certificate" in p


def test_past_contest_is_skip():
    t = triage(load("03-past-deadline-contest.md"), TODAY)
    assert t.status == "SKIP"
    assert "deadline passed" in t.flags
    assert "certificate for finalists only" in t.flags


def test_done_only_after_human_confirmation():
    b = Board()
    t = triage(load("01-online-ctf.md"), TODAY)
    b.set(t.event, "GO, planned")
    assert b.confirm("looks good") is None
    assert b.items[t.event] == "GO, planned"
    assert b.confirm("Registered for the CTF, mark it.") == t.event
    assert "confirmed in the room" in b.items[t.event]


def test_switch_mention_prefix_is_ignored():
    raw = "@desk-triager " + load("01-online-ctf.md")
    t = triage(strip_mentions(raw), TODAY)
    assert t.event.startswith("Example Spring Online CTF")
    assert t.status == "GO"
