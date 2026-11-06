"""Pure, deterministic workflow logic. No network, easy to test."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], 1)}
_MON = "(" + "|".join(MONTHS) + ")"
_DATE = re.compile(rf"(\d{{1,2}})(?:\s*[-–]\s*(\d{{1,2}}))?\s+{_MON}(?:\s+(\d{{4}}))?", re.I)
_DATE_RANGE_MON = re.compile(rf"(\d{{1,2}})\s*[-–]\s*(\d{{1,2}})\s+{_MON}", re.I)
_YEAR = re.compile(r"\b(20\d\d)\b")
CONFIRM = re.compile(r"\b(registered|submitted|done|joined)\b", re.I)


@dataclass
class Triage:
    event: str
    dates: str
    fmt: str
    format_note: str
    certificate: str
    certificate_quote: str
    deadline: str
    deadline_date: date | None
    team_size: str
    action: str
    status: str = ""
    reason: str = ""
    flags: list[str] = field(default_factory=list)


def _sentences(text: str) -> list[str]:
    paras = [" ".join(p.split()) for p in re.split(r"\n\s*\n", text)]
    out = []
    for i, p in enumerate(paras):
        parts = [p] if i == 0 else re.split(r"(?<=[.!?])\s+", p)
        out += [x.strip() for x in parts if x.strip()]
    return out


def _event_name(text: str) -> str:
    for line in text.splitlines():
        line = re.sub(r"\(.*?\)|^(fwd|fw):", "", line.strip(), flags=re.I).strip(" :-\"")
        if not line:
            continue
        m = re.match(r"([A-Z][\w&]*(?:\s+[A-Z0-9][\w&]*)*)", line)
        if m and len(m.group(1).split()) >= 2:
            return m.group(1)
        if "hackathon" in line.lower() or "ctf" in line.lower():
            continue
        return line[:60]
    return "not stated"


def _year(text: str) -> int | None:
    m = _YEAR.search(text)
    return int(m.group(1)) if m else None


def _first_date(s: str, year: int | None) -> date | None:
    m = _DATE.search(s)
    if not m:
        return None
    y = int(m.group(4)) if m.group(4) else year
    if not y:
        return None
    return date(y, MONTHS[m.group(3).lower()], int(m.group(1)))


def triage(text: str, today: date) -> Triage:
    low = text.lower()
    sents = _sentences(text)
    year = _year(text)

    # Dates: first sentence that carries a date.
    dates = next((s for s in sents if _DATE.search(s) or _DATE_RANGE_MON.search(s)), "not stated")

    # Format.
    online = bool(re.search(r"\bonline\b|remote", low))
    offline = bool(re.search(r"on-site|onsite|in person|in-person|tech park|venue|offline", low))
    if online and offline:
        fmt = "hybrid"
    elif offline:
        fmt = "offline"
    elif online:
        fmt = "online"
    else:
        fmt = "not stated"
    in_person_bits = [s for s in sents if re.search(r"on-site|onsite|in person|tech park|venue", s, re.I)]
    format_note = "; ".join(in_person_bits)

    # Certificate.
    cert_s = next((s for s in sents if "certificate" in s.lower()), "")
    if not cert_s:
        certificate = "not stated"
    elif re.search(r"\bno\b.*certificate|not sure|no idea", cert_s, re.I):
        certificate = "not stated"
    elif re.search(r"finalists only|only .*finalist|to finalists", cert_s, re.I):
        certificate = "finalists only"
    else:
        certificate = "yes"

    # Deadline: registration sentence first, else event start.
    reg = next((s for s in sents if re.search(r"regist", s, re.I)), "")
    deadline_date = _first_date(reg, year) if reg else None
    if deadline_date is None:
        deadline_date = _first_date(dates, year) if dates != "not stated" else None
        if deadline_date is None and dates != "not stated":
            m = _DATE_RANGE_MON.search(dates)
            if m and year:
                deadline_date = date(year, MONTHS[m.group(3).lower()], int(m.group(1)))
    deadline = reg or (f"event start {deadline_date.isoformat()}" if deadline_date else "not stated")
    closed = bool(re.search(r"registration closed|closes? when the event starts", reg, re.I)) and "closed" in reg.lower()

    m = re.search(r"teams?\s+(?:of\s+)?(?:up to\s+)?(\d+(?:\s*[-–]\s*\d+)?)\s*(?:ppl|people|members)?", low)
    team_size = m.group(0) if m else ("individual" if "individual" in low else "not stated")

    t = Triage(_event_name(text), dates, fmt, format_note, certificate, cert_s,
               deadline, deadline_date, team_size, action="register")

    # Classification.
    if fmt == "offline":
        t.flags.append("offline only")
    if deadline_date and deadline_date < today:
        t.flags.append("deadline passed")
    if closed:
        t.flags.append("registration closed")
    if certificate == "finalists only":
        t.flags.append("certificate for finalists only")
    if t.flags:
        t.status, t.action = "SKIP", "skip"
        t.reason = ", ".join(t.flags)
    elif fmt == "online" and certificate == "yes":
        t.status, t.reason = "GO", "fully online, certificate for participants, deadline reachable"
    else:
        missing = []
        if certificate != "yes":
            missing.append("certificate terms not stated")
        if fmt != "online":
            missing.append(f"format is {fmt}" + (f" ({format_note})" if format_note else ""))
        t.status, t.action = "CHECK", "ask organisers"
        t.reason = "; ".join(missing)
    return t


def render_triage(t: Triage, text: str) -> str:
    first = _sentences(text)[0] if text.strip() else ""
    lines = [
        f"**{t.event}**: {first}",
        f"- Event: {t.event}",
        f"- Dates: {t.dates}",
        f"- Format: {t.fmt}" + (f" (in-person part: {t.format_note})" if t.format_note else ""),
        f"- Certificate: {t.certificate}" + (f' ("{t.certificate_quote}")' if t.certificate_quote else ""),
        f"- Deadline that matters next: {t.deadline}",
        f"- Team size: {t.team_size}",
        f"- Needed action: {t.action}",
        f"**{t.status}**: {t.reason}.",
    ]
    return "\n".join(lines)


def handoff_line(t: Triage, ops_name: str) -> str:
    when = t.deadline_date.isoformat() if t.deadline_date else "the deadline (not stated)"
    return f"@{ops_name} please plan: {t.event} - {t.action} by {when}"


def plan(t: Triage) -> str:
    when = t.deadline_date.isoformat() if t.deadline_date else "<deadline>"
    if t.status == "CHECK":
        steps = [
            ("captain", "today", "send the organiser question below"),
            ("captain", "on reply", "re-paste the answer here for a new triage"),
            ("member", "before " + when, "prepare team names and roles"),
        ]
    else:
        steps = [
            ("captain", "before " + when, "register the team on the event site"),
            ("member", "before " + when, "join the event chat / platform"),
            ("anyone", "day 1", "read rules and pick tasks"),
            ("anyone", "during event", "submit work and keep proof"),
            ("captain", "after event", "collect the certificate"),
        ]
    out = [f"Plan for **{t.event}** ({t.status}):"]
    out += [f"{i}. [ ] {what} - {who}, {by}" for i, (who, by, what) in enumerate(steps, 1)]
    if t.status == "CHECK":
        q = []
        if "certificate" in t.reason:
            q.append("whether every participant receives a participation certificate")
        if "format" in t.reason:
            q.append("whether the whole event, including kickoff and finals, can be done online")
        out.append("Question to organisers: Hello! Our student team is interested in "
                   f"{t.event}. Could you please confirm " + " and ".join(q) + "? Thank you!")
    out.append(f"Team message draft: <captain> here. {t.event}: {t.status}. "
               f"Next step: {steps[0][2]} by {when}. Reply 'registered' here when done.")
    return "\n".join(out)


class Board:
    """Running list of open events kept by the agents."""

    def __init__(self) -> None:
        self.items: dict[str, str] = {}

    def set(self, event: str, status: str) -> None:
        self.items[event] = status

    def confirm(self, text: str) -> str | None:
        """Mark an item done only when a person says so explicitly."""
        m = CONFIRM.search(text)
        if not m:
            return None
        for name in self.items:
            words = [w for w in re.findall(r"[a-z0-9]+", name.lower()) if len(w) > 2]
            if any(w in text.lower() for w in words):
                self.items[name] = f"{m.group(1).lower()} (confirmed in the room)"
                return name
        return None

    def render(self) -> str:
        if not self.items:
            return "Open events: none"
        return "Open events:\n" + "\n".join(f"{i}. {k}: {v}" for i, (k, v) in enumerate(self.items.items(), 1))


def strip_mentions(text: str) -> str:
    """Drop the leading @name mentions Switch prepends to addressed messages."""
    return re.sub(r"^(\s*@[a-z0-9][a-z0-9._-]*[,:]?\s*)+", "", text)
