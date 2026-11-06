# Campus Campaign Desk

A [Switch](https://github.com/sandbox-quantum/switch) room where a student
competition team and two AI agents triage online hackathon / CTF / contest
announcements and turn them into checklists, so the team registers on time,
submits, and collects participation certificates.

Built for **Flip the Switch** (WeMakeDevs x DevTools Academy x Switch,
Nov 4-7 2026), **Track 01 - Best Business Workflow**.

## The problem

Student teams get event announcements from dozens of channels: uni chats,
forwarded posts, CTF calendars. Each one has to be checked for the same
things (online or not? certificate? deadline? team size?) and then turned
into actions. Doing this by hand is slow, deadlines get missed, and offline
events slip in by accident.

## The workflow

```
person pastes an announcement in the team chat (Mattermost / Slack / Discord / Telegram)
        |
        v   Switch room "desk-campaign-desk"
desk-triager  -> one-line restatement + triage card + GO / CHECK / SKIP
        |  "@desk-ops please plan: ..."   (agent-to-agent handoff in the room)
        v
desk-ops      -> checklist with owners and dates, question to organisers,
                 draft team message; appends to plan.md
        |
        v
person confirms ("registered", "submitted") -> desk-ops updates status
```

| Agent | Addressing | Role |
|---|---|---|
| `desk-triager` | `anyone` | Extracts event, dates, format, certificate terms, deadline, team size, needed action. Classifies GO / CHECK / SKIP. Keeps a running list of open events. |
| `desk-ops` | `owner-agents` | Only acts on the triager's handoffs or its owner. Produces checklists, organiser questions and reusable reply drafts. Never marks work done without a human confirming in the room. |

## Why Switch is essential

Switch is the whole runtime of this project; nothing else connects the parts:

- **The room** is the shared log both agents and the people read from. The
  triager's running list and desk-ops' plans live there.
- **Agent-to-agent handoff** happens by addressing `@desk-ops` inside the
  room; `addressing: owner-agents` means desk-ops ignores random chatter and
  only works on triaged items.
- **The bridge** mirrors the room into the team's chat app (bundled
  Mattermost by default), so teammates use the agents without installing
  anything.
- **Switch Console** creates both agents, each backed by an existing coding
  agent (Claude Code, Codex or OpenCode) in its own working directory.

Remove Switch and you have two unconnected CLI sessions with no team chat,
no handoff and no human confirmation step.

## Repository layout

| Path | What it is |
|---|---|
| `campus-campaign-desk.template.yaml` | Switch template (same format as `examples/agent-templates/triage-pair.template.yaml` in the Switch repo): params, two agents, one bridged room, kickoff |
| `demo/01..03-*.md` | Fictional sample announcements: a GO, a CHECK and a SKIP case |
| `demo/SCRIPT.md` | Step-by-step demo / video script with expected agent behaviour |
| `desk_agents/` | Custom Switch protocol agents (path b) and the deterministic triage logic |
| `tests/` | Tests on the three demo samples |
| `deploy/` | Headless local Switch server notes |
| `demo/runs/` | Logs of real runs |
| `scripts/validate_template.py` | Checks the YAML, agent references, @mentions, and that no secrets/emails are in it |

## Two ways to run it

**(a) Official path - Switch Console + a coding agent.** Import the template
below; Console backs `desk-triager` and `desk-ops` with Claude Code, Codex or
OpenCode, and the instructions in the YAML drive them.

**(b) No coding-agent account needed - custom protocol agents.**
`desk_agents/` implements the same two agents as plain Python clients of the
[Switch agent protocol](https://docs.switchagents.ai/switch-rooms/internals/agent-protocol):
they register with `POST /agents`, open `/agents/{id}/connection/ws`, answer
pings, act only on `message` events with `payload.addressed: true`, and work
through Switch operations (`create_room`, `send_targeted_message`,
`post_message`, `read_context`). Extraction is deterministic (dates, online /
hybrid / offline, certificate wording, deadlines), so the demo is
repeatable. Handoff to desk-ops is a real addressed Switch message.

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q tests               # 5 tests on the demo samples
# start a local Switch server: see deploy/README.md
printf 'SWITCH_URL=http://localhost:8000\nSWITCH_REGISTRATION_KEY=<bootstrap key>\n' > .env
.venv/bin/python -m desk_agents.run_agents --create-room              # agents wait in desk-campaign-desk
.venv/bin/python -m desk_agents.run_agents --create-room --demo \
    --log demo/runs/my-run.log                                       # headless scripted run
```

Without `--demo`, people paste announcements into the room (in Mattermost
when the server runs with `--profile collab`) and address `@desk-triager`.
`--demo` adds `desk-demo-feeder`, a scripted agent that pastes the three
samples and the confirmation line, standing in for a person so the run
needs no chat client.

**Real run log:** `demo/runs/run-20261106-1056.log` and its
`.context.json` (the room history read back through `read_context`) come
from an actual run against a local Switch 0.31.0 server (internal room, no
Mattermost bridge). Note: on Switch 0.31.0 an agent cannot change its own
`addressing` (the server answers 403 and tells the owner to change it in
Console); the run works anyway because all three agents share one owner.

## Run it with Switch Console (path a)

Requirements: Docker, Switch Console, and one AI coding agent you are signed
in to (Claude Code, Codex or OpenCode). Switch is free; the agent needs its
own subscription or API key.

1. Install **Switch Console** from the
   [latest release](https://github.com/sandbox-quantum/switch/releases/latest)
   (macOS; Windows and Linux AppImage/DEB in early access). Install and start
   **Docker**.
2. Follow the [quickstart](https://docs.switchagents.ai/switch-rooms/getting-started):
   *Get started* -> *On this computer* -> *Start*, wait for
   "Local server is running", pick your coding agent for switch-buddy.
3. Validate the template (optional): `pip install pyyaml && python3 scripts/validate_template.py`
4. In Switch Console open **Templates**, load
   `campus-campaign-desk.template.yaml`, set `team` (default `desk`), leave
   `provider` / `bridge` on their defaults (first installed agent, server's
   default chat app = bundled Mattermost), and deploy.
5. Open the room `desk-campaign-desk` in Mattermost. The kickoff message
   makes both agents introduce themselves.
6. Paste the samples from `demo/` in order and follow `demo/SCRIPT.md`.

To use Slack, Discord or Telegram instead, connect it in Switch Console
(or ask switch-buddy) before deploying and choose it in the `bridge` field.

## Data and safety

The agents are instructed not to repeat phones, emails or passwords, to
write "not stated" instead of guessing, and to use placeholders like
`<captain>` in drafts. All sample events in `demo/` are fictional. No keys
or credentials are stored in this repository.

## License

MIT, see [LICENSE](LICENSE).
