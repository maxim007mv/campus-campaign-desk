"""Run desk-triager and desk-ops as custom Switch protocol agents.

  python -m desk_agents.run_agents --room <room_id>          # join an existing room
  python -m desk_agents.run_agents --create-room             # create desk-campaign-desk
  python -m desk_agents.run_agents --create-room --demo      # also feed demo/*.md via a
                                                             # scripted feeder agent
Reads SWITCH_URL and SWITCH_REGISTRATION_KEY from the environment / .env.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from datetime import date
from pathlib import Path

from .logic import Board, strip_mentions, handoff_line, plan, render_triage, triage
from .switch_client import Agent, register

TRIAGER, OPS, FEEDER = "desk-triager", "desk-ops", "desk-demo-feeder"
ROOT = Path(__file__).resolve().parent.parent


def load_env() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--room")
    ap.add_argument("--create-room", action="store_true")
    ap.add_argument("--internal", action="store_true", help="agent-only room, no chat bridge")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--log", default="")
    a = ap.parse_args()
    load_env()
    base = os.environ.get("SWITCH_URL", "http://localhost:8000").rstrip("/")
    key = os.environ["SWITCH_REGISTRATION_KEY"]

    names = [TRIAGER, OPS] + ([FEEDER] if a.demo else [])
    desc = {TRIAGER: "Triages pasted event announcements", OPS: "Turns triage into checklists",
            FEEDER: "Scripted demo feeder that pastes demo/*.md (stands in for a person)"}
    agents = {n: Agent(base, n, register(base, key, n, desc[n])) for n in names}
    for n in (TRIAGER, OPS):
      try:
        await agents[n].op("update_agent_detail", agent_id=agents[n].id,
                           addressing="anyone" if n == TRIAGER else "owner_and_owner_agents")
      except RuntimeError as e:  # Switch 0.31 lets only the owner change this
        print("note: addressing not changed:", str(e)[:160])

    room = a.room
    if a.create_room:
        res = await agents[TRIAGER].op("create_room", name="desk-campaign-desk",
                                       description="Event triage and planning for a student competition team",
                                       agent_names=names, internal_only=a.internal)
        room = res.get("room_id") or res.get("id")
        print("room:", json.dumps(res)[:300])
    board = Board()
    log: list[str] = []

    def note(who: str, text: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {who}: {text}"
        print(line, flush=True)
        log.append(line)

    async def say(n: str, body: str, to: list[str] | None = None, thread: str | None = None) -> None:
        args = {"body": body}
        if thread:
            args["thread_id"] = thread
        if to:
            await agents[n].op("send_targeted_message", target_names=to, **args)
        else:
            await agents[n].op("post_message", **args)
        note(n, ("@" + ",@".join(to) + " " if to else "") + body)

    async def on_triager(p: dict) -> None:
        body = strip_mentions(p.get("body", ""))
        note(f"<- {TRIAGER} from {p.get('sender_name')}", body[:120].replace("\n", " "))
        if board.confirm(body):
            await say(TRIAGER, "Noted, confirmed in the room.\n" + board.render(), thread=p.get("message_id"))
            return
        t = triage(body, date.today())
        board.set(t.event, t.status)
        msg = render_triage(t, body) + "\n\n" + board.render()
        if t.status == "SKIP":
            await say(TRIAGER, msg, thread=p.get("message_id"))
        else:
            await say(TRIAGER, msg + "\n\n" + handoff_line(t, OPS).split(" ", 1)[1], to=[OPS])
            ops_queue.append(t)

    ops_queue: list = []

    async def on_ops(p: dict) -> None:
        note(f"<- {OPS} from {p.get('sender_name')}", p.get("body", "")[:120].replace("\n", " "))
        if not ops_queue:
            return
        t = ops_queue.pop(0)
        text = plan(t)
        (ROOT / "plan.md").open("a").write(text + "\n\n")
        await say(OPS, text, thread=p.get("message_id"))

    tasks = [asyncio.create_task(agents[TRIAGER].run(room, on_triager)),
             asyncio.create_task(agents[OPS].run(room, on_ops))]
    if a.demo:
        tasks.append(asyncio.create_task(agents[FEEDER].run(room, None)))
    for n in names:
        await asyncio.wait_for(agents[n].ready.wait(), 20)

    if a.demo:
        await asyncio.sleep(2)
        for f in sorted((ROOT / "demo").glob("0*.md")):
            await say(FEEDER, f.read_text().strip(), to=[TRIAGER])
            await asyncio.sleep(6)
        await say(FEEDER, "Registered for the CTF, mark it.", to=[TRIAGER])
        await asyncio.sleep(6)
        if a.log:
            ctx = await agents[FEEDER].op("read_context")
            Path(a.log).write_text("\n".join(log) + "\n")
            Path(a.log).with_suffix(".context.json").write_text(json.dumps(ctx, indent=2, ensure_ascii=False))
        for t in tasks:
            t.cancel()
        return
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
